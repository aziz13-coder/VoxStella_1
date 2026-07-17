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
        "summary": "Balanced reading for a pair when the relationship purpose is not specified.",
        "weights": {
            "cross_chart_contacts": 1.0,
            "spouse_palace_contacts": 1.0,
            "day_master_exchange": 1.0,
            "timing_alignment": 1.0,
            "useful_element_supply": 1.0,
        },
    },
    "romantic": {
        "label": "Romantic",
        "summary": "Emphasizes Day pillar / spouse-palace contacts and current timing pressure.",
        "weights": {
            "cross_chart_contacts": 1.0,
            "spouse_palace_contacts": 1.35,
            "day_master_exchange": 1.0,
            "timing_alignment": 1.15,
            "useful_element_supply": 1.0,
        },
    },
    "family": {
        "label": "Family",
        "summary": "Emphasizes Day Master exchange and de-emphasizes attraction-style spouse-palace scoring.",
        "weights": {
            "cross_chart_contacts": 0.85,
            "spouse_palace_contacts": 0.75,
            "day_master_exchange": 1.15,
            "timing_alignment": 0.9,
            "useful_element_supply": 1.0,
        },
    },
    "business": {
        "label": "Business",
        "summary": "Emphasizes useful-element supply, Day Master exchange, and current timing alignment.",
        "weights": {
            "cross_chart_contacts": 0.9,
            "spouse_palace_contacts": 0.65,
            "day_master_exchange": 1.15,
            "timing_alignment": 1.2,
            "useful_element_supply": 1.2,
        },
    },
}


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
    scoring = _pair_scoring(
        primary_profile,
        relationship_profile,
        events,
        timing_alignment,
        relationship_context=relationship_context,
    )
    day_master_exchange = _day_master_exchange(primary_profile, relationship_profile)
    judgement = _pair_judgement(
        primary_profile=primary_profile,
        relationship_profile=relationship_profile,
        events=events,
        timing_alignment=timing_alignment,
        day_master_exchange=day_master_exchange,
        scoring=scoring,
    )
    return {
        "status": "product_defined_uncalibrated_preview",
        "method": "bazi_pair_relationship_codes_v1",
        "relationship_context": relationship_context,
        "subjects": {
            "primary": _subject_summary(primary_profile, "Primary"),
            "relationship": _subject_summary(relationship_profile, "Relationship"),
        },
        "day_master_exchange": day_master_exchange,
        "timing_alignment": timing_alignment,
        "scoring": scoring,
        "judgement": judgement,
        "interpretation": _pair_interpretation(events, timing_alignment, scoring),
        "events": events,
        "summary": _pair_summary(events),
        "source_basis": [
            {
                "id": "local.destiny_code_revealed_relationships",
                "basis": "The local source documents combinations, clashes, harms, punishments, destructions, and complete sets within one chart. Applying those codes across two charts is a product-defined extrapolation.",
            },
            {
                "id": "local.destiny_code_five_factors",
                "basis": "The local source defines Five Factor / Ten God relationships. Treating one person's Day Master as another person's target stem is a product-defined pair heuristic.",
            },
            {
                "id": "local.destiny_code_palace_timing",
                "basis": "The local source supports natal palace and timing interpretation; its use as a two-person compatibility weight is not source-calibrated.",
            },
            {
                "id": "web.compatibility_method_cross_check",
                "basis": "Public compatibility material mentions similar dimensions, but it does not validate this product's baseline, weights, thresholds, or grade bands.",
            },
        ],
        "source_confidence": confidence_tags("computed_rule", "provisional_model", "needs_validation"),
        "notes": [
            "The score is a product-defined uncalibrated heuristic evidence index, not a source-derived compatibility measure or fate verdict.",
            "Source-backed intra-chart codes are shown as inputs; their cross-chart application and all numeric weighting are product choices.",
            f"Context profile: {RELATIONSHIP_CONTEXT_PROFILES[relationship_context]['label']} - {RELATIONSHIP_CONTEXT_PROFILES[relationship_context]['summary']}",
            "Day-pillar contacts are highlighted because the Day branch is the partner palace in the current palace model.",
            "Active Luck or annual contacts to either Day pillar are timing pressure markers, not automatic relationship outcomes.",
            "Useful-element supply is included only as provisional support until the strength model has broader fixtures.",
        ],
    }


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
    tone = _pair_tone(event.get("type"))
    return {
        **event,
        "intensity": intensity,
        "tone": tone,
        "reading_note": _pair_event_note(event.get("type"), intensity, tone),
    }


