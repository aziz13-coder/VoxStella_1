from pathlib import Path
import os
import sys
import threading
import time

import pytest

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
        assert str(exc) == "Unsupported astrocartography angle filter: NADIR"


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
        assert str(exc) == "Unsupported astrocartography angle filter: NADIR"


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
    chiron_provenance = planets["Chiron"]["calculation_provenance"]
    if chiron_provenance["ephemeris_engine"] == "moshier":
        assert chiron_provenance["source"] == "moshier"


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


def test_compute_chart_bundle_rejects_malformed_datetime_before_realtime_fallback(monkeypatch):
    called = {"get_current_data": False}

    class FakeEngine:
        settings = astro_clock_api.AstroClockSettings(
            mode=astro_clock_api.ClockMode.REALTIME,
            location="Birthplace",
            timezone="UTC",
            latitude=31.0,
            longitude=35.0,
        )

        def get_current_data(self, **_kwargs):
            called["get_current_data"] = True
            raise AssertionError("Malformed natal time must not reach realtime calculation")

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: FakeEngine())

    with pytest.raises(ValueError, match="Invalid datetime"):
        astro_clock_api._compute_chart_bundle_for(
            "not-a-datetime",
            "Birthplace",
            "UTC",
            latitude=31.0,
            longitude=35.0,
        )

    assert called["get_current_data"] is False


def test_direct_natal_bundle_preserves_numeric_zero_uncertainty(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: {
            "chart_data": {"planets": {}},
            "meta": {
                "timestamp": "1990-01-01T12:00:00+00:00",
                "location": "Birthplace",
                "latitude": 31.0,
                "longitude": 35.0,
            },
        },
    )

    bundle = astro_clock_api._natal_bundle_from_query(
        {
            "natal_datetime": "1990-01-01T12:00:00Z",
            "natal_location": "Birthplace",
            "latitude": 31.0,
            "longitude": 35.0,
            "natal_time_uncertainty_minutes": 0,
        }
    )

    assert bundle["birth_time"]["uncertainty_minutes"] == 0.0
    assert bundle["birth_time"]["ranking_eligible"] is True


def test_natal_snap_propagates_birth_time_certification_and_ranking_eligibility(monkeypatch):
    snap = {
        "effective_datetime": "1990-01-01T12:00:00Z",
        "location": "Birthplace",
        "timezone": "UTC",
        "latitude": 31.0,
        "longitude": 35.0,
        "certification": {
            "status": "unresolved_rectification",
            "confidence": "low",
            "birth": {"source_time_status": "unknown"},
        },
    }
    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: {"snap-1": snap})
    monkeypatch.setattr(astro_clock_api, "_hydrate_snap_payload", lambda value: value)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: {
            "chart_data": {"planets": {}},
            "meta": {
                "timestamp": "1990-01-01T12:00:00+00:00",
                "location": "Birthplace",
                "latitude": 31.0,
                "longitude": 35.0,
            },
        },
    )

    bundle = astro_clock_api._bundle_from_snap_id("snap-1")

    assert bundle["birth_time"]["status"] == "unresolved_rectification"
    assert bundle["birth_time"]["ranking_eligible"] is False
    assert bundle["meta"]["birth_time"] == bundle["birth_time"]
    assert bundle["meta"]["coordinate_source"] == "saved_snap"


def test_birth_time_quality_preserves_time_only_rectification_search_window():
    quality = astro_clock_api._astrocartography_birth_time_quality(
        certification={
            "status": "rectified_candidate",
            "confidence": "medium",
            "search": {
                "start_time": "00:58",
                "end_time": "01:02",
            },
        },
    )

    assert quality["search_window_minutes"] == 4.0
    assert quality["effective_uncertainty_minutes"] is None
    assert quality["ranking_eligible"] is True

    wide_search_quality = astro_clock_api._astrocartography_birth_time_quality(
        certification={
            "status": "rectified_candidate",
            "confidence": "low",
            "search": {
                "start_time": "00:00",
                "end_time": "01:00",
            },
        },
    )
    assert wide_search_quality["search_window_minutes"] == 60.0
    assert wide_search_quality["effective_uncertainty_minutes"] is None
    assert wide_search_quality["ranking_eligibility"] == "provisional"
    assert wide_search_quality["ranking_eligible"] is True

    certified_quality = astro_clock_api._astrocartography_birth_time_quality(
        certification={
            "status": "certified_source",
            "confidence": "high",
            "birth": {"source_time_status": "certificate"},
            "search": {
                "start_time": "00:00",
                "end_time": "23:59",
            },
        },
    )
    assert certified_quality["search_window_minutes"] == 1439.0
    assert certified_quality["effective_uncertainty_minutes"] is None
    assert certified_quality["ranking_eligibility"] == "confirmed"
    assert certified_quality["ranking_eligible"] is True


