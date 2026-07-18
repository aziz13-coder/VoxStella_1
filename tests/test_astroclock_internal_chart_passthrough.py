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


def _confirmed_saved_snap(**overrides):
    snap = {
        "schema_version": 2,
        "id": "confirmed-snap",
        "effective_datetime": "2001-06-15T08:15:00+00:00",
        "local_datetime": "2001-06-15T09:15:00+01:00",
        "location": "Lisbon, Portugal",
        "timezone": "Europe/Lisbon",
        "latitude": 38.7223,
        "longitude": -9.1393,
        "coordinate_provenance": {
            "source": "user_confirmed_context_override",
            "persisted_with_chart": True,
            "review_required": False,
        },
        "calculation_context": {
            "instant_utc": "2001-06-15T08:15:00+00:00",
            "local_datetime": "2001-06-15T09:15:00+01:00",
            "timezone": "Europe/Lisbon",
            "location": "Lisbon, Portugal",
            "latitude": 38.7223,
            "longitude": -9.1393,
            "house_system_code": "R",
            "review_required": False,
            "time_provenance": {"ambiguous": False},
        },
        "dashboard": {},
    }
    snap.update(overrides)
    return snap


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


def test_receptions_route_uses_confirmed_saved_snap_context(monkeypatch):
    saved_snap = _confirmed_saved_snap()
    captured = {}

    class _StubStore:
        def get(self, snap_id):
            return saved_snap if snap_id == "confirmed-snap" else None

    class _StubEngine:
        settings = _stub_clock_settings()

        def get_current_data(self, settings=None):
            raise AssertionError("live engine context must not replace the saved chart")

    def _fake_compute(
        dt_iso,
        location,
        timezone_name,
        house_system_code=None,
        **kwargs,
    ):
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
        return {
            "chart_data": {"source": "confirmed-saved-snap"},
            "meta": {
                "timestamp": "2001-06-15T09:15:00+01:00",
                "location": location,
                "timezone": timezone_name,
                "latitude": kwargs.get("latitude"),
                "longitude": kwargs.get("longitude"),
            },
        }

    def _fake_extract(chart):
        assert chart == {"chart_data": {"source": "confirmed-saved-snap"}}
        return {
            "traditional_reception": {
                "type": "none",
                "display_text": "Saved chart reception",
            },
            "mutual": [],
            "top_unilateral": [],
        }

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _StubStore())
    monkeypatch.setattr(astro_clock_api, "_engine_instance", lambda: _StubEngine())
    monkeypatch.setattr(astro_clock_api, "_compute_chart_bundle_for", _fake_compute)
    monkeypatch.setattr(astro_clock_api, "_extract_receptions_payload", _fake_extract)

    response = _make_app().test_client().get(
        "/api/astro-clock/receptions"
        "?snap_id=confirmed-snap"
        "&house_system_code=R"
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["traditional_reception"]["display_text"] == (
        "Saved chart reception"
    )
    assert captured == {
        "dt_iso": "2001-06-15T08:15:00+00:00",
        "location": "Lisbon, Portugal",
        "timezone": "Europe/Lisbon",
        "house_system_code": "R",
        "latitude": 38.7223,
        "longitude": -9.1393,
    }


@pytest.mark.parametrize(
    ("snap", "error_fragment"),
    (
        (
            _confirmed_saved_snap(
                coordinate_provenance={
                    **_confirmed_saved_snap()["coordinate_provenance"],
                    "review_required": True,
                },
                calculation_context={
                    **_confirmed_saved_snap()["calculation_context"],
                    "coordinate_provenance": {
                        "source": "legacy_migration",
                        "persisted_with_chart": True,
                        "review_required": True,
                    },
                    "review_required": True,
                },
            ),
            "requires review",
        ),
        (
            _confirmed_saved_snap(superseded_by="corrected-snap"),
            "superseded by a corrected copy",
        ),
    ),
)
def test_receptions_route_rejects_unsafe_saved_snap_context(
    monkeypatch,
    snap,
    error_fragment,
):
    class _StubStore:
        def get(self, snap_id):
            return snap if snap_id == "confirmed-snap" else None

    monkeypatch.setattr(astro_clock_api, "_snaps", lambda: _StubStore())
    monkeypatch.setattr(
        astro_clock_api,
        "_compute_chart_bundle_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unsafe saved chart must be rejected before calculation")
        ),
    )

    response = _make_app().test_client().get(
        "/api/astro-clock/receptions?snap_id=confirmed-snap"
    )

    assert response.status_code == 400
    assert error_fragment in response.get_json()["error"]


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
        "&include_modern=1"
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
    assert sun["coordinate_meta"]["HOR"]["source"] == "topocentric_local_space"
    assert sun["coordinate_meta"]["HOR"]["speed_source"] == "topocentric_finite_difference"
    assert sun["coordinate_meta"]["HOR"]["latitude_speed_source"] == "topocentric_finite_difference"
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
    assert data["body_policy"]["scope"] == "traditional_plus_modern"
    assert not any(row["name"] == "Hidden Test Point" for row in data["objects"])

    cusp = next(row for row in data["objects"] if row["name"] == "House 1")
    assert cusp["buse"] is True
    assert cusp["bfull"] is False
    assert cusp["object_type"] == "cusp"
    assert cusp["EQL"]["longitude"] == 18.0
    assert cusp["EQL"]["latitude"] == 0.0
    assert cusp["EQU"]["longitude"] != 18.0
    assert cusp["EQU"]["latitude"] != 0.0
    assert cusp["coordinate_meta"]["EQU"]["speed_source"] == "unavailable"
    assert cusp["coordinate_meta"]["EQU"]["latitude_speed_source"] == "unavailable"
    assert cusp["coordinate_meta"]["HOR"]["speed_source"] == "unavailable"
    assert cusp["coordinate_meta"]["HOR"]["latitude_speed_source"] == "unavailable"
    assert cusp["HOR"]["speed"] is None
    assert cusp["HOR"]["latitude_speed"] is None
    assert captured["settings"].location == "Israel"


