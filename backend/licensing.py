"""
License verification helpers for the horary backend.

All high-value endpoints must validate an Ed25519-signed token that is issued
by the external licensing server.  The public key (base64) is injected via the
LICENSE_PUBLIC_KEY_B64 environment variable at runtime.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
from functools import lru_cache
from typing import Optional

from nacl import exceptions as nacl_exceptions
from nacl import signing

logger = logging.getLogger(__name__)

LICENSE_BYPASS_ENV = "LICENSE_BYPASS"
DEV_LICENSE_BYPASS_ENV = "ALLOW_DEV_LICENSE_BYPASS"
PUBLIC_KEY_ENV = "LICENSE_PUBLIC_KEY_B64"
LOCAL_SESSION_SECRET_ENV = "VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64"
LOCAL_DEVICE_ID_ENV = "VOX_STELLA_DEVICE_ID"
LEGACY_PERPETUAL_PLAN_KEYWORDS = ("perpetual", "lifetime", "forever")
PERPETUAL_LICENSE_KINDS = {"perpetual", "lifetime", "forever"}
RENEWABLE_LICENSE_KINDS = {"subscription", "renewable", "term"}
LOCAL_SESSION_TOKEN_TYPE = "local_license_session"


class LicenseError(Exception):
    """Raised when a license token cannot be validated."""


class LicenseConfigError(RuntimeError):
    """Raised when required licensing configuration is missing."""


def _normalize_plan_name(plan: str | None) -> str:
    return (plan or "").strip().lower()


def _normalize_license_kind(kind: str | None) -> str | None:
    normalized = (kind or "").strip().lower()
    if not normalized:
        return None
    if normalized in RENEWABLE_LICENSE_KINDS:
        return "subscription"
    if normalized in PERPETUAL_LICENSE_KINDS:
        return "perpetual"
    return None


def _is_perpetual_plan(plan: str | None) -> bool:
    normalized = _normalize_plan_name(plan)
    return any(keyword in normalized for keyword in LEGACY_PERPETUAL_PLAN_KEYWORDS)


def _license_requires_entitlement_refresh(payload: dict) -> bool:
    explicit = payload.get("requires_entitlement_refresh")
    if isinstance(explicit, bool):
        return explicit

    kind = _normalize_license_kind(payload.get("kind"))
    if kind is not None:
        return kind != "perpetual"

    return not _is_perpetual_plan(payload.get("plan"))


@lru_cache()
def _get_verify_key() -> signing.VerifyKey:
    """Return the Ed25519 VerifyKey configured for this runtime."""
    b64_key = os.getenv(PUBLIC_KEY_ENV, "").strip()
    if not b64_key:
        raise LicenseConfigError(
            f"{PUBLIC_KEY_ENV} is not configured – unable to validate licenses"
        )
    try:
        key_bytes = base64.b64decode(b64_key)
        return signing.VerifyKey(key_bytes)
    except Exception as exc:  # pragma: no cover - defensive
        raise LicenseConfigError("Invalid LICENSE_PUBLIC_KEY_B64 value") from exc


@lru_cache()
def _get_local_session_secret() -> bytes | None:
    secret_b64 = os.getenv(LOCAL_SESSION_SECRET_ENV, "").strip()
    if not secret_b64:
        return None
    try:
        secret = base64.b64decode(secret_b64)
    except Exception as exc:  # pragma: no cover - defensive
        raise LicenseConfigError("Invalid local license session secret") from exc
    if len(secret) < 32:
        raise LicenseConfigError("Local license session secret is too short")
    return secret


def _get_expected_device_id() -> str | None:
    value = os.getenv(LOCAL_DEVICE_ID_ENV, "").strip()
    return value or None


def _enforce_device_binding(payload: dict) -> None:
    expected_device_id = _get_expected_device_id()
    if not expected_device_id:
        return
    actual_device_id = str(payload.get("device") or "").strip()
    if not actual_device_id or actual_device_id != expected_device_id:
        raise LicenseError("license token device mismatch")


def _verify_local_session_token(signature: bytes, payload_bytes: bytes, payload: dict) -> dict:
    secret = _get_local_session_secret()
    if not secret:
        raise LicenseConfigError("Local license session secret is not configured")

    expected_signature = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise LicenseError("invalid local license session signature")

    token_type = str(payload.get("token_type") or "").strip().lower()
    if token_type != LOCAL_SESSION_TOKEN_TYPE:
        raise LicenseError("invalid local license session payload")

    for field in ("lic", "plan", "device"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise LicenseError(f"invalid local license session claim: {field}")

    iat = payload.get("iat")
    exp = payload.get("exp")
    try:
        iat_int = int(iat)
        exp_int = int(exp)
    except (TypeError, ValueError):
        raise LicenseError("invalid local license session timing")
    if iat_int <= 0 or exp_int <= iat_int:
        raise LicenseError("invalid local license session timing")

    from time import time

    now = int(time())
    if exp_int <= now:
        raise LicenseError("local license session expired")

    _enforce_device_binding(payload)
    return payload


def should_bypass_license() -> bool:
    """Return True only when bypass is explicitly enabled in non-packaged dev."""

    def _is_truthy(value: str | None) -> bool:
        return (value or "").strip().lower() in {"1", "true", "yes"}

    def _is_packaged_runtime() -> bool:
        if getattr(sys, "frozen", False):
            return True
        return _is_truthy(os.getenv("APP_IS_PACKAGED"))

    bypass_requested = _is_truthy(os.getenv(DEV_LICENSE_BYPASS_ENV)) or _is_truthy(
        os.getenv(LICENSE_BYPASS_ENV)
    )
    if not bypass_requested:
        return False

    env_name = (os.getenv("FLASK_ENV") or os.getenv("VOX_STELLA_ENV") or "").strip().lower()
    is_dev_env = env_name in {"dev", "development", "local", "test", "testing"}
    if not env_name:
        # Preserve existing local-dev workflow when env is unset.
        is_dev_env = not _is_packaged_runtime()

    if _is_packaged_runtime() or not is_dev_env:
        logger.warning("License bypass requested but ignored outside development runtime.")
        return False
    return True


def verify_license_token(token: str) -> dict:
    """
    Validate a bearer token and return its payload.

    Tokens are compact strings in the form base64(signature).base64(payload).
    The payload must decode to JSON and include at minimum `lic`, `plan`,
    `device`, `iat`, and `verified_at`. Newer tokens also carry explicit
    entitlement policy claims such as `kind` and
    `requires_entitlement_refresh`; legacy tokens fall back to plan-name
    heuristics for compatibility. Renewable licenses must carry a valid future
    `next_verify_at`; perpetual licenses do not require periodic entitlement
    refresh.
    """
    if not token:
        raise LicenseError("missing license token")

    try:
        sig_b64, body_b64 = token.split(".", 1)
    except ValueError:
        raise LicenseError("malformed license token")

    try:
        signature = base64.b64decode(sig_b64)
        payload_bytes = base64.b64decode(body_b64)
    except Exception as exc:
        raise LicenseError("invalid license token encoding") from exc

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise LicenseError("invalid license payload") from exc
    if not isinstance(payload, dict):
        raise LicenseError("invalid license payload")

    token_type = str(payload.get("token_type") or "").strip().lower()
    if token_type == LOCAL_SESSION_TOKEN_TYPE:
        return _verify_local_session_token(signature, payload_bytes, payload)

    verify_key = _get_verify_key()
    try:
        verify_key.verify(payload_bytes, signature)
    except nacl_exceptions.BadSignatureError:
        raise LicenseError("invalid license signature")

    for field in ("lic", "plan", "device"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise LicenseError(f"invalid license claim: {field}")

    kind = payload.get("kind")
    if kind is not None and _normalize_license_kind(kind) is None:
        raise LicenseError("invalid license claim: kind")

    refresh_flag = payload.get("requires_entitlement_refresh")
    if refresh_flag is not None and not isinstance(refresh_flag, bool):
        raise LicenseError("invalid license claim: requires_entitlement_refresh")

    offline_capable = payload.get("offline_capable")
    if offline_capable is not None and not isinstance(offline_capable, bool):
        raise LicenseError("invalid license claim: offline_capable")

    iat = payload.get("iat")
    try:
        iat_int = int(iat)
    except (TypeError, ValueError):
        raise LicenseError("invalid license issue time")
    if iat_int <= 0:
        raise LicenseError("invalid license issue time")

    verified_at = payload.get("verified_at")
    try:
        verified_at_int = int(verified_at)
    except (TypeError, ValueError):
        raise LicenseError("license entitlement refresh required")
    if verified_at_int <= 0:
        raise LicenseError("license entitlement refresh required")

    next_verify_at_int = None
    if _license_requires_entitlement_refresh(payload):
        next_verify_at = payload.get("next_verify_at")
        try:
            next_verify_at_int = int(next_verify_at)
        except (TypeError, ValueError):
            raise LicenseError("license entitlement refresh required")
        if next_verify_at_int <= 0 or next_verify_at_int < verified_at_int:
            raise LicenseError("license entitlement refresh required")

    exp = payload.get("exp")
    exp_int = None
    from time import time

    now = int(time())
    if exp is not None:
        try:
            exp_int = int(exp)
        except (TypeError, ValueError):
            raise LicenseError("invalid license expiry")
        else:
            if exp_int <= now:
                raise LicenseError("license token expired")
    if next_verify_at_int is not None and next_verify_at_int <= now and exp_int is None:
        raise LicenseError("license entitlement refresh required")

    _enforce_device_binding(payload)
    return payload


def extract_bearer_token(headers: dict[str, str]) -> Optional[str]:
    """Extract Bearer <token> from standard Authorization headers."""
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
