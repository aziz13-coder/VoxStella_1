from __future__ import annotations

from typing import Any, Dict

try:
    from ..models import Aspect, Planet
except ImportError:  # pragma: no cover - fallback for script execution
    from models import Aspect, Planet


EASY_ASPECTS = {Aspect.CONJUNCTION, Aspect.SEXTILE, Aspect.TRINE}
_BLOCKING_PERFECTION_TYPES = {
    "prohibition",
    "frustration",
    "refranation",
    "abscission",
    "combustion_veto",
}

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

_PET_TURNED_LOCATION_HINTS = {
    1: [
        "Close to home, the doorway, yard, crate, or its usual resting place",
        "Near the pet's own bed, bowl, blanket, or familiar scent trail",
    ],
    2: [
        "Near food, treats, bowls, stored supplies, or the pet's belongings",
        "With collars, leads, toys, or a place where necessities are kept",
    ],
    3: [
        "On a nearby route, sidewalk, lane, vehicle path, or neighbor stop",
        "Near short trips, local streets, messages, or a place people pass through often",
    ],
    4: [
        "Near home ground, the yard, garage, shed, garden, or low places",
        "In a familiar base area, under something, or near the property's foundation",
    ],
    5: [
        "Near parks, play areas, toys, children, or leisure spaces",
        "Where the pet might wander for play, attention, or excitement",
    ],
    6: [
        "Near routine care, utility spaces, feeding routines, or service areas",
        "With a carer, worker, kennel area, or somewhere animals are regularly handled",
    ],
    7: [
        "With another person, a neighbor, partner, or someone temporarily holding the pet",
        "On the far side of the street, yard, or property, or with another household",
    ],
    8: [
        "In a hidden, frightened, locked, dark, or difficult-to-reach place",
        "Somewhere shut away, tucked in, or avoided out of fear",
    ],
    9: [
        "Farther away, toward open country, travel routes, or a more distant property",
        "Near fields, roadways, study/travel places, or beyond the immediate neighborhood",
    ],
    10: [
        "At a public, professional, or visible place where people would notice the pet",
        "Near offices, front-facing buildings, or somewhere elevated or exposed",
    ],
    11: [
        "With friends, helpers, rescuers, or among community contacts",
        "Near guest areas, group spaces, or someone friendly to the querent",
    ],
    12: [
        "At a veterinary hospital, animal shelter, kennel, or confinement place",
        "In an isolated back room, enclosure, or behind-the-scenes place where animals are kept apart",
    ],
}


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


