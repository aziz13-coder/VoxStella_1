from __future__ import annotations

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.viral_content import score_viral_content_election


def test_viral_content_penalties_lower_score():
    chart = {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Saturn": {
                "planet": "Saturn",
                "longitude": "210°30",
                "house": 11,
                "retrograde": True,
            },
            "Mercury": {
                "planet": "Mercury",
                "longitude": "180°00",
                "retrograde": True,
                "house": 6,
            },
            "Moon": {
                "planet": "Moon",
                "longitude": "95°15",
                "house": 12,
                "speed": 10.5,
            },
        },
        "considerations": {"moon_void": False},
        "moon_state": {},
    }

    score = score_viral_content_election(chart)
    assert score.value < 0.0