def test_exact_target_coordinates_bypass_geocoding_and_preserve_candidate_id(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("geocoder must not run")),
    )

    target = astro_clock_api._resolve_astrocartography_target(
        "Paris, France",
        target_id="geonames:2988507",
        target_latitude="48.8566",
        target_longitude="2.3522",
    )

    assert target["candidate_id"] == "geonames:2988507"
    assert target["latitude"] == 48.8566
    assert target["longitude"] == 2.3522
    assert target["coordinate_source"] == "atlas_candidate"


def test_direct_target_country_alias_resolves_exact_catalog_city_not_timezone_false_positive(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Exact catalog city must resolve before the broad geocoder")
        ),
    )

    target = astro_clock_api._resolve_astrocartography_target("London, UK")

    assert target["candidate_id"] == "geonames:2643743"
    assert target["label"].startswith("London,")
    assert target["latitude"] == pytest.approx(51.50853)
    assert target["longitude"] == pytest.approx(-0.12574)
    assert target["coordinate_source"] == "bundled_geonames_catalog"


def test_direct_target_rejects_unrelated_substring_city_match(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_astrocartography_catalog_target",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (51.0, -1.0, "Yorkton, Canada"),
    )

    with pytest.raises(astro_clock_api.LocationError, match="unrelated catalog city"):
        astro_clock_api._resolve_astrocartography_target("York")


@pytest.mark.parametrize(
    ("query", "candidate_id"),
    [
        ("London", "geonames:2643743"),
        ("London UK", "geonames:2643743"),
        ("London, U.K.", "geonames:2643743"),
        ("London Great Britain", "geonames:2643743"),
        ("London, England, UK", "geonames:2643743"),
        ("Manchester, UK", "geonames:2643123"),
        ("Cambridge, UK", "geonames:2653941"),
        ("Oxford, UK", "geonames:2640729"),
        ("Berlin, DE", "geonames:2950159"),
        ("Jerusalem, IL", "geonames:281184"),
        ("Springfield, Illinois, USA", "geonames:4250542"),
        ("Springfield Illinois", "geonames:4250542"),
        ("Springfield, MO, USA", "geonames:4409896"),
        ("Victoria, BC, Canada", "geonames:6174041"),
        ("Victoria BC", "geonames:6174041"),
        ("San Jose, CA, USA", "geonames:5392171"),
        ("San Jose CA", "geonames:5392171"),
        ("New York, NY, USA", "geonames:5128581"),
        ("Paris, Ile-de-France, France", "geonames:2988507"),
        ("México City", "geonames:3530597"),
    ],
)
def test_direct_target_resolves_exact_structured_city_identity(
    monkeypatch,
    query,
    candidate_id,
):
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Structured catalog identity must resolve before geocoding")
        ),
    )

    target = astro_clock_api._resolve_astrocartography_target(query)

    assert target["candidate_id"] == candidate_id
    assert target["coordinate_source"] == "bundled_geonames_catalog"
    assert target["identity"]["policy"] == "exact_city_and_structured_qualifier_match"


def test_direct_target_population_dominance_is_explicit_not_silent():
    target = astro_clock_api._resolve_astrocartography_target("London")

    assert target["candidate_id"] == "geonames:2643743"
    assert target["identity"]["status"] == "population_dominant"
    assert target["identity"]["ambiguity"]["auto_selected"] is True
    assert target["identity"]["ambiguity"]["policy_threshold_ratio"] == 5.0


@pytest.mark.parametrize("query", ["Springfield", "Cambridge", "Victoria"])
def test_direct_target_fails_closed_for_unqualified_ambiguous_city(query):
    with pytest.raises(astro_clock_api.LocationError, match="is ambiguous"):
        astro_clock_api._resolve_astrocartography_target(query)


@pytest.mark.parametrize(
    "query",
        [
            "Springfield, California, USA",
            "Victoria, AB, Canada",
            "San Jose, BC, USA",
            "Paris, Texas, France",
        ],
)
def test_direct_target_rejects_wrong_region_or_country_qualifiers(query):
    with pytest.raises(astro_clock_api.LocationError, match="qualifiers do not match"):
        astro_clock_api._resolve_astrocartography_target(query)


