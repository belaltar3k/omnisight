# app/messaging/kafka_consumer.py
import json
import asyncio
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.incident_metric import IncidentMetric
from app.messaging.redis_pubsub import publish_dashboard_update

logger = logging.getLogger("omnisight.analytics.kafka")

def save_incident_to_db(data: dict):
    """Synchronous DB operation wrapped for the async consumer."""
    db: Session = SessionLocal()
    try:
        # Create a new time-series metric from the Kafka event
        new_metric = IncidentMetric(
            timestamp=datetime.now(timezone.utc),
            incident_id=data.get("incident_id"),
            crime_type=data.get("crime_type", "unknown"),
            priority=data.get("priority", "medium"),
            zone_id=data.get("zone_id"),
            camera_id=data.get("camera_id"), # Assuming camera_id comes in payload
            confidence=data.get("confidence", 0.0),
            status="new",
            is_false_positive=False
        )
        db.add(new_metric)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save Kafka event to DB: {e}")
    finally:
        db.close()

async def start_kafka_consumer():
    """Starts the AIOKafkaConsumer to listen for cross-service events."""
    topics = ["sentinel.incident.new", "sentinel.incident.status_changed"]
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="omnisight_analytics_group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest"
    )

    try:
        await consumer.start()
        logger.info(f"Kafka Consumer started listening to topics: {topics}")
        
        async for msg in consumer:
            payload = msg.value
            topic = msg.topic
            
            logger.info(f"Received Kafka Event on {topic}: {payload}")
            
            if topic == "sentinel.incident.new":
                data = {
                    "incident_id": payload.get("incidentId"),
                    "crime_type": payload.get("crimeType", "unknown"),
                    "priority": payload.get("priority", "medium"),
                    "zone_id": payload.get("zoneId"),
                    "camera_id": payload.get("cameraId"),
                    "confidence": payload.get("confidence", 0.0),
                }
                # 1. Save to TimescaleDB
                await asyncio.to_thread(save_incident_to_db, data)
                
                # 2. Push to Redis for WebSocket clients to update live dashboards
                dashboard_event = {
                    "type": "NEW_INCIDENT",
                    "data": data
                }
                await publish_dashboard_update(dashboard_event)

            elif topic == "sentinel.incident.status_changed":
                # Push status updates to Redis for the dashboard
                dashboard_event = {
                    "type": "STATUS_UPDATE",
                    "data": {
                        "incident_id": payload.get("incidentId"),
                        "from_status": payload.get("fromStatus"),
                        "to_status": payload.get("toStatus"),
                        "assigned_to": payload.get("assignedTo"),
                        "performed_by": payload.get("performedBy")
                    }
                }
                await publish_dashboard_update(dashboard_event)

    except Exception as e:
        logger.error(f"Kafka Consumer error: {e}")
    finally:
        await consumer.stop()