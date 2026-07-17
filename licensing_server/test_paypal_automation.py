import base64
import datetime as dt
import importlib.util
import inspect
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from nacl.signing import SigningKey


APP_PATH = Path(__file__).with_name("app.py")
PLAN_ID = "P-83N24493LW950963HNIIXO7Q"
WEBSITE_PLAN_ID = "P-4L214935JK8549417NIAB5KY"


def _load_module(monkeypatch, tmp_path):
    module_name = f"licensing_server_paypal_automation_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader

    signing_key = SigningKey.generate()
    monkeypatch.setenv(
        "LICENSE_PRIVATE_KEY_B64",
        base64.b64encode(bytes(signing_key)).decode("ascii"),
    )
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client-id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "webhook-id")
    monkeypatch.setenv("PAYPAL_PLAN_ID", PLAN_ID)
    monkeypatch.setenv("PAYPAL_LICENSE_PLAN", "premium-desktop-monthly")
    monkeypatch.setenv("PAYPAL_PAYEE_MERCHANT_ID", "MERCHANT-VOX-STELLA")
    monkeypatch.setenv("PAYPAL_ONETIME_PRODUCT_ID", "VOX-STELLA-LIFETIME")

    spec.loader.exec_module(module)
    module.DB_PATH = tmp_path / "licenses.db"
    module.init_db()
    return module


def _paypal_subscription(
    subscription_id="I-SUBSCRIPTION-123",
    *,
    status="ACTIVE",
    plan_id=PLAN_ID,
    update_time="2025-01-01T00:00:00.000000Z",
    status_update_time=None,
):
    subscription = {
        "id": subscription_id,
        "status": status,
        "plan_id": plan_id,
        "update_time": update_time,
        "subscriber": {
            "payer_id": "PAYER-123",
            "email_address": "buyer@example.com",
        },
        "billing_info": {
            "next_billing_time": "2099-06-23T12:30:00Z",
        },
    }
    if status_update_time is not None:
        subscription["status_update_time"] = status_update_time
    return subscription


def _paypal_capture(
    capture_id="CAPTURE-250",
    *,
    order_id="ORDER-250",
    update_time="2025-01-01T00:00:00.000000Z",
):
    return {
        "id": capture_id,
        "status": "COMPLETED",
        "update_time": update_time,
        "amount": {"currency_code": "USD", "value": "250.00"},
        "supplementary_data": {"related_ids": {"order_id": order_id}},
        "payee": {
            "merchant_id": "MERCHANT-VOX-STELLA",
            "email_address": "billing@voxstella.example",
        },
    }


def _paypal_order(
    order_id="ORDER-250",
    *,
    capture_id="CAPTURE-250",
    product_id="VOX-STELLA-LIFETIME",
    custom_id="voxstella-lifetime",
    invoice_id="VS-250-0001",
):
    return {
        "id": order_id,
        "payer": {
            "email_address": "one-time-buyer@example.com",
            "payer_id": "PAYER-250",
        },
        "purchase_units": [
            {
                "reference_id": product_id,
                "custom_id": custom_id,
                "invoice_id": invoice_id,
                "payee": {
                    "merchant_id": "MERCHANT-VOX-STELLA",
                    "email_address": "billing@voxstella.example",
                },
                "payments": {"captures": [{"id": capture_id}]},
            }
        ],
    }


def _fetch_license_by_subscription(db_path: Path, subscription_id: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "select * from licenses where paypal_subscription_id=?",
            (subscription_id,),
        ).fetchone()
    finally:
        conn.close()


def _fetch_license_by_capture(db_path: Path, capture_id: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "select * from licenses where paypal_capture_id=?",
            (capture_id,),
        ).fetchone()
    finally:
        conn.close()


def test_init_db_safely_migrates_duplicate_paypal_order_ids(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    legacy_db = tmp_path / "legacy-duplicate-orders.db"
    module.DB_PATH = legacy_db
    with sqlite3.connect(legacy_db) as conn:
        conn.executescript(
            """
            create table licenses (
              license_key text primary key,
              plan text not null default 'pro',
              max_devices integer not null default 1,
              active integer not null default 1,
              issued_at integer not null,
              notes text,
              paypal_order_id text,
              paypal_capture_id text
            );
            create table activations (
              id integer primary key autoincrement,
              license_key text not null,
              device_id text not null,
              activated_at integer not null,
              unique(license_key, device_id)
            );
            create index idx_licenses_paypal_order_id
              on licenses(paypal_order_id)
              where paypal_order_id is not null;
            """
        )
        conn.execute(
            """
            insert into licenses
              (license_key, active, issued_at, paypal_order_id, paypal_capture_id)
            values ('ORDER-WINNER', 1, 100, 'ORDER-DUPLICATE', 'CAPTURE-WINNER')
            """
        )
        conn.execute(
            """
            insert into licenses
              (license_key, active, issued_at, paypal_order_id, paypal_capture_id)
            values ('ORDER-LOSER', 1, 200, 'ORDER-DUPLICATE', 'CAPTURE-LOSER')
            """
        )
        conn.execute(
            """
            insert into activations (license_key, device_id, activated_at)
            values ('ORDER-LOSER', 'duplicate-device', 200)
            """
        )

    module.init_db()

    with module.db() as conn:
        winner = conn.execute(
            "select * from licenses where license_key='ORDER-WINNER'"
        ).fetchone()
        loser = conn.execute(
            "select * from licenses where license_key='ORDER-LOSER'"
        ).fetchone()
        loser_activation = conn.execute(
            "select 1 from activations where license_key='ORDER-LOSER'"
        ).fetchone()
        loser_capture_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='capture' and resource_id='CAPTURE-LOSER'
            """
        ).fetchone()
        order_index = next(
            row
            for row in conn.execute("pragma index_list('licenses')").fetchall()
            if row["name"] == "idx_licenses_paypal_order_id"
        )

        assert winner["paypal_order_id"] == "ORDER-DUPLICATE"
        assert int(winner["active"]) == 1
        assert loser["paypal_order_id"] is None
        assert int(loser["active"]) == 0
        assert loser["status"] == "duplicate"
        assert loser_activation is None
        assert loser_capture_state is None
        assert int(order_index["unique"]) == 1

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                insert into licenses
                  (license_key, issued_at, paypal_order_id)
                values ('ORDER-THIRD', 300, 'ORDER-DUPLICATE')
                """
            )


