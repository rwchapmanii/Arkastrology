from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ReadingHistoryItem(BaseModel):
    id: str
    chart_type: str
    status: str
    headline: str
    subject_label: str
    created_at: str
    updated_at: Optional[str] = None
    favorite: bool = False
    tags: List[str] = Field(default_factory=list)
    reading_payload: dict[str, Any]


class ReadingHistoryTagFacet(BaseModel):
    tag: str
    count: int


class ReadingHistoryChartTypeFacet(BaseModel):
    chart_type: str
    count: int


class ReadingHistoryListResponse(BaseModel):
    status: str = "ok"
    items: List[ReadingHistoryItem] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 20
    has_more: bool = False
    next_offset: Optional[int] = None
    favorites_count: int = 0
    available_tags: List[ReadingHistoryTagFacet] = Field(default_factory=list)
    chart_type_counts: List[ReadingHistoryChartTypeFacet] = Field(default_factory=list)


class ReadingHistoryRecord(BaseModel):
    user_id: str
    id: str
    chart_type: str
    status: str
    headline: str
    subject_label: str
    created_at: str
    updated_at: Optional[str] = None
    favorite: bool = False
    tags: List[str] = Field(default_factory=list)
    reading_payload: dict[str, Any]


class ReadingHistoryUpdateRequest(BaseModel):
    favorite: Optional[bool] = None
    tags: Optional[List[str]] = None


class ReadingHistoryDetailResponse(BaseModel):
    status: str = "ok"
    item: Optional[ReadingHistoryItem] = None
