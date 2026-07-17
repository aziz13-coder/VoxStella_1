from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask
import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
from backend.astro_clock_engine import AstroClockSettings, ClockMode


class _SentinelChart:
    pass


def _stub_clock_settings():
    return AstroClockSettings(
        mode=ClockMode.REALTIME,
        location="Greenwich, UK",
        timezone="UTC",
        custom_time=None,
        latitude=51.4769,
        longitude=-0.0005,
        paused_at=None,
        house_system_code="R",
    )


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def test_receptions_fallback_prefers_internal_raw_chart(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        settings = _stub_clock_settings()

        def get_current_data(self, settings=None):
            return types.SimpleNamespace(
                settings=settings or self.settings,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": sentinel,
                }
            )

    class _FakeCalc:
        def calculate_comprehensive_reception(self, chart_obj, _a, _b):
            assert chart_obj is sentinel
            return {"type": "none", "traditional_strength": 0}

        def does_planet_receive(self, chart_obj, _receiver, _received):
            assert chart_obj is sentinel
            return {"has_reception": False, "dignities": [], "reception_strength": 0}

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "TraditionalReceptionCalculator", _FakeCalc)
    monkeypatch.setattr(
        astro_clock_api,
        "deserialize_chart_for_evaluation",
        lambda _chart_data: (_ for _ in ()).throw(AssertionError("deserialize should not be called")),
    )

    app = _make_app()
    client = app.test_client()

    response = client.get("/api/astro-clock/receptions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["traditional_reception"]["type"] == "none"
    assert payload["data"]["mutual"] == []
    assert payload["data"]["top_unilateral"] == []


def test_receptions_summary_ignores_legacy_reception_without_detail(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        settings = _stub_clock_settings()

        def get_current_data(self, settings=None):
            return types.SimpleNamespace(
                settings=settings or self.settings,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "traditional_factors": {
                        "reception": "mixed_reception",
                    },
                    "_raw_chart": sentinel,
                }
            )

    class _FakeCalc:
        def calculate_comprehensive_reception(self, chart_obj, _a, _b):
            assert chart_obj is sentinel
            return {"type": "none", "traditional_strength": 0}

        def does_planet_receive(self, chart_obj, _receiver, _received):
            assert chart_obj is sentinel
            return {"has_reception": False, "dignities": [], "reception_strength": 0}

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "TraditionalReceptionCalculator", _FakeCalc)
    monkeypatch.setattr(
        astro_clock_api,
        "deserialize_chart_for_evaluation",
        lambda _chart_data: (_ for _ in ()).throw(AssertionError("deserialize should not be called")),
    )

    app = _make_app()
    client = app.test_client()

    response = client.get("/api/astro-clock/receptions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["traditional_reception"]["type"] == "none"
    assert payload["data"]["traditional_reception"]["display_text"] == "No reception"
    assert payload["data"]["mutual"] == []
    assert payload["data"]["top_unilateral"] == []


def test_receptions_summary_tracks_computed_mutual_pairs(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        settings = _stub_clock_settings()

        def get_current_data(self, settings=None):
            return types.SimpleNamespace(
                settings=settings or self.settings,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": sentinel,
                }
            )

    class _FakeCalc:
        def calculate_comprehensive_reception(self, chart_obj, a, b):
            assert chart_obj is sentinel
            if {a.value, b.value} == {"Venus", "Mars"}:
                return {"type": "mixed_reception", "traditional_strength": 5}
            return {"type": "none", "traditional_strength": 0}

        def does_planet_receive(self, chart_obj, _receiver, _received):
            assert chart_obj is sentinel
            return {"has_reception": False, "dignities": [], "reception_strength": 0}

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "TraditionalReceptionCalculator", _FakeCalc)
    monkeypatch.setattr(
        astro_clock_api,
        "deserialize_chart_for_evaluation",
        lambda _chart_data: (_ for _ in ()).throw(AssertionError("deserialize should not be called")),
    )

    app = _make_app()
    client = app.test_client()

    response = client.get("/api/astro-clock/receptions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["traditional_reception"]["type"] == "mixed_reception"
    assert payload["data"]["traditional_reception"]["display_text"] == "Mixed reception"
    assert payload["data"]["traditional_reception"]["mutual_count"] == 1
    assert len(payload["data"]["mutual"]) == 1
    pair = payload["data"]["mutual"][0]
    assert {pair["p1"], pair["p2"]} == {"Venus", "Mars"}
    assert pair["type"] == "mixed_reception"
    assert pair["strength"] == 5


def test_dashboard_includes_chart_scoped_receptions(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        settings = types.SimpleNamespace(location="City of London", timezone="Europe/London")

        def get_current_data(self, settings=None):
            return types.SimpleNamespace(
                timestamp=datetime(2025, 9, 27, 16, 25, tzinfo=timezone.utc),
                settings=settings or types.SimpleNamespace(location="City of London", timezone="Europe/London"),
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": sentinel,
                },
            )

    class _FakeCalc:
        def calculate_comprehensive_reception(self, chart_obj, a, b):
            assert chart_obj is sentinel
            if {a.value, b.value} == {"Venus", "Mars"}:
                return {"type": "mixed_reception", "traditional_strength": 5}
            return {"type": "none", "traditional_strength": 0}

        def does_planet_receive(self, chart_obj, _receiver, _received):
            assert chart_obj is sentinel
            return {"has_reception": False, "dignities": [], "reception_strength": 0}

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "TraditionalReceptionCalculator", _FakeCalc)
    monkeypatch.setattr(
        astro_clock_api,
        "_serialize_real_time",
        lambda _data: {"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
    )
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *_args, **_kwargs: {})

    app = _make_app()
    client = app.test_client()

    response = client.get("/api/astro-clock/dashboard")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    receptions = payload["data"]["receptions"]
    assert receptions["traditional_reception"]["type"] == "mixed_reception"
    assert receptions["traditional_reception"]["display_text"] == "Mixed reception"
    assert receptions["traditional_reception"]["mutual_count"] == 1
    assert len(receptions["mutual"]) == 1
    assert receptions["top_unilateral"] == []


