from pathlib import Path
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import astro_clock_engine
from horary_engine.engine import HoraryEngine


def _fake_chart_result(_question, settings):
    return {
        "chart_data": {
            "planets": [
                {"planet": "Moon", "longitude": 12.5, "sign": "Aries", "house": 1},
                {"planet": "Sun", "longitude": 24.0, "sign": "Aries", "house": 1},
                {"planet": "Mercury", "longitude": 28.0, "sign": "Aries", "house": 1},
            ],
            "timezone_info": {
                "timezone": settings.get("timezone") or "UTC",
                "local_time": "2026-04-05T11:00:00+03:00",
                "utc_time": "2026-04-05T08:00:00+00:00",
            },
        },
        "considerations": {"moon_void": False},
        "moon_last_aspect": None,
        "moon_next_aspect": None,
    }


def test_engine_uses_cached_coords_for_horary_calls(monkeypatch):
    eng = astro_clock_engine.AstroClockEngine()
    captured = {}

    def _capture_judge(_question, settings):
        captured.update(settings)
        return _fake_chart_result(_question, settings)

    monkeypatch.setattr(eng.horary_engine, "judge", _capture_judge)
    monkeypatch.setattr(
        astro_clock_engine,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("safe_geocode should not run when coords already exist")),
    )
    monkeypatch.setattr(eng.timezone_manager, "get_timezone_for_location", lambda _lat, _lon: "Asia/Jerusalem")

    eng.update_settings(
        location="Jerusalem, Israel",
        timezone="UTC",
        latitude=31.778,
        longitude=35.235,
    )

    data = eng.get_current_data()

    assert data.settings.location == "Jerusalem, Israel"
    assert captured["latitude"] == 31.778
    assert captured["longitude"] == 35.235
    assert captured["timezone"] == "Asia/Jerusalem"


def test_engine_resolves_default_greenwich_through_shared_geocoder(monkeypatch):
    eng = astro_clock_engine.AstroClockEngine()
    captured = {}
    geocode_calls = []

    def _capture_judge(_question, settings):
        captured.update(settings)
        return _fake_chart_result(_question, settings)

    def _fake_geocode(location, *_args, **_kwargs):
        geocode_calls.append(location)
        return 51.4769, -0.0005, "Greenwich, UK"

    monkeypatch.setattr(eng.horary_engine, "judge", _capture_judge)
    monkeypatch.setattr(astro_clock_engine, "safe_geocode", _fake_geocode)
    monkeypatch.setattr(eng.timezone_manager, "get_timezone_for_location", lambda _lat, _lon: "Europe/London")

    data = eng.get_current_data()

    assert data.settings.location == "Greenwich, UK"
    assert geocode_calls == ["Greenwich, UK"]
    assert captured["location"] == "Greenwich, UK"
    assert captured["latitude"] == 51.4769
    assert captured["longitude"] == -0.0005
    assert captured["timezone"] == "Europe/London"


def test_horary_engine_forwards_pre_resolved_coords(monkeypatch):
    horary = HoraryEngine()
    captured = {}

    def _capture_inner(**kwargs):
        captured.update(kwargs)
        return {"chart_data": {"planets": []}}

    monkeypatch.setattr(horary.engine, "judge_question", _capture_inner)

    horary.judge(
        "Astro Clock Real-time Chart",
        {
            "location": "Jerusalem, Israel",
            "latitude": 31.778,
            "longitude": 35.235,
            "location_name": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
        },
    )

    assert captured["latitude"] == 31.778
    assert captured["longitude"] == 35.235
    assert captured["location_name"] == "Jerusalem, Israel"


def test_timezone_label_uses_local_utc_offset_not_absolute_delta():
    chart_data = {
        "timezone_info": {
            "timezone": "Asia/Baghdad",
            "local_time": "2005-10-19T14:15:00+03:00",
            "utc_time": "2005-10-19T11:15:00+00:00",
        }
    }

    assert astro_clock_api._timezone_label_from_chart_data(chart_data) == "Asia/Baghdad (UTC+03:00)"