def test_directional_3d_derives_equatorial_speed_from_complete_ecliptic_rates(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_directional_equatorial_from_swiss", lambda *_args: None)
    eql, equ, hor, meta, gaps = astro_clock_api._directional_coordinate_triplet(
        120.0,
        5.0,
        1.0,
        object_id="planet:Fixture",
        name="Fixture",
        info={},
        object_type="planet",
        ecliptic_speed_source="native",
        ecliptic_latitude_speed=0.1,
        timestamp_iso="2026-03-22T00:00:00+00:00",
        observer_latitude=31.778,
        observer_longitude=35.235,
        obliquity_deg=23.4392911,
        horizontal_samples={
            "current": {"azimuth_deg": 0.0, "altitude_deg": 0.0},
        },
    )

    assert eql == {"longitude": 120.0, "latitude": 5.0, "speed": 1.0}
    assert equ["longitude"] == pytest.approx(123.349, abs=0.001)
    assert equ["latitude"] == pytest.approx(25.033, abs=0.001)
    assert equ["speed"] == pytest.approx(1.097, abs=0.001)
    assert equ["latitude_speed"] == pytest.approx(-0.121, abs=0.001)
    assert meta["EQU"]["source"] == "derived_from_ecliptic"
    assert meta["EQU"]["speed_source"] == "derived"
    assert meta["EQU"]["latitude_speed_source"] == "derived"
    assert hor["longitude"] == 0.0
    assert hor["latitude"] == 0.0
    assert hor["speed"] is None
    assert gaps == []


def test_directional_3d_computes_horizon_rates_for_planets_but_not_cusps():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Paris, France",
        timezone="Europe/Paris",
        custom_time=datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        latitude=48.85341,
        longitude=2.3488,
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
        datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert set(sun["HOR"]) == {"longitude", "latitude", "speed", "latitude_speed"}
    assert abs(sun["HOR"]["speed"]) > 0.001
    assert abs(sun["HOR"]["latitude_speed"]) > 0.001
    assert sun["coordinate_meta"]["HOR"]["speed_source"] == "topocentric_finite_difference"
    assert sun["coordinate_meta"]["HOR"]["latitude_speed_source"] == "topocentric_finite_difference"

    cusp = next(row for row in payload["objects"] if row["name"] == "House 1")
    assert cusp["HOR"]["speed"] is None
    assert cusp["HOR"]["latitude_speed"] is None
    assert cusp["coordinate_meta"]["HOR"]["speed_source"] == "unavailable"
    assert cusp["coordinate_meta"]["HOR"]["latitude_speed_source"] == "unavailable"


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
        custom_time=datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        latitude=48.85341,
        longitude=2.3488,
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
        datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
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
        custom_time=datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        latitude=48.85341,
        longitude=2.3488,
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
        datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
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
                timestamp=datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
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
        lambda location, *args, **kwargs: (48.85341, 2.3488)
        if str(location).startswith("Paris")
        else None,
    )

    app = _make_app()
    client = app.test_client()

    response = client.get(
        "/api/astro-clock/directional-3d"
        "?mode=manual"
        "&datetime=2000-02-29T11%3A34%3A00%2B00%3A00"
        "&location=Paris%2C%20France"
        "&timezone=Europe%2FParis"
        "&latitude=0"
        "&longitude=0"
        "&house_system_code=T"
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["chart_info"]["latitude"] == 48.85341
    assert data["chart_info"]["longitude"] == 2.3488
    assert data["objects"][0]["HOR"]["longitude"] != 0.0


def test_directional_3d_synthetic_fixture_matches_documented_geometry():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Paris, France",
        timezone="Europe/Paris",
        custom_time=datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        latitude=48.85341,
        longitude=2.3488,
        paused_at=None,
        house_system_code="R",
    )
    payload = astro_clock_api._build_directional_3d_payload(
        {
            "planets": {
                "Sun": {
                    "longitude": 340.1876997214984,
                    "latitude": 0.000034793745936609156,
                    "speed": 1.0041225057414884,
                    "latitude_speed": -0.0000342535809478038,
                },
                "Moon": {
                    "longitude": 275.3227074412695,
                    "latitude": 2.4413693232988773,
                    "speed": 11.820046434245233,
                    "latitude_speed": -0.9510301141631097,
                },
            },
            "house_cusps": [93.76528231103039],
            "house_system_code": "R",
        },
        datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc),
        settings,
    )

    sun = next(row for row in payload["objects"] if row["name"] == "Sun")
    assert sun["EQU"]["latitude"] == pytest.approx(-7.748, abs=0.02)
    assert sun["EQU"]["longitude"] == pytest.approx(341.709, abs=0.02)
    assert sun["HOR"]["latitude"] == pytest.approx(33.038, abs=0.02)
    assert sun["HOR"]["longitude"] == pytest.approx(171.400, abs=0.02)
    assert sun["coordinate_meta"]["HOR"]["source"] == "topocentric_local_space"

    moon = next(row for row in payload["objects"] if row["name"] == "Moon")
    assert moon["HOR"]["latitude"] == pytest.approx(1.987, abs=0.02)
    assert moon["HOR"]["longitude"] == pytest.approx(233.105, abs=0.02)
    assert moon["coordinate_meta"]["HOR"]["source"] == "topocentric_local_space"

    cusp = next(row for row in payload["objects"] if row["name"] == "House 1")
    assert cusp["bfull"] is False
    assert cusp["EQU"] == {
        "longitude": pytest.approx(94.103, abs=0.02),
        "latitude": pytest.approx(23.384, abs=0.02),
        "speed": None,
        "latitude_speed": None,
    }
    assert cusp["HOR"]["latitude"] == pytest.approx(0.0, abs=0.02)
    assert cusp["HOR"]["longitude"] == pytest.approx(52.901, abs=0.02)
    assert cusp["HOR"]["speed"] is None


