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
    / "transit_pre_event_control_replay_slice_8.json"
)


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


def _prediction_label(row):
    return str(row.get("label") or row.get("description") or "")


def _describe_hit(hit):
    target = hit.get("target_label") or hit.get("natal")
    return f"{hit.get('transiting')} {hit.get('aspect')} {target}"


def _measure_case(payload, case):
    data = payload.get("data") or {}
    predictions = data.get("predictions") or []
    hits = data.get("transits") or []
    mode = case["measurement_mode"]

    if mode in {"honor_prediction_and_context", "honor_prediction_only"}:
        prediction_rows = [
            {
                "label": _prediction_label(row),
                "description": row.get("description"),
                "event_type": row.get("event_type"),
                "life_area": row.get("life_area"),
                "score": float(row.get("score") or 0.0),
            }
            for row in predictions[:12]
            if row.get("event_type") in set(case["expected_event_types"])
            and _prediction_label(row) in set(case["expected_prediction_descriptions"])
        ]
        context_rows = [
            {
                "description": _describe_hit(row),
                "keywords": sorted(set(row.get("enriched_keywords") or [])),
                "significance": float(row.get("significance") or 0.0),
            }
            for row in hits[:30]
            if _describe_hit(row) in set(case["expected_context_descriptions"])
            and set(case["expected_context_keywords"]).issubset(set(row.get("enriched_keywords") or []))
        ]
        return {
            "data": data,
            "prediction_strength": max((row["score"] for row in prediction_rows), default=0.0),
            "prediction_rows": prediction_rows,
            "hit_strength": max((row["significance"] for row in context_rows), default=0.0),
            "context_rows": context_rows,
        }

    if mode == "crisis_hit":
        crisis_rows = [
            {
                "description": _describe_hit(row),
                "keywords": sorted(set(row.get("enriched_keywords") or [])),
                "significance": float(row.get("significance") or 0.0),
            }
            for row in hits[:40]
            if _describe_hit(row) in set(case["expected_crisis_hit_descriptions"])
            and set(case["expected_crisis_keywords"]).issubset(set(row.get("enriched_keywords") or []))
        ]
        return {
            "data": data,
            "hit_strength": max((row["significance"] for row in crisis_rows), default=0.0),
            "crisis_rows": crisis_rows,
        }

    if mode == "marriage_cluster_score":
        matching_rows = [
            {
                "label": _prediction_label(row),
                "description": row.get("description"),
                "event_type": row.get("event_type"),
                "life_area": row.get("life_area"),
                "score": float(row.get("score") or 0.0),
            }
            for row in predictions[:20]
            if _prediction_label(row) in set(case["expected_prediction_descriptions"])
        ]
        return {
            "data": data,
            "match_count": len(matching_rows),
            "match_score_sum": sum(row["score"] for row in matching_rows),
            "matching_rows": matching_rows,
        }

    raise AssertionError(f"Unsupported measurement_mode: {mode}")


class TransitPreEventControlReplaySliceEightTests(TestCase):
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
        return _measure_case(payload, case)

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "obama_nobel_peace_announcement",
                "al_gore_nobel_peace_announcement",
                "george_w_bush_iraq_address",
                "charles_diana_wedding",
            ],
        )

    def test_fixture_tracks_sources_and_controls(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["resolved_location"])
                self.assertIsInstance(case["latitude"], float)
                self.assertIsInstance(case["longitude"], float)
                self.assertTrue(case["sources"]["natal"])
                self.assertEqual(len(case["control_datetimes"]), 2)
                self.assertTrue(case["time_basis"])
                self.assertTrue(case["time_confidence"])

    def test_event_date_beats_multiple_pre_event_controls_on_primary_measure(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                event = self._run_case(case, case["event_datetime"])

                mode = case["measurement_mode"]
                if mode in {"honor_prediction_and_context", "honor_prediction_only"}:
                    self.assertTrue(
                        event["prediction_rows"],
                        msg=f"{case['id']} event_predictions={event['prediction_rows']}",
                    )
                    self.assertTrue(
                        event["context_rows"],
                        msg=f"{case['id']} event_context={event['context_rows']}",
                    )
                elif mode == "crisis_hit":
                    self.assertTrue(
                        event["crisis_rows"],
                        msg=f"{case['id']} event_crisis_rows={event['crisis_rows']}",
                    )
                elif mode == "marriage_cluster_score":
                    self.assertGreaterEqual(
                        event["match_count"],
                        int(case["minimum_match_count"]),
                        msg=f"{case['id']} event_matches={event['matching_rows']}",
                    )

                for control_datetime in case["control_datetimes"]:
                    control = self._run_case(case, control_datetime)
                    with self.subTest(case=case["id"], control=control_datetime):
                        if mode == "honor_prediction_and_context":
                            self.assertGreaterEqual(
                                event["prediction_strength"],
                                control["prediction_strength"] + float(case["minimum_prediction_delta"]),
                                msg=(
                                    f"{case['id']} prediction_strength event={event['prediction_strength']} "
                                    f"control={control['prediction_strength']} "
                                    f"event_predictions={event['prediction_rows']} "
                                    f"control_predictions={control['prediction_rows']}"
                                ),
                            )
                            self.assertGreaterEqual(
                                event["hit_strength"],
                                control["hit_strength"] + float(case["minimum_hit_delta"]),
                                msg=(
                                    f"{case['id']} hit_strength event={event['hit_strength']} "
                                    f"control={control['hit_strength']} "
                                    f"event_context={event['context_rows']} "
                                    f"control_context={control['context_rows']}"
                                ),
                            )
                        elif mode == "honor_prediction_only":
                            self.assertGreaterEqual(
                                event["prediction_strength"],
                                control["prediction_strength"] + float(case["minimum_prediction_delta"]),
                                msg=(
                                    f"{case['id']} prediction_strength event={event['prediction_strength']} "
                                    f"control={control['prediction_strength']} "
                                    f"event_predictions={event['prediction_rows']} "
                                    f"control_predictions={control['prediction_rows']}"
                                ),
                            )
                        elif mode == "crisis_hit":
                            self.assertGreaterEqual(
                                event["hit_strength"],
                                control["hit_strength"] + float(case["minimum_hit_delta"]),
                                msg=(
                                    f"{case['id']} hit_strength event={event['hit_strength']} "
                                    f"control={control['hit_strength']} "
                                    f"event_crisis={event['crisis_rows']} "
                                    f"control_crisis={control['crisis_rows']}"
                                ),
                            )
                        elif mode == "marriage_cluster_score":
                            self.assertGreaterEqual(
                                event["match_score_sum"],
                                control["match_score_sum"] + float(case["minimum_match_score_delta"]),
                                msg=(
                                    f"{case['id']} match_score_sum event={event['match_score_sum']} "
                                    f"control={control['match_score_sum']} "
                                    f"event_matches={event['matching_rows']} "
                                    f"control_matches={control['matching_rows']}"
                                ),
                            )


if __name__ == "__main__":
    import unittest

    unittest.main()
