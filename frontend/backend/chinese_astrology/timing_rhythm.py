from typing import Any, Dict, List, Optional, Sequence

from .curation import confidence_tags
from .relationships import (
    _dedupe_events,
    _detect_dynamic,
    _natal_points,
    _pair_tone,
    _sort_events,
    _timing_point,
)
from .tables import BRANCH_INDEX, CONTROLS, PRODUCES, STEM_INDEX


GROWTH_STAGE_SEQUENCE = (
    {"key": "chang_sheng", "label": "Chang Sheng", "meaning": "birth / emergence", "group": "rising"},
    {"key": "mu_yu", "label": "Mu Yu", "meaning": "cleansing / exposure", "group": "transitional"},
    {"key": "guan_dai", "label": "Guan Dai", "meaning": "coming of age", "group": "rising"},
    {"key": "lin_guan", "label": "Lin Guan", "meaning": "office / authority", "group": "rising"},
    {"key": "di_wang", "label": "Di Wang", "meaning": "imperial peak", "group": "peak"},
    {"key": "shuai", "label": "Shuai", "meaning": "decline", "group": "transitional"},
    {"key": "bing", "label": "Bing", "meaning": "illness", "group": "contracting"},
    {"key": "si", "label": "Si", "meaning": "death", "group": "contracting"},
    {"key": "mu", "label": "Mu", "meaning": "tomb / storage", "group": "storage"},
    {"key": "jue", "label": "Jue", "meaning": "severance", "group": "contracting"},
    {"key": "tai", "label": "Tai", "meaning": "womb / gestation", "group": "transitional"},
    {"key": "yang", "label": "Yang", "meaning": "nourishment", "group": "transitional"},
)

GROWTH_STAGE_BRANCHES_BY_STEM = {
    "Jia": ("Hai", "Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu"),
    "Yi": ("Wu", "Si", "Chen", "Mao", "Yin", "Chou", "Zi", "Hai", "Xu", "You", "Shen", "Wei"),
    "Bing": ("Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai", "Zi", "Chou"),
    "Ding": ("You", "Shen", "Wei", "Wu", "Si", "Chen", "Mao", "Yin", "Chou", "Zi", "Hai", "Xu"),
    "Wu": ("Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai", "Zi", "Chou"),
    "Ji": ("You", "Shen", "Wei", "Wu", "Si", "Chen", "Mao", "Yin", "Chou", "Zi", "Hai", "Xu"),
    "Geng": ("Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai", "Zi", "Chou", "Yin", "Mao", "Chen"),
    "Xin": ("Zi", "Hai", "Xu", "You", "Shen", "Wei", "Wu", "Si", "Chen", "Mao", "Yin", "Chou"),
    "Ren": ("Shen", "You", "Xu", "Hai", "Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei"),
    "Gui": ("Mao", "Yin", "Chou", "Zi", "Hai", "Xu", "You", "Shen", "Wei", "Wu", "Si", "Chen"),
}

SOURCE_BASIS = [
    {
        "id": "anchor.timing.luck_pillars",
        "basis": "Da Yun / 10-year luck rhythm starts from the month pillar, direction, and solar-term start age.",
    },
    {
        "id": "anchor.ten_gods.five_factors",
        "basis": "Each timing stem is read as a Ten God / Five Factor relative to the natal Day Master.",
    },
    {
        "id": "anchor.relationships.codes",
        "basis": "Timing layers are checked against natal pillars through stem/branch combinations, clashes, harms, punishments, destructions, and complete sets.",
    },
    {
        "id": "anchor.useful_elements.climate_damage",
        "basis": "Useful-element support or pressure is shown as timing evidence, not as an automatic final Yong Shen ruling.",
    },
    {
        "id": "anchor.timing.growth_stages",
        "basis": "The 12 growth-stage table is exposed as a qi-state preview for the Day Master against each timing branch.",
    },
]