def test_receptions_route_honors_manual_request_context(monkeypatch):
    sentinel = _SentinelChart()
    captured = {}

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="Greenwich, UK",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.4769,
            longitude=-0.0005,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            captured["settings"] = settings
            return types.SimpleNamespace(
                timestamp=datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc),
                settings=settings or self.settings,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": sentinel,
                },
            )

    class _FakeCalc:
        def calculate_comprehensive_reception(self, chart_obj, _a, _b):
            assert chart_obj is sentinel
            return {"type": "none", "traditional_strength": 0}

        def does_planet_receive(self, chart_obj, _receiver, _received):
            assert chart_obj is sentinel
            return {"has_reception": False, "dignities": [], "reception_strength": 0}

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "TraditionalReceptionCalculator", _FakeCalc)

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/receptions"
        "?mode=manual"
        "&datetime=2026-03-22T06%3A32%3A00"
        "&location=Israel"
        "&timezone=Asia%2FJerusalem"
        "&latitude=31.778"
        "&longitude=35.235"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    settings = captured["settings"]
    assert settings is not None
    assert settings.mode.value == ClockMode.MANUAL.value
    assert settings.location == "Israel"
    assert settings.timezone == "Asia/Jerusalem"
    assert settings.latitude == 31.778
    assert settings.longitude == 35.235


def test_current_route_honors_manual_request_context(monkeypatch):
    captured = {}

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="Greenwich, UK",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.4769,
            longitude=-0.0005,
            paused_at=None,
            house_system_code="P",
        )

        def get_current_data(self, settings=None):
            captured["settings"] = settings
            active_settings = settings or self.settings
            return types.SimpleNamespace(
                timestamp=datetime(2026, 3, 22, 4, 32, tzinfo=timezone.utc),
                settings=active_settings,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                },
                moon_state=None,
                dispositor_chains={},
                current_aspects=[],
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/current"
        "?mode=manual"
        "&datetime=2026-03-22T06%3A32%3A00"
        "&location=Israel"
        "&timezone=Asia%2FJerusalem"
        "&latitude=31.778"
        "&longitude=35.235"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    settings = captured["settings"]
    assert settings is not None
    assert settings.mode.value == ClockMode.MANUAL.value
    assert settings.location == "Israel"
    assert settings.timezone == "Asia/Jerusalem"
    assert settings.latitude == 31.778
    assert settings.longitude == 35.235
    assert settings.house_system_code == "R"