def test_init_db_preserves_terminal_order_evidence_before_duplicate_cleanup(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    with module.db() as conn:
        conn.execute("drop index idx_licenses_paypal_order_id")
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_order_id, paypal_capture_id, paypal_status
            ) values (
              'ACTIVE-WINNER', 'pro', 1, 1, 100, 'perpetual', 'active',
              'ORDER-TERMINAL-DUP', 'CAPTURE-ACTIVE-WINNER', 'COMPLETED'
            )
            """
        )
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_order_id, paypal_capture_id, paypal_status
            ) values (
              'REFUNDED-LOSER', 'pro', 1, 0, 200, 'perpetual', 'refunded',
              'ORDER-TERMINAL-DUP', 'CAPTURE-REFUNDED-LOSER',
              'PAYMENT.CAPTURE.REFUNDED'
            )
            """
        )
        conn.execute(
            """
            insert into activations (
              license_key, device_id, activated_at, last_activity
            ) values ('ACTIVE-WINNER', 'winner-device', 100, 100)
            """
        )

    module.init_db()

    with module.db() as conn:
        winner = conn.execute(
            "select * from licenses where license_key='ACTIVE-WINNER'"
        ).fetchone()
        activation = conn.execute(
            "select 1 from activations where license_key='ACTIVE-WINNER'"
        ).fetchone()
        order_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='order' and resource_id='ORDER-TERMINAL-DUP'
            """
        ).fetchone()
    assert int(winner["active"]) == 0
    assert winner["status"] == "refunded"
    assert activation is None
    assert int(order_state["terminal"]) == 1
    assert order_state["source_id"] == "migration:terminal"


def test_init_db_closes_terminal_state_across_duplicate_capture_order_aliases(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    shared_capture_id = "CAPTURE-OLD-SHARED"
    refunded_order_id = "ORDER-OLD-REFUNDED"
    reusable_order_id = "ORDER-REUSABLE"
    with module.db() as conn:
        conn.execute("drop index idx_licenses_paypal_capture_id")
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_capture_id, paypal_order_id, paypal_status
            ) values (
              'REFUNDED-OLDER', 'pro', 1, 0, 100, 'perpetual', 'refunded',
              ?, ?, 'PAYMENT.CAPTURE.REFUNDED'
            )
            """,
            (shared_capture_id, refunded_order_id),
        )
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_capture_id, paypal_order_id, paypal_status
            ) values (
              'ACTIVE-NEWER-DUPLICATE', 'pro', 1, 1, 200,
              'perpetual', 'active', ?, ?, 'COMPLETED'
            )
            """,
            (shared_capture_id, reusable_order_id),
        )
        conn.execute(
            """
            insert into activations (
              license_key, device_id, activated_at, last_activity
            ) values (
              'ACTIVE-NEWER-DUPLICATE', 'duplicate-device', 200, 200
            )
            """
        )

    module.init_db()

    with module.db() as conn:
        reusable_order_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='order' and resource_id=?
            """,
            (reusable_order_id,),
        ).fetchone()
        duplicate_row = conn.execute(
            """
            select * from licenses
            where license_key='ACTIVE-NEWER-DUPLICATE'
            """
        ).fetchone()
        duplicate_activation = conn.execute(
            """
            select 1 from activations
            where license_key='ACTIVE-NEWER-DUPLICATE'
            """
        ).fetchone()
    assert int(reusable_order_state["terminal"]) == 1
    assert (
        reusable_order_state["source_id"]
        == "migration:terminal-closure"
    )
    assert duplicate_row["paypal_capture_id"] is None
    assert duplicate_row["paypal_order_id"] == reusable_order_id
    assert duplicate_row["status"] == "duplicate"
    assert duplicate_activation is None

    new_capture_id = "CAPTURE-NEW-ATTEMPT"
    new_capture = _paypal_capture(
        new_capture_id,
        order_id=reusable_order_id,
        update_time="2025-01-05T00:00:00.000000Z",
    )
    new_order = _paypal_order(
        reusable_order_id,
        capture_id=new_capture_id,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda _capture_id: new_capture,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda _order_id: new_order,
    )
    response = TestClient(module.app).post(
        "/license/activate-paypal-purchase",
        json={
            "paypalId": new_capture_id,
            "deviceId": "new-device",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "paypal-order-revoked"
    assert _fetch_license_by_capture(module.DB_PATH, new_capture_id) is None
    with module.db() as conn:
        projected_capture = conn.execute(
            """
            select 1 from paypal_resource_states
            where resource_kind='capture' and resource_id=?
            """,
            (new_capture_id,),
        ).fetchone()
    assert projected_capture is None


def test_init_db_upgrades_existing_paypal_state_and_event_tables(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    legacy_db = tmp_path / "legacy-paypal-state.db"
    module.DB_PATH = legacy_db
    with sqlite3.connect(legacy_db) as conn:
        conn.executescript(
            """
            create table licenses (
              license_key text primary key,
              plan text not null default 'pro',
              max_devices integer not null default 1,
              active integer not null default 1,
              issued_at integer not null,
              notes text
            );
            create table activations (
              id integer primary key autoincrement,
              license_key text not null,
              device_id text not null,
              activated_at integer not null,
              unique(license_key, device_id)
            );
            create table paypal_events (
              event_id text primary key,
              event_type text not null,
              subscription_id text,
              processed_at integer not null
            );
            create table paypal_resource_states (
              resource_kind text not null,
              resource_id text not null,
              state_time_us integer not null,
              state_status text not null,
              state_rank integer not null,
              terminal integer not null default 0,
              source_id text,
              updated_at integer not null,
              primary key(resource_kind, resource_id)
            );
            insert into paypal_events (
              event_id, event_type, subscription_id, processed_at
            ) values (
              'WH-LEGACY', 'BILLING.SUBSCRIPTION.SUSPENDED',
              'I-LEGACY', 100
            );
            insert into paypal_resource_states (
              resource_kind, resource_id, state_time_us, state_status,
              state_rank, terminal, source_id, updated_at
            ) values (
              'subscription', 'I-LEGACY', 1, 'MIGRATED:SUSPENDED',
              30, 0, 'migration:restrictive', 100
            );
            """
        )

    module.init_db()

    with module.db() as conn:
        event_columns = {
            row["name"]
            for row in conn.execute("pragma table_info(paypal_events)").fetchall()
        }
        state_columns = {
            row["name"]
            for row in conn.execute(
                "pragma table_info(paypal_resource_states)"
            ).fetchall()
        }
        event = conn.execute(
            "select * from paypal_events where event_id='WH-LEGACY'"
        ).fetchone()
        state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id='I-LEGACY'
            """
        ).fetchone()
    assert {"event_time_us", "disposition"} <= event_columns
    assert {
        "provider_status_time_us",
        "provider_update_time_us",
        "provisional",
    } <= state_columns
    assert event["event_time_us"] is None
    assert event["disposition"] == "legacy_processed"
    assert int(state["provisional"]) == 1


def test_init_db_atomically_deduplicates_all_paypal_identity_columns(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    with module.db() as conn:
        conn.execute("drop index idx_licenses_paypal_subscription_id")
        conn.execute("drop index idx_licenses_paypal_capture_id")
        rows = (
            (
                "SUB-WINNER",
                100,
                "I-DUPLICATE-SUB",
                None,
                None,
            ),
            (
                "SUB-LOSER",
                200,
                "I-DUPLICATE-SUB",
                None,
                None,
            ),
            (
                "CAPTURE-WINNER",
                100,
                None,
                "CAPTURE-DUPLICATE",
                "ORDER-CAPTURE-WINNER",
            ),
            (
                "CAPTURE-LOSER",
                200,
                None,
                "CAPTURE-DUPLICATE",
                "ORDER-CAPTURE-LOSER",
            ),
        )
        conn.executemany(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_subscription_id, paypal_capture_id, paypal_order_id,
              paypal_status
            ) values (?, 'pro', 1, 1, ?, 'perpetual', 'active', ?, ?, ?, 'ACTIVE')
            """,
            rows,
        )
        conn.executemany(
            """
            insert into activations (
              license_key, device_id, activated_at, last_activity
            ) values (?, ?, 200, 200)
            """,
            (
                ("SUB-LOSER", "sub-loser-device"),
                ("CAPTURE-LOSER", "capture-loser-device"),
            ),
        )

    module.init_db()

    with module.db() as conn:
        rows = {
            row["license_key"]: row
            for row in conn.execute(
                """
                select * from licenses
                where license_key in (
                  'SUB-WINNER', 'SUB-LOSER',
                  'CAPTURE-WINNER', 'CAPTURE-LOSER'
                )
                """
            ).fetchall()
        }
        loser_activations = conn.execute(
            """
            select count(*) from activations
            where license_key in ('SUB-LOSER', 'CAPTURE-LOSER')
            """
        ).fetchone()[0]
        indexes = {
            row["name"]: int(row["unique"])
            for row in conn.execute("pragma index_list('licenses')").fetchall()
        }
    assert rows["SUB-WINNER"]["paypal_subscription_id"] == "I-DUPLICATE-SUB"
    assert rows["SUB-LOSER"]["paypal_subscription_id"] is None
    assert rows["SUB-LOSER"]["paypal_status"] == "DUPLICATE_SUBSCRIPTION"
    assert rows["CAPTURE-WINNER"]["paypal_capture_id"] == "CAPTURE-DUPLICATE"
    assert rows["CAPTURE-LOSER"]["paypal_capture_id"] is None
    assert rows["CAPTURE-LOSER"]["paypal_status"] == "DUPLICATE_CAPTURE"
    assert loser_activations == 0
    assert indexes["idx_licenses_paypal_subscription_id"] == 1
    assert indexes["idx_licenses_paypal_capture_id"] == 1
    assert indexes["idx_licenses_paypal_order_id"] == 1


def test_init_db_does_not_terminally_latch_generic_admin_disabled_purchase(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    with module.db() as conn:
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              paypal_capture_id, paypal_order_id, paypal_status
            ) values (
              'ADMIN-DISABLED', 'pro', 1, 0, 100, 'perpetual', 'disabled',
              'CAPTURE-ADMIN-DISABLED', 'ORDER-ADMIN-DISABLED', 'COMPLETED'
            )
            """
        )

    module.init_db()

    with module.db() as conn:
        terminal_count = conn.execute(
            """
            select count(*) from paypal_resource_states
            where terminal=1 and resource_id in (
              'CAPTURE-ADMIN-DISABLED', 'ORDER-ADMIN-DISABLED'
            )
            """
        ).fetchone()[0]
    assert terminal_count == 0


def test_concurrent_different_captures_cannot_claim_the_same_order(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    first_conn = module.db()
    begin_seen = threading.Event()
    outcome = []

    try:
        first = module._upsert_paypal_onetime_license(
            first_conn,
            _paypal_capture("CAPTURE-RACE-ONE", order_id="ORDER-RACE"),
            order=_paypal_order(
                "ORDER-RACE",
                capture_id="CAPTURE-RACE-ONE",
            ),
        )

        def claim_same_order_with_different_capture():
            try:
                with module.db() as second_conn:
                    second_conn.set_trace_callback(
                        lambda sql: begin_seen.set()
                        if sql.strip().lower().startswith("begin immediate")
                        else None
                    )
                    row = module._upsert_paypal_onetime_license(
                        second_conn,
                        _paypal_capture(
                            "CAPTURE-RACE-TWO",
                            order_id="ORDER-RACE",
                        ),
                        order=_paypal_order(
                            "ORDER-RACE",
                            capture_id="CAPTURE-RACE-TWO",
                        ),
                    )
                    outcome.append(("ok", row["license_key"]))
            except module.HTTPException as exc:
                outcome.append(("http", exc.status_code, exc.detail))
            except Exception as exc:  # pragma: no cover - diagnostic assertion below
                outcome.append(("error", type(exc).__name__, str(exc)))

        worker = threading.Thread(target=claim_same_order_with_different_capture)
        worker.start()
        acquired_serialization = begin_seen.wait(timeout=2)
        first_conn.commit()
        worker.join(timeout=7)

        assert acquired_serialization
        assert not worker.is_alive()
        assert outcome == [("http", 409, "paypal-order-already-claimed")]
    finally:
        if first_conn.in_transaction:
            first_conn.rollback()
        first_conn.close()

    with module.db() as conn:
        rows = conn.execute(
            "select * from licenses where paypal_order_id='ORDER-RACE'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["license_key"] == first["license_key"]
    assert rows[0]["paypal_capture_id"] == "CAPTURE-RACE-ONE"


def test_concurrent_identical_subscription_activations_are_idempotent(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    fetch_barrier = threading.Barrier(2)

    def fetch_subscription(subscription_id):
        fetch_barrier.wait(timeout=5)
        return _paypal_subscription(subscription_id)

    monkeypatch.setattr(module, "_fetch_paypal_subscription", fetch_subscription)

    def activate():
        return module.activate_paypal_subscription(
            module.PayPalActivateReq(
                subscriptionId="I-CONCURRENT-ACTIVATION",
                deviceId="device-concurrent",
                email="buyer@example.com",
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (executor.submit(activate), executor.submit(activate))
        results = [future.result(timeout=10) for future in futures]

    payloads = [module.parse_and_verify_token(result["token"]) for result in results]
    assert payloads[0]["lic"] == payloads[1]["lic"]
    with module.db() as conn:
        licenses = conn.execute(
            """
            select license_key from licenses
            where paypal_subscription_id='I-CONCURRENT-ACTIVATION'
            """
        ).fetchall()
        activations = conn.execute(
            """
            select device_id from activations
            where license_key=?
            """,
            (payloads[0]["lic"],),
        ).fetchall()
    assert len(licenses) == 1
    assert [row["device_id"] for row in activations] == ["device-concurrent"]


def test_concurrent_identical_webhooks_are_claimed_once(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    fetch_barrier = threading.Barrier(2)

    def fetch_subscription(subscription_id):
        fetch_barrier.wait(timeout=5)
        return _paypal_subscription(subscription_id)

    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    monkeypatch.setattr(module, "_fetch_paypal_subscription", fetch_subscription)
    client = TestClient(module.app)
    event = {
        "id": "WH-CONCURRENT-IDENTICAL",
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "create_time": "2025-01-02T00:00:00.000000Z",
        "resource": {"id": "I-CONCURRENT-WEBHOOK"},
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = [
            future.result(timeout=10)
            for future in (
                executor.submit(client.post, "/paypal/webhook", json=event),
                executor.submit(client.post, "/paypal/webhook", json=event),
            )
        ]

    assert all(response.status_code == 200 for response in responses)
    outcomes = sorted(
        (response.json()["duplicate"], response.json()["processed"])
        for response in responses
    )
    assert outcomes == [(False, True), (True, False)]
    with module.db() as conn:
        event_count = conn.execute(
            "select count(*) from paypal_events where event_id=?",
            (event["id"],),
        ).fetchone()[0]
        license_count = conn.execute(
            """
            select count(*) from licenses
            where paypal_subscription_id='I-CONCURRENT-WEBHOOK'
            """
        ).fetchone()[0]
    assert event_count == 1
    assert license_count == 1


def test_paypal_subscription_retries_only_license_key_collisions(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    with module.db() as conn:
        conn.execute(
            """
            insert into licenses (license_key, issued_at)
            values ('COLLISION-KEY', 1)
            """
        )
    generated_keys = iter(("COLLISION-KEY", "RETRY-WINNER-KEY"))
    monkeypatch.setattr(module, "_generate_license_key", lambda: next(generated_keys))

    with module.db() as conn:
        row = module._upsert_paypal_subscription_license(
            conn,
            _paypal_subscription("I-LICENSE-KEY-COLLISION"),
            event_type="BILLING.SUBSCRIPTION.ACTIVATED",
        )

    assert row["license_key"] == "RETRY-WINNER-KEY"
    assert row["paypal_subscription_id"] == "I-LICENSE-KEY-COLLISION"


def test_webhook_claim_rolls_back_when_entitlement_mutation_fails(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    subscription = _paypal_subscription("I-RETRY-AFTER-FAILURE")
    subscription["billing_info"] = {}
    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    monkeypatch.setattr(module, "_fetch_paypal_subscription", lambda _subscription_id: subscription)
    client = TestClient(module.app)
    event = {
        "id": "WH-ROLLBACK-CLAIM",
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "create_time": "2025-01-02T00:00:00.000000Z",
        "resource": {"id": "I-RETRY-AFTER-FAILURE"},
    }

    failed = client.post("/paypal/webhook", json=event)

    assert failed.status_code == 400
    assert failed.json()["detail"] == "paypal-subscription-period-missing"
    with module.db() as conn:
        assert not module._paypal_event_already_processed(conn, event["id"])

    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda _subscription_id: _paypal_subscription("I-RETRY-AFTER-FAILURE"),
    )
    retried = client.post("/paypal/webhook", json=event)

    assert retried.status_code == 200
    assert retried.json() == {
        "ok": True,
        "duplicate": False,
        "processed": True,
    }


def test_webhook_handler_is_sync_so_blocking_paypal_io_runs_in_threadpool(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)

    assert not inspect.iscoroutinefunction(module.paypal_webhook)
    route = next(
        route
        for route in module.app.routes
        if getattr(route, "path", None) == "/paypal/webhook"
    )
    assert not inspect.iscoroutinefunction(route.endpoint)


@pytest.mark.parametrize(
    "api_base",
    (
        "http://api-m.paypal.com",
        "file:///tmp/fake-paypal",
        "https://api-m.paypal.com.evil.example",
        "https://api-m.paypal.com@evil.example",
        "https://api-m.paypal.com/v1",
        "https://api-m.paypal.com:444",
        "https://api-m.paypal.com:not-a-port",
    ),
)
def test_paypal_api_base_rejects_non_paypal_or_non_https_origins(
    monkeypatch,
    tmp_path,
    api_base,
):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setenv("PAYPAL_API_BASE", api_base)

    with pytest.raises(module.HTTPException) as exc_info:
        module._paypal_api_base()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "paypal-api-base-invalid"


@pytest.mark.parametrize(
    "event_type",
    (
        "PAYMENT.CAPTURE.REVERSED",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.DECLINED",
    ),
)
def test_terminal_capture_events_use_capture_resource_id(
    monkeypatch,
    tmp_path,
    event_type,
):
    module = _load_module(monkeypatch, tmp_path)

    assert module._paypal_capture_id_from_event(
        {
            "event_type": event_type,
            "resource": {"id": "CAPTURE-TERMINAL-ID"},
        }
    ) == "CAPTURE-TERMINAL-ID"
    assert module._paypal_capture_id_from_event(
        {
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "resource": {"id": "REFUND-NOT-CAPTURE-ID"},
        }
    ) is None


def test_declined_webhook_tombstones_capture_and_order(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-DECLINED"
    order_id = "ORDER-DECLINED"
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    client = TestClient(module.app)

    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-CAPTURE-DECLINED",
            "event_type": "PAYMENT.CAPTURE.DECLINED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {
                "id": capture_id,
                "supplementary_data": {
                    "related_ids": {"order_id": order_id}
                },
            },
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["processed"] is True
    with module.db() as conn:
        states = conn.execute(
            """
            select resource_kind, terminal from paypal_resource_states
            where resource_id in (?, ?)
            order by resource_kind
            """,
            (capture_id, order_id),
        ).fetchall()
    assert [(row["resource_kind"], row["terminal"]) for row in states] == [
        ("capture", 1),
        ("order", 1),
    ]


def test_terminal_webhook_does_not_claim_when_alias_resolution_fails(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-ALIAS-RETRY"
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )

    def fail_capture_fetch(_capture_id):
        raise module.HTTPException(
            status_code=502,
            detail="paypal-api-failed",
        )

    monkeypatch.setattr(module, "_fetch_paypal_capture", fail_capture_fetch)
    client = TestClient(module.app)
    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-ALIAS-RETRY",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {"capture_id": capture_id},
        },
    )

    assert response.status_code == 502
    with module.db() as conn:
        event = conn.execute(
            "select 1 from paypal_events where event_id='WH-ALIAS-RETRY'"
        ).fetchone()
        state = conn.execute(
            """
            select 1 from paypal_resource_states
            where resource_kind='capture' and resource_id=?
            """,
            (capture_id,),
        ).fetchone()
    assert event is None
    assert state is None


def test_paused_completed_snapshot_cannot_resurrect_refunded_capture(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-PAUSED-REFUND"
    order_id = "ORDER-PAUSED-REFUND"
    stale_capture = _paypal_capture(
        capture_id,
        order_id=order_id,
        update_time="2025-01-01T00:00:00.000000Z",
    )
    order = _paypal_order(order_id, capture_id=capture_id)
    monkeypatch.setattr(module, "_fetch_paypal_capture", lambda _capture_id: stale_capture)
    monkeypatch.setattr(module, "_fetch_paypal_order", lambda _order_id: order)
    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    client = TestClient(module.app)

    initial = client.post(
        "/license/activate-paypal-purchase",
        json={"paypalId": capture_id, "deviceId": "device-before-refund"},
    )
    assert initial.status_code == 200, initial.text

    snapshot_ready = threading.Event()
    release_snapshot = threading.Event()
    outcome = []

    def paused_order_fetch(_capture):
        snapshot_ready.set()
        if not release_snapshot.wait(timeout=10):
            raise AssertionError("Timed out waiting to release stale capture snapshot")
        return order

    monkeypatch.setattr(module, "_fetch_order_for_capture", paused_order_fetch)

    def retry_activation():
        try:
            module.activate_paypal_purchase(
                module.PayPalPurchaseActivateReq(
                    paypalId=capture_id,
                    deviceId="device-before-refund",
                )
            )
            outcome.append(("ok",))
        except module.HTTPException as exc:
            outcome.append(("http", exc.status_code, exc.detail))
        except Exception as exc:  # pragma: no cover - diagnostic assertion below
            outcome.append(("error", type(exc).__name__, str(exc)))

    worker = threading.Thread(target=retry_activation)
    worker.start()
    assert snapshot_ready.wait(timeout=5)

    refund = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-PAUSED-REFUND",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {
                "id": "REFUND-PAUSED",
                "supplementary_data": {
                    "related_ids": {
                        "capture_id": capture_id,
                        "order_id": order_id,
                    }
                },
            },
        },
    )
    release_snapshot.set()
    worker.join(timeout=10)

    assert refund.status_code == 200, refund.text
    assert refund.json()["processed"] is True
    assert not worker.is_alive()
    assert outcome == [("http", 409, "paypal-capture-revoked")]
    with module.db() as conn:
        license_row = conn.execute(
            "select * from licenses where paypal_capture_id=?",
            (capture_id,),
        ).fetchone()
        activation_count = conn.execute(
            "select count(*) from activations where license_key=?",
            (license_row["license_key"],),
        ).fetchone()[0]
        capture_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='capture' and resource_id=?
            """,
            (capture_id,),
        ).fetchone()
    assert int(license_row["active"]) == 0
    assert license_row["status"] == "refunded"
    assert activation_count == 0
    assert int(capture_state["terminal"]) == 1


def test_refund_before_entitlement_creates_permanent_capture_and_order_tombstones(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-REFUND-FIRST"
    order_id = "ORDER-REFUND-FIRST"
    capture = _paypal_capture(
        capture_id,
        order_id=order_id,
        update_time="2025-01-01T00:00:00.000000Z",
    )
    order = _paypal_order(order_id, capture_id=capture_id)
    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    monkeypatch.setattr(module, "_fetch_paypal_capture", lambda _capture_id: capture)
    monkeypatch.setattr(module, "_fetch_paypal_order", lambda _order_id: order)
    client = TestClient(module.app)
    refund_event = {
        "id": "WH-REFUND-BEFORE-TARGET",
        "event_type": "PAYMENT.CAPTURE.REFUNDED",
        "create_time": "2025-01-03T00:00:00.000000Z",
        "resource": {
            "id": "REFUND-BEFORE-TARGET",
            "supplementary_data": {
                "related_ids": {
                    "capture_id": capture_id,
                }
            },
        },
    }

    refund = client.post("/paypal/webhook", json=refund_event)
    duplicate_refund = client.post("/paypal/webhook", json=refund_event)
    activation = client.post(
        "/license/activate-paypal-purchase",
        json={"paypalId": capture_id, "deviceId": "device-after-refund"},
    )
    stale_completion = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-STALE-COMPLETION",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "create_time": "2025-01-01T00:00:00.000000Z",
            "resource": {"id": capture_id},
        },
    )

    assert refund.status_code == 200
    assert refund.json() == {"ok": True, "duplicate": False, "processed": True}
    assert duplicate_refund.status_code == 200
    assert duplicate_refund.json()["duplicate"] is True
    assert activation.status_code == 409
    assert activation.json()["detail"] == "paypal-capture-revoked"
    assert stale_completion.status_code == 200
    assert stale_completion.json() == {
        "ok": True,
        "duplicate": False,
        "processed": False,
    }
    assert _fetch_license_by_capture(module.DB_PATH, capture_id) is None
    with module.db() as conn:
        states = conn.execute(
            """
            select resource_kind, terminal from paypal_resource_states
            where resource_id in (?, ?)
            order by resource_kind
            """,
            (capture_id, order_id),
        ).fetchall()
        events = conn.execute(
            """
            select event_id, disposition from paypal_events
            where event_id in ('WH-REFUND-BEFORE-TARGET', 'WH-STALE-COMPLETION')
            order by event_id
            """
        ).fetchall()
    assert [(row["resource_kind"], row["terminal"]) for row in states] == [
        ("capture", 1),
        ("order", 1),
    ]
    assert [(row["event_id"], row["disposition"]) for row in events] == [
        ("WH-REFUND-BEFORE-TARGET", "applied"),
        ("WH-STALE-COMPLETION", "terminal_blocked"),
    ]


