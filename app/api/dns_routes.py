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
from app.storage import record_repository as repo
from app.services.bulk_handler import export_dns_records
from app.storage.db import get_db
from pydantic import BaseModel
import json
from sqlalchemy import select,update
from sqlalchemy.dialects.postgresql import JSON,TEXT

# ✅ NEW: validation utils
from app.utils.hostname_utils import is_valid_hostname
from app.utils.record_utils import (
    validate_dns_record_type_conflict,
    value_exists_for_hostname,
    has_cname_cycle
)
from app.core.errors import ErrorCode, raise_error

router = APIRouter()

@router.post("/", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def add_dns_record(request: Request, record: DNSRecordInput, db: AsyncSession = Depends(get_db)):
    hostname = record.hostname.lower()
    print("here")
    # Step 1: ✅ Validate hostname
    if not is_valid_hostname(hostname):
        raise_error(ErrorCode.INVALID_HOSTNAME, status_code=400)

    # Step 2: ✅ Check if value already exists for the hostname
    result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == hostname))
    existing_records = result.scalars().all()

    if existing_records:
        for existing in existing_records:
            print("In")
            print("Record:",record.type,existing.type.value)
            print(existing.type in [RecordType.A.value, RecordType.AAAA.value])
            print(record.type == existing.type.value)
            if existing.type.value in [RecordType.A.value, RecordType.AAAA.value] and record.type == existing.type.value:
                print("A record")
                existing_values = json.loads(existing.value)
                new_values = [str(ip) for ip in record.value]
                print("Exist", existing_values,new_values)
                intersection = set(existing_values).intersection(set(new_values))
                print("Intersection",intersection)
                if intersection:
                    raise_error(ErrorCode.DUPLICATE_RECORD, status_code=409)
                else:
                    continue

            elif existing.type != record.type:
                raise_error(ErrorCode.DUPLICATE_RECORD, status_code=409)

    if record.type == RecordType.CNAME.value:
        print("Inside CNAME check")
        print("record value",record.value)
        print("record hostname",record.hostname)
        has_loop = await has_cname_cycle(record.hostname, record.value, db)
        print(has_loop)
        if has_loop:
            raise_error(ErrorCode.CNAME_LOOP, status_code=400)

    # Step 3: ✅ Insert new record
    value = (
        [str(ip) for ip in record.value]
        if isinstance(record.value, list)
        else record.value.dict() if isinstance(record.value, BaseModel)
        else str(record.value)  # Ensure plain string
    )


    new_record = DNSRecord(
        hostname=hostname,
        type=record.type,
        value=json.dumps(value),
        ttl_seconds=record.ttl_seconds,
        timestamp_created=datetime.utcnow(),
    )

    db.add(new_record)
    await db.commit()
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


@router.delete("/{hostname}",dependencies=[Depends(verify_api_key)])
async def delete_dns_record(
    hostname: str,
    type: RecordType,
    value: str,
    db: AsyncSession = Depends(get_db)
):
    hostname = hostname.lower()
    value = value.strip('"')  # Clean up surrounding quotes, if any

    result = await db.execute(
        select(DNSRecord).where(DNSRecord.hostname == hostname, DNSRecord.type == type)
    )
    records = result.scalars().all()

    if not records:
        raise HTTPException(status_code=404, detail="Record not found")

    for record in records:
        record_value = json.loads(record.value) if isinstance(record.value, str) else record.value

        if type in [RecordType.A, RecordType.AAAA]:
            if isinstance(record_value, list):
                if value in record_value:
                    if len(record_value) == 1:
                        # Only one IP — delete the record
                        await db.delete(record)
                        await db.commit()
                        return {"message": f"Record deleted (only value): {value}"}
                    else:
                        # Remove just the IP and update
                        record_value.remove(value)
                        record.value = json.dumps(record_value)
                        await db.commit()
                        return {"message": f"Value {value} removed from record"}
        else:
            # For other types (CNAME, MX, TXT), do exact match
            if str(record_value).strip('"') == value:
                await db.delete(record)
                await db.commit()
                return {"message": f"Record deleted for {hostname} with value {value}"}

    raise HTTPException(status_code=404, detail="Value not found in any record")


@router.post("/bulk/import", dependencies=[Depends(verify_api_key)])
async def bulk_import(file: UploadFile, db: AsyncSession = Depends(get_db)):
    try:
        contents = await file.read()
        try:
            decoded = contents.decode("utf-8")
            raw_records = json.loads(decoded)
        except Exception:
            raise_error("Invalid JSON format", status_code=400)

        if not isinstance(raw_records, list):
            raise_error("JSON must be a list of DNS records", status_code=400)

        success = 0
        skipped = 0
        errors = []

        for idx, item in enumerate(raw_records, start=1):
            try:
                record = DNSRecordInput.model_validate(item)
                # Reuse the actual logic from the add endpoint
                await add_dns_record(request=None, record=record, db=db)
                success += 1
            except HTTPException as e:
                errors.append({"index": idx, "error": e.detail})
                skipped += 1
            except Exception as e:
                errors.append({"index": idx, "error": "Internal server error"})
                skipped += 1

        await db.commit()

        return {
            "message": "Bulk import completed",
            "records_imported": success,
            "records_skipped": skipped,
            "errors": errors,
        }


    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate entry in bulk import")


@router.get("/bulk/export",dependencies=[Depends(verify_api_key)], response_model=list)
async def bulk_export(db: AsyncSession = Depends(get_db)):
    return await export_dns_records(db)
