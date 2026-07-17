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
    / "transit_public_authority_replay_slice_1.json"
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


class TransitPublicAuthorityReplaySliceOneTests(TestCase):
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

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "donald_trump_inauguration",
                "kamala_harris_inauguration",
                "sergio_mattarella_president",
            ],
        )

    def test_fixture_tracks_coordinates_and_sources(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["resolved_location"])
                self.assertIsInstance(case["latitude"], float)
                self.assertIsInstance(case["longitude"], float)
                self.assertTrue(case["sources"]["natal"])
                self.assertTrue(case["sources"]["event"])

    def test_public_authority_cases_align_against_live_transit_route(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
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
                            "transit_datetime": case["transit_datetime"],
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
                data = payload.get("data") or {}

                self.assertEqual((data.get("natal") or {}).get("location"), natal_meta.get("location"))
                self.assertEqual((data.get("natal") or {}).get("timezone"), natal_meta.get("timezone"))
                self.assertEqual((data.get("natal") or {}).get("house_system_code"), case["house_system_code"])

                predictions = data.get("predictions") or []
                top_predictions = predictions[:12]
                matching_prediction = next(
                    (
                        row
                        for row in top_predictions
                        if row.get("event_type") == case["expected_prediction_event_type"]
                        and row.get("life_area") == case["expected_prediction_life_area"]
                        and _prediction_label(row) in case["expected_prediction_descriptions"]
                    ),
                    None,
                )
                self.assertIsNotNone(
                    matching_prediction,
                    msg=(
                        f"{case['id']} top_predictions="
                        f"{[{k: row.get(k) for k in ('description', 'event_type', 'life_area', 'score')} for row in top_predictions]}"
                    ),
                )

                top_hits = data.get("transits") or []
                matching_public_hit = next(
                    (
                        row
                        for row in top_hits[:40]
                        if _describe_hit(row) in case["expected_public_hit_descriptions"]
                        and set(case["expected_public_hit_keywords"]).issubset(set(row.get("enriched_keywords") or []))
                    ),
                    None,
                )
                self.assertIsNotNone(
                    matching_public_hit,
                    msg=(
                        f"{case['id']} top_hits="
                        f"{[{ 'descriptor': _describe_hit(row), 'keywords': row.get('enriched_keywords'), 'score': row.get('score'), 'significance': row.get('significance') } for row in top_hits[:20]]}"
                    ),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
