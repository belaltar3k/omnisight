from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.db.redis import get_redis_client

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list = []
    tools_used: list = []


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db=Depends(get_db)):
    from app.services.chatbot_service import ChatbotService

    session_id = req.session_id or str(uuid.uuid4())

    redis = await get_redis_client()
    service = ChatbotService(redis_client=redis)

    result = await service.chat(
        session_id=session_id,
        message=req.message,
        db=db,
    )
    return ChatResponse(**result)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Return full conversation history for a session."""
    redis = await get_redis_client()
    from app.services.chatbot_service import ChatbotService
    service = ChatbotService(redis_client=redis)
    history = await service.get_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    redis = await get_redis_client()
    from app.services.chatbot_service import ChatbotService
    service = ChatbotService(redis_client=redis)
    await service.clear_history(session_id)
    return {"ok": True, "session_id": session_id}
