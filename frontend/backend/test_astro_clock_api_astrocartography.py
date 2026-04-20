from pathlib import Path
import os
import sys
import threading
import time

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import astrocartography_service


def _clear_atlas_sessions():
    with astro_clock_api._atlas_search_lock:
        astro_clock_api._atlas_search_sessions.clear()


def test_astrocartography_map_degrades_when_global_parans_fail(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_bundle_from_query",
        lambda args: {"meta": {"timestamp": "2024-01-01T00:00:00Z"}},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_transit_bundle_from_query",
        lambda args, natal_meta=None: None,
    )
    monkeypatch.setattr(
        astrocartography_service,
        "build_astrocartography_lines",
        lambda timestamp_iso, bodies=None, angles=None: {
            "bodies": ["Sun"],
            "angles": ["MC"],
            "lines": [
                {
                    "id": "Sun:MC",
                    "body": "Sun",
                    "angle": "MC",
                    "label": "Sun MC",
                    "color": "#f59e0b",
                    "segments": [[[-89.0, 0.0], [89.0, 0.0]]],
                }
            ],
        },
    )

    def _explode(*args, **kwargs):
        raise RuntimeError("global paran failure")

    monkeypatch.setattr(astrocartography_service, "build_global_paran_tracks", _explode)

    response = client.get("/api/astro-clock/astrocartography/map")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["map"]["natal_lines"]
    assert payload["data"]["map"]["global_parans"]["track_count"] == 0
    assert payload["data"]["map"]["global_parans"]["degraded"] is True


def test_astrocartography_atlas_search_async_session_returns_progress_and_result(monkeypatch):
    client = app_module.app.test_client()
    _clear_atlas_sessions()

    monkeypatch.setattr(
        astro_clock_api,
        "_run_astrocartography_atlas_search",
        lambda params, progress_callback=None, should_continue=None: (
            progress_callback and progress_callback(
                {
                    "stage": "score_candidates",
                    "percent": 0.6,
                    "message": "Scoring atlas candidates",
                    "done": 4,
                    "total": 8,
                    "candidate_count": 8,
                    "shortlisted_count": 4,
                }
            ),
            {
                "goal": {"id": "home", "label": "Home", "summary": "Test summary"},
                "atlas": {"candidate_count": 8, "shortlisted_count": 4, "viable_count": 2},
                "results": [{"target": {"label": "Paris, France"}, "location_score": {"score": 77}}],
                "ranking": [{"rank": 1, "label": "Paris, France", "score": 77}],
            },
        )[1],
    )

    start = client.post(
        "/api/astro-clock/astrocartography/atlas-search/start",
        json={"goal_id": "home", "natal_snap_id": "snap-1"},
    )
    start_payload = start.get_json()

    assert start.status_code == 200
    assert start_payload["success"] is True
    session_id = start_payload["data"]["session_id"]
    assert session_id

    progress_payload = None
    result_payload = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        progress_response = client.get(f"/api/astro-clock/astrocartography/atlas-search/progress?session_id={session_id}")
        progress_payload = progress_response.get_json()
        if progress_payload["data"]["ready"]:
            result_response = client.get(f"/api/astro-clock/astrocartography/atlas-search/result?session_id={session_id}")
            result_payload = result_response.get_json()
            break
        time.sleep(0.02)

    assert progress_payload is not None
    assert progress_payload["data"]["stage"] in {"score_candidates", "ready"}
    assert result_payload is not None
    assert result_payload["success"] is True
    assert result_payload["data"]["ready"] is True
    assert result_payload["data"]["result"]["ranking"][0]["label"] == "Paris, France"


