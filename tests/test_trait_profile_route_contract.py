from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase, mock

from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


class TraitProfileRouteContractTests(TestCase):
    def test_trait_profile_returns_chart_snapshot_and_profile_payload(self):
        class _StubSettings:
            mode = "realtime"
            location = "Jerusalem"
            timezone = "Asia/Jerusalem"
            house_system_code = "R"
            custom_time = None

        class _StubEngine:
            settings = _StubSettings()

            def get_current_data(self, settings=None):
                active = settings or self.settings
                return types.SimpleNamespace(
                    timestamp=active.custom_time or datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc),
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
            def evaluate(self, metrics):
                self.metrics = metrics
                return {
                    "summary": {"dominant_element": "Fire", "dominant_modality": "Cardinal", "flags": {"mercury_shock": True}},
                    "top_traits": [{"id": "warlike", "name": "Warlike", "score": 42.0, "band": "possible", "polarity": "neutral", "source_status": "curated", "provisional": False}],
                    "summary_traits": [{"id": "warlike", "name": "Warlike", "score": 42.0, "band": "possible", "polarity": "neutral", "source_status": "curated", "provisional": False}],
                    "top_traits_by_polarity": {"positive": [], "neutral": [{"id": "warlike", "name": "Warlike", "score": 42.0, "band": "possible", "polarity": "neutral", "source_status": "curated", "provisional": False}], "negative": []},
                    "traits": [{"id": "warlike", "name": "Warlike", "score": 42.0, "band": "possible", "polarity": "neutral", "source_status": "curated", "provisional": False}],
                    "guidance": [{"category": "Morin House", "term": "H1", "do": "Lean into: life", "dont": "Avoid excess"}],
                    "trait_enrichment_meta": {"morin_keywords_policy": "canonical_non_scoring", "version": 1},
                }

        fake_house_influence = types.SimpleNamespace(
            compute_house_influences=lambda *_args, **_kwargs: {
                "houses": [
                    {
                        "house": 1,
                        "sign": "Pisces",
                        "influences": [{"planet": "Mars", "type": "occupation", "value": 60.24}],
                    }
                ],
                "planet_strengths": {},
            }
        )
        fake_traits_engine = types.SimpleNamespace(TraitEngine=lambda: _FakeTraitEngine())

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=_StubEngine()), mock.patch.object(
            astro_clock_api,
            "compute_metrics",
            return_value={"element_balance": {"Fire": 4.0}, "modality_balance": {"Cardinal": 3.0}},
        ), mock.patch.object(
            astro_clock_api,
            "compute_sect_info",
            return_value={"chart_sect": "day"},
        ), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            return_value={
                "timestamp": "2026-03-29T08:00:00+00:00",
                "location": "Jerusalem",
                "timezone": "Asia/Jerusalem",
                "timezone_label": "Asia/Jerusalem (UTC+02:00)",
                "planets": [{"planet": "Sun", "sign": "Aries", "house": 1, "longitude": 1.5}],
                "top_aspects": [{"planet1": "Sun", "planet2": "Moon", "aspect": "Conjunction", "orb": 0.4}],
                "morin_patterns": {"translation": [{"planet": "Mercury"}]},
            },
        ), mock.patch.dict(
            sys.modules,
            {"house_influence": fake_house_influence, "traits.engine": fake_traits_engine},
        ):
            app = _make_app()
            client = app.test_client()
            response = client.get("/api/astro-clock/traits/profile?special_degree=25%20Leo")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["summary"]["dominant_element"], "Fire")
        self.assertEqual(data["special_degrees"], ["25 Leo"])
        self.assertEqual(data["chart_snapshot"]["location"], "Jerusalem")
        self.assertEqual(data["chart_snapshot"]["house_system"], "R")
        self.assertEqual(data["chart_snapshot"]["morin_patterns"]["translation"][0]["planet"], "Mercury")
        self.assertEqual(data["top_traits"][0]["id"], "warlike")
        self.assertEqual(data["summary_traits"][0]["id"], "warlike")
        self.assertEqual(data["top_traits_by_polarity"]["neutral"][0]["id"], "warlike")
        self.assertEqual(data["top_traits"][0]["source_status"], "curated")
        self.assertFalse(data["top_traits"][0]["provisional"])
        self.assertEqual(data["guidance"][0]["category"], "Morin House")
        self.assertEqual(data["trait_enrichment_meta"]["morin_keywords_policy"], "canonical_non_scoring")

    def test_trait_profile_gracefully_degrades_when_aux_layers_fail(self):
        class _StubSettings:
            mode = "realtime"
            location = "Jerusalem"
            timezone = "Asia/Jerusalem"
            house_system_code = "R"
            custom_time = None

        class _StubEngine:
            settings = _StubSettings()

            def get_current_data(self, settings=None):
                active = settings or self.settings
                return types.SimpleNamespace(
                    timestamp=active.custom_time or datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc),
                    settings=active,
                    chart_result={"chart_data": {"ascendant": 18.9, "midheaven": 271.5, "planets": {}, "aspects": []}},
                )

        class _ExplodingTraitEngine:
            def evaluate(self, _metrics):
                raise RuntimeError("trait engine unavailable")

        fake_traits_engine = types.SimpleNamespace(TraitEngine=lambda: _ExplodingTraitEngine())

        with mock.patch.object(astro_clock_api, "_engine_instance", return_value=_StubEngine()), mock.patch.object(
            astro_clock_api,
            "_build_dashboard_payload",
            side_effect=RuntimeError("dashboard failed"),
        ), mock.patch.object(
            astro_clock_api,
            "compute_metrics",
            side_effect=RuntimeError("metrics failed"),
        ), mock.patch.object(
            astro_clock_api,
            "compute_sect_info",
            side_effect=RuntimeError("sect failed"),
        ), mock.patch.dict(
            sys.modules,
            {"house_influence": types.SimpleNamespace(compute_house_influences=mock.Mock(side_effect=RuntimeError("house failed"))), "traits.engine": fake_traits_engine},
        ):
            app = _make_app()
            client = app.test_client()
            response = client.get("/api/astro-clock/traits/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertIsNone(data["summary"])
        self.assertEqual(data["top_traits"], [])
        self.assertEqual(data["summary_traits"], [])
        self.assertEqual(data["top_traits_by_polarity"], {})
        self.assertEqual(data["traits"], [])
        self.assertEqual(data["guidance"], [])
        self.assertEqual(data["house_influences"], {"houses": []})
        self.assertIsNone(data["sect"])
        self.assertEqual(data["chart_snapshot"]["location"], None)
