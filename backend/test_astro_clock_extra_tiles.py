from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import asteroids as asteroids_module
from almutens import compute_almuten_for_longitude, compute_chart_almutens


def _houses():
    return [i * 30.0 for i in range(12)]


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


def test_candidate_ephemeris_paths_prefers_source_bundle(monkeypatch):
    monkeypatch.delenv("VOX_STELLA_SWISSEPH_PATH", raising=False)
    monkeypatch.delenv("SWISSEPH_PATH", raising=False)
    monkeypatch.delattr(asteroids_module.sys, "_MEIPASS", raising=False)

    paths = asteroids_module._candidate_ephemeris_paths()

    assert paths[0].endswith(r"backend\ephemeris\sweph")


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

    monkeypatch.setattr(astro_clock_api, "compute_fixed_star_hits", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "compute_arabic_parts", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", lambda *args, **kwargs: {"mutual": [], "top_unilateral": []})
    monkeypatch.setattr(astro_clock_api, "compute_cusp_aspects", lambda *args, **kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_chart_almutens", lambda *args, **kwargs: expected_almutens)
    monkeypatch.setattr(astro_clock_api, "compute_asteroid_positions", lambda *args, **kwargs: expected_asteroids)

    with app_module.app.test_request_context("/api/astro-clock/dashboard"):
        payload = astro_clock_api._build_dashboard_payload(eng, data)

    assert payload["almutens"] == expected_almutens
    assert payload["asteroids"] == expected_asteroids


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
