from typing import Any

from pydantic import BaseModel, Field


class AnalyticsEventRequest(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=80)
    context: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventResponse(BaseModel):
    status: str = "recorded"
    event_id: str
    recorded_at: str
