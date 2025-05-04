from fastapi import APIRouter, Depends, HTTPException, UploadFile, Request,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy import select, delete, and_, cast,String

from app.storage.db import AsyncSessionLocal
from app.auth.api_key import verify_api_key
from app.auth.rate_limiter import limiter
from app.models.record_schema import DNSRecordInput, DNSRecordResponse
from app.models.record_db import DNSRecord, RecordType
from app.models.response_schema import GroupedRecordsResponse
from app.services.resolver import resolve_hostname
from app.services.bulk_handler import bulk_import
from app.storage import record_repository as repo
from app.services.bulk_handler import export_dns_records
from app.storage.db import get_db
from pydantic import BaseModel
import json
from sqlalchemy import select,update
from sqlalchemy.dialects.postgresql import JSON,TEXT
from app.utils.hostname_utils import is_regex_hostname
from app.services.CRUD import validate_hostname,insert_new_record,delete_record_by_value
from app.utils.record_utils import (
    check_for_duplicate_records,
    value_exists_for_hostname,
    has_cname_cycle
)
from app.core.errors import ErrorCode, raise_error
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def add_dns_record(request: Request, record: DNSRecordInput, db: AsyncSession = Depends(get_db)):
    hostname = record.hostname.lower()
    logger.debug(f"Received request to add record for hostname: {hostname}")
    
    # Step 1: Validate the hostname and check if it exists in the database
    existing_records = await validate_hostname(hostname, db)

    # Step 2: Check for duplicate records
    if existing_records:
        await check_for_duplicate_records(existing_records, record)

    # Step 3: Check for CNAME cycle (if applicable)
    if record.type == RecordType.CNAME.value:
        logger.info(f"Checking CNAME cycle for {record.hostname}")
        has_cycle = await has_cname_cycle(record.hostname, record.value.strip('"').lower(), db)
        if has_cycle:
            logger.error(f"CNAME loop detected for {record.hostname}")
            raise_error(ErrorCode.CNAME_LOOP, status_code=400)

    # Step 4: Insert the new record into the database
    new_record = await insert_new_record(record, db)

    return {"message": "Record added", "hostname": hostname}

@router.get("/{hostname}/records", dependencies=[Depends(verify_api_key)],response_model=GroupedRecordsResponse)
async def list_records_for_hostname(hostname: str, db: AsyncSession = Depends(get_db)):
    records = await repo.fetch_by_hostname(db, hostname)
    if not records:
        raise HTTPException(status_code=404, detail="No records found for hostname")
    formatted = {
        "hostname": hostname.lower(),
        "records": []
    }

    for record in records:
        value = record.value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list) and len(parsed) == 1:
                    value = parsed[0]
                else:
                    value = parsed
            except json.JSONDecodeError:
                pass

        formatted["records"].append({
            "type": record.type,
            "value": value
        })

    return formatted


@router.get("/{hostname}",dependencies=[Depends(verify_api_key)])
async def resolve_dns(hostname: str, db: AsyncSession = Depends(get_db)):
    result = await resolve_hostname(hostname, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found or expired")
    return result


@router.delete("/{hostname}", dependencies=[Depends(verify_api_key)])
async def delete_dns_record(
    hostname: str,
    type: RecordType,
    value: str,
    db: AsyncSession = Depends(get_db)
):
    hostname = hostname.lower()
    value = value.strip('"')  # Clean up surrounding quotes, if any

    # Delegate the deletion logic to the utility function
    response = await delete_record_by_value(hostname, type, value, db)

    return response


@router.post("/bulk/import", dependencies=[Depends(verify_api_key)])
async def bulk_import_handler(file: UploadFile, db: AsyncSession = Depends(get_db)):
    # Call the bulk import function from the bulk handler
    return await bulk_import(file, db)


@router.get("/bulk/export",dependencies=[Depends(verify_api_key)], response_model=list)
async def bulk_export(db: AsyncSession = Depends(get_db)):
    return await export_dns_records(db)
