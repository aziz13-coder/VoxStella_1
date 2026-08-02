import base64
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app  # noqa: E402
import licensing  # noqa: E402
import mcp_api  # noqa: E402


def _local_session(secret: bytes, device: str, *, expired: bool = False) -> str:
    now = int(time.time())
    payload = {
        "token_type": "local_license_session",
        "lic": "local-session:test",
        "plan": "perpetual",
        "kind": "perpetual",
        "device": device,
        "iat": now - (120 if expired else 1),
        "exp": now - 1 if expired else now + 120,
        "verified_at": now - 60,
        "requires_entitlement_refresh": False,
        "offline_capable": True,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret, body, hashlib.sha256).digest()
    return f"{base64.b64encode(signature).decode()}.{base64.b64encode(body).decode()}"


def _secure_runtime(monkeypatch):
    secret = b"mcp-test-session-secret-that-is-at-least-32-bytes"
    device = "mcp-test-device-identity"
    monkeypatch.setenv("APP_IS_PACKAGED", "1")
    monkeypatch.setenv("ALLOW_DEV_LICENSE_BYPASS", "0")
    monkeypatch.setenv("LICENSE_BYPASS", "0")
    monkeypatch.setenv(
        "VOX_STELLA_LOCAL_LICENSE_SESSION_SECRET_B64",
        base64.b64encode(secret).decode("ascii"),
    )
    monkeypatch.setenv("VOX_STELLA_DEVICE_ID", device)
    licensing._get_local_session_secret.cache_clear()
    return secret, device


def test_mcp_routes_are_not_public(monkeypatch):
    _secure_runtime(monkeypatch)
    client = backend_app.app.test_client()

    capabilities = client.get("/api/mcp/capabilities")
    chart = client.post("/api/mcp/chart", json={})

    assert capabilities.status_code == 402
    assert chart.status_code == 402
    assert capabilities.get_json()["error"] == "license_required"


def test_mcp_capabilities_accept_fresh_device_bound_local_session(monkeypatch):
    secret, device = _secure_runtime(monkeypatch)
    client = backend_app.app.test_client()

    response = client.get(
        "/api/mcp/capabilities",
        headers={"X-License-Token": _local_session(secret, device)},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["license_required"] is True
    serialized = json.dumps(payload)
    assert "mcp-test-session-secret" not in serialized
    assert "local-session:test" not in serialized


def test_mcp_routes_reject_expired_local_session(monkeypatch):
    secret, device = _secure_runtime(monkeypatch)
    client = backend_app.app.test_client()

    response = client.get(
        "/api/mcp/capabilities",
        headers={"X-License-Token": _local_session(secret, device, expired=True)},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "license_invalid"


def test_mcp_chart_validation_is_returned_as_bounded_client_error(monkeypatch):
    secret, device = _secure_runtime(monkeypatch)
    client = backend_app.app.test_client()

    response = client.post(
        "/api/mcp/chart",
        headers={"X-License-Token": _local_session(secret, device)},
        json={
            "datetime": "2026-08-01T14:30:00+03:00",
            "timezone": "Asia/Jerusalem",
            "latitude": 100,
            "longitude": 35.235,
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "invalid_request"
    assert "latitude" in payload["detail"]


def test_mcp_request_body_size_is_bounded(monkeypatch):
    secret, device = _secure_runtime(monkeypatch)
    client = backend_app.app.test_client()

    response = client.post(
        "/api/mcp/chart",
        headers={"X-License-Token": _local_session(secret, device)},
        json={"location": "x" * (65 * 1024)},
    )

    assert response.status_code == 400
    assert "size limit" in response.get_json()["detail"]


def test_mcp_synastry_is_license_gated_and_uses_explicit_adapter(monkeypatch):
    secret, device = _secure_runtime(monkeypatch)
    captured = {}

    def fake_synastry(payload):
        captured.update(payload)
        return {"schema_version": "voxstella.astrology.v1", "engine_id": "memo"}

    monkeypatch.setattr(mcp_api, "calculate_synastry", fake_synastry)
    client = backend_app.app.test_client()
    body = {"chart_a": {"label": "A"}, "chart_b": {"label": "B"}}

    denied = client.post("/api/mcp/synastry", json=body)
    allowed = client.post(
        "/api/mcp/synastry",
        headers={"X-License-Token": _local_session(secret, device)},
        json=body,
    )

    assert denied.status_code == 402
    assert allowed.status_code == 200
    assert allowed.get_json()["data"]["engine_id"] == "memo"
    assert captured == body
