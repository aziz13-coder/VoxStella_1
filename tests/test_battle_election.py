from __future__ import annotations

import copy
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.battle import score_battle_election


def _base_chart() -> dict:
    chart = {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Sun": {
                "planet": "Sun",
                "longitude": 280.0,
                "sign": "Capricorn",
                "house": 10,
                "retrograde": False,
                "speed": 0.98,
            },
            "Moon": {
                "planet": "Moon",
                "longitude": 12.0,
                "sign": "Aries",
                "house": 1,
                "retrograde": False,
                "speed": 13.5,
            },
            "Mars": {
                "planet": "Mars",
                "longitude": 15.0,
                "sign": "Aries",
                "house": 1,
                "retrograde": False,
                "speed": 0.7,
            },
            "Jupiter": {
                "planet": "Jupiter",
                "longitude": 50.0,
                "sign": "Taurus",
                "house": 2,
                "retrograde": False,
                "speed": 0.2,
            },
            "Saturn": {
                "planet": "Saturn",
                "longitude": 200.0,
                "sign": "Libra",
                "house": 7,
                "retrograde": False,
                "speed": 0.1,
            },
            "Venus": {
                "planet": "Venus",
                "longitude": 45.0,
                "sign": "Taurus",
                "house": 2,
                "retrograde": False,
                "speed": 1.2,
            },
            "Mercury": {
                "planet": "Mercury",
                "longitude": 290.0,
                "sign": "Capricorn",
                "house": 10,
                "retrograde": False,
                "speed": 1.5,
            },
            "North Node": {
                "planet": "North Node",
                "longitude": 120.0,
                "sign": "Leo",
                "house": 5,
                "retrograde": False,
            },
        },
        "planetary_aspects_precise": [],
        "moon_next_aspect": {"planet": "Jupiter", "aspect": "Trine", "phase": "applying"},
        "considerations": {"moon_void": False},
        "moon_state": {},
    }
    return chart


def _chart_with_updates(**updates) -> dict:
    chart = _base_chart()
    for key, value in updates.items():
        if key == "planets":
            for pname, fields in value.items():
                chart["planets"].setdefault(pname, {}).update(fields)
        else:
            chart[key] = value
    return chart


def test_battle_prohibits_void_moon():
    chart = _chart_with_updates(moon_state={"void_of_course": True})
    result = score_battle_election(chart)
    assert result.value <= -9000
    assert any("Prohibition" in tag for tag in result.tags)


def test_battle_prohibits_mars_retrograde_for_attack():
    chart = _chart_with_updates(planets={"Mars": {"retrograde": True}})
    result = score_battle_election(chart, options={"action_type": "attack"})
    assert result.value <= -9000
    assert any("Mars retrograde" in tag for tag in result.tags)


def test_battle_allows_mars_retrograde_for_defense():
    chart = _chart_with_updates(planets={"Mars": {"retrograde": True}})
    result = score_battle_election(chart, options={"action_type": "defense"})
    assert result.value > 0
    assert all("Prohibition" not in tag for tag in result.tags)


def test_attack_orientation_bonus_exceeds_defense():
    chart = _base_chart()
    attack = score_battle_election(copy.deepcopy(chart), options={"action_type": "attack"})
    defense = score_battle_election(copy.deepcopy(chart), options={"action_type": "defense"})
    assert attack.value > defense.value


def test_defense_orientation_bonus_when_mars_occidental():
    chart = _chart_with_updates(
        planets={
            "Mars": {
                "longitude": 120.0,
                "sign": "Leo",
                "house": 5,
            }
        }
    )
    defense = score_battle_election(copy.deepcopy(chart), options={"action_type": "defense"})
    attack = score_battle_election(copy.deepcopy(chart), options={"action_type": "attack"})
    assert defense.value > attack.value


def test_battle_nodes_alone_do_not_trigger_prohibition():
    chart = _chart_with_updates(
        planets={
            "South Node": {
                "planet": "South Node",
                "longitude": 210.0,
                "sign": "Scorpio",
                "house": 8,
            }
        }
    )
    result = score_battle_election(chart)
    assert result.value > -9000
    assert all("Prohibition" not in tag for tag in result.tags)


def test_battle_planetary_timing_boosts_attack_on_mars_day_hour():
    chart = _base_chart()
    base = score_battle_election(copy.deepcopy(chart), options={"action_type": "attack"})
    timed = score_battle_election(
        copy.deepcopy(chart),
        options={
            "action_type": "attack",
            "include_traditional_timing": True,
            "day_ruler": "Mars",
            "hour_ruler": "Mars",
        },
    )
    assert timed.value > base.value
    assert any("Planetary day ruler Mars" in tag or "Planetary hour ruler Mars" in tag for tag in timed.tags)


def test_battle_planetary_timing_supports_defense_on_saturn_day_hour():
    chart = _base_chart()
    base = score_battle_election(copy.deepcopy(chart), options={"action_type": "defense"})
    timed = score_battle_election(
        copy.deepcopy(chart),
        options={
            "action_type": "defense",
            "include_traditional_timing": True,
            "day_ruler": "Saturn",
            "hour_ruler": "Saturn",
        },
    )
    assert timed.value > base.value
    assert any("Planetary day ruler Saturn" in tag or "Planetary hour ruler Saturn" in tag for tag in timed.tags)


def test_battle_planetary_timing_penalizes_offense_on_venus_day_hour():
    chart = _base_chart()
    base = score_battle_election(copy.deepcopy(chart), options={"action_type": "attack"})
    timed = score_battle_election(
        copy.deepcopy(chart),
        options={
            "action_type": "attack",
            "include_traditional_timing": True,
            "day_ruler": "Venus",
            "hour_ruler": "Venus",
        },
    )
    assert timed.value < base.value
    assert any("weakens timing" in tag for tag in timed.tags)