def _pair_tone(event_type: Any) -> str:
    raw = str(event_type or "")
    if raw in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination"}:
        return "supportive"
    if raw in {"branch_clash", "branch_harm", "branch_punishment", "self_punishment", "branch_destruction"}:
        return "challenging"
    return "mixed"


def _pair_event_note(event_type: Any, intensity: str, tone: str) -> str:
    if tone == "supportive":
        base = "Combination contact can describe shared channels, attraction, or ease when the affected elements are usable."
    elif tone == "challenging":
        base = "Friction contact marks pressure that must be judged through the affected palaces and element condition."
    else:
        base = "Complete-set contact is mixed until the chart context shows whether it stabilizes or overstimulates the pair."
    if intensity == "day_partner_palace":
        return f"{base} Both Day pillars are involved, so partner-palace relevance is high."
    if intensity == "partner_palace_contact":
        return f"{base} One Day pillar is involved, so partnership relevance is elevated."
    if intensity == "matched_pillar":
        return f"{base} The same life-stage palace is involved in both charts."
    return base


def _sort_pair_events(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    intensity_rank = {
        "day_partner_palace": 0,
        "partner_palace_contact": 1,
        "matched_pillar": 2,
        "cross_pillar": 3,
    }
    tone_rank = {"challenging": 0, "mixed": 1, "supportive": 2}
    return sorted(events, key=lambda event: (
        intensity_rank.get(str(event.get("intensity")), 9),
        tone_rank.get(str(event.get("tone")), 9),
        str(event.get("label") or ""),
    ))


def _pair_summary(events: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "total": len(events),
        "supportive": 0,
        "mixed": 0,
        "challenging": 0,
        "day_partner_palace": 0,
        "partner_palace_contact": 0,
        "matched_pillar": 0,
        "cross_pillar": 0,
    }
    for event in events:
        tone = str(event.get("tone") or "mixed")
        intensity = str(event.get("intensity") or "cross_pillar")
        event_type = str(event.get("type") or "unknown")
        counts[tone] = counts.get(tone, 0) + 1
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


def _pair_scoring(
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
    events: Sequence[Dict[str, Any]],
    timing_alignment: Dict[str, Any],
    *,
    relationship_context: str,
) -> Dict[str, Any]:
    relationship_context = _normalize_relationship_context(relationship_context)
    context_profile = RELATIONSHIP_CONTEXT_PROFILES[relationship_context]
    weights = context_profile["weights"]
    components = [
        _score_cross_chart_contacts(events),
        _score_spouse_palace_contacts(events),
        _score_day_master_exchange(primary_profile, relationship_profile),
        _score_timing_alignment(timing_alignment),
        _score_useful_element_supply(primary_profile, relationship_profile),
    ]
    weighted_components = [
        _apply_context_weight(component, weights.get(str(component.get("key") or ""), 1.0))
        for component in components
    ]
    raw_delta = sum(int(component.get("delta") or 0) for component in components)
    weighted_delta = round(sum(float(component.get("weighted_delta") or 0.0) for component in weighted_components))
    delta = _clamp_int(weighted_delta, -50, 50)
    score = _clamp_int(50 + delta, 0, 100)
    band = _score_band(score)
    confidence = _score_confidence(weighted_components)
    calibration = _compatibility_calibration_status(relationship_context, weighted_components)
    return {
        "status": "product_defined_uncalibrated_heuristic",
        "method": "bazi_pair_weighted_evidence_score_v1",
        "index_label": "Product-defined uncalibrated heuristic evidence index",
        "numeric_provenance": "product_defined_not_source_calibrated",
        "calibrated": False,
        "relationship_context": relationship_context,
        "relationship_context_label": context_profile["label"],
        "context_profile": {
            "key": relationship_context,
            "label": context_profile["label"],
            "summary": context_profile["summary"],
            "weights": dict(weights),
        },
        "score": score,
        "base_score": 50,
        "delta": delta,
        "raw_delta": raw_delta,
        "grade": band["grade"],
        "grade_label": band["label"],
        "band": band["band"],
        "confidence": confidence,
        "confidence_scope": "input_evidence_coverage_only",
        "components": weighted_components,
        "calibration": calibration,
        "source_evidence": _compatibility_source_evidence(calibration),
        "source_confidence": confidence_tags("computed_rule", "provisional_model", "needs_validation"),
        "interpretive_limits": [
            "The numeric baseline, component values, context weights, thresholds, and grade bands are product-defined and uncalibrated.",
            "The index weighs configured evidence; it is not a source-derived compatibility score and does not promise a relationship outcome.",
            "Context profiles shift component weights; raw component deltas are retained for audit.",
            "A high heuristic index can still require work when timing pressure is active.",
            "A low heuristic index can still be workable when both people consciously manage the pressured palaces.",
        ],
    }


def _compatibility_calibration_status(relationship_context: str, components: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    fixture_ids_by_context = {
        "general": ["compatibility.general_pair_score_seed"],
        "romantic": ["compatibility.romantic_pair_score_seed"],
        "family": ["compatibility.family_pair_score_seed"],
        "business": ["compatibility.business_pair_score_seed"],
    }
    fixture_ids = fixture_ids_by_context.get(relationship_context, [])
    evidence_count = sum(int(component.get("evidence_count") or 0) for component in components)
    return {
        "status": "uncalibrated_product_heuristic",
        "calibrated": False,
        "relationship_context": relationship_context,
        "fixture_ids": fixture_ids,
        "evidence_count": evidence_count,
        "source_ids": [],
        "numeric_provenance": "product_defined_not_source_calibrated",
        "notes": [
            "The listed fixtures are smoke examples, not calibration evidence.",
            "No local source validates the baseline, component values, context weights, thresholds, or score bands.",
        ],
    }


def _compatibility_source_evidence(calibration: Dict[str, Any]) -> List[Dict[str, Any]]:
    fixture_ids = calibration.get("fixture_ids") if isinstance(calibration.get("fixture_ids"), list) else []
    return [{
        "source_id": "product.compatibility_heuristic_v1",
        "rule_id": "compatibility.weighted_pair_score",
        "claim": "The baseline, component values, context weights, thresholds, and grade bands are product-defined and remain uncalibrated.",
        "strength": "uncalibrated_product_heuristic",
        "fixture_ids": fixture_ids,
    }]


def _apply_context_weight(component: Dict[str, Any], weight: float) -> Dict[str, Any]:
    raw_delta = int(component.get("delta") or 0)
    weighted_delta = round(float(raw_delta) * float(weight), 2)
    return {
        **component,
        "raw_delta": raw_delta,
        "weight": round(float(weight), 2),
        "weighted_delta": weighted_delta,
        "delta": int(round(weighted_delta)),
    }


def _score_cross_chart_contacts(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    raw = 0.0
    for event in events:
        event_type = str(event.get("type") or "")
        intensity = str(event.get("intensity") or "")
        multiplier = {
            "day_partner_palace": 1.45,
            "partner_palace_contact": 1.25,
            "matched_pillar": 1.0,
            "cross_pillar": 0.75,
        }.get(intensity, 0.75)
        base = {
            "stem_combination": 2.0,
            "branch_combination": 3.0,
            "three_harmony_combination": 4.0,
            "seasonal_combination": 4.0,
            "branch_cross": 0.0,
            "branch_clash": -3.5,
            "branch_harm": -3.0,
            "branch_punishment": -3.5,
            "self_punishment": -3.0,
            "branch_destruction": -3.0,
        }.get(event_type, 0.0)
        raw += base * multiplier
    delta = _clamp_int(round(raw), -18, 18)
    return {
        "key": "cross_chart_contacts",
        "label": "Cross-chart contacts",
        "delta": delta,
        "range": {"min": -18, "max": 18},
        "evidence_count": len(events),
        "summary": "Combinations add support; clashes, harms, punishments, and destructions subtract, with Day-pillar contacts weighted higher.",
    }


def _score_spouse_palace_contacts(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    spouse_events = [
        event for event in events
        if event.get("intensity") in {"day_partner_palace", "partner_palace_contact"}
    ]
    raw = 0.0
    for event in spouse_events:
        tone = _pair_tone(event.get("type"))
        intensity = str(event.get("intensity") or "")
        multiplier = 1.35 if intensity == "day_partner_palace" else 1.0
        if tone == "supportive":
            raw += 4.0 * multiplier
        elif tone == "challenging":
            raw -= 5.0 * multiplier
        else:
            raw -= 1.0 * multiplier
    delta = _clamp_int(round(raw), -22, 22)
    return {
        "key": "spouse_palace_contacts",
        "label": "Spouse palace contacts",
        "delta": delta,
        "range": {"min": -22, "max": 22},
        "evidence_count": len(spouse_events),
        "summary": "Day Branch / spouse-palace contacts are scored separately because local and web sources treat them as the relationship checkpoint.",
    }


def _score_day_master_exchange(primary_profile: Dict[str, Any], relationship_profile: Dict[str, Any]) -> Dict[str, Any]:
    exchange = _day_master_exchange(primary_profile, relationship_profile)
    if exchange.get("status") != "available":
        return {
            "key": "day_master_exchange",
            "label": "Day Master exchange",
            "delta": 0,
            "range": {"min": -10, "max": 10},
            "evidence_count": 0,
            "confidence": "low",
            "summary": "Day Master exchange is unavailable.",
        }
    primary_view = exchange.get("primary_to_relationship") or {}
    relationship_view = exchange.get("relationship_to_primary") or {}
    raw = _ten_god_exchange_delta(primary_view) + _ten_god_exchange_delta(relationship_view)
    delta = _clamp_int(raw, -10, 10)
    return {
        "key": "day_master_exchange",
        "label": "Day Master exchange",
        "delta": delta,
        "range": {"min": -10, "max": 10},
        "evidence_count": 2,
        "summary": exchange.get("summary") or "Both Day Masters can be compared through Five Factor / Ten God exchange.",
    }


def _ten_god_exchange_delta(view: Dict[str, Any]) -> int:
    factor = str(view.get("factor") or "")
    god = str(view.get("god") or "")
    factor_score = {
        "Resource": 4,
        "Output": 2,
        "Companion": 1,
        "Wealth": 1,
        "Influence": 0,
    }.get(factor, 0)
    god_score = {
        "Direct Resource": 1,
        "Eating God": 1,
        "Friend": 1,
        "Direct Wealth": 1,
        "Direct Officer": 1,
        "Seven Killings": -2,
        "Hurting Officer": -1,
        "Rob Wealth": -1,
    }.get(god, 0)
    return factor_score + god_score


def _score_timing_alignment(timing_alignment: Dict[str, Any]) -> Dict[str, Any]:
    status_weights = {
        "active_pressure": -10,
        "active_support": 6,
        "active_mixed": -2,
        "natal_pressure": -4,
        "natal_support": 3,
        "natal_mixed": 0,
        "quiet": 0,
    }
    raw = 0
    evidence_count = 0
    statuses = []
    for profile in timing_alignment.values():
        if not isinstance(profile, dict):
            continue
        status = str(profile.get("status") or "quiet")
        statuses.append(status)
        raw += status_weights.get(status, 0)
        evidence_count += int((profile.get("counts") or {}).get("day_events") or 0)
    delta = _clamp_int(raw, -18, 14)
    return {
        "key": "timing_alignment",
        "label": "Timing alignment",
        "delta": delta,
        "range": {"min": -18, "max": 14},
        "evidence_count": evidence_count,
        "summary": f"Timing states: {', '.join(statuses) if statuses else 'unavailable'}. Active pressure weighs more than natal background pressure.",
    }


def _score_useful_element_supply(primary_profile: Dict[str, Any], relationship_profile: Dict[str, Any]) -> Dict[str, Any]:
    primary_supply = _one_way_useful_supply(primary_profile, relationship_profile)
    relationship_supply = _one_way_useful_supply(relationship_profile, primary_profile)
    raw = primary_supply["delta"] + relationship_supply["delta"]
    delta = _clamp_int(raw, -8, 14)
    confidence = "medium"
    if primary_supply.get("confidence") == "low" or relationship_supply.get("confidence") == "low":
        confidence = "low"
    return {
        "key": "useful_element_supply",
        "label": "Useful element supply",
        "delta": delta,
        "range": {"min": -8, "max": 14},
        "evidence_count": primary_supply["evidence_count"] + relationship_supply["evidence_count"],
        "confidence": confidence,
        "summary": "Partner element totals are checked against each subject's provisional favorable and unfavorable elements.",
        "details": {
            "primary_receives": primary_supply,
            "relationship_receives": relationship_supply,
        },
    }


def _one_way_useful_supply(receiver_profile: Dict[str, Any], supplier_profile: Dict[str, Any]) -> Dict[str, Any]:
    useful = receiver_profile.get("useful_elements") if isinstance(receiver_profile, dict) else {}
    supplier_balance = supplier_profile.get("element_balance") if isinstance(supplier_profile, dict) else {}
    totals = supplier_balance.get("total") if isinstance(supplier_balance, dict) else {}
    if not isinstance(useful, dict) or not isinstance(totals, dict):
        return {"delta": 0, "evidence_count": 0, "confidence": "low", "matches": []}

    confidence = "low" if useful.get("status") == "withheld" else "medium"
    matches: List[Dict[str, Any]] = []
    raw = 0
    for row in useful.get("favorable") or []:
        if not isinstance(row, dict):
            continue
        element = row.get("element")
        if not element:
            continue
        count = int(totals.get(element) or 0)
        if count <= 0:
            continue
        integrity = row.get("integrity") if isinstance(row.get("integrity"), dict) else {}
        addition = 3 if integrity.get("availability") == "missing" else 2
        if integrity.get("pressure") == "pressured":
            addition -= 1
        raw += max(1, addition)
        matches.append({"element": element, "role": row.get("role"), "supplier_count": count, "direction": "favorable"})

    for row in useful.get("unfavorable") or []:
        if not isinstance(row, dict):
            continue
        element = row.get("element")
        if not element:
            continue
        count = int(totals.get(element) or 0)
        if count >= 3:
            raw -= 1
            matches.append({"element": element, "role": row.get("role"), "supplier_count": count, "direction": "unfavorable_load"})

    return {
        "delta": _clamp_int(raw, -4, 7),
        "evidence_count": len(matches),
        "confidence": confidence,
        "matches": matches[:6],
    }


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(round(float(value)))
    except Exception:
        number = 0
    return max(int(minimum), min(int(maximum), number))


def _score_band(score: int) -> Dict[str, str]:
    if score >= 85:
        return {"grade": "A", "band": "high_support", "label": "High support"}
    if score >= 70:
        return {"grade": "B", "band": "strong_with_conditions", "label": "Strong with conditions"}
    if score >= 55:
        return {"grade": "C", "band": "workable_mixed", "label": "Workable / mixed"}
    if score >= 40:
        return {"grade": "D", "band": "strained", "label": "Strained"}
    return {"grade": "E", "band": "high_friction", "label": "High friction"}


def _score_confidence(components: Sequence[Dict[str, Any]]) -> str:
    low_count = sum(1 for component in components if component.get("confidence") == "low")
    evidence_count = sum(int(component.get("evidence_count") or 0) for component in components)
    if low_count >= 2 or evidence_count < 3:
        return "low"
    if low_count == 1 or evidence_count < 8:
        return "medium"
    return "medium_high"


def _pair_interpretation(
    events: Sequence[Dict[str, Any]],
    timing_alignment: Dict[str, Any],
    scoring: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = _pair_summary(events)
    day_contacts = int(summary.get("day_partner_palace", 0) or 0) + int(summary.get("partner_palace_contact", 0) or 0)
    challenging = int(summary.get("challenging", 0) or 0)
    supportive = int(summary.get("supportive", 0) or 0)
    score = int((scoring or {}).get("score") or 0)
    active_pressure_subjects = [
        key for key, profile in timing_alignment.items()
        if isinstance(profile, dict) and profile.get("status") == "active_pressure"
    ]
    if score >= 70 and not active_pressure_subjects:
        focus = "strong_structural_support"
        headline = "The uncalibrated heuristic index shows comparatively strong configured support."
    elif score < 40:
        focus = "high_friction"
        headline = "The uncalibrated heuristic index shows concentrated configured friction."
    elif active_pressure_subjects:
        focus = "timing_pressure"
        headline = "Current timing is the first relationship checkpoint."
    elif day_contacts:
        focus = "partner_palace_contacts"
        headline = "Partner-palace contacts are the first relationship checkpoint."
    elif challenging > supportive:
        focus = "cross_chart_friction"
        headline = "Cross-chart friction outweighs easy combination contacts."
    elif supportive:
        focus = "combination_support"
        headline = "Combination contacts provide the clearest shared channel."
    else:
        focus = "quiet_pair_codes"
        headline = "No strong cross-chart relationship-contact emphasis is configured."
    highlights = []
    if day_contacts:
        highlights.append(f"{day_contacts} cross-chart contact(s) involve at least one Day pillar / partner palace.")
    if active_pressure_subjects:
        highlights.append("At least one subject has active timing pressure on the Day pillar / spouse palace.")
    if challenging:
        highlights.append(f"{challenging} challenging contact(s) need palace and element-condition review.")
    if supportive:
        highlights.append(f"{supportive} supportive combination contact(s) can describe shared channels when the element is usable.")
    if scoring:
        highlights.append(f"Heuristic index: {scoring.get('grade')} / {scoring.get('score')} ({scoring.get('grade_label')}); bands are product-defined and uncalibrated.")
    if not highlights:
        highlights.append("Use Day Master exchange and the individual natal profiles as the next interpretive layer.")
    return {
        "status": "product_defined_uncalibrated_heuristic",
        "focus": focus,
        "headline": headline,
        "highlights": highlights,
    }


def _pair_judgement(
    *,
    primary_profile: Dict[str, Any],
    relationship_profile: Dict[str, Any],
    events: Sequence[Dict[str, Any]],
    timing_alignment: Dict[str, Any],
    day_master_exchange: Dict[str, Any],
    scoring: Dict[str, Any],
) -> Dict[str, Any]:
    summary = _pair_summary(events)
    day_events = [
        event for event in events
        if str(event.get("intensity") or "") in {"day_partner_palace", "partner_palace_contact"}
    ]
    spouse_palace = _relationship_layer_status(day_events)
    useful_component = next(
        (component for component in scoring.get("components") or [] if component.get("key") == "useful_element_supply"),
        {},
    )
    spouse_star = _spouse_star_exchange(primary_profile, relationship_profile)
    timing_statuses = {
        subject: profile.get("status")
        for subject, profile in timing_alignment.items()
        if isinstance(profile, dict)
    }
    timing_activation = {
        "status": (
            "pressured" if "active_pressure" in timing_statuses.values()
            else "supportive" if "active_support" in timing_statuses.values()
            else "mixed" if any(str(value).startswith("active") for value in timing_statuses.values())
            else "quiet"
        ),
        "primary_branch_weight": "day_palace_first",
        "subjects": timing_statuses,
        "summary": "Current timing is judged first by activation of either Day branch / spouse palace.",
    }
    cross_contacts = {
        "status": _relationship_layer_status(events)["status"],
        "supportive": int(summary.get("supportive") or 0),
        "challenging": int(summary.get("challenging") or 0),
        "mixed": int(summary.get("mixed") or 0),
        "day_palace_contacts": len(day_events),
    }
    evidence_order = [
        {"key": "spouse_palace", "label": "Spouse palace / Day branch", "status": spouse_palace["status"]},
        {"key": "spouse_star", "label": "Spouse star by chart context", "status": spouse_star["status"]},
        {"key": "useful_element_exchange", "label": "Useful-element exchange", "status": useful_component.get("confidence") or "low"},
        {"key": "day_master_exchange", "label": "Day Master relationship", "status": day_master_exchange.get("status") or "unavailable"},
        {"key": "cross_chart_contacts", "label": "Cross-chart combinations and clashes", "status": cross_contacts["status"]},
        {"key": "timing_activation", "label": "Current timing activation", "status": timing_activation["status"]},
    ]
    return {
        "status": "product_defined_uncalibrated_heuristic",
        "method": "bazi_relationship_judgement_v2",
        "evidence_order": evidence_order,
        "spouse_palace": spouse_palace,
        "spouse_star": spouse_star,
        "useful_element_exchange": useful_component,
        "day_master_exchange": day_master_exchange,
        "cross_chart_contacts": cross_contacts,
        "timing_activation": timing_activation,
        "summary": "The product heuristic orders spouse palace, spouse star, useful-element exchange, Day Master exchange, contacts, and timing before its uncalibrated index is read.",
    }


def _relationship_layer_status(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    supportive = sum(1 for event in events if _pair_tone(event.get("type")) == "supportive")
    challenging = sum(1 for event in events if _pair_tone(event.get("type")) == "challenging")
    mixed = sum(1 for event in events if _pair_tone(event.get("type")) == "mixed")
    if supportive and challenging:
        status = "mixed"
    elif challenging:
        status = "pressured"
    elif supportive:
        status = "supportive"
    elif mixed:
        status = "mixed"
    else:
        status = "quiet"
    return {
        "status": status,
        "supportive": supportive,
        "challenging": challenging,
        "mixed": mixed,
        "event_count": len(events),
    }


def _spouse_star_exchange(primary_profile: Dict[str, Any], relationship_profile: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    useful_proxy = []
    for label, receiver, supplier in (
        ("primary_receives_relationship", primary_profile, relationship_profile),
        ("relationship_receives_primary", relationship_profile, primary_profile),
    ):
        sex_role = _sex_based_spouse_factor(receiver)
        receiver_factor = _factor_condition(receiver, sex_role.get("factor"))
        supplier_balance = supplier.get("element_balance") if isinstance(supplier, dict) else {}
        totals = supplier_balance.get("total") if isinstance(supplier_balance, dict) else {}
        supplier_count = int(totals.get(receiver_factor.get("element")) or 0) if isinstance(totals, dict) and receiver_factor.get("element") else 0
        rows.append({
            "direction": label,
            "calculation_sex": sex_role.get("calculation_sex"),
            "sex_based_role": sex_role.get("role"),
            "factor": sex_role.get("factor"),
            "natal_condition": receiver_factor,
            "cross_chart_supply": {
                "element": receiver_factor.get("element"),
                "supplier_count": supplier_count,
                "status": "supplied" if supplier_count else "not_supplied",
            },
            "status": (
                "unknown" if sex_role.get("factor") is None
                else "supportive" if supplier_count else
                "natal_only" if int(receiver_factor.get("total_count") or 0) else
                "absent"
            ),
        })
        receiver_useful = receiver.get("useful_elements") if isinstance(receiver, dict) else {}
        matches = []
        if isinstance(receiver_useful, dict) and isinstance(totals, dict):
            for row in receiver_useful.get("favorable") or []:
                if isinstance(row, dict) and row.get("element") and int(totals.get(row.get("element")) or 0) > 0:
                    matches.append({"element": row.get("element"), "role": row.get("role"), "supplier_count": totals.get(row.get("element"))})
        useful_proxy.append({"direction": label, "matches": matches[:4], "match_count": len(matches)})
    total = sum(1 for row in rows if row.get("status") == "supportive")
    unknown = sum(1 for row in rows if row.get("status") == "unknown")
    return {
        "status": "unknown" if unknown == len(rows) else ("supportive" if total else "quiet"),
        "method": "sex_based_spouse_star_exchange_v2",
        "directions": rows,
        "useful_element_proxy": useful_proxy,
        "summary": "Spouse-star context starts with Wealth for male calculation sex and Officer/Killing for female calculation sex, then checks natal condition and cross-chart supply.",
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
