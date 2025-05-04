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

def validate_dns_record_type_conflict(new_type: RecordType, existing: List[DNSRecord]):
    if new_type == RecordType.A:
        for rec in existing:
            if rec.type == RecordType.CNAME:
                raise_error(ErrorCode.CONFLICT_CNAME_EXISTS, status_code=409)
    elif new_type == RecordType.CNAME:
        for rec in existing:
            if rec.type in [RecordType.A, RecordType.AAAA]:
                raise_error(ErrorCode.CONFLICT_A_EXISTS, status_code=409)
            if rec.type == RecordType.CNAME:
                raise_error(ErrorCode.CONFLICT_CNAME_EXISTS, status_code=409)


async def has_cname_cycle(start: str, target: str, db: AsyncSession, visited: set[str] = None) -> bool:
    print("In cname cycle")
    if visited is None:
        visited = set()

    current = target.lower()
    start = start.lower()

    if current == start:
        return True  # Cycle detected

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
        return False  # End of chain, no cycle

    return await has_cname_cycle(start, record.value.strip('"').lower(), db, visited)


async def value_exists_for_hostname(db: AsyncSession, hostname: str, value_to_check: str) -> bool:
    """
    Checks if a given value exists in the DNS record(s) for a specific hostname.
    Handles cases where value is a list (A, AAAA, TXT) or a single value (CNAME, MX).

    Args:
        db: AsyncSession – SQLAlchemy async DB session.
        hostname: str – The DNS record hostname to search for.
        value_to_check: str – The value to check for in the record's 'value' field.

    Returns:
        True if the value exists for the given hostname, False otherwise.
    """
    result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == hostname.lower()))
    records = result.scalars().all()

    for record in records:
        try:
            parsed_value = json.loads(record.value)
            if isinstance(parsed_value, list):
                if value_to_check in parsed_value:
                    return True
            elif isinstance(parsed_value, dict):
                # for MX or structured types - match stringified version
                if value_to_check == json.dumps(parsed_value, sort_keys=True):
                    return True
            else:
                if value_to_check == parsed_value:
                    return True
        except Exception as e:
            print(f"Failed to parse value for hostname={hostname}: {e}")
            continue

    return False
