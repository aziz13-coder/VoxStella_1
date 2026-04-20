from __future__ import annotations

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.beautification import score_beautification_election


def _base_chart() -> dict:
    return {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Sun": {
                "planet": "Sun",
                "longitude": 35.0,
                "sign": "Taurus",
                "house": 2,
            },
            "Moon": {
                "planet": "Moon",
                "longitude": 85.0,
                "sign": "Cancer",
                "house": 4,
                "speed": 13.2,
            },
            "Venus": {
                "planet": "Venus",
                "longitude": 15.0,
                "sign": "Taurus",
                "house": 1,
                "retrograde": False,
            },
            "Jupiter": {
                "planet": "Jupiter",
                "longitude": 195.0,
                "sign": "Libra",
                "house": 7,
            },
            "Mars": {
                "planet": "Mars",
                "longitude": 300.0,
                "sign": "Capricorn",
                "house": 10,
                "retrograde": False,
            },
            "Saturn": {
                "planet": "Saturn",
                "longitude": 260.0,
                "sign": "Sagittarius",
                "house": 9,
                "retrograde": False,
            },
            "Mercury": {
                "planet": "Mercury",
                "longitude": 40.0,
                "sign": "Taurus",
                "house": 2,
                "retrograde": False,
            },
        },
        "planetary_aspects": [
            {"planet1": "Moon", "planet2": "Venus", "aspect": "Trine", "phase": "applying"},
            {"planet1": "Venus", "planet2": "Jupiter", "aspect": "Sextile", "phase": "applying"},
        ],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def test_beautification_transit_positive():
    chart = _base_chart()
    result = score_beautification_election(
        chart,
        options={
            "body_parts": ["cheeks", "lips"],
            "procedure_type": "fillers",
        },
    )
    assert result.value > 60.0
    assert any("Venus dignified" in tag for tag in result.tags)


def test_beautification_forbidden_moon_penalty():
    chart = _base_chart()
    chart["planets"]["Moon"]["sign"] = "Libra"
    chart["planets"]["Moon"]["longitude"] = 190.0
    bad = score_beautification_election(
        chart,
        options={
            "body_parts": ["cheeks"],
            "procedure_type": "fillers",
        },
    )
    assert bad.value < 40.0
    assert any("Moon in forbidden sign" in tag for tag in bad.tags)


def test_beautification_with_natal_bonus():
    chart = _base_chart()
    natal = {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Venus": {"planet": "Venus", "longitude": 45.0, "sign": "Taurus"},
            "Mars": {"planet": "Mars", "longitude": 15.0, "sign": "Aries"},
        },
    }
    natal_hits = [
        {"transiting": "Venus", "aspect": "Trine", "target_label": "Asc"},
        {"transiting": "Mars", "aspect": "Square", "target_label": "Venus"},
    ]
    scored = score_beautification_election(
        chart,
        natal_hits=natal_hits,
        options={
            "body_parts": ["cheeks"],
            "procedure_type": "fillers",
            "natal_cd": natal,
        },
    )
    assert any("Natal" in tag for tag in scored.tags)