def test_direct_target_geonames_id_is_resolved_first_and_validated():
    target = astro_clock_api._resolve_astrocartography_target(
        "Springfield, Illinois, USA",
        target_id="4250542",
    )

    assert target["candidate_id"] == "geonames:4250542"
    assert target["identity"]["status"] == "id_exact"

    with pytest.raises(astro_clock_api.LocationError, match="does not match"):
        astro_clock_api._resolve_astrocartography_target(
            "Paris, France",
            target_id="geonames:2643743",
        )


def test_direct_target_geonames_coordinates_are_identity_and_distance_validated():
    target = astro_clock_api._resolve_astrocartography_target(
        "Paris, France",
        target_id="2988507",
        target_latitude=48.8566,
        target_longitude=2.3522,
    )

    assert target["candidate_id"] == "geonames:2988507"
    assert target["identity"]["status"] == "request_coordinates_id_validated"
    assert target["identity"]["geonames_coordinate_distance_km"] < 2.0

    with pytest.raises(astro_clock_api.LocationError, match="does not match"):
        astro_clock_api._resolve_astrocartography_target(
            "Paris, France",
            target_id="geonames:2643743",
            target_latitude=48.8566,
            target_longitude=2.3522,
        )
    with pytest.raises(astro_clock_api.LocationError, match="differ from the bundled catalog"):
        astro_clock_api._resolve_astrocartography_target(
            "Paris, France",
            target_id="geonames:2988507",
            target_latitude=51.50853,
            target_longitude=-0.12574,
        )


def test_direct_target_custom_id_requires_exact_coordinates():
    with pytest.raises(astro_clock_api.LocationError, match="requires exact"):
        astro_clock_api._resolve_astrocartography_target(
            "Custom Target",
            target_id="custom:target",
        )

    target = astro_clock_api._resolve_astrocartography_target(
        "Custom Target",
        target_id="custom:target",
        target_latitude=1.25,
        target_longitude=2.5,
    )
    assert target["candidate_id"] == "custom:target"
    assert target["latitude"] == 1.25
    assert target["longitude"] == 2.5


def test_target_analysis_separates_birthplace_and_relocated_local_space(monkeypatch):
    calls = []

    monkeypatch.setattr(
        astrocartography_service,
        "build_location_reading",
        lambda *_args, **_kwargs: {"nearest_lines": []},
    )
    monkeypatch.setattr(astrocartography_service, "crossing_candidates_for_point", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(astrocartography_service, "build_intersection_workspace", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astrocartography_service, "build_paran_candidates_for_point", lambda *_args, **_kwargs: {"items": []})
    monkeypatch.setattr(astrocartography_service, "build_delineation_report", lambda **_kwargs: {"headline": "ok"})

    def fake_local_space(_timestamp, latitude, longitude, **_kwargs):
        calls.append((latitude, longitude))
        return {"rays": []}

    monkeypatch.setattr(astrocartography_service, "build_local_space_workspace", fake_local_space)
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_relocation_chart_bundle",
        lambda **_kwargs: {
            "available": True,
            "chart_data": {"planets": {}},
            "meta": {},
            "provenance": {
                "coordinate_source": "atlas_candidate",
                "degraded": False,
            },
            "warnings": [],
        },
    )
    monkeypatch.setattr(astrocartography_goal_engine, "extract_relocation_features", lambda _chart: {"metrics": {}})
    monkeypatch.setattr(astrocartography_goal_engine, "summarize_relocation_features", lambda _features: {})

    result = astro_clock_api._astrocartography_target_analysis(
        target_location="Paris, France",
        resolved_name="Paris, France",
        latitude=48.8566,
        longitude=2.3522,
        natal_meta={
            "timestamp": "1990-01-01T12:00:00Z",
            "location": "Birthplace",
            "latitude": 31.0,
            "longitude": 35.0,
        },
        natal_chart_data={"planets": {"Sun": {"longitude": 280.0}}},
        natal_lines_payload={"lines": [], "bodies": ["Sun"], "angles": ["ASC", "MC"]},
        house_system_code="R",
        target_identity={
            "status": "population_dominant",
            "policy": "exact_city_and_structured_qualifier_match",
            "ambiguity": {
                "candidate_count": 2,
                "auto_selected": True,
                "policy_threshold_ratio": 5.0,
            },
        },
    )

    assert calls[0] == (31.0, 35.0)
    assert calls[-1] == (48.8566, 2.3522)
    assert result["natal"]["local_space"]["origin_kind"] == "birthplace"
    assert result["relocation"]["local_space"]["origin_kind"] == "relocated_target"
    assert result["calculation"]["relocation"]["coordinate_source"] == "atlas_candidate"
    assert result["target"]["identity"]["status"] == "population_dominant"
    assert result["provenance"]["target_resolution"]["ambiguity"]["auto_selected"] is True


