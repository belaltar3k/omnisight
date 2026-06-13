# app/messaging/redis_pubsub.py
import json
import logging
from app.db.redis import redis_client

logger = logging.getLogger("omnisight.analytics.pubsub")

CHANNEL_NAME = "dashboard_live_updates"

async def publish_dashboard_update(event_data: dict):
    """Publish real-time updates to Redis so all connected WebSockets receive it."""
    try:
        message = json.dumps(event_data)
        await redis_client.publish(CHANNEL_NAME, message)
        logger.info(f"Published update to Redis channel {CHANNEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")

async def subscribe_dashboard_updates():
    """Generator that yields new messages from the Redis Pub/Sub channel."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL_NAME)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]
    except Exception as e:
        logger.error(f"Redis subscription error: {e}")
    finally:
        await pubsub.unsubscribe(CHANNEL_NAME)