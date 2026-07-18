from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import os
import sys

import pytest

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import astro_clock_engine as astro_clock_engine_module
import asteroids as asteroids_module
import forensic.local_space as local_space_module
from almutens import compute_almuten_for_longitude, compute_chart_almutens


def _houses():
    return [i * 30.0 for i in range(12)]


def test_local_space_azimuth_uses_east_positive_from_north():
    east = local_space_module._az_alt_from_ra_dec(ra_hours=6, dec_deg=0, lat_deg=0, lst_hours=0)
    west = local_space_module._az_alt_from_ra_dec(ra_hours=18, dec_deg=0, lat_deg=0, lst_hours=0)

    assert east["azimuth_deg"] == 90.0
    assert west["azimuth_deg"] == 270.0


def test_astro_clock_engine_resolves_default_runtime_settings(monkeypatch):
    engine = astro_clock_engine_module.AstroClockEngine()
    captured = {}

    def _fake_judge(_question, settings):
        captured["settings"] = dict(settings)
        return {"chart_data": {}}

    monkeypatch.setattr(engine.horary_engine, "judge", _fake_judge)

    _result, resolved = engine._generate_chart_with_horary_engine(datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc))

    assert captured["settings"]["location"] == "Greenwich, UK"
    assert captured["settings"]["timezone"] == "Europe/London"
    assert captured["settings"]["latitude"] == 51.4769
    assert captured["settings"]["longitude"] == -0.0005
    assert resolved.location == "Greenwich, UK"
    assert resolved.timezone == "Europe/London"
    assert resolved.latitude == 51.4769
    assert resolved.longitude == -0.0005


def test_astro_clock_engine_preserves_coordinates_resolved_by_horary_path(monkeypatch):
    engine = astro_clock_engine_module.AstroClockEngine()
    engine.settings.location = "utah"
    engine.settings.timezone = "America/Denver"
    engine.settings.latitude = None
    engine.settings.longitude = None

    def _fake_judge(_question, settings):
        assert settings["latitude"] is None
        assert settings["longitude"] is None
        return {
            "chart_data": {
                "timezone_info": {
                    "timezone": "America/Denver",
                    "coordinates": {
                        "latitude": 39.321,
                        "longitude": -111.0937,
                    },
                },
            },
        }

    monkeypatch.setattr(engine.horary_engine, "judge", _fake_judge)

    _result, resolved = engine._generate_chart_with_horary_engine(datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc))

    assert resolved.location == "utah"
    assert resolved.timezone == "America/Denver"
    assert resolved.latitude == 39.321
    assert resolved.longitude == -111.0937


def test_astro_clock_engine_rejects_horary_location_error_payload(monkeypatch):
    engine = astro_clock_engine_module.AstroClockEngine()
    engine.settings.location = "utah"
    engine.settings.timezone = "America/Denver"
    engine.settings.latitude = None
    engine.settings.longitude = None

    def _fake_judge(_question, settings):
        assert settings["location"] == "utah"
        return {
            "error": "Geocoding failed for 'utah': 429 Too many requests",
            "judgment": "LOCATION_ERROR",
            "confidence": 0,
            "error_type": "LocationError",
        }

    monkeypatch.setattr(engine.horary_engine, "judge", _fake_judge)

    with pytest.raises(astro_clock_engine_module.LocationError):
        engine._generate_chart_with_horary_engine(datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc))


def test_compute_almuten_for_longitude_switches_triplicity_by_sect():
    day_result = compute_almuten_for_longitude(180.5, True)
    night_result = compute_almuten_for_longitude(180.5, False)

    day_saturn = next(item for item in day_result["candidates"] if item["planet"] == "Saturn")
    day_mercury = next(item for item in day_result["candidates"] if item["planet"] == "Mercury")
    night_saturn = next(item for item in night_result["candidates"] if item["planet"] == "Saturn")
    night_mercury = next(item for item in night_result["candidates"] if item["planet"] == "Mercury")

    assert day_result["leader"] == "Saturn"
    assert day_saturn["breakdown"]["triplicity"] == 3
    assert "triplicity" not in day_mercury["breakdown"]
    assert "triplicity" not in night_saturn["breakdown"]
    assert night_mercury["breakdown"]["triplicity"] == 3


def test_compute_chart_almutens_returns_dashboard_points(monkeypatch):
    monkeypatch.setattr(
        "almutens.compute_sect_info",
        lambda _chart_data: {"chart_sect": "Diurnal"},
    )

    result = compute_chart_almutens({"houses": _houses()})

    assert result["sect"] == "Day"
    assert [item["key"] for item in result["items"]] == [
        "ascendant",
        "midheaven",
        "house_2",
        "house_7",
        "house_11",
        "house_12",
    ]
    assert result["points"]["ascendant"]["label"] == "Ascendant"
    assert result["points"]["house_11"]["point_id"] == 34
    assert result["points"]["house_12"]["point_id"] == 35