def test_relocation_house_failure_is_candidate_level_and_never_substitutes_house_system(monkeypatch):
    class FakeSwe:
        GREG_CAL = 1

        @staticmethod
        def julday(*_args):
            return 2451545.0

        @staticmethod
        def houses(*_args):
            raise RuntimeError("houses cannot be computed at this polar latitude")

    monkeypatch.setattr(astro_clock_api, "require_swisseph", lambda: FakeSwe())

    result = astro_clock_api._compute_relocation_chart_bundle(
        natal_chart_data={"planets": {"Sun": {"longitude": 280.0}}},
        natal_meta={"timestamp": "1990-01-01T12:00:00Z"},
        target_label="Polar City",
        latitude=78.0,
        longitude=15.0,
        timezone_name="Arctic/Longyearbyen",
        house_system_code="P",
        coordinate_source="atlas_candidate",
    )

    assert result["available"] is False
    assert result["relocation_unavailable"] is True
    assert result["error"]["code"] == "polar_house_calculation_unavailable"
    assert result["meta"]["house_system_code"] == "P"
    assert result["provenance"]["house_system_code"] == "P"
    assert result["provenance"]["house_system_substituted"] is False
    assert result["provenance"]["coordinate_source"] == "atlas_candidate"
    assert "substituted" in result["warnings"][0]


def test_relocation_rejects_unknown_house_code_before_swiss_silent_fallback(monkeypatch):
    class FakeSwe:
        GREG_CAL = 1

        @staticmethod
        def julday(*_args):
            return 2451545.0

        @staticmethod
        def houses(*_args):
            raise AssertionError("Unsupported house code must not reach Swiss Ephemeris")

    monkeypatch.setattr(astro_clock_api, "require_swisseph", lambda: FakeSwe())

    with pytest.raises(ValueError, match="Unsupported house_system_code 'Z'"):
        astro_clock_api._compute_relocation_chart_bundle(
            natal_chart_data={"planets": {"Sun": {"longitude": 280.0}}},
            natal_meta={"timestamp": "1990-01-01T12:00:00Z"},
            target_label="Test City",
            latitude=40.0,
            longitude=-74.0,
            timezone_name="America/New_York",
            house_system_code="Z",
            coordinate_source="request_coordinates",
        )


