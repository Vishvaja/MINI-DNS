# storage/record_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, cast
from sqlalchemy.dialects.postgresql import JSONB
from app.models.record_db import DNSRecord
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException


async def fetch_by_hostname(db: AsyncSession, hostname: str):
    result = await db.execute(select(DNSRecord).where(DNSRecord.hostname == hostname.lower()))
    return result.scalars().all()

async def insert_record(db: AsyncSession, record: DNSRecord):
    try:
        db.add(record)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate record.")

async def delete_dns_record(db: AsyncSession, hostname: str, record_type: str, value: str) -> bool:
    # Cast string value as JSON string (e.g., "z.com" → '"z.com"')
    json_value = f'"{value}"' if record_type == "CNAME" else value

    stmt = delete(DNSRecord).where(
        and_(
            DNSRecord.hostname == hostname,
            DNSRecord.type == record_type,
            DNSRecord.value == json_value
        )
    ).returning(DNSRecord.id)

    result = await db.execute(stmt)
    await db.commit()
    return len(result.scalars().all()) > 0

async def fetch_all_records(db: AsyncSession):
    result = await db.execute(select(DNSRecord))
    return result.scalars().all()
