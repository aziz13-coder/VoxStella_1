import base64
import hashlib
import hmac
import importlib.util
import json
import sys
import time
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


def test_verify_license_token_rejects_forced_legacy_offline_activation(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()
    lic = "FAKE-LEGACY-OFFLINE"
    device = "fake-device"
    monkeypatch.setattr(
        backend_licensing,
        "LEGACY_OFFLINE_ACTIVATION_REVALIDATION_LIST",
        (
            {
                "lic_hash": hashlib.sha256(lic.lower().encode("utf-8")).hexdigest(),
                "device_hash": hashlib.sha256(device.lower().encode("utf-8")).hexdigest(),
            },
        ),
    )

    payload = {
        "lic": lic,
        "plan": "perpetual",
        "kind": "perpetual",
        "device": device,
        "iat": 1_700_000_000,
        "verified_at": 1_700_000_000,
        "offline_capable": True,
    }

    try:
        backend_licensing.verify_license_token(_sign_token(signing_key, payload))
    except backend_licensing.LicenseError as exc:
        assert "refresh required" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected forced legacy offline activation to be rejected")


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


def test_verify_license_token_rejects_future_issue_and_verification_times(monkeypatch):
    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PUBLIC_KEY_B64",
        base64.b64encode(bytes(signing_key.verify_key)).decode("ascii"),
    )
    backend_licensing._get_verify_key.cache_clear()
    now = int(time.time())
    future = now + backend_licensing.LICENSE_CLOCK_SKEW_SECONDS + 1

    future_issue_payload = {
        "lic": "LIC-FUTURE-IAT",
        "plan": "perpetual",
        "kind": "perpetual",
        "device": "device-1",
        "iat": future,
        "verified_at": now,
        "offline_capable": True,
    }
    future_verification_payload = {
        **future_issue_payload,
        "lic": "LIC-FUTURE-VERIFIED",
        "iat": now,
        "verified_at": future,
    }

    for payload in (future_issue_payload, future_verification_payload):
        try:
            backend_licensing.verify_license_token(_sign_token(signing_key, payload))
        except backend_licensing.LicenseError as exc:
            assert "future" in str(exc).lower()
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected future-dated token to be rejected")


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

    now = int(time.time())
    payload = {
        "token_type": "local_license_session",
        "lic": f"local-session:{'a' * 64}",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": now - 1,
        "exp": now + 120,
        "verified_at": now - 10,
        "next_verify_at": now + 120,
        "entitlement_exp": now + 120,
        "offline_capable": False,
    }

    claims = backend_licensing.verify_license_token(_sign_local_session(secret, payload))

    assert claims["token_type"] == "local_license_session"
    assert claims["device"] == "device-1"


def test_verify_license_token_accepts_stale_subscription_local_session_within_durable_expiry(monkeypatch):
    secret = b"x" * 32
    monkeypatch.setenv("VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64", base64.b64encode(secret).decode("ascii"))
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "device-1")
    backend_licensing._get_local_session_secret.cache_clear()
    now = int(time.time())
    payload = {
        "token_type": "local_license_session",
        "lic": f"local-session:{'c' * 64}",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": now,
        "exp": now + 120,
        "verified_at": now - 605_000,
        "next_verify_at": now - 200,
        "entitlement_exp": now + 180,
        "requires_entitlement_refresh": True,
        "offline_capable": False,
    }

    claims = backend_licensing.verify_license_token(_sign_local_session(secret, payload))

    assert claims["next_verify_at"] < now
    assert claims["exp"] <= claims["entitlement_exp"]


def test_verify_license_token_rejects_tampered_local_entitlement_expiry(monkeypatch):
    secret = b"x" * 32
    monkeypatch.setenv("VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64", base64.b64encode(secret).decode("ascii"))
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "device-1")
    backend_licensing._get_local_session_secret.cache_clear()
    now = int(time.time())
    payload = {
        "token_type": "local_license_session",
        "lic": f"local-session:{'d' * 64}",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": now,
        "exp": now + 120,
        "verified_at": now - 605_000,
        "next_verify_at": now - 200,
        "entitlement_exp": now + 180,
        "requires_entitlement_refresh": True,
        "offline_capable": False,
    }
    signed_token = _sign_local_session(secret, payload)
    signature_b64, _ = signed_token.split(".", 1)
    tampered_payload = {**payload, "entitlement_exp": now + 86_400}
    tampered_body = json.dumps(tampered_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    tampered_token = f"{signature_b64}.{base64.b64encode(tampered_body).decode('ascii')}"

    try:
        backend_licensing.verify_license_token(tampered_token)
    except backend_licensing.LicenseError as exc:
        assert "signature" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected an entitlement-expiry claim change to invalidate the session signature")


def test_verify_license_token_rejects_overlong_or_boundary_crossing_local_sessions(monkeypatch):
    secret = b"x" * 32
    monkeypatch.setenv("VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64", base64.b64encode(secret).decode("ascii"))
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "device-1")
    backend_licensing._get_local_session_secret.cache_clear()
    now = int(time.time())
    base_payload = {
        "token_type": "local_license_session",
        "lic": f"local-session:{'b' * 64}",
        "plan": "pro",
        "kind": "subscription",
        "device": "device-1",
        "iat": now,
        "verified_at": now,
        "next_verify_at": now + 600,
        "entitlement_exp": now + 600,
        "offline_capable": False,
    }

    overlong = {
        **base_payload,
        "exp": now + backend_licensing.MAX_LOCAL_SESSION_TTL_SECONDS + 1,
    }
    crossing_boundary = {
        **base_payload,
        "exp": now + 120,
        "entitlement_exp": now + 60,
    }
    missing_grace_boundary = {
        **base_payload,
        "verified_at": now - 60,
        "next_verify_at": now + 60,
        "exp": now + 120,
    }
    missing_grace_boundary.pop("entitlement_exp")

    for payload, expected in (
        (overlong, "maximum"),
        (crossing_boundary, "boundary"),
        (missing_grace_boundary, "boundary"),
    ):
        try:
            backend_licensing.verify_license_token(_sign_local_session(secret, payload))
        except backend_licensing.LicenseError as exc:
            assert expected in str(exc).lower()
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected invalid local session to be rejected")


def test_verify_license_token_rejects_pending_paypal_local_session(monkeypatch):
    secret = b"x" * 32
    monkeypatch.setenv("VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64", base64.b64encode(secret).decode("ascii"))
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", "device-1")
    backend_licensing._get_verify_key.cache_clear()
    backend_licensing._get_local_session_secret.cache_clear()

    payload = {
        "token_type": "local_license_session",
        "lic": "paypal-pending:I-FAKE-SUB",
        "plan": "premium-desktop-monthly",
        "kind": "subscription",
        "device": "device-1",
        "iat": 1_700_000_000,
        "exp": 4_100_000_000,
        "verified_at": 1_700_000_000,
        "next_verify_at": 4_100_000_000,
        "offline_capable": False,
        "paypal_pending_verification": True,
    }

    try:
        backend_licensing.verify_license_token(_sign_local_session(secret, payload))
    except backend_licensing.LicenseError as exc:
        assert "pending paypal" in str(exc).lower()
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected pending PayPal local session to be rejected")


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
