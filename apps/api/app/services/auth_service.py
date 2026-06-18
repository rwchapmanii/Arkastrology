from __future__ import annotations

import base64
import json
import secrets
import threading
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.services.state_service import get_state_dir, get_state_file
from app.models.auth import (
    AccountPreferences,
    AccountProfile,
    AccountProfileResponse,
    AccountProfileUpdateRequest,
    AccountSummary,
    AuthRequest,
    AuthSessionResponse,
    EmailRequest,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    SessionStatusResponse,
    TokenConfirmRequest,
    TokenDeliveryResponse,
    VerificationConfirmResponse,
)
from app.services.email_delivery_service import EmailDeliveryService

STATE_DIR = get_state_dir()
USERS_PATH = get_state_file("users.json")
SESSIONS_PATH = get_state_file("sessions.json")
SESSION_TTL_DAYS = 30
TOKEN_TTL_MINUTES = 30
HASH_ROUNDS = 310_000
STORE_LOCK = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _future_iso(minutes: int) -> str:
    return (_now() + timedelta(minutes=minutes)).isoformat()


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _default_preferences() -> dict[str, bool]:
    return {
        "include_jungian_default": False,
        "include_red_book_prompts_default": False,
    }


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default_payload: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default_payload

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default_payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _load_users_store() -> dict[str, Any]:
    return _read_json(USERS_PATH, {"version": 1, "users": []})


def _load_sessions_store() -> dict[str, Any]:
    return _read_json(SESSIONS_PATH, {"version": 1, "sessions": []})


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _salt() -> str:
    return base64.b64encode(secrets.token_bytes(16)).decode("utf-8")


def _hash_password(password: str, salt_value: str) -> str:
    digest = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        base64.b64decode(salt_value.encode("utf-8")),
        HASH_ROUNDS,
    )
    return base64.b64encode(digest).decode("utf-8")


def _verify_password(password: str, salt_value: str, stored_hash: str) -> bool:
    return secrets.compare_digest(_hash_password(password, salt_value), stored_hash)


def _display_name_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    tokens = [token for token in local.replace(".", " ").replace("_", " ").split() if token]
    return " ".join(token.capitalize() for token in tokens) or email


