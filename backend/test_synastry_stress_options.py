import itertools
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from synastry_stress_support import assert_report_invariants, build_curated_report, build_report_from_seed


OPTION_CASES = [
    {
        "include_modern": include_modern,
        "include_nodes": include_nodes,
        "include_chiron": include_chiron,
        "orb_profile": orb_profile,
    }
    for include_modern, include_nodes, include_chiron, orb_profile in itertools.product(
        (True, False),
        (True, False),
        (True, False),
        ("tight", "balanced", "wide"),
    )
]


def _case_id(options):
    modern = "modern-on" if options["include_modern"] else "modern-off"
    nodes = "nodes-on" if options["include_nodes"] else "nodes-off"
    chiron = "chiron-on" if options["include_chiron"] else "chiron-off"
    return f"{modern}-{nodes}-{chiron}-{options['orb_profile']}"


@pytest.mark.parametrize("seed", (2, 7, 13))
@pytest.mark.parametrize("options", OPTION_CASES, ids=_case_id)
def test_option_matrix_reports_remain_valid(seed, options):
    report = build_report_from_seed(seed, **options)
    assert_report_invariants(report)
    assert report["options"] == options


@pytest.mark.parametrize(
    "layer_options",
    (
        {"include_modern": True, "include_nodes": True, "include_chiron": True},
        {"include_modern": False, "include_nodes": False, "include_chiron": False},
        {"include_modern": True, "include_nodes": False, "include_chiron": False},
        {"include_modern": False, "include_nodes": True, "include_chiron": True},
    ),
    ids=("all-layers", "core-only", "modern-only", "nodes-chiron-only"),
)
@pytest.mark.parametrize("seed", (3, 11, 17))
def test_wide_orbs_do_not_reduce_cross_aspect_candidates(seed, layer_options):
    tight = build_report_from_seed(seed, **layer_options, orb_profile="tight")
    wide = build_report_from_seed(seed, **layer_options, orb_profile="wide")

    assert len(wide["aspect_links"]) >= len(tight["aspect_links"])


def test_optional_point_layers_are_removed_from_active_points_and_aspects():
    full = build_curated_report(include_modern=True, include_nodes=True, include_chiron=True, orb_profile="balanced")
    reduced = build_curated_report(include_modern=False, include_nodes=False, include_chiron=False, orb_profile="balanced")

    disallowed = {"Uranus", "Neptune", "Pluto", "North Node", "South Node", "Chiron"}

    assert disallowed & set(full["governance"]["active_points"])
    assert not (disallowed & set(reduced["governance"]["active_points"]))
    assert all(
        item["point_a"] not in disallowed and item["point_b"] not in disallowed
        for item in reduced["aspect_links"]
    )
