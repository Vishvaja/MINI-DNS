import pytest
import asyncio
import random
import string

HEADERS = {"X-API-Key": "supersecret"}

def random_hostname(prefix):
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{suffix}.com"

@pytest.mark.asyncio
async def test_dns_resolver_with_cname_chain(client):
    # Generate unique hostnames to avoid conflict
    direct_a = random_hostname("direct")
    alias1 = random_hostname("alias1")
    alias2 = random_hostname("alias2")

    # A record
    a_record = {
        "hostname": direct_a,
        "type": "A",
        "value": ["9.9.9.9"],
        "ttl_seconds": 300
    }

    # CNAME -> A
    cname1 = {
        "hostname": alias1,
        "type": "CNAME",
        "value": direct_a,
        "ttl_seconds": 300
    }

    # CNAME -> CNAME -> A
    cname2 = {
        "hostname": alias2,
        "type": "CNAME",
        "value": alias1,
        "ttl_seconds": 300
    }

    # Add A record
    r1 = await client.post("/api/dns/", json=a_record, headers=HEADERS)
    assert r1.status_code == 200

    await asyncio.sleep(0.05)

    # Add first CNAME
    r2 = await client.post("/api/dns/", json=cname1, headers=HEADERS)
    assert r2.status_code == 200

    await asyncio.sleep(0.05)

    # Add second CNAME
    r3 = await client.post("/api/dns/", json=cname2, headers=HEADERS)
    assert r3.status_code == 200

    await asyncio.sleep(0.1)

    # Resolve alias2 (should follow alias2 -> alias1 -> direct_a)
    resolve_resp = await client.get(f"/api/dns/{alias2}", headers=HEADERS)
    assert resolve_resp.status_code == 200
    data = resolve_resp.json()

    assert data["hostname"] == alias2
    assert data["pointsTo"] == direct_a
    assert data["resolvedIps"] == ["9.9.9.9"]
    assert data["recordType"] == "CNAME"