@pytest.mark.parametrize(
    ("swiss_azimuth", "public_azimuth"),
    [
        (0.0, 180.0),
        (90.0, 270.0),
        (180.0, 0.0),
        (270.0, 90.0),
    ],
)
def test_directional_swiss_azimuth_is_normalized_to_north_zero_eastward(
    monkeypatch,
    swiss_azimuth,
    public_azimuth,
):
    fake_swiss = types.SimpleNamespace(
        GREG_CAL=1,
        ECL2HOR=0,
        julday=lambda *_args: 2451545.0,
        azalt=lambda *_args: (swiss_azimuth, 12.5, 12.5),
    )
    monkeypatch.setattr(astro_clock_api, "require_swisseph", lambda: fake_swiss)

    azimuth, altitude, source = astro_clock_api._directional_horizontal_from_ecliptic(
        "2000-01-01T12:00:00+00:00",
        0.0,
        0.0,
        0.0,
        0.0,
        23.4392911,
    )

    assert azimuth == public_azimuth
    assert altitude == 12.5
    assert source == "swisseph_azalt"


def test_directional_timestamp_requires_an_explicit_offset_and_normalizes_to_utc():
    assert astro_clock_api._directional_timestamp_iso(
        "1990-01-13T21:33:00+02:00",
        label="Directional 3D",
    ) == "1990-01-13T19:33:00+00:00"

    with pytest.raises(ValueError, match="timezone-aware"):
        astro_clock_api._directional_timestamp_iso(
            "1990-01-13T21:33:00",
            label="Directional 3D",
        )


