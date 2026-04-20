from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
from backend.astro_clock_engine import AstroClockSettings, ClockMode


class _SentinelChart:
    pass


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def test_receptions_fallback_prefers_internal_raw_chart(monkeypatch):
    sentinel = _SentinelChart()

    class _StubEngine:
        def get_current_data(self):
            return types.SimpleNamespace(
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
        def get_current_data(self):
            return types.SimpleNamespace(
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
        def get_current_data(self):
            return types.SimpleNamespace(
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

        def get_current_data(self):
            return types.SimpleNamespace(
                timestamp=datetime(2025, 9, 27, 16, 25, tzinfo=timezone.utc),
                settings=types.SimpleNamespace(location="City of London", timezone="Europe/London"),
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
