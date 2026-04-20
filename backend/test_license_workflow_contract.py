import base64
import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path

from nacl.signing import SigningKey


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import licensing as backend_licensing  # noqa: E402


def _sign_token(signing_key: SigningKey, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = signing_key.sign(body).signature
    return (
        f"{base64.b64encode(signature).decode('ascii')}."
        f"{base64.b64encode(body).decode('ascii')}"
    )


def _sign_local_session(secret: bytes, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret, body, hashlib.sha256).digest()
    return (
        f"{base64.b64encode(signature).decode('ascii')}."
        f"{base64.b64encode(body).decode('ascii')}"
    )


def test_verify_license_token_accepts_fresh_entitlement(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-123",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": True,
        "next_verify_at": 4_100_000_000,
    }

    claims = backend_licensing.verify_license_token(_sign_token(signing_key, payload))

    assert claims["lic"] == "LIC-123"
    assert claims["next_verify_at"] == payload["next_verify_at"]


def test_verify_license_token_rejects_stale_entitlement(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-123",
        "plan": "lifetime",
        "kind": "subscription",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": True,
        "next_verify_at": 1,
    }

    try:
        backend_licensing.verify_license_token(_sign_token(signing_key, payload))
    except backend_licensing.LicenseError as exc:
        assert "refresh required" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected stale entitlement token to be rejected")


def test_verify_license_token_allows_stale_entitlement_until_expiry(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-123",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": True,
        "next_verify_at": 1_700_000_100,
        "exp": 4_100_000_000,
    }

    claims = backend_licensing.verify_license_token(_sign_token(signing_key, payload))

    assert claims["lic"] == "LIC-123"
    assert claims["exp"] == payload["exp"]


def test_verify_license_token_accepts_perpetual_with_offline_claims(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-PERP-1",
        "plan": "pro",
        "kind": "perpetual",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": False,
        "offline_capable": True,
    }

    claims = backend_licensing.verify_license_token(_sign_token(signing_key, payload))

    assert claims["kind"] == "perpetual"
    assert claims["offline_capable"] is True


def test_verify_license_token_accepts_perpetual_refresh_claims_until_expiry(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-PERP-2",
        "plan": "pro",
        "kind": "perpetual",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": True,
        "offline_capable": False,
        "next_verify_at": 1_700_000_100,
        "exp": 4_100_000_000,
    }

    claims = backend_licensing.verify_license_token(_sign_token(signing_key, payload))

    assert claims["kind"] == "perpetual"
    assert claims["requires_entitlement_refresh"] is True


def test_verify_license_token_accepts_legacy_lifetime_without_kind(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-LIFE-1",
        "plan": "lifetime",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
    }

    claims = backend_licensing.verify_license_token(_sign_token(signing_key, payload))

    assert claims["plan"] == "lifetime"


def test_verify_license_token_rejects_invalid_kind_claim(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()

    payload = {
        "lic": "LIC-BAD-1",
        "plan": "pro",
        "kind": "unknown",
        "device": "device-1",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
    }

    try:
        backend_licensing.verify_license_token(_sign_token(signing_key, payload))
    except backend_licensing.LicenseError as exc:
        assert "kind" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected invalid kind claim to be rejected")


def test_verify_license_token_rejects_device_mismatch_when_runtime_device_is_known(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "expected-device")
    backend_licensing._get_verify_key.cache_clear()
    backend_licensing._get_local_session_secret.cache_clear()

    payload = {
        "lic": "LIC-DEVICE-1",
        "plan": "pro",
        "kind": "subscription",
        "device": "other-device",
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "requires_entitlement_refresh": True,
        "next_verify_at": 4_100_000_000,
    }

    try:
        backend_licensing.verify_license_token(_sign_token(signing_key, payload))
    except backend_licensing.LicenseError as exc:
        assert "device mismatch" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected device-mismatched token to be rejected")


def test_verify_license_token_accepts_local_renderer_session(monkeypatch):
    secret = b"x" * 32
    monkeypatch.setenv("VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64", base64.b64encode(secret).decode("ascii"))
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "device-1")
    backend_licensing._get_verify_key.cache_clear()
    backend_licensing._get_local_session_secret.cache_clear()

    payload = {
        "token_type": "local_license_session",
        "lic": "LIC-LOCAL-1",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": 1_700_000_000,
        "exp": 4_100_000_000,
        "verified_at": 1_700_000_000,
        "next_verify_at": 1_700_000_100,
        "offline_capable": False,
    }

    claims = backend_licensing.verify_license_token(_sign_local_session(secret, payload))

    assert claims["token_type"] == "local_license_session"
    assert claims["device"] == "device-1"


def test_health_endpoint_returns_structured_200():
    app_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("backend_app_health_test", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    client = module.app.test_client()
    response = client.get("/api/health?skip_network=true")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] in {"healthy", "degraded", "unhealthy"}
    assert isinstance(payload.get("services"), dict)
