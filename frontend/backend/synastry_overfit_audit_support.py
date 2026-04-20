from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import (  # noqa: E402
    build_report_from_chart_data,
    build_report_from_seed,
    category_map,
    make_equal_house_chart,
    report_has_rule,
)


BURDEN_FLOOR_RULE_ID = "burden_oppressive_cluster_floor"
COMPATIBILITY_GATE_RULE_ID = "compatibility_conflict_gate"
ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID = "attraction_supportive_polarity_floor"
ATTRACTION_STRESS_FLOOR_RULE_ID = "attraction_stress_cluster_floor"
ATTACHMENT_FLOOR_RULE_ID = "attachment_enduring_binding_cluster_floor"


def build_oppressive_cluster_report() -> Dict[str, Any]:
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 220.0,
            "Moon": 10.0,
            "Mercury": 70.0,
            "Venus": 100.0,
            "Mars": 190.0,
            "Jupiter": 250.0,
            "Saturn": 40.0,
        },
    )
    chart_b = make_equal_house_chart(
        180.0,
        {
            "Sun": 300.0,
            "Moon": 130.0,
            "Mercury": 250.0,
            "Venus": 310.0,
            "Mars": 20.0,
            "Jupiter": 80.0,
            "Saturn": 190.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b, label_a="Oppressive A", label_b="Oppressive B")


def build_serious_but_workable_saturn_report() -> Dict[str, Any]:
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
        180.0,
        {
            "Moon": 100.0,
            "Sun": 220.0,
            "Mercury": 250.0,
            "Venus": 310.0,
            "Mars": 20.0,
            "Jupiter": 80.0,
            "Saturn": 280.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b, label_a="Serious A", label_b="Serious B")


def build_high_friction_without_hard_saturn_report() -> Dict[str, Any]:
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 10.0,
            "Moon": 40.0,
            "Mercury": 70.0,
            "Venus": 100.0,
            "Mars": 130.0,
            "Jupiter": 220.0,
            "Saturn": 260.0,
        },
    )
    chart_b = make_equal_house_chart(
        180.0,
        {
            "Sun": 130.0,
            "Moon": 100.0,
            "Mercury": 160.0,
            "Venus": 190.0,
            "Mars": 40.0,
            "Jupiter": 310.0,
            "Saturn": 20.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b, label_a="Conflict A", label_b="Conflict B")


def build_supportive_polarity_chemistry_report() -> Dict[str, Any]:
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 0.0,
            "Moon": 40.0,
            "Mercury": 70.0,
            "Venus": 0.0,
            "Mars": 150.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    chart_b = make_equal_house_chart(
        0.0,
        {
            "Sun": 240.0,
            "Moon": 120.0,
            "Mercury": 250.0,
            "Venus": 10.0,
            "Mars": 180.0,
            "Jupiter": 80.0,
            "Saturn": 140.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b, label_a="Polarity A", label_b="Polarity B")


def build_magnetic_stress_cluster_report() -> Dict[str, Any]:
    chart_a = make_equal_house_chart(
        0.0,
        {
            "Sun": 0.0,
            "Moon": 40.0,
            "Mercury": 70.0,
            "Venus": 0.0,
            "Mars": 270.0,
            "Jupiter": 220.0,
            "Saturn": 310.0,
        },
    )
    chart_b = make_equal_house_chart(
        0.0,
        {
            "Sun": 240.0,
            "Moon": 90.0,
            "Mercury": 160.0,
            "Venus": 190.0,
            "Mars": 90.0,
            "Jupiter": 300.0,
            "Saturn": 0.0,
        },
    )
    return build_report_from_chart_data(chart_a, chart_b, label_a="Magnetic A", label_b="Magnetic B")


def report_rule_ids_by_category(report: Dict[str, Any], category_id: str) -> List[str]:
    category = category_map(report).get(category_id) or {}
    return [
        str(item.get("rule_family_id") or "")
        for item in (category.get("evidence_items") or [])
        if str(item.get("rule_family_id") or "").strip()
    ]


def seeded_adjustment_audit(seed_count: int = 24) -> Dict[str, Any]:
    burden_floor_seeds: List[int] = []
    compatibility_gate_seeds: List[int] = []
    attraction_supportive_floor_seeds: List[int] = []
    attraction_stress_floor_seeds: List[int] = []
    attachment_floor_seeds: List[int] = []
    sample_hits: List[Dict[str, Any]] = []

    for seed in range(seed_count):
        report = build_report_from_seed(seed)
        categories = category_map(report)
        has_burden_floor = report_has_rule(report, BURDEN_FLOOR_RULE_ID)
        has_compatibility_gate = report_has_rule(report, COMPATIBILITY_GATE_RULE_ID)
        has_attraction_supportive_floor = report_has_rule(report, ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID)
        has_attraction_stress_floor = report_has_rule(report, ATTRACTION_STRESS_FLOOR_RULE_ID)
        has_attachment_floor = report_has_rule(report, ATTACHMENT_FLOOR_RULE_ID)
        if has_burden_floor:
            burden_floor_seeds.append(seed)
        if has_compatibility_gate:
            compatibility_gate_seeds.append(seed)
        if has_attraction_supportive_floor:
            attraction_supportive_floor_seeds.append(seed)
        if has_attraction_stress_floor:
            attraction_stress_floor_seeds.append(seed)
        if has_attachment_floor:
            attachment_floor_seeds.append(seed)
        if (
            has_burden_floor
            or has_compatibility_gate
            or has_attraction_supportive_floor
            or has_attraction_stress_floor
            or has_attachment_floor
        ):
            sample_hits.append(
                {
                    "seed": seed,
                    "has_burden_floor": has_burden_floor,
                    "has_compatibility_gate": has_compatibility_gate,
                    "has_attraction_supportive_floor": has_attraction_supportive_floor,
                    "has_attraction_stress_floor": has_attraction_stress_floor,
                    "has_attachment_floor": has_attachment_floor,
                    "attraction_score": float((categories.get("attraction") or {}).get("score") or 0.0),
                    "attachment_score": float((categories.get("attachment") or {}).get("score") or 0.0),
                    "burden_score": float((categories.get("burden") or {}).get("score") or 0.0),
                    "compatibility_score": float((categories.get("compatibility") or {}).get("score") or 0.0),
                }
            )

    return {
        "seed_count": seed_count,
        "burden_floor_count": len(burden_floor_seeds),
        "burden_floor_seeds": burden_floor_seeds,
        "compatibility_gate_count": len(compatibility_gate_seeds),
        "compatibility_gate_seeds": compatibility_gate_seeds,
        "attraction_supportive_floor_count": len(attraction_supportive_floor_seeds),
        "attraction_supportive_floor_seeds": attraction_supportive_floor_seeds,
        "attraction_stress_floor_count": len(attraction_stress_floor_seeds),
        "attraction_stress_floor_seeds": attraction_stress_floor_seeds,
        "attachment_floor_count": len(attachment_floor_seeds),
        "attachment_floor_seeds": attachment_floor_seeds,
        "sample_hits": sample_hits,
    }
