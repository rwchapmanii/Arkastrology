from __future__ import annotations

import json
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional
from urllib import error, request

from app.services.env_service import load_local_env
from app.services.state_service import get_state_dir, get_state_file

load_local_env()

STATE_DIR = get_state_dir()
OUTBOX_PATH = get_state_file("email_outbox.json")
OUTBOX_LOCK = threading.Lock()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _mail_mode() -> str:
    configured = os.getenv("EMAIL_DELIVERY_MODE", "auto").strip().lower()
    if configured in {"smtp", "debug", "disabled", "api"}:
        return configured
    if _email_provider() and os.getenv("EMAIL_FROM_ADDRESS"):
        return "api"
    if os.getenv("SMTP_HOST") and os.getenv("EMAIL_FROM_ADDRESS"):
        return "smtp"
    return "debug"


def _email_provider() -> str:
    configured = (os.getenv("EMAIL_PROVIDER") or "").strip().lower()
    if configured:
        return configured
    if (os.getenv("RESEND_API_KEY") or "").strip():
        return "resend"
    return ""


def _from_header() -> str:
    address = (os.getenv("EMAIL_FROM_ADDRESS") or "no-reply@theark.local").strip()
    name = (os.getenv("EMAIL_FROM_NAME") or "The Ark").strip()
    return f"{name} <{address}>" if name else address


