from __future__ import annotations
import asyncio
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

_redis: Optional[redis.Redis] = None

def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis

async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        except Exception:
            pass
        _redis = None
