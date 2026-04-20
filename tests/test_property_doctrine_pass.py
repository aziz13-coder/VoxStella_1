from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.category_rules import get_category_rules  # noqa: E402
from backend.horary_engine.property_doctrine import (  # noqa: E402
    analyze_property_question_text,
    derive_property_category_rules,
    evaluate_property_advisability_snapshot,
)
from backend.taxonomy import Category  # noqa: E402


def test_property_doctrine_splits_acquisition_vs_advisability_vs_condition():
    advise = analyze_property_question_text("Should I invest in this house?", "QUALITY")
    acquire = analyze_property_question_text("Will I buy this house?", "OCCURRENCE")
    sale = analyze_property_question_text("Will we sell the house soon?", "OCCURRENCE")
    condition = analyze_property_question_text("Is this house good?", "QUALITY")
    occupancy = analyze_property_question_text("When will my tenant move out?", "OCCURRENCE")
    eviction = analyze_property_question_text("Will I get evicted/loose my home?", "OCCURRENCE")

    assert advise["family"] == "advisability_profit"
    assert advise["relevant_houses"] == [1, 4, 7, 10]
    assert acquire["family"] == "acquisition"
    assert acquire["relevant_houses"] == [1, 4, 7]
    assert sale["family"] == "sale"
    assert sale["relevant_houses"] == [1, 4, 7]
    assert condition["family"] == "condition"
    assert occupancy["family"] == "occupancy_change"
    assert occupancy["relevant_houses"] == [1, 4, 7]
    assert occupancy["quesited_house"] == 7
    assert eviction["family"] == "eviction_risk"
    assert eviction["relevant_houses"] == [1, 4, 7]
    assert eviction["quesited_house"] == 4


def test_property_rule_derivation_keeps_l2_secondary_but_promotes_l10_for_advice():
    base_rules = get_category_rules(Category.PROPERTY)
    advise_rules = derive_property_category_rules(
        base_rules, {"family": "advisability_profit"}
    )
    acquire_rules = derive_property_category_rules(base_rules, {"family": "acquisition"})

    assert advise_rules["primary_significators"] == ["L1", "L4", "L10"]
    assert "L2" in advise_rules["secondary_significators"]
    assert advise_rules["outcome_houses"] == [4, 7, 10]

    assert acquire_rules["primary_significators"] == ["L1", "L4", "L7"]
    assert acquire_rules["secondary_significators"] == ["L10", "L2"]
    assert acquire_rules["outcome_houses"] == [4, 7]


def test_property_advisability_snapshot_supports_clear_yes_without_direct_perfection():
    result = evaluate_property_advisability_snapshot(
        {
            "family": "advisability_profit",
            "l1_name": "Saturn",
            "l1_dignity": 2,
            "l1_house": 1,
            "l1_retrograde": False,
            "l4_name": "Mercury",
            "l4_dignity": 5,
            "l4_house": 4,
            "l4_retrograde": False,
            "l4_solar_condition": "Free of Sun",
            "l10_name": "Jupiter",
            "l10_dignity": 7,
            "l10_house": 10,
            "l10_retrograde": False,
            "l10_solar_condition": "Free of Sun",
            "benefic_in_4": True,
            "malefic_in_4": False,
            "fortune_in_10": True,
            "infortune_in_10": False,
            "benefic_in_asc": False,
            "malefic_in_asc": False,
            "moon_in_asc_unimpeded": False,
        }
    )

    assert result["applies"] is True
    assert result["result"] == "YES"
    assert result["profit_score"] >= 9
    assert result["property_score"] >= 8
    assert any("10th-house profit testimony" in entry["rule"] for entry in result["reasoning"])


def test_property_advisability_snapshot_denies_clear_no_when_l4_is_severely_afflicted():
    result = evaluate_property_advisability_snapshot(
        {
            "family": "advisability_profit",
            "l1_name": "Saturn",
            "l1_dignity": 1,
            "l1_house": 1,
            "l1_retrograde": False,
            "l4_name": "Mercury",
            "l4_dignity": -6,
            "l4_house": 7,
            "l4_retrograde": True,
            "l4_solar_condition": "Combustion",
            "l10_name": "Jupiter",
            "l10_dignity": 5,
            "l10_house": 10,
            "l10_retrograde": False,
            "l10_solar_condition": "Free of Sun",
            "benefic_in_4": False,
            "malefic_in_4": True,
            "fortune_in_10": False,
            "infortune_in_10": False,
            "benefic_in_asc": False,
            "malefic_in_asc": False,
            "moon_in_asc_unimpeded": False,
        }
    )

    assert result["applies"] is True
    assert result["result"] == "NO"
    assert result["severe_property_affliction"] is True
    assert result["property_score"] <= -10
    assert any("4th-house property condition" in entry["rule"] for entry in result["reasoning"])
