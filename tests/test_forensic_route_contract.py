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
        self.assertIn("level", payload["survivability"])
        self.assertIn("outcome_band", payload["survivability"])
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