def test_compute_asteroid_positions_includes_major_bodies_and_proserpina(monkeypatch):
    class FakeSwe:
        AST_OFFSET = 10000
        FLG_SWIEPH = 1
        FLG_SPEED = 2
        GREG_CAL = 1

        def julday(self, *_args):
            return 2461146.0

        def set_ephe_path(self, _path):
            return None

        def calc_ut(self, _jd_ut, point_id, _flags):
            payloads = {
                10001: [15.0, 0.4, 0.0, 0.15],
                10002: [67.5, 1.1, 0.0, -0.07],
                10003: [129.25, 0.2, 0.0, 0.09],
                10004: [201.75, -0.3, 0.0, 0.03],
                10026: [312.0, 0.8, 0.0, 0.05],
            }
            return payloads[point_id], None

    monkeypatch.setattr(asteroids_module, "swe", FakeSwe())
    monkeypatch.setattr(asteroids_module, "_resolve_ephemeris_path", lambda: r"C:\Program Files (x86)\Galaxy\SwisEph")

    result = asteroids_module.compute_asteroid_positions(
        {"houses": _houses()},
        "2026-04-15T12:00:00+00:00",
    )

    assert result["status"] == "ok"
    assert result["ephemeris_available"] is True
    assert [item["name"] for item in result["items"]] == [
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Proserpina",
    ]
    assert result["items"][1]["retrograde"] is True
    assert result["items"][-1]["galaxy_body_id"] == 17
    assert result["items"][-1]["direction_label"]


def test_compute_asteroid_positions_can_include_point_dependency_bodies(monkeypatch):
    class FakeSwe:
        AST_OFFSET = 10000
        FICT_OFFSET = 40
        MEAN_APOG = 12
        FLG_SWIEPH = 1
        FLG_SPEED = 2
        GREG_CAL = 1

        def julday(self, *_args):
            return 2447905.314583333

        def set_ephe_path(self, _path):
            return None

        def calc_ut(self, _jd_ut, point_id, _flags):
            payloads = {
                10001: [15.0, 0.4, 0.0, 0.15],
                10002: [67.5, 1.1, 0.0, -0.07],
                10003: [129.25, 0.2, 0.0, 0.09],
                10004: [201.75, -0.3, 0.0, 0.03],
                10026: [312.0, 0.8, 0.0, 0.05],
                10433: [299.8, -0.1, 0.0, 0.59],
                12: [217.84, -5.07, 0.0, 0.11],
                57: [217.38, 0.0, 0.0, 0.004],
            }
            return payloads[point_id], None

    monkeypatch.setattr(asteroids_module, "swe", FakeSwe())
    monkeypatch.setattr(asteroids_module, "_resolve_ephemeris_path", lambda: r"C:\Program Files (x86)\Galaxy\SwisEph")

    result = asteroids_module.compute_asteroid_positions(
        {"houses": _houses()},
        "2001-02-03T12:15:00+00:00",
        include_point_dependencies=True,
    )

    names = [item["name"] for item in result["items"]]
    assert result["status"] == "ok"
    assert names == [
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Proserpina",
        "Eros",
        "Lilith",
        "Selena",
    ]
    by_name = {item["name"]: item for item in result["items"]}
    assert by_name["Eros"]["galaxy_body_id"] == 15
    assert by_name["Lilith"]["galaxy_body_id"] == 18
    assert by_name["Selena"]["galaxy_body_id"] == 19


def test_points_chart_extension_upserts_point_dependency_bodies(monkeypatch):
    captured = {}

    def fake_extend(chart_data, *_args, **_kwargs):
        out = dict(chart_data)
        out["planets"] = list(chart_data.get("planets") or [])
        return out

    def fake_asteroids(_chart_data, _timestamp_iso, **kwargs):
        captured["include_point_dependencies"] = kwargs.get("include_point_dependencies")
        return {
            "items": [
                {"name": "Eros", "longitude": 11.0, "latitude": 0.1, "house": 1, "sign": "Aries", "degree_in_sign": 11.0, "speed": 0.5, "galaxy_body_id": 15},
                {"name": "Lilith", "longitude": 22.0, "latitude": -1.0, "house": 2, "sign": "Aries", "degree_in_sign": 22.0, "speed": 0.1, "galaxy_body_id": 18},
                {"name": "Selena", "longitude": 33.0, "latitude": 0.0, "house": 3, "sign": "Taurus", "degree_in_sign": 3.0, "speed": 0.01, "galaxy_body_id": 19},
            ],
            "missing": [],
            "status": "ok",
            "message": None,
            "ephemeris_available": True,
        }

    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_synastry", fake_extend)
    monkeypatch.setattr(astro_clock_api, "compute_asteroid_positions", fake_asteroids)

    result = astro_clock_api._extend_chart_data_for_points(
        {"houses": _houses(), "planets": [{"planet": "Sun", "longitude": 1.0}]},
        "2001-02-03T12:15:00+00:00",
    )

    planets = {row["planet"]: row for row in result["planets"]}
    assert captured["include_point_dependencies"] is True
    assert planets["Eros"]["longitude"] == 11.0
    assert planets["Lilith"]["longitude"] == 22.0
    assert planets["Selena"]["longitude"] == 33.0


def test_candidate_ephemeris_paths_prefers_source_bundle(monkeypatch):
    monkeypatch.delenv("VOX_STELLA_SWISSEPH_PATH", raising=False)
    monkeypatch.delenv("SWISSEPH_PATH", raising=False)
    monkeypatch.delenv("HORARY_BACKEND_DIR", raising=False)
    monkeypatch.delattr(asteroids_module.sys, "_MEIPASS", raising=False)

    paths = asteroids_module._candidate_ephemeris_paths()

    assert paths[0].endswith(r"backend\ephemeris\sweph")


