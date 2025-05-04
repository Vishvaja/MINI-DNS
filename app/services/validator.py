from app.models.record_db import RecordType, DNSRecord
from app.models.record_schema import DNSRecordInput
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta
from app.core.errors import ErrorCode, raise_error


if not is_valid_hostname(hostname):
    raise_error(ErrorCode.INVALID_HOSTNAME, status_code=400)

def validate_dns_record_type_conflict(new_type: RecordType, existing: List[DNSRecord]):
    if new_type == RecordType.A:
        for rec in existing:
            if rec.type == RecordType.CNAME:
                raise HTTPException(status_code=409, detail="CNAME already exists for this hostname")
    elif new_type == RecordType.CNAME:
        for rec in existing:
            if rec.type in [RecordType.A, RecordType.AAAA]:
                raise HTTPException(status_code=409, detail="A/AAAA records already exist for this hostname")
            if rec.type == RecordType.CNAME:
                raise HTTPException(status_code=409, detail="Only one CNAME record allowed per hostname")



async def check_cname_loop(start: str, target: str, db: AsyncSession, max_depth: int = 10):
    visited = set()
    current = target.lower()
    depth = 0

    while True:
        if current == start:
            raise HTTPException(status_code=400, detail="CNAME loop detected")
        if current in visited:
            break
        visited.add(current)
        result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == current))
        records = result.scalars().all()
        cname = next((r for r in records if r.type == RecordType.CNAME), None)
        if not cname:
            break
        current = cname.value.lower()
        depth += 1
        if depth > max_depth:
            raise HTTPException(status_code=400, detail="CNAME chaining exceeds allowed depth")