def test_astrocartography_atlas_search_cancel_marks_session_cancelled(monkeypatch):
    client = app_module.app.test_client()
    _clear_atlas_sessions()
    entered_search = threading.Event()

    def _run_with_cancel(params, progress_callback=None, should_continue=None):
        if progress_callback is not None:
            progress_callback(
                {
                    "stage": "score_candidates",
                    "percent": 0.35,
                    "message": "Scoring atlas candidates",
                    "done": 3,
                    "total": 12,
                }
            )
        entered_search.set()
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if should_continue is not None:
                should_continue()
            time.sleep(0.01)
        return {"results": [], "ranking": []}

    monkeypatch.setattr(astro_clock_api, "_run_astrocartography_atlas_search", _run_with_cancel)

    start = client.post(
        "/api/astro-clock/astrocartography/atlas-search/start",
        json={"goal_id": "home", "natal_snap_id": "snap-1"},
    )
    start_payload = start.get_json()
    session_id = start_payload["data"]["session_id"]

    assert entered_search.wait(1.0)

    cancel = client.post(
        "/api/astro-clock/astrocartography/atlas-search/cancel",
        json={"session_id": session_id},
    )
    cancel_payload = cancel.get_json()

    assert cancel.status_code == 200
    assert cancel_payload["success"] is True
    assert (
        cancel_payload["data"]["progress"]["cancel_requested"] is True
        or cancel_payload["data"]["progress"]["cancelled"] is True
    )

    progress_payload = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        progress_response = client.get(f"/api/astro-clock/astrocartography/atlas-search/progress?session_id={session_id}")
        progress_payload = progress_response.get_json()
        if progress_payload["data"]["cancelled"]:
            break
        time.sleep(0.02)

    assert progress_payload is not None
    assert progress_payload["data"]["ready"] is True
    assert progress_payload["data"]["cancelled"] is True
    assert progress_payload["data"]["stage"] == "cancelled"

    result_response = client.get(f"/api/astro-clock/astrocartography/atlas-search/result?session_id={session_id}")
    result_payload = result_response.get_json()

    assert result_response.status_code == 200
    assert result_payload["success"] is True
    assert result_payload["data"]["cancelled"] is True
    assert result_payload["data"]["error"] == "Atlas search cancelled"
    assert "result" not in result_payload["data"]


def test_prune_atlas_search_sessions_evicts_expired_terminal_entries(monkeypatch):
    _clear_atlas_sessions()
    monkeypatch.setattr(astro_clock_api, "_ATLAS_SEARCH_SESSION_TTL_SECONDS", 30.0)
    monkeypatch.setattr(astro_clock_api, "_ATLAS_SEARCH_SESSION_MAX", 2)

    with astro_clock_api._atlas_search_lock:
        astro_clock_api._atlas_search_sessions.update(
            {
                "expired-ready": {
                    "session_id": "expired-ready",
                    "ready": True,
                    "updated_at": 10.0,
                    "created_at": 10.0,
                },
                "old-ready": {
                    "session_id": "old-ready",
                    "ready": True,
                    "updated_at": 60.0,
                    "created_at": 60.0,
                },
                "new-ready": {
                    "session_id": "new-ready",
                    "ready": True,
                    "updated_at": 95.0,
                    "created_at": 95.0,
                },
                "active-run": {
                    "session_id": "active-run",
                    "ready": False,
                    "failed": False,
                    "cancelled": False,
                    "updated_at": 99.0,
                    "created_at": 99.0,
                },
            }
        )
        astro_clock_api._prune_atlas_search_sessions_locked(now=100.0)
        remaining = set(astro_clock_api._atlas_search_sessions)

    assert "expired-ready" not in remaining
    assert "old-ready" not in remaining
    assert "new-ready" in remaining
    assert "active-run" in remaining


def test_run_astrocartography_atlas_search_raises_clear_error_when_filters_exclude_goal(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_natal_bundle_from_query",
        lambda args: {"meta": {"timestamp": "2024-01-01T00:00:00Z"}},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_transit_bundle_from_query",
        lambda args, natal_meta=None: None,
    )

    try:
        astro_clock_api._run_astrocartography_atlas_search(
            {
                "goal_id": "gambling_luck",
                "natal_snap_id": "snap-1",
                "body": ["Sun"],
                "angle": ["DSC"],
            }
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Current body/angle filters exclude the selected goal model's atlas signature"


def test_astrocartography_compare_sorts_by_raw_score_before_display_score(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_bundle_from_query",
        lambda args: {"meta": {"timestamp": "2024-01-01T00:00:00Z"}},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_transit_bundle_from_query",
        lambda args, natal_meta=None: None,
    )
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda value: (0.0, 0.0, str(value)),
    )
    monkeypatch.setattr(
        astrocartography_service,
        "build_astrocartography_lines",
        lambda timestamp_iso, bodies=None, angles=None: {
            "bodies": ["Venus"],
            "angles": ["ASC"],
            "lines": [],
        },
    )

    def fake_target_analysis(**kwargs):
        label = str(kwargs.get("resolved_name") or "")
        if label == "Control City":
            raw_score = 0.51
        else:
            raw_score = 0.49
        return {
            "target": {"label": label, "query": label},
            "location_score": {
                "score": 51,
                "raw_score": raw_score,
                "top_supports": [],
                "top_cautions": [],
            },
        }

    monkeypatch.setattr(astro_clock_api, "_astrocartography_target_analysis", fake_target_analysis)

    response = client.get(
        "/api/astro-clock/astrocartography/compare"
        "?target_location=Event%20City&target_location=Control%20City&goal_id=gambling_luck"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert [row["label"] for row in payload["data"]["ranking"]] == ["Control City", "Event City"]
    assert payload["data"]["ranking"][0]["raw_score"] == 0.51