def test_candidate_ephemeris_paths_include_packaged_runtime_and_resource_dirs(monkeypatch, tmp_path):
    monkeypatch.delenv("VOX_STELLA_SWISSEPH_PATH", raising=False)
    monkeypatch.delenv("SWISSEPH_PATH", raising=False)
    monkeypatch.delattr(asteroids_module.sys, "_MEIPASS", raising=False)

    runtime_dir = tmp_path / "resources" / "backend" / "runtime" / "horary_backend"
    monkeypatch.setenv("HORARY_BACKEND_DIR", str(runtime_dir))

    paths = asteroids_module._candidate_ephemeris_paths()

    assert str(runtime_dir / "_internal" / "ephemeris" / "sweph") in paths
    assert str(runtime_dir.parent.parent / "ephemeris" / "sweph") in paths


def test_compute_asteroid_positions_falls_back_when_existing_bundle_cannot_be_read(monkeypatch, tmp_path):
    bad_bundle = tmp_path / "resources" / "backend" / "runtime" / "horary_backend" / "_internal" / "ephemeris" / "sweph"
    good_bundle = tmp_path / "resources" / "backend" / "ephemeris" / "sweph"
    bad_bundle.mkdir(parents=True)
    good_bundle.mkdir(parents=True)

    class FakeSwe:
        AST_OFFSET = 10000
        FLG_SWIEPH = 1
        FLG_SPEED = 2
        GREG_CAL = 1

        def __init__(self):
            self.path = ""
            self.paths = []

        def julday(self, *_args):
            return 2461161.875

        def set_ephe_path(self, path):
            self.path = path
            self.paths.append(path)

        def calc_ut(self, _jd_ut, point_id, _flags):
            if self.path == str(bad_bundle):
                raise RuntimeError("SwissEph file not found in packaged _internal bundle")
            payloads = {
                10001: [48.68, 0.0, 0.0, 0.41],
                10002: [1.61, 0.0, 0.0, 0.31],
                10003: [307.62, 0.0, 0.0, 0.17],
                10004: [354.61, 0.0, 0.0, 0.45],
                10026: [190.26, 0.0, 0.0, -0.14],
            }
            return payloads[point_id], None

    fake_swe = FakeSwe()
    monkeypatch.setattr(asteroids_module, "swe", fake_swe)
    monkeypatch.setattr(
        asteroids_module,
        "_candidate_ephemeris_paths",
        lambda: [str(bad_bundle), str(good_bundle)],
    )

    result = asteroids_module.compute_asteroid_positions(
        {"houses": _houses()},
        "2026-05-01T09:00:00+00:00",
    )

    assert fake_swe.paths == [str(bad_bundle), "", str(good_bundle), ""]
    assert result["status"] == "ok"
    assert result["ephemeris_available"] is True
    assert result["missing"] == []
    assert [item["name"] for item in result["items"]] == [
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Proserpina",
    ]


def test_compute_asteroid_positions_serializes_swisseph_state_during_calculation(monkeypatch, tmp_path):
    import threading
    import time

    ephe_path = tmp_path / "ephemeris" / "sweph"
    ephe_path.mkdir(parents=True)
    observed = {"blocked_during_calc": False, "entered_after_calc": False}
    contender_thread = None

    def contender():
        with asteroids_module.swisseph_lock():
            observed["entered_after_calc"] = True

    class FakeSwe:
        AST_OFFSET = 10000
        FLG_SWIEPH = 1
        FLG_SPEED = 2
        GREG_CAL = 1

        def julday(self, *_args):
            return 2461161.875

        def set_ephe_path(self, _path):
            return None

        def calc_ut(self, _jd_ut, point_id, _flags):
            nonlocal contender_thread
            if point_id == 10001 and contender_thread is None:
                contender_thread = threading.Thread(target=contender)
                contender_thread.start()
                time.sleep(0.05)
                observed["blocked_during_calc"] = not observed["entered_after_calc"]
            payloads = {
                10001: [48.68, 0.0, 0.0, 0.41],
                10002: [1.61, 0.0, 0.0, 0.31],
                10003: [307.62, 0.0, 0.0, 0.17],
                10004: [354.61, 0.0, 0.0, 0.45],
                10026: [190.26, 0.0, 0.0, -0.14],
            }
            return payloads[point_id], None

    monkeypatch.setattr(asteroids_module, "swe", FakeSwe())
    monkeypatch.setattr(asteroids_module, "_candidate_ephemeris_paths", lambda: [str(ephe_path)])

    result = asteroids_module.compute_asteroid_positions(
        {"houses": _houses()},
        "2026-05-01T09:00:00+00:00",
    )
    contender_thread.join(timeout=1)

    assert result["status"] == "ok"
    assert observed == {"blocked_during_calc": True, "entered_after_calc": True}


def test_dashboard_payload_includes_almutens_and_asteroids(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "ascendant": 12.5,
                "midheaven": 281.25,
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Sun", "longitude": 15.0, "speed": 1.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 95.0, "speed": 13.0, "sign": "Cancer", "house": 4},
                ],
                "aspects": [],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    eng = SimpleNamespace(settings=settings)
    expected_almutens = {"items": [{"key": "ascendant", "leader": "Mars"}], "points": {}, "display_order": [], "sect": "Day"}
    expected_asteroids = {"items": [{"name": "Ceres"}], "missing": [], "status": "ok", "message": None, "ephemeris_available": True}
    expected_compass = {
        "azimuths": [{"planet": "Sun", "azimuth_deg": 181.2, "altitude_deg": 24.0, "longitude_deg": 15.0}],
        "ascendant": 12.5,
        "latitude": 31.78,
        "longitude": 35.22,
        "source": "local_space",
        "has_altitude": True,
    }

    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: expected_almutens)
    monkeypatch.setattr(astro_clock_api, "compute_asteroid_positions", lambda *args, **kwargs: expected_asteroids)
    monkeypatch.setattr(astro_clock_api, "_build_local_space_compass_payload", lambda *args, **kwargs: expected_compass)

    with app_module.app.test_request_context("/api/astro-clock/dashboard"):
        payload = astro_clock_api._build_dashboard_payload(eng, data)

    assert payload["almutens"] == expected_almutens
    assert payload["asteroids"] == expected_asteroids
    assert payload["compass"] == expected_compass
    assert payload["ascendant"] == 12.5
    assert payload["midheaven"] == 281.25


