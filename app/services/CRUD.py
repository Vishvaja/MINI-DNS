from app.models.record_db import DNSRecord
from app.models.record_schema import DNSRecordInput
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json
import logging
from app.utils.hostname_utils import is_regex_hostname
from app.core.errors import ErrorCode, raise_error
from sqlalchemy import select
from pydantic import BaseModel
from app.models.record_db import DNSRecord, RecordType

logger = logging.getLogger(__name__)

async def validate_hostname(hostname: str, db):
    if not is_regex_hostname(hostname):
        logger.error(f"Invalid hostname: {hostname}")
        raise_error(ErrorCode.INVALID_HOSTNAME, status_code=400)

    result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == hostname))
    existing_records = result.scalars().all()

    return existing_records

async def fetch_by_hostname(db: AsyncSession, hostname: str):
    result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == hostname.lower()))
    return result.scalars().all()

async def insert_new_record(record: DNSRecordInput, db):
    value = (
        [str(ip) for ip in record.value]
        if isinstance(record.value, list)
        else record.value.dict() if isinstance(record.value, BaseModel)
        else str(record.value)
    )

    new_record = DNSRecord(
        hostname=record.hostname,
        type=record.type,
        value=json.dumps(value),
        ttl_seconds=record.ttl_seconds,
        timestamp_created=datetime.utcnow(),
    )
    db.add(new_record)
    await db.commit()
    logger.info(f"Record added for {record.hostname}")
    return new_record

async def delete_record_by_value(hostname: str, type: RecordType, value: str, db):
    logger.info(f"Attempting to delete record for {hostname} of type {type} with value {value}")
    result = await db.execute(
        select(DNSRecord).where(DNSRecord.hostname == hostname, DNSRecord.type == type)
    )
    records = result.scalars().all()

    if not records:
        logger.error(f"No records found for {hostname} with type {type}")
        raise_error(ErrorCode.RECORD_NOT_FOUND, status_code=404)

    for record in records:
        record_value = json.loads(record.value) if isinstance(record.value, str) else record.value
        if type in [RecordType.A, RecordType.AAAA]:
            if isinstance(record_value, list):
                if value in record_value:
                    if len(record_value) == 1:
                        logger.info(f"Deleting record {hostname} (only value {value})")
                        await db.delete(record)
                        await db.commit()
                        return {"message": f"Record deleted (only value): {value}"}
                    else:
                        logger.info(f"Removing value {value} from record for {hostname}")
                        record_value.remove(value)
                        record.value = json.dumps(record_value)
                        await db.commit()
                        return {"message": f"Value {value} removed from record"}
        else:
            if str(record_value).strip('"') == value:
                logger.info(f"Deleting record for {hostname} with value {value}")
                await db.delete(record)
                await db.commit()
                return {"message": f"Record deleted for {hostname} with value {value}"}

    logger.error(f"Value {value} not found in any record for {hostname}")
    raise_error(ErrorCode.RECORD_NOT_FOUND, status_code=404)