RHYTHM_LIMITS = [
    "BaZi Timing Rhythm is not Six-Star Divination and does not use Hosoki branded fortune-cycle labels.",
    "Timing layers are source-gated BaZi evidence; they do not independently finalize a Yong Shen.",
]


def build_timing_rhythm(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    timing: Optional[Dict[str, Any]],
    useful_elements: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(timing, dict):
        return _not_enabled("Timing data is unavailable.")

    layer_specs = _timing_layer_specs(timing)
    if not layer_specs:
        return _not_enabled("Life Timing requires at least an annual or flowing timing layer.")

    natal_points = _natal_points(pillars)
    day_master_stem = ((pillars.get("day") or {}) if isinstance(pillars, dict) else {}).get("stem")
    favorable = _candidate_elements((useful_elements or {}).get("favorable"))
    unfavorable = _candidate_elements((useful_elements or {}).get("unfavorable"))

    rows = []
    for spec in layer_specs:
        pillar = spec.get("pillar")
        if not isinstance(pillar, dict):
            continue
        events = _events_for_layer(natal_points, spec, pillar)
        element_effects = _element_effects(pillar, favorable, unfavorable)
        growth_stage = _growth_stage(day_master_stem, pillar.get("branch"))
        interpretive_effects = _interpretive_effects(str(spec["layer"]), element_effects, events)
        ying_qi = _ying_qi_layer(str(spec["layer"]), pillar, interpretive_effects, events)
        score = _layer_score(element_effects, events)
        rows.append({
            "layer": spec["layer"],
            "label": spec["label"],
            "scope": spec["scope"],
            "pillar": _compact_pillar(pillar),
            "period": spec.get("period") or {},
            "calculation_basis": _calculation_basis(spec, pillar),
            "evidence_role": "contextual_timing_only",
            "source_strength": _source_strength(spec["layer"]),
            "release_gate": _release_gate(spec["layer"]),
            "ten_god": {
                "stem": pillar.get("ten_god"),
                "factor": pillar.get("five_factor"),
            },
            "layer_weighting": _layer_weighting(str(spec["layer"])),
            "useful_element_effects": element_effects,
            "interpretive_effects": interpretive_effects,
            "ying_qi": ying_qi,
            "relationship_events": [_compact_event(event) for event in events[:6]],
            "relationship_summary": _relationship_summary(events),
            "growth_stage": growth_stage,
            "score": score,
            "tone": _tone(score, element_effects, events),
        })

    if not rows:
        return _not_enabled("Life Timing could not resolve usable timing layers.")

    supporting = [row for row in rows if row["tone"] == "supportive"]
    pressuring = [row for row in rows if row["tone"] == "pressuring"]
    day_contacts = [
        event
        for row in rows
        for event in row.get("relationship_events") or []
        if "Day" in (event.get("affected_palaces") or [])
    ]
    summary = _summary_text(rows, supporting, pressuring, day_contacts)

    return {
        "status": "source_based_preview",
        "method": "bazi_timing_rhythm_v1",
        "scope": "bazi_timing_not_branded_fortune_cycle",
        "reference_datetime_utc": timing.get("reference_datetime_utc") or (timing.get("debug") or {}).get("reference_datetime_utc"),
        "layers": rows,
        "summary": summary,
        "event_activation": _event_activation(rows),
        "signals": {
            "supporting_layers": [_layer_ref(row) for row in supporting],
            "pressure_layers": [_layer_ref(row) for row in pressuring],
            "day_pillar_contacts": day_contacts[:6],
        },
        "calibration": _calibration_payload(rows),
        "source_basis": SOURCE_BASIS,
        "source_evidence": [
            {
                "source_id": "anchor.timing.luck_pillars",
                "rule_id": "timing_rhythm.da_yun_liu_nian_flowing_layers",
                "claim": "The rhythm is built from Da Yun, annual, month, day, and hour pillars using existing BaZi timing calculations.",
                "fixture_ids": ["timing_rhythm.current_layers_reference"],
            },
            {
                "source_id": "anchor.timing.growth_stages",
                "rule_id": "timing_rhythm.growth_stage_preview",
                "claim": "Growth stages are displayed as qi-state evidence and do not change final useful-god release gates.",
                "fixture_ids": ["timing_rhythm.growth_stage_day_master_branch"],
            },
            {
                "source_id": "anchor.relationships.codes",
                "rule_id": "timing_rhythm.ying_qi_activation",
                "claim": "Ying Qi is shown when timing layers activate natal useful elements, spouse palace, or relationship contacts by combination, clash, punishment, harm, or destruction.",
                "fixture_ids": ["timing_rhythm.ying_qi_activation_reference"],
            },
        ],
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model", "school_variant"),
        "limits": RHYTHM_LIMITS,
    }


def _not_enabled(summary: str) -> Dict[str, Any]:
    return {
        "status": "not_enabled",
        "method": "bazi_timing_rhythm_v1",
        "layers": [],
        "summary": summary,
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
        "limits": RHYTHM_LIMITS,
    }


def _layer_weighting(layer: str) -> Dict[str, Any]:
    if layer == "da_yun":
        return {
            "stem_weight": 0.4,
            "branch_weight": 0.6,
            "rule": "Da Yun emphasizes the branch/rooted environmental force before the decade stem.",
        }
    if layer == "liu_nian":
        return {
            "stem_weight": 0.6,
            "branch_weight": 0.4,
            "rule": "Liu Nian emphasizes the year stem as the arriving visible qi before branch context.",
        }
    if layer == "flowing_month":
        return {
            "stem_weight": 0.5,
            "branch_weight": 0.5,
            "rule": "Flowing month is kept balanced until worked examples calibrate stem/branch priority.",
        }
    return {
        "stem_weight": 0.45,
        "branch_weight": 0.55,
        "rule": "Shorter flowing layers retain branch contact context while staying preview-only.",
    }


def _layer_label(layer: str) -> str:
    return {
        "da_yun": "Current 10-Year Luck",
        "liu_nian": "Current BaZi Year",
        "flowing_month": "Flowing Month",
        "flowing_day": "Flowing Day",
        "flowing_hour": "Flowing Hour",
    }.get(layer, str(layer or "Timing Layer").replace("_", " ").title())


def _token_label(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _effect_verb(kind: str) -> str:
    return {
        "rescue": "rescues",
        "activate": "activates",
        "damage": "pressures",
        "expose": "brings forward",
    }.get(kind, _token_label(kind).lower() or "highlights")


def _event_effect_summary(label: str, kind: str, layer_label: str) -> str:
    if kind == "arrival":
        return f"{label} marks an arrival signal during {layer_label}."
    if kind == "movement":
        return f"{label} marks movement during {layer_label}."
    if kind == "pressure":
        return f"{label} adds pressure during {layer_label}."
    return f"{label} comes into focus during {layer_label}."


def _interpretive_effects(
    layer: str,
    element_effects: Sequence[Dict[str, Any]],
    events: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    layer_label = _layer_label(layer)
    for effect in element_effects:
        target_role = str(effect.get("target_role") or "")
        effect_name = str(effect.get("effect") or "")
        if target_role == "favorable" and effect_name in {"supplies", "supports"}:
            kind = "rescue" if layer in {"da_yun", "liu_nian"} else "activate"
        elif target_role == "favorable" and effect_name == "pressures":
            kind = "damage"
        elif target_role == "unfavorable" and effect_name == "pressures":
            kind = "rescue"
        elif target_role == "unfavorable" and effect_name in {"supplies", "supports"}:
            kind = "damage"
        else:
            kind = "expose"
        rows.append({
            "kind": kind,
            "source": "useful_element",
            "target_element": effect.get("target_element"),
            "source_element": effect.get("source_element"),
            "placement": effect.get("placement"),
            "summary": f"{layer_label} {_effect_verb(kind)} {effect.get('target_element') or 'the element'} through {_token_label(effect.get('placement'))}.",
        })
    for event in events[:6]:
        event_type = str(event.get("type") or "")
        if event_type in {"stem_combination", "branch_combination", "three_harmony_combination", "seasonal_combination"}:
            kind = "arrival"
        elif event_type == "branch_clash":
            kind = "movement"
        elif event_type in {"branch_harm", "branch_punishment", "self_punishment", "branch_destruction"}:
            kind = "pressure"
        else:
            kind = "expose"
        label = str(event.get("label") or _token_label(event_type) or "Timing contact")
        rows.append({
            "kind": kind,
            "source": "relationship_contact",
            "event_type": event_type,
            "label": label,
            "affected_palaces": event.get("affected_palaces") or [],
            "summary": _event_effect_summary(label, kind, layer_label),
        })
    return rows


def _layer_activation_role(layer: str) -> Dict[str, str]:
    if layer == "da_yun":
        return {
            "role": "field",
            "label": "Decade Field",
            "rule": "Da Yun sets the decade field; its branch/root quality weighs more heavily than the visible stem.",
        }
    if layer == "liu_nian":
        return {
            "role": "visible_trigger",
            "label": "Annual Trigger",
            "rule": "Liu Nian is the visible annual trigger and is read against Da Yun before natal contacts are finalized.",
        }
    if layer == "flowing_month":
        return {"role": "event_window", "label": "Timing Window", "rule": "Flowing month narrows the annual trigger into a month-sized window."}
    if layer == "flowing_day":
        return {"role": "day_trigger", "label": "Day Trigger", "rule": "Flowing day marks short-window contact and should echo a natal/year/month signal."}
    return {"role": "hour_trigger", "label": "Hour Trigger", "rule": "Flowing hour is the narrowest trigger and remains confirmation-level evidence."}


def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def _ying_qi_summary(layer_label: str, contact_count: int, rescue_count: int, pressure_count: int) -> str:
    return (
        f"{layer_label} activates {_plural(contact_count, 'Day or spouse-palace contact')}, "
        f"brings {_plural(rescue_count, 'rescue or arrival signal')}, "
        f"and adds {_plural(pressure_count, 'pressure or movement signal')}."
    )


def _event_touches_main_position(event: Dict[str, Any]) -> bool:
    affected = {str(item) for item in event.get("affected_palaces") or []}
    if "Day" in affected:
        return True
    return any(
        isinstance(point, dict) and point.get("pillar") == "day"
        for point in event.get("points") or []
    )


def _ying_qi_layer(
    layer: str,
    pillar: Dict[str, Any],
    interpretive_effects: Sequence[Dict[str, Any]],
    events: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    role = _layer_activation_role(layer)
    kinds = [str(effect.get("kind") or "expose") for effect in interpretive_effects]
    event_types = [str(event.get("type") or "") for event in events if isinstance(event, dict)]
    main_events = [event for event in events if isinstance(event, dict) and _event_touches_main_position(event)]
    pressure_count = sum(1 for kind in kinds if kind in {"damage", "pressure", "movement"})
    rescue_count = sum(1 for kind in kinds if kind in {"rescue", "arrival", "activate"})
    base = {"da_yun": 2, "liu_nian": 3, "flowing_month": 2, "flowing_day": 2, "flowing_hour": 1}.get(layer, 1)
    activation_score = base + len(main_events) + pressure_count + rescue_count
    if not kinds and not event_types:
        activation_state = "quiet"
    elif main_events and layer in {"liu_nian", "flowing_month", "flowing_day", "flowing_hour"}:
        activation_state = "event_trigger"
    elif layer == "da_yun":
        activation_state = "field_active" if (kinds or event_types) else "field_quiet"
    else:
        activation_state = "activated"
    fu_yin = any(
        event_type == "same_pillar"
        or "Fu Yin" in str(event.get("label") or "")
        for event_type, event in zip(event_types, events)
    )
    fan_yin = any(
        str(event.get("type") or "") == "branch_clash" and _event_touches_main_position(event)
        for event in events
        if isinstance(event, dict)
    )
    return {
        "status": activation_state,
        "status_label": activation_state.replace("_", " ").title(),
        "method": "bazi_ying_qi_layer_v1",
        "activation_role": role["role"],
        "activation_role_label": role["label"],
        "rule": role["rule"],
        "pillar": {"stem": pillar.get("stem"), "branch": pillar.get("branch")},
        "activation_score": activation_score,
        "main_position_linked": bool(main_events),
        "spouse_palace_linked": bool(main_events),
        "counts": {
            "main_position_contacts": len(main_events),
            "rescue_arrival_signals": rescue_count,
            "pressure_movement_signals": pressure_count,
        },
        "effect_kinds": sorted(set(kinds)),
        "contact_types": sorted(set(event_types)),
        "fu_yin": fu_yin,
        "fan_yin": fan_yin,
        "summary": _ying_qi_summary(role["label"], len(main_events), rescue_count, pressure_count),
        "source_page_refs": [
            "lu_zhiji_bazi_advanced:pp108-110",
            "lu_zhiji_fate_search:p361",
            "sanming_tonghui_part3:p243",
        ],
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
    }


def _event_activation(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    triggers: List[Dict[str, Any]] = []
    for row in rows:
        ying_qi = row.get("ying_qi") if isinstance(row.get("ying_qi"), dict) else {}
        if not ying_qi or str(ying_qi.get("status")) in {"quiet", "field_quiet"}:
            continue
        triggers.append({
            "layer": row.get("layer"),
            "label": row.get("label"),
            "status": ying_qi.get("status"),
            "status_label": ying_qi.get("status_label"),
            "activation_role": ying_qi.get("activation_role"),
            "activation_role_label": ying_qi.get("activation_role_label"),
            "activation_score": ying_qi.get("activation_score"),
            "main_position_linked": ying_qi.get("main_position_linked"),
            "counts": ying_qi.get("counts") or {},
            "effect_kinds": ying_qi.get("effect_kinds") or [],
            "contact_types": ying_qi.get("contact_types") or [],
            "summary": ying_qi.get("summary"),
        })
    triggers.sort(key=lambda row: (int(row.get("activation_score") or 0), row.get("layer") or ""), reverse=True)
    spouse_sync = [
        trigger for trigger in triggers
        if trigger.get("main_position_linked") and trigger.get("layer") in {"da_yun", "liu_nian", "flowing_month", "flowing_day", "flowing_hour"}
    ]
    return {
        "status": "active" if triggers else "quiet",
        "method": "bazi_ying_qi_activation_v1",
        "primary_triggers": triggers[:5],
        "spouse_timing": {
            "status": "synchronized" if len(spouse_sync) >= 2 else ("single_trigger" if spouse_sync else "quiet"),
            "trigger_count": len(spouse_sync),
            "layers": [trigger.get("layer") for trigger in spouse_sync[:5]],
            "summary": (
                "Spouse palace has multi-layer timing activation."
                if len(spouse_sync) >= 2 else
                "Spouse palace has a single timing trigger." if spouse_sync else
                "No spouse-palace timing trigger is active."
            ),
        },
        "summary": (
            f"{len(triggers)} timing layer(s) are activating natal evidence."
            if triggers else
            "No timing layer is currently strong enough to act as Ying Qi activation."
        ),
        "source_page_refs": [
            "lu_zhiji_bazi_advanced:pp108-110",
            "lu_zhiji_fate_search:p361",
            "sanming_tonghui_part3:p243",
        ],
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
    }


def _timing_layer_specs(timing: Dict[str, Any]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    active = timing.get("active_luck_pillar")
    if isinstance(active, dict):
        specs.append({
            "layer": "da_yun",
            "scope": "luck",
            "label": "Current 10-Year Luck",
            "pillar": active,
            "period": {
                "age_label": active.get("age_label"),
                "starts_on": active.get("starts_on"),
                "ends_on": active.get("ends_on"),
                "calendar_start_year": active.get("calendar_start_year"),
                "calendar_end_year": active.get("calendar_end_year"),
            },
        })
    annual = timing.get("annual_pillar")
    if isinstance(annual, dict):
        specs.append({
            "layer": "liu_nian",
            "scope": "annual",
            "label": "Current BaZi Year",
            "pillar": annual,
            "period": {
                "bazi_year": annual.get("bazi_year"),
                "calendar_year": annual.get("calendar_year"),
                "year_boundary": annual.get("year_boundary"),
            },
        })
    for key, layer, scope, label in (
        ("flowing_month_pillar", "flowing_month", "flowing_month", "Flowing Month"),
        ("flowing_day_pillar", "flowing_day", "flowing_day", "Flowing Day"),
        ("flowing_hour_pillar", "flowing_hour", "flowing_hour", "Flowing Hour"),
    ):
        pillar = timing.get(key)
        if isinstance(pillar, dict):
            specs.append({
                "layer": layer,
                "scope": scope,
                "label": label,
                "pillar": pillar,
                "period": pillar.get("period") if isinstance(pillar.get("period"), dict) else {},
            })
    return specs


def _candidate_elements(rows: Any) -> List[str]:
    elements: List[str] = []
    source_rows = rows if isinstance(rows, list) else []
    for row in source_rows:
        if isinstance(row, dict) and row.get("element"):
            elements.append(str(row["element"]))
        elif isinstance(row, str):
            elements.append(row)
    return list(dict.fromkeys(elements))


def _element_effects(pillar: Dict[str, Any], favorable: Sequence[str], unfavorable: Sequence[str]) -> List[Dict[str, Any]]:
    effects: List[Dict[str, Any]] = []
    for placement, symbol, element in (
        ("stem", pillar.get("stem"), pillar.get("stem_element")),
        ("branch", pillar.get("branch"), pillar.get("branch_element")),
    ):
        element = str(element or "")
        if not element:
            continue
        effect = _effect_against_candidates(element, favorable, "favorable")
        if effect:
            effects.append({"placement": placement, "symbol": symbol, "source_element": element, **effect})
        effect = _effect_against_candidates(element, unfavorable, "unfavorable")
        if effect:
            effects.append({"placement": placement, "symbol": symbol, "source_element": element, **effect})
    return effects


def _effect_against_candidates(source_element: str, targets: Sequence[str], role: str) -> Optional[Dict[str, Any]]:
    for target in targets:
        if source_element == target:
            effect = "supplies"
        elif PRODUCES.get(source_element) == target:
            effect = "supports"
        elif CONTROLS.get(source_element) == target:
            effect = "pressures"
        elif CONTROLS.get(target) == source_element:
            effect = "drains_into"
        else:
            continue
        return {
            "target_role": role,
            "target_element": target,
            "effect": effect,
            "status": f"{effect}_{role}",
        }
    return None


def _events_for_layer(
    natal_points: Sequence[Dict[str, Any]],
    spec: Dict[str, Any],
    pillar: Dict[str, Any],
) -> List[Dict[str, Any]]:
    point = _timing_point(pillar, str(spec["scope"]))
    events = _detect_dynamic(natal_points, point, scope=str(spec["scope"]))
    return _sort_events(_dedupe_events(events))


def _layer_score(element_effects: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> int:
    score = 0
    for effect in element_effects:
        role = effect.get("target_role")
        name = effect.get("effect")
        if role == "favorable":
            score += {"supplies": 3, "supports": 2, "drains_into": 1, "pressures": -3}.get(str(name), 0)
        elif role == "unfavorable":
            score += {"supplies": -2, "supports": -1, "pressures": 1, "drains_into": 0}.get(str(name), 0)
    for event in events:
        tone = _pair_tone(event.get("type"))
        touches_day = "Day" in (event.get("affected_palaces") or [])
        weight = 2 if touches_day else 1
        if tone == "supportive":
            score += weight
        elif tone == "challenging":
            score -= weight
    return score


def _tone(score: int, element_effects: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> str:
    if score >= 3:
        return "supportive"
    if score <= -3:
        return "pressuring"
    if element_effects or events:
        return "mixed"
    return "quiet"


def _growth_stage(day_master_stem: Any, branch: Any) -> Dict[str, Any]:
    stem_key = str(day_master_stem or "")
    branch_key = str(branch or "")
    if stem_key not in STEM_INDEX or branch_key not in BRANCH_INDEX:
        return {"status": "unavailable", "stage": None}
    branches = GROWTH_STAGE_BRANCHES_BY_STEM.get(stem_key)
    if not branches or branch_key not in branches:
        return {"status": "unavailable", "stage": None}
    stage = GROWTH_STAGE_SEQUENCE[branches.index(branch_key)]
    return {
        "status": "source_backed_preview",
        "day_master_stem": stem_key,
        "branch": branch_key,
        "stage": stage["key"],
        "label": stage["label"],
        "meaning": stage["meaning"],
        "group": stage["group"],
        "page_ref": {
            "source_id": "local.four_pillars_growth_stages",
            "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.pages.jsonl",
            "pages": [63],
        },
    }


def _compact_pillar(pillar: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stem": pillar.get("stem"),
        "branch": pillar.get("branch"),
        "animal": pillar.get("animal"),
        "stem_element": pillar.get("stem_element"),
        "branch_element": pillar.get("branch_element"),
        "stem_polarity": pillar.get("stem_polarity"),
        "branch_polarity": pillar.get("branch_polarity"),
        "ten_god": pillar.get("ten_god"),
        "five_factor": pillar.get("five_factor"),
    }


def _compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
    scope = event.get("scope")
    return {
        "type": event.get("type"),
        "label": event.get("label"),
        "scope": scope,
        "scope_label": event.get("scope_label"),
        "tone": _pair_tone(event.get("type")),
        "intensity": event.get("intensity"),
        "element": event.get("element"),
        "affected_palaces": event.get("affected_palaces") or [],
        "affected_domains": event.get("affected_domains") or [],
        "source_anchor": {
            "id": "anchor.relationships.codes",
            "contact_layer": scope,
            "basis": "natal-vs-timing stem/branch relationship code",
        },
    }


def _calculation_basis(spec: Dict[str, Any], pillar: Dict[str, Any]) -> Dict[str, Any]:
    layer = str(spec.get("layer") or "")
    period = spec.get("period") if isinstance(spec.get("period"), dict) else {}
    basis = {
        "method": "computed_sexagenary",
        "boundary_used": None,
        "source_page_refs": _source_page_refs(layer),
    }
    if layer == "da_yun":
        basis["method"] = "month_pillar_direction_sequence"
        basis["boundary_used"] = {
            "starts_on": period.get("starts_on"),
            "ends_on": period.get("ends_on"),
            "age_label": period.get("age_label"),
        }
    elif layer == "liu_nian":
        basis["boundary_used"] = {
            "bazi_year": period.get("bazi_year"),
            "calendar_year": period.get("calendar_year"),
            "year_boundary": period.get("year_boundary"),
        }
    elif layer == "flowing_month":
        solar_term = period.get("solar_term") if isinstance(period.get("solar_term"), dict) else {}
        basis["boundary_used"] = {
            "solar_term": solar_term.get("key") or solar_term.get("name"),
            "calendar_year": period.get("calendar_year"),
            "calendar_month": period.get("calendar_month"),
        }
    elif layer == "flowing_day":
        basis["boundary_used"] = {"local_date": period.get("local_date")}
    elif layer == "flowing_hour":
        basis["boundary_used"] = {
            "hour_branch": period.get("hour_branch") or pillar.get("branch"),
            "local_datetime": period.get("local_datetime"),
        }
    return basis


def _source_page_refs(layer: str) -> List[Dict[str, Any]]:
    if layer == "da_yun":
        return [
            {
                "source_id": "local.destiny_code_luck_pillars",
                "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.pages.jsonl",
                "pages": [92, 94, 101, 103],
            }
        ]
    if layer == "liu_nian":
        return [
            {
                "source_id": "local.destiny_code_revealed_luck_cycles",
                "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.pages.jsonl",
                "pages": [331],
            }
        ]
    return [
        {
            "source_id": "local.four_pillars_growth_stages",
            "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.pages.jsonl",
            "pages": [62, 63, 66, 67],
        }
    ]


def _source_strength(layer: str) -> str:
    if layer in {"da_yun", "liu_nian"}:
        return "local_worked_example"
    return "computed_no_worked_example"


def _release_gate(layer: str) -> str:
    if layer in {"flowing_month", "flowing_day", "flowing_hour"}:
        return "preview_only_until_worked_examples_curated"
    return "timing_assisted_finalization_blocked"


def _relationship_summary(events: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    summary = {"total": len(events), "supportive": 0, "challenging": 0, "mixed": 0}
    for event in events:
        tone = _pair_tone(event.get("type"))
        summary[tone] = summary.get(tone, 0) + 1
    return summary


def _layer_ref(row: Dict[str, Any]) -> Dict[str, Any]:
    pillar = row.get("pillar") if isinstance(row.get("pillar"), dict) else {}
    return {
        "layer": row.get("layer"),
        "label": row.get("label"),
        "pillar": f"{pillar.get('stem') or '-'} {pillar.get('branch') or '-'}",
        "tone": row.get("tone"),
        "score": row.get("score"),
    }


def _calibration_payload(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    flow_layers = [row for row in rows if str(row.get("layer") or "").startswith("flowing_")]
    contact_layers = [row for row in rows if int((row.get("relationship_summary") or {}).get("total") or 0) > 0]
    fixture_ids = [
        "timing_rhythm.current_layers_reference",
        "timing_rhythm.growth_stage_day_master_branch",
        "timing_rhythm.flowing_month_contact_reference",
        "timing_rhythm.flowing_day_hour_contact_reference",
    ]
    return {
        "status": "calibration_seeded_preview",
        "fixture_ids": fixture_ids,
        "layer_count": len(rows),
        "flow_layer_count": len(flow_layers),
        "contact_layer_count": len(contact_layers),
        "release_gate": "timing_assisted_finalization_blocked",
        "notes": [
            "Flowing month/day/hour contacts are visible timing evidence, not final outcome scoring.",
            "Timing-assisted final Yong Shen remains blocked until stronger sourced positive and negative examples are curated.",
        ],
    }


def _summary_text(
    rows: Sequence[Dict[str, Any]],
    supporting: Sequence[Dict[str, Any]],
    pressuring: Sequence[Dict[str, Any]],
    day_contacts: Sequence[Dict[str, Any]],
) -> str:
    if pressuring and supporting:
        lead = "Current timing is mixed: supportive and pressuring layers are both active."
    elif pressuring:
        lead = "Current timing is pressuring: the active layers add more friction than support."
    elif supporting:
        lead = "Current timing is supportive: the active layers add usable support signals."
    else:
        lead = "Current timing is quiet: the active layers do not strongly shift the useful-element or relationship-contact picture."
    detail = f"{len(rows)} timing layer(s) are resolved across decade/year/month/day/hour where available."
    if day_contacts:
        detail += f" {len(day_contacts)} contact(s) touch the Day pillar, so partner/self palace timing should be reviewed."
    return f"{lead} {detail}"
