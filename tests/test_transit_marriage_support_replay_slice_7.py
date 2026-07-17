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
    / "transit_marriage_support_replay_slice_7.json"
)

MARRIAGE_KEYWORDS = {
    "engagement",
    "family_celebration",
    "marriage",
    "partnership_strengthened",
    "wedding",
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


def _measure_marriage_support(payload):
    data = payload.get("data") or {}
    predictions = data.get("predictions") or []
    hits = data.get("transits") or []

    prediction_rows = []
    for row in predictions[:12]:
        if row.get("event_type") == "marriage" or row.get("life_area") == "marriage":
            prediction_rows.append(
                {
                    "label": _prediction_label(row),
                    "description": row.get("description"),
                    "event_type": row.get("event_type"),
                    "life_area": row.get("life_area"),
                    "score": float(row.get("score") or 0.0),
                }
            )

    support_rows = []
    best_support = 0.0
    for row in hits[:40]:
        overlap = sorted(set(row.get("enriched_keywords") or []) & MARRIAGE_KEYWORDS)
        if not overlap:
            continue
        significance = float(row.get("significance") or 0.0)
        best_support = max(best_support, significance)
        support_rows.append(
            {
                "description": _describe_hit(row),
                "keywords": overlap,
                "significance": significance,
                "score": row.get("score"),
            }
        )

    return {
        "data": data,
        "prediction_rows": prediction_rows,
        "support_rows": support_rows,
        "best_support": best_support,
    }


class TransitMarriageSupportReplaySliceSevenTests(TestCase):
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
        return _measure_marriage_support(payload), natal_meta

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "charles_diana_wedding",
                "prince_harry_wedding",
            ],
        )

    def test_fixture_tracks_sources_and_time_basis(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["resolved_location"])
                self.assertIsInstance(case["latitude"], float)
                self.assertIsInstance(case["longitude"], float)
                self.assertTrue(case["sources"]["natal"])
                self.assertTrue(case["sources"]["event_time_basis"])
                self.assertTrue(case["sources"]["event_day_context"])
                self.assertTrue(case["time_basis"])
                self.assertTrue(case["time_confidence"])

    def test_event_date_beats_control_on_bounded_marriage_support(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                event, natal_meta = self._run_case(case, case["event_datetime"])
                control, _ = self._run_case(case, case["control_datetime"])

                self.assertEqual((event["data"].get("natal") or {}).get("location"), natal_meta.get("location"))
                self.assertEqual((event["data"].get("natal") or {}).get("timezone"), natal_meta.get("timezone"))
                self.assertEqual((event["data"].get("natal") or {}).get("house_system_code"), case["house_system_code"])

                if case["measurement_mode"] == "prediction_cluster":
                    matching_predictions = [
                        row
                        for row in event["prediction_rows"]
                        if row.get("label") in set(case["expected_prediction_descriptions"])
                    ]
                    self.assertGreaterEqual(
                        len(matching_predictions),
                        int(case["minimum_prediction_match_count"]),
                        msg=f"{case['id']} event_predictions={event['prediction_rows']}",
                    )
                    self.assertGreaterEqual(
                        len(event["prediction_rows"]),
                        len(control["prediction_rows"]) + int(case["minimum_prediction_count_delta"]),
                        msg=(
                            f"{case['id']} event_predictions={event['prediction_rows']} "
                            f"control_predictions={control['prediction_rows']}"
                        ),
                    )
                elif case["measurement_mode"] == "support_hit_delta":
                    matching_support = next(
                        (
                            row
                            for row in event["support_rows"]
                            if row.get("description") in set(case["expected_support_descriptions"])
                            and set(case["expected_support_keywords"]).issubset(set(row.get("keywords") or []))
                        ),
                        None,
                    )
                    self.assertIsNotNone(
                        matching_support,
                        msg=f"{case['id']} event_support={event['support_rows']}",
                    )
                    event_support_strength = max(
                        (
                            float(row.get("significance") or 0.0)
                            for row in event["support_rows"]
                            if set(case["expected_support_keywords"]).issubset(set(row.get("keywords") or []))
                        ),
                        default=0.0,
                    )
                    control_support_strength = max(
                        (
                            float(row.get("significance") or 0.0)
                            for row in control["support_rows"]
                            if set(case["expected_support_keywords"]).issubset(set(row.get("keywords") or []))
                        ),
                        default=0.0,
                    )
                    self.assertGreaterEqual(
                        event_support_strength,
                        control_support_strength + float(case["minimum_support_delta"]),
                        msg=(
                            f"{case['id']} event_support_strength={event_support_strength} "
                            f"control_support_strength={control_support_strength} "
                            f"event_support={event['support_rows']} "
                            f"control_support={control['support_rows']}"
                        ),
                    )
                else:
                    self.fail(f"Unknown measurement_mode={case['measurement_mode']!r}")


if __name__ == "__main__":
    import unittest

    unittest.main()
