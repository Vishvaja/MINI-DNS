from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging
from app.models.record_db import DNSRecord, RecordType
from app.models.record_schema import DNSRecordInput
from pydantic import ValidationError
from app.services.CRUD import validate_hostname,insert_new_record,delete_record_by_value
from app.services.CRUD import validate_hostname,fetch_by_hostname,insert_new_record,delete_record_by_value
from app.utils.record_utils import (
    check_for_duplicate_records,
    has_cname_cycle
)
from app.core.errors import ErrorCode, raise_error

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
        # Read and clean file contents
        contents = await file.read()
        logger.info(f"Raw file contents: {contents[:200]}...")  # Log first 200 chars
        cleaned_contents = contents.decode("utf-8").replace("\r\n", "\n").strip()
        logger.info(f"Cleaned file contents: {cleaned_contents[:500]}...")

        # Parse the cleaned contents to get the list of records
        try:
            raw_records = json.loads(cleaned_contents)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")

        if not isinstance(raw_records, list):
            raise HTTPException(status_code=400, detail="JSON must be a list of DNS records")

        # Initialize counters for success, skipped, and error records
        success = 0
        skipped = 0
        errors = []

        # Iterate through each record and process it
        for idx, item in enumerate(raw_records, start=1):
            try:
                logger.info(f"Processing record at index {idx}: {item}")

                # Validate the hostname - here since json processing must be careful
                hostname = item.get("hostname").lower()
                logger.info("Hostname %s",hostname)
                existing_records = await validate_hostname(hostname, db)
                logger.info(f"Existing records for {hostname}: {existing_records}")

                # Handle delete operation for action delete
                if item.get("action") == "delete":
                    record_type = item.get("type")
                    record_value = item.get("value")
                    if record_type not in [e.value for e in RecordType]:
                        raise HTTPException(status_code=400, detail="Invalid record type for delete operation")
                    result = await delete_record_by_value(hostname, record_type, record_value, db)
                    skipped += 1
                    continue
                record = DNSRecord()
                record.hostname = item.get("hostname")
                record.type = item.get("type")
                record.value = item.get("value")
                record.ttl_seconds = item.get("ttl_seconds")
                #Same logic as addition
                existing_records = await validate_hostname(hostname, db)

                if existing_records:
                    await check_for_duplicate_records(existing_records, record)

                if record.type == RecordType.CNAME.value:
                    logger.info(f"Checking CNAME cycle for {record.hostname}")
                    has_cycle = await has_cname_cycle(record.hostname, record.value.strip('"').lower(), db)
                    if has_cycle:
                        logger.error(f"CNAME loop detected for {record.hostname}")
                        raise_error(ErrorCode.CNAME_LOOP, status_code=400)

                new_record = await insert_new_record(record, db)
                logger.info(f"New Record inserted {new_record.hostname}")
                success += 1
            except ValidationError as e:
                logger.error(f"Validation error for record at index {idx}: {e.errors()}")
                errors.append({"index": idx, "error": f"Validation error: {e.errors()}"})
                skipped += 1
            except HTTPException as e:
                errors.append({"index": idx, "error": e.detail})
                skipped += 1
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})
                skipped += 1

            except Exception as e:
                logger.error(f"Error processing record at index {idx}: {e}")
                errors.append({"index": idx, "error": str(e)})
                skipped += 1

        await db.commit()

        return {
            "message": "Bulk import completed",
            "records_imported": success,
            "records_skipped": skipped,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error during bulk import: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
