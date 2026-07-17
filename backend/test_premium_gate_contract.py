import importlib.util
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent


def _load_app_module(module_name):
    app_path = BACKEND_DIR / "app.py"
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    spec = importlib.util.spec_from_file_location(module_name, app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _clear_license_bypass(monkeypatch):
    for key in ("ALLOW_DEV_LICENSE_BYPASS", "LICENSE_BYPASS", "APP_IS_PACKAGED"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("VOX_STELLA_ENV", "production")


@pytest.mark.parametrize(
    ("path", "payload"),
    (
        (
            "/api/astro-clock/chinese-astrology/bazi",
            {"date": "2000-01-01", "location": "Greenwich, UK"},
        ),
        (
            "/api/astro-clock/chinese-astrology/compatibility",
            {"person_a": {"date": "2000-01-01"}, "person_b": {"date": "2001-01-01"}},
        ),
        (
            "/api/astro-clock/chinese-astrology/iching-oracle",
            {"question": "Will this be gated?"},
        ),
    ),
)
def test_chinese_astrology_routes_require_license_when_bypass_is_off(monkeypatch, path, payload):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_chinese_premium_gate_test")

    with module.app.test_request_context(
        path,
        method="POST",
        json=payload,
    ):
        response, status = module.enforce_license_guard()

    assert status == 402
    assert response.get_json()["error"] == "license_required"


def test_directional_3d_route_requires_license_when_bypass_is_off(monkeypatch):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_directional_3d_premium_gate_test")

    with module.app.test_request_context(
        "/api/astro-clock/directional-3d?datetime=2026-05-13T12:00:00Z&location=Greenwich%2C%20UK&latitude=51.4769&longitude=-0.0005",
        method="GET",
    ):
        response, status = module.enforce_license_guard()

    assert status == 402
    assert response.get_json()["error"] == "license_required"


def test_public_astro_clock_manual_and_realtime_contexts_stay_free(monkeypatch):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_realtime_premium_gate_test")

    with module.app.test_request_context(
        "/api/astro-clock/dashboard?mode=manual&datetime=2026-05-13T12:00:00&location=Greenwich%2C%20UK",
        method="GET",
    ):
        assert module.enforce_license_guard() is None

    with module.app.test_request_context(
        "/api/astro-clock/dashboard?mode=realtime&location=Greenwich%2C%20UK",
        method="GET",
    ):
        assert module.enforce_license_guard() is None


@pytest.mark.parametrize(
    "path",
    (
        "/api/astro-clock/current-premium",
        "/api/astro-clock/dashboard-private",
        "/api/astro-clock/planetary-hours-export",
        "/api/astro-clock/receptions-admin",
        "/api/astro-clock/compass-secret",
    ),
)
def test_public_astro_clock_names_do_not_exempt_prefix_collisions(monkeypatch, path):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_public_prefix_collision_test")

    with module.app.test_request_context(path, method="GET"):
        response, status = module.enforce_license_guard()

    assert status == 402
    assert response.get_json()["error"] == "license_required"


@pytest.mark.parametrize(
    "path",
    (
        "/api/astro-clock/stream-ticket",
        "/api/astro-clock/stream-private",
        "/api/astro-clock/transits/window/stream-export",
        "/api/astro-clock/election/suggest/stream-admin",
    ),
)
def test_stream_ticket_targets_reject_mint_endpoint_and_prefix_collisions(monkeypatch, path):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_stream_ticket_target_test")

    with pytest.raises(ValueError, match="unsupported stream path"):
        module._normalize_stream_target(path)


def test_stream_ticket_cannot_outlive_originating_session(monkeypatch):
    _clear_license_bypass(monkeypatch)
    module = _load_app_module("backend_app_stream_ticket_expiry_test")
    clock = {"now": 1_700_000_000.0}
    monkeypatch.setattr(module.time, "time", lambda: clock["now"])
    module._stream_ticket_cache.clear()

    target = module._normalize_stream_target(
        "/api/astro-clock/transits/window/stream?b=2&a=1"
    )
    claims = {"lic": "local-session:test", "exp": clock["now"] + 30}
    ticket = module._mint_stream_ticket(claims, target)

    assert target.endswith("?a=1&b=2")
    assert module._stream_ticket_cache[ticket]["exp"] == claims["exp"]

    clock["now"] = claims["exp"]
    assert module._consume_stream_ticket(ticket, target) is None
    with pytest.raises(ValueError, match="expired"):
        module._mint_stream_ticket(claims, target)
