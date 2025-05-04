import pytest
import asyncio
import random
import string

HEADERS = {"X-API-Key": "supersecret"}

def random_hostname(prefix):
    return f"{prefix}-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6)) + ".com"

@pytest.mark.asyncio
async def test_list_dns_records(client):
    # Use different hostnames for each record type due to API constraints
    hostname_a = random_hostname("list-a")
    hostname_txt = random_hostname("list-txt")

    # Create A and TXT records under different hostnames
    records = [
        {
            "hostname": hostname_a,
            "type": "A",
            "value": ["192.168.123.1"],
            "ttl_seconds": 300
        },
        {
            "hostname": hostname_txt,
            "type": "TXT",
            "value": ["v=spf1 include:_spf.example.com ~all"],
            "ttl_seconds": 300
        }
    ]

    # Insert records
    for record in records:
        res = await client.post("/api/dns/", json=record, headers=HEADERS)
        assert res.status_code == 200
        await asyncio.sleep(0.05)

    # Fetch and validate A record
    res_a = await client.get(f"/api/dns/{hostname_a}/records", headers=HEADERS)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["hostname"] == hostname_a
    print(f"A Record Response for {hostname_a}:", data_a)
    assert any(r["type"] == "A" and r["value"] == "192.168.123.1" for r in data_a["records"])


    # Fetch and validate TXT record
    res_txt = await client.get(f"/api/dns/{hostname_txt}/records", headers=HEADERS)
    assert res_txt.status_code == 200
    data_txt = res_txt.json()
    print(f"TXT Record Response for {hostname_txt}:", data_txt)
    assert data_txt["hostname"] == hostname_txt
    assert any(r["type"] == "TXT" and "spf" in r["value"] for r in data_txt["records"])
