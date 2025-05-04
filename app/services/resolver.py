from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.record_db import DNSRecord, RecordType
from datetime import datetime, timedelta
import json

async def resolve_hostname(hostname: str, db: AsyncSession):
    visited = set()
    original_hostname = hostname.lower()
    current = original_hostname
    cname_chain = []

    while True:
        if current in visited:
            return None
        visited.add(current)

        result = await db.execute(
            select(DNSRecord).where(DNSRecord.hostname == current)
        )
        records = result.scalars().all()
        now = datetime.utcnow()
        valid_records = [
            r for r in records
            if (r.timestamp_created + timedelta(seconds=r.ttl_seconds)) >= now
        ]
        if not valid_records:
            return None

        aaaa_records = [
            json.loads(r.value) if isinstance(r.value, str) else r.value
            for r in valid_records if r.type in [RecordType.A, RecordType.AAAA]
        ]
        flat_ips = [ip for sublist in aaaa_records for ip in sublist]

        if flat_ips:
            return {
                "hostname": original_hostname,
                "resolvedIps": flat_ips,
                "recordType": "CNAME" if cname_chain else "A/AAAA",
                "pointsTo": cname_chain[-1] if cname_chain else original_hostname
            }

        # CNAME chain
        cname_record = next((r for r in valid_records if r.type == RecordType.CNAME), None)
        if cname_record:
            cname_target = cname_record.value.strip('"').lower()
            cname_chain.append(cname_target)
            current = cname_target
        else:
            return None

def is_expired(record: DNSRecord) -> bool:
    expiry_time = record.timestamp_created + timedelta(seconds=record.ttl_seconds)
    return datetime.utcnow() > expiry_time
