from app.models.record_db import RecordType, DNSRecord
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

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