def test_relocation_endpoint_exposes_chart_payload(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(
        astro_clock_api,
        "_build_astrocartography_location_payload",
        lambda _args: {
            "target": {"candidate_id": "geonames:1", "label": "Test City"},
            "birth_time": {"ranking_eligible": True},
            "distance_policy": {"version": "test"},
            "calculation": {"degraded": False},
            "relocation": {
                "available": True,
                "chart": {"ascendant": 12.0, "houses": [float(index * 30) for index in range(12)]},
            },
        },
    )

    response = client.get("/api/astro-clock/astrocartography/relocation?target_location=Test%20City")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["relocation"]["available"] is True
    assert payload["data"]["relocation"]["chart"]["ascendant"] == 12.0


def test_paran_angle_filter_requires_both_events_to_match():
    payload = {
        "track_count": 2,
        "lead_track": {"id": "allowed"},
        "tracks": [
            {"id": "allowed", "angle_a": "ASC", "angle_b": "MC"},
            {"id": "excluded", "angle_a": "DSC", "angle_b": "IC"},
        ],
    }

    filtered = astro_clock_api._filter_astrocartography_parans(
        payload,
        angles=["ASC", "MC"],
    )

    assert filtered["track_count"] == 1
    assert filtered["lead_track"]["id"] == "allowed"
    assert filtered["tracks"][0]["id"] == "allowed"


def test_paran_angle_filter_scans_before_display_limit():
    payload = {
        "track_count": 25,
        "lead_track": {"id": "excluded-0"},
        "tracks": [
            {
                "id": f"excluded-{index}",
                "label": f"Excluded {index}",
                "angle_a": "DSC",
                "angle_b": "IC",
            }
            for index in range(24)
        ] + [
            {
                "id": "allowed-after-default-prefix",
                "label": "Sun ASC paran Moon MC",
                "angle_a": "ASC",
                "angle_b": "MC",
            }
        ],
    }

    filtered = astro_clock_api._filter_astrocartography_parans(
        payload,
        angles=["ASC", "MC"],
        limit=24,
    )

    assert filtered["track_count"] == 1
    assert filtered["returned_count"] == 1
    assert filtered["lead_track"]["id"] == "allowed-after-default-prefix"
    assert filtered["headline"].startswith("Sun ASC paran Moon MC")


def test_compare_preserves_aligned_exact_candidate_coordinates(monkeypatch):
    client = app_module.app.test_client()
    captured = []

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_bundle_from_query",
        lambda _args: {
            "chart_data": {"planets": {}},
            "meta": {"timestamp": "2024-01-01T00:00:00Z"},
        },
    )
    monkeypatch.setattr(astro_clock_api, "_transit_bundle_from_query", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        astrocartography_service,
        "build_astrocartography_lines",
        lambda *_args, **_kwargs: {"bodies": ["Sun"], "angles": ["MC"], "lines": []},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("geocoder must not run")),
    )

    def fake_analysis(**kwargs):
        captured.append(kwargs)
        return {
            "target": {
                "candidate_id": kwargs.get("target_id"),
                "label": kwargs.get("resolved_name"),
                "query": kwargs.get("target_location"),
                "latitude": kwargs.get("latitude"),
                "longitude": kwargs.get("longitude"),
                "coordinate_source": kwargs.get("coordinate_source"),
            },
            "location_score": {"score": 50, "raw_score": 1.0},
        }

    monkeypatch.setattr(astro_clock_api, "_astrocartography_target_analysis", fake_analysis)

    response = client.get(
        "/api/astro-clock/astrocartography/compare"
        "?target_location=Paris&target_location=London"
        "&target_id=geonames%3A2988507&target_id=geonames%3A2643743"
        "&target_latitude=48.8566&target_latitude=51.5074"
        "&target_longitude=2.3522&target_longitude=-0.1278"
    )

    assert response.status_code == 200
    response_payload = response.get_json()["data"]
    assert [row["target_id"] for row in captured] == [
        "geonames:2988507",
        "geonames:2643743",
    ]
    assert [(row["latitude"], row["longitude"]) for row in captured] == [
        (48.8566, 2.3522),
        (51.5074, -0.1278),
    ]
    assert all(row["coordinate_source"] == "atlas_candidate" for row in captured)
    assert response_payload["calculation"] == response_payload["provenance"]
    assert response_payload["calculation"]["natal"]["engine"] == "Swiss Ephemeris"
    ranking = response_payload["ranking"]
    assert {row["candidate_id"] for row in ranking} == {
        "geonames:2988507",
        "geonames:2643743",
    }
    assert {
        (row["latitude"], row["longitude"], row["coordinate_source"])
        for row in ranking
    } == {
        (48.8566, 2.3522, "atlas_candidate"),
        (51.5074, -0.1278, "atlas_candidate"),
    }


def test_atlas_ranking_rejects_unknown_birth_time_before_candidate_scan(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_natal_bundle_from_query",
        lambda _args: {
            "chart_data": {},
            "meta": {
                "timestamp": "2024-01-01T00:00:00Z",
                "birth_time": {
                    "ranking_eligible": False,
                    "ranking_eligibility": "ineligible_unknown_time",
                },
            },
        },
    )

    with pytest.raises(ValueError, match="City ranking is unavailable"):
        astro_clock_api._run_astrocartography_atlas_search(
            {"goal_id": "love", "natal_datetime": "2024-01-01T00:00:00Z"}
        )


def test_atlas_ranking_rejects_date_only_natal_input_before_candidate_scan():
    with pytest.raises(ValueError, match="natal_datetime must include"):
        astro_clock_api._run_astrocartography_atlas_search(
            {
                "goal_id": "love",
                "natal_datetime": "1990-01-01",
                "natal_location": "Jerusalem",
            }
        )


def test_angular_event_registry_groups_crossing_and_paran_presentations_once():
    canonical_id = "angular-event:Moon:DSC|Sun:MC"
    registry = astro_clock_api._astrocartography_angular_event_registry(
        crossings=[
            {
                "id": f"{canonical_id}:crossing",
                "canonical_event_id": canonical_id,
                "event_kind": "angular-line-crossing",
            }
        ],
        intersections={
            "primary_crossings": [
                {
                    "id": f"{canonical_id}:intersection",
                    "canonical_event_id": canonical_id,
                    "event_kind": "angular-line-crossing",
                }
            ],
            "blend_candidates": [],
        },
        parans={
            "items": [
                {
                    "id": f"{canonical_id}:paran-point",
                    "canonical_event_id": canonical_id,
                    "event_kind": "paran-crossing-point",
                }
            ]
        },
    )

    assert registry["event_count"] == 1
    assert registry["duplicate_presentation_count"] == 2
    assert {row["section"] for row in registry["events"][0]["presentations"]} == {
        "crossings",
        "intersections",
        "parans",
    }
    assert {row["event_kind"] for row in registry["events"][0]["presentations"]} == {
        "angular-line-crossing",
        "paran-crossing-point",
    }
