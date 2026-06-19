from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.chart import BirthProfile


class PublicChartProfileRequest(BaseModel):
    profile: BirthProfile
    headline: Optional[str] = None
    biography: Optional[str] = None
    is_discoverable: bool = True


class DirectoryProfileSummary(BaseModel):
    profile_id: str
    kind: str
    display_name: str
    headline: Optional[str] = None
    biography: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    profile: BirthProfile
    is_discoverable: bool = True
    relationship_added: bool = False
    source_label: Optional[str] = None


class DirectoryProfileListResponse(BaseModel):
    status: str = "ok"
    items: List[DirectoryProfileSummary] = Field(default_factory=list)
    total: int = 0


class RelationshipEntry(BaseModel):
    relationship_id: str
    profile_id: str
    kind: str
    display_name: str
    headline: Optional[str] = None
    biography: Optional[str] = None
    added_at: str
    tags: List[str] = Field(default_factory=list)
    profile: BirthProfile
    source_label: Optional[str] = None


class RelationshipListResponse(BaseModel):
    status: str = "ok"
    items: List[RelationshipEntry] = Field(default_factory=list)


class AddRelationshipRequest(BaseModel):
    profile_id: str


class PublicChartProfileResponse(BaseModel):
    status: str = "ok"
    public_profile: Optional[DirectoryProfileSummary] = None

