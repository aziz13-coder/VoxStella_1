import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import (
    assert_report_invariants,
    build_report_from_chart_data,
    build_report_from_seed,
    category_map,
    clone_chart_data,
    find_aspect_hit,
    make_equal_house_chart,
    make_seeded_pair,
    planet_longitude,
    rule_evidence_deltas,
    set_planet_longitude,
)


def _exact_venus_mars_fixture():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 10.0,
            "Moon": 200.0,
            "Mercury": 40.0,
            "Venus": 70.0,
            "Mars": 100.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    chart_b = make_equal_house_chart(
        180.0,
        {
            "Sun": 250.0,
            "Moon": 20.0,
            "Mercury": 300.0,
            "Venus": 100.0,
            "Mars": 20.0,
            "Jupiter": 150.0,
            "Saturn": 10.0,
        },
    )
    return chart_a, chart_b


def test_exact_contact_strength_declines_monotonically_as_orb_widens():
    chart_a, base_chart_b = _exact_venus_mars_fixture()
    sampled_orbs = []
    sampled_closeness = []
    sampled_rule_deltas = []

    for delta in (0.0, 0.1, 0.25, 0.5, 1.0, 2.0):
        chart_b = clone_chart_data(base_chart_b)
        set_planet_longitude(chart_b, "Venus", planet_longitude(chart_b, "Venus") + delta)
        report = build_report_from_chart_data(chart_a, chart_b)
        assert_report_invariants(report)

        aspect_hit = find_aspect_hit(report, "Mars", "Venus", "Conjunction")
        assert aspect_hit is not None
        sampled_orbs.append(round(float(aspect_hit["orb"]), 6))
        sampled_closeness.append(round(float(aspect_hit["closeness"]), 6))
        sampled_rule_deltas.append(max(rule_evidence_deltas(report, "venus_mars_attraction")))

    assert sampled_orbs == sorted(sampled_orbs)
    assert sampled_closeness == sorted(sampled_closeness, reverse=True)
    assert sampled_rule_deltas == sorted(sampled_rule_deltas, reverse=True)


@pytest.mark.parametrize("seed", (1, 7, 13))
def test_small_seeded_perturbations_keep_stable_corpus_within_bounded_drift(seed):
    thresholds = {0.1: 0.6, 0.25: 1.0, 0.5: 1.8, 1.0: 3.2}
    base_report = build_report_from_seed(seed)
    assert_report_invariants(base_report)
    base_categories = category_map(base_report)

    bundle_a, bundle_b, _chart_a, _chart_b = make_seeded_pair(seed)
    base_chart_b = bundle_b["chart_data"]
    base_venus_longitude = planet_longitude(base_chart_b, "Venus")

    for delta, max_allowed_raw_drift in thresholds.items():
        shifted_chart_b = clone_chart_data(base_chart_b)
        set_planet_longitude(shifted_chart_b, "Venus", base_venus_longitude + delta)
        shifted_report = build_report_from_chart_data(bundle_a["chart_data"], shifted_chart_b)
        assert_report_invariants(shifted_report)

        shifted_categories = category_map(shifted_report)
        max_observed_raw_drift = max(
            abs(float(shifted_categories[key]["raw_score"]) - float(base_categories[key]["raw_score"]))
            for key in shifted_categories
            if key != "overall"
        )
        assert max_observed_raw_drift <= max_allowed_raw_drift

