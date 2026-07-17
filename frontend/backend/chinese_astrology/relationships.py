from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .curation import confidence_tags
from .tables import ten_god


PILLAR_DOMAIN_LABELS = {
    "year": "Ancestry / outer world",
    "month": "Family / career structure",
    "day": "Self / partner palace",
    "hour": "Future / inner aims",
}

STEM_COMBINATIONS = {
    frozenset(("Jia", "Ji")): {"element": "Earth", "label": "Jia-Ji combination"},
    frozenset(("Yi", "Geng")): {"element": "Metal", "label": "Yi-Geng combination"},
    frozenset(("Bing", "Xin")): {"element": "Water", "label": "Bing-Xin combination"},
    frozenset(("Ding", "Ren")): {"element": "Wood", "label": "Ding-Ren combination"},
    frozenset(("Wu", "Gui")): {"element": "Fire", "label": "Wu-Gui combination"},
}

BRANCH_COMBINATIONS = {
    frozenset(("Zi", "Chou")): {"element": "Earth", "label": "Zi-Chou branch combination"},
    frozenset(("Yin", "Hai")): {"element": "Wood", "label": "Yin-Hai branch combination"},
    frozenset(("Mao", "Xu")): {"element": "Fire", "label": "Mao-Xu branch combination"},
    frozenset(("Chen", "You")): {"element": "Metal", "label": "Chen-You branch combination"},
    frozenset(("Shen", "Si")): {"element": "Water", "label": "Shen-Si branch combination"},
    frozenset(("Wei", "Wu")): {"element": "Fire", "label": "Wei-Wu branch combination"},
}

THREE_HARMONY_COMBINATIONS = {
    frozenset(("Yin", "Wu", "Xu")): {"element": "Fire", "label": "Fire three-harmony combination"},
    frozenset(("Hai", "Mao", "Wei")): {"element": "Wood", "label": "Wood three-harmony combination"},
    frozenset(("Shen", "Zi", "Chen")): {"element": "Water", "label": "Water three-harmony combination"},
    frozenset(("Si", "You", "Chou")): {"element": "Metal", "label": "Metal three-harmony combination"},
}

SEASONAL_COMBINATIONS = {
    frozenset(("Yin", "Mao", "Chen")): {"element": "Wood", "label": "Spring seasonal combination"},
    frozenset(("Si", "Wu", "Wei")): {"element": "Fire", "label": "Summer seasonal combination"},
    frozenset(("Shen", "You", "Xu")): {"element": "Metal", "label": "Autumn seasonal combination"},
    frozenset(("Hai", "Zi", "Chou")): {"element": "Water", "label": "Winter seasonal combination"},
}

BRANCH_CLASHES = {
    frozenset(("Zi", "Wu")): "Zi-Wu clash",
    frozenset(("Chou", "Wei")): "Chou-Wei clash",
    frozenset(("Shen", "Yin")): "Shen-Yin clash",
    frozenset(("Mao", "You")): "Mao-You clash",
    frozenset(("Chen", "Xu")): "Chen-Xu clash",
    frozenset(("Si", "Hai")): "Si-Hai clash",
}

BRANCH_HARMS = {
    frozenset(("Zi", "Wei")): "Zi-Wei harm",
    frozenset(("Yin", "Si")): "Yin-Si harm",
    frozenset(("Shen", "Hai")): "Shen-Hai harm",
    frozenset(("Chou", "Wu")): "Chou-Wu harm",
    frozenset(("Mao", "Chen")): "Mao-Chen harm",
    frozenset(("You", "Xu")): "You-Xu harm",
}

BRANCH_DESTRUCTIONS = {
    frozenset(("Zi", "You")): "Zi-You destruction",
    frozenset(("Shen", "Si")): "Shen-Si destruction",
    frozenset(("Chen", "Chou")): "Chen-Chou destruction",
    frozenset(("Wu", "Mao")): "Wu-Mao destruction",
    frozenset(("Yin", "Hai")): "Yin-Hai destruction",
    frozenset(("Xu", "Wei")): "Xu-Wei destruction",
}

PUNISHMENT_PAIRS = {
    frozenset(("Yin", "Si")): {"subtype": "ungrateful", "label": "Yin-Si ungrateful punishment"},
    frozenset(("Si", "Shen")): {"subtype": "ungrateful", "label": "Si-Shen ungrateful punishment"},
    frozenset(("Shen", "Yin")): {"subtype": "ungrateful", "label": "Shen-Yin ungrateful punishment"},
    frozenset(("Wei", "Chou")): {"subtype": "bullying", "label": "Wei-Chou bullying punishment"},
    frozenset(("Chou", "Xu")): {"subtype": "bullying", "label": "Chou-Xu bullying punishment"},
    frozenset(("Xu", "Wei")): {"subtype": "bullying", "label": "Xu-Wei bullying punishment"},
    frozenset(("Zi", "Mao")): {"subtype": "uncivilized", "label": "Zi-Mao uncivilized punishment"},
}

SELF_PUNISHMENT_BRANCHES = {
    "Chen": "Chen self-punishment",
    "Wu": "Wu self-punishment",
    "You": "You self-punishment",
    "Hai": "Hai self-punishment",
}

FOUR_BRANCH_CROSSES = {
    frozenset(("Zi", "Wu", "You", "Mao")): {"subtype": "love_success", "label": "Love-success cross"},
    frozenset(("Chou", "Wei", "Xu", "Chen")): {"subtype": "artistic_literature", "label": "Artistic-literature cross"},
}

RELATIONSHIP_CONTEXT_PROFILES = {
    "general": {
        "label": "General",
        "summary": "General pair context keeps marriage-specific evidence conditional rather than assuming a spouse relationship.",
        "evidence_order": [
            "day_master_context",
            "useful_element_comparison",
            "individual_timing",
            "cross_chart_overlay",
        ],
        "conditional_evidence": ["natal_spouse_palace", "natal_spouse_star"],
        "excluded_evidence": [],
    },
    "romantic": {
        "label": "Romantic",
        "summary": "Romantic context begins with each natal spouse palace and spouse star, then reads individual timing and comparison evidence.",
        "evidence_order": [
            "natal_spouse_palace",
            "natal_spouse_star",
            "individual_timing",
            "day_master_context",
            "useful_element_comparison",
            "cross_chart_overlay",
        ],
        "conditional_evidence": [],
        "excluded_evidence": [],
    },
    "family": {
        "label": "Family",
        "summary": "Family context does not apply marriage-specific spouse-palace or spouse-star doctrine.",
        "evidence_order": [
            "day_master_context",
            "useful_element_comparison",
            "individual_timing",
            "cross_chart_overlay",
        ],
        "conditional_evidence": [],
        "excluded_evidence": ["natal_spouse_palace", "natal_spouse_star"],
    },
    "business": {
        "label": "Business",
        "summary": "Business context reads directional role, element, and timing evidence without importing marriage doctrine.",
        "evidence_order": [
            "day_master_context",
            "useful_element_comparison",
            "individual_timing",
            "cross_chart_overlay",
        ],
        "conditional_evidence": [],
        "excluded_evidence": ["natal_spouse_palace", "natal_spouse_star"],
    },
}

