import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import (
    build_curated_report,
    build_report_from_chart_data,
    build_report_from_seed,
    load_rule_catalog,
    make_equal_house_chart,
)


def _coverage_reports():
    reports = [build_curated_report()]
    for seed in range(40):
        reports.append(build_report_from_seed(seed))
        reports.append(build_report_from_seed(seed, swap=True))

    moon_quincunx_a = make_equal_house_chart(
        0.0,
        {"Moon": 10.0, "Sun": 200.0, "Mercury": 251.0, "Venus": 302.0, "Mars": 344.0, "Jupiter": 83.0, "Saturn": 147.0},
    )
    moon_quincunx_b = make_equal_house_chart(
        180.0,
        {"Moon": 160.0, "Sun": 20.0, "Mercury": 75.0, "Venus": 120.0, "Mars": 220.0, "Jupiter": 280.0, "Saturn": 320.0},
    )
    reports.append(build_report_from_chart_data(moon_quincunx_a, moon_quincunx_b))

    mercury_quincunx_a = make_equal_house_chart(
        0.0,
        {"Moon": 10.0, "Sun": 200.0, "Mercury": 20.0, "Venus": 302.0, "Mars": 344.0, "Jupiter": 83.0, "Saturn": 147.0},
    )
    mercury_quincunx_b = make_equal_house_chart(
        180.0,
        {"Moon": 130.0, "Sun": 260.0, "Mercury": 170.0, "Venus": 120.0, "Mars": 220.0, "Jupiter": 280.0, "Saturn": 320.0},
    )
    reports.append(build_report_from_chart_data(mercury_quincunx_a, mercury_quincunx_b))

    moon_activation_a = make_equal_house_chart(0.0, {"Moon": 10.0, "Sun": 200.0})
    moon_activation_b = make_equal_house_chart(
        180.0,
        {"Sun": 100.0, "Moon": 200.0, "Mercury": 260.0, "Venus": 320.0, "Mars": 150.0, "Jupiter": 230.0, "Saturn": 20.0},
    )
    reports.append(build_report_from_chart_data(moon_activation_a, moon_activation_b))
    return reports


def test_coverage_corpus_exercises_every_catalog_rule_id():
    catalog = load_rule_catalog()
    catalog_rule_ids = {str(item.get("id") or "") for item in catalog.get("rule_families") or []}
    seen_rule_ids = set()

    for report in _coverage_reports():
        seen_rule_ids.update(str(item) for item in report.get("governance", {}).get("active_rule_family_ids") or [])

    missing_rule_ids = sorted(rule_id for rule_id in catalog_rule_ids if rule_id and rule_id not in seen_rule_ids)
    assert missing_rule_ids == []


def test_coverage_corpus_exercises_every_catalog_rule_kind():
    catalog = load_rule_catalog()
    kind_by_id = {str(item.get("id") or ""): str(item.get("kind") or "") for item in catalog.get("rule_families") or []}
    seen_kinds = set()

    for report in _coverage_reports():
        for rule_id in report.get("governance", {}).get("active_rule_family_ids") or []:
            kind = kind_by_id.get(str(rule_id) or "")
            if kind:
                seen_kinds.add(kind)

    expected_kinds = {str(item.get("kind") or "") for item in catalog.get("rule_families") or [] if str(item.get("kind") or "")}
    assert sorted(seen_kinds) == sorted(expected_kinds)