def _session_record(user_id: str) -> dict[str, str]:
    created_at = _now_iso()
    expires_at = (_now() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
    return {
        "token": secrets.token_urlsafe(48),
        "user_id": user_id,
        "created_at": created_at,
        "last_seen_at": created_at,
        "expires_at": expires_at,
    }


def _token_record() -> dict[str, str]:
    return {
        "token": f"{secrets.randbelow(1_000_000):06d}",
        "requested_at": _now_iso(),
        "expires_at": (_now() + timedelta(minutes=TOKEN_TTL_MINUTES)).isoformat(),
    }


def _generic_delivery_response(status_value: str, email: str, notes: list[str]) -> TokenDeliveryResponse:
    return TokenDeliveryResponse(
        status=status_value,
        token_expires_at=_future_iso(TOKEN_TTL_MINUTES),
        delivery_mode="suppressed",
        delivery_target=email,
        prototype_token=None,
        notes=notes,
    )


def _account_summary(user_record: dict[str, Any]) -> AccountSummary:
    return AccountSummary(
        user_id=user_record["id"],
        email=user_record["email"],
        display_name=user_record.get("display_name"),
        preferences=AccountPreferences(**user_record.get("preferences", _default_preferences())),
        email_verified=bool(user_record.get("email_verified", False)),
        timezone_name=user_record.get("timezone_name"),
        bio=user_record.get("bio"),
    )


def _account_profile(user_record: dict[str, Any]) -> AccountProfile:
    return AccountProfile(
        display_name=user_record.get("display_name"),
        timezone_name=user_record.get("timezone_name"),
        bio=user_record.get("bio"),
        email_verified=bool(user_record.get("email_verified", False)),
    )


def _session_response(user_record: dict[str, Any], session_record: dict[str, str], notes: Optional[list[str]] = None) -> AuthSessionResponse:
    return AuthSessionResponse(
        session_token=session_record["token"],
        session_expires_at=session_record["expires_at"],
        account=_account_summary(user_record),
        notes=notes or [],
    )


def _session_status_response(user_record: dict[str, Any], session_record: dict[str, str]) -> SessionStatusResponse:
    return SessionStatusResponse(
        session_expires_at=session_record["expires_at"],
        account=_account_summary(user_record),
    )


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header.")
    return token.strip()


def _find_user_by_email(users_store: dict[str, Any], email: str) -> Optional[dict[str, Any]]:
    return next((user for user in users_store["users"] if user["email"] == email), None)


def _validated_token(record: Optional[dict[str, str]], token: str) -> bool:
    if not record:
        return False
    if record.get("token") != token:
        return False
    expires_at = record.get("expires_at")
    if not expires_at:
        return False
    return _parse_iso(expires_at) > _now()


class AuthService:
    @staticmethod
    def get_user_id_for_session(authorization: Optional[str]) -> str:
        user_record, _ = AuthService._require_session(authorization)
        return str(user_record["id"])

    @staticmethod
    def get_optional_user_id_for_session(authorization: Optional[str]) -> Optional[str]:
        if not authorization:
            return None
        return AuthService.get_user_id_for_session(authorization)

    @staticmethod
    def register(request: AuthRequest) -> AuthSessionResponse:
        email = _normalize_email(request.email)
        if not email or "@" not in email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid email is required.")

        with STORE_LOCK:
            users_store = _load_users_store()
            existing = _find_user_by_email(users_store, email)
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")

            salt_value = _salt()
            now = _now_iso()
            verification_record = _token_record()
            user_record = {
                "id": str(uuid4()),
                "email": email,
                "display_name": (request.display_name or "").strip() or _display_name_from_email(email),
                "password_salt": salt_value,
                "password_hash": _hash_password(request.password, salt_value),
                "preferences": _default_preferences(),
                "email_verified": False,
                "timezone_name": None,
                "bio": None,
                "verification_token": verification_record,
                "password_reset_token": None,
                "created_at": now,
                "updated_at": now,
            }
            users_store["users"].append(user_record)
            _write_json(USERS_PATH, users_store)

            sessions_store = _load_sessions_store()
            session_record = _session_record(user_record["id"])
            sessions_store["sessions"].append(session_record)
            _write_json(SESSIONS_PATH, sessions_store)

        delivery = EmailDeliveryService.deliver_token_email(
            kind="verification",
            recipient_email=email,
            display_name=user_record.get("display_name"),
            token=verification_record["token"],
            expires_at=verification_record["expires_at"],
        )
        notes = [
            "Account created.",
            *delivery["notes"],
        ]
        if delivery.get("prototype_token"):
            notes.append("Debug token exposure is enabled for local development.")
        return _session_response(user_record, session_record, notes)

    @staticmethod
    def login(request: AuthRequest) -> AuthSessionResponse:
        email = _normalize_email(request.email)

        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = _find_user_by_email(users_store, email)
            if not user_record or not _verify_password(request.password, user_record["password_salt"], user_record["password_hash"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

            sessions_store = _load_sessions_store()
            session_record = _session_record(user_record["id"])
            sessions_store["sessions"].append(session_record)
            _write_json(SESSIONS_PATH, sessions_store)

        notes = [] if user_record.get("email_verified") else ["Email is not yet verified."]
        return _session_response(user_record, session_record, notes)

    @staticmethod
    def get_session(authorization: Optional[str]) -> SessionStatusResponse:
        user_record, session_record = AuthService._require_session(authorization)
        return _session_status_response(user_record, session_record)

    @staticmethod
    def get_preferences(authorization: Optional[str]) -> PreferencesResponse:
        user_record, _ = AuthService._require_session(authorization)
        return PreferencesResponse(preferences=AccountPreferences(**user_record.get("preferences", _default_preferences())))

    @staticmethod
    def update_preferences(request: PreferencesUpdateRequest, authorization: Optional[str]) -> PreferencesResponse:
        token = _extract_bearer_token(authorization)
        with STORE_LOCK:
            users_store = _load_users_store()
            sessions_store = _load_sessions_store()
            session_record = next((session for session in sessions_store["sessions"] if session["token"] == token), None)
            if not session_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found.")
            if _parse_iso(session_record["expires_at"]) <= _now():
                sessions_store["sessions"] = [session for session in sessions_store["sessions"] if session["token"] != token]
                _write_json(SESSIONS_PATH, sessions_store)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired.")

            user_record = next((user for user in users_store["users"] if user["id"] == session_record["user_id"]), None)
            if not user_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found for session.")

            preferences = {**_default_preferences(), **user_record.get("preferences", {})}
            if request.include_jungian_default is not None:
                preferences["include_jungian_default"] = request.include_jungian_default
            if request.include_red_book_prompts_default is not None:
                preferences["include_red_book_prompts_default"] = request.include_red_book_prompts_default
            user_record["preferences"] = preferences
            user_record["updated_at"] = _now_iso()
            session_record["last_seen_at"] = _now_iso()

            _write_json(USERS_PATH, users_store)
            _write_json(SESSIONS_PATH, sessions_store)

        return PreferencesResponse(preferences=AccountPreferences(**preferences))

    @staticmethod
    def get_profile(authorization: Optional[str]) -> AccountProfileResponse:
        user_record, _ = AuthService._require_session(authorization)
        return AccountProfileResponse(profile=_account_profile(user_record))

    @staticmethod
    def update_profile(request: AccountProfileUpdateRequest, authorization: Optional[str]) -> AccountProfileResponse:
        token = _extract_bearer_token(authorization)
        with STORE_LOCK:
            users_store = _load_users_store()
            sessions_store = _load_sessions_store()
            session_record = next((session for session in sessions_store["sessions"] if session["token"] == token), None)
            if not session_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found.")
            user_record = next((user for user in users_store["users"] if user["id"] == session_record["user_id"]), None)
            if not user_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found for session.")

            if request.display_name is not None:
                user_record["display_name"] = request.display_name.strip() or None
            if request.timezone_name is not None:
                user_record["timezone_name"] = request.timezone_name.strip() or None
            if request.bio is not None:
                user_record["bio"] = request.bio.strip() or None
            user_record["updated_at"] = _now_iso()
            session_record["last_seen_at"] = _now_iso()
            _write_json(USERS_PATH, users_store)
            _write_json(SESSIONS_PATH, sessions_store)

        return AccountProfileResponse(profile=_account_profile(user_record))

    @staticmethod
    def request_email_verification(request: EmailRequest) -> TokenDeliveryResponse:
        email = _normalize_email(request.email)
        if not email or "@" not in email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid email is required.")

        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = _find_user_by_email(users_store, email)
            if not user_record:
                return _generic_delivery_response(
                    status_value="verification_requested",
                    email=email,
                    notes=["If an account exists for that address, a verification email has been queued."],
                )
            verification_record = _token_record()
            user_record["verification_token"] = verification_record
            user_record["updated_at"] = _now_iso()
            _write_json(USERS_PATH, users_store)

        delivery = EmailDeliveryService.deliver_token_email(
            kind="verification",
            recipient_email=email,
            display_name=user_record.get("display_name"),
            token=verification_record["token"],
            expires_at=verification_record["expires_at"],
        )
        return TokenDeliveryResponse(
            status="verification_requested",
            token_expires_at=verification_record["expires_at"],
            delivery_mode=delivery["delivery_mode"],
            delivery_target=delivery["delivery_target"],
            prototype_token=delivery.get("prototype_token"),
            notes=delivery["notes"],
        )

    @staticmethod
    def confirm_email_verification(request: TokenConfirmRequest) -> VerificationConfirmResponse:
        email = _normalize_email(request.email)
        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = _find_user_by_email(users_store, email)
            if not user_record or not _validated_token(user_record.get("verification_token"), request.token.strip()):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Verification token is invalid or expired.")
            user_record["email_verified"] = True
            user_record["verification_token"] = None
            user_record["updated_at"] = _now_iso()
            _write_json(USERS_PATH, users_store)

        return VerificationConfirmResponse(
            status="email_verified",
            email_verified=True,
            notes=["Email verification completed."],
        )

    @staticmethod
    def request_password_reset(request: EmailRequest) -> TokenDeliveryResponse:
        email = _normalize_email(request.email)
        if not email or "@" not in email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid email is required.")

        with STORE_LOCK:
            users_store = _load_users_store()
            user_record = _find_user_by_email(users_store, email)
            if not user_record:
                return _generic_delivery_response(
                    status_value="password_reset_requested",
                    email=email,
                    notes=["If an account exists for that address, a password reset email has been queued."],
                )
            reset_record = _token_record()
            user_record["password_reset_token"] = reset_record
            user_record["updated_at"] = _now_iso()
            _write_json(USERS_PATH, users_store)

        delivery = EmailDeliveryService.deliver_token_email(
            kind="password_reset",
            recipient_email=email,
            display_name=user_record.get("display_name"),
            token=reset_record["token"],
            expires_at=reset_record["expires_at"],
        )
        return TokenDeliveryResponse(
            status="password_reset_requested",
            token_expires_at=reset_record["expires_at"],
            delivery_mode=delivery["delivery_mode"],
            delivery_target=delivery["delivery_target"],
            prototype_token=delivery.get("prototype_token"),
            notes=delivery["notes"],
        )

    @staticmethod
    def confirm_password_reset(request: PasswordResetConfirmRequest) -> PasswordResetConfirmResponse:
        email = _normalize_email(request.email)
        with STORE_LOCK:
            users_store = _load_users_store()
            sessions_store = _load_sessions_store()
            user_record = _find_user_by_email(users_store, email)
            if not user_record or not _validated_token(user_record.get("password_reset_token"), request.token.strip()):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password-reset token is invalid or expired.")
            salt_value = _salt()
            user_record["password_salt"] = salt_value
            user_record["password_hash"] = _hash_password(request.new_password, salt_value)
            user_record["password_reset_token"] = None
            user_record["updated_at"] = _now_iso()
            sessions_store["sessions"] = [session for session in sessions_store["sessions"] if session["user_id"] != user_record["id"]]
            _write_json(USERS_PATH, users_store)
            _write_json(SESSIONS_PATH, sessions_store)

        return PasswordResetConfirmResponse(
            status="password_reset_complete",
            notes=["Password updated. Existing sessions were revoked for safety."],
        )

    @staticmethod
    def logout(authorization: Optional[str]) -> LogoutResponse:
        token = _extract_bearer_token(authorization)
        with STORE_LOCK:
            sessions_store = _load_sessions_store()
            sessions_store["sessions"] = [session for session in sessions_store["sessions"] if session["token"] != token]
            _write_json(SESSIONS_PATH, sessions_store)
        return LogoutResponse()

    @staticmethod
    def _require_session(authorization: Optional[str]) -> tuple[dict[str, Any], dict[str, str]]:
        token = _extract_bearer_token(authorization)
        with STORE_LOCK:
            sessions_store = _load_sessions_store()
            users_store = _load_users_store()
            session_record = next((session for session in sessions_store["sessions"] if session["token"] == token), None)
            if not session_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found.")

            if _parse_iso(session_record["expires_at"]) <= _now():
                sessions_store["sessions"] = [session for session in sessions_store["sessions"] if session["token"] != token]
                _write_json(SESSIONS_PATH, sessions_store)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired.")

            user_record = next((user for user in users_store["users"] if user["id"] == session_record["user_id"]), None)
            if not user_record:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found for session.")

            session_record["last_seen_at"] = _now_iso()
            _write_json(SESSIONS_PATH, sessions_store)
            return user_record, session_record
