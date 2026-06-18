import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.env_service import load_local_env

load_local_env()

app = FastAPI(
    title="The Ark API",
    version="0.1.0",
    description="Internal backend for The Ark's explainable astrology readings.",
)


def _allowed_origins() -> list[str]:
    configured = (os.getenv("ALLOWED_ORIGINS") or "").strip()
    if not configured:
        return [
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://localhost:19006",
            "http://127.0.0.1:19006",
        ]
    if configured == "*":
        return ["*"]
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


allowed_origins = _allowed_origins()
allow_all_origins = allowed_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=(os.getenv("ALLOWED_ORIGIN_REGEX") or "").strip() or None,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