def test_dashboard_payload_augments_modern_planets_when_requested(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "ascendant": 12.5,
                "midheaven": 281.25,
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Sun", "longitude": 15.0, "speed": 1.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 95.0, "speed": 13.0, "sign": "Cancer", "house": 4},
                ],
                "aspects": [],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    eng = SimpleNamespace(settings=settings)

    def fake_extend(chart_data, meta, *, include_modern, include_chiron):
        assert include_modern is True
        assert include_chiron is False
        planets = list(chart_data.get("planets") or [])
        planets.append({"planet": "Uranus", "longitude": 120.0, "speed": 0.2, "sign": "Leo", "house": 5})
        out = dict(chart_data)
        out["planets"] = planets
        return out

    monkeypatch.setattr(astro_clock_api, "_extend_chart_data_for_synastry", fake_extend)
    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: {"items": [], "points": {}, "display_order": [], "sect": None})
    monkeypatch.setattr(astro_clock_api, "compute_asteroid_positions", lambda *args, **kwargs: {"items": [], "missing": [], "status": "ok", "message": None, "ephemeris_available": True})
    monkeypatch.setattr(astro_clock_api, "compute_planetary_aspects_precise", lambda *args, **kwargs: [])

    with app_module.app.test_request_context("/api/astro-clock/dashboard?include_modern=1"):
        payload = astro_clock_api._build_dashboard_payload(eng, data, include_modern=True)

    assert [row["planet"] for row in payload["planets"]] == ["Sun", "Moon", "Uranus"]


def test_dashboard_payload_uses_precise_aspects_and_dedupes_duplicates(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 16, 2, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Moon", "longitude": 95.0, "speed": 13.0, "sign": "Cancer", "house": 4},
                    {"planet": "Mars", "longitude": 97.1, "speed": 0.7, "sign": "Cancer", "house": 4},
                    {"planet": "Saturn", "longitude": 97.5, "speed": 0.1, "sign": "Cancer", "house": 4},
                ],
                "aspects": [
                    {"planet1": "Moon", "planet2": "Saturn", "aspect": "Conjunction", "orb": 2.1},
                ],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[
            {"planet1": "Moon", "planet2": "Saturn", "aspect": "Conjunction", "orb": 2.1},
        ],
    )
    eng = SimpleNamespace(settings=settings)

    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {"planetary_aspects": []})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: {"items": [], "points": {}, "display_order": [], "sect": None})
    monkeypatch.setattr(
        astro_clock_api,
        "compute_asteroid_positions",
        lambda *args, **kwargs: {"items": [], "missing": [], "status": "ok", "message": None, "ephemeris_available": True},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_planetary_aspects_precise",
        lambda *args, **kwargs: [
            {"planet1": "Moon", "planet2": "Saturn", "aspect": "Conjunction", "orb": 2.1, "phase": "separating"},
            {"planet1": "Saturn", "planet2": "Moon", "aspect": "Conjunction", "orb": 0.4, "phase": "applying"},
            {"planet1": "Mars", "planet2": "Saturn", "aspect": "Conjunction", "orb": 2.5, "phase": "applying"},
        ],
    )

    with app_module.app.test_request_context("/api/astro-clock/dashboard"):
        payload = astro_clock_api._build_dashboard_payload(eng, data)

    assert payload["tightest_aspect"]["planet1"] == "Saturn"
    assert payload["tightest_aspect"]["planet2"] == "Moon"
    assert payload["tightest_aspect"]["orb"] == 0.4
    assert payload["top_aspects"][0]["orb"] == 0.4
    assert len(payload["planetary_aspects_precise"]) == 2
    moon_saturn = [
        row for row in payload["planetary_aspects_precise"]
        if {row["planet1"], row["planet2"]} == {"Moon", "Saturn"} and row["aspect"] == "Conjunction"
    ]
    assert len(moon_saturn) == 1
    assert moon_saturn[0]["phase"] == "applying"


