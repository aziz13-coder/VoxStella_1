from __future__ import annotations

from typing import Any, Dict, List, Optional

from .curation import confidence_tags
from .relationships import PILLAR_DOMAIN_LABELS


PALACE_ORDER = ("year", "month", "day", "hour")

PALACE_CONTEXT = {
    "year": {
        "pillar_label": "Year",
        "life_stage": "Childhood",
        "age_range": "0-17",
        "outer_domain": "ancestry, grandparents, public background, and the wider world",
        "stem_domain": "outer image and inherited atmosphere",
        "branch_domain": "early-life ground, family background, and broad social field",
        "privacy": "outer",
    },
    "month": {
        "pillar_label": "Month",
        "life_stage": "Adolescence / formation",
        "age_range": "18-34",
        "outer_domain": "parents, siblings, colleagues, schooling, and career structure",
        "stem_domain": "visible social formation and work-family expectations",
        "branch_domain": "peer field, family structure, and practical career ground",
        "privacy": "social",
    },
    "day": {
        "pillar_label": "Day",
        "life_stage": "Adulthood",
        "age_range": "35-51",
        "outer_domain": "selfhood, spouse/partner palace, and deep one-to-one bonds",
        "stem_domain": "Day Master reference point and conscious self-position",
        "branch_domain": "partner palace, close relationship ground, and embodied self-life",
        "privacy": "intimate",
    },
    "hour": {
        "pillar_label": "Hour",
        "life_stage": "Later life / future aims",
        "age_range": "52+",
        "outer_domain": "children, inner home, private aims, and later-life direction",
        "stem_domain": "private aspirations and messages from the inner life",
        "branch_domain": "hidden interior, future ground, and unclear or developing aims",
        "privacy": "private",
    },
}

SOURCE_BASIS = [
    {
        "id": "local.four_pillars_palace_context",
        "label": "Ba Zi - The Four Pillars of Destiny",
        "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md",
        "basis": "Hour, Day, Month, and Year are read as Tian Gan/Di Zhi palace columns with life-stage/domain emphasis; adjacent interactions are weighted above separated contacts.",
    }
]


