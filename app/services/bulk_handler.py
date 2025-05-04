# app/services/bulk_handler.py

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json
from sqlalchemy.exc import IntegrityError
import logging
from app.models.record_db import DNSRecord, RecordType
from app.models.record_schema import DNSRecordInput
from app.storage import record_repository as repo
from pydantic import ValidationError

from app.utils.hostname_utils import is_regex_hostname
from app.utils.record_utils import (
    validate_dns_record_type_conflict,
    has_cname_cycle,
)
from app.core.errors import ErrorCode, raise_error
from app.services.CRUD import validate_hostname,insert_new_record,delete_record_by_value


logger = logging.getLogger(__name__)

async def export_dns_records(db: AsyncSession):
    from sqlalchemy import select
    result = await db.execute(select(DNSRecord))
    records = result.scalars().all()
    return [
        {
            "hostname": r.hostname,
            "type": r.type.value,
            "value": r.value,
            "ttl_seconds": r.ttl_seconds,
            "timestamp_created": r.timestamp_created.isoformat(),
        }
        for r in records
    ]

async def bulk_import(file, db):
    try:
        contents = await file.read()

        # Log raw contents to inspect the input
        logger.info(f"Raw file contents: {contents[:200]}...")  # Log first 200 chars

        # Clean up the content by removing extra newlines and carriage returns
        cleaned_contents = contents.decode("utf-8").replace("\r\n", "\n").strip()

        # Log cleaned contents for further inspection
        logger.info(f"Cleaned file contents: {cleaned_contents[:500]}...")

        try:
            raw_records = json.loads(cleaned_contents)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")

        # Ensure the parsed JSON is a list of records
        if not isinstance(raw_records, list):
            raise HTTPException(status_code=400, detail="JSON must be a list of DNS records")

        # Initialize counters for success, skipped, and error records
        success = 0
        skipped = 0
        errors = []

        # Step 2: Iterate through each record and process it
        for idx, item in enumerate(raw_records, start=1):
            try:
                # Validate the hostname
                hostname = item.get("hostname", "").lower()
                existing_records = await validate_hostname(hostname, db)
                print("Existing record",existing_records)
                # If the record type is delete, use the delete logic
                if item.get("action") == "delete":
                    record_type = item.get("type")
                    record_value = item.get("value")
                    # Ensure type is a valid RecordType
                    if record_type not in [e.value for e in RecordType]:
                        raise HTTPException(status_code=400, detail="Invalid record type for delete operation")
                    # Call delete function
                    result = await delete_record_by_value(hostname, record_type, record_value, db)
                    skipped += 1
                    continue
                print("Moving On")
                print("Item",item)
                # Otherwise, insert the record (reuse existing logic)
                # Check if item has the required fields before validation
                try:
                    required_fields = ["hostname", "type", "value"]
                    missing_fields = [field for field in required_fields if field not in item]
                    if missing_fields:
                        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
                    print("All items present")
                    # Perform the validation using Pydantic
                    record = DNSRecordInput.parse_obj(item)  # Validate the record
                    logger.info(f"Record validated successfully: {record}")
                    await insert_new_record(record, db)  # Insert the validated record
                    success += 1
                except ValidationError as e:
                # Log and store detailed validation error
                    logger.error(f"Validation error for record at index {idx}: {e.errors()}")
                    errors.append({"index": idx, "error": f"Validation error: {e.errors()}"})
                    skipped += 1
                except HTTPException as e:
                    errors.append({"index": idx, "error": e.detail})
                    skipped += 1
                except Exception as e:
                    errors.append({"index": idx, "error": str(e)})
                    skipped += 1
                
            except ValidationError as e:
                # Log and store detailed validation error
                logger.error(f"Validation error for record at index {idx}: {e.errors()}")
                errors.append({"index": idx, "error": f"Validation error: {e.errors()}"})
                skipped += 1
            except HTTPException as e:
                errors.append({"index": idx, "error": e.detail})
                skipped += 1
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})
                skipped += 1

        # Step 3: Commit the changes to the database
        await db.commit()

        # Step 4: Return a summary of the bulk import operation
        return {
            "message": "Bulk import completed",
            "records_imported": success,
            "records_skipped": skipped,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error during bulk import: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")