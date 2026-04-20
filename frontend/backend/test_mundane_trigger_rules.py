from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_models import ActiveClockContext, MundaneContextRequest, ResolvedMundaneContext
from mundane_trigger_rules import compute_trigger_profiles, index_trigger_profiles


def _context(*, chart_type_id: str = "war_event", chart_resolution=None):
    return ResolvedMundaneContext(
        request=MundaneContextRequest(chart_type=chart_type_id, domain="war_conflict", polity_id="france"),
        active_clock=ActiveClockContext(
            timestamp=datetime(2025, 4, 11, 12, 0, tzinfo=timezone.utc).isoformat(),
            location="Paris, France",
            timezone="Europe/Paris",
            mode="manual",
            house_system_code="P",
            latitude=48.8566,
            longitude=2.3522,
        ),
        chart_type={"id": chart_type_id, "label": chart_type_id},
        domain={"id": "war_conflict", "label": "war_conflict"},
        location_context={"id": "event_chart", "label": "event_chart"},
        polity={"id": "france", "label": "France", "capital": "Paris, France", "default_location": "Paris, France"},
        reference_chart=None,
        event_context={"location_context_type": "event_chart", "reference_location": "Paris, France"},
        chart_resolution=chart_resolution or {},
        research_flags=["benchmark_backed"],
        source_tags=["watters_war_houses"],
    )


def test_compute_trigger_profiles_reports_angularity_and_retrograde_mars():
    context = _context(
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "house_rulers": {"1": "Mars"},
                "planets": {
                    "Mars": {"house": 1, "retrograde": True, "longitude": 2.0},
                    "Jupiter": {"house": 10, "retrograde": False, "longitude": 91.5},
                },
            },
            "signals": {"mars_retrograde": True},
        }
    )

    profiles = index_trigger_profiles(context, trigger_ids=["angularity", "retrograde_mars"])

    assert profiles["angularity"]["active"] is True
    assert profiles["angularity"]["metrics"]["malefic_angular_count"] >= 1
    assert profiles["angularity"]["metrics"]["strongest_planet"] == "Mars"
    assert profiles["retrograde_mars"]["active"] is True
    assert profiles["retrograde_mars"]["metrics"]["retrograde"] is True
    assert 1 in profiles["retrograde_mars"]["metrics"]["rules_houses"]


def test_compute_trigger_profiles_reports_eclipse_degree_activation():
    context = _context(
        chart_resolution={
            "primary_chart": {
                "kind": "eclipse",
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {"Saturn": {"house": 10, "retrograde": False, "longitude": 91.0}},
            },
            "signals": {
                "activation_hits": [
                    {"planet": "Saturn", "target_point": "Sun", "orb_deg": 0.8},
                    {"planet": "Mars", "target_point": "Moon", "orb_deg": 1.4},
                ]
            },
        }
    )

    profile = index_trigger_profiles(context, trigger_ids=["eclipse_degree_activation"])["eclipse_degree_activation"]

    assert profile["active"] is True
    assert profile["metrics"]["hit_count"] == 2
    assert profile["metrics"]["strongest_orb_deg"] == 0.8
    assert "Saturn" in profile["metrics"]["activating_planets"]


def test_compute_trigger_profiles_marks_cycle_context_as_background_when_uncomputed():
    context = _context(
        chart_type_id="national_chart",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {},
            },
            "signals": {},
        },
    )

    profile = index_trigger_profiles(context, trigger_ids=["mutation_and_conjunction_cycles"])["mutation_and_conjunction_cycles"]

    assert profile["active"] is False
    assert profile["status"] == "background_only"
    assert "background_only" in profile["research_flags"]


def test_compute_trigger_profiles_reports_computed_cycle_context():
    context = _context(
        chart_type_id="aries_ingress",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {},
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
        },
    )

    profile = index_trigger_profiles(context, trigger_ids=["mutation_and_conjunction_cycles"])["mutation_and_conjunction_cycles"]

    assert profile["status"] == "computed"
    assert profile["active"] is True
    assert profile["score"] >= 12
    assert profile["metrics"]["turning_window_active"] is True
    assert profile["metrics"]["conjunction_sign"] == "Aquarius"
    assert "long_cycle_backdrop" in profile["research_flags"]


def test_compute_trigger_profiles_returns_requested_subset_only():
    context = _context(
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {"Mars": {"house": 1, "retrograde": False, "longitude": 5.0}},
            },
            "signals": {},
        }
    )

    profiles = compute_trigger_profiles(context, trigger_ids=["angularity"])

    assert [row["id"] for row in profiles] == ["angularity"]
