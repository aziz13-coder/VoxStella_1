import importlib.util
from pathlib import Path
from uuid import uuid4


APP_PATH = Path(__file__).with_name("app.py")


def _load_module():
    module_name = f"licensing_server_token_policy_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_subscription_payload_requires_refresh_and_expires():
    module = _load_module()
    now = 1_700_000_000
    paid_through = now + (30 * 24 * 3600)
    payload = module._build_signed_payload(
        subject="user@example.com",
        license_key="LIC-123",
        plan="pro",
        license_kind="subscription",
        device_id="device-1",
        now=now,
        current_period_end=paid_through,
    )

    assert payload["kind"] == "subscription"
    assert payload["requires_entitlement_refresh"] is True
    assert payload["offline_capable"] is False
    assert payload["next_verify_at"] == now + (7 * 24 * 3600)
    assert payload["exp"] == now + (7 * 24 * 3600) + (48 * 3600)


def test_subscription_payload_cannot_outlive_paid_through_plus_grace():
    module = _load_module()
    now = 1_700_000_000
    paid_through = now + 3600
    entitlement_deadline = paid_through + module.SUBS_GRACE_SECONDS
    payload = module._build_signed_payload(
        subject="user@example.com",
        license_key="LIC-123",
        plan="pro",
        license_kind="subscription",
        device_id="device-1",
        now=now,
        current_period_end=paid_through,
    )

    assert payload["next_verify_at"] == entitlement_deadline
    assert payload["exp"] == entitlement_deadline


def test_subscription_is_expired_at_the_exact_paid_through_grace_boundary():
    module = _load_module()
    paid_through = 1_700_000_000
    boundary = paid_through + module.SUBS_GRACE_SECONDS
    state = module._evaluate_license_state(
        {
            "active": 1,
            "license_key": "LIC-123",
            "kind": "subscription",
            "status": "active",
            "current_period_end": paid_through,
        },
        boundary,
    )

    assert state["allowed"] is False
    assert state["reason"] == "subscription-expired"


def test_subscription_payload_requires_authoritative_paid_through_boundary():
    module = _load_module()

    try:
        module._build_signed_payload(
            subject="user@example.com",
            license_key="LIC-123",
            plan="pro",
            license_kind="subscription",
            device_id="device-1",
            now=1_700_000_000,
        )
    except RuntimeError as exc:
        assert "paid-through" in str(exc)
    else:
        raise AssertionError("Expected subscription token construction to require paid-through")


def test_subscription_payload_still_expires_when_refresh_cadence_is_disabled(monkeypatch):
    monkeypatch.setenv("LICENSE_VERIFY_INTERVAL_SECONDS", "0")
    module = _load_module()
    now = 1_700_000_000
    paid_through = now + (30 * 24 * 3600)
    payload = module._build_signed_payload(
        subject="user@example.com",
        license_key="LIC-123",
        plan="pro",
        license_kind="subscription",
        device_id="device-1",
        now=now,
        current_period_end=paid_through,
    )

    assert payload["requires_entitlement_refresh"] is False
    assert "next_verify_at" not in payload
    assert payload["exp"] == paid_through + module.SUBS_GRACE_SECONDS


def test_perpetual_payload_is_offline_capable_without_refresh_boundary():
    module = _load_module()
    payload = module._build_signed_payload(
        subject="user@example.com",
        license_key="LIC-123",
        plan="pro",
        license_kind="perpetual",
        device_id="device-1",
        now=1_700_000_000,
    )

    assert payload["kind"] == "perpetual"
    assert payload["requires_entitlement_refresh"] is False
    assert payload["offline_capable"] is True
    assert "next_verify_at" not in payload
    assert "exp" not in payload


def test_perpetual_payload_can_opt_into_refresh_without_reclassifying_kind(monkeypatch):
    monkeypatch.setenv("LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS", str(21 * 24 * 3600))
    monkeypatch.setenv("LICENSE_PERPETUAL_GRACE_SECONDS", str(72 * 3600))
    module = _load_module()
    now = 1_700_000_000
    payload = module._build_signed_payload(
        subject="user@example.com",
        license_key="LIC-123",
        plan="pro",
        license_kind="perpetual",
        device_id="device-1",
        now=now,
    )

    assert payload["kind"] == "perpetual"
    assert payload["requires_entitlement_refresh"] is True
    assert payload["offline_capable"] is False
    assert payload["next_verify_at"] == now + (21 * 24 * 3600)
    assert payload["exp"] == now + (21 * 24 * 3600) + (72 * 3600)
