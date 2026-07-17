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
    / "transit_public_crisis_replay_slice_5.json"
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


def _describe_hit(hit):
    target = hit.get("target_label") or hit.get("natal")
    return f"{hit.get('transiting')} {hit.get('aspect')} {target}"


def _measure_crisis_support(payload):
    data = payload.get("data") or {}
    hits = data.get("transits") or []
    interesting = []
    best_strength = 0.0
    for row in hits[:40]:
        keywords = sorted(set(row.get("enriched_keywords") or []) & {
            "accident_major",
            "attack_violence",
            "conflict",
            "warfare_involvement",
            "war_declaration_offensive",
            "war_response_defensive",
            "internal_conflict_war",
            "death_violent",
            "death_threat_high",
            "death_threat_moderate",
        })
        if not keywords:
            continue
        significance = float(row.get("significance") or 0.0)
        best_strength = max(best_strength, significance)
        interesting.append(
            {
                "description": _describe_hit(row),
                "keywords": keywords,
                "significance": significance,
                "score": row.get("score"),
            }
        )
    return {
        "data": data,
        "top_hits": hits[:20],
        "best_strength": best_strength,
        "interesting_hits": interesting,
    }


class TransitPublicCrisisReplaySliceFiveTests(TestCase):
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
        return _measure_crisis_support(payload), natal_meta

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "george_w_bush_iraq_address",
                "shinzo_abe_assassination",
            ],
        )

    def test_fixture_tracks_sources_and_time_basis(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["resolved_location"])
                self.assertIsInstance(case["latitude"], float)
                self.assertIsInstance(case["longitude"], float)
                self.assertTrue(case["sources"]["natal"])
                self.assertTrue(case["sources"]["event"])
                self.assertTrue(case["time_basis"])
                self.assertTrue(case["time_confidence"])

    def test_event_date_beats_nearby_control_on_public_crisis_support(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                event = self._run_case(case, case["event_datetime"])
                control = self._run_case(case, case["control_datetime"])
                event_data, natal_meta = event
                control_data, _ = control

                self.assertEqual((event_data["data"].get("natal") or {}).get("location"), natal_meta.get("location"))
                self.assertEqual((event_data["data"].get("natal") or {}).get("timezone"), natal_meta.get("timezone"))
                self.assertEqual((event_data["data"].get("natal") or {}).get("house_system_code"), case["house_system_code"])

                matching_hit = next(
                    (
                        row
                        for row in event_data["interesting_hits"]
                        if row.get("description") in set(case["expected_crisis_hit_descriptions"])
                        and set(case["expected_crisis_keywords"]).issubset(set(row.get("keywords") or []))
                    ),
                    None,
                )
                self.assertIsNotNone(
                    matching_hit,
                    msg=f"{case['id']} event_hits={event_data['interesting_hits']}",
                )

                self.assertGreaterEqual(
                    event_data["best_strength"],
                    control_data["best_strength"] + float(case["minimum_hit_delta"]),
                    msg=(
                        f"{case['id']} event_best={event_data['best_strength']} "
                        f"control_best={control_data['best_strength']} "
                        f"event_hits={event_data['interesting_hits']} "
                        f"control_hits={control_data['interesting_hits']}"
                    ),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
