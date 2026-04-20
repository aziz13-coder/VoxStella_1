from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.battle import score_battle_election
from backend.election_models.business import score_business_election
from backend.election_models.contract import score_contract_election
from backend.election_models.journey import score_journey_election
from backend.election_models.legal import score_legal_election
from backend.election_models.marriage import score_marriage_election
from backend.election_models.surgery import score_surgery_election
from tests.election_stress_utils import (
    base_battle_chart,
    base_business_chart,
    base_contract_chart,
    base_journey_chart,
    base_legal_chart,
    base_marriage_chart,
    base_surgery_chart,
    clone_chart,
    set_aspects,
    set_planet,
    set_whole_sign_asc,
)


def test_surgery_mercury_retrograde_never_beats_direct_control():
    control_chart = base_surgery_chart()
    control = score_surgery_election(control_chart, options={"procedure": "cutting", "surgery_sign": "Leo"})

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Mercury", retrograde=True)
    variant = score_surgery_election(variant_chart, options={"procedure": "cutting", "surgery_sign": "Leo"})

    assert control.value > variant.value
    assert variant.value <= -90.0
    assert any("Mercury retrograde" in tag for tag in variant.tags)


def test_surgery_moon_applying_to_retrograde_planet_never_beats_control():
    control_chart = base_surgery_chart()
    control = score_surgery_election(control_chart, options={"procedure": "cutting", "surgery_sign": "Leo"})

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Jupiter", retrograde=True)
    variant = score_surgery_election(variant_chart, options={"procedure": "cutting", "surgery_sign": "Leo"})

    assert control.value > variant.value
    assert any("Moon applying to retrograde planet" in tag for tag in variant.tags)


def test_journey_fixed_asc_never_beats_movable_control():
    control_chart = base_journey_chart()
    control = score_journey_election(control_chart)

    variant_chart = clone_chart(control_chart)
    set_whole_sign_asc(variant_chart, 30.0)
    variant = score_journey_election(variant_chart)

    assert control.value > variant.value
    assert any("Cardinal Asc (movement)" in tag for tag in control.tags)
    assert any("Fixed Asc (delays)" in tag for tag in variant.tags)


def test_journey_retrograde_asc_ruler_never_beats_direct_control():
    control_chart = base_journey_chart()
    control = score_journey_election(control_chart)

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Venus", retrograde=True)
    variant = score_journey_election(variant_chart)

    assert control.value > variant.value
    assert any("ASC ruler retrograde" in tag for tag in variant.tags)


def test_battle_l1_to_stronger_l7_prohibition_overrides_positive_supports():
    control_chart = base_battle_chart()
    control = score_battle_election(control_chart, options={"action_type": "attack"})

    variant_chart = clone_chart(control_chart)
    set_aspects(
        variant_chart,
        [{"planet1": "Venus", "planet2": "Mars", "aspect": "Square", "phase": "applying"}],
    )
    variant = score_battle_election(variant_chart, options={"action_type": "attack"})

    assert control.value > variant.value
    assert variant.value <= -9000.0
    assert any("Ascendant ruler applying to stronger 7th ruler" in tag for tag in variant.tags)


def test_contract_new_contract_mercury_retrograde_scores_below_direct_control():
    control_chart = base_contract_chart()
    control = score_contract_election(control_chart, options={"prefer_fixed_asc": True, "contract_mode": "new"})

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Mercury", retrograde=True)
    variant = score_contract_election(variant_chart, options={"prefer_fixed_asc": True, "contract_mode": "new"})

    assert control.value > variant.value
    assert any("Deal-breaker: Mercury retrograde" in tag for tag in variant.tags)


def test_business_improving_mc_ruler_never_lowers_score():
    weak_chart = base_business_chart()
    set_planet(weak_chart, "Saturn", longitude=120.0, sign="Leo", house=5, retrograde=True)
    weak = score_business_election(weak_chart)

    strong_chart = base_business_chart()
    set_planet(strong_chart, "Saturn", longitude=275.0, sign="Capricorn", house=10, retrograde=False)
    strong = score_business_election(strong_chart)

    assert strong.value > weak.value
    assert any("MC ruler retrograde" in tag for tag in weak.tags)
    assert any("MC ruler angular" in tag for tag in strong.tags)


def test_marriage_venus_retrograde_never_beats_direct_control():
    control_chart = base_marriage_chart()
    control = score_marriage_election(control_chart)

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Venus", retrograde=True)
    variant = score_marriage_election(variant_chart)

    assert control.value > variant.value
    assert any("Deal-breaker: Venus retrograde" in tag for tag in variant.tags)


def test_legal_mercury_retrograde_never_beats_direct_control():
    control_chart = base_legal_chart()
    control = score_legal_election(control_chart, options={"legal_action": "filing"})

    variant_chart = clone_chart(control_chart)
    set_planet(variant_chart, "Mercury", retrograde=True)
    variant = score_legal_election(variant_chart, options={"legal_action": "filing"})

    assert control.value > variant.value
    assert any("Mercury retrograde" in tag for tag in variant.tags)
