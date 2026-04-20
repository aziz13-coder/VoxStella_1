from pathlib import Path
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


def test_engine_uses_builtin_greenwich_coords_without_geocoding(monkeypatch):
    eng = astro_clock_engine.AstroClockEngine()
    captured = {}

    def _capture_judge(_question, settings):
        captured.update(settings)
        return _fake_chart_result(_question, settings)

    monkeypatch.setattr(eng.horary_engine, "judge", _capture_judge)
    monkeypatch.setattr(
        astro_clock_engine,
        "safe_geocode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("safe_geocode should not run for built-in Greenwich fallback")),
    )
    monkeypatch.setattr(eng.timezone_manager, "get_timezone_for_location", lambda _lat, _lon: "Europe/London")

    data = eng.get_current_data()

    assert data.settings.location is None
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
