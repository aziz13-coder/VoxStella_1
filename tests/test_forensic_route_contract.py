from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase, mock

from flask import Flask, request


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
import forensic.engine as forensic_engine_module
import forensic.survivability as survivability_module


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _stub_data():
    settings = types.SimpleNamespace(
        location="Jerusalem, Israel",
        timezone="Asia/Jerusalem",
        house_system_code="W",
    )
    return types.SimpleNamespace(
        timestamp=datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc),
        settings=settings,
        chart_result={
            "chart_data": {
                "planets": [],
                "aspects": [],
                "house_rulers": {},
            }
        },
    )


def _stub_dashboard_payload():
    return {
        "timestamp": "2026-03-22T06:32:00+00:00",
        "location": "Jerusalem, Israel",
        "timezone_label": "Asia/Jerusalem",
        "planets": [],
        "moon": None,
        "moon_timeline": None,
        "top_aspects": [],
        "tightest_aspect": None,
        "fixed_star_hits": [],
        "arabic_parts": {},
        "solar_conditions": {},
        "house_cusps": [],
        "house_rulers": {},
        "sect": {},
    }


class ForensicRouteContractTests(TestCase):
    def test_forensic_route_uses_shared_request_context(self):
        captured = {}
        data = _stub_data()

        def _fake_context(_eng):
            captured["mode"] = request.args.get("mode")
            captured["datetime"] = request.args.get("datetime")
            captured["location"] = request.args.get("location")
            captured["timezone"] = request.args.get("timezone")
            captured["house_system_code"] = request.args.get("house_system_code")
            return data, data.settings

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            side_effect=_fake_context,
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: _stub_dashboard_payload(),
        ):
            response = client.get(
                "/api/astro-clock/forensic"
                "?mode=manual"
                "&datetime=2026-03-22T06:32:00"
                "&location=Israel"
                "&timezone=Asia/Jerusalem"
                "&house_system_code=W"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["timestamp"], "2026-03-22T06:32:00+00:00")
        self.assertEqual(payload["location"], "Jerusalem, Israel")
        self.assertIn("features", payload)
        self.assertIn("dominance", payload)
        self.assertIn("survivability", payload)
        self.assertIn("axis_assessment", payload)
        self.assertIn("scoring_categories", payload)
        self.assertEqual(payload["axis_assessment"]["method"], "explicit_rule_id_category_mapping_v1")
        self.assertFalse(payload["axis_assessment"]["uses_free_text"])
        self.assertEqual(payload["analysis_metadata"]["intended_use"], "symbolic_research_only")
        self.assertFalse(payload["analysis_metadata"]["scientifically_validated_for_forensic_use"])
        self.assertFalse(payload["analysis_metadata"]["is_statistical_probability"])
        self.assertEqual(payload["analysis_metadata"]["house_system"]["effective_code"], "W")
        self.assertEqual(payload["analysis_metadata"]["house_system"]["source"], "request_override")
        self.assertIn("level", payload["survivability"])
        self.assertIn("outcome_band", payload["survivability"])
        self.assertEqual(payload["survivability"]["classification_policy"]["version"], "deduplicated_v2")
        self.assertIn("recovery_support", payload["survivability"].get("breakdown") or {})
        self.assertEqual(
            captured,
            {
                "mode": "manual",
                "datetime": "2026-03-22T06:32:00",
                "location": "Israel",
                "timezone": "Asia/Jerusalem",
                "house_system_code": "W",
            },
        )

    def test_forensic_route_applies_development_selected_default_house_system(self):
        captured = {}
        data = _stub_data()

        def _fake_context(_eng, *, house_system_override=None):
            captured["house_system_override"] = house_system_override
            data.settings.house_system_code = house_system_override
            return data, data.settings

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            side_effect=_fake_context,
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: _stub_dashboard_payload(),
        ):
            response = client.get("/api/astro-clock/forensic?mode=manual")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertEqual(captured["house_system_override"], "R")
        house_policy = (payload.get("analysis_metadata") or {}).get("house_system") or {}
        self.assertEqual(house_policy.get("default_code"), "R")
        self.assertEqual(house_policy.get("effective_code"), "R")
        self.assertEqual(house_policy.get("source"), "forensic_default")
        self.assertEqual(
            (house_policy.get("development_selection") or {}).get("evaluation_scope"),
            "development_only_not_holdout_validation",
        )

    def test_forensic_route_reports_rule_load_failures(self):
        data = _stub_data()

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: _stub_dashboard_payload(),
        ), mock.patch.object(
            forensic_engine_module,
            "load_knowledge",
            side_effect=RuntimeError("broken forensic rules"),
        ):
            response = client.get("/api/astro-clock/forensic")

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "forensic_rule_engine_unavailable")
        self.assertIn("rules", payload["detail"].lower())

    def test_forensic_route_reports_rule_evaluation_failures(self):
        data = _stub_data()

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: _stub_dashboard_payload(),
        ), mock.patch.object(
            forensic_engine_module,
            "load_knowledge",
            return_value=[{"id": "rule"}],
        ), mock.patch.object(
            forensic_engine_module,
            "evaluate",
            side_effect=RuntimeError("evaluation failed"),
        ):
            response = client.get("/api/astro-clock/forensic")

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "forensic_rule_engine_unavailable")
        self.assertIn("evaluation", payload["detail"].lower())

    def test_forensic_route_marks_child_hospital_case_context(self):
        data = _stub_data()

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: {
                **_stub_dashboard_payload(),
                "location": "Children's Hospital, Chester, England",
            },
        ):
            response = client.get(
                "/api/astro-clock/forensic"
                "?mode=manual"
                "&datetime=2015-06-08T20:26:00"
                "&location=Children%27s%20Hospital%2C%20Chester%2C%20England"
                "&timezone=Europe/London"
                "&case_type=child"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["features"]["case_context"]["case_type"], "child")
        self.assertTrue(payload["features"]["case_context"]["child_case"])
        self.assertTrue(payload["features"]["case_context"]["healthcare_context"])
        self.assertTrue(payload["features"]["case_context"]["healthcare_child_context"])

    def test_forensic_route_returns_mcintosh_asc_ruler_placement(self):
        data = _stub_data()

        def fake_dashboard(*_args, **_kwargs):
            payload = _stub_dashboard_payload()
            payload.update(
                {
                    "planets": [
                        {"planet": "Venus", "longitude": 45.0, "house": 7, "sign": "Taurus"},
                        {"planet": "Mars", "longitude": 120.0, "house": 1, "sign": "Leo"},
                    ],
                    "house_rulers": {"1": "Venus", "7": "Mars"},
                    "house_cusps": [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0],
                }
            )
            return payload

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=fake_dashboard,
        ):
            response = client.get("/api/astro-clock/forensic")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        placement = payload.get("asc_ruler_placement") or {}
        self.assertEqual(placement.get("ruler"), "Venus")
        self.assertEqual(placement.get("house"), 7)
        self.assertIn("suspect", placement.get("summary", "").lower())
        self.assertTrue(placement.get("cues"))
        self.assertEqual((payload.get("features") or {}).get("asc_ruler_placement"), placement)
        self.assertIn("7", payload.get("asc_ruler_house_meanings") or {})

    def test_request_context_helper_honors_explicit_coordinates(self):
        app = Flask(__name__)
        prev = types.SimpleNamespace(
            mode=astro_clock_api.ClockMode.REALTIME,
            location="Jerusalem, Israel",
            timezone="Asia/Jerusalem",
            custom_time=None,
            paused_at=None,
            house_system_code="W",
            latitude=31.7683,
            longitude=35.2137,
        )
        captured = {}

        def _fake_get_current_data(settings=None):
            captured["settings"] = settings
            return types.SimpleNamespace(
                timestamp=datetime(2026, 3, 22, 6, 32, tzinfo=timezone.utc),
                settings=settings,
                chart_result={"chart_data": {"planets": [], "aspects": [], "house_rulers": {}}},
            )

        eng = types.SimpleNamespace(settings=prev, get_current_data=_fake_get_current_data)

        with app.test_request_context(
            "/api/astro-clock/forensic"
            "?mode=manual"
            "&datetime=2026-03-22T06:32:00"
            "&location=Basra%2C%20Iraq"
            "&timezone=Asia/Baghdad"
            "&latitude=30.51624"
            "&longitude=47.84212"
        ):
            data, active_settings = astro_clock_api._data_for_request_clock_context(eng)

        self.assertIsNotNone(data)
        self.assertEqual(active_settings.location, "Basra, Iraq")
        self.assertEqual(active_settings.timezone, "Asia/Baghdad")
        self.assertAlmostEqual(active_settings.latitude, 30.51624)
        self.assertAlmostEqual(active_settings.longitude, 47.84212)
        self.assertEqual(captured["settings"], active_settings)

    def test_forensic_route_rejects_invalid_latitude(self):
        app = _make_app()
        client = app.test_client()
        prev = types.SimpleNamespace(
            mode=astro_clock_api.ClockMode.REALTIME,
            location="Jerusalem, Israel",
            timezone="Asia/Jerusalem",
            custom_time=None,
            paused_at=None,
            house_system_code="W",
            latitude=31.7683,
            longitude=35.2137,
        )
        eng = types.SimpleNamespace(settings=prev, get_current_data=lambda settings=None: _stub_data())

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=eng):
            response = client.get(
                "/api/astro-clock/forensic"
                "?mode=manual"
                "&datetime=2026-03-22T06:32:00"
                "&location=Basra%2C%20Iraq"
                "&timezone=Asia/Baghdad"
                "&latitude=abc"
                "&longitude=47.84212"
            )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid latitude")

    def test_forensic_route_rejects_invalid_mode_before_context_resolution(self):
        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            side_effect=AssertionError("context resolver should not be called"),
        ):
            response = client.get("/api/astro-clock/forensic?mode=INVALID_MODE")

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid mode")

    def test_forensic_route_rejects_invalid_case_type_before_context_resolution(self):
        app = _make_app()
        client = app.test_client()

        with mock.patch.object(
            astro_clock_api,
            "_engine_instance",
            side_effect=AssertionError("chart context must not be resolved"),
        ):
            response = client.get("/api/astro-clock/forensic?case_type=unknown")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid case_type")

    def test_forensic_route_rejects_malformed_abduction_origin_before_context_resolution(self):
        app = _make_app()
        client = app.test_client()

        with mock.patch.object(
            astro_clock_api,
            "_engine_instance",
            side_effect=AssertionError("context resolver should not be called"),
        ):
            response = client.get("/api/astro-clock/forensic?abduction=1&origin=abc,def")

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid origin coordinates")

    def test_forensic_route_rejects_out_of_range_abduction_origin_before_context_resolution(self):
        app = _make_app()
        client = app.test_client()

        with mock.patch.object(
            astro_clock_api,
            "_engine_instance",
            side_effect=AssertionError("context resolver should not be called"),
        ):
            response = client.get("/api/astro-clock/forensic?abduction=1&origin=91,181")

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid origin coordinates")

    def test_forensic_route_rejects_non_finite_abduction_corridor_before_context_resolution(self):
        app = _make_app()
        client = app.test_client()

        for corridor_deg in ("nan", "inf", "-inf"):
            with self.subTest(corridor_deg=corridor_deg), mock.patch.object(
                astro_clock_api,
                "_engine_instance",
                side_effect=AssertionError("context resolver should not be called"),
            ):
                response = client.get(
                    "/api/astro-clock/forensic"
                    f"?abduction=1&origin=30,40&corridor_deg={corridor_deg}"
                )

            self.assertEqual(response.status_code, 400)
            payload = response.get_json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["error"], "Invalid corridor_deg")

    def test_forensic_route_merges_precise_modern_aspects_into_features(self):
        captured = {}
        data = _stub_data()

        def _fake_dashboard(*_args, **kwargs):
            captured.update(kwargs)
            payload = _stub_dashboard_payload()
            payload["planets"] = [
                {"planet": "Moon", "longitude": 10.0, "house": 1, "sign": "Aries"},
                {"planet": "Mercury", "longitude": 20.0, "house": 2, "sign": "Aries"},
                {"planet": "Neptune", "longitude": 200.0, "house": 8, "sign": "Libra"},
            ]
            payload["planetary_aspects_precise"] = [
                {
                    "planet1": "Mercury",
                    "planet2": "Neptune",
                    "aspect": "Square",
                    "phase": "applying",
                    "orb": 1.8,
                }
            ]
            return payload

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=_fake_dashboard,
        ):
            response = client.get("/api/astro-clock/forensic?mode=manual")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(captured.get("include_modern"))
        self.assertTrue(captured.get("extend_modern_chart_data"))
        payload = response.get_json()
        features = payload.get("features") or {}
        self.assertIn("Neptune", features.get("planets") or {})
        aspects = features.get("aspects") or {}
        self.assertIn("Mercury_to_Neptune", aspects)
        self.assertTrue(aspects["Mercury_to_Neptune"].get("applying"))

    def test_forensic_route_passes_light_mediation_into_survivability_features(self):
        captured = {}
        data = _stub_data()
        data.chart_result = {
            "reasoning": [
                {
                    "stage": "Perfection",
                    "rule": "Translation of light by Jupiter carries testimony to the victim",
                }
            ],
            "translator": "Jupiter",
            "chart_data": {
                "planets": [],
                "aspects": [],
                "house_rulers": {},
            },
        }

        def fake_compute_survivability(features, findings=None, categories=None, *, case_type="general"):
            captured["features"] = features
            return {
                "level": "Moderate",
                "score": 0.0,
                "outcome_band": "mixed_nonfatal",
                "case_type": case_type,
                "victim_significators": [],
                "breakdown": {"recovery_support": 0.0, "light_mediation": 0.0},
                "evidence": {"light_mediation": []},
                "note": "stubbed",
            }

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=lambda *_args, **_kwargs: _stub_dashboard_payload(),
        ), mock.patch.object(
            survivability_module,
            "compute_survivability",
            side_effect=fake_compute_survivability,
        ):
            response = client.get("/api/astro-clock/forensic?mode=manual")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("light_mediation", {}).get("translation"))
        self.assertEqual(payload.get("light_mediation", {}).get("translator"), "Jupiter")
        feature_mediation = captured["features"].get("light_mediation") or {}
        self.assertTrue(feature_mediation.get("translation"))
        self.assertEqual(feature_mediation.get("translator"), "Jupiter")

    def test_forensic_route_extracts_morin_light_mediation_with_participants(self):
        captured = {}
        data = _stub_data()

        def fake_dashboard(*_args, **kwargs):
            captured["dashboard_kwargs"] = kwargs
            payload = _stub_dashboard_payload()
            payload["morin_patterns"] = {
                "translation": [
                    {
                        "from": "Moon",
                        "middle": "Jupiter",
                        "to": "Sun",
                        "from_leg": {
                            "aspect": "Trine",
                            "orb": 0.4,
                            "phase": "separating",
                            "partile": True,
                        },
                        "to_leg": {
                            "aspect": "Sextile",
                            "orb": 0.9,
                            "phase": "applying",
                            "complete_platic": True,
                        },
                        "favorable": True,
                    }
                ],
                "collection": [],
            }
            return payload

        def fake_compute_survivability(features, findings=None, categories=None, *, case_type="general"):
            captured["features"] = features
            return {
                "level": "Moderate",
                "score": 0.0,
                "outcome_band": "mixed_nonfatal",
                "case_type": case_type,
                "victim_significators": [],
                "breakdown": {"recovery_support": 0.0, "light_mediation": 0.0},
                "evidence": {"light_mediation": []},
                "note": "stubbed",
            }

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=fake_dashboard,
        ), mock.patch.object(
            survivability_module,
            "compute_survivability",
            side_effect=fake_compute_survivability,
        ):
            response = client.get("/api/astro-clock/forensic?mode=manual")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(captured["dashboard_kwargs"].get("include_morin"))
        payload = response.get_json() or {}
        mediation = payload.get("light_mediation") or {}
        self.assertTrue(mediation.get("translation"))
        self.assertEqual(mediation.get("translator"), "Jupiter")
        self.assertEqual(mediation.get("participants"), ["Moon", "Jupiter", "Sun"])
        self.assertEqual(mediation.get("from_leg", {}).get("aspect"), "Trine")
        self.assertEqual(mediation.get("to_leg", {}).get("aspect"), "Sextile")
        self.assertEqual(len(mediation.get("legs") or []), 2)
        self.assertEqual(
            (captured["features"].get("light_mediation") or {}).get("participants"),
            ["Moon", "Jupiter", "Sun"],
        )
        self.assertEqual(
            (captured["features"].get("light_mediation") or {}).get("legs", [])[0].get("aspect"),
            "Trine",
        )

    def test_forensic_route_extracts_morin_denial_as_prohibition_not_collection(self):
        captured = {}
        data = _stub_data()

        def fake_dashboard(*_args, **kwargs):
            captured["dashboard_kwargs"] = kwargs
            payload = _stub_dashboard_payload()
            payload["morin_patterns"] = {
                "translation": [],
                "collection": [],
                "frustration": [
                    {
                        "frustrated": "Moon",
                        "target": "Mars",
                        "frustrating": "Saturn",
                        "days_C_before_A": 1.5,
                    }
                ],
            }
            return payload

        def fake_compute_survivability(features, findings=None, categories=None, *, case_type="general"):
            captured["features"] = features
            return {
                "level": "Moderate",
                "score": 0.0,
                "outcome_band": "mixed_nonfatal",
                "case_type": case_type,
                "victim_significators": [],
                "breakdown": {"recovery_support": 0.0, "light_mediation": 0.0},
                "evidence": {"light_mediation": []},
                "note": "stubbed",
            }

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=object()), mock.patch.object(
            astro_clock_api,
            "_data_for_request_clock_context",
            return_value=(data, data.settings),
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=fake_dashboard,
        ), mock.patch.object(
            survivability_module,
            "compute_survivability",
            side_effect=fake_compute_survivability,
        ):
            response = client.get("/api/astro-clock/forensic?mode=manual")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(captured["dashboard_kwargs"].get("include_morin"))
        mediation = (response.get_json() or {}).get("light_mediation") or {}
        self.assertTrue(mediation.get("prohibition"))
        self.assertFalse(mediation.get("translation"))
        self.assertFalse(mediation.get("collection"))
        self.assertEqual(mediation.get("denial_type"), "frustration")
        self.assertEqual(mediation.get("prohibitor"), "Saturn")
        self.assertEqual(mediation.get("participants"), ["Moon", "Mars", "Saturn"])
        self.assertEqual(
            (captured["features"].get("light_mediation") or {}).get("denial_type"),
            "frustration",
        )

    def test_forensic_route_returns_abduction_map_payload_for_manual_case(self):
        app = _make_app()
        client = app.test_client()

        response = client.get(
            "/api/astro-clock/forensic",
            query_string={
                "mode": "manual",
                "datetime": "2004-08-12T23:00:00",
                "location": "Basra, Iraq",
                "timezone": "Asia/Baghdad",
                "house_system_code": "R",
                "latitude": "30.51624",
                "longitude": "47.84212",
                "abduction": "1",
                "origin": "30.51624,47.84212",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("abduction_map", payload)
        self.assertIn("survivability", payload)
        feature_planets = (payload.get("features") or {}).get("planets") or {}
        self.assertIn("Uranus", feature_planets)
        self.assertIn("Neptune", feature_planets)
        self.assertIn("Pluto", feature_planets)
        feature_aspects = (payload.get("features") or {}).get("aspects") or {}
        self.assertTrue(
            any(any(name in key for name in ("Uranus", "Neptune", "Pluto")) for key in feature_aspects)
        )

        abduction_map = payload["abduction_map"]
        self.assertAlmostEqual(float(abduction_map["origin"]["lat"]), 30.51624, places=5)
        self.assertAlmostEqual(float(abduction_map["origin"]["lon"]), 47.84212, places=5)
        self.assertEqual(abduction_map["origin_source"], "query_origin")
        self.assertIsInstance(abduction_map.get("bearings"), list)
        self.assertGreater(len(abduction_map["bearings"]), 0)
        first_bearing = abduction_map["bearings"][0]
        self.assertIn("planet", first_bearing)
        self.assertIn("azimuth_deg", first_bearing)

    def test_forensic_route_honors_case_type_for_survivability(self):
        app = _make_app()
        client = app.test_client()

        response = client.get(
            "/api/astro-clock/forensic",
            query_string={
                "mode": "manual",
                "datetime": "2005-02-04T13:45:00",
                "location": "Baghdad University, Baghdad, Iraq",
                "timezone": "Asia/Baghdad",
                "house_system_code": "R",
                "case_type": "adult_female",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        self.assertIn("survivability", payload)
        self.assertEqual(payload["survivability"].get("case_type"), "adult_female")
        self.assertIn(payload["survivability"].get("outcome_band"), {"release_favored", "risk_loaded_survival", "fatal_pressure_dominant", "nonfatal_tilt", "mixed_nonfatal"})
        self.assertIn("Moon", payload["survivability"].get("victim_significators") or [])
        self.assertGreaterEqual(len(payload["survivability"].get("victim_significators") or []), 2)
        self.assertIn("recovery_support", payload["survivability"].get("breakdown") or {})

    def test_forensic_route_uses_query_coordinates_for_abduction_map_when_origin_missing(self):
        app = _make_app()
        client = app.test_client()

        response = client.get(
            "/api/astro-clock/forensic",
            query_string={
                "mode": "manual",
                "datetime": "2004-08-12T23:00:00",
                "location": "Al-Istiqlal Street, Al Ashar, Basra, Iraq",
                "timezone": "Asia/Baghdad",
                "house_system_code": "R",
                "latitude": "30.51624",
                "longitude": "47.84212",
                "abduction": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("abduction_map", payload)

        abduction_map = payload["abduction_map"]
        self.assertAlmostEqual(float(abduction_map["origin"]["lat"]), 30.51624, places=5)
        self.assertAlmostEqual(float(abduction_map["origin"]["lon"]), 47.84212, places=5)
        self.assertEqual(abduction_map["origin_source"], "query_coordinates")
        roles = {item.get("role") for item in abduction_map.get("bearings") or []}
        self.assertIn("H7_ruler", roles)
        self.assertIn("H3_ruler", roles)
        self.assertIn("H9_ruler", roles)
