from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from datetime import datetime, timedelta
from app.models.record_db import DNSRecord
from app.storage.db import AsyncSessionLocal
from app.core.config import settings
import asyncio
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

async def purge_expired_records():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DNSRecord))
        records = result.scalars().all()

        for record in records:
            expiry = record.timestamp_created + timedelta(seconds=record.ttl_seconds)
            if datetime.utcnow() > expiry:
                logger.info(f"Deleting expired record: {record.hostname}")
                await db.execute(delete(DNSRecord).where(DNSRecord.hostname == record.hostname))
        await db.commit()

async def periodic_cleanup():
    while True:
        await purge_expired_records()
        await asyncio.sleep(settings.TTL_CLEANUP_INTERVAL)

def start_cleanup_task(app: FastAPI):
    @app.on_event("startup")
    async def start_task():
        asyncio.create_task(periodic_cleanup())
