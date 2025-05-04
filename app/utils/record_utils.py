# app/utils/record_utils.py

from app.models.record_db import RecordType, DNSRecord
from app.models.record_schema import DNSRecordInput
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel, Field, IPvAnyAddress, validator
from app.core.errors import ErrorCode, raise_error
import json
import logging

logger = logging.getLogger(__name__)

async def check_for_duplicate_records(existing_records, record):
    for existing in existing_records:
        logger.debug(f"Existing Record: {existing.type}, New Record: {record.type}")
        
        if existing.type.value in [RecordType.A.value, RecordType.AAAA.value] and record.type == existing.type.value:
            existing_values = json.loads(existing.value)
            new_values = [str(ip) for ip in record.value]
            logger.debug(f"Existing values: {existing_values}, New values: {new_values}")
            
            intersection = set(existing_values).intersection(set(new_values))
            if intersection:
                logger.error(f"Duplicate record found for {record.hostname}")
                raise_error(ErrorCode.DUPLICATE_RECORD, status_code=409)

        elif existing.type != record.type:
            logger.error(f"Duplicate record type for {record.hostname}")
            raise_error(ErrorCode.DUPLICATE_RECORD, status_code=409)

#We can further implement  acname depth reached algo , error code has been mentioned in the error code class.
async def has_cname_cycle(start: str, target: str, db: AsyncSession, visited: set[str] = None) -> bool:
    print("In cname cycle")
    if visited is None:
        visited = set()

    current = target.lower()
    start = start.lower()

    if current == start:
        return True  # Cycle detected(dfs visited approach)

    if current in visited:
        return False  # Already checked this node

    visited.add(current)
    print("Current",current)
    print("Start", start)
    result = await db.execute(
        select(DNSRecord).where(
            DNSRecord.hostname == current,
            DNSRecord.type == RecordType.CNAME
        )
    )
    record = result.scalar()

    if not record:
        return False  

    return await has_cname_cycle(start, record.value.strip('"').lower(), db, visited)

