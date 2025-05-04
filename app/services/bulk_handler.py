# app/services/bulk_handler.py

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json
import logging
from app.models.record_db import DNSRecord, RecordType
from app.models.record_schema import DNSRecordInput
from app.storage import record_repository as repo
from app.utils.hostname_utils import is_valid_hostname
from app.utils.record_utils import (
    validate_dns_record_type_conflict,
    has_cname_cycle,
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
