from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

import pytest


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.business import score_business_election
from backend.election_models.battle import score_battle_election
from backend.election_models.common import (
    _ang_sep,
    _collect_planets,
    _get_aspects_list,
    _house_from_lon,
    _is_via_combusta,
    _safe_float,
    _sign_from_lon,
)
from backend.election_models.contract import score_contract_election
from backend.election_models.journey import score_journey_election
from backend.election_models.surgery import score_surgery_election
from tests.election_stress_utils import (
    base_battle_chart,
    base_business_chart,
    base_contract_chart,
    base_journey_chart,
    base_surgery_chart,
    clone_chart,
    set_aspects,
)


def _assert_score_shape(score_obj) -> None:
    assert isinstance(score_obj.value, (int, float))
    assert math.isfinite(float(score_obj.value))
    assert isinstance(score_obj.tags, list)
    assert all(isinstance(tag, str) for tag in score_obj.tags)


def _variant_without_houses_and_optionals(chart: dict) -> dict:
    variant = clone_chart(chart)
    variant.pop("house_cusps", None)
    variant.pop("houses", None)
    variant.pop("moon_next_aspect", None)
    variant.pop("considerations", None)
    variant.pop("moon_state", None)
    planets = variant.get("planets") or {}
    if isinstance(planets, dict):
        for info in planets.values():
            if isinstance(info, dict):
                info.pop("house", None)
    return variant


def _variant_minimal_planets(chart: dict) -> dict:
    variant = clone_chart(chart)
    planets = variant.get("planets") or {}
    if isinstance(planets, dict):
        keep = {"Sun", "Moon", "Mercury"}
        variant["planets"] = {name: info for name, info in planets.items() if name in keep}
    variant.pop("planetary_aspects_precise", None)
    variant.pop("aspects", None)
    variant.pop("planetary_aspects", None)
    return variant


def _variant_planets_list_with_alias_aspects(chart: dict) -> dict:
    variant = clone_chart(chart)
    planets = []
    for name, info in (variant.get("planets") or {}).items():
        if not isinstance(info, dict):
            continue
        row = dict(info)
        row["planet"] = name
        row.pop("house", None)
        planets.append(row)
    variant["planets"] = planets
    aspects = list(variant.pop("planetary_aspects_precise", []) or [])
    random.Random(7).shuffle(aspects)
    variant["aspects"] = aspects
    return variant


SCORER_CASES = [
    (
        "surgery",
        score_surgery_election,
        base_surgery_chart,
        {"procedure": "cutting", "surgery_sign": "Leo"},
    ),
    ("journey", score_journey_election, base_journey_chart, {}),
    (
        "battle",
        score_battle_election,
        base_battle_chart,
        {"action_type": "attack"},
    ),
    (
        "contract",
        score_contract_election,
        base_contract_chart,
        {"prefer_fixed_asc": True, "contract_mode": "new"},
    ),
    ("business", score_business_election, base_business_chart, {}),
]


@pytest.mark.parametrize(
    ("variant_name", "variant_builder"),
    [
        ("no_houses_or_optionals", _variant_without_houses_and_optionals),
        ("minimal_planets", _variant_minimal_planets),
        ("planets_list_with_alias_aspects", _variant_planets_list_with_alias_aspects),
    ],
)
@pytest.mark.parametrize(("matter", "scorer", "chart_factory", "options"), SCORER_CASES)
def test_priority_scorers_return_finite_scores_on_sparse_variants(
    matter: str,
    scorer,
    chart_factory,
    options: dict,
    variant_name: str,
    variant_builder,
):
    chart = variant_builder(chart_factory())
    score_obj = scorer(chart, options=dict(options))

    _assert_score_shape(score_obj)


def test_common_helper_primitives_tolerate_sparse_and_wraparound_inputs():
    assert _safe_float("15:30:00") == pytest.approx(15.5)
    assert _safe_float("not-a-number") is None
    assert _sign_from_lon(359.9) == "Pisces"
    assert _house_from_lon(
        359.0,
        [330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0],
    ) == 1
    assert _house_from_lon(
        15.0,
        [330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0],
    ) == 2
    assert _ang_sep("bad", 10.0) == 999.0
    assert _is_via_combusta(195.0) is True
    assert _is_via_combusta(225.0) is False
    assert _collect_planets({"planets": [{"planet": "Moon", "longitude": 45.0}]})["Moon"]["longitude"] == 45.0
    aspects = [{"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Trine"}]
    assert _get_aspects_list({"aspects": aspects}) == aspects


@pytest.mark.parametrize(
    ("scorer", "chart_factory", "options"),
    [
        (score_contract_election, base_contract_chart, {"prefer_fixed_asc": True, "contract_mode": "new"}),
        (score_business_election, base_business_chart, {}),
    ],
)
def test_aspect_alias_and_order_do_not_change_commerce_scores(scorer, chart_factory, options):
    baseline = chart_factory()
    set_aspects(
        baseline,
        [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Trine", "phase": "applying"},
            {"planet1": "Mercury", "planet2": "Venus", "aspect": "Sextile", "phase": "applying"},
            {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Square", "phase": "applying"},
        ],
    )
    forward = scorer(clone_chart(baseline), options=dict(options))

    alias_variant = clone_chart(baseline)
    shuffled = list(reversed(alias_variant.pop("planetary_aspects_precise")))
    alias_variant["aspects"] = shuffled
    reverse = scorer(alias_variant, options=dict(options))

    assert forward.value == reverse.value
    assert Counter(forward.tags) == Counter(reverse.tags)