def test_order_only_terminal_event_resolves_and_tombstones_capture_alias(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-RESOLVED-FROM-ORDER"
    order_id = "ORDER-TERMINAL-ONLY"
    order = _paypal_order(order_id, capture_id=capture_id)
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda _order_id: order,
    )
    client = TestClient(module.app)

    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-ORDER-ONLY-TERMINAL",
            "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {
                "id": "REFUND-ORDER-ONLY",
                "supplementary_data": {
                    "related_ids": {"order_id": order_id}
                },
            },
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["processed"] is True
    with module.db() as conn:
        states = conn.execute(
            """
            select resource_kind, resource_id, terminal
              from paypal_resource_states
             where resource_id in (?, ?)
             order by resource_kind
            """,
            (capture_id, order_id),
        ).fetchall()
    assert [
        (row["resource_kind"], row["resource_id"], row["terminal"])
        for row in states
    ] == [
        ("capture", capture_id, 1),
        ("order", order_id, 1),
    ]


def test_order_tombstone_rolls_back_partial_capture_projection(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-ORDER-TOMBSTONE"
    order_id = "ORDER-ONLY-TOMBSTONE"
    capture = _paypal_capture(
        capture_id,
        order_id=order_id,
        update_time="2025-01-01T00:00:00.000000Z",
    )
    order = _paypal_order(order_id, capture_id=capture_id)
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda _capture_id: capture,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda _order_id: order,
    )
    client = TestClient(module.app)

    with module.db() as conn:
        assert module._revoke_paypal_onetime_license(
            conn,
            None,
            order_id,
            "PAYMENT.CAPTURE.REFUNDED",
            1_760_000_000,
            authoritative_time_us=module._parse_paypal_ordering_timestamp(
                "2025-01-02T00:00:00.000000Z"
            ),
            state_source_id="TEST-ORDER-TOMBSTONE",
        )
    completion = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-COMPLETION-BLOCKED-BY-ORDER",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "create_time": "2025-01-01T00:00:00.000000Z",
            "resource": {"id": capture_id},
        },
    )

    assert completion.status_code == 200
    assert completion.json()["processed"] is False
    with module.db() as conn:
        capture_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='capture' and resource_id=?
            """,
            (capture_id,),
        ).fetchone()
        order_state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='order' and resource_id=?
            """,
            (order_id,),
        ).fetchone()
        completion_event = conn.execute(
            "select disposition from paypal_events where event_id=?",
            ("WH-COMPLETION-BLOCKED-BY-ORDER",),
        ).fetchone()
    assert capture_state is None
    assert int(order_state["terminal"]) == 1
    assert completion_event["disposition"] == "terminal_blocked"


