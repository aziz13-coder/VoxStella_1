from __future__ import annotations

"""Stable, auditable mapping from fired rules to benchmark outcome axes.

Free-text titles and rationales are explanatory output. They are not a safe
machine interface: a single incidental word can imply an unrelated outcome.
This module intentionally uses only explicit rule metadata, stable rule IDs,
and narrow category mappings.
"""

from typing import Any, Dict, Iterable, List


AXIS_ORDER = (
    "violence_homicide",
    "abduction_missing_person",
    "deception_coverup",
    "immediate_scene_or_vicinity_context",
    "trafficking_or_possession_context",
    "communication_vehicle_short_distance_context",
    "family_home_end_matter_context",
    "party_entertainment_context",
    "routine_disruption_stalker_context",
    "suspect_territory_context",
    "death_financial_entanglement_context",
    "far_distance_departure_context",
    "public_authority_witness_context",
    "friends_social_circle_context",
    "hidden_captive_kidnapped_context",
    "domestic_partner_involvement",
    "family_involvement",
    "child_victim",
    "water_disappearance_or_drowning",
    "accident_or_disaster",
    "friend_or_close_associate",
    "authority_or_public_case",
    "accomplice_or_witness",
    "route_vehicle_transport",
)

CATEGORY_AXIS_MAP = {
    "Violence": ("violence_homicide",),
    "Abduction": ("abduction_missing_person",),
    "Deception": ("deception_coverup",),
    "Domestic": ("domestic_partner_involvement",),
    "Family": ("family_involvement",),
    "Children": ("child_victim",),
    "Water": ("water_disappearance_or_drowning",),
    "Disaster": ("accident_or_disaster",),
    "Associates": ("friend_or_close_associate",),
    "Public": ("authority_or_public_case",),
    "Witness": ("accomplice_or_witness",),
}

# Categories capture the primary meaning. These IDs add a second, explicit
# axis that genuinely belongs to the same compound rule.
RULE_AXIS_MAP = {
    "vehicle_crash_or_transport_harm_pattern": ("route_vehicle_transport",),
    "travel_accident_or_disaster_pattern": ("route_vehicle_transport",),
    "waterborne_accident_or_disaster_pattern": ("route_vehicle_transport",),
    "air_disaster_launch_pattern": ("route_vehicle_transport",),
    "known_person_route_harm_moon_dispositor_bridge": ("route_vehicle_transport",),
    "domestic_partner_route_abduction_pressure": (
        "abduction_missing_person",
        "route_vehicle_transport",
    ),
}


def _axes_for_finding(finding: Dict[str, Any]) -> Iterable[str]:
    for axis in finding.get("axis_hints") or []:
        if axis in AXIS_ORDER:
            yield axis
    for axis in CATEGORY_AXIS_MAP.get(str(finding.get("category") or ""), ()):
        yield axis
    for axis in RULE_AXIS_MAP.get(str(finding.get("id") or ""), ()):
        yield axis


def assess_axes(findings: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    support: Dict[str, List[Dict[str, Any]]] = {axis: [] for axis in AXIS_ORDER}
    excluded_rule_ids: List[str] = []
    for finding in findings or []:
        if not isinstance(finding, dict):
            continue
        if finding.get("scoring_eligible", True) is False:
            rule_id = str(finding.get("id") or "")
            if rule_id:
                excluded_rule_ids.append(rule_id)
            continue
        for axis in dict.fromkeys(_axes_for_finding(finding)):
            support[axis].append(
                {
                    "rule_id": finding.get("id"),
                    "category": finding.get("category"),
                    "weight": finding.get("weight", 1),
                    "validation_status": finding.get("validation_status", "unvalidated"),
                    "source_refs": list(finding.get("source_refs") or []),
                }
            )

    predicted = [axis for axis in AXIS_ORDER if support[axis]]
    return {
        "predicted_axes": predicted,
        "support": {axis: rows for axis, rows in support.items() if rows},
        "method": "explicit_rule_id_category_mapping_v1",
        "uses_free_text": False,
        "threshold_tuned": False,
        "excluded_non_scoring_rule_ids": list(dict.fromkeys(excluded_rule_ids)),
    }
