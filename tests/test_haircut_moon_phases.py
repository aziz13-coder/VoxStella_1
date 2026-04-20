from __future__ import annotations

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.haircut import score_haircut_election


def _chart(moon_lon: float, sun_lon: float) -> dict:
    return {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Sun": {
                "planet": "Sun",
                "longitude": sun_lon,
                "sign": "Aries",
                "house": 1,
                "retrograde": False,
                "speed": 0.98,
            },
            "Moon": {
                "planet": "Moon",
                "longitude": moon_lon,
                "sign": "Taurus",
                "house": 1,
                "retrograde": False,
                "speed": 12.5,
            },
            "Venus": {
                "planet": "Venus",
                "longitude": 50.0,
                "sign": "Taurus",
                "house": 2,
                "retrograde": False,
                "speed": 1.2,
            },
        },
        "planetary_aspects_precise": [],
        "considerations": {"moon_void": False},
        "moon_state": {},
    }


def test_haircut_waxing_bonus_when_moon_leads():
    chart = _chart(moon_lon=350.0, sun_lon=300.0)  # Moon ahead of Sun => waxing
    result = score_haircut_election(chart, options={"hair_goal": "growth"})

    assert any("Waxing Moon" in tag for tag in result.tags)
    assert all("Waning Moon" not in tag for tag in result.tags)


def test_haircut_waning_bonus_when_moon_trails():
    chart = _chart(moon_lon=100.0, sun_lon=150.0)  # Moon behind Sun => waning
    result = score_haircut_election(chart, options={"hair_goal": "lasting"})

    assert any("Waning Moon" in tag for tag in result.tags)
    assert all("Waxing Moon" not in tag for tag in result.tags)
