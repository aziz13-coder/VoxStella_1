from __future__ import annotations

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

import transits_workflow_benchmark_runner as runner


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def get_json(self):
        return self._payload


class _FakeClient:
    def __init__(self, routes):
        self._routes = routes

    def get(self, path, query_string=None):
        query = query_string or {}
        if path == "/api/astro-clock/transits":
            return _FakeResponse(
                {
                    "success": True,
                    "data": {
                        "transits": [
                            {"transiting": "Jupiter", "aspect": "Trine", "target_label": "MC"},
                            {"transiting": "Venus", "aspect": "Sextile", "target_label": "Moon"},
                        ],
                        "predictions": [
                            {"event_type": "public_recognition", "life_area": "honors", "label": "Jupiter Trine MC"}
                        ],
                    },
                }
            )
        if path == "/api/astro-clock/transits/window":
            return _FakeResponse(
                {
                    "success": True,
                    "data": {
                        "series": [
                            {
                                "timestamp": query["start"] if query["start"] == "1613-05-08T00:00:00+00:00" else "1615-07-07T12:00:00+00:00",
                                "top": [
                                    {"transiting": "Jupiter", "aspect": "Trine", "target_label": "MC"},
                                    {"transiting": "Mars", "aspect": "Opposition", "target_label": "Asc"},
                                ],
                                "predictions": [
                                    {"event_type": "public_recognition", "life_area": "honors", "label": "Jupiter Trine MC"},
                                    {"event_type": "accident_major", "life_area": "danger", "label": "Mars Opposition Asc"},
                                ],
                            },
                            {
                                "timestamp": "1613-05-09T12:00:00+00:00",
                                "top": [
                                    {"transiting": "Jupiter", "aspect": "Trine", "target_label": "MC"},
                                ],
                                "predictions": [
                                    {"event_type": "public_recognition", "life_area": "honors", "label": "Jupiter Trine MC"},
                                ],
                            },
                            {
                                "timestamp": "1615-07-07T12:00:00+00:00",
                                "top": [
                                    {"transiting": "Mars", "aspect": "Opposition", "target_label": "Asc"},
                                ],
                                "predictions": [
                                    {"event_type": "accident_major", "life_area": "danger", "label": "Mars Opposition Asc"},
                                ],
                            },
                        ]
                    },
                }
            )
        if path == "/api/astro-clock/predictor":
            step = int(query["step_minutes"])
            if query["start"].startswith("1613"):
                ts = "1613-05-10T00:00:00+00:00" if step == 180 else "1613-05-11T00:00:00+00:00"
                return _FakeResponse(
                    {
                        "success": True,
                        "data": {
                            "prediction_groups": [
                                {
                                    "event_type": "public_recognition",
                                    "life_area": "honors",
                                    "label": "Jupiter Trine MC",
                                    "dominant_timestamp": ts,
                                }
                            ]
                        },
                    }
                )
            ts = "1615-07-07T12:00:00+00:00" if step == 180 else "1615-07-08T00:00:00+00:00"
            return _FakeResponse(
                {
                    "success": True,
                    "data": {
                        "prediction_groups": [
                            {
                                "event_type": "accident_major",
                                "life_area": "danger",
                                "label": "Mars Opposition Asc",
                                "dominant_timestamp": ts,
                            }
                        ]
                    },
                }
            )
        raise AssertionError(f"Unexpected path {path}")


def test_run_exact_scan_consistency_case_passes_on_overlap():
    case = {
        "case_id": "exact_scan",
        "natal_datetime": "1583-02-23T05:45:00+00:00",
        "natal_location": "Villefranche, France",
        "natal_timezone": "Europe/Paris",
        "house_system_code": "R",
        "transit_datetime": "1613-05-09T12:00:00+00:00",
        "window_start": "1613-05-08T00:00:00+00:00",
        "window_end": "1613-05-10T00:00:00+00:00",
        "step_minutes": 180,
        "expected_transit_overlap_min": 1,
        "expected_prediction_overlap_min": 1,
    }
    result = runner.run_exact_scan_consistency_case(case, client=_FakeClient({}), quiet_engine=True)
    assert result["passed"] is True
    assert result["transit_overlap_count"] >= 1
    assert result["prediction_overlap_count"] >= 1


