import base64
import importlib.util
import io
import re
import sqlite3
import threading
from pathlib import Path
from urllib.error import HTTPError
from uuid import uuid4

from fastapi.testclient import TestClient
from nacl.signing import SigningKey


APP_PATH = Path(__file__).with_name("app.py")
MINT_PATH = Path(__file__).with_name("scripts") / "mint_keys.py"
RUNNER_PATH = Path(__file__).with_name("run-licensing-server.bat")


def _load_module(monkeypatch, tmp_path, **environment):
    module_name = f"licensing_server_hardening_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader

    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PRIVATE_KEY_B64",
        base64.b64encode(bytes(signing_key)).decode("ascii"),
    )
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-client-secret")
    for name, value in environment.items():
        monkeypatch.setenv(name, str(value))

    spec.loader.exec_module(module)
    module.DB_PATH = tmp_path / "licenses.db"
    module.init_db()
    return module


def _insert_perpetual_entitlement(
    module,
    *,
    devices=("device-1",),
    license_key="TEST-LICENSE-1",
):
    now = int(module.time.time())
    with sqlite3.connect(module.DB_PATH) as conn:
        conn.execute(
            """
            insert into licenses
              (license_key, plan, max_devices, active, issued_at, kind, status)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (license_key, "pro", len(devices), 1, now, "perpetual", "active"),
        )
        for device in devices:
            conn.execute(
                """
                insert into activations
                  (license_key, device_id, activated_at, last_activity)
                values (?, ?, ?, ?)
                """,
                (license_key, device, now, now),
            )
    return now


def _signed_refresh_token(
    module,
    *,
    device="device-1",
    license_key="TEST-LICENSE-1",
    issued_at: int,
    expires_at: int | None,
):
    payload = {
        "sub": "buyer@example.com",
        "lic": license_key,
        "plan": "pro",
        "kind": "perpetual",
        "device": device,
        "iat": issued_at,
        "verified_at": issued_at,
        "requires_entitlement_refresh": False,
        "offline_capable": True,
    }
    if expires_at is not None:
        payload["exp"] = expires_at
    return module.sign_payload(payload)


def _activation_exists(module, license_key: str, device_id: str) -> bool:
    with sqlite3.connect(module.DB_PATH) as conn:
        row = conn.execute(
            "select 1 from activations where license_key=? and device_id=?",
            (license_key, device_id),
        ).fetchone()
    return row is not None


def test_public_deactivation_rejects_raw_key_and_device_without_token(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    _insert_perpetual_entitlement(module)

    response = TestClient(module.app).post(
        "/license/deactivate",
        json={"key": "TEST-LICENSE-1", "deviceId": "device-1"},
    )

    assert response.status_code == 422
    assert _activation_exists(module, "TEST-LICENSE-1", "device-1")


def test_public_deactivation_rejects_tampered_token_even_with_valid_key(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    _insert_perpetual_entitlement(module)

    response = TestClient(module.app).post(
        "/license/deactivate",
        json={
            "token": "invalid.signature",
            "key": "TEST-LICENSE-1",
            "deviceId": "device-1",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid-token"
    assert _activation_exists(module, "TEST-LICENSE-1", "device-1")


def test_public_deactivation_requires_exact_signed_device_binding(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module, devices=("device-1", "device-2"))
    token = _signed_refresh_token(
        module,
        device="device-1",
        issued_at=now,
        expires_at=now + 3600,
    )

    response = TestClient(module.app).post(
        "/license/deactivate",
        json={"token": token, "deviceId": "device-2"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "device-mismatch"
    assert _activation_exists(module, "TEST-LICENSE-1", "device-1")
    assert _activation_exists(module, "TEST-LICENSE-1", "device-2")


def test_public_deactivation_rejects_request_key_from_another_license(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module)
    _insert_perpetual_entitlement(
        module,
        devices=("device-1",),
        license_key="OTHER-LICENSE-2",
    )
    token = _signed_refresh_token(
        module,
        issued_at=now,
        expires_at=now + 3600,
    )

    response = TestClient(module.app).post(
        "/license/deactivate",
        json={
            "token": token,
            "key": "OTHER-LICENSE-2",
            "deviceId": "device-1",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "license-mismatch"
    assert _activation_exists(module, "TEST-LICENSE-1", "device-1")
    assert _activation_exists(module, "OTHER-LICENSE-2", "device-1")


def test_public_deactivation_accepts_bound_token_and_is_idempotent(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module)
    token = _signed_refresh_token(
        module,
        issued_at=now - 3600,
        expires_at=now - 1,
    )
    client = TestClient(module.app)
    request = {
        "token": token,
        "key": "test-license-1",
        "deviceId": "device-1",
    }

    first = client.post("/license/deactivate", json=request)
    second = client.post("/license/deactivate", json=request)

    assert first.status_code == 200
    assert first.json() == {"ok": True}
    assert second.status_code == 200
    assert not _activation_exists(module, "TEST-LICENSE-1", "device-1")


def test_device_limit_count_and_insert_are_serialized(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module, devices=())
    first_conn = module.db()
    begin_seen = threading.Event()
    outcome = []

    try:
        first_license = module.fetch_license_by_key(first_conn, "TEST-LICENSE-1")
        module._activate_license_row(first_conn, first_license, "device-first", now)

        def activate_second_device():
            try:
                with module.db() as second_conn:
                    second_conn.set_trace_callback(
                        lambda sql: begin_seen.set()
                        if sql.strip().lower().startswith("begin immediate")
                        else None
                    )
                    second_license = module.fetch_license_by_key(
                        second_conn,
                        "TEST-LICENSE-1",
                    )
                    module._activate_license_row(
                        second_conn,
                        second_license,
                        "device-second",
                        now,
                    )
                    outcome.append(("ok",))
            except module.HTTPException as exc:
                outcome.append(("http", exc.status_code, exc.detail))
            except Exception as exc:  # pragma: no cover - diagnostic assertion below
                outcome.append(("error", type(exc).__name__, str(exc)))

        worker = threading.Thread(target=activate_second_device)
        worker.start()
        acquired_serialization = begin_seen.wait(timeout=2)
        first_conn.commit()
        worker.join(timeout=7)

        assert acquired_serialization
        assert not worker.is_alive()
        assert outcome == [("http", 409, "device-limit-reached")]
    finally:
        if first_conn.in_transaction:
            first_conn.rollback()
        first_conn.close()

    with module.db() as conn:
        devices = conn.execute(
            """
            select device_id from activations
            where license_key='TEST-LICENSE-1'
            """
        ).fetchall()
    assert [row["device_id"] for row in devices] == ["device-first"]


def test_expired_signed_token_can_refresh_after_authoritative_revalidation(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module)
    expired_token = _signed_refresh_token(
        module,
        issued_at=now - 3600,
        expires_at=now - 1,
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/refresh",
        json={"token": expired_token, "deviceId": "device-1"},
    )

    assert response.status_code == 200, response.text
    refreshed = module.parse_and_verify_token(response.json()["token"])
    assert refreshed["device"] == "device-1"
    assert refreshed["iat"] >= now


def test_refresh_rejects_rebinding_even_when_other_device_is_activated(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module, devices=("device-1", "device-2"))
    token = _signed_refresh_token(
        module,
        issued_at=now - 60,
        expires_at=now + 3600,
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/refresh",
        json={"token": token, "deviceId": "device-2"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "device-mismatch"


def test_refresh_rejects_future_issued_or_missing_device_claims(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module)
    future_token = _signed_refresh_token(
        module,
        issued_at=now + module.TOKEN_FUTURE_SKEW_SECONDS + 60,
        expires_at=now + module.TOKEN_FUTURE_SKEW_SECONDS + 3600,
    )
    missing_device_payload = module.parse_and_verify_token(
        _signed_refresh_token(module, issued_at=now, expires_at=now + 3600)
    )
    missing_device_payload.pop("device")
    missing_device_token = module.sign_payload(missing_device_payload)
    client = TestClient(module.app)

    future_response = client.post(
        "/license/refresh",
        json={"token": future_token, "deviceId": "device-1"},
    )
    missing_response = client.post(
        "/license/refresh",
        json={"token": missing_device_token, "deviceId": "device-1"},
    )

    assert future_response.status_code == 400
    assert future_response.json()["detail"] == "invalid-token"
    assert missing_response.status_code == 400
    assert missing_response.json()["detail"] == "invalid-token"


def test_expired_token_still_requires_current_device_activation(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = _insert_perpetual_entitlement(module)
    expired_token = _signed_refresh_token(
        module,
        issued_at=now - 3600,
        expires_at=now - 1,
    )
    with sqlite3.connect(module.DB_PATH) as conn:
        conn.execute("delete from activations where device_id='device-1'")
    client = TestClient(module.app)

    response = client.post(
        "/license/refresh",
        json={"token": expired_token, "deviceId": "device-1"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "device-not-activated"


def test_public_rate_limit_returns_retry_after_and_bounds_client_state(monkeypatch, tmp_path):
    module = _load_module(
        monkeypatch,
        tmp_path,
        LICENSE_PUBLIC_RATE_LIMIT_REQUESTS=2,
        LICENSE_RATE_LIMIT_MAX_CLIENTS=2,
        PAYPAL_CHECKOUT_RATE_LIMIT_REQUESTS=1,
    )
    client = TestClient(module.app)

    first = client.post("/license/verify", content="{", headers={"content-type": "application/json"})
    second = client.post("/license/verify", content="{", headers={"content-type": "application/json"})
    limited = client.post("/license/verify", content="{", headers={"content-type": "application/json"})

    assert first.status_code == 422
    assert second.status_code == 422
    assert limited.status_code == 429
    assert limited.json()["detail"] == "rate-limit-exceeded"
    assert int(limited.headers["Retry-After"]) >= 1
    assert client.get("/checkout/desktop-monthly").status_code == 200
    assert client.get("/checkout/desktop-monthly").status_code == 429

    limiter = module._BoundedRateLimiter(max_requests=1, window_seconds=60, max_clients=2)
    for client_id in ("one", "two", "three"):
        limiter.check(client_id, now=1)
    assert len(limiter._buckets) == 2
    assert set(limiter._buckets) == {"two", "three"}


def test_desktop_checkout_is_hardened_and_shows_copyable_subscription_id(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    client = TestClient(module.app)

    response = client.get(
        "/checkout/desktop-monthly"
        "?deviceId=DEVICE-SECRET&token=AUTH-SECRET&license=LICENSE-SECRET"
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "https://www.paypal.com" in csp
    nonce_match = re.search(r"script-src 'nonce-([^']+)'", csp)
    assert nonce_match
    nonce = nonce_match.group(1)
    assert len(re.findall(rf"<(?:style|script) nonce=\"{re.escape(nonce)}\"", response.text)) == 3
    assert f'data-csp-nonce="{nonce}"' in response.text

    assert module.DEFAULT_PAYPAL_DESKTOP_CLIENT_ID in response.text
    assert f'data-plan-id="{module.DEFAULT_PAYPAL_DESKTOP_PLAN_ID}"' in response.text
    assert "https://www.paypal.com/sdk/js?" in response.text
    assert "Copy ID" in response.text
    assert "data.subscriptionID" in response.text
    assert "DEVICE-SECRET" not in response.text
    assert "AUTH-SECRET" not in response.text
    assert "LICENSE-SECRET" not in response.text
    assert "test-client-secret" not in response.text
    assert "LICENSE_PRIVATE_KEY_B64" not in response.text


def test_desktop_checkout_rejects_injected_or_unapproved_configuration(monkeypatch, tmp_path):
    injected = 'client"><script>alert(1)</script>'
    module = _load_module(
        monkeypatch,
        tmp_path,
        PAYPAL_DESKTOP_CLIENT_ID=injected,
    )
    response = TestClient(module.app).get("/checkout/desktop-monthly")

    assert response.status_code == 503
    assert response.json()["detail"] == "paypal-checkout-client-id-invalid"
    assert injected not in response.text

    monkeypatch.setenv("PAYPAL_DESKTOP_CLIENT_ID", module.DEFAULT_PAYPAL_DESKTOP_CLIENT_ID)
    monkeypatch.setenv("PAYPAL_DESKTOP_PLAN_ID", "P-ATTACKER")
    plan_response = TestClient(module.app).get("/checkout/desktop-monthly")
    assert plan_response.status_code == 503
    assert plan_response.json()["detail"] == "paypal-checkout-plan-not-allowed"


def test_checkout_renderer_escapes_all_dynamic_attributes(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    body = module._render_paypal_desktop_checkout(
        'client"><script>alert(1)</script>',
        'P-PLAN" data-evil="yes',
        'nonce"><script>alert(2)</script>',
    )

    assert 'client"><script>' not in body
    assert 'data-plan-id="P-PLAN" data-evil=' not in body
    assert 'nonce="nonce"><script>' not in body
    assert "%3Cscript%3E" in body
    assert "P-PLAN&quot; data-evil=&quot;yes" in body
    assert "nonce&quot;&gt;&lt;script&gt;" in body


def test_paypal_oauth_token_is_cached_until_near_expiry(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"access_token":"cached-token","expires_in":600}'

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return FakeResponse()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    assert module._paypal_access_token() == "cached-token"
    assert module._paypal_access_token() == "cached-token"
    assert calls == [(f"{module._paypal_api_base()}/v1/oauth2/token", 20)]


def test_paypal_api_retries_once_with_fresh_oauth_token_after_401(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    issued_tokens = iter(("token-one", "token-two"))
    api_authorizations = []

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def fake_urlopen(request, timeout):
        assert timeout == 20
        if request.full_url.endswith("/v1/oauth2/token"):
            token = next(issued_tokens)
            return FakeResponse(
                f'{{"access_token":"{token}","expires_in":600}}'.encode("utf-8")
            )
        api_authorizations.append(request.get_header("Authorization"))
        if len(api_authorizations) == 1:
            raise HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                {},
                io.BytesIO(b'{"name":"AUTHENTICATION_FAILURE"}'),
            )
        return FakeResponse(b'{"ok":true}')

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    assert module._paypal_api_request("GET", "/v1/test") == {"ok": True}
    assert api_authorizations == ["Bearer token-one", "Bearer token-two"]


def test_launcher_and_direct_start_share_offline_perpetual_default(monkeypatch, tmp_path):
    monkeypatch.delenv("LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS", raising=False)
    module = _load_module(monkeypatch, tmp_path)
    runner = RUNNER_PATH.read_text(encoding="utf-8")

    assert module.PERPETUAL_VERIFY_INTERVAL_SECONDS == 0
    assert (
        'if "%LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS%"=="" '
        'set "LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS=0"'
    ) in runner


def test_mint_key_generator_uses_secrets_choice(monkeypatch):
    module_name = f"licensing_server_mint_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, MINT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    calls = []

    def fake_choice(alphabet):
        calls.append(alphabet)
        return alphabet[0]

    monkeypatch.setattr(module.secrets, "choice", fake_choice)

    assert module.gen_key(blocks=2, block_size=3) == "AAA-AAA"
    assert calls == [module.ALPHABET] * 6