def _ordinal(num: int | None) -> str:
    if num is None:
        return "unknown"
    if 10 <= (num % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")
    return f"{num}{suffix}"


def _turned_house(radical_house: int | None, base_house: int) -> int | None:
    if radical_house is None:
        return None
    return ((int(radical_house) - int(base_house)) % 12) + 1


def _secondary_preempts_primary(
    primary_exact_in_days: float | None,
    secondary_type: str | None,
    secondary_exact_in_days: float | None,
) -> bool:
    if secondary_type not in _BLOCKING_PERFECTION_TYPES or secondary_exact_in_days is None:
        return False
    if primary_exact_in_days is None:
        return True
    return float(secondary_exact_in_days) < float(primary_exact_in_days)


def analyze_pet_question_text(question: str) -> Dict[str, Any]:
    q = (question or "").lower().strip()
    missing_tokens = (
        "where is",
        "where's",
        "lost",
        "missing",
        "misplaced",
        "stolen",
        "disappeared",
        "come home",
        "come back",
        "return home",
        "return",
        "be found",
        "find my",
        "find our",
        "find the",
        "recover my",
        "recover our",
        "recover the",
    )
    recovery_tokens = (
        "get better",
        "recover",
        "recovery",
        "survive",
        "survival",
        "alive",
        "well",
        "healthy",
        "make it",
        "pull through",
        "improve",
    )

    if any(token in q for token in missing_tokens):
        return {
            "family": "missing",
            "doctrine": (
                "Missing-pet questions are judged through the 6th-house pet significator, "
                "recovery testimony, and location clues rather than as generic event charts."
            ),
        }
    if any(token in q for token in recovery_tokens):
        return {
            "family": "recovery",
            "doctrine": "Pet recovery and survival questions judge the animal's condition and survival testimony, not only direct perfection.",
        }
    return {
        "family": "general",
        "doctrine": "Default pet analysis.",
    }


def build_pet_recovery_snapshot(
    chart: Any,
    quesited_planet: Planet,
    pet_analysis: Dict[str, Any] | None,
    pet_safety: Dict[str, Any] | None,
    moon_support: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = pet_analysis or {}
    if analysis.get("family") != "recovery":
        return None

    pet = chart.planets.get(quesited_planet)
    moon_next = getattr(chart, "moon_next_aspect", None)
    if not pet:
        return None

    solar_condition = getattr(getattr(pet, "solar_condition", None), "condition", None) or "Free of Sun"
    return {
        "family": "recovery",
        "pet_name": quesited_planet.value,
        "pet_house": getattr(pet, "house", None),
        "pet_sign": getattr(pet, "sign", None),
        "pet_dignity": int(getattr(pet, "dignity_score", 0) or 0),
        "pet_retrograde": bool(getattr(pet, "retrograde", False)),
        "pet_solar_condition": solar_condition,
        "pet_safety_score": int((pet_safety or {}).get("score", 0) or 0),
        "moon_score": int((moon_support or {}).get("score", 0) or 0),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": bool(getattr(moon_next, "applying", False)) if moon_next else False,
    }


def build_pet_missing_snapshot(
    chart: Any,
    quesited_planet: Planet,
    pet_analysis: Dict[str, Any] | None,
    perfection: Dict[str, Any] | None,
    reception_info: Dict[str, Any] | None,
    moon_support: Dict[str, Any] | None,
    pet_safety: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    analysis = pet_analysis or {}
    if analysis.get("family") != "missing":
        return None

    pet = chart.planets.get(quesited_planet)
    moon_next = getattr(chart, "moon_next_aspect", None)
    moon_last = getattr(chart, "moon_last_aspect", None)
    if not pet:
        return None

    solar_condition = getattr(getattr(pet, "solar_condition", None), "condition", None) or "Free of Sun"
    pet_sign = getattr(getattr(pet, "sign", None), "sign_name", None) or str(getattr(pet, "sign", ""))
    pet_house = getattr(pet, "house", None)
    pet_relative_house = _turned_house(pet_house, 6)
    dispositor = getattr(getattr(pet, "sign", None), "ruler", None)
    dispositor_pos = chart.planets.get(dispositor) if dispositor else None
    dispositor_house = getattr(dispositor_pos, "house", None) if dispositor_pos else None
    dispositor_relative_house = _turned_house(dispositor_house, 6) if dispositor_house else None
    secondary = (perfection or {}).get("secondary") or {}
    primary_exact_in_days = (perfection or {}).get("exact_in_days")
    secondary_type = secondary.get("type")
    secondary_exact_in_days = secondary.get("exact_in_days")

    return {
        "family": "missing",
        "pet_name": quesited_planet.value,
        "pet_house": pet_house,
        "pet_relative_house": pet_relative_house,
        "pet_sign": pet_sign,
        "pet_sign_element": _SIGN_ELEMENTS.get(pet_sign),
        "pet_sign_modality": _SIGN_MODALITIES.get(pet_sign),
        "pet_sign_direction": _SIGN_BEARINGS.get(pet_sign),
        "pet_dignity": int(getattr(pet, "dignity_score", 0) or 0),
        "pet_retrograde": bool(getattr(pet, "retrograde", False)),
        "pet_angularity": _angularity(pet_house),
        "pet_solar_condition": solar_condition,
        "perfection_type": (perfection or {}).get("type"),
        "perfection_exact_in_days": primary_exact_in_days,
        "secondary_perfection_type": secondary_type,
        "secondary_perfection_reason": secondary.get("reason"),
        "secondary_perfection_exact_in_days": secondary_exact_in_days,
        "secondary_preempts_primary": _secondary_preempts_primary(
            primary_exact_in_days,
            secondary_type,
            secondary_exact_in_days,
        ),
        "reception_type": (reception_info or {}).get("type", "none"),
        "traditional_strength": int((reception_info or {}).get("traditional_strength", 0) or 0),
        "one_way": list((reception_info or {}).get("one_way", []) or []),
        "moon_score": int((moon_support or {}).get("score", 0) or 0),
        "pet_safety_score": int((pet_safety or {}).get("score", 0) or 0),
        "moon_next_planet": getattr(moon_next, "planet", None),
        "moon_next_aspect": getattr(moon_next, "aspect", None),
        "moon_next_applying": bool(getattr(moon_next, "applying", False)) if moon_next else False,
        "moon_last_planet": getattr(moon_last, "planet", None),
        "moon_last_aspect": getattr(moon_last, "aspect", None),
        "dispositor_name": dispositor.value if dispositor else None,
        "dispositor_house": dispositor_house,
        "dispositor_relative_house": dispositor_relative_house,
    }


def evaluate_pet_recovery_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Pet Doctrine",
            "rule": "Pet family: recovery/survival (judge whether the animal survives and improves, not only whether an event perfects)",
            "weight": 0,
        }
    ]

    score = 0
    safety_score = snapshot.get("pet_safety_score", 0)
    moon_score = snapshot.get("moon_score", 0)
    if safety_score:
        score += safety_score
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet safety testimony totals {safety_score:+d}",
                "weight": safety_score,
            }
        )
    if moon_score:
        score += moon_score
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Moon testimony for recovery totals {moon_score:+d}",
                "weight": moon_score,
            }
        )

    if snapshot.get("pet_dignity", 0) >= 0:
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is at least workable in condition",
                "weight": 1,
            }
        )
    elif snapshot.get("pet_dignity", 0) <= -4:
        score -= 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is severely debilitated",
                "weight": -2,
            }
        )

    if snapshot.get("pet_retrograde"):
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is retrograde, favoring return or reversal from the worst point",
                "weight": 1,
            }
        )

    if snapshot.get("pet_solar_condition") == "Combustion":
        score -= 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is combust, heavily weakening vitality",
                "weight": -2,
            }
        )

    if (
        snapshot.get("moon_next_applying")
        and snapshot.get("moon_next_aspect") in EASY_ASPECTS
        and snapshot.get("moon_next_planet") in {Planet.VENUS, Planet.JUPITER, Planet[snapshot["pet_name"].upper()]}
    ):
        target = snapshot["moon_next_planet"].value
        aspect_name = getattr(snapshot["moon_next_aspect"], "display_name", "Applying aspect")
        score += 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Moon next applies by {aspect_name} to {target}, supporting recovery",
                "weight": 2,
            }
        )

    if score >= 8:
        result = "YES"
        confidence = 84
    elif score >= 3:
        result = "YES"
        confidence = 70
    else:
        result = "NO"
        confidence = 76

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }


