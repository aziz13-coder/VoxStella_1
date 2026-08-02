from datetime import datetime, timezone
from pathlib import Path
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module
import astro_clock_api
import context_layers
import primary_directions
import transits_morin


def _clock_payload():
    return {
        "timestamp": datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc).isoformat(),
        "location": "Paris, France",
        "timezone": "Europe/Paris",
        "mode": "manual",
        "house_system_code": "R",
        "latitude": 48.8566,
        "longitude": 2.3522,
    }


def test_transits_context_auto_returns_context_maturity(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {
                "house_rulers": {"1": "Saturn", "10": "Jupiter"},
                "planets": {"Sun": {"longitude": 10.0}, "Moon": {"longitude": 20.0}},
            },
            {
                "timestamp": "1583-02-23T05:45:00+00:00",
                "location": "Villefranche, France",
                "timezone": "Europe/Paris",
            },
        ),
    )
    monkeypatch.setattr(
        context_layers,
        "compute_solar_arc_windows",
        lambda natal_dt, year, natal_cd: [
            {"start": "1613-05-01T00:00:00+00:00", "end": "1613-05-03T00:00:00+00:00", "label": "Solar Arc Window"}
        ],
    )
    monkeypatch.setattr(
        context_layers,
        "compute_progressed_planet_windows",
        lambda natal_dt, year, natal_cd: [
            {
                "start": "1613-05-08T00:00:00+00:00",
                "end": "1613-05-10T00:00:00+00:00",
                "outer_start": "1613-05-07T00:00:00+00:00",
                "outer_end": "1613-05-11T00:00:00+00:00",
                "label": "Progressed Window",
            }
        ],
    )
    monkeypatch.setattr(context_layers, "suggest_focus_from_natal", lambda natal_cd: ([1, 10], ["Saturn", "Jupiter"]))
    monkeypatch.setattr(
        primary_directions,
        "compute_primary_direction_windows",
        lambda natal_dt, year, natal_cd: [
            {"start": "1613-05-09T00:00:00+00:00", "end": "1613-05-10T00:00:00+00:00", "label": "PD Window"}
        ],
    )

    response = client.get(
        "/api/astro-clock/context/auto",
        query_string={
            "natal_datetime": "1583-02-23T05:45:00+00:00",
            "natal_location": "Villefranche, France",
            "natal_timezone": "Europe/Paris",
            "anchor_center": "1613-05-09T12:00:00+00:00",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert "context_maturity" in data
    maturity = data["context_maturity"]
    assert maturity["primary_directions"]["level"] == "partial"
    assert maturity["solar_arc"]["level"] == "partial"
    assert maturity["secondary_progressions"]["level"] == "partial"
    assert maturity["solar_return"]["level"] == "partial"
    assert maturity["lunar_return"]["level"] == "helper_only"
    assert maturity["focus_suggestions"]["level"] == "helper_only"


def test_prediction_sort_prioritizes_crisis_angle_testimony_over_benefic_honors():
    honors = {
        "event_type": "promotion",
        "life_area": "honors",
        "probability": 0.261,
        "score": 0.0,
        "label": "Sun Trine Jupiter",
        "factors": {
            "transit": "Sun Trine Jupiter",
            "determination_strength": 0.0,
            "significance": 0.0,
        },
    }
    crisis = {
        "event_type": "accident_major",
        "life_area": "danger",
        "probability": 1.0,
        "score": 30.0,
        "label": "Mars Quincunx Asc",
        "factors": {
            "transit": "Mars Quincunx Asc",
            "direction": "Danger direction @ 1615-07-07T12:00:00+00:00",
            "determination_strength": -0.9,
            "significance": -8.0,
        },
    }

    ranked = sorted([honors, crisis], key=astro_clock_api._prediction_sort_key)

    assert ranked[0]["event_type"] == "accident_major"
    assert astro_clock_api._prediction_domain_alignment(crisis) == 1.0
    assert astro_clock_api._prediction_crisis_focus(crisis) > 0.0


def test_prediction_payload_distinguishes_rule_support_from_probability():
    hit = {
        "transiting": "Mars",
        "aspect": "Square",
        "target_label": "C7",
        "determination_strength": 0.18,
        "concordance": {"overall_concordance": 0.42},
        "prediction": {
            "eventType": "relationship_conflict",
            "lifeArea": "relationships",
            "description": "Theme only",
            "evidenceLevel": "theme_only",
            "isEventPrediction": False,
            "score": 12.0,
        },
    }

    prediction = astro_clock_api._prediction_from_hit(hit, "2026-05-10T12:00:00+00:00")

    assert prediction["probability"] == 0.42
    assert prediction["rule_support"] == 0.42
    assert prediction["probability_basis"] == "morin_rule_concordance"
    assert prediction["is_statistical_probability"] is False
    assert prediction["evidence_level"] == "theme_only"
    assert prediction["is_event_prediction"] is False


def test_retry_enrichment_restores_request_history_before_fallback(monkeypatch):
    registry_context = transits_morin._new_transit_registry_context()
    registry_context["simultaneous"]["Asc"].append({"marker": "original"})
    calls = []

    def fake_enrich(_chart, hits, _timestamp, **kwargs):
        active_registry = kwargs["registry_context"]["simultaneous"]["Asc"]
        calls.append(list(active_registry))
        if kwargs.get("pd_windows"):
            active_registry.append({"marker": "failed-rich-pass"})
            raise RuntimeError("rich pass failed")
        assert list(active_registry) == [{"marker": "original"}]
        return [{**hits[0], "fallback": True}]

    monkeypatch.setattr(transits_morin, "enrich_hits_with_concordance", fake_enrich)

    result = astro_clock_api._retry_enrich_transit_hits(
        {},
        [{"transiting": "Saturn", "target_label": "Asc"}],
        "2026-01-01T00:00:00Z",
        pd_windows=[{"start": "2026-01-01T00:00:00Z"}],
        registry_context=registry_context,
    )

    assert result[0]["fallback"] is True
    assert len(calls) == 2
    assert list(registry_context["simultaneous"]["Asc"]) == [
        {"marker": "original"}
    ]


def test_retry_enrichment_restores_request_history_when_both_passes_fail(monkeypatch):
    registry_context = transits_morin._new_transit_registry_context()
    registry_context["simultaneous"]["Asc"].append({"marker": "original"})

    def fake_enrich(_chart, _hits, _timestamp, **kwargs):
        kwargs["registry_context"]["simultaneous"]["Asc"].append(
            {"marker": "partial-pass"}
        )
        raise RuntimeError("enrichment failed")

    monkeypatch.setattr(transits_morin, "enrich_hits_with_concordance", fake_enrich)
    raw_hits = [{"transiting": "Saturn", "target_label": "Asc"}]

    result = astro_clock_api._retry_enrich_transit_hits(
        {},
        raw_hits,
        "2026-01-01T00:00:00Z",
        pd_windows=[{"start": "2026-01-01T00:00:00Z"}],
        registry_context=registry_context,
    )

    assert result is raw_hits
    assert list(registry_context["simultaneous"]["Asc"]) == [
        {"marker": "original"}
    ]


def test_theme_only_event_does_not_receive_predictor_event_bonus():
    base = {
        "event_type": "relationship_conflict",
        "life_area": "relationships",
        "probability": 0.42,
        "score": 12.0,
        "factors": {"determination_strength": 0.18, "significance": 12.0},
    }
    theme = {**base, "evidence_level": "theme_only", "is_event_prediction": False}
    supported = {**base, "evidence_level": "supported", "is_event_prediction": True}

    assert (
        astro_clock_api._predictor_occurrence_support(supported)
        - astro_clock_api._predictor_occurrence_support(theme)
    ) == 20.0


def test_select_dominant_occurrence_uses_midpoint_of_strongest_band():
    occurrences = [
        {"date": "1615-07-01T00:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-04T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-08T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-12T00:00:00+00:00", "support_score": 86.3, "score": 30.0},
        {"date": "1615-07-14T12:00:00+00:00", "support_score": 86.3, "score": 30.0},
    ]

    dominant = astro_clock_api._select_dominant_occurrence(occurrences)

    assert dominant == "1615-07-08T12:00:00+00:00"


def test_predictor_peak_rows_dedupe_repeated_support_window_identity():
    def row(timestamp, step_score, count, event_type="promotion", life_area="honors", transit="Jupiter Semi-sextile MC"):
        return {
            "timestamp": timestamp,
            "step_score": step_score,
            "count": count,
            "predictions": [
                {
                    "date": timestamp,
                    "event_type": event_type,
                    "life_area": life_area,
                    "label": transit,
                    "description": f"{transit} indicates {event_type}",
                    "probability": 1.0,
                    "score": 60.0,
                    "tags": [event_type, life_area],
                    "factors": {
                        "transit": transit,
                        "determination_strength": 1.0,
                        "significance": 60.0,
                    },
                }
            ],
        }

    peaks = astro_clock_api._build_predictor_peak_rows(
        [
            row("2026-05-01T00:00:00+00:00", 900.0, 90),
            row("2026-05-01T10:00:00+00:00", 890.0, 91),
            row("2026-05-03T20:00:00+00:00", 880.0, 92),
            row(
                "2026-05-01T01:00:00+00:00",
                780.0,
                80,
                event_type="family_problems",
                life_area="home",
                transit="Mars Square Saturn",
            ),
        ],
        limit=10,
    )
    serialized = astro_clock_api._serialize_peak_rows(peaks)

    promotion_peaks = [
        peak for peak in serialized
        if peak.get("event_type") == "promotion" and peak.get("transit") == "Jupiter Semi-sextile MC"
    ]

    assert len(promotion_peaks) == 1
    assert any(peak.get("event_type") == "family_problems" for peak in serialized)


def test_predictor_route_peaks_use_support_groups_not_repeated_row_primary():
    series = [
        {
            "timestamp": "2026-05-01T00:00:00+00:00",
            "step_score": 900.0,
            "count": 90,
            "predictions": [
                {
                    "date": "2026-05-01T00:00:00+00:00",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "label": "Jupiter Semi-sextile MC",
                    "description": "Jupiter Semi-sextile MC indicates promotion",
                    "probability": 1.0,
                    "score": 60.0,
                    "tags": ["promotion", "honors"],
                    "factors": {"transit": "Jupiter Semi-sextile MC", "determination_strength": 1.0, "significance": 60.0},
                }
            ],
        },
        {
            "timestamp": "2026-05-01T01:00:00+00:00",
            "step_score": 890.0,
            "count": 88,
            "predictions": [
                {
                    "date": "2026-05-01T01:00:00+00:00",
                    "event_type": "promotion",
                    "life_area": "honors",
                    "label": "Jupiter Semi-sextile MC",
                    "description": "Jupiter Semi-sextile MC indicates promotion",
                    "probability": 1.0,
                    "score": 60.0,
                    "tags": ["promotion", "honors"],
                    "factors": {"transit": "Jupiter Semi-sextile MC", "determination_strength": 1.0, "significance": 60.0},
                }
            ],
        },
    ]
    groups = [
        {
            "event_type": "promotion",
            "life_area": "honors",
            "label": "Jupiter Semi-sextile MC",
            "description": "Jupiter Semi-sextile MC indicates promotion",
            "transit": "Jupiter Semi-sextile MC",
            "dominant_timestamp": "2026-05-01T00:00:00+00:00",
            "support_focus": 500.0,
            "support_density": 100.0,
            "support_score": 1000.0,
            "probability_max": 1.0,
            "domain_alignment_max": 1.0,
            "occurrences": [{"date": "2026-05-01T00:00:00+00:00", "support_score": 108.8}],
        },
        {
            "event_type": "family_problems",
            "life_area": "home",
            "label": "Mars Square Saturn",
            "description": "Mars Square Saturn indicates family problems",
            "transit": "Mars Square Saturn",
            "dominant_timestamp": "2026-05-01T01:00:00+00:00",
            "support_focus": 450.0,
            "support_density": 90.0,
            "support_score": 900.0,
            "probability_max": 1.0,
            "domain_alignment_max": 1.0,
            "occurrences": [{"date": "2026-05-01T01:00:00+00:00", "support_score": 78.8}],
        },
    ]

    peaks = astro_clock_api._build_predictor_group_peak_rows(series, groups, limit=10)
    serialized = astro_clock_api._serialize_peak_rows(peaks)

    assert [peak["event_type"] for peak in serialized] == ["promotion", "family_problems"]
    assert serialized[0]["support_score"] == 108.8
    assert serialized[1]["support_score"] == 78.8


def test_transit_scan_routes_reject_oversized_windows_before_scanning(monkeypatch):
    client = app_module.app.test_client()
    scan_called = False

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {
                "house_rulers": {"1": "Saturn"},
                "planets": {"Sun": {"longitude": 10.0}},
            },
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )
    monkeypatch.setattr(astro_clock_api, "_STREAM_MAX_STEPS", 10)

    def fail_scan(*args, **kwargs):
        nonlocal scan_called
        scan_called = True
        raise AssertionError("scan should not run after bounds validation fails")

    monkeypatch.setattr(transits_morin, "scan_morin_transits_window", fail_scan)

    query = {
        "natal_datetime": "1990-01-01T00:00:00+00:00",
        "natal_location": "London, UK",
        "natal_timezone": "Europe/London",
        "start": "2026-01-01T00:00:00+00:00",
        "end": "2026-01-01T02:00:00+00:00",
        "step_minutes": "5",
    }

    for path in (
        "/api/astro-clock/transits/window",
        "/api/astro-clock/predictor",
        "/api/astro-clock/transits/window/stream",
        "/api/astro-clock/transits/window/export",
    ):
        response = client.get(path, query_string=query)
        payload = response.get_json()

        assert response.status_code == 400
        assert payload["success"] is False
        assert "max is 10" in payload["error"]

    assert scan_called is False


def test_exact_transits_route_applies_serialized_filters(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {
                "house_rulers": {"1": "Saturn"},
                "planets": {"Sun": {"longitude": 10.0}},
            },
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )
    monkeypatch.setattr(astro_clock_api, "_compute_pd_windows_for_years", lambda *args, **kwargs: [])
    monkeypatch.setattr(astro_clock_api, "_retry_enrich_transit_hits", lambda _cd, hits, _ts, **kwargs: hits)

    def fake_compute(*args, **kwargs):
        return [
            {
                "transiting": "Jupiter",
                "natal": "Moon",
                "target_label": "Moon",
                "aspect": "Trine",
                "orb": 0.2,
                "score": 20,
                "significance": 20,
            },
            {
                "transiting": "Saturn",
                "natal": "Sun",
                "target_label": "Sun",
                "aspect": "Square",
                "orb": 0.1,
                "score": 40,
                "significance": 40,
                "prediction": {"eventType": "illness", "lifeArea": "health"},
            },
        ]

    monkeypatch.setattr(transits_morin, "compute_morin_transits_to_natal", fake_compute)

    response = client.get(
        "/api/astro-clock/transits",
        query_string={
            "natal_datetime": "1990-01-01T00:00:00+00:00",
            "natal_location": "London, UK",
            "natal_timezone": "Europe/London",
            "transit_datetime": "2026-01-01T00:00:00+00:00",
            "transiting": "Saturn",
            "natal": "Sun",
            "aspect": "Square",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    rows = payload["data"]["transits"]
    assert len(rows) == 1
    assert rows[0]["transiting"] == "Saturn"
    assert rows[0]["natal"] == "Sun"
    assert rows[0]["aspect"] == "Square"


def test_transit_scan_routes_reject_invalid_step_before_scanning(monkeypatch):
    client = app_module.app.test_client()
    scan_called = False

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {
                "house_rulers": {"1": "Saturn"},
                "planets": {"Sun": {"longitude": 10.0}},
            },
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )

    def fail_scan(*args, **kwargs):
        nonlocal scan_called
        scan_called = True
        raise AssertionError("scan should not run after step validation fails")

    monkeypatch.setattr(transits_morin, "scan_morin_transits_window", fail_scan)

    query = {
        "natal_datetime": "1990-01-01T00:00:00+00:00",
        "natal_location": "London, UK",
        "natal_timezone": "Europe/London",
        "start": "2026-01-01T00:00:00+00:00",
        "end": "2026-01-01T02:00:00+00:00",
        "step_minutes": "not-a-number",
    }

    for path in (
        "/api/astro-clock/transits/window",
        "/api/astro-clock/predictor",
        "/api/astro-clock/transits/window/stream",
        "/api/astro-clock/transits/window/export",
    ):
        response = client.get(path, query_string=query)
        payload = response.get_json()

        assert response.status_code == 400
        assert payload["success"] is False
        assert payload["error"] == "Invalid step_minutes"

    assert scan_called is False


def test_exact_transit_routes_reject_invalid_timestamp_before_compute(monkeypatch):
    client = app_module.app.test_client()
    compute_called = False

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {"planets": {"Sun": {"longitude": 10.0}}},
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )

    def fail_compute(*args, **kwargs):
        nonlocal compute_called
        compute_called = True
        raise AssertionError("compute should not run after timestamp validation fails")

    monkeypatch.setattr(transits_morin, "compute_morin_transits_to_natal", fail_compute)
    query = {
        "natal_datetime": "1990-01-01T00:00:00+00:00",
        "natal_location": "London, UK",
        "natal_timezone": "Europe/London",
        "transit_datetime": "not-an-instant",
    }

    for path in (
        "/api/astro-clock/transits",
        "/api/astro-clock/transits/export",
    ):
        response = client.get(path, query_string=query)
        payload = response.get_json()

        assert response.status_code == 400
        assert payload["success"] is False
        assert payload["error"] == "Invalid transit_datetime"

    assert compute_called is False


def test_window_context_filter_normalizes_mixed_naive_and_aware_instants(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {"planets": {"Sun": {"longitude": 10.0}}},
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )
    monkeypatch.setattr(astro_clock_api, "_compute_pd_windows_for_years", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        transits_morin,
        "scan_morin_transits_window",
        lambda *args, **kwargs: [
            {
                "timestamp": "2026-01-01T01:00:00Z",
                "count": 0,
                "top": [],
                "step_score": 0.0,
                "tone": "mixed",
            },
            {
                "timestamp": "2026-01-01T03:00:00+00:00",
                "count": 0,
                "top": [],
                "step_score": 0.0,
                "tone": "mixed",
            },
        ],
    )

    response = client.get(
        "/api/astro-clock/transits/window",
        query_string={
            "natal_datetime": "1990-01-01T00:00:00+00:00",
            "natal_location": "London, UK",
            "natal_timezone": "Europe/London",
            "start": "2026-01-01T00:00:00",
            "end": "2026-01-01T04:00:00Z",
            "step_minutes": "60",
            "pd_start": "2026-01-01T00:30:00",
            "pd_end": "2026-01-01T01:30:00Z",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert [row["timestamp"] for row in payload["data"]["series"]] == [
        "2026-01-01T01:00:00Z",
    ]


def test_scan_datetime_validation_preserves_explicit_offset():
    parsed, error = astro_clock_api._parse_transit_scan_datetime(
        "2026-01-01T12:00:00-05:00",
        "start",
    )

    assert error is None
    assert parsed is not None
    assert parsed.isoformat() == "2026-01-01T12:00:00-05:00"


def test_scan_routes_reject_incomplete_context_windows(monkeypatch):
    client = app_module.app.test_client()
    scan_called = False

    monkeypatch.setattr(
        astro_clock_api,
        "_natal_from_query",
        lambda args: (
            {"planets": {"Sun": {"longitude": 10.0}}},
            {
                "timestamp": "1990-01-01T00:00:00+00:00",
                "location": "London, UK",
                "timezone": "Europe/London",
            },
        ),
    )

    def fail_scan(*args, **kwargs):
        nonlocal scan_called
        scan_called = True
        raise AssertionError("scan should not run after context validation fails")

    monkeypatch.setattr(transits_morin, "scan_morin_transits_window", fail_scan)
    query = {
        "natal_datetime": "1990-01-01T00:00:00+00:00",
        "natal_location": "London, UK",
        "natal_timezone": "Europe/London",
        "start": "2026-01-01T00:00:00Z",
        "end": "2026-01-01T04:00:00Z",
        "step_minutes": "60",
        "pd_start": "2026-01-01T00:30:00Z",
    }

    for path in (
        "/api/astro-clock/transits/window",
        "/api/astro-clock/predictor",
        "/api/astro-clock/transits/window/stream",
        "/api/astro-clock/transits/window/export",
    ):
        response = client.get(path, query_string=query)
        payload = response.get_json()

        assert response.status_code == 400
        assert payload["success"] is False
        assert payload["error"] == "pd_start and pd_end must be provided together"

    assert scan_called is False
