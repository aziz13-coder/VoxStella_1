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
    / "transit_war_response_replay_slice_9.json"
)


WAR_KEYWORDS = {
    "attack_violence",
    "conflict",
    "warfare_involvement",
    "war_declaration_offensive",
    "war_response_defensive",
    "internal_conflict_war",
}


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
        )


def _describe_hit(hit):
    target = hit.get("target_label") or hit.get("natal")
    return f"{hit.get('transiting')} {hit.get('aspect')} {target}"


def _measure_war_response(payload):
    data = payload.get("data") or {}
    hits = data.get("transits") or []
    war_rows = []
    for row in hits[:60]:
        keywords = sorted(set(row.get("enriched_keywords") or []) & WAR_KEYWORDS)
        if not keywords:
            continue
        war_rows.append(
            {
                "description": _describe_hit(row),
                "event_type": ((row.get("prediction") or {}).get("eventType")),
                "life_area": ((row.get("prediction") or {}).get("lifeArea")),
                "keywords": keywords,
                "significance": float(row.get("significance") or 0.0),
                "score": float(row.get("score") or 0.0),
            }
        )
    return {
        "data": data,
        "war_rows": war_rows,
        "war_hit_count": len(war_rows),
        "war_significance_sum": sum(row["significance"] for row in war_rows),
    }


class TransitWarResponseReplaySliceNineTests(TestCase):
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
        return _measure_war_response(payload)

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            ["george_w_bush_iraq_address"],
        )

    def test_fixture_tracks_sources_and_controls(self):
        case = self.cases[0]
        self.assertTrue(case["resolved_location"])
        self.assertIsInstance(case["latitude"], float)
        self.assertIsInstance(case["longitude"], float)
        self.assertTrue(case["sources"]["natal"])
        self.assertTrue(case["sources"]["event"])
        self.assertEqual(len(case["control_datetimes"]), 2)
        self.assertEqual(case["time_confidence"], "high")

    def test_event_date_keeps_denser_war_response_cluster_than_prior_controls(self):
        case = self.cases[0]
        event = self._run_case(case, case["event_datetime"])

        self.assertGreaterEqual(
            event["war_hit_count"],
            int(case["minimum_hit_count"]),
            msg=f"event_war_rows={event['war_rows']}",
        )

        for description in case["expected_war_hit_descriptions"]:
            self.assertTrue(
                any(
                    row["description"] == description
                    and set(case["expected_war_keywords"]).issubset(set(row["keywords"]))
                    for row in event["war_rows"]
                ),
                msg=f"missing {description} in event_war_rows={event['war_rows']}",
            )

        self.assertTrue(
            any(
                row["event_type"] in {
                    "attack_violence",
                    "war_declaration_offensive",
                    "war_response_defensive",
                    "internal_conflict_war",
                    "warfare_involvement",
                    "enemy_attack",
                }
                for row in event["war_rows"]
            ),
            msg=f"missing war-specific event type in event_war_rows={event['war_rows']}",
        )
        self.assertTrue(
            any(row["life_area"] == "conflict" for row in event["war_rows"]),
            msg=f"missing conflict life area in event_war_rows={event['war_rows']}",
        )
        self.assertFalse(
            any("marriage" in row["keywords"] for row in event["war_rows"]),
            msg=f"unexpected marriage keyword in event_war_rows={event['war_rows']}",
        )

        for control_datetime in case["control_datetimes"]:
            with self.subTest(control=control_datetime):
                control = self._run_case(case, control_datetime)
                self.assertGreaterEqual(
                    event["war_significance_sum"],
                    control["war_significance_sum"] + float(case["minimum_significance_sum_delta"]),
                    msg=(
                        f"event_war_sum={event['war_significance_sum']} "
                        f"control_war_sum={control['war_significance_sum']} "
                        f"event_war_rows={event['war_rows']} "
                        f"control_war_rows={control['war_rows']}"
                    ),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
