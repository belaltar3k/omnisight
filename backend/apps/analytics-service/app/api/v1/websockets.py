# app/api/v1/websockets.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.messaging.redis_pubsub import subscribe_dashboard_updates

logger = logging.getLogger("omnisight.analytics.websocket")

router = APIRouter(prefix="/ws", tags=["Real-Time"])

@router.websocket("/live-dashboard")
async def live_dashboard_websocket(websocket: WebSocket):
    """
    Frontend clients connect here to receive live dashboard updates.
    """
    await websocket.accept()
    logger.info("New WebSocket connection established for live dashboard.")
    
    try:
        # Listen to Redis generator
        async for message in subscribe_dashboard_updates():
            await websocket.send_text(message)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()