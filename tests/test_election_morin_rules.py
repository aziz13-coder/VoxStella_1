from __future__ import annotations

import copy
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.journey import score_journey_election
from backend.election_models.surgery import score_surgery_election


def _journey_base_chart() -> dict:
    return {
        "house_cusps": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 100.0, "sign": "Cancer", "house": 10, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 20.0, "sign": "Aries", "house": 7, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 195.0, "sign": "Libra", "house": 1, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 250.0, "sign": "Sagittarius", "house": 3, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 260.0, "sign": "Sagittarius", "house": 3, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 70.0, "sign": "Gemini", "house": 9, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def _surgery_base_chart() -> dict:
    return {
        "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 13.5},
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


def test_journey_prefers_cardinal_venus_asc_over_fixed_venus_asc():
    cardinal = _journey_base_chart()
    fixed = copy.deepcopy(cardinal)
    fixed["house_cusps"] = [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0]

    cardinal_score = score_journey_election(cardinal)
    fixed_score = score_journey_election(fixed)

    assert cardinal_score.value > fixed_score.value
    assert any("Cardinal Asc (movement)" in tag for tag in cardinal_score.tags)
    assert any("Fixed Asc (delays)" in tag for tag in fixed_score.tags)


def test_surgery_avoids_cutting_when_moon_rules_target_body_part():
    chart = _surgery_base_chart()
    chart["planets"]["Moon"].update({"sign": "Aries", "longitude": 10.0, "house": 1})

    score = score_surgery_election(chart, options={"surgery_sign": "Aries", "procedure": "cutting"})

    assert score.value <= -90.0
    assert any("Moon in Aries (target body sign)" in tag for tag in score.tags)
    assert any("Never timing contraindications" in tag for tag in score.tags)


def test_purging_prefers_pisces_moon_over_non_water_moon():
    pisces = _surgery_base_chart()
    pisces["planets"]["Moon"].update({"sign": "Pisces", "longitude": 350.0, "house": 11})

    aquarius = _surgery_base_chart()
    aquarius["planets"]["Moon"].update({"sign": "Aquarius", "longitude": 320.0, "house": 11})

    pisces_score = score_surgery_election(pisces, options={"procedure": "purging"})
    aquarius_score = score_surgery_election(aquarius, options={"procedure": "purging"})

    assert pisces_score.value > aquarius_score.value
    assert any("Purging: Moon in Scorpio/Pisces" in tag for tag in pisces_score.tags)
    assert all("Purging: Moon in Scorpio/Pisces" not in tag for tag in aquarius_score.tags)


def test_surgery_rule13_is_not_double_counted():
    chart = {
        "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        "planets": {
            "Sun": {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
            "Moon": {"planet": "Moon", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 13.5},
            "Mercury": {"planet": "Mercury", "longitude": 75.0, "sign": "Gemini", "house": 3, "retrograde": False, "speed": 1.2},
            "Venus": {"planet": "Venus", "longitude": 45.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.0},
            "Mars": {"planet": "Mars", "longitude": 120.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 0.6},
            "Jupiter": {"planet": "Jupiter", "longitude": 15.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 0.2},
            "Saturn": {"planet": "Saturn", "longitude": 300.0, "sign": "Aquarius", "house": 11, "retrograde": False, "speed": 0.1},
        },
        "planetary_aspects_precise": [
            {"planet1": "Moon", "planet2": "Jupiter", "aspect": "Conjunction", "phase": "applying"},
        ],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Conjunction", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }

    score = score_surgery_election(chart, options={"procedure": "diagnostic"})

    assert score.value == 6.45
    assert score.tags.count("Rule13: Moon conj Jupiter/Saturn while waxing (good)") == 1