def evaluate_pet_missing_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False, "reasoning": [], "result": None}

    reasoning = [
        {
            "stage": "Pet Doctrine",
            "rule": (
                "Missing-pet family: judge the 6th-house pet significator for recovery, "
                "condition, and whereabouts rather than as a generic event chart"
            ),
            "weight": 0,
        }
    ]

    score = 0
    perfection_type = str(snapshot.get("perfection_type") or "")
    secondary_type = str(snapshot.get("secondary_perfection_type") or "")
    if snapshot.get("secondary_preempts_primary"):
        score -= 5
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": (
                    f"An earlier {secondary_type or 'blocking testimony'} pre-empts the apparent recovery route: "
                    f"{snapshot.get('secondary_perfection_reason') or 'the recovery testimony is blocked before completion'}"
                ),
                "weight": -5,
            }
        )
    elif perfection_type in _BLOCKING_PERFECTION_TYPES:
        score -= 5
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": (
                    f"Primary perfection is {perfection_type}, so the recovery route is blocked rather than completed"
                ),
                "weight": -5,
            }
        )
    elif perfection_type.startswith("direct") or perfection_type in {"translation", "collection", "separating"}:
        score += 4
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Recovery testimony exists through {perfection_type or 'direct contact'}",
                "weight": 4,
            }
        )

    reception_strength = snapshot.get("traditional_strength", 0)
    if reception_strength >= 3:
        score += 3
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "Reception between querent and pet significators supports the animal being found",
                "weight": 3,
            }
        )
    elif snapshot.get("one_way"):
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "One-way reception gives secondary support for recovery",
                "weight": 1,
            }
        )

    if snapshot.get("pet_retrograde"):
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is retrograde, favoring return or retracing",
                "weight": 1,
            }
        )

    angularity = snapshot.get("pet_angularity")
    if angularity == "angular":
        score += 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator is angular, favoring quick visibility or return",
                "weight": 2,
            }
        )
    elif angularity == "succedent":
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator is succedent, so recovery is possible though not immediate",
                "weight": 1,
            }
        )
    else:
        score -= 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator is cadent, which delays or complicates retrieval",
                "weight": -1,
            }
        )

    dignity = snapshot.get("pet_dignity", 0)
    if dignity >= 0:
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is still workable in condition",
                "weight": 1,
            }
        )
    elif dignity <= -5:
        score -= 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Pet significator {snapshot['pet_name']} is badly afflicted, suggesting distress rather than final loss",
                "weight": -2,
            }
        )

    solar_condition = (snapshot.get("pet_solar_condition") or "Free of Sun").lower()
    if "combust" in solar_condition:
        score -= 3
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator is combust, showing heavy weakness or concealment",
                "weight": -3,
            }
        )
    elif "under" in solar_condition and "beam" in solar_condition:
        score -= 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator is under the beams, showing obscurity but not final loss",
                "weight": -1,
            }
        )

    moon_score = snapshot.get("moon_score", 0)
    if moon_score >= 2:
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"Moon testimony adds supportive movement toward recovery ({moon_score:+d})",
                "weight": 1,
            }
        )

    if snapshot.get("pet_safety_score", 0) <= -4:
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The chart warns the pet may be recovered in a stressed or injured condition",
                "weight": 0,
            }
        )

    moon_next_planet = snapshot.get("moon_next_planet")
    moon_next_aspect = snapshot.get("moon_next_aspect")
    target_name = getattr(moon_next_planet, "value", moon_next_planet)
    if (
        snapshot.get("moon_next_applying")
        and moon_next_aspect in EASY_ASPECTS
        and target_name in {snapshot.get("pet_name"), "Venus", "Jupiter", snapshot.get("dispositor_name")}
    ):
        score += 2
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"The Moon next applies harmoniously to {target_name}, supporting recovery or contact",
                "weight": 2,
            }
        )

    moon_last_planet = snapshot.get("moon_last_planet")
    moon_last_aspect = snapshot.get("moon_last_aspect")
    last_name = getattr(moon_last_planet, "value", moon_last_planet)
    if last_name in {"Venus", "Jupiter", snapshot.get("pet_name")} and moon_last_aspect in {
        Aspect.CONJUNCTION,
        Aspect.SEXTILE,
        Aspect.TRINE,
        Aspect.SQUARE,
    }:
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": f"The Moon recently separated from {last_name}, leaving a fresh trace on the pet matter",
                "weight": 1,
            }
        )

    if snapshot.get("pet_relative_house") == 12:
        score += 1
        reasoning.append(
            {
                "stage": "Pet Doctrine",
                "rule": "The pet significator lies in the turned 12th from the 6th, pointing to shelter, confinement, or veterinary holding rather than final loss",
                "weight": 1,
            }
        )

    if score >= 5:
        result = "YES"
        confidence = 84
    elif score >= 1:
        result = "YES"
        confidence = 70
    else:
        result = "NO"
        confidence = 74

    return {
        "applies": True,
        "result": result,
        "confidence": confidence,
        "score": score,
        "reasoning": reasoning,
    }


