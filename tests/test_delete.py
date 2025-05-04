# tests/test_delete.py

import pytest
import asyncio
import uuid

HEADERS = {"X-API-Key": "supersecret"}

@pytest.mark.asyncio
async def test_delete_dns_records(client):
    # Unique hostname per test run
    hostname = f"delete-{uuid.uuid4().hex[:8]}.com"

    # Create A record
    a_record = {
        "hostname": hostname,
        "type": "A",
        "value": ["10.0.0.1"],
        "ttl_seconds": 300
    }
    response = await client.post("/api/dns/", json=a_record, headers=HEADERS)
    assert response.status_code == 200
    await asyncio.sleep(0.05)

    # Delete specific IP from A record
    delete_response = await client.delete(
        f"/api/dns/{hostname}?type=A&value=10.0.0.1",
        headers=HEADERS
    )
    assert delete_response.status_code == 200
    assert "deleted" in delete_response.json()["message"]

    # Try deleting a non-existing value (should 404)
    bad_delete = await client.delete(
        f"/api/dns/{hostname}?type=A&value=1.1.1.1",
        headers=HEADERS
    )
    assert bad_delete.status_code == 404

    # Try deleting a non-existing hostname
    not_found = await client.delete(
        "/api/dns/unknownhost.com?type=MX&value=mail.unknown.com",
        headers=HEADERS
    )
    assert not_found.status_code == 404
