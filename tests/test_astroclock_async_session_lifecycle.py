from __future__ import annotations

import sys
import threading
import types
from pathlib import Path

import pytest
from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def test_bounded_daemon_executor_rejects_work_beyond_running_and_queue_capacity():
    executor = astro_clock_api._BoundedDaemonExecutor(max_workers=1, max_queue=1)
    first_started = threading.Event()
    release_first = threading.Event()
    second_completed = threading.Event()

    def first_job():
        first_started.set()
        release_first.wait(timeout=5)

    try:
        assert executor.submit("first", first_job) is True
        assert first_started.wait(timeout=2)
        assert executor.submit("second", second_completed.set) is True
        assert executor.submit("third", lambda: None) is False

        snapshot = executor.snapshot()
        assert snapshot["workers"] == 1
        assert snapshot["queue_capacity"] == 1
        assert snapshot["accepted"] == 2
        assert snapshot["rejected"] == 1
        assert snapshot["running"] == 1
        assert snapshot["queued"] == 1
    finally:
        release_first.set()

    try:
        assert second_completed.wait(timeout=2)
    finally:
        executor.shutdown(wait=True)
    assert executor.snapshot()["closed"] is True


def test_initialize_background_session_refuses_to_exceed_active_session_cap():
    sessions = {
        "active": {
            "session_id": "active",
            "created_at": 1.0,
            "updated_at": 1.0,
            "ready": False,
            "failed": False,
        }
    }
    lock = threading.Lock()

    initialized = astro_clock_api._initialize_background_session(
        sessions,
        lock,
        "new",
        {"ready": False, "failed": False},
        is_terminal=lambda session: bool(session.get("ready") or session.get("failed")),
        max_sessions=1,
        ttl_seconds=60.0,
    )

    assert initialized is False
    assert set(sessions) == {"active"}


@pytest.mark.parametrize(
    ("store_name", "prune_name"),
    [
        ("_atlas_search_sessions", "_prune_atlas_search_sessions_locked"),
        ("_weather_scan_sessions", "_prune_weather_scan_sessions_locked"),
        ("_mundane_scan_sessions", "_prune_mundane_scan_sessions_locked"),
        ("_research_sessions", "_prune_research_sessions_locked"),
    ],
)
def test_workflow_session_pruning_expires_terminal_state_but_preserves_active(
    monkeypatch,
    store_name,
    prune_name,
):
    sessions = {
        "expired": {
            "session_id": "expired",
            "ready": True,
            "failed": False,
            "created_at": 1.0,
            "updated_at": 1.0,
        },
        "active": {
            "session_id": "active",
            "ready": False,
            "failed": False,
            "running": True,
            "created_at": 1.0,
            "updated_at": 1.0,
        },
    }
    monkeypatch.setattr(astro_clock_api, store_name, sessions)

    getattr(astro_clock_api, prune_name)(now=10_000.0)

    assert "expired" not in sessions
    assert "active" in sessions


def test_atlas_start_reports_retryable_capacity_failure(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_atlas_search_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_submit_background_job", lambda *_args, **_kwargs: False)
    client = _make_app().test_client()

    response = client.post("/api/astro-clock/astrocartography/atlas-search/start", json={})

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["retryable"] is True
    assert payload["runtime"]["restart_volatile"] is True
    stored = list(astro_clock_api._atlas_search_sessions.values())
    assert len(stored) == 1
    assert stored[0]["failed"] is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/astro-clock/astrocartography/atlas-search/progress?session_id=missing",
        "/api/astro-clock/weather/scan/progress?session_id=missing",
        "/api/astro-clock/mundane/scan/progress?session_id=missing",
    ],
)
def test_missing_process_local_session_is_explicitly_restart_volatile(monkeypatch, path):
    monkeypatch.setattr(astro_clock_api, "_atlas_search_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_weather_scan_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_mundane_scan_sessions", {})
    client = _make_app().test_client()

    response = client.get(path)

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["restart_volatile"] is True
    assert "backend restarts" in payload["error"]


def test_background_runtime_status_reports_executor_and_session_counts(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_atlas_search_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_weather_scan_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_mundane_scan_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_research_sessions", {})
    client = _make_app().test_client()

    response = client.get("/api/astro-clock/runtime/background")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["restart_volatile"] is True
    assert payload["session_persistence"] == "process_memory"
    assert payload["executor"]["workers"] >= 1
    assert payload == astro_clock_api.get_background_runtime_metrics()
    assert payload["sessions"]["research_compile"] == {
        "total": 0,
        "active": 0,
        "terminal": 0,
    }


def test_research_compile_deduplicates_active_session_before_using_stale_cache(
    monkeypatch,
    tmp_path,
):
    session_id = "same-session"
    active = {
        "session_id": session_id,
        "ready": False,
        "failed": False,
        "running": True,
        "stage": "running",
        "done": 3,
        "total": 10,
        "created_at": 1.0,
        "updated_at": 1.0,
    }
    monkeypatch.setattr(astro_clock_api, "_research_sessions", {session_id: active})
    monkeypatch.setattr(astro_clock_api, "_research_session_id", lambda *_args: session_id)
    monkeypatch.setattr(astro_clock_api, "_ensure_research_cache_dir", lambda: tmp_path)
    (tmp_path / f"{session_id}.json").write_text('{"rows": [{"date": "old"}]}', encoding="utf-8")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("duplicate request must not submit another worker")

    monkeypatch.setattr(astro_clock_api, "_submit_background_job", fail_submit)

    returned_id, progress = astro_clock_api._start_research_compile({})

    assert returned_id == session_id
    assert progress["running"] is True
    assert progress["done"] == 3
    assert astro_clock_api._research_sessions[session_id] is active
    assert "source" not in active


def test_research_progress_reports_lost_process_local_session(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_research_sessions", {})
    monkeypatch.setattr(astro_clock_api, "_research_mode_enabled", lambda: True)
    client = _make_app().test_client()

    response = client.get("/api/astro-clock/research/lotto/progress?session_id=missing")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["restart_volatile"] is True


def test_location_route_commits_resolved_context_atomically(monkeypatch):
    class StubEngine:
        def __init__(self):
            self.settings = types.SimpleNamespace(
                location="Old Place",
                timezone="Old/Timezone",
                latitude=1.0,
                longitude=2.0,
            )
            self.updates = []

        def update_settings(self, **updates):
            self.updates.append(dict(updates))
            for key, value in updates.items():
                setattr(self.settings, key, value)

    engine = StubEngine()

    def resolve_coords(location, **_kwargs):
        assert location == "New Place"
        assert engine.settings.location == "Old Place"
        return 31.7683, 35.2137

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", resolve_coords)
    monkeypatch.setattr(
        astro_clock_api,
        "_tz_instance",
        lambda: types.SimpleNamespace(
            get_timezone_for_location=lambda _lat, _lon: "Asia/Jerusalem"
        ),
    )
    client = _make_app().test_client()

    response = client.post(
        "/api/astro-clock/location",
        json={"location": "New Place"},
    )

    assert response.status_code == 200
    assert engine.updates == [
        {
            "location": "New Place",
            "latitude": 31.7683,
            "longitude": 35.2137,
            "timezone": "Asia/Jerusalem",
        }
    ]
    payload = response.get_json()["data"]
    assert payload["location"] == "New Place"
    assert payload["timezone"] == "Asia/Jerusalem"