COMPATIBILITY_DOCTRINE_FIXTURE_IDS = {
    "general": "compatibility.doctrine_general_scope_v1",
    "romantic": "compatibility.doctrine_romantic_natal_priority_v1",
    "family": "compatibility.doctrine_family_scope_guard_v1",
    "business": "compatibility.doctrine_business_scope_guard_v1",
}
COMPATIBILITY_DOCTRINE_LIMIT_FIXTURE_ID = "compatibility.doctrine_cross_chart_limit_v1"


def analyze_relationships(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    natal_points = _natal_points(pillars)
    timing = timing or {}
    events: List[Dict[str, Any]] = []
    events.extend(_detect_within_scope(natal_points, scope="natal"))

    active_luck = timing.get("active_luck_pillar")
    if isinstance(active_luck, dict):
        events.extend(_detect_dynamic(natal_points, _timing_point(active_luck, "luck"), scope="luck"))

    annual = timing.get("annual_pillar")
    if isinstance(annual, dict):
        events.extend(_detect_dynamic(natal_points, _timing_point(annual, "annual"), scope="annual"))

    for key, scope in (
        ("flowing_month_pillar", "flowing_month"),
        ("flowing_day_pillar", "flowing_day"),
        ("flowing_hour_pillar", "flowing_hour"),
    ):
        pillar = timing.get(key)
        if isinstance(pillar, dict):
            events.extend(_detect_dynamic(natal_points, _timing_point(pillar, scope), scope=scope))

    return {
        "events": _sort_events(_dedupe_events(events)),
        "summary": _summary(events),
        "source_basis": "structural BaZi relationship-code tables: stem combinations, branch combinations, clashes, harms, punishments, destructions, and complete branch sets; timing contacts include current Luck, annual, flowing month, flowing day, and flowing hour layers when available",
        "source_confidence": confidence_tags("local_source", "computed_rule"),
    }


def analyze_pair_relationships(
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
    relationship_context: str = "general",
) -> Dict[str, Any]:
    relationship_context = _normalize_relationship_context(relationship_context)
    uncertain_subjects = _pair_boundary_uncertainty(primary_profile, relationship_profile)
    if uncertain_subjects:
        return {
            "status": "withheld",
            "method": "bazi_pair_qualitative_doctrine_v1",
            "relationship_context": relationship_context,
            "subjects": {
                "primary": _subject_summary(primary_profile, "Primary"),
                "relationship": _subject_summary(relationship_profile, "Relationship"),
            },
            "reason_code": "birth_time_boundary_uncertainty",
            "reason": "A recorded birth-time range crosses a BaZi pillar boundary.",
            "ambiguity": {
                "status": "requires_resolved_birth_time",
                "affected_subjects": uncertain_subjects,
                "message": (
                    "Pair doctrine is withheld because at least one birth time crosses a pillar boundary "
                    "within the recorded uncertainty window. Resolve that subject's birth-time range first."
                ),
            },
            "notes": [
                "No doctrine, score, grade, judgement, or cross-chart overlay is produced while a pillar boundary is unresolved.",
            ],
        }
    primary_points = _subject_points(primary_profile, "primary", "Primary")
    relationship_points = _subject_points(relationship_profile, "relationship", "Relationship")
    events: List[Dict[str, Any]] = []

    for primary_point in primary_points:
        for relationship_point in relationship_points:
            for event in _pair_events(primary_point, relationship_point, scope="pair", force_indirect=True):
                events.append(_pair_event_context(event))

    for event in _set_events([*primary_points, *relationship_points], scope="pair"):
        if _event_has_both_subjects(event):
            events.append(_pair_event_context(event))

    events = _sort_pair_events(_dedupe_events(events))
    timing_alignment = {
        "primary": _relationship_timing_profile(primary_profile, "Primary"),
        "relationship": _relationship_timing_profile(relationship_profile, "Relationship"),
    }
    day_master_exchange = _day_master_exchange(primary_profile, relationship_profile)
    doctrine = _pair_doctrine(
        primary_profile=primary_profile,
        relationship_profile=relationship_profile,
        events=events,
        timing_alignment=timing_alignment,
        day_master_exchange=day_master_exchange,
        relationship_context=relationship_context,
    )
    return {
        "status": "qualitative_evidence_only",
        "method": "bazi_pair_qualitative_doctrine_v1",
        "relationship_context": relationship_context,
        "subjects": {
            "primary": _subject_summary(primary_profile, "Primary"),
            "relationship": _subject_summary(relationship_profile, "Relationship"),
        },
        "day_master_exchange": day_master_exchange,
        "timing_alignment": timing_alignment,
        "doctrine": doctrine,
        "interpretation": doctrine["synthesis"],
        "events": events,
        "summary": _pair_overlay_summary(events),
        "source_basis": [
            {
                "id": "local.destiny_code_book1_spouse_doctrine",
                "pages": [246, 247],
                "basis": "The local source evaluates an individual's relationship context through the natal spouse palace and the Wealth or Influence spouse-star condition.",
            },
            {
                "id": "local.destiny_code_book2_relationship_timing",
                "pages": [299],
                "basis": "The local source treats spouse-star appearance and contacts to the natal spouse palace as individual timing evidence, not a pair outcome score.",
            },
            {
                "id": "local.lu_zhiji_spouse_star_context",
                "pages": [188, 189, 190, 191, 192, 193],
                "basis": "The local Chinese source supports sex-dependent spouse-star roles and natal chart condition.",
            },
            {
                "id": "local.destiny_code_book2_cross_chart_limit",
                "pages": [89],
                "basis": "The local source expressly limits Combination Codes to elemental association within one chart; cross-chart contacts are therefore isolated as a product comparison overlay with no outcome authority.",
            },
        ],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant", "needs_validation"),
        "notes": [
            "No aggregate compatibility score, grade, or outcome probability is computed.",
            "Source-backed natal spouse-palace, spouse-star, and timing evidence is kept separate for each subject.",
            "Day Master and useful-element comparisons are directional context, not proof that one chart supplies or fixes another.",
            "Cross-chart stem and branch contacts are a product comparison overlay, not a classical matching verdict.",
            f"Context profile: {RELATIONSHIP_CONTEXT_PROFILES[relationship_context]['label']} - {RELATIONSHIP_CONTEXT_PROFILES[relationship_context]['summary']}",
        ],
    }


def _pair_boundary_uncertainty(
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    affected: List[Dict[str, Any]] = []
    for key, fallback_label, profile in (
        ("primary", "Primary", primary_profile),
        ("relationship", "Relationship", relationship_profile),
    ):
        uncertainty = profile.get("uncertainty") if isinstance(profile, dict) else {}
        birth_time = uncertainty.get("birth_time") if isinstance(uncertainty, dict) else {}
        calculation_status = profile.get("calculation_status") if isinstance(profile, dict) else None
        is_uncertain = calculation_status == "uncertain_birth_time_boundary"
        if isinstance(birth_time, dict):
            is_uncertain = is_uncertain or birth_time.get("status") == "uncertain"
        if not is_uncertain:
            continue
        affected.append({
            "subject": key,
            "subject_label": (
                profile.get("snap_label") if isinstance(profile, dict) else None
            ) or fallback_label,
            "calculation_status": calculation_status,
            "birth_time": birth_time if isinstance(birth_time, dict) else {},
        })
    return affected


def _natal_points(pillars: Dict[str, Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for order, pillar_name in enumerate(("year", "month", "day", "hour")):
        pillar = pillars.get(pillar_name)
        if not pillar:
            continue
        points.append(_point_from_pillar(pillar, "natal", pillar_name, order))
    return points


TIMING_EVENT_LAYERS = {"luck", "annual", "flowing_month", "flowing_day", "flowing_hour"}


def _timing_point(pillar: Dict[str, Any], layer: str) -> Dict[str, Any]:
    order = {
        "luck": 4,
        "annual": 5,
        "flowing_month": 6,
        "flowing_day": 7,
        "flowing_hour": 8,
    }.get(layer, 9)
    return _point_from_pillar(pillar, layer, layer, order)


def _point_from_pillar(pillar: Dict[str, Any], layer: str, pillar_name: str, order: int) -> Dict[str, Any]:
    return {
        "layer": layer,
        "pillar": pillar_name,
        "order": order,
        "stem": pillar.get("stem"),
        "branch": pillar.get("branch"),
        "animal": pillar.get("animal"),
        "stem_element": pillar.get("stem_element"),
        "branch_element": pillar.get("branch_element"),
        "ten_god": pillar.get("ten_god"),
        "five_factor": pillar.get("five_factor"),
        "domain": PILLAR_DOMAIN_LABELS.get(pillar_name, _timing_domain(layer)),
    }


def _subject_points(profile: Dict[str, Any], subject: str, subject_label: str) -> List[Dict[str, Any]]:
    pillars = profile.get("pillars") if isinstance(profile, dict) else {}
    if not isinstance(pillars, dict):
        return []
    points: List[Dict[str, Any]] = []
    for order, pillar_name in enumerate(("year", "month", "day", "hour")):
        pillar = pillars.get(pillar_name)
        if not pillar:
            continue
        point = _point_from_pillar(pillar, "pair", pillar_name, order)
        point["subject"] = subject
        point["subject_label"] = subject_label
        point["domain"] = f"{subject_label}: {point.get('domain')}"
        points.append(point)
    return points


def _timing_domain(layer: str) -> str:
    if layer == "luck":
        return "Current 10-year luck pillar"
    if layer == "annual":
        return "Current BaZi year"
    if layer == "flowing_month":
        return "Current flowing month"
    if layer == "flowing_day":
        return "Current flowing day"
    if layer == "flowing_hour":
        return "Current flowing hour"
    return layer


def _detect_within_scope(points: Sequence[Dict[str, Any]], scope: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for left, right in combinations(points, 2):
        events.extend(_pair_events(left, right, scope=scope))
    events.extend(_set_events(points, scope=scope))
    events.extend(_self_punishment_events(points, scope=scope))
    return events


def _detect_dynamic(natal_points: Sequence[Dict[str, Any]], timing_point: Dict[str, Any], scope: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for natal_point in natal_points:
        events.extend(_pair_events(natal_point, timing_point, scope=scope, force_indirect=True))
    events.extend(_set_events([*natal_points, timing_point], scope=scope, require_timing=True))
    events.extend(
        _self_punishment_events(
            [*natal_points, timing_point],
            scope=scope,
            require_timing=True,
        )
    )
    return events


def _pair_events(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    scope: str,
    force_indirect: bool = False,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    stem_pair = frozenset((left.get("stem"), right.get("stem")))
    branch_pair = frozenset((left.get("branch"), right.get("branch")))
    separation = abs(int(left.get("order") or 0) - int(right.get("order") or 0))
    intensity = "indirect" if force_indirect else ("direct" if separation == 1 else "indirect")

    combo = STEM_COMBINATIONS.get(stem_pair)
    if combo and (force_indirect or separation <= 2):
        events.append(_event(
            event_type="stem_combination",
            label=combo["label"],
            points=(left, right),
            scope=scope,
            intensity=intensity,
            element=combo["element"],
            symbols=tuple(stem_pair),
        ))

    combo = BRANCH_COMBINATIONS.get(branch_pair)
    if combo and (force_indirect or separation <= 2):
        events.append(_event(
            event_type="branch_combination",
            label=combo["label"],
            points=(left, right),
            scope=scope,
            intensity=intensity,
            element=combo["element"],
            symbols=tuple(branch_pair),
        ))

    clash = BRANCH_CLASHES.get(branch_pair)
    if clash:
        events.append(_event("branch_clash", clash, (left, right), scope, intensity, symbols=tuple(branch_pair)))

    harm = BRANCH_HARMS.get(branch_pair)
    if harm:
        events.append(_event("branch_harm", harm, (left, right), scope, intensity, symbols=tuple(branch_pair)))

    destruction = BRANCH_DESTRUCTIONS.get(branch_pair)
    if destruction:
        events.append(_event("branch_destruction", destruction, (left, right), scope, intensity, symbols=tuple(branch_pair)))

    punishment = PUNISHMENT_PAIRS.get(branch_pair)
    if punishment:
        events.append(_event(
            event_type="branch_punishment",
            label=punishment["label"],
            points=(left, right),
            scope=scope,
            intensity=intensity,
            subtype=punishment["subtype"],
            symbols=tuple(branch_pair),
        ))

    return events


def _set_events(
    points: Sequence[Dict[str, Any]],
    *,
    scope: str,
    require_timing: bool = False,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for table, event_type in (
        (THREE_HARMONY_COMBINATIONS, "three_harmony_combination"),
        (SEASONAL_COMBINATIONS, "seasonal_combination"),
        (FOUR_BRANCH_CROSSES, "branch_cross"),
    ):
        for branch_set, meta in table.items():
            matched = _points_for_branches(points, branch_set)
            if len({point.get("branch") for point in matched}) != len(branch_set):
                continue
            if require_timing and not any(point.get("layer") in TIMING_EVENT_LAYERS for point in matched):
                continue
            events.append(_event(
                event_type=event_type,
                label=meta["label"],
                points=tuple(matched),
                scope=scope,
                intensity="complete_set",
                element=meta.get("element"),
                subtype=meta.get("subtype"),
                symbols=tuple(sorted(branch_set)),
            ))
    return events


def _self_punishment_events(
    points: Sequence[Dict[str, Any]],
    *,
    scope: str,
    require_timing: bool = False,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    by_branch: Dict[str, List[Dict[str, Any]]] = {}
    for point in points:
        branch = point.get("branch")
        if branch in SELF_PUNISHMENT_BRANCHES:
            by_branch.setdefault(str(branch), []).append(point)
    for branch, matched in by_branch.items():
        if len(matched) < 2:
            continue
        if require_timing and not any(point.get("layer") in TIMING_EVENT_LAYERS for point in matched):
            continue
        events.append(_event(
            event_type="self_punishment",
            label=SELF_PUNISHMENT_BRANCHES[branch],
            points=tuple(matched),
            scope=scope,
            intensity="repeated_branch",
            subtype="self",
            symbols=(branch,),
        ))
    return events


def _points_for_branches(points: Sequence[Dict[str, Any]], branch_set: Iterable[str]) -> List[Dict[str, Any]]:
    wanted = set(branch_set)
    matched: List[Dict[str, Any]] = []
    seen = set()
    for point in points:
        branch = point.get("branch")
        if branch in wanted and branch not in seen:
            matched.append(point)
            seen.add(branch)
    return matched


def _event(
    event_type: str,
    label: str,
    points: Sequence[Dict[str, Any]],
    scope: str,
    intensity: str,
    *,
    element: Optional[str] = None,
    subtype: Optional[str] = None,
    symbols: Sequence[str] = (),
) -> Dict[str, Any]:
    point_payloads = [_event_point(point) for point in points]
    point_ids = [
        f"{point.get('subject')}:{point['pillar']}" if point.get("subject") else point["pillar"]
        for point in point_payloads
    ]
    return {
        "id": f"{scope}:{event_type}:{':'.join(sorted(str(symbol) for symbol in symbols if symbol))}:{':'.join(point_ids)}",
        "type": event_type,
        "subtype": subtype,
        "label": label,
        "scope": scope,
        "scope_label": _scope_label(scope),
        "intensity": intensity,
        "element": element,
        "symbols": [symbol for symbol in symbols if symbol],
        "points": point_payloads,
        "affected_palaces": [point["pillar_label"] for point in point_payloads],
        "affected_domains": [point["domain"] for point in point_payloads],
        "notes_key": f"{event_type}_{'_'.join(sorted(str(symbol).lower() for symbol in symbols if symbol))}",
    }


def _event_point(point: Dict[str, Any]) -> Dict[str, Any]:
    pillar = str(point.get("pillar") or "")
    subject_label = point.get("subject_label")
    pillar_label = _pillar_label(pillar)
    return {
        "subject": point.get("subject"),
        "subject_label": subject_label,
        "layer": point.get("layer"),
        "pillar": pillar,
        "pillar_label": f"{subject_label} {pillar_label}" if subject_label else pillar_label,
        "stem": point.get("stem"),
        "branch": point.get("branch"),
        "animal": point.get("animal"),
        "domain": point.get("domain"),
        "ten_god": point.get("ten_god"),
        "five_factor": point.get("five_factor"),
    }


def _pillar_label(pillar: str) -> str:
    labels = {
        "year": "Year",
        "month": "Month",
        "day": "Day",
        "hour": "Hour",
        "luck": "Current Luck",
        "annual": "Current Year",
        "flowing_month": "Flowing Month",
        "flowing_day": "Flowing Day",
        "flowing_hour": "Flowing Hour",
    }
    return labels.get(pillar, pillar.title())


def _scope_label(scope: str) -> str:
    if scope == "luck":
        return "Current 10-Year Luck"
    if scope == "annual":
        return "Current Year"
    if scope == "flowing_month":
        return "Flowing Month"
    if scope == "flowing_day":
        return "Flowing Day"
    if scope == "flowing_hour":
        return "Flowing Hour"
    if scope == "pair":
        return "Pair"
    return "Natal"


def _dedupe_events(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for event in events:
        deduped[event["id"]] = event
    return list(deduped.values())


def _sort_events(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scope_rank = {"natal": 0, "luck": 1, "annual": 2, "flowing_month": 3, "flowing_day": 4, "flowing_hour": 5, "pair": 6}
    type_rank = {
        "branch_clash": 0,
        "branch_harm": 1,
        "branch_punishment": 2,
        "self_punishment": 3,
        "branch_destruction": 4,
        "stem_combination": 5,
        "branch_combination": 6,
        "three_harmony_combination": 7,
        "seasonal_combination": 8,
        "branch_cross": 9,
    }
    return sorted(events, key=lambda event: (
        scope_rank.get(str(event.get("scope")), 9),
        type_rank.get(str(event.get("type")), 99),
        str(event.get("label") or ""),
    ))


def _summary(events: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    deduped = _dedupe_events(events)
    counts: Dict[str, int] = {
        "total": len(deduped),
        "natal": 0,
        "luck": 0,
        "annual": 0,
        "flowing_month": 0,
        "flowing_day": 0,
        "flowing_hour": 0,
    }
    for event in deduped:
        scope = str(event.get("scope") or "")
        counts[scope] = counts.get(scope, 0) + 1
        event_type = str(event.get("type") or "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _event_has_both_subjects(event: Dict[str, Any]) -> bool:
    subjects = {point.get("subject") for point in event.get("points") or []}
    return "primary" in subjects and "relationship" in subjects


def _pair_event_context(event: Dict[str, Any]) -> Dict[str, Any]:
    points = event.get("points") if isinstance(event, dict) else []
    pillars = [str(point.get("pillar") or "") for point in points if isinstance(point, dict)]
    same_pillar = len(set(pillars)) == 1 and bool(pillars)
    day_contact = "day" in pillars
    if day_contact and same_pillar:
        intensity = "day_partner_palace"
    elif day_contact:
        intensity = "partner_palace_contact"
    elif same_pillar:
        intensity = "matched_pillar"
    else:
        intensity = "cross_pillar"
    contact_family = _pair_contact_family(event.get("type"))
    return {
        **event,
        "intensity": intensity,
        "contact_family": contact_family,
        "reading_note": _pair_event_note(event.get("type"), intensity, contact_family),
    }


def _pair_contact_family(event_type: Any) -> str:
    raw = str(event_type or "")
    if raw in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination"}:
        return "combination_contact"
    if raw in {"branch_clash", "branch_harm", "branch_punishment", "self_punishment", "branch_destruction"}:
        return "pressure_contact"
    return "other_contact"


def _pair_tone(event_type: Any) -> str:
    raw = str(event_type or "")
    if raw in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination"}:
        return "supportive"
    if raw in {"branch_clash", "branch_harm", "branch_punishment", "self_punishment", "branch_destruction"}:
        return "challenging"
    return "mixed"


def _pair_event_note(event_type: Any, intensity: str, contact_family: str) -> str:
    if contact_family == "combination_contact":
        base = "The comparison overlay found a combination-form elemental association; it is not evidence of interpersonal compatibility."
    elif contact_family == "pressure_contact":
        base = "The comparison overlay found a pressure-form contact; it does not by itself predict conflict between two people."
    else:
        base = "The comparison overlay found a configured contact that has no standalone interpersonal meaning."
    if intensity == "day_partner_palace":
        return f"{base} Both Day branches are involved, so each natal spouse-palace condition should be reviewed separately."
    if intensity == "partner_palace_contact":
        return f"{base} One Day branch is involved, but the cross-chart contact has no source-backed outcome authority."
    if intensity == "matched_pillar":
        return f"{base} The same pillar position appears in both charts."
    return base


def _sort_pair_events(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    intensity_rank = {
        "day_partner_palace": 0,
        "partner_palace_contact": 1,
        "matched_pillar": 2,
        "cross_pillar": 3,
    }
    family_rank = {"pressure_contact": 0, "other_contact": 1, "combination_contact": 2}
    return sorted(events, key=lambda event: (
        intensity_rank.get(str(event.get("intensity")), 9),
        family_rank.get(str(event.get("contact_family")), 9),
        str(event.get("label") or ""),
    ))


def _pair_overlay_summary(events: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "total": len(events),
        "combination_contacts": 0,
        "pressure_contacts": 0,
        "other_contacts": 0,
        "day_partner_palace": 0,
        "partner_palace_contact": 0,
        "matched_pillar": 0,
        "cross_pillar": 0,
    }
    for event in events:
        family = str(event.get("contact_family") or _pair_contact_family(event.get("type")))
        intensity = str(event.get("intensity") or "cross_pillar")
        event_type = str(event.get("type") or "unknown")
        family_key = {
            "combination_contact": "combination_contacts",
            "pressure_contact": "pressure_contacts",
        }.get(family, "other_contacts")
        counts[family_key] = counts.get(family_key, 0) + 1
        counts[intensity] = counts.get(intensity, 0) + 1
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _normalize_relationship_context(value: Any) -> str:
    raw = str(value or "general").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "default": "general",
        "pair": "general",
        "partner": "romantic",
        "marriage": "romantic",
        "love": "romantic",
        "romance": "romantic",
        "kin": "family",
        "parent_child": "family",
        "parent": "family",
        "sibling": "family",
        "work": "business",
        "career": "business",
        "commerce": "business",
        "partnership": "business",
    }
    key = aliases.get(raw, raw)
    return key if key in RELATIONSHIP_CONTEXT_PROFILES else "general"


def _relationship_timing_profile(profile: Dict[str, Any], fallback_label: str) -> Dict[str, Any]:
    pillars = profile.get("pillars") if isinstance(profile, dict) else {}
    day_pillar = pillars.get("day") if isinstance(pillars, dict) else None
    relationships = profile.get("relationships") if isinstance(profile, dict) else {}
    events = relationships.get("events") if isinstance(relationships, dict) else []
    day_events = [
        event for event in (events if isinstance(events, list) else [])
        if _event_touches_pillar(event, "day")
    ]
    natal_events = [event for event in day_events if event.get("scope") == "natal"]
    active_events = [event for event in day_events if event.get("scope") in {"luck", "annual"}]
    challenging_active = [event for event in active_events if _pair_tone(event.get("type")) == "challenging"]
    supportive_active = [event for event in active_events if _pair_tone(event.get("type")) == "supportive"]
    challenging_natal = [event for event in natal_events if _pair_tone(event.get("type")) == "challenging"]
    supportive_natal = [event for event in natal_events if _pair_tone(event.get("type")) == "supportive"]
    status = "quiet"
    if challenging_active:
        status = "active_pressure"
    elif supportive_active:
        status = "active_support"
    elif active_events:
        status = "active_mixed"
    elif challenging_natal:
        status = "natal_pressure"
    elif supportive_natal:
        status = "natal_support"
    elif natal_events:
        status = "natal_mixed"

    timing = profile.get("timing") if isinstance(profile, dict) else {}
    active_luck = timing.get("active_luck_pillar") if isinstance(timing, dict) else None
    annual = timing.get("annual_pillar") if isinstance(timing, dict) else None
    return {
        "status": status,
        "subject_label": (profile.get("snap_label") if isinstance(profile, dict) else None) or fallback_label,
        "spouse_palace": _spouse_palace_payload(day_pillar),
        "counts": {
            "day_events": len(day_events),
            "natal": len(natal_events),
            "active": len(active_events),
            "challenging_active": len(challenging_active),
            "supportive_active": len(supportive_active),
            "challenging_natal": len(challenging_natal),
            "supportive_natal": len(supportive_natal),
        },
        "active_luck_pillar": _timing_pillar_summary(active_luck),
        "annual_pillar": _timing_pillar_summary(annual),
        "top_events": [_compact_event(event) for event in [*active_events, *natal_events][:4]],
        "reading_note": _timing_profile_note(status),
    }


def _event_touches_pillar(event: Dict[str, Any], pillar_name: str) -> bool:
    points = event.get("points") if isinstance(event, dict) else []
    return any(isinstance(point, dict) and point.get("pillar") == pillar_name for point in points or [])


def _spouse_palace_payload(day_pillar: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(day_pillar, dict):
        return None
    return {
        "stem": day_pillar.get("stem"),
        "branch": day_pillar.get("branch"),
        "animal": day_pillar.get("animal"),
        "stem_element": day_pillar.get("stem_element"),
        "branch_element": day_pillar.get("branch_element"),
    }


def _timing_pillar_summary(pillar: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(pillar, dict):
        return None
    return {
        "stem": pillar.get("stem"),
        "branch": pillar.get("branch"),
        "animal": pillar.get("animal"),
        "ten_god": pillar.get("ten_god"),
        "five_factor": pillar.get("five_factor"),
        "age_label": pillar.get("age_label"),
        "bazi_year": pillar.get("bazi_year"),
    }


def _compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": event.get("id"),
        "type": event.get("type"),
        "label": event.get("label"),
        "scope": event.get("scope"),
        "scope_label": event.get("scope_label"),
        "tone": _pair_tone(event.get("type")),
        "symbols": event.get("symbols") if isinstance(event.get("symbols"), list) else [],
        "affected_palaces": event.get("affected_palaces") if isinstance(event.get("affected_palaces"), list) else [],
    }


def _timing_profile_note(status: str) -> str:
    if status == "active_pressure":
        return "Current timing is pressing the Day pillar / spouse palace through a challenging relationship contact."
    if status == "active_support":
        return "Current timing is contacting the Day pillar / spouse palace through a supportive combination."
    if status == "active_mixed":
        return "Current timing is touching the Day pillar / spouse palace, but the contact is mixed until chart context is weighed."
    if status == "natal_pressure":
        return "Natal partner-palace pressure is present even without an active timing trigger."
    if status == "natal_support":
        return "Natal partner-palace support is present through a configured combination."
    if status == "natal_mixed":
        return "Natal partner-palace contact is present and needs element/favorability review."
    return "No configured relationship-contact pressure is concentrated on the Day pillar / spouse palace."


COMPATIBILITY_DOCTRINE_LAYER_META = {
    "natal_spouse_palace": {
        "label": "Natal spouse palace",
        "source_scope": "individual_natal_relationship_doctrine",
    },
    "natal_spouse_star": {
        "label": "Natal spouse star",
        "source_scope": "individual_natal_relationship_doctrine",
    },
    "individual_timing": {
        "label": "Individual relationship timing",
        "source_scope": "individual_timing_doctrine",
    },
    "day_master_context": {
        "label": "Directional Day Master context",
        "source_scope": "contextual_comparison_observation",
    },
    "useful_element_comparison": {
        "label": "Unweighted element-presence comparison",
        "source_scope": "presence_only_contextual_comparison",
    },
    "cross_chart_overlay": {
        "label": "Cross-chart contact overlay",
        "source_scope": "product_defined_comparison_overlay",
    },
}


def _pair_doctrine(
    *,
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
    events: Sequence[Dict[str, Any]],
    timing_alignment: Dict[str, Any],
    day_master_exchange: Dict[str, Any],
    relationship_context: str,
) -> Dict[str, Any]:
    relationship_context = _normalize_relationship_context(relationship_context)
    context_profile = RELATIONSHIP_CONTEXT_PROFILES[relationship_context]
    layers = {
        "natal_spouse_palace": _natal_spouse_palace_layer(primary_profile, relationship_profile),
        "natal_spouse_star": _spouse_star_exchange(primary_profile, relationship_profile),
        "individual_timing": _individual_timing_layer(timing_alignment),
        "day_master_context": {
            **day_master_exchange,
            "method": "directional_ten_god_context_v1",
            "source_scope": "contextual_comparison_observation",
            "outcome_authority": "none",
        },
        "useful_element_comparison": _useful_element_comparison(primary_profile, relationship_profile),
        "cross_chart_overlay": _cross_chart_overlay(events),
    }
    evidence_order = [
        _doctrine_evidence_row(key, layers.get(key), applicability="primary")
        for key in context_profile["evidence_order"]
    ]
    conditional_evidence = [
        _doctrine_evidence_row(key, layers.get(key), applicability="conditional")
        for key in context_profile["conditional_evidence"]
    ]
    fixture_ids = [
        COMPATIBILITY_DOCTRINE_FIXTURE_IDS[relationship_context],
        COMPATIBILITY_DOCTRINE_LIMIT_FIXTURE_ID,
    ]
    synthesis = _doctrine_synthesis(
        relationship_context=relationship_context,
        context_profile=context_profile,
        layers=layers,
        events=events,
    )
    return {
        "status": "qualitative_evidence_only",
        "method": "bazi_pair_qualitative_doctrine_v1",
        "relationship_context": relationship_context,
        "context_profile": {
            "key": relationship_context,
            "label": context_profile["label"],
            "summary": context_profile["summary"],
            "evidence_order": list(context_profile["evidence_order"]),
            "conditional_evidence": list(context_profile["conditional_evidence"]),
            "excluded_evidence": list(context_profile["excluded_evidence"]),
        },
        "aggregate_policy": {
            "mode": "none",
            "reason": "The curated sources do not provide a validated aggregate pair formula, band, or outcome probability.",
        },
        "evidence_order": evidence_order,
        "conditional_evidence": conditional_evidence,
        "layers": layers,
        "synthesis": synthesis,
        "fixture_ids": fixture_ids,
        "source_evidence": _compatibility_doctrine_source_evidence(fixture_ids),
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant", "needs_validation"),
        "interpretive_limits": [
            "Natal spouse-palace, spouse-star, and timing evidence describes each subject separately.",
            "Directional Day Master and element-presence comparisons are contextual observations, not relationship outcomes.",
            "Raw element totals are unweighted presence inventory; they are not qi strength and do not prove supply.",
            "Cross-chart contact detection is a product overlay because the cited Combination Codes source expressly limits those codes to one chart.",
            "No aggregate compatibility score, grade, or prediction is produced.",
        ],
    }


def _doctrine_evidence_row(key: str, layer: Any, *, applicability: str) -> Dict[str, Any]:
    meta = COMPATIBILITY_DOCTRINE_LAYER_META[key]
    payload = layer if isinstance(layer, dict) else {}
    return {
        "key": key,
        "label": meta["label"],
        "status": payload.get("status") or "unavailable",
        "applicability": applicability,
        "source_scope": meta["source_scope"],
    }


def _compatibility_doctrine_source_evidence(fixture_ids: Sequence[str]) -> List[Dict[str, Any]]:
    return [
        {
            "source_id": "local.destiny_code_book1_spouse_doctrine",
            "page_refs": [246, 247],
            "claim_scope": "individual_natal_relationship_context",
            "supports": ["natal_spouse_palace", "natal_spouse_star"],
            "fixture_ids": list(fixture_ids),
        },
        {
            "source_id": "local.destiny_code_book2_relationship_timing",
            "page_refs": [299],
            "claim_scope": "individual_relationship_timing",
            "supports": ["individual_timing"],
            "fixture_ids": list(fixture_ids),
        },
        {
            "source_id": "local.lu_zhiji_spouse_star_context",
            "page_refs": [188, 189, 190, 191, 192, 193],
            "claim_scope": "individual_natal_spouse_star",
            "supports": ["natal_spouse_star"],
            "fixture_ids": list(fixture_ids),
        },
        {
            "source_id": "local.destiny_code_book2_cross_chart_limit",
            "page_refs": [89],
            "claim_scope": "explicit_method_limit",
            "limits": ["cross_chart_overlay", "aggregate_pair_verdict"],
            "fixture_ids": [COMPATIBILITY_DOCTRINE_LIMIT_FIXTURE_ID],
        },
    ]


def _element_candidate_role(profile: Dict[str, Any], element: Any) -> Dict[str, Any]:
    element = str(element or "")
    useful = profile.get("useful_elements") if isinstance(profile, dict) else {}
    if not element or not isinstance(useful, dict):
        return {
            "status": "unresolved",
            "element": element or None,
            "candidate_role": "unresolved",
            "useful_element_status": None,
        }
    for group, candidate_role in (
        ("favorable", "favorable_candidate"),
        ("unfavorable", "unfavorable_candidate"),
    ):
        for row in useful.get(group) or []:
            if isinstance(row, dict) and row.get("element") == element:
                return {
                    "status": "available",
                    "element": element,
                    "candidate_role": candidate_role,
                    "role": row.get("role"),
                    "useful_element_status": useful.get("status"),
                }
    return {
        "status": "available" if useful.get("status") else "unresolved",
        "element": element,
        "candidate_role": "unresolved",
        "useful_element_status": useful.get("status"),
    }


def _spouse_palace_condition(profile: Dict[str, Any], fallback_label: str) -> Dict[str, Any]:
    pillars = profile.get("pillars") if isinstance(profile, dict) else {}
    day_pillar = pillars.get("day") if isinstance(pillars, dict) else None
    palace = _spouse_palace_payload(day_pillar)
    if not palace:
        return {
            "status": "unavailable",
            "subject_label": fallback_label,
            "summary": "The Day branch is unavailable, so this subject's natal spouse-palace condition cannot be reviewed.",
        }
    element_context = _element_candidate_role(profile, palace.get("branch_element"))
    return {
        "status": "available",
        "subject_label": (profile.get("snap_label") if isinstance(profile, dict) else None) or fallback_label,
        "palace": palace,
        "element_context": element_context,
        "source_scope": "individual_natal_relationship_context",
        "outcome_authority": "individual_context_only",
        "summary": (
            f"{palace.get('branch') or 'Unknown'} is this subject's natal Day branch / spouse palace. "
            "Its element-candidate role is individual natal context and is not a verdict about the pair."
        ),
    }


def _natal_spouse_palace_layer(
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
) -> Dict[str, Any]:
    subjects = {
        "primary": _spouse_palace_condition(primary_profile, "Primary"),
        "relationship": _spouse_palace_condition(relationship_profile, "Relationship"),
    }
    available = sum(1 for row in subjects.values() if row.get("status") == "available")
    return {
        "status": "available" if available == 2 else ("partial" if available else "unavailable"),
        "method": "natal_spouse_palace_condition_v1",
        "subjects": subjects,
        "source_scope": "individual_natal_relationship_doctrine",
        "outcome_authority": "individual_context_only",
        "summary": "Each natal Day branch / spouse palace is reviewed separately; cross-chart contacts do not determine its condition.",
    }


def _presence_inventory(profile: Dict[str, Any]) -> Dict[str, Any]:
    inventory = profile.get("element_presence") if isinstance(profile, dict) else {}
    if not isinstance(inventory, dict) or not inventory:
        inventory = profile.get("element_balance") if isinstance(profile, dict) else {}
    counts = {}
    if isinstance(inventory, dict):
        counts = inventory.get("counts") or inventory.get("total") or {}
    return {
        "status": "available" if isinstance(counts, dict) and bool(counts) else "unavailable",
        "model_id": (
            inventory.get("model_id") if isinstance(inventory, dict) else None
        ) or "legacy_element_presence_counts",
        "measure": (
            inventory.get("measure") if isinstance(inventory, dict) else None
        ) or "unweighted_presence_count",
        "counts": counts if isinstance(counts, dict) else {},
        "is_qi_strength": False,
    }


def _one_way_element_presence_context(
    receiver_profile: Dict[str, Any],
    compared_profile: Dict[str, Any],
) -> Dict[str, Any]:
    useful = receiver_profile.get("useful_elements") if isinstance(receiver_profile, dict) else {}
    inventory = _presence_inventory(compared_profile)
    counts = inventory["counts"]
    if not isinstance(useful, dict) or inventory["status"] != "available":
        return {
            "status": "unavailable",
            "inventory_basis": "unweighted_element_presence",
            "inventory_model_id": inventory["model_id"],
            "inventory_measure": inventory["measure"],
            "favorable_candidate_matches": [],
            "unfavorable_candidate_matches": [],
            "outcome_authority": "none",
        }

    def matches(group: str, candidate_role: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for candidate in useful.get(group) or []:
            if not isinstance(candidate, dict) or not candidate.get("element"):
                continue
            element = str(candidate["element"])
            count = int(counts.get(element) or 0)
            if count <= 0:
                continue
            rows.append({
                "element": element,
                "role": candidate.get("role"),
                "candidate_role": candidate_role,
                "presence_count": count,
                "presence_status": "present_only",
            })
        return rows

    favorable = matches("favorable", "favorable_candidate")
    unfavorable = matches("unfavorable", "unfavorable_candidate")
    useful_status = str(useful.get("status") or "unresolved")
    return {
        "status": "available" if useful_status != "withheld" else "partial",
        "useful_element_status": useful_status,
        "inventory_basis": "unweighted_element_presence",
        "inventory_model_id": inventory["model_id"],
        "inventory_measure": inventory["measure"],
        "semantics": {
            "is_qi_strength": False,
            "interpretation": "A match records element presence only; it does not establish usable qi, strength, or support from one chart to another.",
        },
        "favorable_candidate_matches": favorable,
        "unfavorable_candidate_matches": unfavorable,
        "outcome_authority": "none",
    }


def _useful_element_comparison(
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
) -> Dict[str, Any]:
    directions = {
        "primary_context": _one_way_element_presence_context(primary_profile, relationship_profile),
        "relationship_context": _one_way_element_presence_context(relationship_profile, primary_profile),
    }
    available = sum(1 for row in directions.values() if row.get("status") in {"available", "partial"})
    return {
        "status": "available" if available == 2 else ("partial" if available else "unavailable"),
        "method": "directional_element_presence_context_v1",
        "directions": directions,
        "source_scope": "presence_only_contextual_comparison",
        "inventory_basis": "unweighted_element_presence",
        "outcome_authority": "none",
        "summary": "The comparison records unweighted element presence against each subject's provisional candidates; presence is not qi strength or supply.",
    }


def _individual_timing_layer(timing_alignment: Dict[str, Any]) -> Dict[str, Any]:
    subjects = {
        key: value
        for key, value in timing_alignment.items()
        if key in {"primary", "relationship"} and isinstance(value, dict)
    }
    available = len(subjects)
    return {
        "status": "available" if available == 2 else ("partial" if available else "unavailable"),
        "method": "individual_relationship_timing_context_v1",
        "subjects": subjects,
        "source_scope": "individual_timing_doctrine",
        "outcome_authority": "individual_context_only",
        "summary": "Luck and annual contacts are retained as separate timing context for each subject; they are not merged into a pair outcome.",
    }


def _cross_chart_overlay(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    summary = _pair_overlay_summary(events)
    return {
        "status": "contacts_present" if summary["total"] else "quiet",
        "method": "product_defined_cross_chart_contact_overlay_v1",
        "summary": summary,
        "source_scope": "product_defined_comparison_overlay",
        "outcome_authority": "none",
        "limitation": (
            "The cited Combination Codes source defines elemental association within one BaZi chart. "
            "Cross-chart contacts are shown only as a comparison overlay and cannot support an interpersonal verdict."
        ),
    }


def _doctrine_synthesis(
    *,
    relationship_context: str,
    context_profile: Dict[str, Any],
    layers: Dict[str, Any],
    events: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    spouse_star = layers.get("natal_spouse_star") or {}
    timing = layers.get("individual_timing") or {}
    timing_subjects = timing.get("subjects") if isinstance(timing, dict) else {}
    active_timing = [
        key
        for key, row in (timing_subjects or {}).items()
        if isinstance(row, dict) and str(row.get("status") or "").startswith("active")
    ]
    if relationship_context == "romantic" and spouse_star.get("status") == "unknown":
        focus = "missing_natal_spouse_star_input"
        headline = "Calculation sex is needed before the natal spouse-star layer can be completed."
    elif active_timing:
        focus = "individual_timing_context"
        headline = "At least one subject has active individual relationship-timing evidence to review."
    elif relationship_context == "romantic":
        focus = "individual_natal_relationship_context"
        headline = "Read each natal spouse palace and spouse star separately before comparison overlays."
    else:
        focus = "contextual_pair_observations"
        headline = "The pair view presents directional context without an aggregate compatibility verdict."

    overlay_summary = _pair_overlay_summary(events)
    highlights = [
        context_profile["summary"],
        "Natal spouse-palace and spouse-star evidence remains attached to each subject rather than merged into a pair result.",
        "Directional Day Master roles and unweighted element presence are contextual observations only.",
        (
            f"The product overlay detected {overlay_summary['total']} cross-chart contact(s); "
            "those contacts have no source-backed interpersonal outcome authority."
        ),
        "No aggregate score, grade, band, or relationship prediction is produced.",
    ]
    if active_timing:
        highlights.insert(
            1,
            f"Active individual timing context is present for: {', '.join(active_timing)}.",
        )
    return {
        "status": "qualitative_evidence_only",
        "focus": focus,
        "headline": headline,
        "highlights": highlights,
    }


def _spouse_star_exchange(primary_profile: Dict[str, Any], relationship_profile: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for label, receiver, compared in (
        ("primary_context", primary_profile, relationship_profile),
        ("relationship_context", relationship_profile, primary_profile),
    ):
        sex_role = _sex_based_spouse_factor(receiver)
        natal_condition = _factor_condition(receiver, sex_role.get("factor"))
        element = natal_condition.get("element")
        natal_condition = {
            **natal_condition,
            "element_context": _element_candidate_role(receiver, element),
            "source_scope": "individual_natal_relationship_context",
        }
        inventory = _presence_inventory(compared)
        presence_count = int(inventory["counts"].get(element) or 0) if element else 0
        rows.append({
            "direction": label,
            "calculation_sex": sex_role.get("calculation_sex"),
            "sex_based_role": sex_role.get("role"),
            "factor": sex_role.get("factor"),
            "natal_condition": natal_condition,
            "compared_chart_element_presence": {
                "element": element,
                "presence_count": presence_count,
                "presence_status": "present_only" if presence_count else "not_present",
                "inventory_basis": "unweighted_element_presence",
                "inventory_model_id": inventory["model_id"],
                "inventory_measure": inventory["measure"],
                "is_qi_strength": False,
                "outcome_authority": "none",
            },
            "status": "unknown" if sex_role.get("factor") is None else "available",
        })
    unknown = sum(1 for row in rows if row.get("status") == "unknown")
    return {
        "status": "unknown" if unknown == len(rows) else ("partial" if unknown else "available"),
        "method": "sex_based_spouse_star_context_v3",
        "directions": rows,
        "source_scope": "individual_natal_relationship_doctrine",
        "outcome_authority": "individual_context_only",
        "summary": (
            "Spouse-star doctrine selects Wealth for male calculation sex and Influence for female calculation sex, "
            "then reports each natal condition separately. Compared-chart element counts are presence-only context."
        ),
    }


def _sex_based_spouse_factor(profile: Dict[str, Any]) -> Dict[str, Any]:
    birth = profile.get("birth") if isinstance(profile, dict) else {}
    sex = str((birth or {}).get("calculation_sex") or profile.get("calculation_sex") or "").lower()
    if sex == "male":
        return {"calculation_sex": "male", "role": "wife_star", "factor": "Wealth"}
    if sex == "female":
        return {"calculation_sex": "female", "role": "husband_star", "factor": "Influence"}
    return {"calculation_sex": None, "role": "unknown", "factor": None}


def _factor_condition(profile: Dict[str, Any], factor: Optional[str]) -> Dict[str, Any]:
    if not factor:
        return {"status": "unknown", "factor": None, "summary": "Calculation sex is required before spouse-star factor can be selected."}
    ten_gods = profile.get("ten_gods") if isinstance(profile, dict) else {}
    profile_rows = (ten_gods.get("factor_profile") if isinstance(ten_gods, dict) else {}) or {}
    for row in profile_rows.get("factors") or []:
        if isinstance(row, dict) and row.get("factor") == factor:
            total = int(row.get("total_count") or 0)
            return {
                "status": "present" if total else "absent",
                "factor": factor,
                "element": row.get("element"),
                "visible_count": int(row.get("visible_count") or 0),
                "hidden_count": int(row.get("hidden_count") or 0),
                "total_count": total,
                "summary": row.get("summary") or row.get("domain_summary"),
            }
    return {"status": "absent", "factor": factor, "total_count": 0, "summary": f"{factor} spouse-star factor is not visible in the returned factor profile."}


def _subject_summary(profile: Dict[str, Any], fallback_label: str) -> Dict[str, Any]:
    day_master = profile.get("day_master") if isinstance(profile, dict) else {}
    birth = profile.get("birth") if isinstance(profile, dict) else {}
    return {
        "source_snap_id": profile.get("source_snap_id") if isinstance(profile, dict) else None,
        "snap_label": profile.get("snap_label") if isinstance(profile, dict) else None,
        "label": (profile.get("snap_label") if isinstance(profile, dict) else None) or fallback_label,
        "day_master": {
            "stem": day_master.get("stem") if isinstance(day_master, dict) else None,
            "element": day_master.get("element") if isinstance(day_master, dict) else None,
            "polarity": day_master.get("polarity") if isinstance(day_master, dict) else None,
        },
        "birth": {
            "date": birth.get("date") if isinstance(birth, dict) else None,
            "time": birth.get("time") if isinstance(birth, dict) else None,
            "location": birth.get("location") if isinstance(birth, dict) else None,
        },
    }


def _day_master_exchange(primary_profile: Dict[str, Any], relationship_profile: Dict[str, Any]) -> Dict[str, Any]:
    primary_day = primary_profile.get("day_master") if isinstance(primary_profile, dict) else {}
    relationship_day = relationship_profile.get("day_master") if isinstance(relationship_profile, dict) else {}
    primary_index = primary_day.get("stem_index") if isinstance(primary_day, dict) else None
    relationship_index = relationship_day.get("stem_index") if isinstance(relationship_day, dict) else None
    if primary_index is None or relationship_index is None:
        return {
            "status": "unavailable",
            "message": "Both Day Master stems are required before Five Factor exchange can be read.",
        }
    primary_to_relationship = ten_god(int(primary_index), int(relationship_index))
    relationship_to_primary = ten_god(int(relationship_index), int(primary_index))
    return {
        "status": "available",
        "primary_to_relationship": {
            "factor": primary_to_relationship.get("factor"),
            "god": primary_to_relationship.get("god"),
        },
        "relationship_to_primary": {
            "factor": relationship_to_primary.get("factor"),
            "god": relationship_to_primary.get("god"),
        },
        "summary": (
            f"Primary reads Relationship through {primary_to_relationship.get('factor')} "
            f"({primary_to_relationship.get('god')}); Relationship reads Primary through "
            f"{relationship_to_primary.get('factor')} ({relationship_to_primary.get('god')})."
        ),
    }