def build_pet_missing_location_projection(snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not snapshot:
        return {"applies": False}

    pet_relative_house = snapshot.get("pet_relative_house")
    sign_element = snapshot.get("pet_sign_element")
    sign_modality = snapshot.get("pet_sign_modality")
    sign_direction = snapshot.get("pet_sign_direction")
    pet_name = snapshot.get("pet_name") or "the pet"
    dispositor_relative_house = snapshot.get("dispositor_relative_house")

    primary_places: list[Dict[str, Any]] = []
    secondary_places: list[Dict[str, Any]] = []
    environment_traits: list[Dict[str, Any]] = []
    directional_cues: list[Dict[str, Any]] = []
    evidence: list[Dict[str, Any]] = []

    for idx, label in enumerate(_PET_TURNED_LOCATION_HINTS.get(int(pet_relative_house or 0), [])):
        weight = 6 - idx
        reason = f"{_ordinal(int(pet_relative_house))} house from the 6th placement of {pet_name}"
        _push_unique(primary_places, label, reason, weight)
        evidence.append({"factor": "turned_house", "rule": reason, "clue": label})

    if dispositor_relative_house and dispositor_relative_house != pet_relative_house:
        for idx, label in enumerate(_PET_TURNED_LOCATION_HINTS.get(int(dispositor_relative_house), [])[:1]):
            weight = 4 - idx
            reason = (
                f"The dispositor of {pet_name} falls in the {_ordinal(int(dispositor_relative_house))} "
                "house from the 6th, adding a secondary place clue"
            )
            _push_unique(secondary_places, label, reason, weight)
            evidence.append({"factor": "dispositor", "rule": reason, "clue": label})

    if sign_direction:
        label = f"{sign_direction}"
        rule = f"{snapshot.get('pet_sign')} gives the bearing for the search direction"
        _push_unique(directional_cues, label, rule, 5)
        evidence.append({"factor": "sign_direction", "rule": rule, "clue": label})

    if sign_element == "Fire":
        label = "Near heat, sunlight, a wall, fence, or exposed outdoor place"
        rule = "Fire signs lift the search toward warm, active, or exposed places"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Air":
        label = "Near roads, openings, stairs, breezy places, or raised sight-lines"
        rule = "Air signs point to movement, open routes, and more elevated ground"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Earth":
        label = "Low to the ground, under things, in a yard, shed, or practical storage place"
        rule = "Earth signs keep the search low, grounded, and tied to solid places"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "element", "rule": rule, "clue": label})
    elif sign_element == "Water":
        label = "Near damp ground, puddles, drains, water, kitchens, baths, or washing areas"
        rule = "Water signs point to damp or watery environments"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "element", "rule": rule, "clue": label})

    if sign_modality == "Mutable":
        label = "Between places, on the move, along a route, or near bags/containers/openings"
        rule = "Mutable signs often show movement between one place and another"
        _push_unique(environment_traits, label, rule, 3)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})
    elif sign_modality == "Fixed":
        label = "Staying put in one settled hiding place"
        rule = "Fixed signs keep the matter in one place once hidden"
        _push_unique(environment_traits, label, rule, 2)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})
    elif sign_modality == "Cardinal":
        label = "Near a threshold, entrance, gate, roadside, or the start of a path"
        rule = "Cardinal signs bring the search toward entrances, edges, and active movement"
        _push_unique(environment_traits, label, rule, 2)
        evidence.append({"factor": "modality", "rule": rule, "clue": label})

    summary_parts = []
    if primary_places:
        summary_parts.append(primary_places[0]["label"])
    if environment_traits:
        summary_parts.append(environment_traits[0]["label"])
    if directional_cues:
        summary_parts.append(f"Search toward {directional_cues[0]['label']}")

    confidence = "moderate"
    if snapshot.get("traditional_strength", 0) >= 3 or snapshot.get("perfection_type"):
        confidence = "high"

    return {
        "applies": bool(primary_places or environment_traits or directional_cues),
        "summary": "; ".join(summary_parts) if summary_parts else "Search from the pet significator's turned-house and sign clues.",
        "primary_places": primary_places,
        "secondary_places": secondary_places,
        "environment_traits": environment_traits,
        "directional_cues": directional_cues,
        "evidence": evidence,
        "confidence": confidence,
        "confidence_note": "Missing-pet location clues are ranked search hints, not an exact address.",
    }
