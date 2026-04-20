from __future__ import annotations

import re
from typing import Any, Dict

try:
    from ..models import Aspect, Planet
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Aspect, Planet


_SIGN_BEARINGS = {
    "Aries": "East",
    "Taurus": "South by East",
    "Gemini": "West by South",
    "Cancer": "North",
    "Leo": "East by North",
    "Virgo": "South by West",
    "Libra": "West",
    "Scorpio": "North by East",
    "Sagittarius": "East by South",
    "Capricorn": "South",
    "Aquarius": "West by North",
    "Pisces": "North by West",
}

_SIGN_ELEMENTS = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

_SIGN_MODALITIES = {
    "Aries": "Cardinal",
    "Cancer": "Cardinal",
    "Libra": "Cardinal",
    "Capricorn": "Cardinal",
    "Taurus": "Fixed",
    "Leo": "Fixed",
    "Scorpio": "Fixed",
    "Aquarius": "Fixed",
    "Gemini": "Mutable",
    "Virgo": "Mutable",
    "Sagittarius": "Mutable",
    "Pisces": "Mutable",
}

_HOUSE_LOCATION_HINTS = {
    1: [
        "Among the querent's own things or immediate surroundings",
        "Near the querent's usual seat, bag, desk, or entry area",
    ],
    2: [
        "With possessions, money, drawers, bags, or kept valuables",
        "Near a shelf, storage box, purse, or personal effects",
    ],
    3: [
        "On a commute, in a car, classroom, hallway, or neighborhood stop",
        "Among books, papers, messages, or everyday transit items",
    ],
    4: [
        "At home, in the basement, cellar, or lowest part of the property",
        "Near family-kept storage, foundations, or the floor level",
    ],
    5: [
        "Near children, play areas, leisure items, or creative materials",
        "By cosmetics, pleasure items, or a room used for enjoyment",
    ],
    6: [
        "With work materials, utility spaces, tools, or service staff",
        "Near a cleaner, employee, laundry area, or routine work zone",
    ],
    7: [
        "With a partner, spouse, or among another person's belongings",
        "In the bedroom or on the far side of the room or house",
    ],
    8: [
        "In a locked, hidden, dark, or rarely opened place",
        "Near debts, old boxes, secret storage, or something tucked away",
    ],
    9: [
        "With travel gear, study materials, religion, or long-journey items",
        "Near books, luggage, visas, or a place connected with foreign travel",
    ],
    10: [
        "In a workplace, home office, formal room, or parent's area",
        "In an attic, elevated work area, or public-facing room",
    ],
    11: [
        "With a friend or among a friend's belongings",
        "Near guest areas, social spaces, or group-related items",
    ],
    12: [
        "In a hidden, isolated, or behind-the-scenes place",
        "Near laundry piles, closets, under furniture, or neglected corners",
    ],
}


