from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.models.history import (
    ReadingHistoryChartTypeFacet,
    ReadingHistoryDetailResponse,
    ReadingHistoryItem,
    ReadingHistoryListResponse,
    ReadingHistoryTagFacet,
    ReadingHistoryUpdateRequest,
)
from app.services.state_service import get_state_dir, get_state_file

STATE_DIR = get_state_dir()
HISTORY_PATH = get_state_file("reading_history.json")
HISTORY_LOCK = threading.Lock()
MAX_HISTORY_ITEMS_PER_USER = 100
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 50


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_store() -> dict[str, Any]:
    if not HISTORY_PATH.exists():
        return {"version": 1, "items": []}
    try:
        return json.loads(HISTORY_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": 1, "items": []}


def _write_store(payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    HISTORY_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _item_response(item: dict[str, Any]) -> ReadingHistoryItem:
    return ReadingHistoryItem(**item)


def _subject_label(payload: dict[str, Any]) -> str:
    chart_type = payload.get("chart_type")
    if chart_type == "synastry":
        primary = ((payload.get("primary_profile") or {}).get("name") or "Person A").strip()
        secondary = ((payload.get("secondary_profile") or {}).get("name") or "Person B").strip()
        return f"{primary} + {secondary}"
    profile = payload.get("profile") or {}
    return (profile.get("name") or "Natal subject").strip()


def _normalize_chart_type(chart_type: Optional[str]) -> Optional[str]:
    if not chart_type:
        return None
    normalized = chart_type.strip().lower()
    return normalized if normalized in {"natal", "synastry"} else None


def _normalize_tag(tag: Optional[str]) -> Optional[str]:
    if not tag:
        return None
    normalized = tag.strip().lower()
    return normalized or None


def _matches_query(item: dict[str, Any], query: Optional[str], chart_type: Optional[str], tag: Optional[str]) -> bool:
    normalized_chart = _normalize_chart_type(chart_type)
    normalized_tag = _normalize_tag(tag)

    if normalized_chart and str(item.get("chart_type", "")).lower() != normalized_chart:
        return False

    item_tags = [str(entry).strip() for entry in item.get("tags", []) if str(entry).strip()]
    if normalized_tag and normalized_tag not in {entry.lower() for entry in item_tags}:
        return False

    if not query:
        return True

    haystack = " ".join([
        str(item.get("headline", "")),
        str(item.get("subject_label", "")),
        " ".join(item_tags),
        str(item.get("chart_type", "")),
        str(item.get("status", "")),
    ]).lower()
    return query.lower() in haystack


def _build_tag_facets(items: list[dict[str, Any]]) -> list[ReadingHistoryTagFacet]:
    counts = Counter()
    for item in items:
        for tag in item.get("tags", []):
            normalized = str(tag).strip()
            if normalized:
                counts[normalized] += 1
    return [ReadingHistoryTagFacet(tag=tag, count=count) for tag, count in counts.most_common(12)]


def _build_chart_type_facets(items: list[dict[str, Any]]) -> list[ReadingHistoryChartTypeFacet]:
    counts = Counter(str(item.get("chart_type", "unknown")) for item in items)
    ordered = sorted(counts.items(), key=lambda pair: pair[0])
    return [ReadingHistoryChartTypeFacet(chart_type=chart_type, count=count) for chart_type, count in ordered]


class ReadingHistoryService:
    @staticmethod
    def record_reading(user_id: str, reading_payload: dict[str, Any]) -> ReadingHistoryItem:
        timestamp = datetime.now(timezone.utc).isoformat()
        item = {
            "user_id": user_id,
            "id": str(uuid4()),
            "chart_type": reading_payload.get("chart_type", "unknown"),
            "status": reading_payload.get("status", "unknown"),
            "headline": (reading_payload.get("reading") or {}).get("headline", "Untitled reading"),
            "subject_label": _subject_label(reading_payload),
            "created_at": timestamp,
            "updated_at": timestamp,
            "favorite": False,
            "tags": [],
            "reading_payload": reading_payload,
        }

        with HISTORY_LOCK:
            store = _read_store()
            items = [entry for entry in store["items"] if entry.get("user_id") != user_id]
            user_items = [entry for entry in store["items"] if entry.get("user_id") == user_id]
            user_items.insert(0, item)
            trimmed = user_items[:MAX_HISTORY_ITEMS_PER_USER]
            store["items"] = items + trimmed
            _write_store(store)

        return _item_response(item)

    @staticmethod
    def list_readings(
        user_id: str,
        query: Optional[str] = None,
        favorite_only: bool = False,
        chart_type: Optional[str] = None,
        tag: Optional[str] = None,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> ReadingHistoryListResponse:
        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(int(limit), MAX_PAGE_LIMIT))

        with HISTORY_LOCK:
            store = _read_store()
            items = [entry for entry in store["items"] if entry.get("user_id") == user_id]

        items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        filtered = [
            item
            for item in items
            if _matches_query(item, query, chart_type, tag) and (not favorite_only or bool(item.get("favorite", False)))
        ]

        page_items = filtered[safe_offset:safe_offset + safe_limit]
        total = len(filtered)
        next_offset = safe_offset + safe_limit if safe_offset + safe_limit < total else None

        return ReadingHistoryListResponse(
            items=[_item_response(item) for item in page_items],
            total=total,
            offset=safe_offset,
            limit=safe_limit,
            has_more=next_offset is not None,
            next_offset=next_offset,
            favorites_count=sum(1 for item in filtered if bool(item.get("favorite", False))),
            available_tags=_build_tag_facets(filtered),
            chart_type_counts=_build_chart_type_facets(filtered),
        )

    @staticmethod
    def get_reading(user_id: str, reading_id: str) -> ReadingHistoryDetailResponse:
        with HISTORY_LOCK:
            store = _read_store()
            item = next((entry for entry in store["items"] if entry.get("user_id") == user_id and entry.get("id") == reading_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading history item not found.")
        return ReadingHistoryDetailResponse(item=_item_response(item))

    @staticmethod
    def update_reading(user_id: str, reading_id: str, request: ReadingHistoryUpdateRequest) -> ReadingHistoryDetailResponse:
        with HISTORY_LOCK:
            store = _read_store()
            item = next((entry for entry in store["items"] if entry.get("user_id") == user_id and entry.get("id") == reading_id), None)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading history item not found.")
            if request.favorite is not None:
                item["favorite"] = bool(request.favorite)
            if request.tags is not None:
                cleaned_tags = []
                seen = set()
                for tag in request.tags:
                    normalized = str(tag).strip()
                    lowered = normalized.lower()
                    if normalized and lowered not in seen:
                        cleaned_tags.append(normalized)
                        seen.add(lowered)
                item["tags"] = cleaned_tags[:12]
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            _write_store(store)
        return ReadingHistoryDetailResponse(item=_item_response(item))
