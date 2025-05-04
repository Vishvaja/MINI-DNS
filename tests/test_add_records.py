import pytest
import asyncio

HEADERS = {"X-API-Key": "supersecret"}

@pytest.mark.asyncio
async def test_add_dns_record_cases(client):
    # 1. Add valid A record
    response = await client.post("/api/dns/", json={
        "hostname": "example.com",
        "type": "A",
        "value": ["192.168.0.1"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 200

    await asyncio.sleep(0.05)

    # 2. Add duplicate A record (should conflict)
    await client.post("/api/dns/", json={
        "hostname": "duplicate.com",
        "type": "A",
        "value": ["192.168.0.2"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    await asyncio.sleep(0.05)
    duplicate_response = await client.post("/api/dns/", json={
        "hostname": "duplicate.com",
        "type": "A",
        "value": ["192.168.0.2"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert duplicate_response.status_code == 409

    await asyncio.sleep(0.05)

    # 3. Add valid MX record
    response = await client.post("/api/dns/", json={
        "hostname": "mail.com",
        "type": "MX",
        "value": {"priority": 10, "host": "mx1.mail.com"},
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 200

    await asyncio.sleep(0.05)

    # 4. Invalid IP address
    response = await client.post("/api/dns/", json={
        "hostname": "badip.com",
        "type": "A",
        "value": ["999.999.999.999"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 422

    await asyncio.sleep(0.05)

    # 5. Invalid hostname
    response = await client.post("/api/dns/", json={
        "hostname": "invalid_hostname!@#",
        "type": "A",
        "value": ["1.2.3.4"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 400

    await asyncio.sleep(0.05)

    # 6. Add valid TXT record
    response = await client.post("/api/dns/", json={
        "hostname": "txtentry.com",
        "type": "TXT",
        "value": ["v=spf1 include:_spf.google.com ~all"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 200

    await asyncio.sleep(0.05)

    # 7. Add valid CNAME record
    response = await client.post("/api/dns/", json={
        "hostname": "alias.com",
        "type": "CNAME",
        "value": "target.com",
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 200

    await asyncio.sleep(0.05)

    # 8. Conflict: Add A record after CNAME (same hostname)
    response = await client.post("/api/dns/", json={
        "hostname": "alias.com",
        "type": "A",
        "value": ["1.1.1.1"],
        "ttl_seconds": 300
    }, headers=HEADERS)
    assert response.status_code == 409
