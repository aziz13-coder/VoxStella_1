from __future__ import annotations

import itertools
from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.battle import score_battle_election
from backend.election_models.beautification import score_beautification_election
from backend.election_models.journey import score_journey_election
from backend.election_models.legal import score_legal_election
from backend.election_models.surgery import score_surgery_election
from backend.election_models.viral_content import score_viral_content_election
from tests.election_stress_utils import (
    base_battle_chart,
    base_beautification_chart,
    base_journey_chart,
    base_legal_chart,
    base_surgery_chart,
    base_viral_chart,
    clone_chart,
    set_aspects,
    set_planet,
    set_whole_sign_asc,
)


def test_journey_rank_matrix_degrades_with_fixed_asc_and_l1_retrograde():
    scores: dict[tuple[bool, bool], float] = {}

    for fixed_asc, l1_retrograde in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_journey_chart())
        if fixed_asc:
            set_whole_sign_asc(chart, 30.0)
        if l1_retrograde:
            set_planet(chart, "Venus", retrograde=True)
        scores[(fixed_asc, l1_retrograde)] = score_journey_election(chart).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]
    assert scores[(False, True)] > scores[(True, True)]


def test_surgery_rank_matrix_keeps_soft_warning_above_never_conditions():
    scores: dict[tuple[bool, bool], float] = {}

    for moon_to_retrograde, moon_bad_house in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_surgery_chart())
        if moon_to_retrograde:
            set_planet(chart, "Jupiter", retrograde=True)
        if moon_bad_house:
            set_planet(chart, "Moon", house=8, longitude=220.0, sign="Scorpio")
        scores[(moon_to_retrograde, moon_bad_house)] = score_surgery_election(
            chart,
            options={"procedure": "cutting", "surgery_sign": "Leo"},
        ).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]
    assert scores[(False, True)] <= -90.0
    assert scores[(True, True)] <= -90.0


def test_battle_rank_matrix_prohibition_dominates_non_prohibited_variants():
    scores: dict[tuple[bool, bool], float] = {}

    for l1_retrograde, l1_to_stronger_l7 in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_battle_chart())
        if l1_retrograde:
            set_planet(chart, "Venus", retrograde=True)
        if l1_to_stronger_l7:
            set_aspects(
                chart,
                [{"planet1": "Venus", "planet2": "Mars", "aspect": "Square", "phase": "applying"}],
            )
        scores[(l1_retrograde, l1_to_stronger_l7)] = score_battle_election(
            chart,
            options={"action_type": "attack"},
        ).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, True)] <= -9000.0
    assert scores[(True, True)] <= -9000.0
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]


def test_legal_rank_matrix_degrades_with_mercury_rx_and_hostile_court():
    scores: dict[tuple[bool, bool], float] = {}

    for mercury_retrograde, hostile_court in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_legal_chart())
        if mercury_retrograde:
            set_planet(chart, "Mercury", retrograde=True)
        if hostile_court:
            set_planet(chart, "Jupiter", longitude=35.0, sign="Taurus", house=12)
            set_planet(chart, "Saturn", longitude=350.0, sign="Pisces", house=10)
        scores[(mercury_retrograde, hostile_court)] = score_legal_election(
            chart,
            options={"legal_action": "filing"},
        ).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]
    assert scores[(False, True)] > scores[(True, True)]


def test_viral_rank_matrix_degrades_with_mercury_rx_and_audience_drag():
    scores: dict[tuple[bool, bool], float] = {}

    for mercury_retrograde, audience_drag in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_viral_chart())
        if mercury_retrograde:
            set_planet(chart, "Mercury", retrograde=True)
        if audience_drag:
            set_planet(chart, "Jupiter", longitude=5.0, sign="Aries", house=3)
            set_planet(chart, "Saturn", longitude=250.0, sign="Sagittarius", house=11)
        scores[(mercury_retrograde, audience_drag)] = score_viral_content_election(chart).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]
    assert scores[(False, True)] > scores[(True, True)]


def test_beautification_rank_matrix_forbidden_moon_and_venus_rx_stack():
    scores: dict[tuple[bool, bool], float] = {}

    for forbidden_moon, venus_retrograde in itertools.product([False, True], [False, True]):
        chart = clone_chart(base_beautification_chart())
        if forbidden_moon:
            set_planet(chart, "Moon", longitude=190.0, sign="Libra", house=6)
        if venus_retrograde:
            set_planet(chart, "Venus", retrograde=True)
        scores[(forbidden_moon, venus_retrograde)] = score_beautification_election(
            chart,
            options={"body_parts": ["cheeks"], "procedure_type": "fillers"},
        ).value

    assert scores[(False, False)] > scores[(True, False)]
    assert scores[(False, False)] > scores[(False, True)]
    assert scores[(True, False)] > scores[(True, True)]
    assert scores[(False, True)] > scores[(True, True)]
