from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.services.state_service import get_state_dir, get_state_file

STATE_DIR = get_state_dir()
RATE_LIMIT_PATH = get_state_file("rate_limits.json")
RATE_LIMIT_LOCK = threading.Lock()


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_store() -> dict[str, Any]:
    if not RATE_LIMIT_PATH.exists():
        return {"version": 1, "buckets": {}}
    try:
        return json.loads(RATE_LIMIT_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": 1, "buckets": {}}


def _write_store(payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    RATE_LIMIT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


class RateLimitService:
    @staticmethod
    def enforce(scope: str, key: str, limit: int, window_seconds: int, detail: str) -> None:
        if not key.strip() or limit <= 0 or window_seconds <= 0:
            return

        bucket_key = f"{scope}:{key.strip().lower()}"
        now_ts = _now_ts()
        cutoff = now_ts - window_seconds

        with RATE_LIMIT_LOCK:
            store = _read_store()
            buckets = store.setdefault("buckets", {})
            bucket = [int(timestamp) for timestamp in buckets.get(bucket_key, []) if int(timestamp) > cutoff]
            if len(bucket) >= limit:
                retry_after = max(1, window_seconds - (now_ts - min(bucket)))
                buckets[bucket_key] = bucket
                _write_store(store)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=detail,
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now_ts)
            buckets[bucket_key] = bucket
            _write_store(store)
