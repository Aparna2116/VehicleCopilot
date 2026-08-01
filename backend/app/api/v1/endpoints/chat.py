from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.orm import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.llm_provider import get_llm_provider

router = APIRouter(prefix="/chat", tags=["chat"])
_chat_service = ChatService(get_llm_provider())


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    history = [m.model_dump() for m in payload.history]
    reply_text, grounded = _chat_service.reply(
        db, payload.vehicle_id, payload.message, history
    )
    return ChatResponse(reply=reply_text, grounded_in_report=grounded)