def test_dashboard_payload_normalizes_special_degrees_and_passes_arabic_parts_to_metrics(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Sun", "longitude": 15.0, "speed": 1.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 145.25, "speed": 13.0, "sign": "Leo", "house": 5},
                ],
                "aspects": [],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    eng = SimpleNamespace(settings=settings)
    expected_arabic_parts = {"fortune": {"name": "Part of Fortune", "lon": 145.25}}
    captured = {}

    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: expected_arabic_parts)
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        astro_clock_api,
        "compute_metrics",
        lambda cd, timestamp_iso=None, special_degrees=None: captured.update({
            "chart_data": cd,
            "special_degrees": special_degrees,
        }) or {"degree_hits": {"items": []}},
    )
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: {"items": [], "points": {}, "display_order": [], "sect": None})
    monkeypatch.setattr(
        astro_clock_api,
        "compute_asteroid_positions",
        lambda *args, **kwargs: {"items": [], "missing": [], "status": "ok", "message": None, "ephemeris_available": True},
    )

    with app_module.app.test_request_context(
        "/api/astro-clock/dashboard",
        query_string=[
            ("special_degree", "25°15' Leo"),
            ("special_degree", " 25°15' Leo "),
            ("special_degree", "Leo 25°15'"),
        ],
    ):
        payload = astro_clock_api._build_dashboard_payload(eng, data)

    assert payload["special_degrees"] == ["25°15' Leo", "Leo 25°15'"]
    assert captured["special_degrees"] == ["25°15' Leo", "Leo 25°15'"]
    assert captured["chart_data"]["arabic_parts"] == expected_arabic_parts


def test_dashboard_payload_reuses_cached_morin_payload_for_the_same_chart(monkeypatch):
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "houses": _houses(),
                "house_rulers": {"1": "Mars"},
                "planets": [
                    {"planet": "Sun", "longitude": 28.0, "speed": 1.0, "sign": "Aries", "house": 1},
                    {"planet": "Moon", "longitude": 118.0, "speed": 13.0, "sign": "Cancer", "house": 4},
                ],
                "aspects": [],
            }
        },
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    eng = SimpleNamespace(settings=settings)
    calls = {"aspects": 0, "antiscia": 0, "contra": 0, "combustion": 0, "patterns": 0}

    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: {"items": [], "points": {}, "display_order": [], "sect": None})
    monkeypatch.setattr(
        astro_clock_api,
        "compute_asteroid_positions",
        lambda *args, **kwargs: {"items": [], "missing": [], "status": "ok", "message": None, "ephemeris_available": True},
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_morin_aspects",
        lambda *args, **kwargs: calls.__setitem__("aspects", calls["aspects"] + 1) or [
            {"planet1": "Sun", "planet2": "Moon", "aspect": "Trine", "orb": 1.2, "max_orb": 10.0}
        ],
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_morin_antiscia",
        lambda *args, **kwargs: calls.__setitem__("antiscia", calls["antiscia"] + 1) or [
            {"planet1": "Sun", "planet2": "Moon", "aspect": "Antiscia", "orb": 0.4, "max_orb": 1.0}
        ],
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_morin_contra_antiscia",
        lambda *args, **kwargs: calls.__setitem__("contra", calls["contra"] + 1) or [
            {"planet1": "Sun", "planet2": "Moon", "aspect": "Contra-antiscia", "orb": 0.7, "max_orb": 1.0}
        ],
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_morin_combustion",
        lambda *args, **kwargs: calls.__setitem__("combustion", calls["combustion"] + 1) or [
            {"planet": "Mercury", "status": "under_beams", "distance_deg": 5.5}
        ],
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_morin_patterns",
        lambda *args, **kwargs: calls.__setitem__("patterns", calls["patterns"] + 1) or {"stellium": ["Sun", "Moon"]},
    )

    with astro_clock_api._MORIN_PAYLOAD_CACHE_LOCK:
        astro_clock_api._MORIN_PAYLOAD_CACHE.clear()

    with app_module.app.test_request_context("/api/astro-clock/dashboard"):
        first_payload = astro_clock_api._build_dashboard_payload(eng, data, include_morin=True)
        second_payload = astro_clock_api._build_dashboard_payload(eng, data, include_morin=True)

    first_payload["morin_aspects"][0]["planet1"] = "Changed"

    assert first_payload["morin_antiscia"]
    assert second_payload["morin_aspects"][0]["planet1"] == "Sun"
    assert second_payload["morin_patterns"] == {"stellium": ["Sun", "Moon"]}
    assert calls == {"aspects": 1, "antiscia": 1, "contra": 1, "combustion": 1, "patterns": 1}


def _compass_fixture():
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
        latitude=31.778,
        longitude=35.235,
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "ascendant": 15.0,
                "planets": [
                    {"planet": "Sun", "longitude": 15.0},
                    {"planet": "Mercury", "longitude": 45.0},
                    {"planet": "Uranus", "longitude": 90.0},
                ],
            }
        },
    )
    return data, settings


def test_compass_endpoint_prefers_local_space_payload(monkeypatch):
    client = app_module.app.test_client()
    data, settings = _compass_fixture()

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: SimpleNamespace(settings=settings))
    monkeypatch.setattr(astro_clock_api, "_data_for_request_clock_context", lambda _eng: (data, settings))
    monkeypatch.setattr(
        local_space_module,
        "compute_local_space",
        lambda _timestamp, _lat, _lon, planets: {
            planet: {"azimuth_deg": 90.0 + (index * 15.0), "altitude_deg": 20.0 + index}
            for index, planet in enumerate(planets)
        },
    )

    response = client.get("/api/astro-clock/compass?include_modern=1")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["source"] == "local_space"
    assert payload["data"]["has_altitude"] is True
    assert [row["planet"] for row in payload["data"]["azimuths"]] == ["Sun", "Mercury", "Uranus"]
    assert payload["data"]["azimuths"][0]["altitude_deg"] == 20.0
    assert payload["data"]["azimuths"][2]["longitude_deg"] == 90.0


