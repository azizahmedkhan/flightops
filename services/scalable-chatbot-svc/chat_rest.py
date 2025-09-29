"""Separate REST fallback endpoints for the scalable chatbot service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Request payload for creating a chat session via REST."""

    session_id: Optional[str] = None
    customer_name: str
    customer_email: str
    flight_no: Optional[str] = None
    date: Optional[str] = None


class ChatMessage(BaseModel):
    """Request payload for sending a chat message via REST."""

    session_id: str
    message: str
    client_id: Optional[str] = None


def create_chat_router(
    service,
    redis_manager,
    process_chat_message: Callable[[str, Dict[str, Any], str], Awaitable[None]],
) -> APIRouter:
    """Build a router containing the chat REST fallback endpoints."""

    router = APIRouter(prefix="/chat", tags=["chat"])

    @router.post("/session")
    async def create_session(request: SessionCreate, req: Request):
        service.logger.debug("Create session via REST fallback")

        try:
            session_id = request.session_id or str(uuid.uuid4())

            session_context = {
                "session_id": session_id,
                "customer_name": request.customer_name,
                "customer_email": request.customer_email,
                "flight_no": request.flight_no,
                "date": request.date,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0,
            }

            await redis_manager.set_session_context(session_id, session_context)

            service.log_request(req, {"status": "success", "session_id": session_id})
            return {
                "session_id": session_id,
                "status": "created",
                "context": session_context,
            }

        except Exception as exc:  # noqa: BLE001
            service.log_error(exc, "create_session")
            raise HTTPException(status_code=500, detail="Failed to create session") from exc

    @router.get("/session/{session_id}")
    async def get_session(session_id: str, req: Request):
        service.logger.debug("Get session info via REST fallback session_id=%s", session_id)

        try:
            context = await redis_manager.get_session_context(session_id)
            if not context:
                raise HTTPException(status_code=404, detail="Session not found")

            service.log_request(req, {"status": "success", "session_id": session_id})
            return {"session_id": session_id, "context": context}

        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            service.log_error(exc, "get_session")
            raise HTTPException(status_code=500, detail="Failed to get session") from exc

    @router.post("/message")
    async def send_message(message: ChatMessage, req: Request):
        service.logger.debug(
            "Send message via REST fallback session_id=%s client_id=%s",
            message.session_id,
            message.client_id,
        )

        try:
            session_context = await redis_manager.get_session_context(message.session_id)
            if not session_context:
                raise HTTPException(status_code=404, detail="Session not found")

            await process_chat_message(
                message.session_id,
                {"message": message.message},
                message.client_id or "rest",
            )

            service.log_request(
                req,
                {"status": "success", "session_id": message.session_id},
            )
            return {"status": "message_sent", "session_id": message.session_id}

        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            service.log_error(exc, "send_message")
            raise HTTPException(status_code=500, detail="Failed to send message") from exc

    return router


__all__ = [
    "ChatMessage",
    "SessionCreate",
    "create_chat_router",
]
