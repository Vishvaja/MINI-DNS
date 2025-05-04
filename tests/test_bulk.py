import pytest
import json
import io
import asyncio
import random
import string
from fastapi import UploadFile

HEADERS = {"X-API-Key": "supersecret"}

def random_hostname(prefix):
    """Generate a random hostname for testing purposes."""
    return f"{prefix}-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6)) + ".com"

@pytest.mark.asyncio
async def test_bulk_import_add_and_delete(client):
    # Automatically create bulk records for testing
    bulk_records = [
        {
            "hostname": random_hostname("bulk"),
            "type": "A",
            "value": ["1.1.1.1"],
            "ttl_seconds": 300
        },
        {
            "hostname": random_hostname("bulk"),
            "type": "CNAME",
            "value": random_hostname("bulk"),
            "ttl_seconds": 300
        },
        {
            "hostname": random_hostname("bulk"),
            "type": "A",
            "value": ["1.1.1.1"],
            "action": "delete"
        }
    ]

    # Convert the bulk records into a JSON file (simulate file upload)
    file_content = json.dumps(bulk_records)
    file = io.BytesIO(file_content.encode("utf-8"))  # Create a file-like object

    # Perform the bulk import upload
    response = await client.post(
        "/api/dns/bulk/import",  # Adjusted endpoint for bulk import
        headers=HEADERS,
        files={"file": ("bulk.json", file, "application/json")},
    )

    # Assert the response status code is 200 OK
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"

    result = response.json()
    print("✅ Bulk Import Result:", result)

    # Check the result structure and values
    assert "records_imported" in result
    assert "records_skipped" in result
    assert "errors" in result
    assert result["records_imported"] == 2  # 2 valid records: A + CNAME
    assert result["records_skipped"] >= 1   # 1 skipped due to delete or invalid format