def test_subscription_webhooks_are_monotonic_and_allow_newer_reactivation(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription_id = "I-ORDERED-SUBSCRIPTION"
    snapshots = iter(
        (
            _paypal_subscription(
                subscription_id,
                status="SUSPENDED",
                update_time="2025-01-02T00:00:00.000000Z",
                status_update_time="2025-01-02T00:00:00.000000Z",
            ),
            _paypal_subscription(
                subscription_id,
                status="ACTIVE",
                update_time="2025-01-01T00:00:00.000000Z",
                status_update_time="2025-01-01T00:00:00.000000Z",
            ),
            _paypal_subscription(
                subscription_id,
                status="ACTIVE",
                update_time="2025-01-03T00:00:00.000000Z",
                status_update_time="2025-01-03T00:00:00.000000Z",
            ),
            _paypal_subscription(
                subscription_id,
                status="ACTIVE",
                update_time="2025-01-02T12:00:00.000000Z",
                status_update_time="2025-01-02T12:00:00.000000Z",
            ),
        )
    )
    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    monkeypatch.setattr(module, "_fetch_paypal_subscription", lambda _subscription_id: next(snapshots))
    client = TestClient(module.app)

    suspended = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-SUSPENDED-NEWER",
            "event_type": "BILLING.SUBSCRIPTION.SUSPENDED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )
    stale_active = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-ACTIVE-OLDER",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "create_time": "2025-01-01T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )
    duplicate_stale = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-ACTIVE-OLDER",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "create_time": "2025-01-01T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )
    row_after_stale = _fetch_license_by_subscription(module.DB_PATH, subscription_id)
    reactivated = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-REACTIVATED-NEWEST",
            "event_type": "BILLING.SUBSCRIPTION.RE-ACTIVATED",
            "create_time": "2025-01-03T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )
    stale_same_state = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-ACTIVE-STALE-SAME-STATE",
            "event_type": "BILLING.SUBSCRIPTION.UPDATED",
            "create_time": "2025-01-04T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )

    assert suspended.status_code == 200
    assert suspended.json()["processed"] is True
    assert stale_active.status_code == 200
    assert stale_active.json()["processed"] is False
    assert duplicate_stale.status_code == 200
    assert duplicate_stale.json()["duplicate"] is True
    assert row_after_stale["status"] == "suspended"
    assert reactivated.status_code == 200
    assert reactivated.json()["processed"] is True
    assert stale_same_state.status_code == 200
    assert stale_same_state.json()["processed"] is False
    final_row = _fetch_license_by_subscription(module.DB_PATH, subscription_id)
    assert final_row["status"] == "active"
    with module.db() as conn:
        state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
        stale_event = conn.execute(
            "select disposition from paypal_events where event_id=?",
            ("WH-SUB-ACTIVE-STALE-SAME-STATE",),
        ).fetchone()
    assert state["source_id"] == "WH-SUB-REACTIVATED-NEWEST"
    assert state["state_status"] == "ACTIVE:active:0"
    assert stale_event["disposition"] == "ignored_stale"