def test_compass_endpoint_uses_resolved_engine_defaults(monkeypatch):
    client = app_module.app.test_client()
    engine = astro_clock_engine_module.AstroClockEngine()

    monkeypatch.setattr(
        engine.horary_engine,
        "judge",
        lambda _question, _settings: {
            "chart_data": {
                "ascendant": 15.0,
                "planets": [
                    {"planet": "Sun", "longitude": 15.0},
                    {"planet": "Moon", "longitude": 45.0},
                ],
            }
        },
    )
    monkeypatch.setattr(engine, "_calculate_moon_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(engine, "_calculate_dispositor_chains", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(engine, "_extract_aspects_from_result", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(
        local_space_module,
        "compute_local_space",
        lambda _timestamp, _lat, _lon, planets: {
            planet: {"azimuth_deg": 110.0 + (index * 12.0), "altitude_deg": 25.0 + index}
            for index, planet in enumerate(planets)
        },
    )

    response = client.get("/api/astro-clock/compass")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["source"] == "local_space"
    assert payload["data"]["latitude"] == 51.4769
    assert payload["data"]["longitude"] == -0.0005
    assert [row["planet"] for row in payload["data"]["azimuths"]] == ["Sun", "Moon"]


def test_compass_endpoint_reports_local_space_failure_instead_of_approximating(monkeypatch):
    client = app_module.app.test_client()
    data, settings = _compass_fixture()

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: SimpleNamespace(settings=settings))
    monkeypatch.setattr(astro_clock_api, "_data_for_request_clock_context", lambda _eng: (data, settings))

    def _raise_local_space(*_args, **_kwargs):
        raise RuntimeError("local space unavailable")

    monkeypatch.setattr(local_space_module, "compute_local_space", _raise_local_space)

    response = client.get("/api/astro-clock/compass")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["success"] is False
    assert payload["error"] == "Local-space calculation is unavailable"


