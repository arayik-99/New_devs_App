import json
import redis.asyncio as redis
from app.services.reservations import calculate_total_revenue
from typing import Dict, Any
import os

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

CACHE_TTL_SECONDS = 300

def revenue_cache_key(property_id: str, tenant_id: str) -> str:
    if not tenant_id:
        raise ValueError("tenant_id is required to build a revenue cache key")
    return f"revenue:{tenant_id}:{property_id}"


async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    cache_key = revenue_cache_key(property_id, tenant_id)

    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        result = json.loads(cached)
        if result.get("tenant_id") == tenant_id:
            return result
        await redis_client.delete(cache_key)

    # Revenue calculation is delegated to the reservation service.

    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id)

    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(result))

    return result
