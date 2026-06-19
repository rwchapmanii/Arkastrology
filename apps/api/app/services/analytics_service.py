from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.models.analytics import AnalyticsEventResponse
from app.services.state_service import get_state_dir, get_state_file

STATE_DIR = get_state_dir()
ANALYTICS_PATH = get_state_file("analytics_events.json")
ANALYTICS_LOCK = threading.Lock()
MAX_STORED_EVENTS = 20_000


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_store() -> dict[str, Any]:
    if not ANALYTICS_PATH.exists():
        return {"version": 1, "events": []}
    try:
        return json.loads(ANALYTICS_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": 1, "events": []}


def _write_store(payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    ANALYTICS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value[:20]]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested in list(value.items())[:40]:
            sanitized[str(key)[:80]] = _sanitize_value(nested)
        return sanitized
    return str(value)[:500]


class AnalyticsService:
    @staticmethod
    def record_event(event_name: str, context: Optional[dict[str, Any]] = None, user_id: Optional[str] = None) -> AnalyticsEventResponse:
        timestamp = _now_iso()
        normalized_event_name = event_name.strip().lower().replace(" ", "_")[:80] or "unknown_event"
        event_id = str(uuid4())
        event_record = {
            "event_id": event_id,
            "event_name": normalized_event_name,
            "user_id": user_id,
            "recorded_at": timestamp,
            "context": _sanitize_value(context or {}),
        }

        with ANALYTICS_LOCK:
            store = _read_store()
            events = store.get("events", [])
            events.append(event_record)
            store["events"] = events[-MAX_STORED_EVENTS:]
            _write_store(store)

        return AnalyticsEventResponse(event_id=event_id, recorded_at=timestamp)