def test_run_predictor_stability_case_passes_with_bounded_gap():
    case = {
        "case_id": "predictor_stability",
        "natal_datetime": "1583-02-23T05:45:00+00:00",
        "natal_location": "Villefranche, France",
        "natal_timezone": "Europe/Paris",
        "house_system_code": "R",
        "window_start": "1613-05-01T00:00:00+00:00",
        "window_end": "1613-05-15T00:00:00+00:00",
        "step_minutes_primary": 180,
        "step_minutes_secondary": 60,
        "expected_life_area": "honors",
        "expected_event_type": "public_recognition",
        "max_rank": 3,
        "max_dominant_gap_hours": 48,
    }
    result = runner.run_predictor_stability_case(case, client=_FakeClient({}), quiet_engine=True)
    assert result["passed"] is True
    assert result["primary_rank"] == 1
    assert result["secondary_rank"] == 1


def test_run_documented_hindcast_case_passes_when_expected_family_hits_target_window():
    case = {
        "case_id": "hindcast",
        "natal_datetime": "1583-02-23T05:45:00+00:00",
        "natal_location": "Villefranche, France",
        "natal_timezone": "Europe/Paris",
        "house_system_code": "R",
        "window_start": "1615-07-01T00:00:00+00:00",
        "window_end": "1615-07-15T00:00:00+00:00",
        "step_minutes": 180,
        "target_window": {
            "start": "1615-07-07T00:00:00+00:00",
            "end": "1615-07-08T23:59:59+00:00",
        },
        "expected_life_areas": ["danger"],
        "expected_event_types": ["accident_major"],
        "max_rank": 3,
        "max_peak_distance_hours": 48,
    }
    result = runner.run_documented_hindcast_case(case, client=_FakeClient({}), quiet_engine=True)
    assert result["passed"] is True
    assert result["target_window_hit"] is True


def test_run_workflow_benchmarks_aggregates_sections(monkeypatch):
    monkeypatch.setattr(runner, "_build_test_client", lambda: _FakeClient({}))
    monkeypatch.setattr(
        runner,
        "load_exact_scan_consistency_cases",
        lambda **_: [
            {
                "case_id": "exact_scan",
                "natal_datetime": "1583-02-23T05:45:00+00:00",
                "natal_location": "Villefranche, France",
                "natal_timezone": "Europe/Paris",
                "house_system_code": "R",
                "transit_datetime": "1613-05-09T12:00:00+00:00",
                "window_start": "1613-05-08T00:00:00+00:00",
                "window_end": "1613-05-10T00:00:00+00:00",
                "step_minutes": 180,
                "expected_transit_overlap_min": 1,
                "expected_prediction_overlap_min": 1,
            }
        ],
    )
    monkeypatch.setattr(
        runner,
        "load_predictor_stability_cases",
        lambda **_: [
            {
                "case_id": "predictor_stability",
                "natal_datetime": "1583-02-23T05:45:00+00:00",
                "natal_location": "Villefranche, France",
                "natal_timezone": "Europe/Paris",
                "house_system_code": "R",
                "window_start": "1613-05-01T00:00:00+00:00",
                "window_end": "1613-05-15T00:00:00+00:00",
                "step_minutes_primary": 180,
                "step_minutes_secondary": 60,
                "expected_life_area": "honors",
                "expected_event_type": "public_recognition",
                "max_rank": 3,
                "max_dominant_gap_hours": 48,
            }
        ],
    )
    monkeypatch.setattr(
        runner,
        "load_documented_hindcast_cases",
        lambda **_: [
            {
                "case_id": "hindcast",
                "natal_datetime": "1583-02-23T05:45:00+00:00",
                "natal_location": "Villefranche, France",
                "natal_timezone": "Europe/Paris",
                "house_system_code": "R",
                "window_start": "1615-07-01T00:00:00+00:00",
                "window_end": "1615-07-15T00:00:00+00:00",
                "step_minutes": 180,
                "target_window": {
                    "start": "1615-07-07T00:00:00+00:00",
                    "end": "1615-07-08T23:59:59+00:00",
                },
                "expected_life_areas": ["danger"],
                "expected_event_types": ["accident_major"],
                "max_rank": 3,
                "max_peak_distance_hours": 48,
            }
        ],
    )
    result = runner.run_workflow_benchmarks()
    assert result["exact_scan_consistency"]["summary"]["pass_count"] == 1
    assert result["predictor_stability"]["summary"]["pass_count"] == 1
    assert result["documented_hindcasts"]["summary"]["pass_count"] == 1
