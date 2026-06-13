# app/db/redis.py
import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger("omnisight.analytics.redis")

# Create an async redis connection pool
redis_client = redis.from_url(
    settings.REDIS_URL, 
    encoding="utf-8", 
    decode_responses=True
)

async def check_redis_connection():
    """Verify Redis connection on startup"""
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")