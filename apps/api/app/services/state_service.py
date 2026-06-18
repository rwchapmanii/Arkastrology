from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from app.services.env_service import load_local_env

load_local_env()


@lru_cache(maxsize=1)
def get_state_dir() -> Path:
    configured = (os.getenv("ARK_STATE_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[2] / "state"


def get_state_file(filename: str) -> Path:
    return get_state_dir() / filename