def test_directional_horizon_matches_compass_topocentric_contract_for_jerusalem():
    timestamp = datetime(1990, 1, 13, 19, 33, tzinfo=timezone.utc)
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        custom_time=timestamp,
        latitude=31.7683,
        longitude=35.2137,
        paused_at=None,
        house_system_code="R",
    )
    chart_data = {
        "planets": {
            "Sun": {
                "longitude": 293.361998619,
                "latitude": -0.000045159,
                "speed": 1.018358695,
            },
            "Moon": {
                "longitude": 145.988305068,
                "latitude": -0.862928126,
                "speed": 13.056245837,
            },
            "Uranus": {
                "longitude": 276.0,
                "latitude": -0.2,
                "speed": 0.03,
            },
        },
        "house_cusps": [],
        "house_system_code": "R",
    }

    compass = astro_clock_api._build_local_space_compass_payload(
        chart_data,
        timestamp,
        settings,
        include_modern=True,
    )
    directional = astro_clock_api._build_directional_3d_payload(
        chart_data,
        timestamp,
        settings,
        include_modern=True,
    )
    directional_by_name = {
        row["name"]: row
        for row in directional["objects"]
        if row["object_type"] == "planet"
    }

    for compass_row in compass["azimuths"]:
        directional_row = directional_by_name[compass_row["planet"]]
        assert directional_row["HOR"]["longitude"] == pytest.approx(
            compass_row["azimuth_deg"],
            abs=0.001,
        )
        assert directional_row["HOR"]["latitude"] == pytest.approx(
            compass_row["altitude_deg"],
            abs=0.001,
        )
        assert directional_row["coordinate_meta"]["HOR"]["source"] == "topocentric_local_space"

    moon = next(row for row in compass["azimuths"] if row["planet"] == "Moon")
    assert moon["azimuth_deg"] == pytest.approx(91.801, abs=0.001)
    assert moon["altitude_deg"] == pytest.approx(25.374, abs=0.001)
    sun = next(row for row in compass["azimuths"] if row["planet"] == "Sun")
    assert sun["azimuth_deg"] == pytest.approx(280.640, abs=0.001)
    assert sun["altitude_deg"] == pytest.approx(-58.268, abs=0.001)


def test_directional_and_compass_share_explicit_traditional_modern_body_policy():
    timestamp = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Greenwich, UK",
        timezone="UTC",
        custom_time=timestamp,
        latitude=51.4769,
        longitude=-0.0005,
        paused_at=None,
        house_system_code="R",
    )
    chart_data = {
        "planets": {
            "Uranus": {"longitude": 10.0, "latitude": 0.0, "speed": 0.03},
            "North Node": {"longitude": 20.0, "latitude": 0.0, "speed": -0.05},
            "Moon": {"longitude": 30.0, "latitude": 1.0, "speed": 13.0},
            "Chiron": {"longitude": 40.0, "latitude": 2.0, "speed": 0.02},
            "Sun": {"longitude": 50.0, "latitude": 0.0, "speed": 1.0},
        },
        "house_cusps": [],
        "house_system_code": "R",
    }

    traditional = astro_clock_api._build_directional_3d_payload(
        chart_data,
        timestamp,
        settings,
        include_modern=False,
    )
    modern = astro_clock_api._build_directional_3d_payload(
        chart_data,
        timestamp,
        settings,
        include_modern=True,
    )

    assert [
        row["name"] for row in traditional["objects"] if row["object_type"] == "planet"
    ] == ["Sun", "Moon"]
    assert [
        row["name"] for row in modern["objects"] if row["object_type"] == "planet"
    ] == ["Sun", "Moon", "Uranus"]
    assert traditional["body_policy"]["scope"] == "traditional"
    assert modern["body_policy"]["scope"] == "traditional_plus_modern"
    assert traditional["body_policy"]["included"] == ["Sun", "Moon"]
    assert modern["body_policy"]["included"] == ["Sun", "Moon", "Uranus"]
    assert modern["body_policy"]["eligible"] == [
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    ]
    assert modern["body_policy"]["excluded_points"] == [
        "Chiron",
        "North Node",
        "South Node",
        "True Node",
    ]