def build_palace_context(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    relationships: Optional[Dict[str, Any]] = None,
    auxiliary_stars: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    events = list((relationships or {}).get("events") or [])
    palaces: List[Dict[str, Any]] = []
    for pillar_name in PALACE_ORDER:
        context = PALACE_CONTEXT[pillar_name]
        pillar = pillars.get(pillar_name) if isinstance(pillars, dict) else None
        palace_events = _events_for_palace(events, pillar_name)
        auxiliary_refs = _auxiliary_refs_for_palace(auxiliary_stars or {}, pillar_name)
        row = {
            "pillar": pillar_name,
            "pillar_label": context["pillar_label"],
            "life_stage": context["life_stage"],
            "age_range": context["age_range"],
            "domain": PILLAR_DOMAIN_LABELS.get(pillar_name),
            "outer_domain": context["outer_domain"],
            "stem_domain": context["stem_domain"],
            "branch_domain": context["branch_domain"],
            "privacy": context["privacy"],
            "stem": _pillar_value(pillar, "stem"),
            "branch": _pillar_value(pillar, "branch"),
            "animal": _pillar_value(pillar, "animal"),
            "stem_element": _pillar_value(pillar, "stem_element"),
            "branch_element": _pillar_value(pillar, "branch_element"),
            "relationship_events": palace_events,
            "relationship_event_count": len(palace_events),
            "auxiliary_hits": auxiliary_refs,
            "auxiliary_hit_count": len(auxiliary_refs),
        }
        row["summary"] = _palace_summary(pillar_name, pillar, palace_events, auxiliary_refs)
        palaces.append(row)

    return {
        "status": "source_based_preview",
        "method": "four_pillar_palace_context_v1",
        "palaces": palaces,
        "focus": _focus_summary(palaces),
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        "notes": [
            "Palace context shows where relationship contacts and auxiliary markers land before interpretation assigns meaning.",
            "Timing-triggered contacts are treated as indirect unless they activate the natal palace directly.",
        ],
    }


def _events_for_palace(events: List[Dict[str, Any]], pillar_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        points = event.get("points") if isinstance(event.get("points"), list) else []
        matching = [
            point for point in points
            if isinstance(point, dict) and point.get("pillar") == pillar_name
        ]
        if not matching:
            continue
        rows.append({
            "id": event.get("id"),
            "label": event.get("label") or event.get("type") or "relationship code",
            "type": event.get("type"),
            "scope": event.get("scope"),
            "scope_label": event.get("scope_label"),
            "intensity": event.get("intensity"),
            "tone": _event_tone(event.get("type")),
            "other_palaces": _other_palace_labels(points, pillar_name),
            "placement_note": _placement_note(event.get("scope"), event.get("intensity")),
        })
    return rows


def _auxiliary_refs_for_palace(auxiliary_stars: Dict[str, Any], pillar_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    markers = auxiliary_stars.get("markers") if isinstance(auxiliary_stars, dict) else []
    if not isinstance(markers, list):
        markers = []
    if not markers and isinstance(auxiliary_stars, dict):
        peach = auxiliary_stars.get("peach_blossom") if isinstance(auxiliary_stars.get("peach_blossom"), dict) else None
        markers = [peach] if peach else []
    for marker in markers:
        if not isinstance(marker, dict):
            continue
        for activation in marker.get("activations") or []:
            if not isinstance(activation, dict):
                continue
            if activation.get("layer") == "natal" and activation.get("pillar") == pillar_name:
                rows.append({
                    "label": marker.get("label") or "Auxiliary marker",
                    "branch": activation.get("branch"),
                    "stem": activation.get("stem"),
                    "animal": activation.get("animal"),
                    "activation_state": marker.get("marker_state") or (marker.get("pressure") or {}).get("status"),
                })
    return rows


def _pillar_value(pillar: Optional[Dict[str, Any]], key: str) -> Optional[Any]:
    return pillar.get(key) if isinstance(pillar, dict) else None


def _other_palace_labels(points: List[Dict[str, Any]], pillar_name: str) -> List[str]:
    labels: List[str] = []
    for point in points:
        if not isinstance(point, dict) or point.get("pillar") == pillar_name:
            continue
        label = point.get("pillar_label") or str(point.get("pillar") or "").title()
        if label:
            labels.append(label)
    return labels


def _placement_note(scope: Any, intensity: Any) -> str:
    if scope in {"annual", "luck"}:
        return "timing-triggered indirect pressure"
    if intensity == "direct":
        return "adjacent palace contact"
    if intensity == "complete_set":
        return "complete branch-set pattern"
    if intensity == "repeated_branch":
        return "repeated palace branch"
    return "separated palace contact"


def _event_tone(event_type: Any) -> str:
    key = str(event_type or "")
    if key in {"branch_clash", "branch_harm", "branch_destruction", "branch_punishment", "self_punishment"}:
        return "challenging"
    if key in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination"}:
        return "supportive"
    return "mixed"


def _palace_summary(
    pillar_name: str,
    pillar: Optional[Dict[str, Any]],
    events: List[Dict[str, Any]],
    auxiliary_refs: List[Dict[str, Any]],
) -> str:
    context = PALACE_CONTEXT[pillar_name]
    stem = _pillar_value(pillar, "stem") or "-"
    branch = _pillar_value(pillar, "branch") or "-"
    summary = f"{context['pillar_label']} palace frames {context['outer_domain']} through {stem} {branch}."
    if events:
        summary += f" {len(events)} relationship contact(s) land here."
    if auxiliary_refs:
        summary += f" {len(auxiliary_refs)} auxiliary marker(s) land here."
    return summary


def _focus_summary(palaces: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not palaces:
        return {
            "status": "distributed",
            "summary": "No palace data is available.",
            "primary_pillar": None,
        }
    ranked = sorted(
        palaces,
        key=lambda row: (
            int(row.get("relationship_event_count") or 0) + int(row.get("auxiliary_hit_count") or 0),
            -PALACE_ORDER.index(str(row.get("pillar"))) if str(row.get("pillar")) in PALACE_ORDER else 0,
        ),
        reverse=True,
    )
    top = ranked[0]
    score = int(top.get("relationship_event_count") or 0) + int(top.get("auxiliary_hit_count") or 0)
    if score <= 0:
        return {
            "status": "distributed",
            "summary": "No single palace is strongly emphasized by the configured relationship-contact and auxiliary-star layers.",
            "primary_pillar": None,
        }
    return {
        "status": "focused",
        "summary": f"{top['pillar_label']} palace carries the strongest configured relationship/auxiliary emphasis.",
        "primary_pillar": top.get("pillar"),
    }
