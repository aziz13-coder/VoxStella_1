from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent
TESTS_DIR = REPO_ROOT / "tests"
for path in (REPO_ROOT, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from synastry_overfit_audit_support import (
    ATTACHMENT_FLOOR_RULE_ID,
    ATTRACTION_STRESS_FLOOR_RULE_ID,
    ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID,
    BURDEN_FLOOR_RULE_ID,
    build_high_friction_without_hard_saturn_report,
    build_magnetic_stress_cluster_report,
    build_oppressive_cluster_report,
    build_serious_but_workable_saturn_report,
    build_supportive_polarity_chemistry_report,
    report_rule_ids_by_category,
    seeded_adjustment_audit,
)
from synastry_stress_support import category_map, report_has_rule
from tests.synastry_historical_replay_utils import (
    load_synastry_historical_replay_cases,
    replay_synastry_historical_case,
)


SLICE_2_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_2.json"
SLICE_3_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_3.json"


def test_burden_floor_fires_for_general_oppressive_cluster_archetype():
    report = build_oppressive_cluster_report()
    categories = category_map(report)

    assert report_has_rule(report, BURDEN_FLOOR_RULE_ID)
    assert float(categories["burden"]["score"]) >= 70.0
    assert BURDEN_FLOOR_RULE_ID in report_rule_ids_by_category(report, "burden")


def test_burden_floor_does_not_fire_for_serious_but_workable_saturn_archetype():
    report = build_serious_but_workable_saturn_report()
    categories = category_map(report)

    assert not report_has_rule(report, BURDEN_FLOOR_RULE_ID)
    assert float(categories["burden"]["score"]) <= 55.0


def test_burden_floor_does_not_fire_for_high_friction_chart_without_hard_saturn_cluster():
    report = build_high_friction_without_hard_saturn_report()
    categories = category_map(report)

    assert not report_has_rule(report, BURDEN_FLOOR_RULE_ID)
    assert float(categories["friction"]["score"]) >= 70.0


def test_supportive_attraction_floor_fires_for_polarity_plus_chemistry_archetype():
    report = build_supportive_polarity_chemistry_report()
    categories = category_map(report)

    assert report_has_rule(report, ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID)
    assert float(categories["attraction"]["score"]) >= 70.0
    assert ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID in report_rule_ids_by_category(report, "attraction")


def test_stress_attraction_floor_fires_for_magnetic_conflict_archetype():
    report = build_magnetic_stress_cluster_report()
    categories = category_map(report)

    assert report_has_rule(report, ATTRACTION_STRESS_FLOOR_RULE_ID)
    assert float(categories["friction"]["score"]) >= 70.0
    assert float(categories["attraction"]["score"]) >= 55.0
    assert ATTRACTION_STRESS_FLOOR_RULE_ID in report_rule_ids_by_category(report, "attraction")


def test_seeded_adjustment_audit_shows_burden_floor_is_selective():
    audit = seeded_adjustment_audit(seed_count=24)

    assert audit["seed_count"] == 24
    assert 0 < audit["burden_floor_count"] < audit["seed_count"]
    assert audit["burden_floor_count"] < audit["compatibility_gate_count"]
    assert 0 < audit["attraction_supportive_floor_count"] < audit["seed_count"]
    assert audit["attraction_stress_floor_count"] == 0
    assert 0 < audit["attachment_floor_count"] < audit["seed_count"]
    assert audit["attachment_floor_count"] < audit["compatibility_gate_count"]


def test_extended_historical_slice_shows_attraction_floors_fire_selectively_without_burden_floor_spread():
    fixture = load_synastry_historical_replay_cases(path=SLICE_2_PATH)
    statuses = {}
    burden_floor_hits = set()
    supportive_attraction_hits = set()
    stress_attraction_hits = set()

    for case in fixture["cases"]:
        report, comparison = replay_synastry_historical_case(case)
        statuses[case["id"]] = comparison["status"]
        if report_has_rule(report, BURDEN_FLOOR_RULE_ID):
            burden_floor_hits.add(case["id"])
        if report_has_rule(report, ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID):
            supportive_attraction_hits.add(case["id"])
        if report_has_rule(report, ATTRACTION_STRESS_FLOOR_RULE_ID):
            stress_attraction_hits.add(case["id"])

    assert statuses == {
        "frida_kahlo_diego_rivera": "partially_aligned",
        "sid_nancy": "aligned",
        "elizabeth_taylor_richard_burton": "aligned",
    }
    assert burden_floor_hits == set()
    assert supportive_attraction_hits == {"elizabeth_taylor_richard_burton"}
    assert stress_attraction_hits == {"sid_nancy"}


def test_third_historical_slice_confirms_attachment_floor_stays_selective():
    fixture = load_synastry_historical_replay_cases(path=SLICE_3_PATH)
    statuses = {}
    supportive_attraction_hits = set()
    stress_attraction_hits = set()
    burden_floor_hits = set()
    attachment_floor_hits = set()

    for case in fixture["cases"]:
        report, comparison = replay_synastry_historical_case(case)
        statuses[case["id"]] = comparison["status"]
        if report_has_rule(report, BURDEN_FLOOR_RULE_ID):
            burden_floor_hits.add(case["id"])
        if report_has_rule(report, ATTRACTION_SUPPORTIVE_FLOOR_RULE_ID):
            supportive_attraction_hits.add(case["id"])
        if report_has_rule(report, ATTRACTION_STRESS_FLOOR_RULE_ID):
            stress_attraction_hits.add(case["id"])
        if report_has_rule(report, ATTACHMENT_FLOOR_RULE_ID):
            attachment_floor_hits.add(case["id"])

    assert statuses == {
        "frank_sinatra_ava_gardner": "aligned",
        "sartre_beauvoir": "aligned",
    }
    assert burden_floor_hits == set()
    assert supportive_attraction_hits == set()
    assert stress_attraction_hits == set()
    assert attachment_floor_hits == {"sartre_beauvoir"}