def test_directional_3d_route_returns_chart_context_and_coordinate_rows(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        astro_clock_api,
        "_directional_equatorial_from_swiss",
        lambda name, _timestamp_iso: (1.4, 0.7, 0.981, 0.002) if name == "Sun" else None,
    )

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="Greenwich, UK",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.4769,
            longitude=-0.0005,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            captured["settings"] = settings
            return types.SimpleNamespace(
                timestamp=datetime(2026, 3, 22, 4, 32, tzinfo=timezone.utc),
                settings=active,
                chart_result={
                    "chart_data": {
                        "planets": [
                            {
                                "planet": "Sun",
                                "longitude": 1.5,
                                "latitude": 0.1,
                                "speed": 0.98,
                            },
                            {
                                "planet": "Moon",
                                "longitude": 45.0,
                                "latitude": 3.2,
                                "speed": 13.4,
                                "equatorial_longitude": 46.1,
                                "declination": 19.2,
                                "equatorial_speed": 12.9,
                                "declination_speed": -0.22,
                            },
                            {
                                "planet": "Uranus",
                                "longitude": 216.75,
                                "latitude": -0.4,
                                "speed": 0.03,
                            },
                            {
                                "planet": "Hidden Test Point",
                                "longitude": 90.0,
                                "latitude": 0.0,
                                "speed": 0.0,
                                "bnotuse": True,
                            },
                        ],
                        "house_cusps": [18.0, 44.0, 71.0, 99.0, 130.0, 159.0, 198.0, 224.0, 251.0, 279.0, 310.0, 339.0],
                        "house_system_code": "R",
                    },
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/directional-3d"
        "?mode=manual"
        "&datetime=2026-03-22T06%3A32%3A00"
        "&location=Israel"
        "&timezone=Asia%2FJerusalem"
        "&latitude=31.778"
        "&longitude=35.235"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["chart_info"]["utc_datetime"] == "2026-03-22T04:32:00+00:00"
    assert data["chart_info"]["latitude"] == 31.778
    assert data["chart_info"]["longitude"] == 35.235
    assert data["chart_info"]["rotation"] == 9
    assert data["chart_info"]["tilt"] == 19
    assert data["chart_info"]["house_system"] == "R"
    assert data["chart_info"]["obliquity"] != 23.4392911
    assert data["chart_info"]["obliquity_source"] in {"chart", "swisseph", "mean_formula"}
    assert data["systems"] == ["EQL", "EQU", "HOR"]

    sun = next(row for row in data["objects"] if row["name"] == "Sun")
    assert sun["buse"] is True
    assert sun["bfull"] is True
    assert sun["object_type"] == "planet"
    assert sun["symbol"] == "☉"
    assert sun["EQL"] == {"longitude": 1.5, "latitude": 0.1, "speed": 0.98}
    assert set(sun["EQU"]) == {"longitude", "latitude", "speed", "latitude_speed"}
    assert set(sun["HOR"]) == {"longitude", "latitude", "speed", "latitude_speed"}
    assert sun["coordinate_meta"]["EQL"]["source"] == "chart_ecliptic"
    assert sun["coordinate_meta"]["EQU"]["source"] == "derived_from_ecliptic"
    assert sun["coordinate_meta"]["EQU"]["speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["speed_provider"] == "swisseph"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_provider"] == "swisseph"
    assert sun["coordinate_meta"]["HOR"]["source"] in {"swisseph_azalt", "equatorial_fallback"}
    assert sun["coordinate_meta"]["HOR"]["speed_source"] == "finite_difference"
    assert sun["coordinate_meta"]["HOR"]["latitude_speed_source"] == "finite_difference"
    assert abs(sun["HOR"]["speed"]) > 0.001
    assert sun["HOR"]["latitude_speed"] is not None
    moon = next(row for row in data["objects"] if row["name"] == "Moon")
    assert moon["EQU"]["speed"] == 12.9
    assert moon["EQU"]["latitude_speed"] == -0.22
    assert moon["coordinate_meta"]["EQU"]["source"] == "chart_equatorial"
    assert moon["coordinate_meta"]["EQU"]["speed_source"] == "native"
    assert moon["coordinate_meta"]["EQU"]["latitude_speed_source"] == "native"
    assert {
        "code": "equatorial_speed_fallback",
        "object_id": "planet:Sun",
        "object": "Sun",
    } not in data["chart_info"]["data_gaps"]
    assert any(row["name"] == "Uranus" for row in data["objects"])
    assert not any(row["name"] == "Hidden Test Point" for row in data["objects"])

    cusp = next(row for row in data["objects"] if row["name"] == "House 1")
    assert cusp["buse"] is True
    assert cusp["bfull"] is False
    assert cusp["object_type"] == "cusp"
    assert cusp["EQL"]["longitude"] == 18.0
    assert cusp["EQL"]["latitude"] == 0.0
    assert cusp["EQU"]["longitude"] == 18.0
    assert cusp["EQU"]["latitude"] == 0.0
    assert cusp["coordinate_meta"]["EQU"]["speed_source"] == "cusp_static"
    assert cusp["coordinate_meta"]["EQU"]["latitude_speed_source"] == "cusp_static"
    assert cusp["coordinate_meta"]["HOR"]["speed_source"] == "cusp_static"
    assert cusp["coordinate_meta"]["HOR"]["latitude_speed_source"] == "cusp_static"
    assert cusp["HOR"]["speed"] == 0.0
    assert cusp["HOR"]["latitude_speed"] == 0.0
    assert captured["settings"].location == "Israel"


def test_directional_3d_derives_equatorial_speed_from_ecliptic_rates():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Fixture",
        timezone="UTC",
        custom_time=datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc),
        latitude=31.778,
        longitude=35.235,
        paused_at=None,
        house_system_code="R",
    )
    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": [
                {
                    "planet": "Derived Example",
                    "longitude": 120.0,
                    "latitude": 5.0,
                    "speed": 1.0,
                    "latitude_speed": 0.1,
                },
                {
                    "planet": "No Latitude Speed",
                    "longitude": 120.0,
                    "latitude": 5.0,
                    "speed": 1.0,
                },
            ],
            "house_cusps": [],
            "house_system_code": "R",
        },
        datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc),
        settings,
    )

    derived = next(row for row in payload["objects"] if row["name"] == "Derived Example")
    assert derived["EQU"]["longitude"] == pytest.approx(123.349, abs=0.001)
    assert derived["EQU"]["latitude"] == pytest.approx(25.033, abs=0.001)
    assert derived["EQU"]["speed"] == pytest.approx(1.097, abs=0.001)
    assert derived["EQU"]["latitude_speed"] == pytest.approx(-0.121, abs=0.001)
    assert derived["coordinate_meta"]["EQU"]["source"] == "derived_from_ecliptic"
    assert derived["coordinate_meta"]["EQU"]["speed_source"] == "derived"
    assert derived["coordinate_meta"]["EQU"]["latitude_speed_source"] == "derived"

    fallback = next(row for row in payload["objects"] if row["name"] == "No Latitude Speed")
    assert fallback["coordinate_meta"]["EQU"]["speed_source"] == "fallback"
    assert fallback["coordinate_meta"]["EQU"]["latitude_speed_source"] == "unavailable"
    assert fallback["EQU"]["latitude_speed"] is None
    assert {
        "code": "equatorial_speed_fallback",
        "object_id": "planet:No Latitude Speed",
        "object": "No Latitude Speed",
    } in payload["chart_info"]["data_gaps"]


