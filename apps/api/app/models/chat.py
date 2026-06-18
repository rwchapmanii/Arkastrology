from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class GroundedChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class GroundedChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    reading_payload: Optional[dict[str, Any]] = None
    history: List[GroundedChatTurn] = Field(default_factory=list)


class GroundedChatSource(BaseModel):
    title: str
    excerpt: str
    source_type: str
    source_layer: Optional[str] = None
    source_ref: Optional[str] = None


class GroundedChatResponse(BaseModel):
    status: str
    answer: str
    sources: List[GroundedChatSource] = Field(default_factory=list)
    grounding_notes: List[str] = Field(default_factory=list)
