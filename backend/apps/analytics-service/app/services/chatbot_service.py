"""
Core chatbot logic: Redis session storage + Groq tool-calling loop.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from groq import Groq
from sqlalchemy.orm import Session

from app.services.chatbot_tools import TOOL_DEFINITIONS, dispatch_tool

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
SESSION_TTL = 86400  # 24h
MAX_HISTORY = 10     # messages kept per session (last 5 turns)
MAX_TOOL_ROUNDS = 3  # prevent infinite tool-call loops

SYSTEM_PROMPT = """You are OmniSight, an AI surveillance analyst assistant. You help security operators understand what is happening across their monitored zones using real-time and historical data.

You have access to tools that can query:
- Security incident records (crime type, status, priority, zone, camera, timestamps)
- AI vision analysis results (Qwen2.5-VL captions describing exactly what happened in each clip, with events and evidence)
- Live surveillance metrics (crowd density, people count, active alerts per camera)
- Aggregate incident statistics and trends

Guidelines:
- Always use the appropriate tool(s) to fetch real data before answering
- Always cite your sources: include timestamp, camera, and zone when referencing specific incidents
- Be concise, factual, and professional — you are speaking to security operators
- If multiple tools are relevant, call them all before composing your answer
- When a user asks about a zone or time range, pass those filters to the tools
- Format lists clearly. For summaries, group by crime type or time period.
- If no data is found, say so clearly — do not invent incidents

Current date/time (UTC): {datetime}
"""


class ChatbotService:
    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self._groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _session_key(self, session_id: str) -> str:
        return f"omnisight:chat:{session_id}"

    async def get_history(self, session_id: str) -> list[dict]:
        raw = await self._redis.get(self._session_key(session_id))
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    async def save_history(self, session_id: str, history: list[dict]) -> None:
        trimmed = history[-MAX_HISTORY:]
        await self._redis.setex(
            self._session_key(session_id),
            SESSION_TTL,
            json.dumps(trimmed),
        )

    async def clear_history(self, session_id: str) -> None:
        await self._redis.delete(self._session_key(session_id))

    async def chat(
        self,
        session_id: str,
        message: str,
        db: Session,
    ) -> dict:
        if not self._groq:
            return {
                "answer": "Chatbot is not configured. Please set GROQ_API_KEY.",
                "session_id": session_id,
                "sources": [],
                "tools_used": [],
            }

        history = await self.get_history(session_id)
        history.append({"role": "user", "content": message})

        system = SYSTEM_PROMPT.format(
            datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        )

        messages = [{"role": "system", "content": system}] + history

        tools_used = []
        sources = []

        # Tool-calling loop
        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = self._groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    max_tokens=1024,
                    temperature=0.2,
                )
            except Exception as exc:
                logger.error("Groq API error: %s", exc)
                return {
                    "answer": "I encountered an error calling the AI service. Please try again.",
                    "session_id": session_id,
                    "sources": sources,
                    "tools_used": tools_used,
                }

            choice = response.choices[0]
            msg = choice.message

            # No more tool calls — we have the final answer
            if not msg.tool_calls:
                answer = msg.content or ""
                history.append({"role": "assistant", "content": answer})
                await self.save_history(session_id, history)
                return {
                    "answer": answer,
                    "session_id": session_id,
                    "sources": sources,
                    "tools_used": tools_used,
                }

            # Append the assistant's tool-call message
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute every tool call and append results
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}") or {}
                except json.JSONDecodeError:
                    args = {}

                logger.info("Chatbot calling tool: %s args=%s", tool_name, args)
                result = dispatch_tool(tool_name, args, db)
                tools_used.append({"tool": tool_name, "args": args})

                # Collect sources for citation
                _collect_sources(tool_name, result, sources)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        # Exceeded max rounds — ask Groq to wrap up with what it has
        response = self._groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.2,
        )
        answer = response.choices[0].message.content or ""
        history.append({"role": "assistant", "content": answer})
        await self.save_history(session_id, history)
        return {
            "answer": answer,
            "session_id": session_id,
            "sources": sources,
            "tools_used": tools_used,
        }


def _collect_sources(tool_name: str, result: dict, sources: list) -> None:
    """Extract citation-worthy records from tool results."""
    if tool_name in ("search_vlm_analyses",):
        for a in result.get("analyses", [])[:5]:
            sources.append({
                "type": "vlm_analysis",
                "timestamp": a.get("timestamp"),
                "camera_id": a.get("camera_id"),
                "zone": a.get("zone"),
                "crime_type": a.get("crime_type"),
                "caption": a.get("caption"),
                "video_url": a.get("video_url"),
            })
    elif tool_name == "search_incidents":
        for inc in result.get("incidents", [])[:5]:
            sources.append({
                "type": "incident",
                "timestamp": inc.get("detected_at"),
                "camera": inc.get("camera"),
                "crime_type": inc.get("crime_type"),
                "priority": inc.get("priority"),
                "status": inc.get("status"),
            })
    elif tool_name == "semantic_search":
        for r in result.get("results", [])[:5]:
            sources.append({
                "type": "semantic_match",
                "timestamp": r.get("timestamp"),
                "camera_id": r.get("camera_id"),
                "caption": r.get("caption"),
                "similarity_score": r.get("similarity_score"),
                "video_url": r.get("video_url"),
            })