def _sign_name_from_longitude(longitude: float | None) -> str | None:
    if longitude is None:
        return None
    signs = [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    ]
    return signs[int((float(longitude) % 360) // 30)]


def _normalize_delta(value: float) -> float:
    return ((float(value) + 180.0) % 360.0) - 180.0


def _ordinal(num: int | None) -> str:
    if num is None:
        return "unknown"
    if 10 <= (num % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")
    return f"{num}{suffix}"


def _angularity(house: int | None) -> str:
    if house in {1, 4, 7, 10}:
        return "angular"
    if house in {2, 5, 8, 11}:
        return "succedent"
    return "cadent"


def _push_unique(bucket: list[Dict[str, Any]], label: str, reason: str, weight: int) -> None:
    if not label or any(entry.get("label") == label for entry in bucket):
        return
    bucket.append({"label": label, "reason": reason, "weight": int(weight)})


def analyze_lost_object_question_text(question: str) -> Dict[str, Any] | None:
    """Classify lost-object questions into reusable discovery families.

    The purpose here is to protect genuine recovery/location questions from
    being swallowed by money, education, or travel keyword pollution.
    """

    q = (question or "").lower().strip()
    if not q:
        return None

    discovery_patterns = (
        r"\bwhere(?:'s| is)\b",
        r"\blost\b",
        r"\bmissing\b",
        r"\bmisplaced\b",
        r"\blocate\b",
        r"\bdisappeared\b",
        r"\bstolen\b",
        r"\bfind\b.*\b(my|the)\b",
    )
    if not any(re.search(pattern, q, re.IGNORECASE) for pattern in discovery_patterns):
        return None

    document_tokens = (
        "passport",
        "atm card",
        "bank card",
        "debit card",
        "credit card",
        "id card",
        "identity card",
        "driver's license",
        "drivers license",
        "driving licence",
        "license",
        "licence",
        "visa",
        "document",
        "documents",
        "papers",
        "certificate",
        "permit",
        "pass",
    )
    clothing_tokens = (
        "scarf",
        "coat",
        "jacket",
        "glove",
        "hat",
        "shoe",
        "dress",
        "shirt",
        "sock",
        "clothes",
        "clothing",
    )

    object_type = "movable"
    family = "discovery"
    natural_planet = None
    doctrine = "Lost-object questions are judged for recovery and location, not as generic money or success charts."

    if any(token in q for token in document_tokens):
        object_type = "document"
        family = "discovery_timing"
        natural_planet = Planet.MERCURY
        doctrine = "Documents and cards remain lost-object questions; Mercury is a natural witness but the recovery still belongs to the 2nd."
    elif any(token in q for token in clothing_tokens):
        object_type = "clothing"
        family = "discovery"
        natural_planet = Planet.VENUS

    return {
        "family": family,
        "object_type": object_type,
        "relevant_houses": [1, 2],
        "quesited_house": 2,
        "object_house": 2,
        "natural_object_planet": natural_planet,
        "doctrine": doctrine,
    }


def build_lost_object_discovery_snapshot(
    chart: Any,
    querent_planet: Planet,
    quesited_planet: Planet,
    lost_object_analysis: Dict[str, Any] | None,
    perfection: Dict[str, Any] | None,
    reception_info: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """Build a snapshot for lost-object discovery without direct perfection."""

    analysis = lost_object_analysis or {}
    if analysis.get("family") not in {"discovery", "discovery_timing"}:
        return None

    object_pos = chart.planets.get(quesited_planet)
    querent_pos = chart.planets.get(querent_planet)
    if not object_pos or not querent_pos:
        return None

    def _solar_name(planet: Planet) -> str:
        pos = chart.planets.get(planet)
        solar = getattr(pos, "solar_condition", None) if pos else None
        direct = getattr(solar, "condition", None)
        if direct:
            return direct
        solar_analyses = getattr(chart, "solar_analyses", {}) or {}
        analysis = solar_analyses.get(planet)
        condition = getattr(analysis, "condition", None)
        if getattr(condition, "condition_name", None):
            return condition.condition_name
        return "Free of Sun"

    moon_next_planet = None
    moon_next_aspect = None
    moon_next_applying = None
    moon_next_orb = None
    moon_last_planet = None
    moon_last_aspect = None
    moon_next = getattr(chart, "moon_next_aspect", None)
    if moon_next is not None:
        moon_next_planet = getattr(moon_next, "planet", None)
        moon_next_aspect = getattr(moon_next, "aspect", None)
        moon_next_applying = getattr(moon_next, "applying", None)
        moon_next_orb = getattr(moon_next, "orb", None)
    moon_last = getattr(chart, "moon_last_aspect", None)
    if moon_last is not None:
        moon_last_planet = getattr(moon_last, "planet", None)
        moon_last_aspect = getattr(moon_last, "aspect", None)

    natural_planet = analysis.get("natural_object_planet")
    natural_pos = chart.planets.get(natural_planet) if natural_planet else None
    object_sign = (
        getattr(getattr(object_pos, "sign", None), "sign_name", None)
        or str(getattr(object_pos, "sign", ""))
    )
    object_sign_ruler = getattr(getattr(object_pos, "sign", None), "ruler", None)
    dispositor_pos = chart.planets.get(object_sign_ruler) if object_sign_ruler else None

    object_house = getattr(object_pos, "house", None)
    object_longitude = float(getattr(object_pos, "longitude", 0.0) or 0.0)
    next_house = ((int(object_house) % 12) + 1) if object_house else None
    next_cusp_longitude = None
    near_next_cusp = False
    same_sign_as_next_cusp = False
    distance_to_next_cusp = None
    effective_house = object_house
    if next_house and getattr(chart, "houses", None):
        try:
            next_cusp_longitude = float(chart.houses[next_house - 1])
            distance_to_next_cusp = abs(_normalize_delta(next_cusp_longitude - object_longitude))
            cusp_sign = _sign_name_from_longitude(next_cusp_longitude)
            same_sign_as_next_cusp = cusp_sign == object_sign
            near_next_cusp = same_sign_as_next_cusp and distance_to_next_cusp <= 5.0
            if near_next_cusp:
                effective_house = next_house
        except Exception:
            next_cusp_longitude = None
            distance_to_next_cusp = None

    return {
        "family": analysis.get("family"),
        "object_type": analysis.get("object_type", "movable"),
        "querent_name": querent_planet.value,
        "object_name": quesited_planet.value,
        "object_house": getattr(object_pos, "house", None),
        "object_effective_house": effective_house,
        "object_angularity": _angularity(getattr(object_pos, "house", None)),
        "object_sign": object_sign,
        "object_longitude": object_longitude,
        "object_sign_element": _SIGN_ELEMENTS.get(object_sign),
        "object_sign_modality": _SIGN_MODALITIES.get(object_sign),
        "object_sign_direction": _SIGN_BEARINGS.get(object_sign),
        "object_dignity": int(getattr(object_pos, "dignity_score", 0) or 0),
        "object_retrograde": bool(getattr(object_pos, "retrograde", False)),
        "object_solar_condition": _solar_name(quesited_planet),
        "object_near_next_cusp": near_next_cusp,
        "object_same_sign_as_next_cusp": same_sign_as_next_cusp,
        "object_distance_to_next_cusp": distance_to_next_cusp,
        "next_house": next_house,
        "perfection_type": (perfection or {}).get("type"),
        "reception_type": (reception_info or {}).get("type", "none"),
        "traditional_strength": int((reception_info or {}).get("traditional_strength", 0) or 0),
        "one_way": list((reception_info or {}).get("one_way", []) or []),
        "moon_next_planet": moon_next_planet,
        "moon_next_aspect": moon_next_aspect,
        "moon_next_applying": moon_next_applying,
        "moon_next_orb": moon_next_orb,
        "moon_last_planet": moon_last_planet,
        "moon_last_aspect": moon_last_aspect,
        "natural_name": natural_planet.value if natural_planet else None,
        "natural_dignity": int(getattr(natural_pos, "dignity_score", 0) or 0) if natural_pos else None,
        "natural_house": getattr(natural_pos, "house", None) if natural_pos else None,
        "natural_solar_condition": _solar_name(natural_planet) if natural_planet else None,
        "dispositor_name": object_sign_ruler.value if object_sign_ruler else None,
        "dispositor_house": getattr(dispositor_pos, "house", None) if dispositor_pos else None,
        "dispositor_sign": (
            getattr(getattr(dispositor_pos, "sign", None), "sign_name", None)
            or str(getattr(dispositor_pos, "sign", ""))
            if dispositor_pos
            else None
        ),
    }


def evaluate_lost_object_discovery_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Evaluate recovery/location balance for lost-object charts.

    This is intentionally modest. It does not try to produce detailed place
    descriptions; it only prevents discovery questions from being denied simply
    because there is no direct event-style perfection.
    """

    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Lost Object Doctrine",
            "rule": "Lost-object family: discovery is judged by recoverability and condition, not by generic event likelihood alone",
            "weight": 0,
        }
    ]
    score = 0

    perfection_type = snapshot.get("perfection_type")
    if perfection_type in {"translation", "collection", "direct", "separating"}:
        score += 4
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": f"Recovery testimony exists through {perfection_type}",
                "weight": 4,
            }
        )

    solar_condition = (snapshot.get("object_solar_condition") or "Free of Sun")
    solar_condition_key = str(solar_condition).lower()
    if "combust" in solar_condition_key:
        score -= 6
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is combust, suggesting it is badly hidden or destroyed",
                "weight": -6,
            }
        )
    elif "under" in solar_condition_key and "beam" in solar_condition_key:
        score -= 2
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is under the beams, showing obscurity but not final loss",
                "weight": -2,
            }
        )
    else:
        score += 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is free of solar affliction",
                "weight": 1,
            }
        )

    angularity = snapshot.get("object_angularity")
    if angularity == "angular":
        score += 2
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is angular, favoring recovery",
                "weight": 2,
            }
        )
    elif angularity == "succedent":
        score += 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is succedent, so the item is recoverable though not immediately obvious",
                "weight": 1,
            }
        )
    else:
        score -= 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is cadent, which delays or complicates recovery",
                "weight": -1,
            }
        )

    dignity = snapshot.get("object_dignity", 0)
    if dignity >= 2:
        score += 2
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is in workable dignity",
                "weight": 2,
            }
        )
    elif dignity <= -5:
        score -= 2
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "The object significator is badly afflicted",
                "weight": -2,
            }
        )

    if snapshot.get("object_retrograde"):
        score += 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "Retrograde motion suggests the object returns or is recovered",
                "weight": 1,
            }
        )

    reception_strength = snapshot.get("traditional_strength", 0)
    if reception_strength >= 3:
        score += 2
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "Reception between querent and object significator supports recovery",
                "weight": 2,
            }
        )
    elif snapshot.get("one_way"):
        score += 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": "One-way reception gives secondary recovery support",
                "weight": 1,
            }
        )

    moon_next_planet = snapshot.get("moon_next_planet")
    moon_next_aspect = snapshot.get("moon_next_aspect")
    if (
        snapshot.get("moon_next_applying")
        and moon_next_planet is not None
        and moon_next_aspect in {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}
    ):
        target_name = getattr(moon_next_planet, "value", moon_next_planet)
        if target_name == snapshot.get("object_name"):
            score += 3
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "The Moon next applies to the object significator, favoring discovery",
                    "weight": 3,
                }
            )
        elif target_name in {"Jupiter", "Venus", snapshot.get("natural_name")}:
            score += 2
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": f"The Moon next applies harmoniously to {target_name}, supporting recovery",
                    "weight": 2,
                }
            )

    moon_last_planet = snapshot.get("moon_last_planet")
    moon_last_aspect = snapshot.get("moon_last_aspect")
    last_target = getattr(moon_last_planet, "value", moon_last_planet)
    if last_target in {"Venus", "Jupiter"} and moon_last_aspect in {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE, Aspect.SQUARE}:
        score += 1
        reasoning.append(
            {
                "stage": "Lost Object Doctrine",
                "rule": f"The Moon last separated from {last_target}, leaving a recent benefic trace on the matter",
                "weight": 1,
            }
        )

    if snapshot.get("object_type") == "document":
        natural_dignity = snapshot.get("natural_dignity")
        if natural_dignity is not None and natural_dignity >= 0:
            score += 1
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "Mercurial document testimony is sound enough for the item to be found",
                    "weight": 1,
                }
            )
        natural_house = snapshot.get("natural_house")
        if natural_house in {1, 4, 7, 10}:
            score += 1
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "The natural document significator is angular, supporting retrieval in time",
                    "weight": 1,
                }
            )
        object_sign = (snapshot.get("object_sign") or "").lower()
        if object_sign in {"taurus", "libra", "pisces"}:
            score += 1
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "The document significator is in a benefic sign, favoring retrieval from a familiar or orderly place",
                    "weight": 1,
                }
            )
        if object_sign in {"gemini", "libra", "aquarius"}:
            score += 1
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "The document significator is in an airy sign, favoring recovery from an elevated or visible place",
                    "weight": 1,
                }
            )
        if "combust" not in solar_condition_key and snapshot.get("object_dignity", 0) > -5:
            score += 2
            reasoning.append(
                {
                    "stage": "Lost Object Doctrine",
                    "rule": "The document significator is weakened but not destroyed, so misplacement is more likely than permanent loss",
                    "weight": 2,
                }
            )

    if score >= 0:
        return {
            "applies": True,
            "result": "YES",
            "confidence": min(88, 66 + (score * 4)),
            "reasoning": reasoning,
            "score": score,
        }

    if score <= -4:
        return {
            "applies": True,
            "result": "NO",
            "confidence": 76,
            "reasoning": reasoning,
            "score": score,
        }

    return {"applies": False, "reasoning": reasoning, "result": None, "score": score}


def build_lost_object_location_projection(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    """Project likely search places for a lost-object chart.

    This stays modest and ranked: it turns house/sign/dispositor doctrine into
    search clues, not into an exact geolocation claim.
    """

    if not snapshot:
        return {"applies": False}

    effective_house = snapshot.get("object_effective_house") or snapshot.get("object_house")
    object_house = snapshot.get("object_house")
    object_type = snapshot.get("object_type", "movable")
    object_sign = snapshot.get("object_sign")
    sign_element = snapshot.get("object_sign_element")
    sign_modality = snapshot.get("object_sign_modality")
    sign_direction = snapshot.get("object_sign_direction")
    dispositor_house = snapshot.get("dispositor_house")
    dispositor_name = snapshot.get("dispositor_name")
    object_name = snapshot.get("object_name")

    primary_places: list[Dict[str, Any]] = []
    secondary_places: list[Dict[str, Any]] = []
    environment_traits: list[Dict[str, Any]] = []
    directional_cues: list[Dict[str, Any]] = []
    evidence: list[Dict[str, Any]] = []

    for idx, label in enumerate(_HOUSE_LOCATION_HINTS.get(int(effective_house or 0), [])):
        weight = 6 - idx
        reason = f"{_ordinal(int(effective_house))} house placement of {object_name or 'the object significator'}"
        _push_unique(primary_places, label, reason, weight)
        evidence.append({"factor": "house", "rule": reason, "clue": label})

    if effective_house != object_house and effective_house:
        rule = (
            f"{object_name or 'The object significator'} lies within 5 degrees of the next cusp "
            f"in the same sign, so it is read in the {_ordinal(int(effective_house))} house"
        )
        _push_unique(
            environment_traits,
            "Close to the doorway, threshold, or entrance of that room",
            rule,
            5,
        )
        evidence.append(
            {
                "factor": "near_cusp",
                "rule": rule,
                "clue": "Search near the edge, doorway, or threshold first",
            }
        )

    if sign_element == "Fire":
        label = "Near a wall, partition, hearth, heater, or warm place"
        rule = "Fire signs point to heated places or something set against a wall"
        _push_unique(environment_traits, label, rule, 4)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Air":
        label = "High up, near windows, stairs, shelves, or upper rooms"
        rule = "Air signs point upward and toward elevated or airy places"
        _push_unique(environment_traits, label, rule, 4)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Earth":
        label = "On or near the floor, in storage, a pantry, cellar, or garden-side place"
        rule = "Earth signs point to low places, floors, and practical storage"
        _push_unique(environment_traits, label, rule, 4)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Water":
        label = "Near water, bathrooms, kitchens, sinks, damp areas, or washing items"
        rule = "Water signs point to damp places and things connected with water"
        _push_unique(environment_traits, label, rule, 4)
        evidence.append({"factor": "element", "rule": rule, "clue": label})

    if sign_modality == "Mutable":
        label = "Inside something movable: a bag, box, drawer, pocket, or container"
        rule = "Mutable signs often place the object inside something or between places"
        _push_unique(environment_traits, label, rule, 4)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})
    elif sign_modality == "Fixed":
        label = "In a settled place: a cupboard, shelf, drawer, or place it was put away"
        rule = "Fixed signs keep the object in a stable, undisturbed place"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})
    elif sign_modality == "Cardinal":
        label = "Near a passage, entrance, active room, or where things are moved through"
        rule = "Cardinal signs favor thresholds, movement, and active areas"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})

    if sign_direction:
        rule = f"{object_sign} gives the traditional bearing {sign_direction}"
        _push_unique(directional_cues, sign_direction, rule, 2)
        evidence.append(
            {"factor": "direction", "rule": rule, "clue": f"Favour the {sign_direction} direction first"}
        )

    if dispositor_house and dispositor_house != effective_house:
        refinement = _HOUSE_LOCATION_HINTS.get(int(dispositor_house), [])
        if refinement:
            label = refinement[0]
            rule = (
                f"The dispositor {dispositor_name or ''} in the {_ordinal(int(dispositor_house))} house "
                "gives a second location clue"
            ).strip()
            _push_unique(secondary_places, label, rule, 4)
            evidence.append({"factor": "dispositor", "rule": rule, "clue": label})

    if object_type == "document":
        label = "Check desks, papers, folders, travel items, or an office-style surface"
        rule = "Documents keep a Mercurial tone even when the house gives the main location"
        _push_unique(secondary_places, label, rule, 3)
        evidence.append({"factor": "object_type", "rule": rule, "clue": label})
        if object_sign in {"Taurus", "Libra"}:
            venus_label = (
                "Check clothes, pockets, handbags, dressing areas, or where garments were handled"
            )
            venus_rule = (
                "A document in a Venus sign can turn up with clothing, pockets, or soft personal items"
            )
            _push_unique(secondary_places, venus_label, venus_rule, 3)
            evidence.append({"factor": "object_type", "rule": venus_rule, "clue": venus_label})
    elif object_type == "clothing":
        label = "Check wardrobes, coat hooks, soft furnishings, laundry, or where clothes were changed"
        rule = "Clothing questions often repeat Venusian places and soft household storage"
        _push_unique(secondary_places, label, rule, 3)
        evidence.append({"factor": "object_type", "rule": rule, "clue": label})

    summary_bits = [entry["label"] for entry in primary_places[:2]]
    summary_bits.extend(entry["label"] for entry in environment_traits[:2])
    summary = "; ".join(summary_bits)

    confidence = 58
    if primary_places:
        confidence += 10
    if environment_traits:
        confidence += 8
    if secondary_places:
        confidence += 5
    if directional_cues:
        confidence += 3
    if effective_house != object_house:
        confidence += 4
    if dispositor_house and dispositor_house != effective_house:
        confidence += 4
    confidence = min(88, confidence)

    return {
        "applies": True,
        "object_significator": object_name,
        "object_house": object_house,
        "effective_house": effective_house,
        "object_sign": object_sign,
        "sign_element": sign_element,
        "sign_modality": sign_modality,
        "summary": summary,
        "confidence": confidence,
        "confidence_label": (
            "high" if confidence >= 80 else "moderate" if confidence >= 68 else "tentative"
        ),
        "primary_places": primary_places,
        "secondary_places": secondary_places,
        "environment_traits": environment_traits,
        "directional_cues": directional_cues,
        "evidence": evidence,
    }
