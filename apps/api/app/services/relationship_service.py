from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.models.chart import BirthProfile
from app.models.social import (
    AddRelationshipRequest,
    DirectoryProfileListResponse,
    DirectoryProfileSummary,
    PublicChartProfileRequest,
    PublicChartProfileResponse,
    RelationshipEntry,
    RelationshipListResponse,
)
from app.services.auth_service import STORE_LOCK, USERS_PATH, _load_users_store, _now_iso, _write_json
from app.services.state_service import get_state_dir, get_state_file

STATE_DIR = get_state_dir()
RELATIONSHIPS_PATH = get_state_file("relationships.json")
RELATIONSHIPS_LOCK = threading.Lock()
CELEBRITY_PROFILES_PATH = Path(__file__).resolve().parents[4] / "content" / "profiles" / "celebrity_profiles.json"


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_relationship_store() -> dict[str, Any]:
    if not RELATIONSHIPS_PATH.exists():
        return {"version": 1, "items": []}
    try:
        return json.loads(RELATIONSHIPS_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": 1, "items": []}


def _write_relationship_store(payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    RELATIONSHIPS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _load_celebrities() -> list[dict[str, Any]]:
    try:
        return json.loads(CELEBRITY_PROFILES_PATH.read_text())
    except FileNotFoundError:
        return []


def _entry_from_record(record: dict[str, Any]) -> RelationshipEntry:
    return RelationshipEntry(**record)


def _summary_from_payload(
    payload: dict[str, Any],
    relationship_added: bool = False,
) -> DirectoryProfileSummary:
    return DirectoryProfileSummary(
        profile_id=str(payload["profile_id"]),
        kind=str(payload["kind"]),
        display_name=str(payload["display_name"]),
        headline=payload.get("headline"),
        biography=payload.get("biography"),
        tags=list(payload.get("tags") or []),
        profile=BirthProfile(**payload["profile"]),
        is_discoverable=bool(payload.get("is_discoverable", True)),
        relationship_added=relationship_added,
        source_label=payload.get("source_label"),
    )


def _build_search_text(payload: dict[str, Any]) -> str:
    parts = [
        payload.get("display_name") or "",
        payload.get("headline") or "",
        payload.get("biography") or "",
        " ".join(payload.get("tags") or []),
        (payload.get("profile") or {}).get("birth_city") or "",
        (payload.get("profile") or {}).get("birth_country") or "",
    ]
    return " ".join(str(part).strip().lower() for part in parts if part)


class RelationshipService:
    @staticmethod
    def set_public_chart_profile(user_id: str, request: PublicChartProfileRequest) -> PublicChartProfileResponse:
        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = next((user for user in users_store["users"] if user["id"] == user_id), None)
            if not user_record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

            user_record["public_chart_profile"] = {
                "profile_id": f"user:{user_id}",
                "kind": "user",
                "display_name": (request.profile.name or user_record.get("display_name") or user_record["email"]).strip(),
                "headline": (request.headline or "").strip() or "Ark member",
                "biography": (request.biography or user_record.get("bio") or "").strip() or None,
                "tags": ["friend", "ark-member"],
                "profile": request.profile.model_dump(),
                "is_discoverable": bool(request.is_discoverable),
                "source_label": "Ark member",
                "updated_at": _now_iso(),
            }
            user_record["updated_at"] = _now_iso()
            _write_json(USERS_PATH, users_store)

        return PublicChartProfileResponse(public_profile=_summary_from_payload(user_record["public_chart_profile"]))

    @staticmethod
    def get_public_chart_profile(user_id: str) -> PublicChartProfileResponse:
        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = next((user for user in users_store["users"] if user["id"] == user_id), None)
            if not user_record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
            payload = user_record.get("public_chart_profile")
        return PublicChartProfileResponse(public_profile=_summary_from_payload(payload) if payload else None)

    @staticmethod
    def search_directory(user_id: str, query: str = "", limit: int = 20) -> DirectoryProfileListResponse:
        normalized_query = query.strip().lower()
        safe_limit = max(1, min(int(limit), 50))

        with STORE_LOCK:
            users_store = _load_users_store()
        with RELATIONSHIPS_LOCK:
            relationship_store = _read_relationship_store()

        current_relationships = {
            entry.get("profile_id")
            for entry in relationship_store["items"]
            if entry.get("user_id") == user_id
        }

        directory: list[dict[str, Any]] = []
        for celebrity in _load_celebrities():
            directory.append({
                "profile_id": celebrity["id"],
                "kind": "celebrity",
                "display_name": celebrity["display_name"],
                "headline": celebrity.get("headline"),
                "biography": celebrity.get("biography"),
                "tags": celebrity.get("tags") or [],
                "profile": celebrity["profile"],
                "is_discoverable": True,
                "source_label": celebrity.get("source_label") or "Celebrity directory",
            })

        for user_record in users_store["users"]:
            if user_record["id"] == user_id:
                continue
            payload = user_record.get("public_chart_profile")
            if not payload or not payload.get("is_discoverable", False):
                continue
            directory.append(payload)

        if normalized_query:
            directory = [payload for payload in directory if normalized_query in _build_search_text(payload)]

        directory.sort(key=lambda payload: (payload.get("kind") != "user", payload.get("display_name", "").lower()))
        items = [
            _summary_from_payload(payload, relationship_added=payload["profile_id"] in current_relationships)
            for payload in directory[:safe_limit]
        ]
        return DirectoryProfileListResponse(items=items, total=len(directory))

    @staticmethod
    def list_relationships(user_id: str) -> RelationshipListResponse:
        with RELATIONSHIPS_LOCK:
            relationship_store = _read_relationship_store()
            items = [entry for entry in relationship_store["items"] if entry.get("user_id") == user_id]
        items.sort(key=lambda entry: entry.get("added_at", ""), reverse=True)
        return RelationshipListResponse(items=[_entry_from_record(entry) for entry in items])

    @staticmethod
    def add_relationship(user_id: str, request: AddRelationshipRequest) -> RelationshipListResponse:
        profile_id = request.profile_id.strip()
        if not profile_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A profile_id is required.")

        directory_response = RelationshipService.search_directory(user_id=user_id, query="", limit=200)
        payload = next((item for item in directory_response.items if item.profile_id == profile_id), None)
        if not payload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory profile not found.")

        record = {
            "relationship_id": str(uuid4()),
            "user_id": user_id,
            "profile_id": payload.profile_id,
            "kind": payload.kind,
            "display_name": payload.display_name,
            "headline": payload.headline,
            "biography": payload.biography,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "tags": payload.tags,
            "profile": payload.profile.model_dump(),
            "source_label": payload.source_label,
        }

        with RELATIONSHIPS_LOCK:
            store = _read_relationship_store()
            existing = next(
                (
                    entry
                    for entry in store["items"]
                    if entry.get("user_id") == user_id and entry.get("profile_id") == profile_id
                ),
                None,
            )
            if existing:
                return RelationshipService.list_relationships(user_id)
            store["items"].append(record)
            _write_relationship_store(store)

        return RelationshipService.list_relationships(user_id)

    @staticmethod
    def remove_relationship(user_id: str, profile_id: str) -> RelationshipListResponse:
        with RELATIONSHIPS_LOCK:
            store = _read_relationship_store()
            store["items"] = [
                entry
                for entry in store["items"]
                if not (entry.get("user_id") == user_id and entry.get("profile_id") == profile_id)
            ]
            _write_relationship_store(store)
        return RelationshipService.list_relationships(user_id)
