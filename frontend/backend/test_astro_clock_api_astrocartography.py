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
import astrocartography_goal_engine
import astrocartography_goal_models
import astrocartography_service


def _clear_atlas_sessions():
    with astro_clock_api._atlas_search_lock:
        astro_clock_api._atlas_search_sessions.clear()


def _clear_weather_sessions():
    with astro_clock_api._weather_scan_lock:
        astro_clock_api._weather_scan_sessions.clear()


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


def test_prune_weather_scan_sessions_evicts_expired_terminal_entries(monkeypatch):
    _clear_weather_sessions()
    monkeypatch.setattr(astro_clock_api, "_WEATHER_SCAN_SESSION_TTL_SECONDS", 30.0)
    monkeypatch.setattr(astro_clock_api, "_WEATHER_SCAN_SESSION_MAX", 2)

    with astro_clock_api._weather_scan_lock:
        astro_clock_api._weather_scan_sessions.update(
            {
                "expired-ready": {
                    "session_id": "expired-ready",
                    "ready": True,
                    "updated_at": 10.0,
                    "created_at": 10.0,
                },
                "old-failed": {
                    "session_id": "old-failed",
                    "failed": True,
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
                    "updated_at": 99.0,
                    "created_at": 99.0,
                },
            }
        )
        astro_clock_api._prune_weather_scan_sessions_locked(now=100.0)
        remaining = set(astro_clock_api._weather_scan_sessions)

    assert "expired-ready" not in remaining
    assert "old-failed" not in remaining
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
                    "body": ["Chiron"],
                    "angle": ["NADIR"],
                }
            )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Current body/angle filters exclude the selected goal model's atlas signature"


def test_astrocartography_validation_errors_return_400():
    client = app_module.app.test_client()

    location_response = client.get("/api/astro-clock/astrocartography/location")
    compare_response = client.get("/api/astro-clock/astrocartography/compare?target_location=Paris")
    atlas_response = client.get("/api/astro-clock/astrocartography/atlas-search")

    assert location_response.status_code == 400
    assert location_response.get_json()["error"] == "target_location is required"
    assert compare_response.status_code == 400
    assert compare_response.get_json()["error"] == "At least two target_location values are required"
    assert atlas_response.status_code == 400
    assert atlas_response.get_json()["error"] == "goal_id is required"


