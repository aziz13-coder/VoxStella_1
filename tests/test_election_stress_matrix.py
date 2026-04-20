from __future__ import annotations

import copy
from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.battle import score_battle_election
from backend.election_models.beautification import score_beautification_election
from backend.election_models.business import score_business_election
from backend.election_models.conception import score_conception_election
from backend.election_models.contract import score_contract_election
from backend.election_models.haircut import score_haircut_election
from backend.election_models.journey import score_journey_election
from backend.election_models.legal import score_legal_election
from backend.election_models.marriage import score_marriage_election
from backend.election_models.surgery import score_surgery_election
from backend.election_models.viral_content import score_viral_content_election


def _whole_sign_cusps(asc_lon: float) -> list[float]:
    return [float((asc_lon + 30.0 * idx) % 360.0) for idx in range(12)]


def _haircut_chart(moon_sign: str, moon_lon: float) -> dict:
    return {
        "house_cusps": _whole_sign_cusps(0.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 20.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": moon_lon, "sign": moon_sign, "house": 3, "retrograde": False, "speed": 12.8},
            "Venus": {"planet": "Venus", "longitude": 50.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _journey_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(180.0),  # Libra rising, Sagittarius on the 3rd
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 15.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 100.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 13.4},
            "Mercury": {"planet": "Mercury", "longitude": 25.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 195.0, "sign": "Libra", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 150.0, "sign": "Virgo", "house": 12, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 255.0, "sign": "Sagittarius", "house": 1, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 70.0, "sign": "Gemini", "house": 9, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _business_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(270.0),  # Capricorn rising
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 1, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 5, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 165.0, "sign": "Virgo", "house": 9, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 295.0, "sign": "Capricorn", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 8, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 3, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 315.0, "sign": "Aquarius", "house": 2, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _contract_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(210.0),  # Scorpio rising, Taurus on the 7th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 105.0, "sign": "Cancer", "house": 9, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 8, "retrograde": False, "speed": 1.1},
            "Venus": {"planet": "Venus", "longitude": 45.0, "sign": "Taurus", "house": 7, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 175.0, "sign": "Virgo", "house": 11, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 5, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 275.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Trine", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Venus", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _marriage_good_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(210.0),  # Scorpio rising, Taurus on the 7th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 7, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 285.0, "sign": "Capricorn", "house": 3, "retrograde": False, "speed": 1.1},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 6, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 165.0, "sign": "Virgo", "house": 11, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 5, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 245.0, "sign": "Sagittarius", "house": 2, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _marriage_bad_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(120.0),  # Leo rising, Aquarius on the 7th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 6, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 220.0, "sign": "Scorpio", "house": 4, "retrograde": False, "speed": 11.0},
            "Mercury": {"planet": "Mercury", "longitude": 300.0, "sign": "Aquarius", "house": 7, "retrograde": False, "speed": 1.1},
            "Venus": {"planet": "Venus", "longitude": 210.0, "sign": "Scorpio", "house": 4, "retrograde": True, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 1, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 85.0, "sign": "Gemini", "house": 11, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 300.0, "sign": "Aquarius", "house": 7, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Moon", "planet2": "Saturn", "aspect": "Square", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Saturn", "aspect": "Square", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _surgery_chart(moon_sign: str, moon_lon: float, moon_house: int) -> dict:
    return {
        "house_cusps": _whole_sign_cusps(0.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": moon_lon, "sign": moon_sign, "house": moon_house, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 285.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 295.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 70.0, "sign": "Gemini", "house": 3, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _legal_good_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(60.0),  # Gemini rising, Pisces MC
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 260.0, "sign": "Sagittarius", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 195.0, "sign": "Libra", "house": 5, "retrograde": False, "speed": 13.3},
            "Mercury": {"planet": "Mercury", "longitude": 165.0, "sign": "Virgo", "house": 4, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 80.0, "sign": "Gemini", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 345.0, "sign": "Pisces", "house": 10, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 350.0, "sign": "Pisces", "house": 10, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 325.0, "sign": "Aquarius", "house": 9, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Opposition", "phase": "separating"},
            {"planet1": "Mercury", "planet2": "Venus", "aspect": "Square", "phase": "separating"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _legal_bad_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(60.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 260.0, "sign": "Sagittarius", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 270.0, "sign": "Capricorn", "house": 8, "retrograde": False, "speed": 10.5},
            "Mercury": {"planet": "Mercury", "longitude": 350.0, "sign": "Pisces", "house": 10, "retrograde": True, "speed": -0.3},
            "Venus": {"planet": "Venus", "longitude": 150.0, "sign": "Virgo", "house": 4, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 350.0, "sign": "Pisces", "house": 10, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 5.0, "sign": "Aries", "house": 12, "retrograde": True, "speed": -0.1},
            "Saturn": {"planet": "Saturn", "longitude": 165.0, "sign": "Virgo", "house": 4, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Mercury", "planet2": "Mars", "aspect": "Conjunction", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Mars", "aspect": "Square", "phase": "applying"},
        "considerations": {"moon_void": True},
        "moon_state": {"void_of_course": True},
    }


def _beautification_chart(moon_sign: str, moon_lon: float) -> dict:
    return {
        "house_cusps": _whole_sign_cusps(30.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 35.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": moon_lon, "sign": moon_sign, "house": 4, "retrograde": False, "speed": 13.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Taurus", "house": 1, "retrograde": False, "speed": 1.0},
            "Jupiter": {"planet": "Jupiter", "longitude": 195.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.2},
            "Mars": {"planet": "Mars", "longitude": 300.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.6},
            "Saturn": {"planet": "Saturn", "longitude": 260.0, "sign": "Sagittarius", "house": 9, "retrograde": False, "speed": 0.1},
            "Mercury": {"planet": "Mercury", "longitude": 40.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.3},
        },
        "planetary_aspects": [
            {"planet1": "Moon", "planet2": "Venus", "aspect": "Trine", "phase": "applying"},
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        ],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _conception_good_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(90.0),  # Cancer rising, Scorpio 5th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 260.0, "sign": "Sagittarius", "house": 6, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 350.0, "sign": "Pisces", "house": 9, "retrograde": False, "speed": 13.5},
            "Venus": {"planet": "Venus", "longitude": 50.0, "sign": "Taurus", "house": 11, "retrograde": False, "speed": 1.0},
            "Jupiter": {"planet": "Jupiter", "longitude": 105.0, "sign": "Cancer", "house": 1, "retrograde": False, "speed": 0.2},
            "Mars": {"planet": "Mars", "longitude": 285.0, "sign": "Capricorn", "house": 7, "retrograde": False, "speed": 0.6},
            "Saturn": {"planet": "Saturn", "longitude": 325.0, "sign": "Aquarius", "house": 8, "retrograde": False, "speed": 0.1},
            "Mercury": {"planet": "Mercury", "longitude": 165.0, "sign": "Virgo", "house": 3, "retrograde": False, "speed": 1.2},
        },
        "planetary_aspects": [
            {"planet1": "Moon", "planet2": "Venus", "aspect": "Sextile", "phase": "Applying"},
            {"planet1": "Moon", "planet2": "Jupiter", "aspect": "Trine", "phase": "Applying"},
            {"planet1": "Mars", "planet2": "Moon", "aspect": "Sextile", "phase": "Applying"},
        ],
    }


def _conception_bad_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(90.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 350.0, "sign": "Pisces", "house": 9, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 270.0, "sign": "Capricorn", "house": 8, "retrograde": False, "speed": 10.5},
            "Venus": {"planet": "Venus", "longitude": 220.0, "sign": "Scorpio", "house": 5, "retrograde": True, "speed": -0.2},
            "Jupiter": {"planet": "Jupiter", "longitude": 220.0, "sign": "Scorpio", "house": 5, "retrograde": True, "speed": -0.1},
            "Mars": {"planet": "Mars", "longitude": 210.0, "sign": "Libra", "house": 5, "retrograde": False, "speed": 0.6},
            "Saturn": {"planet": "Saturn", "longitude": 100.0, "sign": "Cancer", "house": 1, "retrograde": False, "speed": 0.1},
            "Mercury": {"planet": "Mercury", "longitude": 330.0, "sign": "Pisces", "house": 9, "retrograde": False, "speed": 1.2},
        },
        "planetary_aspects": [
            {"planet1": "Moon", "planet2": "Mars", "aspect": "Square", "phase": "Applying"},
            {"planet1": "Sun", "planet2": "Moon", "aspect": "Square", "phase": "Applying"},
        ],
    }


def _viral_good_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(300.0),  # Aquarius rising, Sagittarius 11th
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 20.0, "sign": "Aries", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 195.0, "sign": "Libra", "house": 9, "retrograde": False, "speed": 13.2},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 5, "retrograde": False, "speed": 1.3},
            "Venus": {"planet": "Venus", "longitude": 315.0, "sign": "Aquarius", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 110.0, "sign": "Cancer", "house": 6, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 250.0, "sign": "Sagittarius", "house": 11, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 340.0, "sign": "Pisces", "house": 2, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects": [
            {"planet1": "Mercury", "planet2": "Jupiter", "aspect": "Opposition", "phase": "separating"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _viral_bad_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(300.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 20.0, "sign": "Aries", "house": 3, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 285.0, "sign": "Capricorn", "house": 12, "retrograde": False, "speed": 10.5},
            "Mercury": {"planet": "Mercury", "longitude": 180.0, "sign": "Libra", "house": 6, "retrograde": True, "speed": -0.2},
            "Venus": {"planet": "Venus", "longitude": 15.0, "sign": "Aries", "house": 3, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 300.0, "sign": "Aquarius", "house": 1, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 5.0, "sign": "Aries", "house": 3, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 250.0, "sign": "Sagittarius", "house": 11, "retrograde": True, "speed": -0.1},
        },
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _battle_chart() -> dict:
    return {
        "house_cusps": _whole_sign_cusps(0.0),
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 0.98},
            "Moon": {"planet": "Moon", "longitude": 12.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 13.5},
            "Mars": {"planet": "Mars", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 0.7},
            "Jupiter": {"planet": "Jupiter", "longitude": 50.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 200.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.1},
            "Venus": {"planet": "Venus", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.2},
            "Mercury": {"planet": "Mercury", "longitude": 290.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.5},
            "North Node": {"planet": "North Node", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False},
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def test_haircut_prefers_common_signs_except_gemini_from_bonatti():
    virgo = score_haircut_election(_haircut_chart("Virgo", 165.0), options={"hair_goal": "growth"})
    gemini = score_haircut_election(_haircut_chart("Gemini", 75.0), options={"hair_goal": "growth"})

    assert virgo.value > gemini.value
    assert any("Virgo" in tag for tag in virgo.tags)
    assert any("Bonatti exception" in tag for tag in gemini.tags)


def test_short_journey_prefers_part_of_fortune_support():
    good_chart = _journey_chart()
    good_chart["arabic_parts"] = {"fortune": {"lon": 250.0, "house": 3, "ruler": "Jupiter"}}

    bad_chart = _journey_chart()
    bad_chart["arabic_parts"] = {"fortune": {"lon": 100.0, "house": 8, "ruler": "Jupiter"}}

    good = score_journey_election(good_chart, options={"journey_type": "short"})
    bad = score_journey_election(bad_chart, options={"journey_type": "short"})

    assert good.value > bad.value
    assert any("Part of Fortune in 3rd" in tag for tag in good.tags)
    assert any("Part of Fortune in 8th" in tag for tag in bad.tags)


def test_business_prefers_fortune_in_gain_houses():
    good_chart = _business_chart()
    good_chart["arabic_parts"] = {"fortune": {"lon": 350.0, "house": 10}}

    bad_chart = _business_chart()
    bad_chart["arabic_parts"] = {"fortune": {"lon": 220.0, "house": 8}}

    good = score_business_election(good_chart)
    bad = score_business_election(bad_chart)

    assert good.value > bad.value
    assert any("Part of Fortune in 1/2/10/11" in tag for tag in good.tags)


def test_contract_penalizes_new_deals_under_mercury_retrograde():
    good = score_contract_election(_contract_chart(), options={"prefer_fixed_asc": True, "contract_mode": "new"})

    bad_chart = copy.deepcopy(_contract_chart())
    bad_chart["planets"]["Mercury"]["retrograde"] = True
    bad_chart["considerations"]["moon_void"] = True
    bad_chart["moon_state"]["void_of_course"] = True
    bad = score_contract_election(bad_chart, options={"prefer_fixed_asc": True, "contract_mode": "new"})

    assert good.value > bad.value
    assert any("Mercury direct" in tag for tag in good.tags)
    assert any("Deal-breaker: Mercury retrograde" in tag for tag in bad.tags)


def test_marriage_prefers_fixed_taurus_frame_over_aquarius_scorpio_mix():
    good = score_marriage_election(_marriage_good_chart())
    bad = score_marriage_election(_marriage_bad_chart())

    assert good.value > bad.value
    assert any("Preferred fixed 7th (Taurus)" in tag for tag in good.tags)
    assert any("Unfavored 7th sign (Aquarius)" in tag for tag in bad.tags)


def test_surgery_prefers_fixed_moon_for_cutting():
    fixed = score_surgery_election(
        _surgery_chart("Taurus", 45.0, 2),
        options={"procedure": "cutting", "surgery_sign": "Aries"},
    )
    mutable = score_surgery_election(
        _surgery_chart("Gemini", 75.0, 3),
        options={"procedure": "cutting", "surgery_sign": "Aries"},
    )

    assert fixed.value > mutable.value
    assert any("Moon in fixed sign (surgery stability)" in tag for tag in fixed.tags)


def test_legal_prefers_judicial_favor_over_hostile_court_signature():
    good = score_legal_election(_legal_good_chart(), options={"legal_action": "filing"})
    bad = score_legal_election(_legal_bad_chart(), options={"legal_action": "filing"})

    assert good.value > bad.value
    assert any("Benefic in 10th" in tag for tag in good.tags)
    assert any("Malefic in 10th" in tag for tag in bad.tags)


def test_beautification_penalizes_forbidden_moon_signs():
    good = score_beautification_election(
        _beautification_chart("Cancer", 85.0),
        options={"body_parts": ["cheeks"], "procedure_type": "fillers"},
    )
    bad = score_beautification_election(
        _beautification_chart("Libra", 190.0),
        options={"body_parts": ["cheeks"], "procedure_type": "fillers"},
    )

    assert good.value > bad.value
    assert any("Moon in forbidden sign" in tag for tag in bad.tags)


def test_conception_prefers_fertile_supportive_frame_over_afflicted_frame():
    good = score_conception_election(_conception_good_chart())
    bad = score_conception_election(_conception_bad_chart())

    assert good.value > bad.value
    assert any("Moon in fertile sign" in tag for tag in good.tags)
    assert any("Critical:" in tag for tag in bad.tags)


def test_viral_content_prefers_social_benefics_and_direct_mercury():
    good = score_viral_content_election(_viral_good_chart())
    bad = score_viral_content_election(_viral_bad_chart())

    assert good.value > bad.value
    assert any("Benefic in 11th" in tag for tag in good.tags)
    assert any("Mercury retrograde" in tag for tag in bad.tags)


def test_battle_prefers_direct_mars_for_attack():
    good = score_battle_election(_battle_chart(), options={"action_type": "attack"})

    bad_chart = copy.deepcopy(_battle_chart())
    bad_chart["planets"]["Mars"]["retrograde"] = True
    bad = score_battle_election(bad_chart, options={"action_type": "attack"})

    assert good.value > bad.value
    assert any("Mars retrograde" in tag for tag in bad.tags)