def test_directional_3d_computes_horizon_rates_for_planets_but_not_cusps():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        latitude=31.777779,
        longitude=35.235001,
        paused_at=None,
        house_system_code="T",
    )

    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": {
                "Sun": {
                    "longitude": 293.889,
                    "latitude": -0.002,
                    "speed": 1.007,
                    "latitude_speed": 0.0,
                },
            },
            "house_cusps": [357.632],
            "house_system_code": "T",
        },
        datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert set(sun["HOR"]) == {"longitude", "latitude", "speed", "latitude_speed"}
    assert abs(sun["HOR"]["speed"]) > 0.001
    assert abs(sun["HOR"]["latitude_speed"]) > 0.001
    assert sun["coordinate_meta"]["HOR"]["speed_source"] == "finite_difference"
    assert sun["coordinate_meta"]["HOR"]["latitude_speed_source"] == "finite_difference"

    cusp = next(row for row in payload["objects"] if row["name"] == "House 1")
    assert cusp["HOR"]["speed"] == 0.0
    assert cusp["HOR"]["latitude_speed"] == 0.0
    assert cusp["coordinate_meta"]["HOR"]["speed_source"] == "cusp_static"
    assert cusp["coordinate_meta"]["HOR"]["latitude_speed_source"] == "cusp_static"


