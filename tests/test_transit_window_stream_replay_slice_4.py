from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
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
    / "transit_window_stream_replay_slice_4.json"
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


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _window_for(case):
    event_dt = _parse_iso(case["event_datetime"])
    half_window = timedelta(hours=float(case.get("window_hours") or 24))
    return (
        (event_dt - half_window).isoformat(),
        (event_dt + half_window).isoformat(),
    )


def _event_score_rank(series, event_ts: str) -> int | None:
    ordered = sorted(
        series,
        key=lambda row: (
            float(row.get("step_score") or 0.0),
            int(row.get("count") or 0),
        ),
        reverse=True,
    )
    for index, row in enumerate(ordered, start=1):
        if row.get("timestamp") == event_ts:
            return index
    return None


def _nearest_peak_distance_hours(peaks, event_ts: str) -> float | None:
    event_dt = _parse_iso(event_ts)
    distances = []
    for peak in peaks:
        peak_ts = peak.get("timestamp") if isinstance(peak, dict) else peak
        if not peak_ts:
            continue
        distances.append(abs((_parse_iso(peak_ts) - event_dt).total_seconds()) / 3600.0)
    return min(distances) if distances else None


def _prediction_label(row):
    return str(row.get("label") or row.get("description") or "")


def _parse_sse_events(body: str):
    blocks = [chunk for chunk in body.split("\n\n") if chunk.startswith("data: ")]
    return [json.loads(chunk[6:]) for chunk in blocks]


class TransitWindowStreamReplaySliceFourTests(TestCase):
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

    def _run_case(self, case):
        bundle = self.natal_bundles[case["id"]]
        natal_chart = bundle.get("chart_data") or {}
        natal_meta = {
            **(bundle.get("meta") or {}),
            "house_system_code": case["house_system_code"],
        }
        start, end = _window_for(case)
        with mock.patch.object(
            astro_clock_api,
            "_natal_from_query",
            return_value=(natal_chart, natal_meta),
        ):
            response = self.client.get(
                "/api/astro-clock/transits/window/stream",
                query_string={
                    "natal_snap_id": case["id"],
                    "house_system_code": case["house_system_code"],
                    "start": start,
                    "end": end,
                    "step_minutes": 60,
                    "include_modern": "1",
                    "include_natal_modern": "1",
                    "include_cusps": "1",
                    "include_antiscia": "1",
                    "include_lots": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("text/event-stream"))
        return _parse_sse_events(response.get_data(as_text=True)), natal_meta

    def test_replay_slice_has_expected_cases(self):
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "donald_trump_inauguration",
                "sergio_mattarella_president",
                "al_gore_nobel_peace_announcement",
            ],
        )

    def test_fixture_tracks_sources_and_time_basis(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["resolved_location"])
                self.assertIsInstance(case["latitude"], float)
                self.assertIsInstance(case["longitude"], float)
                self.assertTrue(case["sources"]["natal"])
                if case["id"] == "al_gore_nobel_peace_announcement":
                    self.assertEqual(case["time_basis"], "official_norwegian_nobel_committee_announcement_slot")
                    self.assertEqual(case["time_confidence"], "medium")
                    self.assertTrue(case["sources"]["time_basis"])

    def test_stream_done_payload_keeps_exact_event_row_localized(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                events, natal_meta = self._run_case(case)
                self.assertTrue(events)
                self.assertEqual(events[0].get("type"), "progress")
                self.assertEqual(events[-1].get("type"), "done")
                self.assertGreaterEqual(
                    sum(1 for event in events if event.get("type") == "progress"),
                    1,
                )

                done = events[-1]
                self.assertEqual((done.get("natal") or {}).get("location"), natal_meta.get("location"))
                self.assertEqual((done.get("natal") or {}).get("timezone"), natal_meta.get("timezone"))
                self.assertEqual((done.get("natal") or {}).get("house_system_code"), case["house_system_code"])

                series = done.get("series") or []
                self.assertTrue(series)
                event_row = next((row for row in series if row.get("timestamp") == case["event_datetime"]), None)
                self.assertIsNotNone(event_row)

                matching_descriptions = [
                    _prediction_label(row)
                    for row in (event_row.get("predictions") or [])
                    if _prediction_label(row) in set(case["expected_exact_event_descriptions"])
                ]
                self.assertTrue(
                    matching_descriptions,
                    msg=(
                        f"{case['id']} event_row_predictions="
                        f"{[{k: row.get(k) for k in ('description', 'event_type', 'life_area', 'score')} for row in (event_row.get('predictions') or [])[:12]]}"
                    ),
                )

                score_rank = _event_score_rank(series, case["event_datetime"])
                self.assertIsNotNone(score_rank)
                self.assertLessEqual(
                    score_rank,
                    int(case["max_step_score_rank"]),
                    msg=(
                        f"{case['id']} score_rank={score_rank} "
                        f"top_scores={[(row.get('timestamp'), row.get('step_score'), row.get('count')) for row in sorted(series, key=lambda r: (float(r.get('step_score') or 0.0), int(r.get('count') or 0)), reverse=True)[:10]]}"
                    ),
                )

                nearest_peak_distance = _nearest_peak_distance_hours(done.get("peaks") or [], case["event_datetime"])
                self.assertIsNotNone(nearest_peak_distance)
                self.assertLessEqual(
                    nearest_peak_distance,
                    float(case["max_peak_distance_hours"]),
                    msg=(
                        f"{case['id']} nearest_peak_distance={nearest_peak_distance} "
                        f"peaks={[(peak.get('timestamp'), peak.get('count'), peak.get('step_score')) for peak in (done.get('peaks') or [])[:10]]}"
                    ),
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