def test_dashboard_and_hours_use_cached_coords_when_geocoder_is_unavailable(monkeypatch):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    geocode_calls = {"count": 0}

    monkeypatch.setattr(astro_clock_api, "_engine", eng)
    monkeypatch.setattr(eng.horary_engine, "judge", _fake_chart_result)

    def _count_geocode(*_args, **_kwargs):
        geocode_calls["count"] += 1
        raise astro_clock_api.LocationError("rate limited")

    monkeypatch.setattr(astro_clock_api, "safe_geocode", _count_geocode)

    eng.update_settings(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        latitude=31.778,
        longitude=35.235,
    )

    class _FakePlanetaryHours:
        def calculate_daily_hours(self, target_date):
            hour = SimpleNamespace(
                hour_number=1,
                ruling_planet=SimpleNamespace(value="Sun"),
                start_time=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc),
                end_time=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1),
                duration_minutes=60,
                is_day_hour=True,
            )
            return SimpleNamespace(
                date=target_date,
                day_ruler=SimpleNamespace(value="Sun"),
                sunrise=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc),
                sunset=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12),
                hours=[hour],
                current_hour=hour,
            )

        def calculate_daily_hours_for_local_date(self, target_date, _timezone_name):
            return self.calculate_daily_hours(target_date)

        def get_current_planetary_hour(self, _target_dt):
            target_date = date(2026, 4, 5)
            return SimpleNamespace(
                hour_number=1,
                ruling_planet=SimpleNamespace(value="Sun"),
                start_time=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc),
                end_time=datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1),
                duration_minutes=60,
                is_day_hour=True,
            )

        def get_planetary_hour_for_local_datetime(self, target_dt, _timezone_name):
            return self.get_current_planetary_hour(target_dt)

    monkeypatch.setattr(astro_clock_api, "_ph_instance", lambda _lat, _lon: _FakePlanetaryHours())

    dashboard_response = client.get("/api/astro-clock/dashboard")
    hours_response = client.get("/api/astro-clock/planetary-hours")

    dashboard_payload = dashboard_response.get_json()
    hours_payload = hours_response.get_json()

    assert dashboard_response.status_code == 200
    assert dashboard_payload["success"] is True
    assert hours_response.status_code == 200
    assert hours_payload["success"] is True
    assert geocode_calls["count"] == 0