def test_directional_3d_uses_swiss_equatorial_speed_before_fallback(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_directional_equatorial_from_swiss",
        lambda name, _timestamp_iso: (295.77, -21.332, 1.064, -0.018) if name == "Sun" else None,
    )
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Fixture",
        timezone="UTC",
        custom_time=datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        latitude=31.777779,
        longitude=35.235001,
        paused_at=None,
        house_system_code="T",
    )

    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": [
                {
                    "planet": "Sun",
                    "longitude": 293.889,
                    "latitude": -0.002,
                    "speed": 1.007,
                },
            ],
            "house_cusps": [],
            "house_system_code": "T",
        },
        datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert sun["EQU"]["longitude"] == pytest.approx(295.77, abs=0.002)
    assert sun["EQU"]["latitude"] == pytest.approx(-21.332, abs=0.003)
    assert sun["EQU"]["speed"] == 1.064
    assert sun["EQU"]["latitude_speed"] == -0.018
    assert sun["coordinate_meta"]["EQU"]["source"] == "derived_from_ecliptic"
    assert sun["coordinate_meta"]["EQU"]["speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["speed_provider"] == "swisseph"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_provider"] == "swisseph"
    assert {
        "code": "equatorial_speed_fallback",
        "object_id": "planet:Sun",
        "object": "Sun",
    } not in payload["chart_info"]["data_gaps"]


def test_directional_3d_uses_swiss_speed_when_chart_equatorial_speed_is_missing(monkeypatch):
    monkeypatch.setattr(
        astro_clock_api,
        "_directional_equatorial_from_swiss",
        lambda name, _timestamp_iso: (295.77, -21.332, 1.064, -0.018) if name == "Sun" else None,
    )
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Fixture",
        timezone="UTC",
        custom_time=datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        latitude=31.777779,
        longitude=35.235001,
        paused_at=None,
        house_system_code="T",
    )

    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": [
                {
                    "planet": "Sun",
                    "longitude": 293.889,
                    "latitude": -0.002,
                    "speed": 1.007,
                    "right_ascension": 295.771,
                    "declination": -21.333,
                },
            ],
            "house_cusps": [],
            "house_system_code": "T",
        },
        datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert sun["EQU"]["longitude"] == 295.771
    assert sun["EQU"]["latitude"] == -21.333
    assert sun["EQU"]["speed"] == 1.064
    assert sun["EQU"]["latitude_speed"] == -0.018
    assert sun["coordinate_meta"]["EQU"]["source"] == "chart_equatorial"
    assert sun["coordinate_meta"]["EQU"]["speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["speed_provider"] == "swisseph"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_source"] == "native"
    assert sun["coordinate_meta"]["EQU"]["latitude_speed_provider"] == "swisseph"
    assert {
        "code": "equatorial_speed_fallback",
        "object_id": "planet:Sun",
        "object": "Sun",
    } not in payload["chart_info"]["data_gaps"]


