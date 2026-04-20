from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import TestCase, mock

from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
import primary_directions
import transits_morin


def _make_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _natal_stub():
    return (
        {"planets": [], "house_rulers": {}},
        {
            "location": "Jerusalem, Israel",
            "timezone": "Asia/Jerusalem",
            "house_system_code": "W",
        },
    )


class TransitRouteContractTests(TestCase):
    def test_scan_window_reuses_exact_engine_with_cached_natal_context(self):
        captured: dict[str, object] = {}

        def _fake_prepare(_natal_cd, **kwargs):
            captured["prepare"] = kwargs
            return "CTX"

        def _fake_compute(_natal_cd, ts_iso, **kwargs):
            captured.setdefault("compute_calls", []).append({"ts": ts_iso, **kwargs})
            return [
                {
                    "transiting": "Jupiter",
                    "natal": "Mercury (antiscia)",
                    "target_label": "Mercury (antiscia)",
                    "target_type": "antiscia",
                    "aspect": "Sextile",
                    "phase": "applying",
                    "score": 9.0,
                }
            ]

        def _fake_enrich(_natal_cd, hits, _ts, **_kwargs):
            enriched = []
            for hit in hits:
                enriched.append(
                    {
                        **hit,
                        "prediction": {
                            "description": "Jupiter Sextile Mercury (antiscia)",
                            "eventType": "promotion",
                            "lifeArea": "honors",
                            "score": 55.0,
                        },
                        "enriched_keywords": ["promotion", "public_recognition"],
                        "significance": 55.0,
                        "tone_score": 0.9,
                    }
                )
            return enriched

        with mock.patch.object(
            transits_morin,
            "_prepare_natal_context",
            side_effect=_fake_prepare,
        ), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=_fake_enrich,
        ):
            rows = transits_morin.scan_morin_transits_window(
                {"planets": []},
                "2026-03-08T00:00:00Z",
                "2026-03-08T01:00:00Z",
                step_minutes=60,
                include_modern=True,
                natal_include_modern=True,
                include_cusps=True,
                include_antiscia=True,
                include_lots=True,
            )

        self.assertEqual(captured["prepare"]["natal_include_modern"], True)
        self.assertGreaterEqual(len(captured["compute_calls"]), 2)
        first_compute = captured["compute_calls"][0]
        self.assertEqual(first_compute["_prepared_ctx"], "CTX")
        self.assertTrue(first_compute["natal_include_modern"])
        self.assertTrue(first_compute["include_antiscia"])
        self.assertEqual(rows[0]["top"][0]["prediction"]["eventType"], "promotion")
        self.assertEqual(rows[0]["_prediction_hits"][0]["prediction"]["lifeArea"], "honors")

    def test_scan_window_does_not_mark_adverse_conflict_mix_as_positive(self):
        def _fake_prepare(_natal_cd, **_kwargs):
            return "CTX"

        def _fake_compute(_natal_cd, _ts_iso, **_kwargs):
            return [
                {"transiting": "Jupiter", "target_label": "MC", "target_type": "cusp", "aspect": "Trine", "score": 12.0},
                {"transiting": "Mars", "target_label": "C7", "target_type": "cusp", "aspect": "Square", "score": 10.0},
            ]

        def _fake_enrich(_natal_cd, hits, _ts, **_kwargs):
            return [
                {
                    **hits[0],
                    "prediction": {
                        "description": "Jupiter Trine MC",
                        "eventType": "promotion",
                        "lifeArea": "honors",
                    },
                    "enriched_keywords": ["public_recognition"],
                    "prediction_tags": ["positive"],
                    "tone_score": 1.0,
                    "significance": 92.0,
                },
                {
                    **hits[1],
                    "prediction": {
                        "description": "Mars Square C7",
                        "eventType": "attack_violence",
                        "lifeArea": "conflict",
                    },
                    "enriched_keywords": ["attack_violence", "conflict"],
                    "prediction_tags": ["mixed_outcome"],
                    "tone_score": -0.15,
                    "significance": 88.0,
                },
            ]

        with mock.patch.object(transits_morin, "_prepare_natal_context", side_effect=_fake_prepare), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=_fake_enrich,
        ):
            rows = transits_morin.scan_morin_transits_window(
                {"planets": []},
                "2026-03-08T00:00:00Z",
                "2026-03-08T01:00:00Z",
                step_minutes=60,
            )

        self.assertEqual(rows[0]["tone"], "mixed")

    def test_scan_window_marks_strong_adverse_row_negative(self):
        def _fake_prepare(_natal_cd, **_kwargs):
            return "CTX"

        def _fake_compute(_natal_cd, _ts_iso, **_kwargs):
            return [
                {"transiting": "Mars", "target_label": "Asc", "target_type": "cusp", "aspect": "Square", "score": 12.0},
                {"transiting": "Saturn", "target_label": "C12", "target_type": "cusp", "aspect": "Conjunction", "score": 11.0},
            ]

        def _fake_enrich(_natal_cd, hits, _ts, **_kwargs):
            return [
                {
                    **hits[0],
                    "prediction": {
                        "description": "Mars Square Asc",
                        "eventType": "injury_accident",
                        "lifeArea": "danger",
                    },
                    "enriched_keywords": ["injury_accident", "danger"],
                    "prediction_tags": ["negative"],
                    "tone_score": -0.9,
                    "significance": 90.0,
                },
                {
                    **hits[1],
                    "prediction": {
                        "description": "Saturn Conjunction C12",
                        "eventType": "arrest_imprisonment",
                        "lifeArea": "secrets",
                    },
                    "enriched_keywords": ["arrest_imprisonment", "secrets"],
                    "prediction_tags": ["negative"],
                    "tone_score": -0.8,
                    "significance": 84.0,
                },
            ]

        with mock.patch.object(transits_morin, "_prepare_natal_context", side_effect=_fake_prepare), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=_fake_enrich,
        ):
            rows = transits_morin.scan_morin_transits_window(
                {"planets": []},
                "2026-03-08T00:00:00Z",
                "2026-03-08T01:00:00Z",
                step_minutes=60,
            )

        self.assertEqual(rows[0]["tone"], "negative")

    def test_single_transits_route_preserves_filters_and_observer_context(self):
        captured: dict[str, object] = {}

        def _fake_compute(natal_cd, ts, **kwargs):
            captured["compute"] = {"natal_cd": natal_cd, "ts": ts, **kwargs}
            return [
                {
                    "transiting": "Saturn",
                    "natal": "Sun",
                    "target_label": "Sun",
                    "target_type": "planet",
                    "aspect": "Square",
                    "score": 7.5,
                    "significance": 6.2,
                }
            ]

        def _fake_enrich(natal_cd, hits, ts, **kwargs):
            captured["enrich"] = {"natal_cd": natal_cd, "ts": ts, **kwargs}
            return [{**hits[0], "concordance": {"overall_concordance": 0.8}}]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=_fake_enrich,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            return_value=[{"event_type": "promotion", "score": 9.1, "probability": 0.91}],
        ):
            response = client.get(
                "/api/astro-clock/transits"
                "?natal_snap_id=snap-1"
                "&house_system_code=W"
                "&transit_datetime=2026-03-08T12:00:00Z"
                "&include_modern=1"
                "&include_natal_modern=1"
                "&include_cusps=1"
                "&include_antiscia=1"
                "&include_lots=1"
                "&focus_house=10"
                "&focus_planet=Saturn"
                "&sensitive_house=4"
                "&sensitive_planet=Moon"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["natal"]["house_system_code"], "W")
        self.assertEqual(data["transit_timestamp"], "2026-03-08T12:00:00Z")
        self.assertEqual(data["predictions"][0]["event_type"], "promotion")

        compute = captured["compute"]
        self.assertEqual(compute["ts"], "2026-03-08T12:00:00Z")
        self.assertTrue(compute["include_modern"])
        self.assertTrue(compute["natal_include_modern"])
        self.assertTrue(compute["include_cusps"])
        self.assertTrue(compute["include_antiscia"])
        self.assertTrue(compute["include_lots"])
        self.assertEqual(compute["focus_houses"], [10])
        self.assertEqual(compute["focus_planets"], ["Saturn"])
        self.assertEqual(compute["sensitive_houses"], [4])
        self.assertEqual(compute["sensitive_planets"], ["Moon"])
        self.assertEqual(compute["observer_location"], "Jerusalem, Israel")
        self.assertEqual(compute["observer_timezone"], "Asia/Jerusalem")

        enrich = captured["enrich"]
        self.assertEqual(enrich["observer_location"], "Jerusalem, Israel")
        self.assertEqual(enrich["observer_timezone"], "Asia/Jerusalem")

    def test_single_transits_route_retries_minimal_enrichment_when_rich_enrichment_fails(self):
        enrich_calls: list[dict[str, object]] = []

        def _fake_compute(_natal_cd, _ts, **_kwargs):
            return [
                {
                    "transiting": "Mars",
                    "natal": "C7",
                    "target_label": "C7",
                    "target_type": "cusp",
                    "aspect": "Opposition",
                    "score": 9.0,
                }
            ]

        def _fake_enrich(_natal_cd, hits, _ts, **kwargs):
            enrich_calls.append({"pd_windows": list(kwargs.get("pd_windows") or [])})
            if kwargs.get("pd_windows"):
                raise RuntimeError("rich enrich failed")
            return [
                {
                    **hits[0],
                    "significance": 81.0,
                    "prediction_score": 81.0,
                    "tone": "mixed",
                    "prediction": {
                        "eventType": "attack_violence",
                        "lifeArea": "conflict",
                        "description": "Mars Opposition C7",
                        "score": 81.0,
                        "tags": ["negative"],
                    },
                    "concordance": {"overall_concordance": 0.81},
                    "enriched_keywords": ["attack_violence", "conflict"],
                }
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=_fake_enrich,
        ), mock.patch.object(
            primary_directions,
            "compute_primary_direction_windows",
            return_value=[{"type": "promotion", "strength": 5.0}],
        ):
            response = client.get(
                "/api/astro-clock/transits"
                "?natal_datetime=1948-05-14T14:00:00.000Z"
                "&natal_location=Jerusalem,+Israel"
                "&natal_timezone=Asia/Jerusalem"
                "&house_system_code=W"
                "&transit_datetime=2026-03-08T12:00:00Z"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(len(enrich_calls), 2)
        self.assertTrue(enrich_calls[0]["pd_windows"])
        self.assertEqual(enrich_calls[1]["pd_windows"], [])
        self.assertEqual(data["transits"][0]["significance"], 81.0)
        self.assertEqual(data["transits"][0]["prediction"]["eventType"], "attack_violence")
        self.assertEqual(data["predictions"][0]["event_type"], "attack_violence")

    def test_transits_window_route_uses_center_range_fallback_and_context_filters(self):
        captured: dict[str, object] = {}

        def _fake_scan(natal_cd, start, end, **kwargs):
            captured["scan"] = {"natal_cd": natal_cd, "start": start, "end": end, **kwargs}
            return [
                {
                    "timestamp": "2026-03-08T09:00:00+00:00",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Square", "score": 5.0}],
                    "step_score": 5.0,
                    "tone": "negative",
                },
                {
                    "timestamp": "2026-03-08T12:00:00+00:00",
                    "count": 1,
                    "top": [{"transiting": "Jupiter", "natal": "Moon", "aspect": "Trine", "score": 6.0}],
                    "step_score": 6.0,
                    "tone": "positive",
                },
            ]

        def _fake_predictions(hits, ts_iso):
            return [{"event_type": f"evt-{ts_iso[:13]}", "score": len(hits)}]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            side_effect=_fake_predictions,
        ):
            response = client.get(
                "/api/astro-clock/transits/window"
                "?natal_snap_id=snap-1"
                "&house_system_code=W"
                "&center=2026-03-08T12:00:00Z"
                "&range_hours=6"
                "&step_minutes=30"
                "&include_modern=1"
                "&focus_house=10"
                "&focus_planet=Jupiter"
                "&sensitive_house=4"
                "&sensitive_planet=Moon"
                "&transiting=Saturn"
                "&natal=Sun"
                "&aspect=Square"
                "&pd_start=2026-03-08T08:00:00Z"
                "&pd_end=2026-03-08T13:00:00Z"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(
            data["context_window"],
            {"start": "2026-03-08T09:00:00+00:00", "end": "2026-03-08T15:00:00+00:00"},
        )
        self.assertEqual(data["context_filters"]["pd"]["start"], "2026-03-08T08:00:00Z")
        self.assertEqual(len(data["series"]), 2)
        self.assertEqual(data["series"][0]["timestamp"], "2026-03-08T09:00:00+00:00")
        self.assertEqual(data["series"][1]["timestamp"], "2026-03-08T12:00:00+00:00")
        self.assertEqual(data["predictions"][0]["event_type"], "evt-2026-03-08T09")

        scan = captured["scan"]
        self.assertEqual(scan["start"], "2026-03-08T09:00:00+00:00")
        self.assertEqual(scan["end"], "2026-03-08T15:00:00+00:00")
        self.assertEqual(scan["step_minutes"], 30)
        self.assertTrue(scan["include_modern"])
        self.assertEqual(scan["focus_houses"], [10])
        self.assertEqual(scan["focus_planets"], ["Jupiter"])
        self.assertEqual(scan["sensitive_houses"], [4])
        self.assertEqual(scan["sensitive_planets"], ["Moon"])
        self.assertEqual(scan["flt_transiting"], ["Saturn"])
        self.assertEqual(scan["flt_natal"], ["Sun"])
        self.assertEqual(scan["flt_aspects"], ["Square"])
        self.assertEqual(scan["observer_location"], "Jerusalem, Israel")
        self.assertEqual(scan["observer_timezone"], "Asia/Jerusalem")

    def test_predictor_route_prefers_explicit_observer_context(self):
        captured: dict[str, object] = {}

        def _fake_scan(natal_cd, start, end, **kwargs):
            captured["scan"] = {"natal_cd": natal_cd, "start": start, "end": end, **kwargs}
            return [
                {
                    "timestamp": "2026-03-08T10:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Jupiter", "natal": "Sun", "aspect": "Trine", "score": 9.0}],
                    "step_score": 9.0,
                    "tone": "positive",
                }
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            return_value=[{
                "event_type": "recognition",
                "life_area": "honors",
                "label": "Jupiter Trine Sun",
                "description": "Jupiter Trine Sun",
                "score": 8.8,
                "probability": 0.88,
                "tags": ["public_recognition"],
                "factors": {
                    "transit": "Jupiter Trine Sun",
                    "determination_strength": 9.0,
                    "significance": 8.8,
                },
            }],
        ):
            response = client.get(
                "/api/astro-clock/predictor"
                "?natal_snap_id=snap-1"
                "&house_system_code=W"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T12:00:00Z"
                "&location=Tokyo"
                "&timezone=Asia/Tokyo"
                "&include_series=1"
                "&limit=5"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]
        self.assertEqual(data["step_minutes"], 60)
        self.assertEqual(data["observer"], {"location": "Tokyo", "timezone": "Asia/Tokyo"})
        self.assertEqual(data["predictions"][0]["event_type"], "recognition")
        self.assertEqual(data["prediction_groups"][0]["event_type"], "recognition")
        self.assertEqual(data["prediction_groups"][0]["count"], 1)
        self.assertIn("public_recognition", data["prediction_groups"][0]["keyword_tokens"])
        self.assertIn("series", data)

        scan = captured["scan"]
        self.assertEqual(scan["observer_location"], "Tokyo")
        self.assertEqual(scan["observer_timezone"], "Asia/Tokyo")

    def test_predictor_route_groups_sustained_support_above_isolated_spike(self):
        def _fake_scan(_natal_cd, _start, _end, **_kwargs):
            return [
                {
                    "timestamp": "2026-03-08T10:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Trine", "score": 18.0}],
                    "step_score": 18.0,
                    "tone": "positive",
                },
                {
                    "timestamp": "2026-03-08T11:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Trine", "score": 19.0}],
                    "step_score": 19.0,
                    "tone": "positive",
                },
                {
                    "timestamp": "2026-03-08T12:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Jupiter", "natal": "MC", "aspect": "Trine", "score": 32.0}],
                    "step_score": 32.0,
                    "tone": "positive",
                },
            ]

        def _fake_predictions(_hits, ts_iso):
            if ts_iso in {"2026-03-08T10:00:00Z", "2026-03-08T11:00:00Z"}:
                return [{
                    "date": ts_iso,
                    "event_type": "recognition",
                    "life_area": "honors",
                    "label": "Saturn Trine Sun",
                    "description": "Saturn Trine Sun",
                    "score": 19.0,
                    "probability": 0.58,
                    "tags": ["public_recognition"],
                    "factors": {
                        "transit": "Saturn Trine Sun",
                        "determination_strength": 8.0,
                        "significance": 16.0,
                    },
                }]
            return [{
                "date": ts_iso,
                "event_type": "promotion",
                "life_area": "honors",
                "label": "Jupiter Trine MC",
                "description": "Jupiter Trine MC",
                "score": 32.0,
                "probability": 0.9,
                "tags": ["honor_award"],
                "factors": {
                    "transit": "Jupiter Trine MC",
                    "determination_strength": 9.0,
                    "significance": 20.0,
                },
            }]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            side_effect=_fake_predictions,
        ):
            response = client.get(
                "/api/astro-clock/predictor"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T12:00:00Z"
                "&limit=5"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        groups = payload["data"]["prediction_groups"]
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0]["description"], "Saturn Trine Sun")
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(groups[1]["description"], "Jupiter Trine MC")
        self.assertGreater(groups[0]["support_score"], groups[1]["support_score"])
        self.assertIn("recognition", groups[0]["keyword_tokens"])
        self.assertIn("honors", groups[0]["keyword_tokens"])

    def test_predictor_group_ranking_balances_diffuse_and_concentrated_support(self):
        predictions = []
        for ts_iso in (
            "2026-03-08T10:00:00Z",
            "2026-03-08T11:00:00Z",
            "2026-03-08T12:00:00Z",
            "2026-03-08T13:00:00Z",
        ):
            predictions.append({
                "date": ts_iso,
                "event_type": "recognition",
                "life_area": "honors",
                "label": "Diffuse Recognition Transit",
                "description": "Diffuse Recognition Transit",
                "score": 14.0,
                "probability": 0.45,
                "tags": ["public_recognition"],
                "factors": {
                    "transit": "Saturn Trine Sun",
                    "determination_strength": 6.0,
                    "significance": 12.0,
                },
            })
        for ts_iso in (
            "2026-03-08T20:00:00Z",
            "2026-03-08T21:00:00Z",
        ):
            predictions.append({
                "date": ts_iso,
                "event_type": "promotion",
                "life_area": "honors",
                "label": "Concentrated Promotion Transit",
                "description": "Concentrated Promotion Transit",
                "score": 50.0,
                "probability": 0.95,
                "tags": ["honor_award"],
                "factors": {
                    "transit": "Jupiter Trine MC",
                    "determination_strength": 20.0,
                    "significance": 40.0,
                },
            })

        groups = astro_clock_api._aggregate_predictor_predictions(predictions, limit=5, step_minutes=60)

        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0]["event_type"], "promotion")
        self.assertEqual(groups[1]["event_type"], "recognition")
        self.assertGreater(groups[1]["support_score"], groups[0]["support_score"])
        self.assertGreater(groups[0]["support_focus"], groups[1]["support_focus"])

    def test_predictor_groups_merge_equivalent_windows_and_keep_supporting_transits(self):
        predictions = []
        for label, transit in (
            ("Jupiter Semi-sextile Saturn", "Jupiter Semi-sextile Saturn"),
            ("Jupiter Sextile Saturn (antiscia)", "Jupiter Sextile Saturn (antiscia)"),
            ("Jupiter Trine Saturn (contra-antiscia)", "Jupiter Trine Saturn (contra-antiscia)"),
        ):
            for ts_iso in (
                "2026-03-08T10:00:00Z",
                "2026-03-08T11:00:00Z",
            ):
                predictions.append({
                    "date": ts_iso,
                    "event_type": "promotion",
                    "life_area": "honors",
                    "label": label,
                    "description": label,
                    "score": 100.0,
                    "probability": 1.0,
                    "tags": ["honor_award"],
                    "factors": {
                        "transit": transit,
                        "determination_strength": 20.0,
                        "significance": 100.0,
                    },
                })

        groups = astro_clock_api._aggregate_predictor_predictions(predictions, limit=5, step_minutes=60)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["event_type"], "promotion")
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(groups[0]["start"], "2026-03-08T10:00:00Z")
        self.assertEqual(groups[0]["end"], "2026-03-08T11:00:00Z")
        self.assertEqual(len(groups[0]["supporting_transits"]), 3)
        self.assertIn("Jupiter Trine Saturn (contra-antiscia)", groups[0]["supporting_transits"])

    def test_predictor_groups_keep_distinct_event_families_visible_before_duplicates(self):
        predictions = []
        for label in (
            "Jupiter Semi-sextile Saturn",
            "Jupiter Sextile Saturn (antiscia)",
            "Jupiter Trine Saturn (contra-antiscia)",
        ):
            for ts_iso in (
                "2026-03-08T10:00:00Z",
                "2026-03-08T11:00:00Z",
            ):
                predictions.append({
                    "date": ts_iso,
                    "event_type": "promotion",
                    "life_area": "honors",
                    "label": label,
                    "description": label,
                    "score": 100.0,
                    "probability": 1.0,
                    "tags": ["honor_award"],
                    "factors": {
                        "transit": label,
                        "determination_strength": 20.0,
                        "significance": 100.0,
                    },
                })

        predictions.append({
            "date": "2026-03-08T11:00:00Z",
            "event_type": "attack_violence",
            "life_area": "conflict",
            "label": "Moon Quincunx C7 (contra-antiscia)",
            "description": "Moon Quincunx C7 (contra-antiscia)",
            "score": 22.5,
            "probability": 0.05,
            "tags": ["conflict"],
            "factors": {
                "transit": "Moon Quincunx C7 (contra-antiscia)",
                "determination_strength": 4.0,
                "significance": 22.5,
            },
        })

        groups = astro_clock_api._aggregate_predictor_predictions(predictions, limit=5, step_minutes=60)

        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0]["event_type"], "promotion")
        self.assertEqual(groups[1]["event_type"], "attack_violence")
        self.assertEqual(groups[1]["life_area"], "conflict")

    def test_predictor_route_splits_disconnected_recurrences_into_separate_windows(self):
        def _fake_scan(_natal_cd, _start, _end, **_kwargs):
            return [
                {
                    "timestamp": "2026-03-08T10:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Trine", "score": 18.0}],
                    "step_score": 18.0,
                    "tone": "positive",
                },
                {
                    "timestamp": "2026-03-08T11:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Trine", "score": 18.5}],
                    "step_score": 18.5,
                    "tone": "positive",
                },
                {
                    "timestamp": "2026-03-08T20:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Saturn", "natal": "Sun", "aspect": "Trine", "score": 18.0}],
                    "step_score": 18.0,
                    "tone": "positive",
                },
            ]

        def _fake_predictions(_hits, ts_iso):
            return [{
                "date": ts_iso,
                "event_type": "recognition",
                "life_area": "honors",
                "label": "Saturn Trine Sun",
                "description": "Saturn Trine Sun",
                "score": 18.0,
                "probability": 0.58,
                "tags": ["public_recognition"],
                "factors": {
                    "transit": "Saturn Trine Sun",
                    "determination_strength": 8.0,
                    "significance": 16.0,
                },
            }]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            side_effect=_fake_predictions,
        ):
            response = client.get(
                "/api/astro-clock/predictor"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T23:00:00Z"
                "&step_minutes=60"
                "&limit=5"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        groups = payload["data"]["prediction_groups"]
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0]["description"], "Saturn Trine Sun")
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(groups[0]["start"], "2026-03-08T10:00:00Z")
        self.assertEqual(groups[0]["end"], "2026-03-08T11:00:00Z")
        self.assertEqual(groups[1]["count"], 1)
        self.assertEqual(groups[1]["start"], "2026-03-08T20:00:00Z")
        self.assertEqual(groups[1]["end"], "2026-03-08T20:00:00Z")
        self.assertLess(groups[0]["window_span_minutes"], 120.0)

    def test_predictor_peaks_choose_family_stronger_row_inside_flat_plateau(self):
        def _fake_scan(_natal_cd, _start, _end, **_kwargs):
            return [
                {
                    "timestamp": "2026-03-08T10:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Mars", "natal": "C7", "aspect": "Square", "score": 24.0}],
                    "step_score": 24.0,
                    "tone": "mixed",
                },
                {
                    "timestamp": "2026-03-08T11:00:00Z",
                    "count": 1,
                    "top": [{"transiting": "Jupiter", "natal": "MC", "aspect": "Trine", "score": 24.0}],
                    "step_score": 24.0,
                    "tone": "positive",
                },
            ]

        def _fake_predictions(_hits, ts_iso):
            if ts_iso == "2026-03-08T10:00:00Z":
                return [{
                    "date": ts_iso,
                    "event_type": "attack_violence",
                    "life_area": "conflict",
                    "label": "Mars Square C7",
                    "description": "Mars Square C7",
                    "score": 24.0,
                    "probability": 0.72,
                    "tags": ["conflict"],
                    "factors": {
                        "transit": "Mars Square C7",
                        "determination_strength": 12.0,
                        "significance": 25.0,
                    },
                }]
            return [{
                "date": ts_iso,
                "event_type": "promotion",
                "life_area": "honors",
                "label": "Jupiter Trine MC",
                "description": "Jupiter Trine MC",
                "score": 24.0,
                "probability": 0.72,
                "tags": ["honor_award"],
                "factors": {
                    "transit": "Jupiter Trine MC",
                    "determination_strength": 6.0,
                    "significance": 14.0,
                },
            }]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            side_effect=_fake_predictions,
        ):
            response = client.get(
                "/api/astro-clock/predictor"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T12:00:00Z"
                "&limit=5"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        peaks = payload["data"]["peaks"]
        self.assertGreaterEqual(len(peaks), 1)
        self.assertEqual(peaks[0]["timestamp"], "2026-03-08T10:00:00Z")
        self.assertEqual(peaks[0]["event_type"], "attack_violence")
        self.assertEqual(peaks[0]["life_area"], "conflict")
        self.assertIn("conflict", peaks[0]["keyword_tokens"])

    def test_row_localization_score_boosts_supported_rows(self):
        row = {
            "timestamp": "2026-03-08T10:00:00Z",
            "step_score": 24.0,
            "predictions": [
                {
                    "date": "2026-03-08T10:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "score": 24.0,
                    "probability": 0.72,
                    "factors": {
                        "determination_strength": 12.0,
                        "significance": 25.0,
                    },
                }
            ],
        }
        astro_clock_api._apply_row_localization(row)
        self.assertEqual(row["raw_step_score"], 24.0)
        self.assertGreater(row["localization_score"], 0.0)
        self.assertGreater(row["step_score"], row["raw_step_score"])

    def test_group_window_localization_is_a_modest_mid_window_nudge(self):
        series = [
            {
                "timestamp": "2026-03-08T10:00:00Z",
                "count": 1,
                "raw_step_score": 640.0,
                "step_score": 640.0,
                "localization_score": 8.0,
                "predictions": [{
                    "date": "2026-03-08T10:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "description": "Jupiter Trine MC",
                    "factors": {"transit": "Jupiter Trine MC"},
                }],
            },
            {
                "timestamp": "2026-03-09T10:00:00Z",
                "count": 1,
                "raw_step_score": 680.0,
                "step_score": 680.0,
                "localization_score": 8.0,
                "predictions": [{
                    "date": "2026-03-09T10:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "description": "Jupiter Trine MC",
                    "factors": {"transit": "Jupiter Trine MC"},
                }],
            },
        ]
        grouped_predictions = [{
            "event_type": "promotion",
            "life_area": "honors",
            "description": "Jupiter Trine MC",
            "transit": "Jupiter Trine MC",
            "start": "2026-03-08T10:00:00Z",
            "end": "2026-03-10T10:00:00Z",
            "dominant_timestamp": "2026-03-08T10:00:00Z",
            "support_density": 120.0,
        }]

        astro_clock_api._apply_group_window_localization(series, grouped_predictions)

        early_row, mid_row = series
        self.assertGreater(float(mid_row["window_localization_score"]), 0.0)
        self.assertGreater(float(early_row["window_localization_score"]), 0.0)
        self.assertLess(float(mid_row["window_localization_score"]), 120.0)
        self.assertLess(float(early_row["window_localization_score"]), 120.0)
        self.assertGreater(float(mid_row["step_score"]), float(early_row["step_score"]))

    def test_predictor_peak_rows_skip_redundant_adjacent_hours(self):
        rows = [
            {
                "timestamp": "2026-03-08T10:00:00Z",
                "count": 4,
                "step_score": 50.0,
                "predictions": [{
                    "date": "2026-03-08T10:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "description": "Jupiter Trine MC",
                    "score": 30.0,
                    "probability": 1.0,
                    "factors": {"transit": "Jupiter Trine MC", "determination_strength": 10.0, "significance": 20.0},
                }],
            },
            {
                "timestamp": "2026-03-08T11:00:00Z",
                "count": 4,
                "step_score": 49.5,
                "predictions": [{
                    "date": "2026-03-08T11:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "description": "Jupiter Trine MC",
                    "score": 29.8,
                    "probability": 1.0,
                    "factors": {"transit": "Jupiter Trine MC", "determination_strength": 10.0, "significance": 20.0},
                }],
            },
            {
                "timestamp": "2026-03-08T20:00:00Z",
                "count": 4,
                "step_score": 48.0,
                "predictions": [{
                    "date": "2026-03-08T20:00:00Z",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "description": "Jupiter Trine MC",
                    "score": 28.0,
                    "probability": 1.0,
                    "factors": {"transit": "Jupiter Trine MC", "determination_strength": 10.0, "significance": 20.0},
                }],
            },
        ]

        peaks = astro_clock_api._build_predictor_peak_rows(rows, limit=5)

        self.assertEqual(len(peaks), 2)
        self.assertEqual(peaks[0]["timestamp"], "2026-03-08T10:00:00Z")
        self.assertEqual(peaks[1]["timestamp"], "2026-03-08T20:00:00Z")

    def test_stream_route_emits_predictor_aware_peaks_and_scores(self):
        call_counter = {"count": 0}

        def _fake_compute(_natal_cd, ts_iso, **kwargs):
            call_counter["count"] += 1
            target = "Sun" if call_counter["count"] == 1 else "Moon"
            return [
                {
                    "transiting": "Saturn",
                    "natal": target,
                    "target_label": target,
                    "target_type": "planet",
                    "aspect": "Square",
                    "score": 5.0 + call_counter["count"],
                    "significance": 4.0 + call_counter["count"],
                    "phase": "applying",
                }
            ]

        def _fake_predictions(_hits, ts_iso):
            event_type = "recognition" if "T00:00:00" in ts_iso else "promotion"
            return [
                {
                    "date": ts_iso,
                    "event_type": event_type,
                    "life_area": "honors",
                    "label": "Saturn Square Sun",
                    "description": "Saturn Square Sun",
                    "score": 18.0 if event_type == "recognition" else 12.0,
                    "probability": 0.72 if event_type == "recognition" else 0.45,
                    "tags": ["public_recognition"],
                    "factors": {
                        "transit": "Saturn Square Sun",
                        "determination_strength": 11.0 if event_type == "recognition" else 5.0,
                        "significance": 21.0 if event_type == "recognition" else 9.0,
                    },
                }
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            astro_clock_api,
            "_validate_stream_scan_bounds",
            return_value=(2, None),
        ), mock.patch.object(
            transits_morin,
            "_prepare_natal_context",
            return_value="CTX",
        ), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=lambda _n, hits, _ts, **_k: hits,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            side_effect=_fake_predictions,
        ):
            response = client.get(
                "/api/astro-clock/transits/window/stream"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T01:00:00Z"
                "&step_minutes=60"
            )

        payloads = [json.loads(chunk[6:]) for chunk in response.get_data(as_text=True).split("\n\n") if chunk.startswith("data: ")]
        done = payloads[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["peaks"][0]["event_type"], "recognition")
        first_row = done["series"][0]
        self.assertIn("raw_step_score", first_row)
        self.assertIn("localization_score", first_row)
        self.assertGreater(float(first_row["step_score"]), float(first_row["raw_step_score"]))

    def test_transits_stream_route_emits_progress_and_done_events(self):
        call_counter = {"count": 0}

        def _fake_compute(_natal_cd, ts_iso, **kwargs):
            call_counter["count"] += 1
            self.assertEqual(kwargs.get("_prepared_ctx"), "CTX")
            self.assertTrue(kwargs.get("natal_include_modern"))
            target = "Sun" if call_counter["count"] == 1 else "Moon"
            return [
                {
                    "transiting": "Saturn",
                    "natal": target,
                    "target_label": target,
                    "target_type": "planet",
                    "aspect": "Square",
                    "score": 5.0 + call_counter["count"],
                    "significance": 4.0 + call_counter["count"],
                    "phase": "applying",
                }
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            astro_clock_api,
            "_validate_stream_scan_bounds",
            return_value=(2, None),
        ), mock.patch.object(
            transits_morin,
            "_prepare_natal_context",
            return_value="CTX",
        ), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=lambda _n, hits, _ts, **_k: hits,
        ), mock.patch.object(
            astro_clock_api,
            "_predictions_from_hits",
            return_value=[{"event_type": "recognition", "score": 7.7, "probability": 0.77}],
        ):
            response = client.get(
                "/api/astro-clock/transits/window/stream"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T00:00:00Z"
                "&end=2026-03-08T01:00:00Z"
                "&step_minutes=60"
                "&include_natal_modern=1"
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("text/event-stream"))
        blocks = [chunk for chunk in response.get_data(as_text=True).split("\n\n") if chunk.startswith("data: ")]
        events = [json.loads(chunk[6:]) for chunk in blocks]
        self.assertEqual(events[0]["type"], "progress")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(len(events[-1]["series"]), 2)
        self.assertEqual(events[-1]["predictions"][0]["event_type"], "recognition")
        self.assertEqual(events[-1]["context_window"]["start"], "2026-03-08T00:00:00Z")

    def test_transits_export_csv_uses_single_transit_contract(self):
        def _fake_compute(_natal_cd, _ts, **_kwargs):
            return [
                {
                    "transiting": "Saturn",
                    "natal": "Sun",
                    "target_label": "Sun",
                    "aspect": "Square",
                    "orb": 0.5,
                    "max_orb": 6.0,
                    "phase": "applying",
                    "partile": True,
                    "complete_platic": False,
                    "score": 7.5,
                    "quality": "malefic",
                    "determination_strength": 4.0,
                },
                {
                    "transiting": "Jupiter",
                    "natal": "Moon",
                    "target_label": "Moon",
                    "aspect": "Trine",
                    "orb": 0.4,
                    "max_orb": 6.0,
                    "phase": "applying",
                    "partile": True,
                    "complete_platic": True,
                    "score": 8.1,
                    "quality": "benefic",
                    "determination_strength": 5.0,
                },
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "compute_morin_transits_to_natal",
            side_effect=_fake_compute,
        ), mock.patch.object(
            transits_morin,
            "enrich_hits_with_concordance",
            side_effect=lambda _n, hits, _ts, **_k: hits,
        ):
            response = client.get(
                "/api/astro-clock/transits/export"
                "?natal_snap_id=snap-1"
                "&transit_datetime=2026-03-08T12:00:00Z"
                "&transiting=Saturn"
                "&aspect=Square"
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment; filename=\"transits.csv\"", response.headers["Content-Disposition"])
        body = response.get_data(as_text=True)
        self.assertIn("Timestamp,Transiting,Natal,Aspect,Orb,MaxOrb,Phase,Partile,CompletePlatic,Score,Quality,DeterminationStrength", body)
        self.assertIn("2026-03-08T12:00:00Z,Saturn,Sun,Square,0.5,6.0,applying,1,0,7.5,malefic,4.0", body)
        self.assertNotIn(",Jupiter,Moon,Trine,", body)

    def test_transits_window_export_csv_uses_window_contract(self):
        def _fake_scan(_natal_cd, _start, _end, **_kwargs):
            return [
                {
                    "timestamp": "2026-03-08T09:00:00+00:00",
                    "count": 1,
                    "top": [
                        {
                            "transiting": "Saturn",
                            "natal": "Sun",
                            "target_label": "Sun",
                            "aspect": "Square",
                            "orb": 0.5,
                            "score": 7.5,
                            "quality": "malefic",
                            "determination_strength": 4.0,
                        }
                    ],
                }
            ]

        app = _make_app()
        client = app.test_client()

        with mock.patch.object(astro_clock_api, "_natal_from_query", return_value=_natal_stub()), mock.patch.object(
            transits_morin,
            "scan_morin_transits_window",
            side_effect=_fake_scan,
        ):
            response = client.get(
                "/api/astro-clock/transits/window/export"
                "?natal_snap_id=snap-1"
                "&start=2026-03-08T09:00:00Z"
                "&end=2026-03-08T12:00:00Z"
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment; filename=\"transits_window.csv\"", response.headers["Content-Disposition"])
        body = response.get_data(as_text=True)
        self.assertIn("Timestamp,TopCount,Transiting,Natal,Aspect,Orb,Score,Quality,DeterminationStrength", body)
        self.assertIn("2026-03-08T09:00:00+00:00,1,Saturn,Sun,Square,0.5,7.5,malefic,4.0", body)