def test_create_snap_and_list_snaps_preserve_saved_context(monkeypatch):
    client = app_module.app.test_client()
    settings = SimpleNamespace(
        mode=SimpleNamespace(value="manual"),
        location="Jerusalem, Israel",
        custom_time=None,
        timezone="Asia/Jerusalem",
        house_system_code="R",
        latitude=31.778,
        longitude=35.235,
    )
    data = SimpleNamespace(
        timestamp=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
        settings=settings,
        chart_result={"chart_data": {"planets": [{"planet": "Moon", "sign": "Capricorn"}]}},
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )

    class DummyStore:
        def __init__(self):
            self.items = []

        def add(self, snap):
            self.items.append(snap)

        def list(self):
            return list(self.items)

    store = DummyStore()
    engine = SimpleNamespace(settings=settings, get_current_data=lambda: data)

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda *_args, **_kwargs: {
            "timezone": "Asia/Jerusalem",
            "timezone_label": "Asia/Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "planets": [{"planet": "Moon", "sign": "Capricorn"}],
        },
    )
    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", lambda *_args, **_kwargs: (31.778, 35.235))
    monkeypatch.setattr(
        astro_clock_api,
        "_ph_instance",
        lambda *_args, **_kwargs: SimpleNamespace(
            get_current_planetary_hour=lambda _dt: SimpleNamespace(
                ruling_planet=SimpleNamespace(value="Saturn")
            )
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_synastry_chart_snapshot_from_chart_data",
        lambda *_args, **_kwargs: {"chart": "snapshot"},
    )
    monkeypatch.setattr(astro_clock_api, "_extract_synastry_profile_hint", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        astro_clock_api,
        "compute_sect_info",
        lambda *_args, **_kwargs: {"chart_sect": "Nocturnal", "sect_light": "Moon"},
    )

    response = client.post("/api/astro-clock/snap", json={"label": "Natal"})
    payload = response.get_json()
    listing = client.get("/api/astro-clock/snaps").get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert store.items[0]["timezone"] == "Asia/Jerusalem"
    assert store.items[0]["latitude"] == 31.778
    assert store.items[0]["longitude"] == 35.235
    assert listing["success"] is True
    assert listing["items"][0]["dashboard"] == {
        "timezone": "Asia/Jerusalem",
        "timezone_label": "Asia/Jerusalem (UTC+03:00)",
        "latitude": 31.778,
        "longitude": 35.235,
    }


def test_create_snap_uses_applied_dashboard_without_recomputing(monkeypatch):
    client = app_module.app.test_client()

    class DummyStore:
        def __init__(self):
            self.items = []

        def add(self, snap):
            self.items.append(snap)

    store = DummyStore()
    settings = astro_clock_api.AstroClockSettings(
        mode=astro_clock_api.ClockMode.REALTIME,
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    def _unexpected_chart_generation(*_args, **_kwargs):
        raise AssertionError("snap should persist the applied dashboard instead of regenerating the chart")

    engine = SimpleNamespace(
        settings=settings,
        get_current_data=_unexpected_chart_generation,
        get_effective_datetime=lambda: datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: store)
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(astro_clock_api, "_build_dashboard_payload", _unexpected_chart_generation)
    monkeypatch.setattr(
        astro_clock_api,
        "_ph_instance",
        lambda *_args, **_kwargs: SimpleNamespace(
            get_current_planetary_hour=lambda _dt: SimpleNamespace(
                ruling_planet=SimpleNamespace(value="Saturn")
            )
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "compute_sect_info",
        lambda *_args, **_kwargs: {"chart_sect": "Nocturnal", "sect_light": "Moon"},
    )

    dashboard = {
        "timestamp": "2001-02-03T10:00:00+00:00",
        "location": "Jerusalem, Israel",
        "timezone": "Asia/Jerusalem",
        "timezone_label": "Asia/Jerusalem",
        "latitude": 31.778,
        "longitude": 35.235,
        "house_system_code": "R",
        "planets": [{"planet": "Moon", "sign": "Capricorn", "longitude": 293.0}],
        "house_cusps": _houses(),
        "house_rulers": {"1": "Mars"},
    }

    response = client.post(
        "/api/astro-clock/snap",
        json={
            "label": "Applied manual chart",
            "mode": "manual",
            "datetime": "2001-02-03T12:00:00",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
            "house_system_code": "R",
            "dashboard": dashboard,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert store.items[0]["label"] == "Applied manual chart"
    assert store.items[0]["effective_datetime"] == "2001-02-03T10:00:00+00:00"
    assert store.items[0]["location"] == "Jerusalem, Israel"
    assert store.items[0]["timezone"] == "Asia/Jerusalem"
    assert store.items[0]["latitude"] == 31.778
    assert store.items[0]["longitude"] == 35.235
    assert store.items[0]["dashboard"]["planets"] == dashboard["planets"]
    assert store.items[0]["chart_snapshot"]["planets"] == dashboard["planets"]


def test_get_snap_does_not_infer_missing_legacy_coordinates_during_read(monkeypatch):
    client = app_module.app.test_client()

    class DummyStore:
        def get(self, snap_id):
            if snap_id != "legacy-snap":
                return None
            return {
                "id": snap_id,
                "label": "Synthetic legacy chart without coordinates",
                "effective_datetime": "2001-02-03T12:15:00+00:00",
                "location": "israel",
                "timezone": None,
                "latitude": None,
                "longitude": None,
                "dashboard": {},
            }

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: DummyStore())
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("saved-chart reads must not geocode")
        ),
    )
    monkeypatch.setattr(
        astro_clock_api,
        "_resolve_timezone_for_context",
        lambda *_args, **_kwargs: "Asia/Jerusalem",
    )

    response = client.get("/api/astro-clock/snaps/legacy-snap")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["snap"]["timezone"] is None
    assert payload["snap"]["latitude"] is None
    assert payload["snap"]["longitude"] is None
    assert payload["snap"]["dashboard"]["timezone"] is None
    assert "latitude" not in payload["snap"]["dashboard"]
    assert "longitude" not in payload["snap"]["dashboard"]
    assert payload["snap"]["coordinate_provenance"]["source"] == "missing"
    assert payload["snap"]["resolved_context"]["chart_native"] is False


def test_specific_snap_bundle_reuses_hydrated_snap_coordinates(monkeypatch):
    class DummyStore:
        def get(self, snap_id):
            assert snap_id == "manual-snap"
            return {
                "id": snap_id,
                "effective_datetime": "2026-05-06T16:23:00+00:00",
                "location": "Salt Lake City, Utah",
                "timezone": "America/Denver",
                "latitude": 39.321,
                "longitude": -111.0937,
                "dashboard": {},
            }

    captured = {}

    def _fake_compute(dt_iso, location, timezone_name, house_system_code=None, **kwargs):
        captured.update(
            {
                "dt_iso": dt_iso,
                "location": location,
                "timezone": timezone_name,
                "house_system_code": house_system_code,
                "latitude": kwargs.get("latitude"),
                "longitude": kwargs.get("longitude"),
            }
        )
        return {"chart_data": {}, "meta": {}}

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: DummyStore())
    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute)

    astro_clock_api._bundle_from_snap_id("manual-snap", house_system_code="R")

    assert captured == {
        "dt_iso": "2026-05-06T16:23:00+00:00",
        "location": "Salt Lake City, Utah",
        "timezone": "America/Denver",
        "house_system_code": "R",
        "latitude": 39.321,
        "longitude": -111.0937,
    }


def test_compute_chart_bundle_with_valid_timezone_defers_coordinates_to_engine(monkeypatch):
    captured = {}
    previous_settings = astro_clock_api.AstroClockSettings(
        mode=astro_clock_api.ClockMode.REALTIME,
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )

    def _get_current_data(settings=None):
        captured["settings"] = settings
        captured["input_latitude"] = settings.latitude
        captured["input_longitude"] = settings.longitude
        return SimpleNamespace(
            timestamp=datetime(2026, 5, 6, 18, 23, tzinfo=timezone.utc),
            settings=settings,
            chart_result={
                "chart_data": {
                    "timezone_info": {
                        "timezone": "America/Denver",
                        "coordinates": {
                            "latitude": 39.321,
                            "longitude": -111.0937,
                        },
                    },
                    "planets": [],
                },
            },
        )

    monkeypatch.setattr(
        astro_clock_api,
        "_engine_instance",
        lambda: SimpleNamespace(settings=previous_settings, get_current_data=_get_current_data),
    )

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("valid timezone should let the horary engine own coordinate resolution")

    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    bundle = astro_clock_api._compute_chart_bundle_for(
        "2026-05-06T12:23:00",
        "utah",
        "America/Denver",
        house_system_code="R",
    )

    assert captured["settings"].location == "utah"
    assert captured["settings"].timezone == "America/Denver"
    assert captured["input_latitude"] is None
    assert captured["input_longitude"] is None
    assert bundle["meta"]["latitude"] == 39.321
    assert bundle["meta"]["longitude"] == -111.0937


