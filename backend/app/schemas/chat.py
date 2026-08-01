from __future__ import annotations

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    vehicle_id: str | None = None
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    grounded_in_report: bool  # True if a specific report's data was used as context
