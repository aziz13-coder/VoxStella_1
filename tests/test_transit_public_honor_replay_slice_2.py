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
import backend.astro_clock_engine as astro_clock_engine
import backend.horary_engine.engine as horary_engine_engine
import backend.horary_engine.services.geolocation as horary_geolocation


REPLAY_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "transit_public_honor_replay_slice_2.json"
)

INTERESTING_EVENT_TYPES = {
    "promotion",
    "opportunity_received",
    "public_recognition",
    "recognition",
}

INTERESTING_HIT_KEYWORDS = {
    "career",
    "public_recognition",
    "promotion",
    "honor_award",
    "new_job",
    "opportunity_received",
    "recognition",
    "achievement",
    "structure_established",
    "authority_earned",
}


def _prediction_label(row):
    return str(row.get("label") or row.get("description") or "")


def _load_replay_cases():
    return json.loads(REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))


def _make_replay_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def _case_map(cases):
    return {str(case["natal_location"]).strip().lower(): case for case in cases}


def _fake_geocode_factory(cases):
    mapped = _case_map(cases)

    def _fake_geocode(location_string: str, timeout: int = 10):
        del timeout
        key = str(location_string or "").strip().lower()
        case = mapped.get(key)
        if not case:
            raise horary_geolocation.LocationError(f"Unexpected test location: {location_string}")
        return (
            float(case["latitude"]),
            float(case["longitude"]),
            str(case["resolved_location"]),
        )

    return _fake_geocode


def _build_natal_bundle(case, fake_geocode):
    with mock.patch.object(astro_clock_api, "safe_geocode", side_effect=fake_geocode), mock.patch.object(
        astro_clock_engine,
        "safe_geocode",
        side_effect=fake_geocode,
    ), mock.patch.object(
        horary_engine_engine,
        "safe_geocode",
        side_effect=fake_geocode,
    ), mock.patch.object(
        horary_geolocation,
        "safe_geocode",
        side_effect=fake_geocode,
    ):
        return astro_clock_api._compute_chart_bundle_for(
            case["natal_datetime"],
            case["natal_location"],
            case["natal_timezone"],
            house_system_code=case["house_system_code"],
            latitude=float(case["latitude"]),
            longitude=float(case["longitude"]),
        )


def _describe_hit(hit):
    target = hit.get("target_label") or hit.get("natal")
    return f"{hit.get('transiting')} {hit.get('aspect')} {target}"


def _measure_slice_signal(payload):
    data = payload.get("data") or {}
    predictions = data.get("predictions") or []
    hits = data.get("transits") or []
    top_predictions = predictions[:12]
    top_hits = hits[:30]

    prediction_strength = 0.0
    prediction_rows = []
    for row in top_predictions:
        if row.get("event_type") in INTERESTING_EVENT_TYPES:
            score = float(row.get("score") or 0.0)
            prediction_strength = max(prediction_strength, score)
            prediction_rows.append(
                {
                    "label": _prediction_label(row),
                    "description": row.get("description"),
                    "event_type": row.get("event_type"),
                    "life_area": row.get("life_area"),
                    "score": score,
                }
            )

    hit_strength = 0.0
    hit_rows = []
    for row in top_hits:
        overlap = sorted(set(row.get("enriched_keywords") or []) & INTERESTING_HIT_KEYWORDS)
        if not overlap:
            continue
        significance = float(row.get("significance") or 0.0)
        hit_strength = max(hit_strength, significance)
        hit_rows.append(
            {
                "description": _describe_hit(row),
                "keywords": overlap,
                "significance": significance,
                "score": row.get("score"),
            }
        )

    return {
        "data": data,
        "top_predictions": top_predictions,
        "top_hits": top_hits,
        "prediction_strength": prediction_strength,
        "prediction_rows": prediction_rows,
        "hit_strength": hit_strength,
        "hit_rows": hit_rows,
    }


class TransitPublicHonorReplaySliceTwoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _load_replay_cases()
        cls.app = _make_replay_app()
        cls.client = cls.app.test_client()
        fake_geocode = _fake_geocode_factory(cls.cases)
        cls.natal_bundles = {
            case["id"]: _build_natal_bundle(case, fake_geocode)
            for case in cls.cases
        }

    def _run_case(self, case, transit_datetime):
        bundle = self.natal_bundles[case["id"]]
        natal_chart = bundle.get("chart_data") or {}
        natal_meta = {
            **(bundle.get("meta") or {}),
            "house_system_code": case["house_system_code"],
        }
        with mock.patch.object(
            astro_clock_api,
            "_natal_from_query",
            return_value=(natal_chart, natal_meta),
        ):
            response = self.client.get(
                "/api/astro-clock/transits",
                query_string={
                    "natal_snap_id": case["id"],
                    "house_system_code": case["house_system_code"],
                    "transit_datetime": transit_datetime,
                    "include_modern": "1",
                    "include_natal_modern": "1",
                    "include_cusps": "1",
                    "include_antiscia": "1",
                    "include_lots": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json() or {}
        self.assertTrue(payload.get("success"))
        return _measure_slice_signal(payload)

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "obama_nobel_peace_announcement",
                "al_gore_nobel_peace_announcement",
            ],
        )

    def test_metadata_basis_and_sources_are_tracked(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["time_basis"], "official_norwegian_nobel_committee_announcement_slot")
                self.assertEqual(case["time_confidence"], "medium")
                self.assertTrue(case["sources"]["natal"])
                self.assertTrue(case["sources"]["event_announcement"])
                self.assertTrue(case["sources"]["time_basis"])

    def test_event_date_beats_nearby_control_on_public_honor_signal(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                event = self._run_case(case, case["event_datetime"])
                control = self._run_case(case, case["control_datetime"])

                matching_prediction = next(
                    (
                        row
                        for row in event["prediction_rows"]
                        if row.get("event_type") in set(case["expected_event_types"])
                        and row.get("label") in set(case["expected_prediction_descriptions"])
                    ),
                    None,
                )
                self.assertIsNotNone(
                    matching_prediction,
                    msg=f"{case['id']} event_predictions={event['prediction_rows']}",
                )

                matching_context_hit = next(
                    (
                        row
                        for row in event["hit_rows"]
                        if row.get("description") in set(case["expected_context_descriptions"])
                        and set(case["expected_context_keywords"]).issubset(set(row.get("keywords") or []))
                    ),
                    None,
                )
                self.assertIsNotNone(
                    matching_context_hit,
                    msg=f"{case['id']} event_hits={event['hit_rows'][:12]}",
                )

                self.assertGreaterEqual(
                    event["prediction_strength"],
                    control["prediction_strength"] + float(case["minimum_prediction_delta"]),
                    msg=(
                        f"{case['id']} prediction_strength event={event['prediction_strength']} "
                        f"control={control['prediction_strength']} "
                        f"event_predictions={event['prediction_rows']} control_predictions={control['prediction_rows']}"
                    ),
                )
                self.assertGreaterEqual(
                    event["hit_strength"],
                    control["hit_strength"] + float(case["minimum_hit_delta"]),
                    msg=(
                        f"{case['id']} hit_strength event={event['hit_strength']} "
                        f"control={control['hit_strength']} "
                        f"event_hits={event['hit_rows']} control_hits={control['hit_rows']}"
                    ),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
