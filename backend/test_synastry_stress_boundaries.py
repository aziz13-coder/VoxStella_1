import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import (
    assert_report_invariants,
    build_report_from_chart_data,
    find_aspect_hit,
    make_equal_house_chart,
    rule_evidence_deltas,
    report_has_rule,
)


def _wraparound_boundary_report():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 359.99,
            "Moon": 140.0,
            "Mercury": 70.0,
            "Venus": 100.0,
            "Mars": 130.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    chart_b = make_equal_house_chart(
        180.0,
        {
            "Moon": 0.01,
            "Sun": 210.0,
            "Mercury": 260.0,
            "Venus": 300.0,
            "Mars": 20.0,
            "Jupiter": 80.0,
            "Saturn": 150.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b)


def _exact_angle_boundary_report():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 10.0,
            "Moon": 40.0,
            "Mercury": 70.0,
            "Venus": 100.0,
            "Mars": 130.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    chart_b = make_equal_house_chart(
        60.0,
        {
            "Sun": 180.0,
            "Moon": 260.0,
            "Mercury": 290.0,
            "Venus": 320.0,
            "Mars": 350.0,
            "Jupiter": 80.0,
            "Saturn": 140.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b)


def _heavy_stack_boundary_report():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 9.7,
            "Moon": 10.4,
            "Mercury": 11.1,
            "Venus": 12.0,
            "Mars": 13.2,
            "Jupiter": 14.1,
            "Saturn": 15.0,
        },
    )
    chart_b = make_equal_house_chart(
        180.0,
        {
            "Sun": 189.8,
            "Moon": 190.3,
            "Mercury": 191.0,
            "Venus": 192.1,
            "Mars": 193.4,
            "Jupiter": 194.0,
            "Saturn": 195.2,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b)


@pytest.mark.parametrize(
    "builder",
    (_wraparound_boundary_report, _exact_angle_boundary_report, _heavy_stack_boundary_report),
    ids=("wraparound", "exact-angle", "heavy-stack"),
)
def test_boundary_fixture_reports_hold_invariants(builder):
    report = builder()
    assert_report_invariants(report)


def test_wraparound_boundary_preserves_cross_sign_conjunction_detection():
    report = _wraparound_boundary_report()
    aspect_hit = find_aspect_hit(report, "Sun", "Moon", "Conjunction")

    assert aspect_hit is not None
    assert float(aspect_hit["orb"]) < 0.05


def test_exact_angle_boundary_preserves_zero_orb_angle_contact():
    report = _exact_angle_boundary_report()
    aspect_hit = find_aspect_hit(report, "Sun", "Descendant", "Conjunction")

    assert aspect_hit is not None
    assert float(aspect_hit["orb"]) == 0.0
    assert float(aspect_hit["exactness"]) == 1.0


def test_inside_vs_outside_orb_boundary_toggles_expected_rule():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 10.0,
            "Moon": 200.0,
            "Mercury": 250.0,
            "Venus": 300.0,
            "Mars": 340.0,
            "Jupiter": 80.0,
            "Saturn": 140.0,
        },
    )
    inside_chart_b = make_equal_house_chart(
        180.0,
        {
            "Moon": 135.9,
            "Sun": 230.0,
            "Mercury": 270.0,
            "Venus": 320.0,
            "Mars": 20.0,
            "Jupiter": 110.0,
            "Saturn": 150.0,
        },
    )
    outside_chart_b = make_equal_house_chart(
        180.0,
        {
            "Moon": 136.1,
            "Sun": 230.0,
            "Mercury": 270.0,
            "Venus": 320.0,
            "Mars": 20.0,
            "Jupiter": 110.0,
            "Saturn": 150.0,
        },
    )

    inside_report = build_report_from_chart_data(chart_a, inside_chart_b, orb_profile="balanced")
    outside_report = build_report_from_chart_data(chart_a, outside_chart_b, orb_profile="balanced")

    assert_report_invariants(inside_report)
    assert_report_invariants(outside_report)
    assert report_has_rule(inside_report, "sun_moon_soft")
    assert not report_has_rule(outside_report, "sun_moon_soft")


def test_house_cusp_crossing_enables_overlay_only_after_crossing():
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 10.0,
            "Moon": 40.0,
            "Mercury": 70.0,
            "Venus": 100.0,
            "Mars": 130.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    before_chart_b = make_equal_house_chart(
        60.0,
        {
            "Sun": 179.99,
            "Moon": 260.0,
            "Mercury": 290.0,
            "Venus": 320.0,
            "Mars": 350.0,
            "Jupiter": 80.0,
            "Saturn": 140.0,
        },
    )
    after_chart_b = make_equal_house_chart(
        60.0,
        {
            "Sun": 180.01,
            "Moon": 260.0,
            "Mercury": 290.0,
            "Venus": 320.0,
            "Mars": 350.0,
            "Jupiter": 80.0,
            "Saturn": 140.0,
        },
    )

    before_report = build_report_from_chart_data(chart_a, before_chart_b)
    after_report = build_report_from_chart_data(chart_a, after_chart_b)

    assert_report_invariants(before_report)
    assert_report_invariants(after_report)
    assert not rule_evidence_deltas(before_report, "overlay_sun_major")
    assert rule_evidence_deltas(after_report, "overlay_sun_major")