def test_astrocartography_direct_goal_filter_validation_matches_atlas_contract():
    try:
        astro_clock_api._validate_astrocartography_goal_filters(
            "gambling_luck",
            bodies=["Chiron"],
            angles=["NADIR"],
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


def test_astrocartography_relocation_uses_resolved_target_coordinates(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        astrocartography_service,
        "build_location_reading",
        lambda *_args, **_kwargs: {"nearest_lines": []},
    )
    monkeypatch.setattr(astrocartography_service, "crossing_candidates_for_point", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(astrocartography_service, "build_intersection_workspace", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astrocartography_service, "build_local_space_workspace", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astrocartography_service, "build_paran_candidates_for_point", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(astrocartography_service, "build_delineation_report", lambda **_kwargs: {"headline": "ok"})
    monkeypatch.setattr(astrocartography_goal_engine, "extract_relocation_features", lambda _chart_data: {"score": 1})
    monkeypatch.setattr(astrocartography_goal_engine, "summarize_relocation_features", lambda _features: {"summary": "ok"})
    monkeypatch.setattr(astrocartography_goal_engine, "evaluate_goal_model", lambda *_args, **_kwargs: {"score": 50})
    monkeypatch.setattr(astrocartography_goal_models, "get_goal_model", lambda goal_id: {"id": goal_id, "label": goal_id, "summary": ""})

    def _fake_bundle(
        dt_iso,
        location,
        timezone_name,
        house_system_code=None,
        latitude=None,
        longitude=None,
        **kwargs,
    ):
        captured.update({
            "dt_iso": dt_iso,
            "location": location,
            "timezone": timezone_name,
            "house_system_code": house_system_code,
            "latitude": latitude,
            "longitude": longitude,
            "include_modern": kwargs.get("include_modern"),
            "include_chiron": kwargs.get("include_chiron"),
        })
        return {
            "chart_data": {},
            "meta": {
                "timestamp": dt_iso,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
            },
        }

    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_bundle)

    result = astro_clock_api._astrocartography_target_analysis(
        target_location="Target City",
        resolved_name="Resolved Target",
        latitude=12.34,
        longitude=56.78,
        natal_meta={"timestamp": "2026-03-22T04:32:00Z"},
        natal_lines_payload={"lines": [], "bodies": ["Sun"]},
        house_system_code="R",
        goal_id="home",
    )

    assert captured["location"] == "Resolved Target"
    assert captured["latitude"] == 12.34
    assert captured["longitude"] == 56.78
    assert captured["house_system_code"] == "R"
    assert captured["include_modern"] is True
    assert captured["include_chiron"] is True
    assert result["relocation"]["meta"]["latitude"] == 12.34
    assert result["relocation"]["meta"]["longitude"] == 56.78


def test_astrocartography_relocation_chart_enrichment_adds_modern_points_and_chiron():
    try:
        import swisseph  # noqa: F401
    except Exception:
        return

    chart_data = {
        "planets": {
            "Sun": {"longitude": 280.0, "house": 1},
            "Moon": {"longitude": 20.0, "house": 2},
        },
        "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
    }
    enriched = astro_clock_api._extend_chart_data_for_synastry(
        chart_data,
        {"timestamp": "2024-01-01T00:00:00+00:00"},
        include_modern=True,
        include_chiron=True,
    )
    planets = enriched.get("planets") or {}

    assert {"Uranus", "Neptune", "Pluto", "Chiron"}.issubset(set(planets))
    assert 0.0 <= float(planets["Chiron"]["longitude"]) < 360.0
    assert planets["Chiron"]["house"] in set(range(1, 13))


def test_astrocartography_goal_scoring_receives_untruncated_line_rows(monkeypatch):
    captured = {}
    lines = [
        {
            "id": f"Body{index}:MC",
            "body": f"Body{index}",
            "angle": "MC",
            "label": f"Body{index} MC",
            "segments": [[[-20.0, float(index)], [20.0, float(index)]]],
        }
        for index in range(9)
    ]

    monkeypatch.setattr(astrocartography_service, "build_intersection_workspace", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astrocartography_service, "build_local_space_workspace", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astrocartography_service, "build_paran_candidates_for_point", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(astrocartography_service, "build_delineation_report", lambda **_kwargs: {"headline": "ok"})
    monkeypatch.setattr(astrocartography_goal_engine, "extract_relocation_features", lambda _chart_data: {"metrics": {}})
    monkeypatch.setattr(astrocartography_goal_engine, "summarize_relocation_features", lambda _features: {"summary": "ok"})
    monkeypatch.setattr(astrocartography_goal_models, "get_goal_model", lambda goal_id: {"id": goal_id, "label": goal_id, "summary": ""})
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: {"chart_data": {}, "meta": {}},
    )

    def fake_evaluate_goal_model(_goal_id, *, natal_rows, natal_crossings, relocation, transit_rows=None, transit_crossings=None):
        captured["natal_ids"] = [row["id"] for row in natal_rows]
        captured["natal_crossings"] = natal_crossings
        return {"score": 50, "raw_score": 0.0}

    monkeypatch.setattr(astrocartography_goal_engine, "evaluate_goal_model", fake_evaluate_goal_model)

    result = astro_clock_api._astrocartography_target_analysis(
        target_location="Target City",
        resolved_name="Resolved Target",
        latitude=0.0,
        longitude=0.0,
        natal_meta={"timestamp": "2026-03-22T04:32:00Z"},
        natal_lines_payload={"lines": lines, "bodies": [f"Body{index}" for index in range(9)]},
        house_system_code="R",
        goal_id="home",
    )

    assert len(result["natal"]["nearest_lines"]) == 8
    assert len(captured["natal_ids"]) == 9
    assert "Body8:MC" in captured["natal_ids"]
