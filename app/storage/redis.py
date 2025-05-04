import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def cache_resolved_hostname(hostname: str, ips: list[str], ttl: int = 3600):
    await redis_client.setex(f"dns_cache:{hostname}", ttl, ",".join(ips))

async def get_cached_hostname(hostname: str):
    result = await redis_client.get(f"dns_cache:{hostname}")
    if result:
        return result.split(",")
    return None

async def invalidate_cache(hostname: str):
    await redis_client.delete(f"dns_cache:{hostname}")