@pytest.mark.parametrize(
    ("first_status", "second_status", "second_processed", "disposition"),
    (
        ("ACTIVE", "SUSPENDED", True, "applied"),
        ("SUSPENDED", "ACTIVE", False, "ignored_stale"),
    ),
)
def test_same_subscription_clock_always_resolves_to_restrictive_state(
    monkeypatch,
    tmp_path,
    first_status,
    second_status,
    second_processed,
    disposition,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription_id = (
        f"I-SAME-CLOCK-{first_status[:3]}-{second_status[:3]}"
    )
    same_clock = "2025-01-10T00:00:00.000000Z"
    snapshots = iter(
        (
            _paypal_subscription(
                subscription_id,
                status=first_status,
                update_time=same_clock,
                status_update_time=same_clock,
            ),
            _paypal_subscription(
                subscription_id,
                status=second_status,
                update_time=same_clock,
                status_update_time=same_clock,
            ),
        )
    )
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda _subscription_id: next(snapshots),
    )
    client = TestClient(module.app)
    event_type = {
        "ACTIVE": "BILLING.SUBSCRIPTION.ACTIVATED",
        "SUSPENDED": "BILLING.SUBSCRIPTION.SUSPENDED",
    }

    first = client.post(
        "/paypal/webhook",
        json={
            "id": f"WH-SAME-CLOCK-FIRST-{first_status}",
            "event_type": event_type[first_status],
            "create_time": "2025-02-01T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )
    second_event_id = f"WH-SAME-CLOCK-SECOND-{second_status}"
    second = client.post(
        "/paypal/webhook",
        json={
            "id": second_event_id,
            "event_type": event_type[second_status],
            "create_time": "2025-02-02T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )

    assert first.status_code == 200, first.text
    assert first.json()["processed"] is True
    assert second.status_code == 200, second.text
    assert second.json()["processed"] is second_processed
    row = _fetch_license_by_subscription(module.DB_PATH, subscription_id)
    assert row["status"] == "suspended"
    with module.db() as conn:
        state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
        event = conn.execute(
            "select disposition from paypal_events where event_id=?",
            (second_event_id,),
        ).fetchone()
    assert int(state["state_rank"]) == 30
    assert state["state_status"] == "SUSPENDED:suspended:0"
    assert event["disposition"] == disposition


def test_subscription_migration_is_provisional_until_fresh_paypal_snapshot(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription_id = "I-MIGRATED-SUSPENDED"
    with module.db() as conn:
        conn.execute(
            """
            insert into licenses (
              license_key, plan, max_devices, active, issued_at, kind, status,
              current_period_end, cancel_at_period_end,
              paypal_subscription_id, paypal_plan_id, paypal_status
            ) values (
              'MIGRATED-SUB-KEY', 'pro', 1, 1, 100, 'subscription',
              'suspended', 4075403400, 0, ?, ?, 'SUSPENDED'
            )
            """,
            (subscription_id, PLAN_ID),
        )
    module.init_db()
    with module.db() as conn:
        provisional = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
    assert int(provisional["provisional"]) == 1
    assert int(provisional["state_time_us"]) == 0

    fresh = _paypal_subscription(
        subscription_id,
        status="ACTIVE",
        update_time="2025-02-01T00:00:00.000000Z",
        status_update_time="2025-02-01T00:00:00.000000Z",
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda _subscription_id: fresh,
    )
    client = TestClient(module.app)
    activated = client.post(
        "/license/activate-paypal",
        json={
            "subscriptionId": subscription_id,
            "deviceId": "migrated-device",
        },
    )

    assert activated.status_code == 200, activated.text
    row = _fetch_license_by_subscription(module.DB_PATH, subscription_id)
    assert row["status"] == "active"
    with module.db() as conn:
        reconciled = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
    assert int(reconciled["provisional"]) == 0
    assert reconciled["state_status"] == "ACTIVE:active:0"


def test_subscription_general_update_clock_advances_billing_period(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription_id = "I-BILLING-CLOCK"
    first = _paypal_subscription(
        subscription_id,
        status="ACTIVE",
        status_update_time="2025-01-01T00:00:00.000000Z",
        update_time="2025-01-02T00:00:00.000000Z",
    )
    second = _paypal_subscription(
        subscription_id,
        status="ACTIVE",
        status_update_time="2025-01-01T00:00:00.000000Z",
        update_time="2025-01-03T00:00:00.000000Z",
    )
    second["billing_info"]["next_billing_time"] = "2099-07-23T12:30:00Z"

    with module.db() as conn:
        module._upsert_paypal_subscription_license(conn, first)
    with module.db() as conn:
        module._upsert_paypal_subscription_license(conn, second)
    row = _fetch_license_by_subscription(module.DB_PATH, subscription_id)
    expected_period_end = int(
        dt.datetime(
            2099,
            7,
            23,
            12,
            30,
            tzinfo=dt.timezone.utc,
        ).timestamp()
    )
    assert int(row["current_period_end"]) == expected_period_end
    with module.db() as conn:
        state = conn.execute(
            """
            select * from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
    assert int(state["provider_status_time_us"]) == (
        module._parse_paypal_ordering_timestamp(
            "2025-01-01T00:00:00.000000Z"
        )
    )
    assert int(state["provider_update_time_us"]) == (
        module._parse_paypal_ordering_timestamp(
            "2025-01-03T00:00:00.000000Z"
        )
    )


def test_paypal_activation_fails_closed_without_resource_ordering_time(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription = _paypal_subscription("I-NO-ORDERING-TIME")
    subscription.pop("update_time")
    capture = _paypal_capture("CAPTURE-NO-ORDERING", order_id="ORDER-NO-ORDERING")
    capture.pop("update_time")
    monkeypatch.setattr(module, "_fetch_paypal_subscription", lambda _subscription_id: subscription)
    monkeypatch.setattr(module, "_fetch_paypal_capture", lambda _capture_id: capture)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda _order_id: _paypal_order(
            "ORDER-NO-ORDERING",
            capture_id="CAPTURE-NO-ORDERING",
        ),
    )
    client = TestClient(module.app)

    subscription_response = client.post(
        "/license/activate-paypal",
        json={"subscriptionId": "I-NO-ORDERING-TIME", "deviceId": "device-1"},
    )
    capture_response = client.post(
        "/license/activate-paypal-purchase",
        json={"paypalId": "CAPTURE-NO-ORDERING", "deviceId": "device-1"},
    )

    assert subscription_response.status_code == 502
    assert subscription_response.json()["detail"] == "paypal-subscription-state-time-missing"
    assert capture_response.status_code == 502
    assert capture_response.json()["detail"] == "paypal-capture-state-time-missing"


def test_subscription_webhook_missing_resource_clocks_rolls_back_claim(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    subscription_id = "I-WEBHOOK-NO-RESOURCE-CLOCK"
    subscription = _paypal_subscription(subscription_id)
    subscription.pop("update_time")
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda _subscription_id: subscription,
    )
    client = TestClient(module.app)

    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-SUB-NO-RESOURCE-CLOCK",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {"id": subscription_id},
        },
    )

    assert response.status_code == 502
    assert (
        response.json()["detail"]
        == "paypal-subscription-state-time-missing"
    )
    with module.db() as conn:
        event = conn.execute(
            "select 1 from paypal_events where event_id=?",
            ("WH-SUB-NO-RESOURCE-CLOCK",),
        ).fetchone()
        state = conn.execute(
            """
            select 1 from paypal_resource_states
            where resource_kind='subscription' and resource_id=?
            """,
            (subscription_id,),
        ).fetchone()
        license_row = conn.execute(
            "select 1 from licenses where paypal_subscription_id=?",
            (subscription_id,),
        ).fetchone()
    assert event is None
    assert state is None
    assert license_row is None


def test_completed_capture_webhook_missing_resource_clock_rolls_back_claim(
    monkeypatch,
    tmp_path,
):
    module = _load_module(monkeypatch, tmp_path)
    capture_id = "CAPTURE-WEBHOOK-NO-CLOCK"
    order_id = "ORDER-WEBHOOK-NO-CLOCK"
    capture = _paypal_capture(capture_id, order_id=order_id)
    capture.pop("update_time")
    order = _paypal_order(order_id, capture_id=capture_id)
    monkeypatch.setattr(
        module,
        "_verify_paypal_webhook_signature",
        lambda _request, _event: None,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda _capture_id: capture,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda _order_id: order,
    )
    client = TestClient(module.app)

    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-CAPTURE-NO-RESOURCE-CLOCK",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {"id": capture_id},
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "paypal-capture-state-time-missing"
    with module.db() as conn:
        event = conn.execute(
            "select 1 from paypal_events where event_id=?",
            ("WH-CAPTURE-NO-RESOURCE-CLOCK",),
        ).fetchone()
        states = conn.execute(
            """
            select 1 from paypal_resource_states
            where (resource_kind='capture' and resource_id=?)
               or (resource_kind='order' and resource_id=?)
            """,
            (capture_id, order_id),
        ).fetchall()
        license_row = conn.execute(
            "select 1 from licenses where paypal_capture_id=?",
            (capture_id,),
        ).fetchone()
    assert event is None
    assert states == []
    assert license_row is None


def test_activate_paypal_subscription_creates_license_and_returns_signed_token(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda subscription_id: _paypal_subscription(subscription_id),
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/activate-paypal",
        json={
            "subscriptionId": "I-SUBSCRIPTION-123",
            "deviceId": "device-1",
            "email": "typed@example.com",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "licenseKey" not in body
    payload = module.parse_and_verify_token(body["token"])
    assert payload["kind"] == "subscription"
    assert payload["plan"] == "premium-desktop-monthly"
    assert payload["device"] == "device-1"

    row = _fetch_license_by_subscription(module.DB_PATH, "I-SUBSCRIPTION-123")
    assert row is not None
    assert row["license_key"] == payload["lic"]
    assert row["kind"] == "subscription"
    assert row["status"] == "active"
    assert row["owner_email"] == "buyer@example.com"
    assert row["paypal_plan_id"] == PLAN_ID
    assert row["paypal_payer_id"] == "PAYER-123"
    assert row["current_period_end"] == int(
        dt.datetime(2099, 6, 23, 12, 30, tzinfo=dt.timezone.utc).timestamp()
    )

    conn = sqlite3.connect(module.DB_PATH)
    try:
        activation = conn.execute(
            "select device_id from activations where license_key=?",
            (payload["lic"],),
        ).fetchone()
    finally:
        conn.close()
    assert activation[0] == "device-1"


def test_paypal_webhook_upserts_subscription_license_once(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    verified_events = []
    fetch_count = 0

    def fake_verify(_request, event):
        verified_events.append(event["id"])

    def fake_fetch(subscription_id):
        nonlocal fetch_count
        fetch_count += 1
        return _paypal_subscription(subscription_id)

    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", fake_verify)
    monkeypatch.setattr(module, "_fetch_paypal_subscription", fake_fetch)
    client = TestClient(module.app)

    event = {
        "id": "WH-EVENT-1",
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "create_time": "2025-01-02T00:00:00.000000Z",
        "resource": {"id": "I-WEBHOOK-123"},
    }

    first = client.post("/paypal/webhook", json=event)
    second = client.post("/paypal/webhook", json=event)

    assert first.status_code == 200, first.text
    assert first.json()["processed"] is True
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    assert verified_events == ["WH-EVENT-1", "WH-EVENT-1"]
    assert fetch_count == 1

    row = _fetch_license_by_subscription(module.DB_PATH, "I-WEBHOOK-123")
    assert row is not None
    assert row["kind"] == "subscription"
    assert row["status"] == "active"


def test_activate_paypal_purchase_accepts_website_subscription_plan(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda subscription_id: _paypal_subscription(subscription_id, plan_id=WEBSITE_PLAN_ID),
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/activate-paypal-purchase",
        json={
            "paypalId": "I-WEBSITE-123",
            "deviceId": "device-website",
            "email": "website-buyer@example.com",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "licenseKey" not in body
    payload = module.parse_and_verify_token(body["token"])
    assert payload["kind"] == "subscription"
    assert payload["device"] == "device-website"

    row = _fetch_license_by_subscription(module.DB_PATH, "I-WEBSITE-123")
    assert row is not None
    assert row["owner_email"] == "buyer@example.com"
    assert row["paypal_plan_id"] == WEBSITE_PLAN_ID


@pytest.mark.parametrize(
    "api_base",
    (
        "https://api-m.paypal.com",
        "https://api-m.sandbox.paypal.com",
    ),
)
def test_activate_paypal_purchase_accepts_one_time_capture(
    monkeypatch,
    tmp_path,
    api_base,
):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setenv("PAYPAL_API_BASE", api_base)
    monkeypatch.setenv("PAYPAL_ONETIME_PRODUCT_ID", "VOX-STELLA-LIFETIME")
    monkeypatch.setenv("PAYPAL_ONETIME_CUSTOM_ID", "voxstella-lifetime")
    monkeypatch.setenv("PAYPAL_ONETIME_INVOICE_ID_PREFIX", "VS-250-")
    monkeypatch.setenv("PAYPAL_PAYEE_MERCHANT_ID", "MERCHANT-VOX-STELLA")
    monkeypatch.setenv("PAYPAL_PAYEE_EMAIL", "billing@voxstella.example")
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda capture_id: _paypal_capture(capture_id),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda order_id: _paypal_order(order_id),
        raising=False,
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/activate-paypal-purchase",
        json={
            "paypalId": "CAPTURE-250",
            "deviceId": "device-onetime",
            "email": "attacker-controlled@example.com",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    payload = module.parse_and_verify_token(body["token"])
    assert payload["kind"] == "perpetual"
    assert payload["plan"] == "premium-desktop-lifetime"
    assert payload["device"] == "device-onetime"

    row = _fetch_license_by_capture(module.DB_PATH, "CAPTURE-250")
    assert row is not None
    assert row["kind"] == "perpetual"
    assert row["owner_email"] == "one-time-buyer@example.com"
    assert row["paypal_capture_id"] == "CAPTURE-250"
    assert row["paypal_order_id"] == "ORDER-250"


def test_paypal_webhook_creates_one_time_license_from_capture_event(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "_verify_paypal_webhook_signature", lambda _request, _event: None)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda capture_id: _paypal_capture(
            capture_id,
            order_id="ORDER-WEBHOOK-250",
        ),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda order_id: {
            **_paypal_order(
                order_id,
                capture_id="CAPTURE-WEBHOOK-250",
            ),
            "payer": {
                "email_address": "webhook-buyer@example.com",
                "payer_id": "PAYER-WEBHOOK",
            },
        },
        raising=False,
    )
    client = TestClient(module.app)

    response = client.post(
        "/paypal/webhook",
        json={
            "id": "WH-ONETIME-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "create_time": "2025-01-02T00:00:00.000000Z",
            "resource": {"id": "CAPTURE-WEBHOOK-250"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["processed"] is True
    assert "licenseKey" not in body

    row = _fetch_license_by_capture(module.DB_PATH, "CAPTURE-WEBHOOK-250")
    assert row is not None
    assert row["kind"] == "perpetual"
    assert row["owner_email"] == "webhook-buyer@example.com"


@pytest.mark.parametrize(
    "api_base",
    (
        "https://api-m.paypal.com",
        "https://api-m.sandbox.paypal.com",
    ),
)
@pytest.mark.parametrize(
    ("blank_names", "expected_detail"),
    [
        (
            (
                "PAYPAL_PAYEE_MERCHANT_ID",
                "PAYPAL_ONETIME_PAYEE_MERCHANT_ID",
            ),
            "paypal-onetime-merchant-binding-not-configured",
        ),
        (
            (
                "PAYPAL_ONETIME_PRODUCT_ID",
                "PAYPAL_ONETIME_EXPECTED_PRODUCT_ID",
                "PAYPAL_ONETIME_CUSTOM_ID",
                "PAYPAL_ONETIME_EXPECTED_CUSTOM_ID",
                "PAYPAL_ONETIME_CUSTOM_ID_PREFIX",
                "PAYPAL_ONETIME_INVOICE_ID",
                "PAYPAL_ONETIME_EXPECTED_INVOICE_ID",
                "PAYPAL_ONETIME_INVOICE_ID_PREFIX",
            ),
            "paypal-onetime-purchase-binding-not-configured",
        ),
    ],
)
def test_one_time_capture_fails_closed_without_identity_contract(
    monkeypatch,
    tmp_path,
    api_base,
    blank_names,
    expected_detail,
):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setenv("PAYPAL_API_BASE", api_base)
    for name in blank_names:
        monkeypatch.setenv(name, "")

    with pytest.raises(module.HTTPException) as exc_info:
        module._assert_paypal_onetime_allowed(
            _paypal_capture(),
            _paypal_order(),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == expected_detail


@pytest.mark.parametrize(
    "api_base",
    (
        "https://api-m.paypal.com",
        "https://api-m.sandbox.paypal.com",
    ),
)
def test_purchase_endpoint_issues_no_license_without_identity_contract(
    monkeypatch,
    tmp_path,
    api_base,
):
    module = _load_module(monkeypatch, tmp_path)
    for name in (
        "PAYPAL_PAYEE_MERCHANT_ID",
        "PAYPAL_ONETIME_PAYEE_MERCHANT_ID",
        "PAYPAL_ONETIME_PRODUCT_ID",
        "PAYPAL_ONETIME_EXPECTED_PRODUCT_ID",
        "PAYPAL_ONETIME_CUSTOM_ID",
        "PAYPAL_ONETIME_EXPECTED_CUSTOM_ID",
        "PAYPAL_ONETIME_CUSTOM_ID_PREFIX",
        "PAYPAL_ONETIME_INVOICE_ID",
        "PAYPAL_ONETIME_EXPECTED_INVOICE_ID",
        "PAYPAL_ONETIME_INVOICE_ID_PREFIX",
    ):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("PAYPAL_API_BASE", api_base)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_capture",
        lambda capture_id: _paypal_capture(capture_id),
    )
    monkeypatch.setattr(
        module,
        "_fetch_paypal_order",
        lambda order_id: _paypal_order(order_id),
    )

    response = TestClient(module.app).post(
        "/license/activate-paypal-purchase",
        json={"paypalId": "CAPTURE-250", "deviceId": "device-attacker"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "paypal-onetime-merchant-binding-not-configured"
    assert _fetch_license_by_capture(module.DB_PATH, "CAPTURE-250") is None


@pytest.mark.parametrize(
    ("env_name", "env_value", "expected_detail"),
    [
        ("PAYPAL_ONETIME_PRODUCT_ID", "ANOTHER-PRODUCT", "paypal-capture-product-mismatch"),
        ("PAYPAL_ONETIME_CUSTOM_ID", "another-custom-id", "paypal-capture-custom-id-mismatch"),
        ("PAYPAL_ONETIME_INVOICE_ID", "ANOTHER-INVOICE", "paypal-capture-invoice-id-mismatch"),
        ("PAYPAL_PAYEE_MERCHANT_ID", "ANOTHER-MERCHANT", "paypal-capture-payee-mismatch"),
        ("PAYPAL_PAYEE_EMAIL", "attacker@example.com", "paypal-capture-payee-mismatch"),
    ],
)
def test_one_time_capture_rejects_configured_identity_mismatch(
    monkeypatch,
    tmp_path,
    env_name,
    env_value,
    expected_detail,
):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(module.HTTPException) as exc_info:
        module._assert_paypal_onetime_allowed(
            _paypal_capture(),
            _paypal_order(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail


def test_one_time_capture_rejects_order_that_does_not_contain_capture(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)

    with pytest.raises(module.HTTPException) as exc_info:
        module._assert_paypal_onetime_allowed(
            _paypal_capture(),
            _paypal_order(capture_id="A-DIFFERENT-CAPTURE"),
        )

    assert exc_info.value.detail == "paypal-capture-order-mismatch"


def test_subscription_activation_rejects_unapproved_plan(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(
        module,
        "_fetch_paypal_subscription",
        lambda subscription_id: _paypal_subscription(
            subscription_id,
            plan_id="P-ATTACKER-CONTROLLED",
        ),
    )
    client = TestClient(module.app)

    response = client.post(
        "/license/activate-paypal",
        json={"subscriptionId": "I-BAD-PLAN", "deviceId": "device-1"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "paypal-plan-mismatch"


def test_subscription_activation_requires_authoritative_paid_through(monkeypatch, tmp_path):
    module = _load_module(monkeypatch, tmp_path)
    subscription = _paypal_subscription("I-NO-PAID-THROUGH")
    subscription["billing_info"] = {}
    monkeypatch.setattr(module, "_fetch_paypal_subscription", lambda _subscription_id: subscription)
    client = TestClient(module.app)

    response = client.post(
        "/license/activate-paypal",
        json={"subscriptionId": "I-NO-PAID-THROUGH", "deviceId": "device-1"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "paypal-subscription-period-missing"


@pytest.mark.parametrize(
    ("path", "payload", "expected_detail"),
    [
        (
            "/license/activate-paypal",
            {"subscriptionId": "I-../../v1/oauth2/token", "deviceId": "device-1"},
            "invalid-paypal-subscription-id",
        ),
        (
            "/license/activate-paypal-purchase",
            {"paypalId": "../orders?capture=other", "deviceId": "device-1"},
            "invalid-paypal-capture-id",
        ),
    ],
)
def test_paypal_activation_rejects_resource_id_path_injection(
    monkeypatch,
    tmp_path,
    path,
    payload,
    expected_detail,
):
    module = _load_module(monkeypatch, tmp_path)

    def unexpected_api_call(*_args, **_kwargs):
        raise AssertionError("Invalid resource IDs must be rejected before calling PayPal")

    monkeypatch.setattr(module, "_paypal_api_request", unexpected_api_call)
    response = TestClient(module.app).post(path, json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
