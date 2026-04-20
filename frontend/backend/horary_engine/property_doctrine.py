from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict

try:
    from ..models import Planet
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Planet


def _unique(items):
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def analyze_property_question_text(question: str, question_intent: str) -> Dict[str, Any]:
    """Classify property questions into Lilly-style families.

    Acquisition questions focus on whether the property will be obtained.
    Advisability/profit questions focus on whether taking the property is
    favorable or profitable. Condition questions focus on the quality of the
    house/land itself.
    """

    q = (question or "").lower().strip()

    property_words = (
        "house",
        "home",
        "property",
        "real estate",
        "land",
        "apartment",
        "flat",
        "building",
    )
    advisability_words = (
        "should i",
        "should we",
        "good to",
        "wise to",
        "advisable",
        "favorable",
        "worth",
        "profit",
        "profitable",
        "invest",
        "investment",
        "return",
        "roi",
        "yield",
        "hire",
        "rent",
        "lease",
        "take this",
        "take the",
    )
    acquisition_patterns = (
        r"\b(buy|purchase|acquire|obtain|get)\b.*\b(house|home|property|real\s*estate|land|flat|apartment|building)\b",
        r"\b(house|home|property|real\s*estate|land|flat|apartment|building)\b.*\b(buy|purchase|acquire|obtain|get)\b",
    )
    sale_patterns = (
        r"\b(sell|sale|selling|dispose of)\b.*\b(house|home|property|real\s*estate|land|flat|apartment|building)\b",
        r"\b(house|home|property|real\s*estate|land|flat|apartment|building)\b.*\b(sell|sale|selling|dispose of)\b",
    )
    condition_words = (
        "is this house good",
        "is the house good",
        "is this property good",
        "is the property good",
        "good house",
        "bad house",
        "good land",
        "bad land",
        "quality of",
        "sound house",
        "sound property",
    )
    friend_house_words = (
        "friend's house",
        "friends house",
        "friend's home",
        "friend home",
        "friend's flat",
        "friend's apartment",
    )
    move_words = ("move", "live", "stay", "relocate")
    rental_words = ("rent", "lease", "hire")
    occupancy_words = ("tenant", "occupant", "lodger", "renter", "boarder")
    occupancy_change_patterns = (
        r"\b(tenant|occupant|lodger|renter|boarder)\b.*\b(move out|leave|vacate|quit)\b",
        r"\b(move out|vacate|quit)\b.*\b(tenant|occupant|lodger|renter|boarder)\b",
        r"\bwill\s+(he|she|they)\b.*\bleave\b.*\b(property|house|home|flat|apartment|building)\b",
        r"\bleave\b.*\b(property|house|home|flat|apartment|building)\b",
    )
    eviction_patterns = (
        r"\b(evict|evicted|eviction)\b",
        r"\blose\b.*\b(home|house|property|flat|apartment)\b",
        r"\bthrow(n)?\s+out\b",
        r"\bput\s+out\b",
    )
    has_property = any(token in q for token in property_words)
    is_acquisition = has_property and any(re.search(pattern, q, re.IGNORECASE) for pattern in acquisition_patterns)
    is_sale = has_property and any(re.search(pattern, q, re.IGNORECASE) for pattern in sale_patterns)
    is_occupancy_change = any(re.search(pattern, q, re.IGNORECASE) for pattern in occupancy_change_patterns)
    is_eviction_risk = has_property and any(re.search(pattern, q, re.IGNORECASE) for pattern in eviction_patterns)

    if any(token in q for token in friend_house_words) and any(token in q for token in move_words):
        family = "friend_house_move"
        relevant_houses = [1, 11]
        doctrine = "A friend's house is judged from the 11th; moving there is judged by the querent and the friend's house."
        property_house = 11
        seller_house = None
        counterparty_house = None
        profit_house = None
        end_house = 11
        quesited_house = 11
    elif any(token in q for token in condition_words):
        family = "condition"
        relevant_houses = [1, 4]
        doctrine = "Lilly goodness or badness of the land or house"
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    elif is_occupancy_change and (has_property or any(token in q for token in occupancy_words)):
        family = "occupancy_change"
        relevant_houses = [1, 4, 7]
        doctrine = "Tenant or occupant departure questions keep the querent or operative holder, the property in the 4th, and the tenant or unwanted occupant in the 7th."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 7
    elif is_eviction_risk:
        family = "eviction_risk"
        relevant_houses = [1, 4, 7]
        doctrine = "Eviction or loss-of-home questions keep the querent, the home in the 4th, and the landlord or housing counterparty in the 7th."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    elif any(token in q for token in rental_words) and any(
        token in q for token in ("house", "home", "property", "flat", "apartment")
    ):
        family = "rental_acquisition"
        relevant_houses = [1, 7, 4]
        doctrine = "Rental questions require the querent, the landlord or current holder, and the property itself."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    elif any(token in q for token in advisability_words) or question_intent == "QUALITY":
        family = "advisability_profit"
        relevant_houses = [1, 4, 7, 10]
        doctrine = "Property advisability weighs the house in the 4th, the counterparty in the 7th, and profit or outcome in the 10th."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    elif is_acquisition:
        family = "acquisition"
        relevant_houses = [1, 4, 7]
        doctrine = "Buying a house keeps the house in the 4th and the other contracting party in the 7th; money remains secondary."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    elif is_sale:
        family = "sale"
        relevant_houses = [1, 4, 7]
        doctrine = "Selling a house keeps the house in the 4th and the buyer or other contracting party in the 7th; money remains secondary."
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4
    else:
        family = "condition"
        relevant_houses = [1, 4]
        doctrine = "Default property condition analysis"
        property_house = 4
        seller_house = 7
        counterparty_house = 7
        profit_house = 10
        end_house = 4
        quesited_house = 4

    return {
        "family": family,
        "relevant_houses": relevant_houses,
        "property_house": property_house,
        "seller_house": seller_house,
        "counterparty_house": counterparty_house,
        "profit_house": profit_house,
        "end_house": end_house,
        "quesited_house": quesited_house,
        "l2_role": "secondary_only",
        "doctrine": doctrine,
    }


