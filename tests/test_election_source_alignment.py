from __future__ import annotations

"""Regression cases for rules reconciled against the repository sources.

Primary texts:
  * horary_knowledge/desktop_books_text/
    Bonatti_on_Elections_Treatise_7_of_Guido_Bonattis_Book_of_Astronomy_...
  * horary_knowledge/desktop_books_text/
    631070497-Jean-Baptiste-Morin-Astrologia-Gallica-book-26.txt

Recovered-reference behavior is covered in the dedicated Marriage Beta,
Business Beta, Estate, and Lunar Fertility contract suites.
"""

import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.battle import score_battle_election
from backend.election_models.business import score_business_election
from backend.election_models.contract import score_contract_election
from backend.election_models.haircut import score_haircut_election
from backend.election_models.journey import score_journey_election
from backend.election_models.legal import score_legal_election
from backend.election_models.surgery import score_surgery_election
from tests.election_stress_utils import (
    base_battle_chart,
    base_business_chart,
    base_contract_chart,
    base_journey_chart,
    base_legal_chart,
    base_surgery_chart,
    clone_chart,
    set_aspects,
    set_planet,
    set_whole_sign_asc,
)


def _set_directed_phase(chart: dict, *, waxing: bool) -> dict:
    """Keep the Moon fixed and place the Sun 60 degrees behind/ahead."""
    moon_lon = float(chart["planets"]["Moon"]["longitude"])
    sun_lon = (moon_lon - 60.0) % 360.0 if waxing else (moon_lon + 60.0) % 360.0
    set_planet(chart, "Sun", longitude=sun_lon)
    return chart


def test_waxing_phase_uses_directed_elongation_across_shared_models():
    cases = (
        (score_business_election, base_business_chart(), {}),
        (score_contract_election, base_contract_chart(), {}),
        (score_journey_election, base_journey_chart(), {}),
    )

    for scorer, base_chart, options in cases:
        waxing = scorer(_set_directed_phase(clone_chart(base_chart), waxing=True), options=options)
        waning = scorer(_set_directed_phase(clone_chart(base_chart), waxing=False), options=options)

        assert "Moon waxing" in waxing.tags
        assert "Moon waning" in waning.tags
        assert "Moon waning" not in waxing.tags
        assert "Moon waxing" not in waning.tags


def test_contract_minimum_direct_days_uses_exact_station_age_input():
    chart = base_contract_chart()
    too_early = score_contract_election(
        chart,
        options={
            "contract_mode": "new",
            "min_mercury_direct_days": 3,
            "mercury_direct_station_age_days": 1.25,
        },
    )
    mature = score_contract_election(
        chart,
        options={
            "contract_mode": "new",
            "min_mercury_direct_days": 3,
            "mercury_direct_station_age_days": 5.0,
        },
    )

    assert mature.value > too_early.value
    assert any("Excluded: Mercury only 1.25d past direct station" in tag for tag in too_early.tags)
    assert "Mercury direct for 5.00d" in mature.tags


def _haircut_chart(moon_lon: float, moon_sign: str) -> dict:
    chart = base_surgery_chart()
    set_planet(chart, "Moon", longitude=moon_lon, sign=moon_sign, house=6)
    set_planet(chart, "Sun", longitude=(moon_lon - 60.0) % 360.0)
    chart["planetary_aspects_precise"] = []
    return chart


def test_bonatti_haircut_sign_rule_and_aries_shaving_exception():
    virgo = score_haircut_election(_haircut_chart(165.0, "Virgo"), options={"haircut_type": "trim"})
    gemini = score_haircut_election(_haircut_chart(75.0, "Gemini"), options={"haircut_type": "trim"})
    aries_chart = _haircut_chart(15.0, "Aries")
    aries_trim = score_haircut_election(aries_chart, options={"haircut_type": "trim"})
    aries_shave = score_haircut_election(aries_chart, options={"haircut_type": "shave"})

    assert virgo.value > gemini.value
    assert any("Common-sign Moon (Virgo)" in tag for tag in virgo.tags)
    assert any("Bonatti exception: Moon in Gemini" in tag for tag in gemini.tags)
    assert aries_trim.value > -90.0
    assert aries_shave.value <= -100.0
    assert any("complete shaving with Moon in Aries" in tag for tag in aries_shave.tags)


def test_bonatti_surgery_primary_rule_prefers_increasing_light():
    waxing_chart = _set_directed_phase(base_surgery_chart(), waxing=True)
    waning_chart = _set_directed_phase(base_surgery_chart(), waxing=False)

    waxing = score_surgery_election(waxing_chart, options={"procedure": "diagnostic"})
    waning = score_surgery_election(waning_chart, options={"procedure": "diagnostic"})

    assert waxing.value > waning.value
    assert "Moon increasing in light (Bonatti surgery support)" in waxing.tags
    assert "Moon decreasing in light (Bonatti surgery caution)" in waning.tags


def test_morin_battle_does_not_prohibit_an_unrelated_eighth_house_planet():
    chart = base_battle_chart()
    set_planet(chart, "Mercury", house=8)

    score = score_battle_election(chart, options={"action_type": "attack"})

    assert score.value > -9000.0
    assert not any("Ascendant ruler applying to stronger 7th ruler" in tag for tag in score.tags)


def test_bonatti_legal_judge_support_is_comparative():
    claimant_chart = base_legal_chart()
    set_whole_sign_asc(claimant_chart, 0.0)  # L1 Mars, L7 Venus, L10 Saturn.
    set_aspects(
        claimant_chart,
        [{"planet1": "Saturn", "planet2": "Mars", "aspect": "Trine", "phase": "applying"}],
    )
    opponent_chart = clone_chart(claimant_chart)
    set_aspects(
        opponent_chart,
        [{"planet1": "Saturn", "planet2": "Venus", "aspect": "Trine", "phase": "applying"}],
    )

    claimant = score_legal_election(claimant_chart, options={"legal_action": "filing"})
    opponent = score_legal_election(opponent_chart, options={"legal_action": "filing"})

    assert claimant.value > opponent.value
    assert any("Judge ruler favors claimant over opponent" in tag for tag in claimant.tags)
    assert any("Judge ruler favors opponent over claimant" in tag for tag in opponent.tags)