def _support_address() -> str:
    return (os.getenv("EMAIL_SUPPORT_ADDRESS") or os.getenv("EMAIL_FROM_ADDRESS") or "support@theark.local").strip()


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_outbox() -> dict[str, Any]:
    if not OUTBOX_PATH.exists():
        return {"version": 1, "messages": []}
    try:
        return json.loads(OUTBOX_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": 1, "messages": []}


def _write_outbox(payload: dict[str, Any]) -> None:
    _ensure_state_dir()
    OUTBOX_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _compose(kind: str, recipient_email: str, display_name: Optional[str], token: str, expires_at: str) -> dict[str, str]:
    recipient_name = (display_name or recipient_email.split("@", 1)[0] or "there").strip()
    support_address = _support_address()

    if kind == "verification":
        subject = "Verify your The Ark email"
        text = (
            f"Hi {recipient_name},\n\n"
            f"Use this verification code to confirm your email address:\n\n{token}\n\n"
            f"This code expires at {expires_at}. If you did not create this account, you can ignore this message.\n\n"
            f"Need help? Reply to {support_address}."
        )
        html = (
            f"<p>Hi {recipient_name},</p>"
            f"<p>Use this verification code to confirm your email address:</p>"
            f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;\">{token}</p>"
            f"<p>This code expires at {expires_at}. If you did not create this account, you can ignore this message.</p>"
            f"<p>Need help? Reply to {support_address}.</p>"
        )
        return {"subject": subject, "text": text, "html": html}

    subject = "Reset your The Ark password"
    text = (
        f"Hi {recipient_name},\n\n"
        f"Use this password-reset code to set a new password:\n\n{token}\n\n"
        f"This code expires at {expires_at}. If you did not request a password reset, you can ignore this message.\n\n"
        f"Need help? Reply to {support_address}."
    )
    html = (
        f"<p>Hi {recipient_name},</p>"
        f"<p>Use this password-reset code to set a new password:</p>"
        f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;\">{token}</p>"
        f"<p>This code expires at {expires_at}. If you did not request a password reset, you can ignore this message.</p>"
        f"<p>Need help? Reply to {support_address}.</p>"
    )
    return {"subject": subject, "text": text, "html": html}


def _record_debug_message(entry: dict[str, Any]) -> None:
    with OUTBOX_LOCK:
        payload = _read_outbox()
        payload["messages"].append(entry)
        payload["messages"] = payload["messages"][-200:]
        _write_outbox(payload)


def _smtp_send(recipient_email: str, composed: dict[str, str]) -> None:
    host = (os.getenv("SMTP_HOST") or "").strip()
    port = int((os.getenv("SMTP_PORT") or "587").strip())
    username = (os.getenv("SMTP_USERNAME") or "").strip() or None
    password = os.getenv("SMTP_PASSWORD") or None
    use_ssl = _env_flag("SMTP_USE_SSL", default=False)
    use_tls = _env_flag("SMTP_USE_TLS", default=not use_ssl)

    if not host:
        raise RuntimeError("SMTP_HOST is not configured.")

    message = EmailMessage()
    message["Subject"] = composed["subject"]
    message["From"] = _from_header()
    message["To"] = recipient_email
    message.set_content(composed["text"])
    message.add_alternative(composed["html"], subtype="html")

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as smtp:
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.ehlo()
        if use_tls:
            context = ssl.create_default_context()
            smtp.starttls(context=context)
            smtp.ehlo()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def _resend_send(recipient_email: str, composed: dict[str, str]) -> None:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured.")

    payload = {
        "from": _from_header(),
        "to": [recipient_email],
        "subject": composed["subject"],
        "html": composed["html"],
        "text": composed["text"],
    }
    raw = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "https://api.resend.com/emails",
        data=raw,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "the-ark-api/1.0",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
            message = parsed.get("message") or parsed.get("name") or body
        except json.JSONDecodeError:
            message = body
        raise RuntimeError(f"Resend API error ({exc.code}): {message}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Resend API request failed: {exc.reason}") from exc


def _api_send(recipient_email: str, composed: dict[str, str]) -> None:
    provider = _email_provider()
    if provider == "resend":
        _resend_send(recipient_email, composed)
        return
    raise RuntimeError(f"Unsupported EMAIL_PROVIDER: {provider or 'unset'}")


class EmailDeliveryService:
    @staticmethod
    def deliver_token_email(kind: str, recipient_email: str, display_name: Optional[str], token: str, expires_at: str) -> dict[str, Any]:
        mode = _mail_mode()
        composed = _compose(kind, recipient_email, display_name, token, expires_at)
        expose_tokens = _env_flag("EMAIL_DEBUG_EXPOSE_TOKENS", default=(mode not in {"smtp", "api"}))

        if mode == "disabled":
            return {
                "delivery_mode": "disabled",
                "delivery_target": recipient_email,
                "prototype_token": token if expose_tokens else None,
                "notes": ["Email delivery is disabled; no outbound email was sent."],
            }

        if mode == "smtp":
            try:
                _smtp_send(recipient_email, composed)
                return {
                    "delivery_mode": "smtp",
                    "delivery_target": recipient_email,
                    "prototype_token": None,
                    "notes": [f"A transactional email was sent to {recipient_email}."],
                }
            except Exception as exc:
                debug_entry = {
                    "kind": kind,
                    "recipient_email": recipient_email,
                    "subject": composed["subject"],
                    "text": composed["text"],
                    "html": composed["html"],
                    "token": token,
                    "expires_at": expires_at,
                    "failure": str(exc),
                }
                _record_debug_message(debug_entry)
                return {
                    "delivery_mode": "debug-fallback",
                    "delivery_target": recipient_email,
                    "prototype_token": token if expose_tokens else None,
                    "notes": [
                        "SMTP delivery failed, so the message was captured in the local debug outbox instead.",
                        str(exc),
                    ],
                }

        if mode == "api":
            try:
                _api_send(recipient_email, composed)
                return {
                    "delivery_mode": "api",
                    "delivery_target": recipient_email,
                    "prototype_token": None,
                    "notes": [f"A transactional email was sent to {recipient_email} via {_email_provider()}."],
                }
            except Exception as exc:
                debug_entry = {
                    "kind": kind,
                    "recipient_email": recipient_email,
                    "subject": composed["subject"],
                    "text": composed["text"],
                    "html": composed["html"],
                    "token": token,
                    "expires_at": expires_at,
                    "failure": str(exc),
                    "provider": _email_provider(),
                }
                _record_debug_message(debug_entry)
                return {
                    "delivery_mode": "debug-fallback",
                    "delivery_target": recipient_email,
                    "prototype_token": token if expose_tokens else None,
                    "notes": [
                        f"{(_email_provider() or 'Email API').capitalize()} delivery failed, so the message was captured in the local debug outbox instead.",
                        str(exc),
                    ],
                }

        debug_entry = {
            "kind": kind,
            "recipient_email": recipient_email,
            "subject": composed["subject"],
            "text": composed["text"],
            "html": composed["html"],
            "token": token,
            "expires_at": expires_at,
        }
        _record_debug_message(debug_entry)
        return {
            "delivery_mode": "debug",
            "delivery_target": recipient_email,
            "prototype_token": token if expose_tokens else None,
            "notes": ["Email was captured in the local debug outbox."],
        }
