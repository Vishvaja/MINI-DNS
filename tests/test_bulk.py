import pytest
from httpx import AsyncClient
from app.main import app
import json

@pytest.mark.asyncio
async def test_bulk_import():
    sample_records = [
        {
            "hostname": "bulk1.com",
            "type": "A",
            "value": ["1.2.3.4"],
            "ttl_seconds": 300
        },
        {
            "hostname": "bulk2.com",
            "type": "CNAME",
            "value": "bulk1.com",
            "ttl_seconds": 300
        }
    ]
    file_data = json.dumps(sample_records)
    files = {"file": ("records.json", file_data)}

    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        # Import the records
        resp = await ac.post("/api/dns/bulk/import", files=files, headers={"X-API-Key": "supersecret"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Bulk import completed"

        # Verify bulk1.com A record
        res1 = await ac.get("/api/dns/bulk1.com", headers={"X-API-Key": "supersecret"})
        assert res1.status_code == 200
        assert res1.json()["resolved"] == ["1.2.3.4"]

        # Verify bulk2.com CNAME record resolves to bulk1.com
        res2 = await ac.get("/api/dns/bulk2.com", headers={"X-API-Key": "supersecret"})
        assert res2.status_code == 200
        assert res2.json()["resolved"] == ["1.2.3.4"]
