from __future__ import annotations

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.election_models.business import score_business_election


def test_business_missing_longitudes_skip_moon_rules():
    chart = {
        "house_cusps": [i * 30.0 for i in range(12)],
        "planets": {
            "Moon": {
                "planet": "Moon",
                "longitude": None,
                "house": None,
            },
            "Sun": {
                "planet": "Sun",
                "longitude": "",
                "house": None,
            },
        },
    }

    result = score_business_election(chart)
    assert all("Moon waxing" not in tag for tag in result.tags)