def test_compass_and_directional_share_legacy_zero_coordinate_reresolution(
    monkeypatch,
):
    import forensic.local_space as local_space_module

    timestamp = datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc)
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Paris, France",
        timezone="Europe/Paris",
        custom_time=timestamp,
        latitude=0.0,
        longitude=0.0,
        paused_at=None,
        house_system_code="R",
    )
    calls = []
    monkeypatch.setattr(
        astro_clock_api,
        "_ensure_coords_for_location",
        lambda location, *args, **kwargs: (
            calls.append((location, kwargs.get("trust_settings"))),
            (48.85341, 2.3488),
        )[1],
    )
    monkeypatch.setattr(
        local_space_module,
        "compute_local_space",
        lambda _timestamp, _lat, _lon, planets: {
            name: {
                "azimuth_deg": 180.0,
                "altitude_deg": 20.0,
                "right_ascension_deg": 10.0,
                "declination_deg": 5.0,
            }
            for name in planets
        },
    )
    chart_data = {
        "planets": {
            "Sun": {
                "longitude": 340.0,
                "latitude": 0.0,
                "speed": 1.0,
            },
        },
        "house_cusps": [],
        "house_system_code": "R",
    }

    compass = astro_clock_api._build_local_space_compass_payload(
        chart_data,
        timestamp,
        settings,
    )
    directional = astro_clock_api._build_directional_3d_payload(
        chart_data,
        timestamp,
        settings,
    )

    assert (compass["latitude"], compass["longitude"]) == (48.85341, 2.3488)
    assert (
        directional["chart_info"]["latitude"],
        directional["chart_info"]["longitude"],
    ) == (48.85341, 2.3488)
    assert calls == [
        ("Paris, France", False),
        ("Paris, France", False),
    ]


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (float("nan"), 35.0),
        (95.0, 35.0),
        (31.0, 181.0),
    ],
)
def test_compass_and_directional_reject_invalid_stored_observer_coordinates(
    latitude,
    longitude,
):
    timestamp = datetime(2000, 2, 29, 11, 34, tzinfo=timezone.utc)
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location=None,
        timezone="UTC",
        custom_time=timestamp,
        latitude=latitude,
        longitude=longitude,
        paused_at=None,
        house_system_code="R",
    )
    chart_data = {
        "planets": {
            "Sun": {
                "longitude": 340.0,
                "latitude": 0.0,
                "speed": 1.0,
            },
        },
        "house_cusps": [],
    }

    with pytest.raises(astro_clock_api.LocationError, match="coordinates"):
        astro_clock_api._build_local_space_compass_payload(
            chart_data,
            timestamp,
            settings,
        )
    with pytest.raises(astro_clock_api.LocationError, match="coordinates"):
        astro_clock_api._build_directional_3d_payload(
            chart_data,
            timestamp,
            settings,
        )


def test_compass_preserves_missing_ascendant_as_unavailable():
    ascendant, selected = astro_clock_api._select_compass_planets(
        {
            "planets": {
                "Sun": {
                    "longitude": 10.0,
                    "latitude": 0.0,
                    "speed": 1.0,
                },
            },
        }
    )

    assert ascendant is None
    assert [name for name, _info in selected] == ["Sun"]
    empty_payload = astro_clock_api._build_local_space_compass_payload(
        {"planets": {}},
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        None,
    )
    assert empty_payload["ascendant"] is None


