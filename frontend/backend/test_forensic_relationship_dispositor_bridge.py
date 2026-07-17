from pathlib import Path
import sys

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from forensic.engine import evaluate, load_knowledge
from forensic.features import extract_features


KNOWLEDGE_DIR = BACKEND_ROOT / "forensic" / "knowledge"


def _route_harm_bridge_dashboard():
    return {
        "house_rulers": {
            "1": "Moon",
            "3": "Mercury",
            "6": "Jupiter",
            "7": "Saturn",
            "8": "Saturn",
            "9": "Jupiter",
        },
        "planets": [
            {"planet": "Moon", "longitude": 157.8446, "sign": "Virgo", "house": 2},
            {"planet": "Mercury", "longitude": 143.2203, "sign": "Leo", "house": 2},
            {"planet": "Saturn", "longitude": 322.9548, "sign": "Aquarius", "house": 8},
            {"planet": "Mars", "longitude": 47.6786, "sign": "Taurus", "house": 10},
            {"planet": "Jupiter", "longitude": 8.7070, "sign": "Aries", "house": 9},
        ],
        "all_aspects": [
            {"planet1": "Mercury", "planet2": "Saturn", "aspect": "Opposition", "orb": 0.266},
            {"planet1": "Mercury", "planet2": "Mars", "aspect": "Square", "orb": 5.54},
        ],
    }


def test_extract_features_tracks_moon_dispositor_bridge_to_seventh_ruler():
    features = extract_features(_route_harm_bridge_dashboard())

    assert features["moon"]["sign"] == "Virgo"
    assert features["moon"]["dispositor"] == "Mercury"
    assert features["moon"]["dispositor_house"] == 2
    assert features["moon"]["dispositor_to_seventh_ruler_hard"] is True
    assert features["moon"]["dispositor_to_seventh_ruler_orb"] == pytest.approx(0.266)


def test_known_person_route_harm_rule_uses_moon_dispositor_bridge():
    features = extract_features(_route_harm_bridge_dashboard())
    findings = evaluate(features, load_knowledge(str(KNOWLEDGE_DIR)))
    finding_ids = {finding.get("id") for finding in findings}

    assert "known_person_route_harm_moon_dispositor_bridge" in finding_ids
