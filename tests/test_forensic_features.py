from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.forensic.features import extract_features
from backend.forensic.engine import evaluate


def test_extract_features_uses_full_aspect_list_when_available():
    dashboard = {
        "planets": [
            {"planet": "Moon", "longitude": 10.0, "house": 1, "sign": "Aries"},
            {"planet": "Mercury", "longitude": 20.0, "house": 2, "sign": "Aries"},
            {"planet": "Neptune", "longitude": 200.0, "house": 8, "sign": "Libra"},
        ],
        "top_aspects": [],
        "tightest_aspect": None,
        "all_aspects": [
            {
                "planet1": "Mercury",
                "planet2": "Neptune",
                "aspect": "Square",
                "applying": True,
                "orb": 1.8,
            }
        ],
    }

    features = extract_features(dashboard)
    aspects = features.get("aspects") or {}
    assert "Mercury_to_Neptune" in aspects
    assert aspects["Mercury_to_Neptune"]["type"] == "square"


def test_extract_features_creates_bidirectional_aspect_aliases():
    dashboard = {
        "planets": [
            {"planet": "Moon", "longitude": 10.0, "house": 1, "sign": "Aries"},
            {"planet": "Mercury", "longitude": 20.0, "house": 2, "sign": "Aries"},
            {"planet": "Neptune", "longitude": 200.0, "house": 8, "sign": "Libra"},
        ],
        "all_aspects": [
            {
                "planet1": "Mercury",
                "planet2": "Neptune",
                "aspect": "Conjunction",
                "applying": False,
                "orb": 0.5,
            }
        ],
    }

    features = extract_features(dashboard)
    aspects = features.get("aspects") or {}
    assert "Mercury_to_Neptune" in aspects
    assert "Neptune_to_Mercury" in aspects
    assert aspects["Mercury_to_Neptune"]["type"] == aspects["Neptune_to_Mercury"]["type"]


def test_extract_features_accepts_precise_aspect_phase_as_applying():
    dashboard = {
        "planets": [
            {"planet": "Mercury", "longitude": 20.0, "house": 2, "sign": "Aries"},
            {"planet": "Neptune", "longitude": 200.0, "house": 8, "sign": "Libra"},
        ],
        "all_aspects": [
            {
                "planet1": "Mercury",
                "planet2": "Neptune",
                "aspect": "Square",
                "phase": "applying",
                "orb": 1.8,
            }
        ],
    }

    features = extract_features(dashboard)
    aspects = features.get("aspects") or {}
    assert aspects["Mercury_to_Neptune"]["applying"] is True


def test_extract_features_preserves_asteroids_and_angles_for_forensic_auxiliary_rules():
    dashboard = {
        "planets": [
            {"planet": "Moon", "longitude": 75.0, "house": 1, "sign": "Gemini"},
        ],
        "house_cusps": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        "asteroids": {
            "items": [
                {
                    "name": "Juno",
                    "number": 3,
                    "tier": "major",
                    "longitude": 180.25,
                    "house": 7,
                    "sign": "Libra",
                    "speed": 0.1,
                }
            ]
        },
    }

    features = extract_features(dashboard)

    assert features["asteroids"]["Juno"]["house"] == 7
    assert features["asteroids"]["Juno"]["degree_in_sign"] == 0.25
    assert features["angles"]["Descendant"]["longitude"] == 180.0


def test_rule_path_with_north_node_space_resolves():
    features = {
        "aspects": {
            "North Node_to_Neptune": {"type": "conjunction"},
        }
    }
    rules = [
        {
            "id": "node_rule",
            "title": "Node rule",
            "category": "Deception",
            "condition": {
                "any": [
                    {"aspects.North Node_to_Neptune.type": ["conjunction", "square"]},
                ]
            },
        }
    ]

    findings = evaluate(features, rules)
    assert len(findings) == 1
    assert findings[0]["id"] == "node_rule"