def test_directional_partial_topocentric_record_is_unavailable(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_directional_equatorial_from_swiss", lambda *_args: None)
    _eql, _equ, hor, meta, gaps = astro_clock_api._directional_coordinate_triplet(
        15.0,
        0.0,
        1.0,
        object_id="planet:Sun",
        name="Sun",
        info={},
        object_type="planet",
        ecliptic_speed_source="native",
        ecliptic_latitude_speed=0.0,
        timestamp_iso="2000-01-01T12:00:00+00:00",
        observer_latitude=0.0,
        observer_longitude=0.0,
        obliquity_deg=23.4392911,
        horizontal_samples={
            "current": {"azimuth_deg": 90.0},
        },
    )

    assert hor == {
        "longitude": None,
        "latitude": None,
        "speed": None,
        "latitude_speed": None,
    }
    assert meta["HOR"]["source"] == "unavailable"
    assert meta["HOR"]["speed_source"] == "unavailable"
    assert {
        "code": "topocentric_horizon_unavailable",
        "object_id": "planet:Sun",
        "object": "Sun",
    } in gaps


def test_directional_missing_values_remain_unavailable_not_zero(monkeypatch):
    monkeypatch.setattr(astro_clock_api, "_directional_equatorial_from_swiss", lambda *_args: None)
    eql, equ, hor, meta, gaps = astro_clock_api._directional_coordinate_triplet(
        15.0,
        None,
        None,
        object_id="planet:Fixture",
        name="Fixture",
        info={},
        object_type="planet",
        ecliptic_speed_source="unavailable",
        ecliptic_latitude_speed=None,
        timestamp_iso="2000-01-01T12:00:00+00:00",
        observer_latitude=0.0,
        observer_longitude=0.0,
        obliquity_deg=23.4392911,
        horizontal_samples={
            "current": {"azimuth_deg": 0.0, "altitude_deg": 0.0},
        },
    )

    assert eql == {"longitude": 15.0, "latitude": None, "speed": None}
    assert equ == {
        "longitude": None,
        "latitude": None,
        "speed": None,
        "latitude_speed": None,
    }
    assert hor == {
        "longitude": 0.0,
        "latitude": 0.0,
        "speed": None,
        "latitude_speed": None,
    }
    assert meta["EQU"]["source"] == "unavailable"
    assert meta["EQU"]["speed_source"] == "unavailable"
    assert meta["HOR"]["speed_source"] == "unavailable"
    assert {gap["code"] for gap in gaps} == {
        "ecliptic_latitude_unavailable",
        "equatorial_speed_unavailable",
    }


def test_directional_preserves_house_numbers_and_converts_cusps_to_equatorial():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="Greenwich, UK",
        timezone="UTC",
        custom_time=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        latitude=51.4769,
        longitude=-0.0005,
        paused_at=None,
        house_system_code="R",
    )
    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": {},
            "house_cusps": {"1": 0.0, "2": None, "3": 45.0},
            "house_system_code": "R",
        },
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        settings,
    )
    cusps = [row for row in payload["objects"] if row["object_type"] == "cusp"]

    assert [row["object_id"] for row in cusps] == ["house:1", "house:3"]
    assert [row["EQL"]["longitude"] for row in cusps] == [0.0, 45.0]
    assert cusps[1]["EQU"]["longitude"] == pytest.approx(42.536, abs=0.001)
    assert cusps[1]["EQU"]["latitude"] == pytest.approx(16.336, abs=0.001)
    assert cusps[1]["EQU"]["speed"] is None
    assert cusps[1]["HOR"]["speed"] is None


def test_directional_polar_metadata_never_relabels_requested_house_system():
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location="High latitude fixture",
        timezone="UTC",
        custom_time=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        latitude=80.0,
        longitude=0.0,
        paused_at=None,
        house_system_code="R",
    )
    payload = astro_clock_api._build_directional_3d_payload(
        {
            "obliquity": 23.4392911,
            "planets": {},
            "house_cusps": [],
            "house_system_code": "R",
        },
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        settings,
    )
    chart_info = payload["chart_info"]

    assert chart_info["house_system"] == "R"
    assert chart_info["house_system_requested"] == "R"
    assert chart_info["house_system_effective"] == "R"
    assert chart_info["house_system_source"] == "chart"
    assert chart_info["house_system_adjusted"] is False
    assert chart_info["house_system_safety_override"] is False
    assert chart_info["polar_region"] is True


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