def test_directional_3d_re_resolves_stale_zero_saved_snap_coordinates(monkeypatch):
    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="Default",
            timezone="UTC",
            custom_time=None,
            latitude=0.0,
            longitude=0.0,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            return types.SimpleNamespace(
                timestamp=datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
                settings=active,
                chart_result={
                    "chart_data": {
                        "planets": {
                            "Sun": {"longitude": 293.889, "latitude": -0.002, "speed": 1.007},
                        },
                        "house_cusps": [357.632],
                        "house_system_code": "T",
                    },
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda location, *args, **kwargs: (31.777779, 35.235001)
        if str(location).startswith("Jerusalem")
        else None,
    )

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/directional-3d"
        "?mode=manual"
        "&datetime=1990-01-13T19%3A33%3A00%2B00%3A00"
        "&location=Jerusalem%2C%20Israel"
        "&timezone=Asia%2FJerusalem"
        "&latitude=0"
        "&longitude=0"
        "&house_system_code=T"
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["chart_info"]["latitude"] == 31.777779
    assert data["chart_info"]["longitude"] == 35.235001
    assert data["objects"][0]["HOR"]["longitude"] != 0.0


def test_directional_3d_aziz_fixture_matches_documented_geometry():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        latitude=31.777779,
        longitude=35.235001,
        paused_at=None,
        house_system_code="T",
    )
    payload = astro_clock_api._build_directional_3d_payload(
        {
            "planets": {
                "Sun": {"longitude": 293.889, "latitude": -0.002, "speed": 1.007},
                "Moon": {"longitude": 152.203, "latitude": -2.224, "speed": 15.042},
            },
            "house_cusps": [357.632],
            "house_system_code": "T",
        },
        datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert sun["EQU"]["latitude"] == pytest.approx(-21.332, abs=0.02)
    assert sun["EQU"]["longitude"] == pytest.approx(295.770, abs=0.02)
    assert sun["HOR"]["latitude"] == pytest.approx(-57.777, abs=0.02)
    assert sun["HOR"]["longitude"] == pytest.approx(100.388, abs=0.02)

    moon = next(row for row in payload["objects"] if row["name"] == "Moon")
    assert moon["HOR"]["latitude"] == pytest.approx(19.893, abs=0.02)
    assert moon["HOR"]["longitude"] == pytest.approx(272.109, abs=0.02)

    cusp = next(row for row in payload["objects"] if row["name"] == "House 1")
    assert cusp["bfull"] is False
    assert cusp["EQU"] == {"longitude": 357.632, "latitude": 0.0, "speed": 0.0, "latitude_speed": 0.0}
    assert cusp["HOR"]["latitude"] == pytest.approx(4.875, abs=0.02)
    assert cusp["HOR"]["longitude"] == pytest.approx(85.857, abs=0.02)


def test_dashboard_respects_manual_request_context(monkeypatch):
    captured = {}

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="London",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.5,
            longitude=-0.1,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            captured["settings"] = active
            ts = active.custom_time or datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc)
            return types.SimpleNamespace(
                timestamp=ts,
                settings=active,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": None,
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(
        astro_clock_api,
        "_serialize_real_time",
        lambda _data: {"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
    )
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *_args, **_kwargs: {})

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/dashboard"
        "?mode=manual"
        "&datetime=2026-03-22T06:32:00"
        "&location=Jerusalem"
        "&timezone=Asia/Jerusalem"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["location"] == "Jerusalem"
    assert payload["data"]["timezone"] == "Asia/Jerusalem"
    assert captured["settings"].mode.value == ClockMode.MANUAL.value
    assert captured["settings"].location == "Jerusalem"
    assert captured["settings"].timezone == "Asia/Jerusalem"
    assert captured["settings"].custom_time is not None


def test_traits_profile_respects_manual_request_context(monkeypatch):
    captured = {}

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="London",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.5,
            longitude=-0.1,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            captured["settings"] = active
            ts = active.custom_time or datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc)
            return types.SimpleNamespace(
                timestamp=ts,
                settings=active,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    }
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "_traits_engine", None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *_args, **_kwargs: {})

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/traits/profile"
        "?mode=manual"
        "&datetime=2026-03-22T06:32:00"
        "&location=Jerusalem"
        "&timezone=Asia/Jerusalem"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert captured["settings"].mode.value == ClockMode.MANUAL.value
    assert captured["settings"].location == "Jerusalem"
    assert captured["settings"].timezone == "Asia/Jerusalem"
    assert captured["settings"].custom_time is not None


def test_dashboard_derives_timezone_from_location_when_request_timezone_missing(monkeypatch):
    captured = {}

    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="London",
            timezone="Europe/London",
            custom_time=None,
            latitude=51.5,
            longitude=-0.1,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            captured["settings"] = active
            ts = active.custom_time or datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc)
            return types.SimpleNamespace(
                timestamp=ts,
                settings=active,
                chart_result={
                    "chart_data": {
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {},
                    },
                    "_raw_chart": None,
                },
            )

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(
        astro_clock_api,
        "_serialize_real_time",
        lambda _data: {"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
    )
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        astro_clock_api,
        "_resolve_timezone_for_context",
        lambda timezone_name, location, **_kwargs: "Asia/Jerusalem" if location == "Israel" else timezone_name,
    )

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/dashboard"
        "?mode=manual"
        "&datetime=2026-03-22T06:32:00"
        "&location=Israel"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["location"] == "Israel"
    assert payload["data"]["timezone"] == "Asia/Jerusalem"
    assert captured["settings"].mode.value == ClockMode.MANUAL.value
    assert captured["settings"].location == "Israel"
    assert captured["settings"].timezone == "Asia/Jerusalem"