def test_manual_mode_prefers_explicit_coords_from_payload(monkeypatch):
    client = app_module.app.test_client()

    class DummyMode:
        MANUAL = "manual-mode"
        REALTIME = "realtime-mode"

        def __init__(self, value):
            self.value = value

    captured = {}
    settings = SimpleNamespace(
        mode=DummyMode("realtime"),
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )
    engine = SimpleNamespace(
        settings=settings,
        update_settings=lambda **_kwargs: None,
        set_mode=lambda selected_mode, **kwargs: captured.update({"mode": selected_mode, **kwargs}),
        pause_at_current_time=lambda: None,
        resume_realtime=lambda: None,
    )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(
        astro_clock_api,
        "_normalize_manual_datetime",
        lambda *_args, **_kwargs: (datetime(2001, 2, 3, 12, 0, tzinfo=timezone.utc), "Asia/Jerusalem"),
    )

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("explicit snap coordinates should bypass location geocoding")

    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    response = client.post(
        "/api/astro-clock/mode",
        json={
            "mode": "manual",
            "datetime": "2001-02-03T12:00:00Z",
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "latitude": 31.778,
            "longitude": 35.235,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert captured["mode"] == "manual-mode"
    assert captured["location"] == "Jerusalem, Israel"
    assert captured["timezone"] == "Asia/Jerusalem"
    assert captured["latitude"] == 31.778
    assert captured["longitude"] == 35.235


def test_manual_mode_with_valid_timezone_defers_location_resolution_to_engine(monkeypatch):
    client = app_module.app.test_client()

    class DummyMode:
        MANUAL = "manual-mode"
        REALTIME = "realtime-mode"

        def __init__(self, value):
            self.value = value

    captured = {}
    settings = SimpleNamespace(
        mode=DummyMode("realtime"),
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
    )
    engine = SimpleNamespace(
        settings=settings,
        update_settings=lambda **_kwargs: None,
        set_mode=lambda selected_mode, **kwargs: captured.update({"mode": selected_mode, **kwargs}),
        pause_at_current_time=lambda: None,
        resume_realtime=lambda: None,
    )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(
        astro_clock_api,
        "_normalize_manual_datetime",
        lambda *_args, **_kwargs: (datetime(2026, 5, 6, 18, 23, tzinfo=timezone.utc), "America/Denver"),
    )

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("valid timezone should let Astro Clock defer geocoding to the horary engine")

    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    response = client.post(
        "/api/astro-clock/mode",
        json={
            "mode": "manual",
            "datetime": "2026-05-06T12:23:00",
            "location": "utah",
            "timezone": "America/Denver",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert captured["mode"] == "manual-mode"
    assert captured["location"] == "utah"
    assert captured["timezone"] == "America/Denver"
    assert captured["latitude"] is None
    assert captured["longitude"] is None


def test_dashboard_manual_context_uses_coords_timezone_for_datetime(monkeypatch):
    client = app_module.app.test_client()

    captured = {}
    previous_settings = SimpleNamespace(
        mode=astro_clock_api.ClockMode.REALTIME,
        location="Greenwich, UK",
        timezone="Europe/London",
        latitude=51.4769,
        longitude=-0.0005,
        custom_time=None,
        paused_at=None,
        house_system_code="regiomontanus",
    )

    def _get_current_data(settings=None):
        captured["settings"] = settings
        return SimpleNamespace(settings=settings)

    engine = SimpleNamespace(settings=previous_settings, get_current_data=_get_current_data)

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: engine)
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda _eng, data, **_kwargs: {
            "mode": getattr(data.settings.mode, "value", data.settings.mode),
            "location": data.settings.location,
            "timezone": data.settings.timezone,
            "latitude": data.settings.latitude,
            "longitude": data.settings.longitude,
        },
    )

    def _unexpected_geocode(*_args, **_kwargs):
        raise AssertionError("dashboard manual context should reuse explicit coordinates")

    monkeypatch.setattr(astro_clock_api, "_ensure_coords_for_location", _unexpected_geocode)

    def _resolve_timezone(timezone_name, location, *, coords=None):
        captured["resolve"] = {
            "timezone_name": timezone_name,
            "location": location,
            "coords": coords,
        }
        if coords == (31.778, 35.235):
            return "Asia/Jerusalem"
        return timezone_name

    monkeypatch.setattr(astro_clock_api, "_resolve_timezone_for_context", _resolve_timezone)

    def _normalize_manual_datetime(dt_raw, *, timezone_name, location):
        captured["normalize"] = {
            "dt_raw": dt_raw,
            "timezone_name": timezone_name,
            "location": location,
        }
        assert timezone_name == "Asia/Jerusalem"
        return datetime(2001, 2, 3, 10, 0, tzinfo=timezone.utc), timezone_name

    monkeypatch.setattr(astro_clock_api, "_normalize_manual_datetime", _normalize_manual_datetime)

    response = client.get(
        "/api/astro-clock/dashboard"
        "?mode=manual"
        "&datetime=2001-02-03T12:00:00"
        "&location=Jerusalem%2C%20Israel"
        "&latitude=31.778"
        "&longitude=35.235"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["mode"] == "manual"
    assert payload["data"]["location"] == "Jerusalem, Israel"
    assert payload["data"]["timezone"] == "Asia/Jerusalem"
    assert payload["data"]["latitude"] == 31.778
    assert payload["data"]["longitude"] == 35.235
    assert captured["resolve"]["coords"] == (31.778, 35.235)
    assert captured["normalize"]["timezone_name"] == "Asia/Jerusalem"