def test_planetary_hours_invalid_location_fails_without_greenwich_fallback(monkeypatch):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    geocode_calls = []

    monkeypatch.setattr(astro_clock_api, "_engine", eng)

    def _fake_current_data(settings=None):
        return SimpleNamespace(
            timestamp=datetime(2026, 4, 5, 8, 0, tzinfo=timezone.utc),
            settings=settings or eng.settings,
            chart_result={"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
        )

    def _fail_geocode(location, *_args, **_kwargs):
        geocode_calls.append(location)
        raise astro_clock_api.LocationError("not found")

    monkeypatch.setattr(eng, "get_current_data", _fake_current_data)
    monkeypatch.setattr(astro_clock_api, "safe_geocode", _fail_geocode)
    eng.update_settings(
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    response = client.get(
        "/api/astro-clock/planetary-hours"
        "?mode=manual&datetime=2026-04-05T11%3A00%3A00"
        "&location=Invalid%20Nowhere"
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "Unable to resolve location for planetary hours" in payload["error"]
    assert geocode_calls
    assert "Greenwich, UK" not in geocode_calls


def test_realtime_mode_location_change_commits_resolved_coords_and_timezone(monkeypatch):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    geocode_calls = {"count": 0}

    monkeypatch.setattr(astro_clock_api, "_engine", eng)

    def _fake_geocode(location, *_args, **_kwargs):
        geocode_calls["count"] += 1
        assert location == "Israel"
        return (31.778, 35.235, "Israel")

    monkeypatch.setattr(astro_clock_api, "safe_geocode", _fake_geocode)
    monkeypatch.setattr(
        astro_clock_api,
        "_tz_instance",
        lambda: SimpleNamespace(get_timezone_for_location=lambda _lat, _lon: "Asia/Jerusalem"),
    )

    eng.update_settings(
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    response = client.post("/api/astro-clock/mode", json={
        "mode": "realtime",
        "location": "Israel",
        "house_system_code": "R",
    })
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert eng.settings.location == "Israel"
    assert eng.settings.timezone == "Asia/Jerusalem"
    assert eng.settings.latitude == 31.778
    assert eng.settings.longitude == 35.235
    assert eng.settings.house_system_code == "R"
    assert geocode_calls["count"] == 1


def test_request_clock_context_does_not_reuse_previous_timezone_for_changed_location(monkeypatch):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    captured = {}

    monkeypatch.setattr(astro_clock_api, "_engine", eng)
    monkeypatch.setattr(
        astro_clock_api,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(astro_clock_api.LocationError("rate limited")),
    )

    def _capture_settings(settings=None):
        captured["settings"] = settings
        raise astro_clock_api.LocationError("stop before chart")

    monkeypatch.setattr(eng, "get_current_data", _capture_settings)

    eng.update_settings(
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    response = client.get("/api/astro-clock/dashboard?mode=realtime&location=Israel")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert captured["settings"].location == "Israel"
    assert captured["settings"].timezone is None
    assert captured["settings"].latitude is None
    assert captured["settings"].longitude is None


def test_request_clock_context_reresolves_explicit_same_location_without_coords(monkeypatch):
    app = app_module.app
    eng = astro_clock_engine.AstroClockEngine()
    captured = {}
    geocode_calls = []

    monkeypatch.setattr(astro_clock_api, "_engine", eng)

    def _fake_geocode(location, *_args, **_kwargs):
        geocode_calls.append(location)
        assert location == "Sadr City, Baghdad, Iraq"
        return (33.3905897, 44.4570662, location)

    monkeypatch.setattr(astro_clock_api, "safe_geocode", _fake_geocode)
    monkeypatch.setattr(
        astro_clock_api,
        "_tz_instance",
        lambda: SimpleNamespace(get_timezone_for_location=lambda _lat, _lon: "Asia/Baghdad"),
    )

    def _capture_settings(settings=None):
        captured["settings"] = settings
        return SimpleNamespace(
            timestamp=datetime(2005, 10, 19, 11, 15, tzinfo=timezone.utc),
            settings=settings,
            chart_result={"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
        )

    monkeypatch.setattr(eng, "get_current_data", _capture_settings)
    eng.update_settings(
        location="Sadr City, Baghdad, Iraq",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    with app.test_request_context(
        "/api/astro-clock/dashboard"
        "?mode=manual"
        "&datetime=2005-10-19T14:15:00"
        "&location=Sadr%20City%2C%20Baghdad%2C%20Iraq"
        "&house_system_code=R"
    ):
        data, active_settings = astro_clock_api._data_for_request_clock_context(eng)

    assert data.settings is active_settings
    assert active_settings.location == "Sadr City, Baghdad, Iraq"
    assert active_settings.timezone == "Asia/Baghdad"
    assert active_settings.latitude == 33.3905897
    assert active_settings.longitude == 44.4570662
    assert geocode_calls == ["Sadr City, Baghdad, Iraq"]


def test_set_mode_reresolves_explicit_same_location_without_coords(monkeypatch):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    geocode_calls = []

    monkeypatch.setattr(astro_clock_api, "_engine", eng)

    def _fake_geocode(location, *_args, **_kwargs):
        geocode_calls.append(location)
        assert location == "Sadr City, Baghdad, Iraq"
        return (33.3905897, 44.4570662, location)

    monkeypatch.setattr(astro_clock_api, "safe_geocode", _fake_geocode)
    monkeypatch.setattr(
        astro_clock_api,
        "_tz_instance",
        lambda: SimpleNamespace(get_timezone_for_location=lambda _lat, _lon: "Asia/Baghdad"),
    )

    eng.update_settings(
        location="Sadr City, Baghdad, Iraq",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    response = client.post("/api/astro-clock/mode", json={
        "mode": "manual",
        "datetime": "2005-10-19T14:15:00",
        "location": "Sadr City, Baghdad, Iraq",
        "house_system_code": "R",
    })
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert eng.settings.location == "Sadr City, Baghdad, Iraq"
    assert eng.settings.timezone == "Asia/Baghdad"
    assert eng.settings.latitude == 33.3905897
    assert eng.settings.longitude == 44.4570662
    assert geocode_calls == ["Sadr City, Baghdad, Iraq"]


def test_snap_store_migrates_legacy_user_snaps(monkeypatch, tmp_path):
    monkeypatch.delenv("HORARY_DATA_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("HORARY_MAX_SNAPS", "500")
    monkeypatch.setattr(astro_clock_api, "_snap_store", None)

    legacy_path = tmp_path / "VoxStella" / "snaps_store.json"
    current_path = tmp_path / "VoxStella" / "backend" / "snaps_store.json"
    legacy_path.parent.mkdir(parents=True)
    current_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps({
        "snaps": [
            {"id": "old-snap", "label": "Old legacy snap"},
            {"id": "shared-snap", "label": "Legacy shared snap"},
        ]
    }), encoding="utf-8")
    current_path.write_text(json.dumps({
        "snaps": [
            {"id": "shared-snap", "label": "Current shared snap"},
            {"id": "new-snap", "label": "New backend snap"},
        ]
    }), encoding="utf-8")

    store = astro_clock_api._snaps()
    snaps = store.list()

    assert [snap["id"] for snap in snaps] == ["old-snap", "shared-snap", "new-snap"]
    assert snaps[1]["label"] == "Current shared snap"
    assert legacy_path.exists()
    saved = json.loads(current_path.read_text(encoding="utf-8"))
    assert [snap["id"] for snap in saved["snaps"]] == ["old-snap", "shared-snap", "new-snap"]


def test_create_snap_uses_payload_context_coords_without_geocoding(monkeypatch, tmp_path):
    client = app_module.app.test_client()
    eng = astro_clock_engine.AstroClockEngine()
    geocode_calls = {"count": 0}

    monkeypatch.setattr(astro_clock_api, "_engine", eng)
    monkeypatch.setattr(astro_clock_api, "_snap_store", None)
    monkeypatch.setenv("HORARY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(eng.horary_engine, "judge", _fake_chart_result)

    def _count_geocode(*_args, **_kwargs):
        geocode_calls["count"] += 1
        raise astro_clock_api.LocationError("rate limited")

    monkeypatch.setattr(astro_clock_api, "safe_geocode", _count_geocode)
    monkeypatch.setattr(astro_clock_engine, "safe_geocode", _count_geocode)

    eng.update_settings(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        latitude=None,
        longitude=None,
    )

    response = client.post("/api/astro-clock/snap", json={
        "label": "Realtime Snap",
        "mode": "realtime",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "house_system_code": "R",
    })
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["id"]
    assert geocode_calls["count"] == 0

    store = astro_clock_api._snaps()
    saved = store.get(payload["data"]["id"])
    assert saved["location"] == "Jerusalem, Israel"
    assert saved["latitude"] == 31.778
    assert saved["longitude"] == 35.235

    manual_response = client.post("/api/astro-clock/snap", json={
        "label": "Manual Snap",
        "mode": "manual",
        "datetime": "2026-03-22T06:32:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "house_system_code": "R",
    })
    manual_payload = manual_response.get_json()

    assert manual_response.status_code == 200
    assert manual_payload["success"] is True
    assert manual_payload["data"]["id"]
    assert geocode_calls["count"] == 0

    manual_saved = store.get(manual_payload["data"]["id"])
    assert manual_saved["location"] == "Jerusalem, Israel"
    assert manual_saved["latitude"] == 31.778
    assert manual_saved["longitude"] == 35.235


def test_moon_state_uses_top_level_planets_before_fallback(caplog):
    eng = astro_clock_engine.AstroClockEngine()
    chart_result = {
        "planets": {
            "Moon": {
                "longitude": 12.5,
                "sign": "Aries",
                "house": 1,
            }
        },
        "considerations": {"moon_void": True},
    }

    with caplog.at_level("WARNING"):
        moon_state = eng._calculate_moon_state({}, [], chart_result)

    assert moon_state.position.longitude == 12.5
    assert moon_state.position.sign.sign_name == "Aries"
    assert moon_state.position.house == 1
    assert moon_state.void_of_course is True
    assert "Moon position not found in chart" not in caplog.text