def derive_property_category_rules(
    base_rules: Dict[str, Any], property_analysis: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Return property rules adjusted by question family.

    Lilly makes the 4th house primary for the property itself, the 7th for the
    other party, and the 10th for price/profit. The 2nd may remain secondary
    for the querent's money but should not become co-primary.
    """

    rules = deepcopy(base_rules or {})
    analysis = property_analysis or {}
    family = analysis.get("family", "condition")

    scored_factors = list(rules.get("scored_factors", []))
    scored_factors.extend(
        ["debilitation", "cadent_significator", "significator_strength", "house_condition"]
    )
    rules["scored_factors"] = _unique(scored_factors)

    if family == "friend_house_move":
        rules["primary_significators"] = ["L1", "L11"]
        rules["secondary_significators"] = []
        rules["outcome_houses"] = [11]
        rules["irrelevant_houses"] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12]
    elif family == "rental_acquisition":
        rules["primary_significators"] = ["L1", "L4"]
        rules["secondary_significators"] = ["L7"]
        rules["outcome_houses"] = [4, 7]
        rules["irrelevant_houses"] = [2, 3, 5, 6, 8, 9, 10, 11, 12]
    elif family == "advisability_profit":
        rules["primary_significators"] = ["L1", "L4", "L10"]
        rules["secondary_significators"] = ["L7", "L2"]
        rules["outcome_houses"] = [4, 7, 10]
        rules["irrelevant_houses"] = [2, 3, 5, 6, 8, 9, 11, 12]
    elif family in {"acquisition", "sale", "occupancy_change", "eviction_risk"}:
        rules["primary_significators"] = ["L1", "L4", "L7"]
        rules["secondary_significators"] = ["L10", "L2"]
        rules["outcome_houses"] = [4, 7]
        rules["irrelevant_houses"] = [3, 5, 6, 8, 9, 11, 12]
    else:
        rules["primary_significators"] = ["L1", "L4"]
        rules["secondary_significators"] = ["L7", "L10"]
        rules["outcome_houses"] = [4]
        rules["irrelevant_houses"] = [2, 3, 5, 6, 7, 8, 9, 10, 11, 12]

    rules["property_family"] = family
    return rules


def _solar_name(value: str | None) -> str:
    return value or "Free of Sun"


def build_property_advisability_snapshot(
    chart: Any, querent_planet: Planet, property_analysis: Dict[str, Any] | None
) -> Dict[str, Any] | None:
    """Build a pure snapshot for property advisability scoring."""

    analysis = property_analysis or {}
    if analysis.get("family") != "advisability_profit":
        return None

    property_house = analysis.get("property_house", 4)
    profit_house = analysis.get("profit_house", 10)

    l4 = chart.house_rulers.get(property_house)
    l10 = chart.house_rulers.get(profit_house)
    l1 = querent_planet
    if not (l1 and l4 and l10):
        return None

    benefics = {Planet.JUPITER, Planet.VENUS}
    malefics = {Planet.MARS, Planet.SATURN}

    def _cond(planet: Planet) -> str:
        pos = chart.planets.get(planet)
        if not pos:
            return "Free of Sun"
        solar = getattr(pos, "solar_condition", None)
        return _solar_name(getattr(solar, "condition", None))

    def _dignity(planet: Planet) -> int:
        pos = chart.planets.get(planet)
        return int(getattr(pos, "dignity_score", 0) or 0) if pos else 0

    def _house(planet: Planet) -> int | None:
        pos = chart.planets.get(planet)
        return getattr(pos, "house", None) if pos else None

    def _retrograde(planet: Planet) -> bool:
        pos = chart.planets.get(planet)
        return bool(getattr(pos, "retrograde", False)) if pos else False

    snapshot = {
        "family": analysis.get("family"),
        "l1_name": l1.value,
        "l1_dignity": _dignity(l1),
        "l1_house": _house(l1),
        "l1_retrograde": _retrograde(l1),
        "l4_name": l4.value,
        "l4_dignity": _dignity(l4),
        "l4_house": _house(l4),
        "l4_retrograde": _retrograde(l4),
        "l4_solar_condition": _cond(l4),
        "l10_name": l10.value,
        "l10_dignity": _dignity(l10),
        "l10_house": _house(l10),
        "l10_retrograde": _retrograde(l10),
        "l10_solar_condition": _cond(l10),
        "benefic_in_4": any(getattr(chart.planets.get(p), "house", None) == property_house for p in benefics),
        "malefic_in_4": any(getattr(chart.planets.get(p), "house", None) == property_house for p in malefics),
        "fortune_in_10": any(getattr(chart.planets.get(p), "house", None) == profit_house for p in benefics),
        "infortune_in_10": any(getattr(chart.planets.get(p), "house", None) == profit_house for p in malefics),
        "benefic_in_asc": any(getattr(chart.planets.get(p), "house", None) == 1 for p in benefics),
        "malefic_in_asc": any(getattr(chart.planets.get(p), "house", None) == 1 for p in malefics if p != l1),
        "moon_in_asc_unimpeded": getattr(chart.planets.get(Planet.MOON), "house", None) == 1,
    }
    return snapshot


def evaluate_property_advisability_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Evaluate Lilly-style property advisability without direct perfection.

    This handles quality/advice questions where Lilly looks at the 10th for
    profit and the 4th for the end and condition of the land/house.
    """

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Property Doctrine",
            "rule": "Property family: advisability/profit (4th = property/end, 10th = profit, 7th = other party)",
            "weight": 0,
        }
    ]

    querent_score = 0
    profit_score = 0
    property_score = 0
    severe_property_affliction = False

    if snapshot.get("l1_house") == 1:
        querent_score += 1
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L1 ({snapshot['l1_name']}) in the Ascendant supports the querent's position",
                "weight": 1,
                "house": 1,
            }
        )
    if snapshot.get("benefic_in_asc"):
        querent_score += 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Fortune in the Ascendant supports taking the property",
                "weight": 2,
                "house": 1,
            }
        )
    if snapshot.get("malefic_in_asc"):
        querent_score -= 3
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Infortune in the Ascendant warns of regret or distaste in the bargain",
                "weight": -3,
                "house": 1,
            }
        )
    if snapshot.get("moon_in_asc_unimpeded"):
        querent_score += 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Moon in the Ascendant supports taking the property",
                "weight": 2,
                "house": 1,
            }
        )
    if snapshot.get("l1_dignity", 0) >= 1:
        querent_score += 1
    elif snapshot.get("l1_dignity", 0) <= -5:
        querent_score -= 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L1 ({snapshot['l1_name']}) is weak, reducing the querent's leverage",
                "weight": -2,
                "house": 1,
            }
        )

    l10_dignity = snapshot.get("l10_dignity", 0)
    if l10_dignity >= 5:
        profit_score += 5
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"10th-house profit testimony: L10 ({snapshot['l10_name']}) is strongly dignified",
                "weight": 5,
                "house": 10,
            }
        )
    elif l10_dignity >= 1:
        profit_score += 3
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"10th-house profit testimony: L10 ({snapshot['l10_name']}) is sound enough to support profit",
                "weight": 3,
                "house": 10,
            }
        )
    elif l10_dignity <= -5:
        profit_score -= 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"10th-house profit testimony: L10 ({snapshot['l10_name']}) is badly afflicted",
                "weight": -4,
                "house": 10,
            }
        )

    if snapshot.get("fortune_in_10"):
        profit_score += 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Fortune in the 10th supports profit from the undertaking",
                "weight": 4,
                "house": 10,
            }
        )
    if snapshot.get("infortune_in_10"):
        profit_score -= 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Infortune in the 10th opposes profit and smooth agreement",
                "weight": -4,
                "house": 10,
            }
        )

    l10_solar = snapshot.get("l10_solar_condition")
    if l10_solar == "Combustion":
        profit_score -= 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L10 ({snapshot['l10_name']}) combust opposes profit",
                "weight": -4,
                "house": 10,
            }
        )
    elif l10_solar == "Under the Beams":
        profit_score -= 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L10 ({snapshot['l10_name']}) under beams weakens profit testimony",
                "weight": -2,
                "house": 10,
            }
        )
    if snapshot.get("l10_retrograde"):
        profit_score -= 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L10 ({snapshot['l10_name']}) retrograde delays or revises the profit picture",
                "weight": -2,
                "house": 10,
            }
        )
    if snapshot.get("l10_house") in {6, 8, 12}:
        profit_score -= 1

    l4_dignity = snapshot.get("l4_dignity", 0)
    if snapshot.get("l4_house") == 4 and l4_dignity >= 1:
        property_score += 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"4th-house property condition: L4 ({snapshot['l4_name']}) is in the 4th and sound",
                "weight": 4,
                "house": 4,
            }
        )
    elif l4_dignity >= 5:
        property_score += 5
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"4th-house property condition: L4 ({snapshot['l4_name']}) is strongly dignified",
                "weight": 5,
                "house": 4,
            }
        )

    if snapshot.get("benefic_in_4"):
        property_score += 4
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Fortune in the 4th supports the land/house and the end of the matter",
                "weight": 4,
                "house": 4,
            }
        )
    if snapshot.get("malefic_in_4"):
        property_score -= 5
        severe_property_affliction = True
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": "Infortune in the 4th opposes the house/land and the end of the matter",
                "weight": -5,
                "house": 4,
            }
        )

    if l4_dignity <= -5:
        property_score -= 5
        severe_property_affliction = True
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"4th-house property condition: L4 ({snapshot['l4_name']}) is badly afflicted",
                "weight": -5,
                "house": 4,
            }
        )
    elif l4_dignity < 0:
        property_score -= 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"4th-house property condition: L4 ({snapshot['l4_name']}) is somewhat weakened",
                "weight": -2,
                "house": 4,
            }
        )

    l4_solar = snapshot.get("l4_solar_condition")
    if l4_solar == "Combustion":
        property_score -= 4
        severe_property_affliction = True
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L4 ({snapshot['l4_name']}) combust strongly afflicts the property or end of the matter",
                "weight": -4,
                "house": 4,
            }
        )
    elif l4_solar == "Under the Beams":
        property_score -= 2
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L4 ({snapshot['l4_name']}) under beams weakens the property testimony",
                "weight": -2,
                "house": 4,
            }
        )
    if snapshot.get("l4_retrograde") and l4_dignity < 0:
        property_score -= 3
        severe_property_affliction = True
        reasoning.append(
            {
                "stage": "Property Doctrine",
                "rule": f"L4 ({snapshot['l4_name']}) retrograde and weak threatens the bargain's stability",
                "weight": -3,
                "house": 4,
            }
        )

    total = querent_score + profit_score + property_score
    result = None
    confidence = None

    if severe_property_affliction and property_score <= -5:
        result = "NO"
        confidence = min(85, 70 + abs(property_score))
    elif total >= 9 and property_score >= 0 and profit_score >= 4:
        result = "YES"
        confidence = min(85, 62 + total)
    elif total <= -7 or profit_score <= -4:
        result = "NO"
        confidence = min(85, 65 + abs(total))

    return {
        "applies": True,
        "reasoning": reasoning,
        "querent_score": querent_score,
        "profit_score": profit_score,
        "property_score": property_score,
        "score": total,
        "result": result,
        "confidence": int(confidence) if isinstance(confidence, (int, float)) else None,
        "severe_property_affliction": severe_property_affliction,
    }
