from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_scan_service
from mundane_models import ActiveClockContext


def _clock_context() -> ActiveClockContext:
    return ActiveClockContext(
        timestamp=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc).isoformat(),
        location="Miami, Florida, USA",
        timezone="America/New_York",
        mode="manual",
        house_system_code="P",
        latitude=25.7617,
        longitude=-80.1918,
    )


def test_build_weather_scan_request_requires_location_for_place_scope():
    try:
        weather_scan_service.build_weather_scan_request(
            {
                "family_id": "wind_event_pressure",
                "scan_scope": "place_timeline",
                "start_datetime": "2026-04-01T00:00:00+00:00",
                "end_datetime": "2026-04-02T00:00:00+00:00",
            }
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "location is required" in str(exc)


def test_build_weather_scan_request_requires_region_for_region_scope():
    try:
        weather_scan_service.build_weather_scan_request(
            {
                "family_id": "wind_event_pressure",
                "scan_scope": "region_timeline",
                "start_datetime": "2026-04-01T00:00:00+00:00",
                "end_datetime": "2026-04-02T00:00:00+00:00",
            }
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "region_id is required" in str(exc)


def test_build_weather_scan_request_accepts_place_coordinates():
    request_model = weather_scan_service.build_weather_scan_request(
        {
            "family_id": "wind_event_pressure",
            "scan_scope": "place_timeline",
            "location": "Miami, Florida, USA",
            "timezone": "America/New_York",
            "latitude": "25.7617",
            "longitude": "-80.1918",
            "start_datetime": "2026-04-01T00:00:00+00:00",
            "end_datetime": "2026-04-02T00:00:00+00:00",
        }
    )

    pool = weather_scan_service._candidate_pool(request_model)

    assert request_model.latitude == 25.7617
    assert request_model.longitude == -80.1918
    assert pool[0]["latitude"] == 25.7617
    assert pool[0]["longitude"] == -80.1918


def test_run_weather_scan_builds_series_and_ranked_rows(monkeypatch):
    request_model = weather_scan_service.build_weather_scan_request(
        {
            "family_id": "wind_event_pressure",
            "scan_scope": "region_timeline",
            "region_id": "persian_gulf",
            "start_datetime": "2026-04-01T00:00:00+00:00",
            "end_datetime": "2026-04-01T12:00:00+00:00",
            "time_step_hours": "6",
            "candidate_limit": "2",
            "top_k": "4",
        }
    )

    monkeypatch.setattr(
        weather_scan_service,
        "_candidate_pool",
        lambda req: [
            {"label": "Doha, Qatar", "country_name": "Qatar", "timezone": "Asia/Qatar", "latitude": 25.2854, "longitude": 51.531},
            {"label": "Dubai, United Arab Emirates", "country_name": "United Arab Emirates", "timezone": "Asia/Dubai", "latitude": 25.2048, "longitude": 55.2708},
        ],
    )

    def fake_eval(req, *, candidate, forecast_datetime, active_clock, bundle_resolver):
        hour = int(str(forecast_datetime)[11:13])
        base = 40 if "Doha" in candidate["label"] else 22
        score = base + (hour // 6)
        if "Dubai" in candidate["label"] and hour == 12:
            score = 48
        return {
            "datetime": forecast_datetime,
            "location": {
                "label": candidate["label"],
                "country_name": candidate["country_name"],
                "timezone": candidate["timezone"],
            },
            "score": score,
            "level": "active" if score >= 36 else "watch",
            "matched_rules": [{"label": "Angular weather signal", "score": score}],
            "summary": "Synthetic test weather row",
            "signals": {"framework_count": 1, "trigger_count": 1, "locality_count": 1, "locality_strength": 8, "path_concentration": 2},
            "event_focus": 10,
        }

    monkeypatch.setattr(weather_scan_service, "_evaluate_candidate_cell", fake_eval)

    payload = weather_scan_service.run_weather_scan(
        request_model,
        active_clock=_clock_context(),
        bundle_resolver=lambda *args, **kwargs: {},
    )

    assert payload["runtime_scope"] == "seed_weather_scan"
    assert payload["counts"]["evaluated"] == 6
    assert payload["counts"]["candidate_count"] == 2
    assert len(payload["results"]) == 4
    assert payload["results"][0]["location"]["label"] == "Dubai, United Arab Emirates"
    assert payload["series"]["series_overview"]["place_count"] == 2
    assert payload["series"]["peak_candidates"][0]["location"]["label"] == "Dubai, United Arab Emirates"
    assert payload["series"]["series_overview"]["ranking_mode"] == "event_focus_weighted"
    assert payload["series"]["places"][0]["event_focus_index"] >= 0


def test_select_series_peak_expands_recurring_equal_peak_window():
    series = [
        {"datetime": "2026-04-01T00:00:00+00:00", "score": 10},
        {"datetime": "2026-04-01T06:00:00+00:00", "score": 20},
        {"datetime": "2026-04-01T12:00:00+00:00", "score": 5},
        {"datetime": "2026-04-01T18:00:00+00:00", "score": 20},
        {"datetime": "2026-04-02T00:00:00+00:00", "score": 8},
    ]

    peak = weather_scan_service._select_series_peak(series)

    assert peak["peak_selection"] == "recurring_equal_peaks"
    assert peak["peak_window_start_datetime"] == "2026-04-01T06:00:00+00:00"
    assert peak["peak_window_end_datetime"] == "2026-04-01T18:00:00+00:00"
    assert peak["peak_occurrence_count"] == 2
