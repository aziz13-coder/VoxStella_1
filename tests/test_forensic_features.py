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
