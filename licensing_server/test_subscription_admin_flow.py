import base64
import importlib.util
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from nacl.signing import SigningKey


APP_PATH = Path(__file__).with_name("app.py")


def _load_module(monkeypatch, tmp_path, *, admin_token="admin-secret", term_days=30):
    module_name = f"licensing_server_subscription_flow_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader

    signing_key = SigningKey.generate()
    monkeypatch.setenv("ADMIN_TOKEN", admin_token)
    monkeypatch.delenv("ADMIN_TOKEN_FILE", raising=False)
    monkeypatch.setenv("ADMIN_COOKIE_SECURE", "0")
    monkeypatch.setenv(
        "LICENSE_PRIVATE_KEY_B64",
        base64.b64encode(bytes(signing_key)).decode("ascii"),
    )
    monkeypatch.setenv("LICENSE_SUBSCRIPTION_TERM_DAYS", str(term_days))

    spec.loader.exec_module(module)
    module.DB_PATH = tmp_path / "licenses.db"
    module.init_db()
    return module


def _extract_csrf(html: str) -> str:
    match = re.search(r"name=['\"]csrf_token['\"]\s+value=['\"]([^'\"]+)['\"]", html)
    assert match, "Expected csrf_token hidden input in response body"
    return match.group(1)


def _login_admin(client: TestClient, token: str) -> str:
    login_page = client.get("/admin/login")
    login_csrf = _extract_csrf(login_page.text)
    response = client.post(
        "/admin/login",
        data={"token": token, "csrf_token": login_csrf},
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    rotated_csrf = response.cookies.get("adm_csrf")
    assert rotated_csrf
    assert rotated_csrf != login_csrf

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    dashboard_csrf = _extract_csrf(dashboard.text)
    assert dashboard_csrf == rotated_csrf
    return dashboard_csrf


def _fetch_only_license_row(db_path: Path) -> sqlite3.Row:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("select * from licenses").fetchone()
        assert row is not None
        return row
    finally:
        conn.close()


def test_admin_create_subscription_without_period_end_defaults_future_end(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path, term_days=30)
    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")

    response = client.post(
        "/admin/create",
        data={
            "csrf_token": csrf,
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "subscriber@example.com",
            "kind": "subscription",
            "status": "active",
            "period_end": "",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    row = _fetch_only_license_row(module.DB_PATH)
    assert row["kind"] == "subscription"
    assert row["current_period_end"] == row["issued_at"] + (30 * 24 * 3600)


def test_subscription_created_without_period_end_can_activate(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path, term_days=30)
    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")

    client.post(
        "/admin/create",
        data={
            "csrf_token": csrf,
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "subscriber@example.com",
            "kind": "subscription",
            "status": "active",
            "period_end": "",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )
    row = _fetch_only_license_row(module.DB_PATH)

    activation = client.post(
        "/license/activate",
        json={"key": row["license_key"], "deviceId": "device-1", "email": row["owner_email"]},
    )

    assert activation.status_code == 200
    payload = module.parse_and_verify_token(activation.json()["token"])
    assert payload["kind"] == "subscription"
    assert payload["next_verify_at"] > payload["verified_at"]


def test_admin_update_blank_subscription_period_end_preserves_existing_value(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path, term_days=30)
    with sqlite3.connect(module.DB_PATH) as conn:
        conn.execute(
            """
            insert into licenses
              (license_key, plan, max_devices, active, issued_at, notes, owner_email, kind, status, current_period_end)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "SUBS-KEEP-0001",
                "pro",
                1,
                1,
                1_700_000_000,
                None,
                "subscriber@example.com",
                "subscription",
                "active",
                1_800_000_000,
            ),
        )

    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")
    response = client.post(
        "/admin/license/SUBS-KEEP-0001/update",
        data={
            "csrf_token": csrf,
            "kind": "subscription",
            "status": "active",
            "current_period_end": "",
            "cancel_at_period_end": 0,
            "max_devices": 1,
            "plan": "pro",
            "owner_email": "subscriber@example.com",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    conn = sqlite3.connect(module.DB_PATH)
    try:
        row = conn.execute(
            "select current_period_end from licenses where license_key='SUBS-KEEP-0001'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == 1_800_000_000


def test_init_db_backfills_existing_subscription_rows(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path, term_days=30)
    db_path = module.DB_PATH
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            drop table if exists activations;
            drop table if exists licenses;
            create table licenses (
              license_key text primary key,
              plan text not null default 'pro',
              max_devices integer not null default 1,
              active integer not null default 1,
              issued_at integer not null,
              notes text,
              owner_email text,
              last_seen integer,
              kind text default 'perpetual',
              status text default 'active',
              current_period_end integer,
              cancel_at_period_end integer
            );
            create table activations (
              id integer primary key autoincrement,
              license_key text not null,
              device_id text not null,
              activated_at integer not null,
              last_activity integer,
              unique(license_key, device_id)
            );
            """
        )
        conn.execute(
            """
            insert into licenses
              (license_key, plan, max_devices, active, issued_at, notes, owner_email, kind, status, current_period_end)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "SUBS-BACKFILL-1",
                "pro",
                1,
                1,
                1_700_000_000,
                None,
                "backfill@example.com",
                "subscription",
                "active",
                None,
            ),
        )

    module.init_db()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "select current_period_end from licenses where license_key='SUBS-BACKFILL-1'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == 1_700_000_000 + (30 * 24 * 3600)


def test_admin_create_perpetual_keeps_period_end_empty(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path, term_days=30)
    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")

    response = client.post(
        "/admin/create",
        data={
            "csrf_token": csrf,
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "perpetual@example.com",
            "kind": "perpetual",
            "status": "active",
            "period_end": "",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    row = _fetch_only_license_row(module.DB_PATH)
    assert row["kind"] == "perpetual"
    assert row["current_period_end"] is None


def test_admin_create_form_remains_valid_after_later_dashboard_get(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    client = TestClient(module.app)
    first_form_csrf = _login_admin(client, "admin-secret")

    later_dashboard = client.get("/admin")
    later_form_csrf = _extract_csrf(later_dashboard.text)
    assert later_form_csrf == first_form_csrf

    response = client.post(
        "/admin/create",
        data={
            "csrf_token": first_form_csrf,
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "",
            "kind": "perpetual",
            "status": "active",
            "period_end": "",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    row = _fetch_only_license_row(module.DB_PATH)
    assert row["kind"] == "perpetual"


def test_admin_create_rejects_wrong_csrf_token(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    client = TestClient(module.app)
    _login_admin(client, "admin-secret")

    response = client.post(
        "/admin/create",
        data={
            "csrf_token": "wrong-token",
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "",
            "kind": "perpetual",
            "status": "active",
            "period_end": "",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "csrf-token-invalid"
    with sqlite3.connect(module.DB_PATH) as conn:
        assert conn.execute("select count(*) from licenses").fetchone()[0] == 0


def test_admin_create_perpetual_ignores_malformed_period_end(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")

    response = client.post(
        "/admin/create",
        data={
            "csrf_token": csrf,
            "count": 1,
            "plan": "pro",
            "max_devices": 1,
            "owner_email": "",
            "kind": "perpetual",
            "status": "active",
            "period_end": "07/17/2026",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    row = _fetch_only_license_row(module.DB_PATH)
    assert row["kind"] == "perpetual"
    assert row["current_period_end"] is None


def test_admin_can_still_deactivate_a_device_without_a_license_token(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    now = int(module.time.time())
    with sqlite3.connect(module.DB_PATH) as conn:
        conn.execute(
            """
            insert into licenses
              (license_key, plan, max_devices, active, issued_at, kind, status)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            ("ADMIN-DEACTIVATE-1", "pro", 1, 1, now, "perpetual", "active"),
        )
        conn.execute(
            """
            insert into activations
              (license_key, device_id, activated_at, last_activity)
            values (?, ?, ?, ?)
            """,
            ("ADMIN-DEACTIVATE-1", "device-admin", now, now),
        )

    client = TestClient(module.app)
    csrf = _login_admin(client, "admin-secret")
    response = client.post(
        "/admin/license/ADMIN-DEACTIVATE-1/deactivate-device",
        data={"csrf_token": csrf, "deviceId": "device-admin"},
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with sqlite3.connect(module.DB_PATH) as conn:
        activation = conn.execute(
            """
            select 1 from activations
            where license_key='ADMIN-DEACTIVATE-1' and device_id='device-admin'
            """
        ).fetchone()
    assert activation is None