def test_trait_profile_includes_chart_snapshot_for_ai_exports(monkeypatch):
    class _StubEngine:
        settings = AstroClockSettings(
            mode=ClockMode.REALTIME,
            location="Jerusalem",
            timezone="Asia/Jerusalem",
            custom_time=None,
            latitude=31.7683,
            longitude=35.2137,
            paused_at=None,
            house_system_code="R",
        )

        def get_current_data(self, settings=None):
            active = settings or self.settings
            return types.SimpleNamespace(
                timestamp=active.custom_time or datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc),
                settings=active,
                chart_result={
                    "chart_data": {
                        "ascendant": 18.9,
                        "midheaven": 271.5,
                        "planets": {},
                        "aspects": [],
                        "house_rulers": {"1": "Mars"},
                    }
                },
            )

    class _FakeTraitEngine:
        def evaluate(self, _metrics):
            return {
                "summary": {"dominant_element": "Fire"},
                "top_traits": [],
                "traits": [],
                "guidance": [],
            }

    fake_house_influence = types.SimpleNamespace(
        compute_house_influences=lambda *_args, **_kwargs: {"houses": [], "planet_strengths": {}}
    )
    fake_traits_engine = types.SimpleNamespace(TraitEngine=lambda: _FakeTraitEngine())

    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "_traits_engine", None)
    monkeypatch.setattr(astro_clock_api, "compute_metrics", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(astro_clock_api, "compute_sect_info", lambda *_args, **_kwargs: {"chart_sect": "day"})
    monkeypatch.setattr(
        astro_clock_api,
        "_build_dashboard_payload",
        lambda *_args, **_kwargs: {
            "timestamp": "2026-03-22T06:32:00+00:00",
            "location": "Jerusalem",
            "timezone": "Asia/Jerusalem",
            "timezone_label": "Asia/Jerusalem (UTC+02:00)",
            "planets": [{"planet": "Sun", "sign": "Aries", "house": 1, "longitude": 1.5}],
            "moon": {"sign": "Taurus", "house": 2},
            "moon_timeline": {"in_voc": False},
            "solar_conditions": {"combustion": [{"planet": "Mercury", "distance_from_sun": 2.1}]},
            "top_aspects": [{"planet1": "Sun", "planet2": "Moon", "aspect": "Conjunction", "orb": 0.4}],
            "morin_aspects": [{"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Sextile", "orb": 0.8}],
            "fixed_star_hits": [{"star": "Regulus", "planet": "Sun"}],
            "house_cusps": [18.9, 44.0, 71.0],
            "house_rulers": {"1": "Mars"},
            "receptions": {
                "traditional_reception": {"label": "Mixed reception"},
                "mutual": [{"p1": "Venus", "p2": "Mars", "type": "mixed_reception", "strength": 4}],
                "top_unilateral": [],
            },
            "special_degrees": ["25 Leo"],
            "morin_patterns": {"translation": [{"planet": "Mercury"}]},
        },
    )
    monkeypatch.setitem(sys.modules, "house_influence", fake_house_influence)
    monkeypatch.setitem(sys.modules, "traits.engine", fake_traits_engine)

    app = _make_app()
    client = app.test_client()

    response = client.get("/api/astro-clock/traits/profile")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["summary"]["dominant_element"] == "Fire"
    assert data["receptions"]["traditional_reception"]["label"] == "Mixed reception"
    assert data["morin_patterns"]["translation"][0]["planet"] == "Mercury"
    assert data["chart_snapshot"]["location"] == "Jerusalem"
    assert data["chart_snapshot"]["timezone"] == "Asia/Jerusalem"
    assert data["chart_snapshot"]["house_system"] == "R"
    assert data["chart_snapshot"]["fixed_star_hits"][0]["star"] == "Regulus"
    assert data["chart_snapshot"]["solar_conditions"]["combustion"][0]["planet"] == "Mercury"
