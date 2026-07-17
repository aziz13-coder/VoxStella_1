from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .curation import confidence_tags
from .tables import BRANCHES, BRANCH_INDEX, CONTROLS, ELEMENTS, PRODUCES, STEM_INDEX, STEMS, ten_god
from .validation import yong_shen_family_gate


LOCAL_SOURCE_BASIS = (
    {
        "id": "local.four_pillars_strength",
        "label": "Ba Zi - The Four Pillars of Destiny",
        "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md",
        "basis": "Day Master strength is treated through the month/season first, then Day-branch normal root, Hour-branch secret root, and formation support across Tian Gan, Di Zhi, eight palaces, and hidden stems.",
    },
    {
        "id": "local.destiny_code_favorable_elements",
        "label": "BaZi - The Destiny Code",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md",
        "basis": "Favorable elements are introduced through strong-versus-weak Day Master balancing before full Yong Shen work.",
    },
    {
        "id": "local.destiny_code_revealed_relationships",
        "label": "BaZi - The Destiny Code Revealed",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md",
        "basis": "Relationship-code severity depends on code type, affected element, affected palace, and natal versus timing activation.",
    },
    {
        "id": "local.destiny_code_five_factors",
        "label": "BaZi - The Destiny Code",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md",
        "basis": "Five Factors are interpreted from the Day Master as Wealth, Output, Influence, Resource, and Companion before direct or indirect Ten God labels are expanded.",
    },
    {
        "id": "local.destiny_code_peach_blossom",
        "label": "BaZi - The Destiny Code",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md",
        "basis": "Personal Peach Blossom is derived from the Day Branch and may appear in natal, Luck Pillar, or annual branches as attraction/popularity potential.",
    },
    {
        "id": "local.destiny_code_revealed_peach_blossom",
        "label": "BaZi - The Destiny Code Revealed",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md",
        "basis": "Peach Blossom must be read with placement, affected palace, element quality, and relationship-contact pressure rather than as an automatic promise.",
    },
    {
        "id": "local.four_pillars_palace_context",
        "label": "Ba Zi - The Four Pillars of Destiny",
        "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md",
        "basis": "Hour, Day, Month, and Year pillars are read as eight Tian Gan/Di Zhi palaces with life-stage and domain emphasis; adjacent palace interactions carry more weight than separated contacts.",
    },
    {
        "id": "local.four_pillars_climate_regulating",
        "label": "Ba Zi - The Four Pillars of Destiny",
        "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md",
        "basis": "Season and month branch are read before final usefulness; growth/cardinal/graveyard branch state and climate correction can name regulating needs separately from simple strength balancing.",
    },
    {
        "id": "local.destiny_code_damaged_useful_element",
        "label": "BaZi - The Destiny Code Revealed",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md",
        "basis": "A favorable element is not automatically useful when absent, blocked, or pressured by active relationship contacts.",
    },
    {
        "id": "local.lu_zhiji_climate_regulating",
        "label": "Lu Zhiji reproduction/revision of Zhong/Liang climate tables",
        "path": "output/chinese_books_private_corpus/ocr/lu_zhiji_fate_search/document.ocr.pages.jsonl",
        "basis": "Lu reproduces Zhong Yiming's ten-Day-Stem by twelve-month regulating tables, cross-checks Liang Xiangrun, and notes slight revisions (PDF pp240-246). The app's priority, function, and override fields are provisional operational metadata rather than literal source columns.",
    },
)


FACTOR_ORDER = ("Companion", "Output", "Wealth", "Influence", "Resource")

FACTOR_KEYWORDS = {
    "Companion": ["willpower", "self-confidence", "peers", "siblings", "competition"],
    "Output": ["expression", "creativity", "communication", "execution", "persuasion"],
    "Wealth": ["assets", "income", "management", "resource control", "capacity"],
    "Influence": ["authority", "rules", "discipline", "status", "responsibility"],
    "Resource": ["learning", "knowledge", "support", "intuition", "assistance"],
}

FACTOR_SOURCE_NOTES = {
    "Companion": "Same-element placements describe self-reference, peers, rivalry, and the confidence or willpower tone around the Day Master.",
    "Output": "Produced-element placements describe expression, skill, creativity, communication, and the ability to turn ideas into action.",
    "Wealth": "Controlled-element placements describe assets, money handling, management capacity, and the chart's relationship with material resources.",
    "Influence": "Controlling-element placements describe rules, pressure, authority, discipline, responsibility, and social status themes.",
    "Resource": "Producing-element placements describe learning, support, knowledge, intuition, protection, and help received by the Day Master.",
}

FACTOR_UI_META = {
    "Companion": {
        "chinese": "比劫",
        "pinyin": "bi jie",
        "relation_chinese": "同我",
        "relation_label": "same element as the Day Master",
        "domain_summary": "Peers, siblings, confidence, independence, competition, and shared resources.",
    },
    "Output": {
        "chinese": "食傷",
        "pinyin": "shi shang",
        "relation_chinese": "我生",
        "relation_label": "the Day Master produces this element",
        "domain_summary": "Expression, talent, production, communication, craft, and visible output.",
    },
    "Wealth": {
        "chinese": "財星",
        "pinyin": "cai xing",
        "relation_chinese": "我克",
        "relation_label": "the Day Master controls this element",
        "domain_summary": "Value, assets, money handling, practical management, and material responsibilities.",
    },
    "Influence": {
        "chinese": "官殺",
        "pinyin": "guan sha",
        "relation_chinese": "克我",
        "relation_label": "this element controls the Day Master",
        "domain_summary": "Rules, pressure, authority, responsibility, discipline, status, and career structure.",
    },
    "Resource": {
        "chinese": "印梟",
        "pinyin": "yin xiao",
        "relation_chinese": "生我",
        "relation_label": "this element produces the Day Master",
        "domain_summary": "Learning, protection, credentials, counsel, support, recovery, and intuition.",
    },
}

FACTOR_LAYER_LABELS = {
    "absent": "not emphasized",
    "surface": "surface-visible",
    "hidden": "hidden-stem placement",
    "surface_and_hidden": "visible and hidden",
}

YONG_SHEN_RULE_FAMILIES = {
    "strong_balancing": "yong_shen.strong_balancing",
    "weak_support": "yong_shen.weak_support",
    "climate_override": "yong_shen.climate_override",
    "dominant_element": "yong_shen.dominant_element",
    "follow_structure": "yong_shen.follow_structure",
    "transformation_structure": "yong_shen.transformation_structure",
    "damaged_alternate": "yong_shen.damaged_alternate",
    "tong_guan": "yong_shen.tong_guan",
    "timing_assisted": "yong_shen.timing_assisted",
    "damage_withheld": "yong_shen.damage_withheld",
    "special_structure_withheld": "yong_shen.special_structure_withheld",
    "balanced_withheld": "yong_shen.balanced_withheld",
    "confidence_withheld": "yong_shen.confidence_withheld",
}

HEAVENLY_STEM_TRANSFORMATIONS = {
    frozenset(("Jia", "Ji")): "Earth",
    frozenset(("Yi", "Geng")): "Metal",
    frozenset(("Bing", "Xin")): "Water",
    frozenset(("Ding", "Ren")): "Wood",
    frozenset(("Wu", "Gui")): "Fire",
}


def _inverse_lookup(mapping: Dict[str, str], target: str) -> Optional[str]:
    for source, mapped in mapping.items():
        if mapped == target:
            return source
    return None


def _element_role_map(day_element: str) -> Dict[str, str]:
    return {
        "Companion": day_element,
        "Output": PRODUCES[day_element],
        "Wealth": CONTROLS[day_element],
        "Influence": _inverse_lookup(CONTROLS, day_element) or "",
        "Resource": _inverse_lookup(PRODUCES, day_element) or "",
    }


def _factor_placement(row: Dict[str, Any], layer: str) -> Dict[str, Any]:
    placement = {
        "layer": layer,
        "pillar": row.get("pillar"),
        "stem": row.get("stem"),
        "god": row.get("god"),
    }
    if row.get("rank") is not None:
        placement["rank"] = row.get("rank")
    return placement


def _factor_favorability(factor: str, element: str, useful_elements: Optional[Dict[str, Any]]) -> str:
    if not isinstance(useful_elements, dict) or useful_elements.get("status") != "provisional":
        return "unresolved"

    favorable_roles: set[str] = set()
    favorable_elements: set[str] = set()
    caution_roles: set[str] = set()
    caution_elements: set[str] = set()
    for row in useful_elements.get("favorable") or []:
        if not isinstance(row, dict):
            continue
        if row.get("role"):
            favorable_roles.add(str(row["role"]))
        if row.get("element"):
            favorable_elements.add(str(row["element"]))
    for row in useful_elements.get("unfavorable") or []:
        if not isinstance(row, dict):
            continue
        if row.get("role"):
            caution_roles.add(str(row["role"]))
        if row.get("element"):
            caution_elements.add(str(row["element"]))

    if factor in favorable_roles or element in favorable_elements:
        return "favorable"
    if factor in caution_roles or element in caution_elements:
        return "caution"
    return "neutral"


FACTOR_STATUS_LABELS = {
    "final_useful": "Final useful",
    "favorable_candidate": "Useful",
    "pressured_useful": "Pressured",
    "needed_absent": "Needed",
    "timing_activated": "Timing",
    "timing_challenged": "Timing pressure",
    "caution": "Caution",
    "neutral": "Neutral",
    "balanced_watch": "Topic",
    "role_only": "Role",
    "quiet": "Quiet",
}

FACTOR_STATUS_TONES = {
    "final_useful": "favorable",
    "favorable_candidate": "favorable",
    "pressured_useful": "caution",
    "needed_absent": "caution",
    "timing_activated": "favorable",
    "timing_challenged": "caution",
    "caution": "caution",
    "neutral": "neutral",
    "balanced_watch": "neutral",
    "role_only": "neutral",
    "quiet": "neutral",
}


def _matches_factor_element(row: Dict[str, Any], factor: str, element: str) -> bool:
    return row.get("role") == factor or row.get("factor") == factor or row.get("element") == element


def _first_matching_row(rows: Any, factor: str, element: str) -> Optional[Dict[str, Any]]:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and _matches_factor_element(row, factor, element):
            return row
    return None


def _strength_factor_direction(strength: str, factor: str) -> str:
    normalized = str(strength or "").lower()
    if normalized in {"strong", "very strong", "extremely strong"}:
        if factor in {"Output", "Wealth", "Influence"}:
            return "favorable"
        if factor in {"Companion", "Resource"}:
            return "caution"
    if normalized in {"weak", "very weak", "extremely weak"}:
        if factor in {"Resource", "Companion"}:
            return "favorable"
        if factor in {"Output", "Wealth", "Influence"}:
            return "caution"
    if normalized in {"balanced", "uncertain", "mixed"}:
        return "balanced"
    return "open"


def _factor_decision_status(
    *,
    factor: str,
    element: str,
    visible_count: int,
    hidden_count: int,
    favorability: str,
    analysis: Dict[str, Any],
    useful_elements: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    total_count = visible_count + hidden_count
    useful_payload = useful_elements if isinstance(useful_elements, dict) else {}
    strength = str(
        useful_payload.get("day_master_strength")
        or analysis.get("strength")
        or "uncertain"
    ).lower()
    direction = favorability if favorability != "unresolved" else _strength_factor_direction(strength, factor)
    favorable_row = _first_matching_row(useful_payload.get("favorable"), factor, element)
    caution_row = _first_matching_row(useful_payload.get("unfavorable"), factor, element)
    damage_row = _first_matching_row(useful_payload.get("damage_assessment"), factor, element)
    timing = useful_payload.get("timing_interaction") if isinstance(useful_payload.get("timing_interaction"), dict) else {}
    timing_row = _first_matching_row(timing.get("items"), factor, element)
    useful_god = useful_payload.get("useful_god") if isinstance(useful_payload.get("useful_god"), dict) else {}
    useful_match = useful_god and (
        useful_god.get("role") == factor
        or useful_god.get("element") == element
    )

    basis: List[str] = []
    if strength in {"strong", "very strong", "extremely strong"}:
        basis.append("Strong Day Master gate: Output, Wealth, and Influence can drain, spend, or restrain excess.")
    elif strength in {"weak", "very weak", "extremely weak"}:
        basis.append("Weak Day Master gate: Resource and Companion can rebuild support.")

    for row in (favorable_row, caution_row):
        if isinstance(row, dict) and row.get("reason"):
            basis.append(str(row["reason"]))
            break

    integrity = {}
    for row in (favorable_row, caution_row):
        if isinstance(row, dict) and isinstance(row.get("integrity"), dict):
            integrity = row["integrity"]
            break
    if integrity.get("summary"):
        basis.append(str(integrity["summary"]))

    damage_status = str((damage_row or {}).get("status") or "")
    if damage_row and damage_row.get("reason"):
        basis.append(str(damage_row["reason"]))
    timing_status = str((timing_row or {}).get("status") or "")
    if timing_row and timing_row.get("summary"):
        basis.append(str(timing_row["summary"]))

    if useful_match and useful_god.get("final_status") == "final":
        status = "final_useful"
    elif damage_status == "damaged":
        status = "pressured_useful"
    elif damage_status == "presence_missing":
        status = "needed_absent"
    elif timing_status == "pressured_by_timing":
        status = "timing_challenged"
    elif damage_status == "timing_assisted" or timing_status in {
        "supplied_by_timing",
        "supported_by_timing",
        "activated_by_timing",
    }:
        status = "timing_activated"
    elif direction == "favorable" or (useful_match and useful_god.get("candidate_status") == "candidate_preview"):
        status = "favorable_candidate"
    elif direction == "caution":
        status = "caution"
    elif direction == "neutral":
        status = "neutral"
    elif direction == "balanced":
        status = "balanced_watch"
    elif total_count <= 0:
        status = "quiet"
    else:
        status = "role_only"

    return {
        "functional_status": status,
        "status_label": FACTOR_STATUS_LABELS.get(status, status.replace("_", " ").title()),
        "status_tone": FACTOR_STATUS_TONES.get(status, "neutral"),
        "strength_direction": direction,
        "damage_status": damage_status or None,
        "timing_status": timing_status or None,
        "decision_basis": list(dict.fromkeys(basis))[:4],
    }


def _factor_layer_status(visible_count: int, hidden_count: int) -> str:
    if visible_count and hidden_count:
        return "surface_and_hidden"
    if visible_count:
        return "surface"
    if hidden_count:
        return "hidden"
    return "absent"


def _factor_summary(
    *,
    factor: str,
    element: str,
    visible_count: int,
    hidden_count: int,
    favorability: str,
    functional_status: str,
) -> str:
    total = visible_count + hidden_count
    if total <= 0:
        if functional_status == "needed_absent":
            return f"{factor} ({element}) is the balancing need by strength logic, but it is not available in checked natal or timing placements."
        return f"{factor} is not emphasized by configured stem placements, so its {element} topics should stay secondary."

    if visible_count and hidden_count:
        layer_text = "appears both on visible stems and in hidden branch stems"
    elif visible_count:
        layer_text = "is visible on the stems, so it is easier to read as outward behavior or visible circumstance"
    else:
        layer_text = "appears in hidden stems, so it is concealed, latent, or context-dependent; hidden placement alone does not establish a usable root"

    if functional_status == "final_useful":
        balance_text = "It is the released useful direction for this chart after the strength, fixture, and damage gates are clear."
    elif functional_status == "pressured_useful":
        balance_text = "It would help by strength logic, but contact pressure touches its element, so read it as useful but unstable."
    elif functional_status == "needed_absent":
        balance_text = "It is a needed balancing direction, but it was not found in checked natal or timing placements."
    elif functional_status == "timing_activated":
        balance_text = "Current timing repeats or activates this factor, making its topics active in the decade/year layer without proving usable qi."
    elif functional_status == "timing_challenged":
        balance_text = "Current timing pressures this factor, so its topics are active but strained."
    elif functional_status == "favorable_candidate" or favorability == "favorable":
        balance_text = "It aligns with the current favorable-element direction for this Day Master strength gate."
    elif functional_status == "caution" or favorability == "caution":
        balance_text = "It belongs to the current caution group, so quantity should not be mistaken for benefit."
    elif favorability == "neutral":
        balance_text = "It is not currently classified as favorable or cautionary."
    elif functional_status == "balanced_watch":
        return f"{factor} ({element}) {layer_text}."
    elif functional_status == "role_only":
        balance_text = "It is present as topic evidence, with no useful-element priority assigned for the current chart state."
    else:
        balance_text = "It is present as a role marker, while strength and timing gates do not prioritize it."

    return f"{factor} ({element}) {layer_text}. {balance_text}"


def _profile_summary(factors: List[Dict[str, Any]]) -> str:
    active = [factor for factor in factors if int(factor.get("total_count") or 0) > 0]
    if not active:
        return "No configured Five Factor placements were detected beyond the Day Master reference point."

    visible = sorted(
        active,
        key=lambda item: (-int(item.get("visible_count") or 0), -int(item.get("total_count") or 0), str(item.get("factor") or "")),
    )
    hidden_ranked = sorted(
        active,
        key=lambda item: (-int(item.get("hidden_count") or 0), -int(item.get("total_count") or 0), str(item.get("factor") or "")),
    )
    most_visible = visible[0] if int(visible[0].get("visible_count") or 0) else None
    most_hidden = hidden_ranked[0] if int(hidden_ranked[0].get("hidden_count") or 0) else None
    parts = []
    if most_visible:
        parts.append(f"{most_visible.get('factor')} is the most visible factor")
    if most_hidden:
        parts.append(f"{most_hidden.get('factor')} is the most repeated hidden-stem factor")
    if not parts:
        parts.append(f"{active[0].get('factor')} is the most repeated configured factor")
    return "; ".join(parts) + ". Ten God labels are read through these Five Factor families before making topic claims."


def build_ten_god_profile(
    *,
    day_stem_index: int,
    ten_gods: Dict[str, Any],
    analysis: Dict[str, Any],
    useful_elements: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day_stem = STEMS[int(day_stem_index) % 10]
    day_element = str(day_stem["element"])
    roles = _element_role_map(day_element)
    visible_rows = [row for row in ten_gods.get("visible") or [] if isinstance(row, dict)]
    hidden_rows = [row for row in ten_gods.get("hidden") or [] if isinstance(row, dict)]

    by_factor: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        factor: {"visible": [], "hidden": []}
        for factor in FACTOR_ORDER
    }
    for row in visible_rows:
        factor = row.get("factor")
        if factor in by_factor:
            by_factor[str(factor)]["visible"].append(row)
    for row in hidden_rows:
        factor = row.get("factor")
        if factor in by_factor:
            by_factor[str(factor)]["hidden"].append(row)

    factors: List[Dict[str, Any]] = []
    for factor in FACTOR_ORDER:
        element = roles.get(factor, "")
        visible = by_factor[factor]["visible"]
        hidden = by_factor[factor]["hidden"]
        visible_count = len(visible)
        hidden_count = len(hidden)
        layer_status = _factor_layer_status(visible_count, hidden_count)
        favorability = _factor_favorability(factor, element, useful_elements)
        decision_status = _factor_decision_status(
            factor=factor,
            element=element,
            visible_count=visible_count,
            hidden_count=hidden_count,
            favorability=favorability,
            analysis=analysis,
            useful_elements=useful_elements,
        )
        gods = sorted({
            str(row.get("god"))
            for row in [*visible, *hidden]
            if row.get("god")
        })
        placements = [
            *(_factor_placement(row, "visible") for row in visible),
            *(_factor_placement(row, "hidden") for row in hidden),
        ]
        factors.append({
            "factor": factor,
            "chinese": FACTOR_UI_META[factor]["chinese"],
            "pinyin": FACTOR_UI_META[factor]["pinyin"],
            "relation_chinese": FACTOR_UI_META[factor]["relation_chinese"],
            "relation_label": FACTOR_UI_META[factor]["relation_label"],
            "domain_summary": FACTOR_UI_META[factor]["domain_summary"],
            "element": element,
            "keywords": FACTOR_KEYWORDS[factor],
            "source_note": FACTOR_SOURCE_NOTES[factor],
            "visible_count": visible_count,
            "hidden_count": hidden_count,
            "total_count": visible_count + hidden_count,
            "layer_status": layer_status,
            "layer_label": FACTOR_LAYER_LABELS[layer_status],
            "favorability": favorability,
            "functional_status": decision_status["functional_status"],
            "status_label": decision_status["status_label"],
            "status_tone": decision_status["status_tone"],
            "strength_direction": decision_status["strength_direction"],
            "damage_status": decision_status["damage_status"],
            "timing_status": decision_status["timing_status"],
            "decision_basis": decision_status["decision_basis"],
            "gods": gods,
            "placements": placements,
            "summary": _factor_summary(
                factor=factor,
                element=element,
                visible_count=visible_count,
                hidden_count=hidden_count,
                favorability=favorability,
                functional_status=decision_status["functional_status"],
            ),
        })

    notes = [
        "Visible stems describe surface expression, while hidden stems show concealed or latent material; hidden-count presence alone does not establish rooted qi.",
    ]
    if str(analysis.get("strength") or "").lower() in {"balanced", "uncertain"}:
        notes.append("A useful-factor priority needs a decisive strength gate or a released climate/special-structure override.")

    return {
        "status": "source_based_preview",
        "interpretation_status": "strength_timing_contact_gated",
        "method": "five_factor_profile_v1",
        "day_master_reference": {
            "stem": day_stem["key"],
            "element": day_element,
            "polarity": day_stem["polarity"],
        },
        "summary": _profile_summary(factors),
        "factors": factors,
        "visible_top": _top_counts(visible_rows, "factor"),
        "hidden_top": _top_counts(hidden_rows, "factor"),
        "notes": notes,
        "derivation_notes": [
            "同我: same element as the Day Master gives Friend / Rob Wealth.",
            "我生: what the Day Master produces gives Eating God / Hurting Officer.",
            "我克: what the Day Master controls gives Indirect Wealth / Direct Wealth.",
            "克我: what controls the Day Master gives Seven Killings / Direct Officer.",
            "生我: what produces the Day Master gives Indirect Resource / Direct Resource.",
        ],
        "context_requirements": [
            "Day Master strength",
            "useful-element direction",
            "visibility and hidden-stem rank",
            "palace placement",
            "timing activation",
            "stem/branch contacts",
        ],
        "source_basis": [LOCAL_SOURCE_BASIS[3], LOCAL_SOURCE_BASIS[0]],
        "source_confidence": confidence_tags("local_source", "computed_rule"),
    }


def _role_item(
    *,
    element: str,
    role: str,
    priority: str,
    reason: str,
    counts: Dict[str, int],
) -> Dict[str, Any]:
    presence_count = int(counts.get(element) or 0)
    return {
        "element": element,
        "role": role,
        "priority": priority,
        "count": presence_count,
        "presence_count": presence_count,
        "presence_measure": "unweighted_presence_count",
        "qi_strength_status": "not_evaluated",
        "reason": reason,
    }


PILLAR_LABELS = {
    "year": "Year",
    "month": "Month",
    "day": "Day",
    "hour": "Hour",
    "luck": "Current Luck",
    "annual": "Current Year",
}

CHALLENGING_RELATIONSHIPS = {
    "branch_clash",
    "branch_harm",
    "branch_punishment",
    "self_punishment",
    "branch_destruction",
}

SUPPORTIVE_RELATIONSHIPS = {
    "stem_combination",
    "branch_combination",
    "three_harmony_combination",
    "seasonal_combination",
}


def _stem_element(symbol: Any) -> Optional[str]:
    key = str(symbol or "")
    if key not in STEM_INDEX:
        return None
    return str(STEMS[STEM_INDEX[key]]["element"])


def _branch_element(symbol: Any) -> Optional[str]:
    key = str(symbol or "")
    if key not in BRANCH_INDEX:
        return None
    return str(BRANCHES[BRANCH_INDEX[key]]["element"])


def _pillar_sources(
    pillar_name: str,
    pillar: Optional[Dict[str, Any]],
    element: str,
    *,
    layer: str,
) -> List[Dict[str, Any]]:
    if not isinstance(pillar, dict):
        return []
    label = PILLAR_LABELS.get(pillar_name, pillar_name.title())
    sources: List[Dict[str, Any]] = []
    stem = pillar.get("stem")
    if pillar.get("stem_element") == element:
        sources.append({
            "layer": layer,
            "pillar": pillar_name,
            "part": "stem",
            "symbol": stem,
            "label": f"{label} stem {stem}",
        })
    branch = pillar.get("branch")
    if pillar.get("branch_element") == element:
        sources.append({
            "layer": layer,
            "pillar": pillar_name,
            "part": "branch",
            "symbol": branch,
            "label": f"{label} branch {branch}",
        })
    for hidden in pillar.get("hidden_stems") or []:
        if isinstance(hidden, dict) and hidden.get("element") == element:
            symbol = hidden.get("key") or hidden.get("stem")
            sources.append({
                "layer": layer,
                "pillar": pillar_name,
                "part": "hidden_stem",
                "symbol": symbol,
                "label": f"{label} hidden {symbol}",
            })
    return sources


def _natal_sources_for_element(pillars: Dict[str, Optional[Dict[str, Any]]], element: str) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    for pillar_name in ("year", "month", "day", "hour"):
        sources.extend(_pillar_sources(pillar_name, pillars.get(pillar_name), element, layer="natal"))
    return sources


def _timing_sources_for_element(timing: Dict[str, Any], element: str) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    active_luck = timing.get("active_luck_pillar")
    annual = timing.get("annual_pillar")
    sources.extend(_pillar_sources("luck", active_luck, element, layer="luck"))
    sources.extend(_pillar_sources("annual", annual, element, layer="annual"))
    return sources


def _relationship_tone(event_type: Any) -> str:
    normalized = str(event_type or "")
    if normalized in CHALLENGING_RELATIONSHIPS:
        return "challenging"
    if normalized in SUPPORTIVE_RELATIONSHIPS:
        return "supportive"
    return "mixed"


def _relationship_event_elements(event: Dict[str, Any]) -> set[str]:
    event_type = str(event.get("type") or "")
    branch_event = event_type.startswith("branch_") or event_type in {
        "three_harmony_combination",
        "seasonal_combination",
        "self_punishment",
    }
    stem_event = event_type == "stem_combination"
    elements: set[str] = set()
    explicit = event.get("element")
    if explicit in ELEMENTS:
        elements.add(str(explicit))
    for symbol in event.get("symbols") or []:
        if stem_event:
            element = _stem_element(symbol)
        elif branch_event:
            element = _branch_element(symbol)
        else:
            element = _stem_element(symbol) or _branch_element(symbol)
        if element:
            elements.add(element)
    for point in event.get("points") or []:
        if not isinstance(point, dict):
            continue
        if stem_event:
            element = _stem_element(point.get("stem"))
            if element:
                elements.add(element)
        elif branch_event:
            element = _branch_element(point.get("branch"))
            if element:
                elements.add(element)
        else:
            for element in (_stem_element(point.get("stem")), _branch_element(point.get("branch"))):
                if element:
                    elements.add(element)
    return elements


def _element_impacts(element: str, relationships: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = relationships.get("events") if isinstance(relationships, dict) else []
    impacts: List[Dict[str, Any]] = []
    for event in events or []:
        if not isinstance(event, dict) or element not in _relationship_event_elements(event):
            continue
        impacts.append({
            "label": event.get("label") or event.get("type") or "relationship code",
            "type": event.get("type"),
            "scope": event.get("scope"),
            "scope_label": event.get("scope_label") or event.get("scope"),
            "tone": _relationship_tone(event.get("type")),
            "intensity": event.get("intensity"),
            "affected_palaces": event.get("affected_palaces") or [],
        })
    tone_rank = {"challenging": 0, "supportive": 1, "mixed": 2}
    return sorted(impacts, key=lambda item: (tone_rank.get(str(item.get("tone")), 9), str(item.get("label") or "")))[:4]


def _integrity_summary(
    *,
    element: str,
    role_group: str,
    natal_sources: List[Dict[str, Any]],
    timing_sources: List[Dict[str, Any]],
    impacts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    challenging = [impact for impact in impacts if impact.get("tone") == "challenging"]
    supportive = [impact for impact in impacts if impact.get("tone") == "supportive"]
    if natal_sources:
        availability = "present_natal"
        opening = f"{element} is present in the natal chart."
    elif timing_sources:
        availability = "timing_supported"
        opening = f"{element} is not present in checked natal placements, but current timing introduces it."
    else:
        availability = "missing"
        opening = f"{element} was not found in checked natal placements or current timing."

    if challenging:
        pressure = "pressured"
        pressure_text = "A challenging relationship code touches this element."
    elif supportive:
        pressure = "supported"
        pressure_text = "A combination or formation touches this element."
    else:
        pressure = "clear"
        pressure_text = "No configured relationship-contact pressure touches this element."

    if role_group == "favorable" and pressure == "pressured":
        pressure_text = "A favorable element is touched by a challenging code, so this stays provisional."
    elif role_group == "unfavorable" and pressure == "pressured":
        pressure_text = "A challenging code touches a caution element; this may reduce or agitate it rather than read as uniformly bad."

    return {
        "availability": availability,
        "availability_semantics": "placement_presence_only",
        "pressure": pressure,
        "decision_authority": "none",
        "summary": f"{opening} {pressure_text}",
    }


def _with_element_integrity(
    recommendations: Dict[str, Any],
    *,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    relationships: Optional[Dict[str, Any]],
    timing: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(recommendations, dict):
        return recommendations

    pillar_data = pillars or {}
    relationship_data = relationships or {}
    timing_data = timing or {}
    payload = {**recommendations}
    day_master_element = str(recommendations.get("day_master_element") or "")
    integrity_rows: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for group_name in ("favorable", "unfavorable", "candidates_to_watch"):
        rows = recommendations.get(group_name)
        if not isinstance(rows, list):
            continue
        updated_rows: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("element"):
                updated_rows.append(row)
                continue
            element = str(row["element"])
            role_group = "watch" if group_name == "candidates_to_watch" else group_name
            raw_natal_sources = _natal_sources_for_element(pillar_data, element)
            day_master_reference_sources = [
                source
                for source in raw_natal_sources
                if element == day_master_element
                and source.get("pillar") == "day"
                and source.get("part") == "stem"
            ]
            natal_sources = [
                source
                for source in raw_natal_sources
                if source not in day_master_reference_sources
            ]
            timing_sources = _timing_sources_for_element(timing_data, element)
            impacts = _element_impacts(element, relationship_data)
            state = _integrity_summary(
                element=element,
                role_group=role_group,
                natal_sources=natal_sources,
                timing_sources=timing_sources,
                impacts=impacts,
            )
            raw_inventory_presence_count = int(row.get("presence_count") or row.get("count") or len(raw_natal_sources) or 0)
            candidate_presence_count = len(natal_sources)
            integrity = {
                **state,
                "natal_count": candidate_presence_count,
                "natal_presence_count": candidate_presence_count,
                "raw_inventory_presence_count": raw_inventory_presence_count,
                "day_master_reference_excluded": bool(day_master_reference_sources),
                "day_master_reference_excluded_count": len(day_master_reference_sources),
                "presence_measure": "unweighted_presence_count",
                "qi_strength_status": "not_evaluated",
                "decision_authority": "none",
                "natal_sources": natal_sources[:5],
                "timing_sources": timing_sources[:5],
                "event_impacts": impacts,
            }
            updated = {
                **row,
                "candidate_presence_count": candidate_presence_count,
                "integrity": integrity,
            }
            updated_rows.append(updated)

            key = (role_group, element)
            if key not in seen:
                seen.add(key)
                integrity_rows.append({
                    "element": element,
                    "role_group": role_group,
                    "role": row.get("role"),
                    "priority": row.get("priority"),
                    **integrity,
                })
        payload[group_name] = updated_rows

    favorable_rows = [row for row in integrity_rows if row.get("role_group") == "favorable"]
    unfavorable_rows = [row for row in integrity_rows if row.get("role_group") == "unfavorable"]
    payload["element_integrity"] = integrity_rows
    payload["integrity_summary"] = {
        "favorable_present": sum(1 for row in favorable_rows if row.get("availability") == "present_natal"),
        "favorable_missing": sum(1 for row in favorable_rows if row.get("availability") == "missing"),
        "favorable_timing_supported": sum(1 for row in favorable_rows if row.get("availability") == "timing_supported"),
        "favorable_pressured": sum(1 for row in favorable_rows if row.get("pressure") == "pressured"),
        "unfavorable_pressured": sum(1 for row in unfavorable_rows if row.get("pressure") == "pressured"),
    }
    notes = list(payload.get("notes") or [])
    integrity_note = (
        "Placement presence distinguishes natal, timing, and not-found evidence for display only; it does not establish candidate qi or decision eligibility."
    )
    if integrity_note not in notes:
        notes.append(integrity_note)
    payload["notes"] = notes
    return payload


CHINESE_CLIMATE_SOURCE_BASIS = LOCAL_SOURCE_BASIS[9]

CLIMATE_SOURCE_READY_STATUSES = {"day_stem_month_rule", "day_stem_configuration_rule"}

CLIMATE_OVERRIDE_FUNCTION_MARKERS = (
    "cooling",
    "moisture",
    "water regulation",
    "root moisture",
    "warming refinement",
    "warming support",
    "moisture balance",
)

JIA_MONTH_CLIMATE_STEMS: Dict[str, Tuple[Tuple[str, str, str], ...]] = {
    "Yin": (
        ("Bing", "warming and growth circulation", "primary"),
        ("Gui", "moisture support", "secondary"),
    ),
    "Mao": (
        ("Geng", "pruning and shaping", "primary"),
        ("Bing", "circulation", "secondary"),
        ("Ding", "refinement", "secondary"),
        ("Wu", "rooting earth", "conditional"),
        ("Ji", "rooting earth", "conditional"),
    ),
    "Chen": (
        ("Geng", "pruning and shaping", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Ren", "moisture support", "secondary"),
    ),
    "Si": (
        ("Gui", "cooling and moisture regulation", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Geng", "shaping support", "secondary"),
    ),
    "Wu": (
        ("Gui", "cooling and moisture regulation", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Geng", "shaping support", "secondary"),
    ),
    "Wei": (
        ("Gui", "cooling and moisture regulation", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Geng", "shaping support", "secondary"),
    ),
    "Shen": (
        ("Geng", "shaping support", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Bing", "warming circulation", "secondary"),
    ),
    "You": (
        ("Geng", "shaping support", "primary"),
        ("Ding", "refinement", "secondary"),
        ("Bing", "warming circulation", "secondary"),
    ),
    "Xu": (
        ("Geng", "shaping support", "primary"),
        ("Jia", "same-stem reinforcement", "secondary"),
        ("Ding", "refinement", "secondary"),
        ("Ren", "moisture support", "conditional"),
        ("Gui", "moisture support", "conditional"),
    ),
    "Hai": (
        ("Geng", "shaping support", "primary"),
        ("Ding", "warming refinement", "secondary"),
        ("Bing", "warming circulation", "secondary"),
        ("Wu", "earth containment", "conditional"),
    ),
    "Zi": (
        ("Ding", "warming refinement", "primary"),
        ("Geng", "source and shaping support", "secondary"),
        ("Bing", "warming circulation", "secondary"),
    ),
    "Chou": (
        ("Ding", "warming refinement", "primary"),
        ("Geng", "source and shaping support", "secondary"),
        ("Bing", "warming circulation", "secondary"),
    ),
}

YI_MONTH_CLIMATE_STEMS: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "Wei": (
        (
            "Gui",
            "moistening Earth and nourishing Wood",
            "primary",
            "Gui moistens Earth and nourishes Yi Wood in Wei month.",
        ),
        (
            "Bing",
            "warming when Metal and Water are abundant",
            "secondary",
            "Use Bing first when the pillars contain abundant Metal and Water in Wei month.",
        ),
    ),
}

BING_MONTH_CLIMATE_STEMS: Dict[str, Tuple[Tuple[str, str, str, str], ...]] = {
    "Hai": (
        (
            "Jia",
            "transforming excessive Water through Wood",
            "primary",
            "Use Jia when Hai-month Water is excessive, transforming it through Wood.",
        ),
        (
            "Wu",
            "earth containment when both body and killing-water are strong",
            "conditional",
            "Use Wu when both the Bing Day Master and killing-water are strong in Hai month.",
        ),
        (
            "Geng",
            "controlling excessive Wood",
            "conditional",
            "Use Geng only when Wood is excessive in Hai month.",
        ),
        (
            "Ren",
            "water regulation only when fire is excessive",
            "conditional",
            "Use Ren only when Fire is excessive in Hai month.",
        ),
    ),
}

GENG_MONTH_CLIMATE_STEMS: Dict[str, Tuple[Tuple[str, str, str, str], ...]] = {
    "Hai": (
        (
            "Ding",
            "warming refinement before ordinary Wealth/Output logic",
            "primary",
            "Hai month cold water needs Fire before ordinary Wealth/Output logic.",
        ),
        ("Bing", "visible warmth in winter metal-water", "secondary", "Bing supports winter warmth when Ding is weak."),
        ("Jia", "material that lets Ding Fire function", "secondary", "Jia assists Ding by giving Fire something to use."),
    ),
    "Zi": (
        (
            "Ding",
            "warming refinement before ordinary Wealth/Output logic",
            "primary",
            "Zi month cold water needs Fire before ordinary Wealth/Output logic.",
        ),
        ("Jia", "material that lets Ding Fire function", "secondary", "Jia assists Ding by giving Fire something to use."),
        ("Bing", "visible warmth in winter metal-water", "secondary", "Bing supports winter warmth when Ding is weak."),
    ),
    "Chou": (
        (
            "Bing",
            "visible winter warmth before ordinary Wealth/Output logic",
            "primary",
            "Chou month cold-damp earth asks for warmth before ordinary Wealth/Output logic.",
        ),
        ("Jia", "loosening and fuel support", "secondary", "Jia helps move cold-damp earth and supports Fire."),
        ("Ding", "refinement heat", "secondary", "Ding refines Geng when winter cold is not overwhelming."),
    ),
}

DAY_STEM_MONTH_CLIMATE_STEMS: Dict[str, Dict[str, Tuple[Tuple[str, ...], ...]]] = {
    "Jia": JIA_MONTH_CLIMATE_STEMS,
    "Yi": {
        "Yin": (("Bing", "warming growth with Gui root moisture", "primary"), ("Gui", "root moisture", "secondary")),
        "Mao": (("Bing", "warming visible growth", "primary"), ("Gui", "root moisture", "secondary")),
        "Chen": (("Gui", "moisture regulation", "primary"), ("Bing", "warming growth", "secondary"), ("Wu", "earth containment when water forms", "conditional")),
        "Si": (
            (
                "Gui",
                "cooling and root moisture",
                "primary",
                "Use Gui exclusively to regulate the urgent heat and dryness of Si month.",
            ),
        ),
        "Wu": (("Gui", "cooling and root moisture", "primary"), ("Bing", "visible growth", "secondary")),
        "Wei": YI_MONTH_CLIMATE_STEMS["Wei"],
        "Shen": (("Bing", "warming against autumn metal", "primary"), ("Gui", "moisture support", "secondary"), ("Ji", "rooting earth when metal is sharp", "conditional")),
        "You": (("Gui", "moisture support", "primary"), ("Bing", "warming visibility", "secondary"), ("Ding", "refinement fire", "secondary")),
        "Xu": (("Gui", "moisture support", "primary"), ("Xin", "metal source and pruning", "secondary")),
        "Hai": (("Bing", "warming for cold wood", "primary"), ("Wu", "earth containment for excess water", "secondary")),
        "Zi": (("Bing", "warming for cold wood", "primary"),),
        "Chou": (("Bing", "warming for cold damp wood", "primary"),),
    },
    "Bing": {
        "Yin": (("Ren", "water regulation for solar fire", "primary"), ("Geng", "source support for water", "secondary")),
        "Mao": (("Ren", "water regulation for solar fire", "primary"), ("Ji", "earth moderation when water is excessive", "conditional")),
        "Chen": (("Ren", "water regulation for solar fire", "primary"), ("Jia", "wood continuity", "secondary")),
        "Si": (("Ren", "water regulation for intense fire", "primary"), ("Geng", "source support", "secondary"), ("Gui", "moisture assistant", "conditional")),
        "Wu": (("Ren", "cooling water regulation", "primary"), ("Geng", "source support", "secondary")),
        "Wei": (("Ren", "cooling water regulation", "primary"), ("Geng", "source support", "secondary")),
        "Shen": (("Ren", "water regulation with autumn metal", "primary"), ("Wu", "earth containment when water is excessive", "conditional")),
        "You": (("Ren", "water regulation", "primary"), ("Gui", "moisture assistant", "secondary")),
        "Xu": (("Jia", "wood-led continuity", "primary"), ("Ren", "water regulation", "secondary")),
        "Hai": BING_MONTH_CLIMATE_STEMS["Hai"],
        "Zi": (("Ren", "water regulation", "primary"), ("Wu", "earth containment", "secondary"), ("Ji", "earth moderation", "conditional")),
        "Chou": (("Ren", "water regulation", "primary"), ("Jia", "wood continuity", "secondary")),
    },
    "Ding": {
        "Yin": (("Jia", "fuel and continuity", "primary"), ("Geng", "cutting support for fuel", "secondary")),
        "Mao": (("Geng", "cutting support for fuel", "primary"), ("Jia", "fuel and continuity", "secondary")),
        "Chen": (("Jia", "fuel and continuity", "primary"), ("Geng", "cutting support", "secondary")),
        "Si": (("Jia", "fuel and continuity", "primary"), ("Geng", "cutting support", "secondary")),
        "Wu": (("Ren", "water regulation for heat", "primary"), ("Geng", "source support", "secondary"), ("Gui", "moisture assistant", "conditional")),
        "Wei": (("Jia", "fuel and continuity", "primary"), ("Ren", "moisture balance", "secondary"), ("Geng", "source support", "conditional")),
        "Shen": (("Jia", "fuel and continuity", "primary"), ("Geng", "cutting support", "secondary"), ("Bing", "visible warmth", "secondary"), ("Wu", "earth containment", "conditional")),
        "You": (("Jia", "fuel and continuity", "primary"), ("Geng", "cutting support", "secondary"), ("Bing", "visible warmth", "secondary"), ("Wu", "earth containment", "conditional")),
        "Xu": (("Jia", "fuel and continuity", "primary"), ("Wu", "earth containment", "secondary"), ("Geng", "cutting support", "conditional")),
        "Hai": (("Jia", "fuel and continuity in cold water", "primary"), ("Geng", "cutting support", "secondary")),
        "Zi": (("Jia", "fuel and continuity in cold water", "primary"), ("Geng", "cutting support", "secondary")),
        "Chou": (("Jia", "fuel and continuity in cold damp earth", "primary"), ("Geng", "cutting support", "secondary")),
    },
    "Wu": {
        "Yin": (("Bing", "warming activation", "primary"), ("Jia", "wood loosening", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Mao": (("Bing", "warming activation", "primary"), ("Jia", "wood loosening", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Chen": (("Jia", "wood loosening", "primary"), ("Bing", "warming activation", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Si": (("Jia", "wood loosening", "primary"), ("Bing", "warming activation", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Wu": (("Ren", "cooling moisture for dry earth", "primary"), ("Jia", "wood loosening", "secondary"), ("Bing", "activation", "conditional")),
        "Wei": (("Gui", "moisture balance", "primary"), ("Bing", "warming activation", "secondary"), ("Jia", "wood loosening", "secondary")),
        "Shen": (("Bing", "warming activation in growing cold", "primary"), ("Gui", "moisture balance", "secondary"), ("Jia", "wood loosening", "secondary")),
        "You": (("Bing", "warming activation", "primary"), ("Gui", "moisture balance", "secondary")),
        "Xu": (("Jia", "wood loosening", "primary"), ("Bing", "warming activation", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Hai": (("Jia", "wood loosening", "primary"), ("Bing", "warming activation", "secondary")),
        "Zi": (("Bing", "warming activation", "primary"), ("Jia", "wood loosening", "secondary")),
        "Chou": (("Bing", "warming activation", "primary"), ("Jia", "wood loosening", "secondary")),
    },
    "Ji": {
        "Yin": (("Bing", "warming activation", "primary"), ("Geng", "source and clearing support", "secondary"), ("Jia", "wood structure", "secondary")),
        "Mao": (("Jia", "wood structure", "primary"), ("Gui", "moisture balance", "secondary"), ("Bing", "warming activation", "secondary")),
        "Chen": (("Bing", "warming activation", "primary"), ("Gui", "moisture balance", "secondary"), ("Jia", "wood structure", "secondary")),
        "Si": (("Gui", "cooling moisture", "primary"), ("Bing", "warming activation", "secondary")),
        "Wu": (("Gui", "cooling moisture", "primary"), ("Bing", "warming activation", "secondary")),
        "Wei": (("Gui", "cooling moisture", "primary"), ("Bing", "warming activation", "secondary")),
        "Shen": (("Bing", "warming activation", "primary"), ("Gui", "moisture balance", "secondary")),
        "You": (("Bing", "warming activation", "primary"), ("Gui", "moisture balance", "secondary")),
        "Xu": (("Jia", "wood structure", "primary"), ("Bing", "warming activation", "secondary"), ("Gui", "moisture balance", "secondary")),
        "Hai": (("Bing", "warming activation", "primary"), ("Jia", "wood structure", "secondary"), ("Wu", "earth containment", "conditional")),
        "Zi": (("Bing", "warming activation", "primary"), ("Jia", "wood structure", "secondary"), ("Wu", "earth containment", "conditional")),
        "Chou": (("Bing", "warming activation", "primary"), ("Jia", "wood structure", "secondary"), ("Wu", "earth containment", "conditional")),
    },
    "Geng": {
        "Yin": (
            ("Wu", "earth protection for buried metal", "primary", "Use Wu when Fire is excessive in Yin month."),
            ("Jia", "loosening thick Earth", "secondary", "Use Jia when thick Earth risks burying Geng Metal in Yin month."),
            ("Ren", "water tempering", "conditional", "Use Ren when the branches form a Fire configuration in Yin month."),
            ("Bing", "warming", "conditional", "Use Bing to warm Geng Metal in Yin month."),
            (
                "Ding",
                "additional Fire refinement",
                "conditional",
                "Use Ding only as the source-listed additional Fire regulator after the Yin-month warming and structural checks.",
            ),
        ),
        "Mao": (("Ding", "forging and refinement", "primary"), ("Jia", "fuel support", "secondary"), ("Geng", "same-metal reinforcement", "conditional"), ("Bing", "visible warmth", "secondary")),
        "Chen": (("Jia", "wood loosening", "primary"), ("Ding", "forging and refinement", "secondary"), ("Ren", "moisture tempering", "conditional"), ("Gui", "moisture assistant", "conditional")),
        "Si": (("Ren", "water tempering for heat", "primary"), ("Wu", "earth containment", "secondary"), ("Bing", "visible warmth", "conditional"), ("Ding", "refinement heat", "conditional")),
        "Wu": (("Ren", "water tempering for heat", "primary"), ("Gui", "moisture assistant", "secondary")),
        "Wei": (("Ding", "refinement heat", "primary"), ("Jia", "fuel support", "secondary")),
        "Shen": (("Ding", "forging and refinement", "primary"), ("Jia", "fuel support", "secondary")),
        "You": (("Ding", "forging and refinement", "primary"), ("Jia", "fuel support", "secondary"), ("Bing", "visible warmth", "secondary")),
        "Xu": (("Jia", "wood loosening", "primary"), ("Ren", "washing and circulation", "secondary")),
        **GENG_MONTH_CLIMATE_STEMS,
    },
    "Xin": {
        "Yin": (("Ji", "earth body support", "primary"), ("Ren", "washing and brightening", "secondary"), ("Geng", "metal support", "secondary")),
        "Mao": (("Ren", "washing and brightening", "primary"), ("Jia", "wood context", "secondary")),
        "Chen": (("Ren", "washing and brightening", "primary"), ("Jia", "wood context", "secondary")),
        "Si": (("Ren", "washing and brightening", "primary"), ("Gui", "moisture assistant", "secondary"), ("Jia", "wood context", "secondary")),
        "Wu": (("Ren", "washing and cooling", "primary"), ("Ji", "earth body support", "secondary"), ("Gui", "moisture assistant", "conditional")),
        "Wei": (("Ren", "washing and cooling", "primary"), ("Geng", "metal support", "secondary"), ("Jia", "wood context", "secondary")),
        "Shen": (("Ren", "washing and brightening", "primary"), ("Jia", "wood context", "secondary"), ("Wu", "earth containment", "conditional")),
        "You": (("Ren", "washing and brightening", "primary"), ("Jia", "wood context", "secondary")),
        "Xu": (("Ren", "washing and brightening", "primary"), ("Jia", "wood context", "secondary")),
        "Hai": (("Ren", "washing and brightening", "primary"), ("Bing", "warming support", "secondary")),
        "Zi": (("Bing", "warming support", "primary"), ("Wu", "earth containment", "secondary"), ("Ren", "washing and brightening", "secondary"), ("Jia", "wood context", "conditional")),
        "Chou": (("Bing", "warming support", "primary"), ("Ren", "washing and brightening", "secondary"), ("Wu", "earth containment", "secondary"), ("Ji", "earth body support", "conditional")),
    },
    "Ren": {
        "Yin": (("Geng", "source support", "primary"), ("Bing", "warming visibility", "secondary"), ("Wu", "banks and containment", "conditional")),
        "Mao": (("Wu", "banks and containment", "primary"), ("Xin", "source support", "secondary"), ("Geng", "source support", "secondary")),
        "Chen": (("Jia", "controlled expression", "primary"), ("Geng", "source support", "secondary")),
        "Si": (("Geng", "source support", "primary"), ("Xin", "source support", "secondary"), ("Ren", "same-water reinforcement", "conditional"), ("Gui", "moisture assistant", "conditional")),
        "Wu": (("Gui", "moisture balance", "primary"), ("Geng", "source support", "secondary"), ("Xin", "source support", "secondary")),
        "Wei": (("Xin", "source support", "primary"), ("Jia", "controlled expression", "secondary")),
        "Shen": (("Wu", "banks and containment", "primary"), ("Ding", "warming transformation", "secondary")),
        "You": (("Jia", "controlled expression", "primary"), ("Geng", "source support", "secondary")),
        "Xu": (("Jia", "controlled expression", "primary"), ("Bing", "warming visibility", "secondary")),
        "Hai": (("Wu", "banks and containment", "primary"), ("Bing", "warming support", "secondary"), ("Geng", "source support", "secondary")),
        "Zi": (("Wu", "banks and containment", "primary"), ("Bing", "warming support", "secondary")),
        "Chou": (("Bing", "warming support", "primary"), ("Ding", "refinement warmth", "secondary"), ("Jia", "controlled expression", "conditional")),
    },
    "Gui": {
        "Yin": (("Xin", "source support", "primary"), ("Bing", "warming visibility", "secondary")),
        "Mao": (("Geng", "source support", "primary"), ("Xin", "source support", "secondary")),
        "Chen": (("Bing", "warming visibility", "primary"), ("Xin", "source support", "secondary"), ("Jia", "controlled expression", "conditional")),
        "Si": (
            ("Xin", "source support", "primary", "Use Xin as the source that sustains Gui Water in Si month."),
            ("Geng", "fallback source support", "conditional", "Use Geng only when Xin is absent in Si month."),
        ),
        "Wu": (("Geng", "source support", "primary"), ("Xin", "source support", "secondary"), ("Ren", "water assistance", "conditional"), ("Gui", "same-water support", "conditional")),
        "Wei": (("Geng", "source support", "primary"), ("Xin", "source support", "secondary"), ("Ren", "water assistance", "conditional"), ("Gui", "same-water support", "conditional")),
        "Shen": (
            (
                "Ding",
                "controlling autumn Metal",
                "primary",
                "Use Ding to control Geng Metal in Shen month; Ding is most effective when rooted in Wu, Xu, or Wei.",
            ),
        ),
        "You": (("Xin", "source support", "primary"), ("Bing", "warming support", "secondary")),
        "Xu": (("Xin", "source support", "primary"), ("Jia", "controlled expression", "secondary"), ("Ren", "water assistance", "conditional"), ("Gui", "same-water support", "conditional")),
        "Hai": (("Geng", "source support", "primary"), ("Xin", "source support", "secondary"), ("Wu", "banks and containment", "secondary"), ("Ding", "warming support", "conditional")),
        "Zi": (("Bing", "warming support", "primary"), ("Xin", "source support", "secondary")),
        "Chou": (
            (
                "Bing",
                "thawing winter cold",
                "primary",
                "Use Bing to thaw winter cold in Chou month; rooting in Yin, Si, Wu, Wei, or Xu strengthens it.",
            ),
            (
                "Ding",
                "secondary winter Fire",
                "secondary",
                "Ding follows Bing as the second source-listed regulator for Gui Water in Chou month.",
            ),
            (
                "Geng",
                "source support under a Fire configuration",
                "conditional",
                "Use Geng only when the branches form a Fire configuration in Chou month.",
            ),
            (
                "Xin",
                "source support under a Fire configuration",
                "conditional",
                "Use Xin only when the branches form a Fire configuration in Chou month.",
            ),
        ),
    },
}

DAY_STEM_CLIMATE_PAGE_REFS: Dict[str, List[str]] = {
    "Jia": ["lu_zhiji_fate_search:p240", "lu_zhiji_bazi_advanced:p21"],
    "Yi": ["lu_zhiji_fate_search:p241", "lu_zhiji_bazi_advanced:p21"],
    "Bing": ["lu_zhiji_fate_search:pp241-242", "lu_zhiji_bazi_advanced:p21"],
    "Ding": ["lu_zhiji_fate_search:p242", "lu_zhiji_bazi_advanced:p21"],
    "Wu": ["lu_zhiji_fate_search:p243", "lu_zhiji_bazi_advanced:p21"],
    "Ji": ["lu_zhiji_fate_search:p243", "lu_zhiji_bazi_advanced:p21"],
    "Geng": ["lu_zhiji_fate_search:p244", "lu_zhiji_bazi_advanced:p21"],
    "Xin": ["lu_zhiji_fate_search:p245", "lu_zhiji_bazi_advanced:p21"],
    "Ren": ["lu_zhiji_fate_search:pp245-246", "lu_zhiji_bazi_advanced:p21"],
    "Gui": ["lu_zhiji_fate_search:p246", "lu_zhiji_bazi_advanced:p21"],
}

DAY_STEM_MONTH_CLIMATE_UNCERTAIN_ROWS = set()

DAY_STEM_CONFIGURATION_CLIMATE_STEMS: Dict[str, Tuple[Tuple[str, str, str], ...]] = {
    "Yi": (
        ("Bing", "visible growth and warmth", "primary"),
        ("Gui", "root moisture", "secondary"),
    ),
    "Bing": (
        ("Ren", "water regulation for solar fire", "primary"),
    ),
    "Ding": (
        ("Jia", "fuel and continuity", "primary"),
        ("Geng", "cutting support for fuel", "secondary"),
    ),
    "Wu": (
        ("Jia", "wood loosening for thick earth", "primary"),
        ("Bing", "warmth and activation", "secondary"),
        ("Gui", "moisture balance", "secondary"),
    ),
    "Ji": (
        ("Jia", "wood structure for field earth", "primary"),
        ("Bing", "warmth and activation", "secondary"),
        ("Gui", "moisture balance", "secondary"),
    ),
    "Geng": (
        ("Ding", "forging and refinement", "primary"),
        ("Jia", "material to cut and shape", "secondary"),
        ("Ren", "tempering and circulation", "conditional"),
    ),
    "Xin": (
        ("Ren", "washing and brightening", "primary"),
        ("Jia", "breaking excess earth", "secondary"),
    ),
    "Ren": (
        ("Wu", "banks and containment", "primary"),
        ("Geng", "source support", "secondary"),
        ("Jia", "controlled expression", "conditional"),
        ("Bing", "warming support", "conditional"),
    ),
    "Gui": (
        ("Xin", "clear source support", "primary"),
        ("Geng", "source support", "secondary"),
    ),
}

SEASON_CLIMATE_FALLBACK_RULES = {
    "Spring": [
        ("Metal", "regulating", "primary", "Spring wood can over-expand; Metal is tracked as a pruning/regulating candidate when the chart needs shape."),
        ("Fire", "circulating", "secondary", "Fire circulates Spring growth and can make Wood evidence productive rather than congested."),
    ],
    "Summer": [
        ("Water", "cooling", "primary", "Summer heat makes Water the main climate-regulating candidate when the chart needs cooling and moisture."),
        ("Metal", "supporting source", "secondary", "Metal is tracked as a source that can support Water when cooling is needed but Water is scarce."),
    ],
    "Autumn": [
        ("Fire", "warming", "primary", "Autumn metal can be cold and sharp; Fire is tracked as warming/refining climate support."),
        ("Water", "moistening", "secondary", "Water can moisten dry Autumn charts when dryness appears in the element balance."),
    ],
    "Winter": [
        ("Fire", "warming", "primary", "Winter cold makes Fire the main warming/regulating candidate before the chart is treated as complete."),
        ("Wood", "circulating", "secondary", "Wood is tracked as a circulation candidate that can move Winter Water toward expression."),
    ],
}


def _stem_key_element(stem_key: str) -> str:
    idx = STEM_INDEX.get(str(stem_key or ""))
    return str(STEMS[idx]["element"]) if idx is not None else ""


def _month_branch_from_context(
    analysis: Dict[str, Any],
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
) -> Optional[str]:
    model = analysis.get("strength_model") if isinstance(analysis.get("strength_model"), dict) else {}
    season_model = model.get("season") if isinstance(model.get("season"), dict) else {}
    month_branch = season_model.get("month_branch")
    if month_branch:
        return str(month_branch)
    month_pillar = (pillars or {}).get("month") if isinstance(pillars, dict) else None
    if isinstance(month_pillar, dict) and month_pillar.get("branch"):
        return str(month_pillar["branch"])
    return None


def _source_climate_targets(
    day_stem_key: str,
    month_branch: Optional[str],
) -> Tuple[str, Tuple[Tuple[str, str, str], ...], List[str]]:
    stem_rows = DAY_STEM_MONTH_CLIMATE_STEMS.get(day_stem_key) or {}
    if month_branch in stem_rows:
        return (
            "day_stem_month_rule",
            stem_rows[str(month_branch)],
            DAY_STEM_CLIMATE_PAGE_REFS.get(day_stem_key, ["lu_zhiji_fate_search:pp240-247"]),
        )
    if day_stem_key in DAY_STEM_CONFIGURATION_CLIMATE_STEMS:
        return (
            "day_stem_configuration_rule",
            DAY_STEM_CONFIGURATION_CLIMATE_STEMS[day_stem_key],
            ["lu_zhiji_fate_search:pp251-255"],
        )
    return "season_fallback", (), []


def _can_override_from_climate_function(function: str) -> bool:
    text = str(function or "").lower()
    return any(marker in text for marker in CLIMATE_OVERRIDE_FUNCTION_MARKERS)


def _climate_row_integrity(
    *,
    element: str,
    count: int,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    relationships: Optional[Dict[str, Any]],
    timing: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    natal_sources = _natal_sources_for_element(pillars or {}, element)
    timing_sources = _timing_sources_for_element(timing or {}, element)
    impacts = _element_impacts(element, relationships or {})
    state = _integrity_summary(
        element=element,
        role_group="favorable",
        natal_sources=natal_sources,
        timing_sources=timing_sources,
        impacts=impacts,
    )
    availability = str(state.get("availability") or "")
    if availability == "missing" and count > 0:
        availability = "present_natal"
        state["summary"] = f"{element} is counted in the chart. {state.get('summary') or ''}".strip()
    elif availability == "missing":
        availability = "absent"
    return {
        **state,
        "availability": availability,
        "natal_count": count,
        "natal_presence_count": count,
        "presence_measure": "unweighted_presence_count",
        "qi_strength_status": "not_evaluated",
        "natal_sources": natal_sources[:5],
        "timing_sources": timing_sources[:5],
        "event_impacts": impacts,
    }


def _climate_row_taboos(function: str, priority: str) -> List[str]:
    text = str(function or "").lower()
    taboos = [
        "Do not finalize this regulating stem if its element is absent, pressured, or unsupported.",
    ]
    if priority == "conditional":
        taboos.append("Do not promote a conditional regulating stem unless the stated condition is active.")
    if any(marker in text for marker in ("cooling", "moisture", "water regulation", "root moisture")):
        taboos.append("Do not add cooling or moisture when cold-water pressure is already the active disease.")
    elif any(marker in text for marker in ("warming", "warmth", "fire", "visible warmth")):
        taboos.append("Do not add warming when heat or Fire excess is already the active disease.")
    elif any(marker in text for marker in ("earth containment", "banks", "containment")):
        taboos.append("Do not use containment as a first medicine when it buries the needed regulator.")
    else:
        taboos.append("Do not treat this as generic element balancing; it belongs to the day-stem/month tiao hou row.")
    return taboos


def _source_climate_rows(
    *,
    day_stem_key: str,
    month_branch: Optional[str],
    counts: Dict[str, int],
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    relationships: Optional[Dict[str, Any]],
    timing: Optional[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    source_status, targets, page_refs = _source_climate_targets(day_stem_key, month_branch)
    rows: List[Dict[str, Any]] = []
    for target in targets:
        stem_key, function, priority = target[:3]
        condition = target[3] if len(target) > 3 else f"{day_stem_key} day in {month_branch or 'recorded'} month regulating-stem row."
        element = _stem_key_element(stem_key)
        count = int(counts.get(element) or 0)
        needs_page_image_check = (day_stem_key, month_branch) in DAY_STEM_MONTH_CLIMATE_UNCERTAIN_ROWS
        integrity = _climate_row_integrity(
            element=element,
            count=count,
            pillars=pillars,
            relationships=relationships,
            timing=timing,
        )
        rows.append({
            "stem": stem_key,
            "element": element,
            "function": function,
            "priority": priority,
            "condition": condition,
            "taboos": _climate_row_taboos(function, priority),
            "count": count,
            "presence_count": count,
            "presence_measure": "unweighted_presence_count",
            "qi_strength_status": "not_evaluated",
            "availability": integrity.get("availability"),
            "pressure": integrity.get("pressure"),
            "integrity": integrity,
            "source_table_key": f"{day_stem_key}:{month_branch}:{stem_key}:{priority}",
            "table_row_ref": {
                "day_stem": day_stem_key,
                "month_branch": month_branch,
                "regulating_stem": stem_key,
                "priority": priority,
            },
            "override_candidate": (
                priority == "primary"
                and source_status in CLIMATE_SOURCE_READY_STATUSES
                and _can_override_from_climate_function(function)
                and not needs_page_image_check
            ),
            "reason": (
                f"{day_stem_key} Day Master in {month_branch or 'the recorded'} month uses {stem_key} "
                f"as a {priority} regulating stem for {function}."
            ),
            "source_rule_status": source_status,
            "source_page_refs": list(page_refs),
            "needs_page_image_check": needs_page_image_check,
            "source_confidence": (
                confidence_tags("local_source", "computed_rule", "needs_validation")
                if needs_page_image_check
                else confidence_tags("local_source", "computed_rule")
            ),
        })
    return source_status, rows, page_refs


def _season_fallback_climate_rows(season: str, counts: Dict[str, int]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for element, function, priority, reason in SEASON_CLIMATE_FALLBACK_RULES.get(season, []):
        count = int(counts.get(element) or 0)
        availability = "present_natal" if count > 0 else "absent"
        rows.append({
            "stem": None,
            "element": element,
            "function": function,
            "priority": priority,
            "count": count,
            "presence_count": count,
            "presence_measure": "unweighted_presence_count",
            "qi_strength_status": "not_evaluated",
            "availability": availability,
            "pressure": "clear",
            "override_candidate": False,
            "reason": reason,
            "source_rule_status": "season_fallback",
            "source_page_refs": ["lu_zhiji_fate_search:p249"],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        })
    return rows


def _climate_adjustment(
    day_stem_index: int,
    analysis: Dict[str, Any],
    counts: Dict[str, int],
    *,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]] = None,
    relationships: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    model = analysis.get("strength_model") if isinstance(analysis.get("strength_model"), dict) else {}
    season_model = model.get("season") if isinstance(model.get("season"), dict) else {}
    season = str(season_model.get("season") or "Unknown")
    month_branch = _month_branch_from_context(analysis, pillars)
    day_stem_key = str(STEMS[int(day_stem_index) % 10]["key"])
    source_status, rows, page_refs = _source_climate_rows(
        day_stem_key=day_stem_key,
        month_branch=month_branch,
        counts=counts,
        pillars=pillars,
        relationships=relationships,
        timing=timing,
    )
    method = "day_stem_month_climate_regulating_v1"
    source_confidence = confidence_tags("local_source", "computed_rule")
    if not rows:
        rows = _season_fallback_climate_rows(season, counts)
        method = "season_climate_regulating_v1"
        source_status = "season_fallback"
        page_refs = ["lu_zhiji_fate_search:p249"] if rows else []
        source_confidence = confidence_tags("local_source", "provisional_model", "needs_validation")
    elif source_status == "day_stem_configuration_rule":
        method = "day_stem_configuration_climate_regulating_v1"
    return {
        "status": "source_based_preview" if rows else "not_applicable",
        "method": method,
        "source_table_status": source_status,
        "day_stem": day_stem_key,
        "season": season,
        "month_branch": month_branch,
        "decision_path": YONG_SHEN_RULE_FAMILIES["climate_override"] if rows else None,
        "override_status": "candidate" if any(row.get("override_candidate") for row in rows) else "watch",
        "recommendations": rows,
        "source_page_refs": page_refs,
        "notes": [
            "Climate/regulating stems are evaluated separately from ordinary strength-balancing favorable elements.",
            "Source-table rows can override ordinary balancing only when the regulating element is present or timing-supported and no blocker is active.",
            "Unweighted presence can establish availability, but it does not establish that the regulating element has usable qi strength.",
            "The source supplies regulating stems and conditions; app priority/function labels are a provisional operational interpretation.",
        ],
        "source_basis": [LOCAL_SOURCE_BASIS[7], CHINESE_CLIMATE_SOURCE_BASIS],
        "source_confidence": source_confidence,
    }


def _source_damage_presence_watch(row: Dict[str, Any], counts: Dict[str, int], day_element: str) -> Optional[Dict[str, Any]]:
    role = str(row.get("role") or "")
    if str(row.get("priority") or "") != "primary":
        return None
    output_element = PRODUCES.get(day_element, "")
    wealth_element = CONTROLS.get(day_element, "")
    resource_element = _inverse_lookup(PRODUCES, day_element) or ""
    damage_family = {
        "Wealth": ("wealth_damaged_by_companion", "Companion", day_element),
        "Influence": ("officer_damaged_by_output", "Output", output_element),
        "Resource": ("resource_damaged_by_wealth", "Wealth", wealth_element),
        "Output": ("output_damaged_by_resource", "Resource", resource_element),
    }.get(role)
    if not damage_family:
        return None
    damage_type, damaging_role, damaging_element = damage_family
    presence_count = int(counts.get(damaging_element) or 0)
    if presence_count <= 0:
        return None
    return {
        "watch_type": damage_type,
        "damaging_role": damaging_role,
        "damaging_element": damaging_element,
        "damaging_presence_count": presence_count,
        "presence_measure": "unweighted_presence_count",
        "status": "presence_only_unclassified",
        "qi_strength_status": "not_evaluated",
        "reason": (
            f"{damaging_role} is present, so the traditional {damage_type.replace('_', ' ')} family is worth checking. "
            "Presence alone does not establish effective damage."
        ),
    }


def _cycle_bridge_element(damaging_element: str, target_element: str) -> Optional[str]:
    first_step = PRODUCES.get(damaging_element)
    if first_step and PRODUCES.get(first_step) == target_element:
        return first_step
    return None


def _damage_rescue_candidates(
    row: Dict[str, Any],
    source_pattern: Optional[Dict[str, Any]],
    counts: Dict[str, int],
    day_element: str,
) -> List[Dict[str, Any]]:
    element = str(row.get("element") or "")
    role = str(row.get("role") or "")
    rows: List[Dict[str, Any]] = []
    role_to_elements = _element_role_map(day_element)
    role_rescue = {
        "Wealth": [("Influence", "Officer/Killing restrains Companion pressure that contests Wealth.")],
        "Influence": [("Resource", "Resource transforms Officer/Killing pressure and restrains Output damage.")],
        "Resource": [("Companion", "Companion helps bear Wealth pressure against Resource.")],
        "Output": [("Wealth", "Wealth can draw Output into function and check excessive Resource/Owl pressure.")],
    }
    for rescue_role, reason in role_rescue.get(role, []):
        rescue_element = role_to_elements.get(rescue_role)
        if rescue_element:
            rows.append({
                "role": rescue_role,
                "element": rescue_element,
                "count": int(counts.get(rescue_element) or 0),
                "presence_count": int(counts.get(rescue_element) or 0),
                "presence_measure": "unweighted_presence_count",
                "qi_strength_status": "not_evaluated",
                "path": "rescue_role",
                "reason": reason,
            })
    if source_pattern:
        bridge = _cycle_bridge_element(str(source_pattern.get("damaging_element") or ""), element)
        if bridge:
            rows.append({
                "role": "Tong Guan",
                "element": bridge,
                "count": int(counts.get(bridge) or 0),
                "presence_count": int(counts.get(bridge) or 0),
                "presence_measure": "unweighted_presence_count",
                "qi_strength_status": "not_evaluated",
                "path": "tong_guan_bridge",
                "reason": f"{bridge} bridges {source_pattern.get('damaging_element')} pressure into {element} function through the generating cycle.",
            })
    return rows


def _damage_channels(
    *,
    source_pattern: Optional[Dict[str, Any]],
    availability: str,
    pressure: str,
    integrity: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if source_pattern:
        rows.append({
            "channel": "sun_yong_source_pattern",
            "status": "damaged",
            "detail": source_pattern.get("damage_type"),
        })
    if pressure == "pressured":
        rows.append({
            "channel": "contact_pressure",
            "status": "damaged",
            "detail": f"{len(integrity.get('event_impacts') or [])} challenging/supportive contact(s) touch the element.",
        })
    if availability in {"missing", "absent"}:
        rows.append({
            "channel": "placement_not_found",
            "status": "presence_missing",
            "detail": "No checked natal or timing placement was found; this is not a qi-strength finding.",
        })
    if availability == "timing_supported":
        rows.append({"channel": "timing_only", "status": "timing_assisted", "detail": "The element appears in timing rather than checked natal placements; usable qi is not established."})
    return rows


def _functional_state(status: str, source_pattern: Optional[Dict[str, Any]], rescue_candidates: List[Dict[str, Any]]) -> str:
    if status == "damaged" and source_pattern and rescue_candidates:
        return "damaged_rescue_qi_unverified"
    if status == "damaged":
        return "damaged_needs_rescue"
    if status == "timing_assisted":
        return "timing_evidence_qi_unverified"
    return "qi_strength_unresolved"


def _damage_status(row: Dict[str, Any], counts: Dict[str, int], day_element: str) -> Dict[str, Any]:
    integrity = row.get("integrity") if isinstance(row.get("integrity"), dict) else {}
    element = str(row.get("element") or "")
    availability = str(integrity.get("availability") or "unknown")
    pressure = str(integrity.get("pressure") or "clear")
    presence_watch = _source_damage_presence_watch(row, counts, day_element)
    source_pattern = None
    if pressure == "pressured":
        status = "damaged"
        severity = "high"
        reason = f"{element} is favorable but touched by a challenging relationship code."
    elif availability == "missing":
        status = "presence_missing"
        severity = "watch"
        reason = f"{element} was not found in checked placements; absence from the inventory does not establish weak or unusable qi."
    elif availability == "timing_supported":
        status = "timing_assisted"
        severity = "watch"
        reason = f"{element} appears in current timing but not checked natal placements; this does not establish rooted or usable qi."
    elif pressure == "supported":
        status = "contact_supported"
        severity = "watch"
        reason = f"{element} is touched by a supportive relationship code, but effective qi remains unevaluated."
    else:
        status = "presence_only"
        severity = "watch"
        reason = f"{element} appears in checked placements, but presence does not establish effective or usable qi."
    rescue_candidates = _damage_rescue_candidates(row, source_pattern, counts, day_element)
    damage_channels = _damage_channels(
        source_pattern=source_pattern,
        availability=availability,
        pressure=pressure,
        integrity=integrity,
    )
    payload = {
        "element": element,
        "role": row.get("role"),
        "priority": row.get("priority"),
        "availability": availability,
        "pressure": pressure,
        "status": status,
        "severity": severity,
        "reason": reason,
        "event_impacts": integrity.get("event_impacts") or [],
        "damage_channels": damage_channels,
        "rescue_candidates": rescue_candidates,
        "functional_state": _functional_state(status, source_pattern, rescue_candidates),
        "qi_strength_status": "not_evaluated",
        "decision_authority": "none" if status != "damaged" else "contact_pressure_only",
        "two_against_one": any(
            int(channel.get("status") == "damaged") for channel in damage_channels
        ) and len([channel for channel in damage_channels if channel.get("status") == "damaged"]) >= 2,
    }
    payload["source_pattern"] = False
    if presence_watch:
        payload["presence_damage_watch"] = presence_watch
    if status == "damaged":
        payload["damage_type"] = "relationship_contact_pressure"
    return payload


def _damage_assessment(payload: Dict[str, Any], counts: Optional[Dict[str, int]] = None, day_element: str = "") -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    counts = counts or {}
    rows = [
        _damage_status(row, counts, day_element)
        for row in payload.get("favorable") or []
        if isinstance(row, dict) and row.get("element")
    ]
    summary = {
        "checked": len(rows),
        "damaged": sum(1 for row in rows if row.get("status") == "damaged"),
        "source_pattern_damaged": sum(1 for row in rows if row.get("status") == "damaged" and row.get("source_pattern") is True),
        "presence_only_watches": sum(1 for row in rows if row.get("presence_damage_watch")),
        "presence_missing": sum(1 for row in rows if row.get("status") == "presence_missing"),
        "presence_only": sum(1 for row in rows if row.get("status") == "presence_only"),
        "absent": sum(1 for row in rows if row.get("status") == "presence_missing"),
        "timing_assisted": sum(1 for row in rows if row.get("status") == "timing_assisted"),
        "supported": sum(1 for row in rows if row.get("status") == "contact_supported"),
        "available": sum(1 for row in rows if row.get("status") == "presence_only"),
    }
    return rows, summary


def _integrity_for_element(payload: Dict[str, Any], element: str) -> Dict[str, Any]:
    for row in payload.get("element_integrity") or []:
        if isinstance(row, dict) and row.get("element") == element:
            return row
    return {}


def _tong_guan_analysis(
    payload: Dict[str, Any],
    damage_rows: List[Dict[str, Any]],
    counts: Dict[str, int],
    day_element: str,
) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for damaged in damage_rows:
        if not isinstance(damaged, dict) or damaged.get("source_pattern") is not True:
            continue
        target = str(damaged.get("element") or "")
        damaging = str(damaged.get("damaging_element") or "")
        bridge = _cycle_bridge_element(damaging, target)
        if not bridge:
            continue
        bridge_count = int(counts.get(bridge) or 0)
        integrity = _integrity_for_element(payload, bridge)
        availability = str(integrity.get("availability") or ("present_natal" if bridge_count else "missing"))
        pressure = str(integrity.get("pressure") or "clear")
        candidates.append({
            "element": bridge,
            "role": "Tong Guan",
            "priority": "bridge",
            "target_element": target,
            "damaging_element": damaging,
            "count": bridge_count,
            "presence_count": bridge_count,
            "presence_measure": "unweighted_presence_count",
            "availability": availability,
            "pressure": pressure,
            "integrity": integrity,
            "source_damage_type": damaged.get("damage_type"),
            "decision_candidate": False,
            "qi_strength_status": "not_evaluated",
            "reason": (
                f"{bridge} is the generating-cycle bridge from {damaging} pressure into {target}. "
                "Raw presence cannot establish that the bridge has usable qi, so this remains evidence-only."
            ),
        })
    primary = next((row for row in candidates if row.get("decision_candidate")), None) or (candidates[0] if candidates else None)
    return {
        "status": "active" if candidates else "not_applicable",
        "method": "tong_guan_bridge_useful_path_v1",
        "primary_candidate": primary,
        "candidates": candidates,
        "notes": [
            "Tong Guan is evaluated as a bridge path when a source damage pattern creates a controlling-cycle conflict.",
            "A counted or visible bridge remains evidence-only until its seasonal/rooted qi is evaluated.",
        ],
        "source_page_refs": ["lu_zhiji_fate_search:pp301-303", "lu_zhiji_fate_search:p317"],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


STRUCTURE_BY_GOD = {
    "Direct Officer": ("direct_officer", "Direct Officer Structure", "shun_yong"),
    "Seven Killings": ("seven_killings", "Seven Killings Structure", "ni_yong"),
    "Direct Wealth": ("direct_wealth", "Direct Wealth Structure", "shun_yong"),
    "Indirect Wealth": ("indirect_wealth", "Indirect Wealth Structure", "shun_yong"),
    "Direct Resource": ("direct_resource", "Direct Resource Structure", "shun_yong"),
    "Indirect Resource": ("indirect_resource", "Indirect Resource Structure", "ni_yong"),
    "Eating God": ("eating_god", "Eating God Structure", "shun_yong"),
    "Hurting Officer": ("hurting_officer", "Hurting Officer Structure", "ni_yong"),
    "Rob Wealth": ("rob_wealth", "Rob Wealth Structure", "ni_yong"),
    "Friend": ("friend", "Companion Structure", "neutral"),
}

DOMINANT_STRUCTURE_BY_ELEMENT = {
    "Wood": {"type": "qu_zhi", "role": "qu_zhi", "frame": {"Hai", "Mao", "Wei", "Yin"}},
    "Fire": {"type": "yan_shang", "role": "yan_shang", "frame": {"Yin", "Wu", "Xu", "Si"}},
    "Earth": {"type": "jia_se", "role": "jia_se", "frame": {"Chen", "Xu", "Chou", "Wei"}},
    "Metal": {"type": "cong_ge", "role": "cong_ge", "frame": {"Si", "You", "Chou", "Shen"}},
    "Water": {"type": "run_xia", "role": "run_xia", "frame": {"Shen", "Zi", "Chen", "Hai"}},
}


def _pillar_hidden_stems(pillar: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hidden = pillar.get("hidden_stems") if isinstance(pillar, dict) else []
    return [row for row in hidden if isinstance(row, dict)] if isinstance(hidden, list) else []


def _hidden_stem_key(row: Dict[str, Any]) -> str:
    return str(row.get("key") or row.get("stem") or "")


def _hidden_stem_element(row: Dict[str, Any]) -> str:
    if row.get("element"):
        return str(row["element"])
    key = _hidden_stem_key(row)
    return _stem_key_element(key) if key else ""


def _chart_stem_records(pillars: Optional[Dict[str, Optional[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not isinstance(pillars, dict):
        return records
    for pillar_name in ("year", "month", "day", "hour"):
        pillar = pillars.get(pillar_name)
        if not isinstance(pillar, dict):
            continue
        if pillar.get("stem"):
            records.append({
                "pillar": pillar_name,
                "layer": "visible",
                "stem": str(pillar.get("stem")),
                "element": str(pillar.get("stem_element") or _stem_key_element(str(pillar.get("stem")))),
            })
        for index, hidden in enumerate(_pillar_hidden_stems(pillar), start=1):
            key = _hidden_stem_key(hidden)
            records.append({
                "pillar": pillar_name,
                "layer": "hidden",
                "stem": key,
                "element": _hidden_stem_element(hidden),
                "rank": hidden.get("rank") or index,
            })
    return records


def _ten_god_payload_for_stem(day_stem_index: int, stem_key: str) -> Dict[str, Any]:
    stem_index = STEM_INDEX.get(str(stem_key or ""))
    if stem_index is None:
        return {"factor": "Unknown", "god": "Unknown"}
    return ten_god(day_stem_index, stem_index)


def _chart_ten_god_counts(day_stem_index: int, pillars: Optional[Dict[str, Optional[Dict[str, Any]]]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for record in _chart_stem_records(pillars):
        if record.get("pillar") == "day" and record.get("layer") == "visible":
            # The Day Master is the reference point, not another Companion placement.
            continue
        stem_key = str(record.get("stem") or "")
        if not stem_key:
            continue
        payload = _ten_god_payload_for_stem(day_stem_index, stem_key)
        factor = str(payload.get("factor") or "")
        god = str(payload.get("god") or "")
        if factor and factor != "Unknown":
            counts[factor] += 1
        if god and god != "Unknown":
            counts[god] += 1
    return dict(counts)


def _structure_presence_watch(
    *,
    watch_type: str,
    watch_family: str,
    factor: str,
    presence_count: int,
    reason: str,
) -> Dict[str, Any]:
    return {
        "type": watch_type,
        "watch_family": watch_family,
        "factor": factor,
        "presence_count": int(presence_count),
        "presence_measure": "unweighted_ten_god_mention_count",
        "status": "presence_only_unclassified",
        "qi_strength_status": "not_evaluated",
        "decision_candidate": False,
        "source_pattern": False,
        "reason": (
            f"{reason} The counted appearance opens a placement-and-qi review only; "
            "it does not establish effective damage, mixing, or rescue."
        ),
    }


def _structure_damage_presence_watches(structure_key: str, ten_god_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    checks = []
    if structure_key in {"direct_officer", "seven_killings"}:
        checks.append((
            "officer_damaged_by_output",
            "Output",
            int(ten_god_counts.get("Output") or ten_god_counts.get("Hurting Officer") or 0),
            "Officer/Killing can be harmed when effective Output, especially Hurting Officer, attacks the authority star.",
        ))
    if structure_key in {"direct_wealth", "indirect_wealth"}:
        checks.append((
            "wealth_damaged_by_companion",
            "Companion",
            int(ten_god_counts.get("Companion") or 0),
            "Wealth can be harmed when effective Companion/Rob Wealth contests it.",
        ))
    if structure_key in {"direct_resource", "indirect_resource"}:
        checks.append((
            "resource_damaged_by_wealth",
            "Wealth",
            int(ten_god_counts.get("Wealth") or 0),
            "Resource can be harmed when effective Wealth controls it.",
        ))
    if structure_key == "eating_god":
        checks.append((
            "output_damaged_by_resource",
            "Resource",
            int(ten_god_counts.get("Resource") or 0),
            "Eating God can be harmed when effective Resource/Owl suppresses output.",
        ))
    return [
        _structure_presence_watch(
            watch_type=watch_type,
            watch_family="damage",
            factor=factor,
            presence_count=count,
            reason=reason,
        )
        for watch_type, factor, count, reason in checks
        if count > 0
    ]


STRUCTURE_RESCUE_MAP = {
    "direct_officer": ("Resource", "Resource can transform authority pressure and restrain Hurting Officer damage."),
    "seven_killings": ("Resource", "Resource can transform Seven Killings into usable authority when the Day Master can receive it."),
    "direct_wealth": ("Influence", "Influence/Officer can restrain Companion pressure that contests Wealth."),
    "indirect_wealth": ("Influence", "Influence/Officer can restrain Companion pressure that contests Wealth."),
    "direct_resource": ("Companion", "Companion helps the Day Master bear Wealth pressure against Resource."),
    "indirect_resource": ("Companion", "Companion helps the Day Master bear Wealth pressure against Resource/Owl."),
    "eating_god": ("Wealth", "Wealth can draw Output into function and check excess Resource/Owl."),
    "hurting_officer": ("Wealth", "Wealth can draw Hurting Officer output into concrete function."),
}


def _structure_rescue_presence_watches(structure_key: str, ten_god_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    rescue = STRUCTURE_RESCUE_MAP.get(structure_key)
    if not rescue:
        return []
    factor, reason = rescue
    count = int(ten_god_counts.get(factor) or 0)
    if count <= 0:
        return []
    return [_structure_presence_watch(
        watch_type="structure_rescue",
        watch_family="rescue",
        factor=factor,
        presence_count=count,
        reason=reason,
    )]


def _structure_mixed_presence_watches(structure_key: str, ten_god_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    checks = []
    if structure_key == "direct_officer" and ten_god_counts.get("Seven Killings", 0):
        checks.append(("officer_killing_mixed", "Seven Killings", int(ten_god_counts["Seven Killings"]), "Direct Officer may be mixed when effective Seven Killings also participates."))
    if structure_key == "seven_killings" and ten_god_counts.get("Direct Officer", 0):
        checks.append(("officer_killing_mixed", "Direct Officer", int(ten_god_counts["Direct Officer"]), "Seven Killings may be mixed when effective Direct Officer also participates."))
    if structure_key == "eating_god" and ten_god_counts.get("Hurting Officer", 0):
        checks.append(("output_mixed", "Hurting Officer", int(ten_god_counts["Hurting Officer"]), "Eating God and Hurting Officer both appear; purity depends on placement, qi, and rescue."))
    return [
        _structure_presence_watch(
            watch_type=watch_type,
            watch_family="mixing",
            factor=factor,
            presence_count=count,
            reason=reason,
        )
        for watch_type, factor, count, reason in checks
    ]


def _structure_assessment(
    structure_key: str,
    damage_patterns: List[Dict[str, Any]],
    rescue_patterns: List[Dict[str, Any]],
    mixed_patterns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if structure_key == "unclassified":
        status = "unclassified"
    elif damage_patterns and rescue_patterns:
        status = "damaged_rescued"
    elif damage_patterns:
        status = "damaged_needs_rescue"
    elif mixed_patterns:
        status = "mixed_needs_clearing"
    else:
        status = "usable"
    return {
        "status": status,
        "ordinary_rules_apply": status in {"usable", "damaged_rescued"},
        "success_failure": (
            "success_with_rescue" if status == "damaged_rescued"
            else "failure_or_lower_grade" if status == "damaged_needs_rescue"
            else "mixed_structure" if status == "mixed_needs_clearing"
            else status
        ),
        "qing_zhuo": "clear" if status == "usable" else ("rescued" if status == "damaged_rescued" else "mixed_or_turbid"),
    }


def _month_command_structure_selection(
    day_stem_index: int,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
) -> Dict[str, Any]:
    month = (pillars or {}).get("month") if isinstance(pillars, dict) else None
    if not isinstance(month, dict):
        return {
            "status": "unavailable",
            "method": "month_command_structure_selection_v1",
            "primary_structure": None,
            "reason": "Month pillar is required before structure selection.",
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        }
    hidden = _pillar_hidden_stems(month)
    command_stem = _hidden_stem_key(hidden[0]) if hidden else str(month.get("stem") or "")
    if not command_stem:
        return {
            "status": "unavailable",
            "method": "month_command_structure_selection_v1",
            "primary_structure": None,
            "reason": "Month command hidden stem is unavailable.",
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        }
    god_payload = _ten_god_payload_for_stem(day_stem_index, command_stem)
    god = str(god_payload.get("god") or "Unknown")
    factor = str(god_payload.get("factor") or "Unknown")
    key, label, use_mode = STRUCTURE_BY_GOD.get(god, ("unclassified", f"{god} Structure", "neutral"))
    counts = _chart_ten_god_counts(day_stem_index, pillars)
    damage_presence_watches = _structure_damage_presence_watches(key, counts)
    rescue_presence_watches = _structure_rescue_presence_watches(key, counts)
    mixed_presence_watches = _structure_mixed_presence_watches(key, counts)
    damage_patterns: List[Dict[str, Any]] = []
    rescue_patterns: List[Dict[str, Any]] = []
    mixed_patterns: List[Dict[str, Any]] = []
    assessment = _structure_assessment(key, damage_patterns, rescue_patterns, mixed_patterns)
    status = assessment["status"]
    return {
        "status": "source_based_preview",
        "method": "month_command_structure_selection_v3",
        "primary_structure": {
            "key": key,
            "label": label,
            "month_branch": month.get("branch"),
            "command_stem": command_stem,
            "factor": factor,
            "god": god,
            "use_mode": use_mode,
            "status": status,
            "damage_patterns": damage_patterns,
            "rescue_patterns": rescue_patterns,
            "mixed_patterns": mixed_patterns,
            "damage_presence_watches": damage_presence_watches,
            "rescue_presence_watches": rescue_presence_watches,
            "mixed_presence_watches": mixed_presence_watches,
            "success_failure": assessment["success_failure"],
            "qing_zhuo": assessment["qing_zhuo"],
            "xiang_shen_candidates": rescue_patterns,
            "xiang_shen_presence_watches": rescue_presence_watches,
            "ji_shen_patterns": damage_patterns + mixed_patterns,
            "ji_shen_presence_watches": damage_presence_watches + mixed_presence_watches,
            "ten_god_counts": counts,
            "ten_god_presence_counts": counts,
            "ten_god_count_semantics": {
                "measure": "unweighted_ten_god_mention_count",
                "is_qi_strength": False,
                "used_for": ["presence_only_review"],
                "not_used_for": ["damage_classification", "rescue_classification", "mixing_classification"],
            },
            "ordinary_rules_apply": assessment["ordinary_rules_apply"],
        },
        "notes": [
            "Month-command structure is selected before ordinary strong/weak balancing is treated as final.",
            "Ten God mention counts open damage, rescue, and mixing reviews but cannot classify their effective qi.",
            "Only evaluated structure evidence may populate damage, rescue, or mixing patterns and alter the structure assessment.",
        ],
        "source_page_refs": ["lu_zhiji_fate_search:pp123-124", "lu_zhiji_advanced:p24"],
        "source_confidence": confidence_tags("local_source", "computed_rule"),
    }


def _branch_keys(pillars: Optional[Dict[str, Optional[Dict[str, Any]]]]) -> List[str]:
    if not isinstance(pillars, dict):
        return []
    return [
        str(pillar.get("branch"))
        for pillar in pillars.values()
        if isinstance(pillar, dict) and pillar.get("branch")
    ]


def _month_supports_element(pillars: Optional[Dict[str, Optional[Dict[str, Any]]]], element: str) -> bool:
    month = (pillars or {}).get("month") if isinstance(pillars, dict) else None
    if not isinstance(month, dict):
        return False
    if str(month.get("branch_element") or "") == element:
        return True
    return any(_hidden_stem_element(row) == element for row in _pillar_hidden_stems(month))


def _day_master_root_present(
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    day_stem_key: str,
    day_element: str,
) -> bool:
    if not isinstance(pillars, dict):
        return False
    for pillar_name in ("day", "hour"):
        pillar = pillars.get(pillar_name)
        if not isinstance(pillar, dict):
            continue
        if str(pillar.get("branch_element") or "") == day_element:
            return True
        for hidden in _pillar_hidden_stems(pillar):
            if _hidden_stem_key(hidden) == day_stem_key or _hidden_stem_element(hidden) == day_element:
                return True
    return False


def _dominant_special_candidate(
    *,
    dominant_element: str,
    day_element: str,
    strength: str,
    ratio: float,
    counts: Dict[str, int],
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
) -> Optional[Dict[str, Any]]:
    if ratio < 0.5:
        return None
    same_element_frame = dominant_element == day_element
    if same_element_frame and strength != "strong":
        return None
    meta = DOMINANT_STRUCTURE_BY_ELEMENT.get(dominant_element, {})
    frame = set(meta.get("frame") or set())
    branch_count = len(frame & set(_branch_keys(pillars)))
    month_support = _month_supports_element(pillars, dominant_element)
    controller = _inverse_lookup(CONTROLS, dominant_element) or ""
    controller_count = int(counts.get(controller) or 0) if controller else 0
    if same_element_frame and (
        ratio < 0.7
        or not month_support
        or branch_count < 2
        or controller_count != 0
    ):
        return None
    structural_conditions_met = (
        ratio >= 0.7
        and controller_count == 0
        and (
            (month_support and branch_count >= 2)
            if same_element_frame
            else (month_support or branch_count >= 2)
        )
    )
    return {
        "type": meta.get("type") or "dominant_element",
        "family": "dominant_element",
        "role": meta.get("role") or "dominant",
        "element": dominant_element,
        "ratio": round(ratio, 3),
        "presence_ratio": round(ratio, 3),
        "ratio_measure": "unweighted_presence_count",
        "classification": "suspected_presence_only",
        "qi_strength_status": "not_evaluated",
        "decision_authority": "none",
        "review_only": True,
        "structural_conditions_met": structural_conditions_met,
        "month_support": month_support,
        "branch_frame_hits": branch_count,
        "opposing_controller_count": controller_count,
        "opposing_controller_presence_count": controller_count,
        "priority": 3,
        "reason": (
            f"{dominant_element} is the most-mentioned element in the unweighted inventory. "
            "Month/frame evidence can trigger review, but presence counts cannot classify a dominant structure."
        ),
    }


def _follow_role(day_element: str, dominant_element: str) -> str:
    if CONTROLS.get(day_element) == dominant_element:
        return "cong_cai"
    if CONTROLS.get(dominant_element) == day_element:
        return "cong_sha"
    if PRODUCES.get(day_element) == dominant_element:
        return "cong_er"
    if PRODUCES.get(dominant_element) == day_element:
        return "cong_qiang"
    return "cong_shi"


def _follow_special_candidate(
    *,
    dominant_element: str,
    day_element: str,
    day_stem_key: str,
    strength: str,
    ratio: float,
    day_count: int,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
) -> Optional[Dict[str, Any]]:
    if strength not in {"weak", "very weak", "extremely weak"} or dominant_element == day_element or ratio < 0.5:
        return None
    root_present = _day_master_root_present(pillars, day_stem_key, day_element)
    blockers = ["day_master_root_present"] if root_present else []
    month_support = _month_supports_element(pillars, dominant_element)
    structural_conditions_met = ratio >= 0.62 and not blockers and month_support
    classification = "false_follow" if blockers else "suspected_presence_only"
    return {
        "type": "follow_structure",
        "family": "follow_structure",
        "role": _follow_role(day_element, dominant_element),
        "element": dominant_element,
        "ratio": round(ratio, 3),
        "presence_ratio": round(ratio, 3),
        "ratio_measure": "unweighted_presence_count",
        "classification": classification,
        "qi_strength_status": "not_evaluated",
        "decision_authority": "none" if classification == "suspected_presence_only" else "structural_blocker_only",
        "review_only": classification == "suspected_presence_only",
        "structural_conditions_met": structural_conditions_met,
        "month_support": month_support,
        "day_element_presence_count": day_count,
        "false_follow_blockers": blockers,
        "priority": 1,
        "reason": (
            "Follow structures require a rootless weak Day Master and an overwhelming chart force. "
            "The root test is structural, but the unweighted presence ratio cannot establish the dominant force's qi."
        ),
    }


def _stem_transformation_candidates(
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    day_stem_key: str,
    day_element: str,
) -> List[Dict[str, Any]]:
    if not isinstance(pillars, dict):
        return []
    stems = [
        str(pillar.get("stem") or "")
        for pillar in pillars.values()
        if isinstance(pillar, dict) and pillar.get("stem")
    ]
    root_present = _day_master_root_present(pillars, day_stem_key, day_element)
    candidates: List[Dict[str, Any]] = []
    for pair, transformed in HEAVENLY_STEM_TRANSFORMATIONS.items():
        if day_stem_key not in pair or not pair <= set(stems):
            continue
        month_support = _month_supports_element(pillars, transformed)
        blockers = []
        if root_present:
            blockers.append("return_to_root_blocker")
        if not month_support:
            blockers.append("month_support_absent")
        classification = "classified" if not blockers else "failed_transformation"
        candidates.append({
            "type": "hua_qi",
            "family": "transformation_structure",
            "role": "hua_qi",
            "stems": sorted(pair),
            "element": transformed,
            "classification": classification,
            "month_support": month_support,
            "blockers": blockers,
            "priority": 2,
            "reason": (
                f"{' and '.join(sorted(pair))} form a transformation pair toward {transformed}; "
                "month support and no return-to-root blocker are required before ordinary balancing is displaced."
            ),
        })
    return candidates


def _special_structure_screen(
    counts: Dict[str, int],
    day_element: str,
    strength: str,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]] = None,
    day_stem_key: str = "",
) -> Dict[str, Any]:
    total = sum(int(counts.get(element) or 0) for element in ELEMENTS)
    dominant_element = max(ELEMENTS, key=lambda element: (int(counts.get(element) or 0), element))
    dominant_count = int(counts.get(dominant_element) or 0)
    day_count = int(counts.get(day_element) or 0)
    ratio = (dominant_count / total) if total else 0.0
    flags: List[Dict[str, Any]] = []
    day_stem_key = day_stem_key or str(((pillars or {}).get("day") or {}).get("stem") or "")
    follow_candidate = _follow_special_candidate(
        dominant_element=dominant_element,
        day_element=day_element,
        day_stem_key=day_stem_key,
        strength=strength,
        ratio=ratio,
        day_count=day_count,
        pillars=pillars,
    )
    if follow_candidate:
        flags.append(follow_candidate)
    flags.extend(_stem_transformation_candidates(pillars, day_stem_key, day_element))
    dominant_candidate = _dominant_special_candidate(
        dominant_element=dominant_element,
        day_element=day_element,
        strength=strength,
        ratio=ratio,
        counts=counts,
        pillars=pillars,
    )
    if dominant_candidate:
        flags.append(dominant_candidate)
    if strength in {"very strong", "extremely strong", "very weak", "extremely weak"} and not flags:
        flags.append({
            "type": "extreme_strength_label",
            "family": "extreme_strength",
            "role": "extreme",
            "element": day_element,
            "classification": "suspected",
            "priority": 4,
            "reason": "Extreme strength labels require manual source fixtures before the MVP treats the structure as classified.",
        })
    flags = sorted(flags, key=lambda flag: (int(flag.get("priority") or 99), str(flag.get("type") or "")))
    classified = [flag for flag in flags if flag.get("classification") == "classified"]
    suspected = [flag for flag in flags if flag.get("classification") != "classified"]
    presence_only_flags = [
        flag for flag in flags
        if flag.get("classification") == "suspected_presence_only"
    ]
    primary_structure = classified[0] if classified else (suspected[0] if suspected else None)
    return {
        "status": "candidate_flags" if flags else "screened_not_classified",
        "method": "presence_screened_special_structure_v2",
        "structure_status": "classified" if classified else ("suspected" if suspected else "none"),
        "structure_types": sorted({str(flag.get("type")) for flag in flags if flag.get("type")}),
        "primary_structure": primary_structure,
        "flags": flags,
        "presence_only_flags": presence_only_flags,
        "presence_only_decision_authority": "none",
        "notes": [
            "Special structures displace ordinary support/pressure rules only when source criteria are classified.",
            "False follow and failed transformation remain visible but withhold final Useful God selection.",
            "Unweighted element ratios can trigger review but cannot classify dominant or follow structures as usable qi.",
        ],
        "source_page_refs": ["lu_zhiji_fate_search:pp281-297", "yuanhai_ziping:pp110-130"],
        "source_confidence": confidence_tags("local_source", "computed_rule"),
    }


def _source_ids_from_basis(source_basis: Iterable[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    for row in source_basis:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def _decision_source_evidence(
    *,
    rule_id: str,
    source_ids: List[str],
    fixture_ids: List[str],
    claim: str,
) -> List[Dict[str, Any]]:
    return [
        {
            "source_id": source_id,
            "rule_id": rule_id,
            "claim": claim,
            "strength": "primary" if index == 0 else "cross_check",
            "fixture_ids": fixture_ids,
        }
        for index, source_id in enumerate(source_ids)
    ]


def _yong_shen_family_for_strength(strength: str) -> str:
    if strength in {"strong", "very strong", "extremely strong"}:
        return YONG_SHEN_RULE_FAMILIES["strong_balancing"]
    if strength in {"weak", "very weak", "extremely weak"}:
        return YONG_SHEN_RULE_FAMILIES["weak_support"]
    return YONG_SHEN_RULE_FAMILIES["balanced_withheld"]


def _family_key_from_decision_path(decision_path: str) -> str:
    return str(decision_path or "").replace("yong_shen.", "")


def _primary_climate_candidate(climate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = climate.get("recommendations") if isinstance(climate.get("recommendations"), list) else []
    return next((row for row in rows if row.get("priority") == "primary"), None)


def _primary_special_candidate(special_screen: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    primary = special_screen.get("primary_structure") if isinstance(special_screen.get("primary_structure"), dict) else None
    if primary and primary.get("classification") == "classified" and primary.get("family") in {
        "dominant_element",
        "follow_structure",
        "transformation_structure",
    }:
        return primary
    return None


def _timing_layer_effect_for_element(element: str, layer_name: str, pillar: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(pillar, dict) or not element:
        return None
    checked = [
        ("stem", pillar.get("stem"), pillar.get("stem_element")),
        ("branch", pillar.get("branch"), pillar.get("branch_element")),
    ]
    for placement, symbol, source_element in checked:
        source_element = str(source_element or "")
        if not source_element:
            continue
        if source_element == element:
            effect = "supplies"
        elif PRODUCES.get(source_element) == element:
            effect = "supports"
        elif CONTROLS.get(source_element) == element:
            effect = "pressures"
        elif CONTROLS.get(element) == source_element:
            effect = "drains_into"
        else:
            effect = "background"
        if effect != "background":
            return {
                "layer": layer_name,
                "placement": placement,
                "symbol": symbol,
                "source_element": source_element,
                "effect": effect,
            }
    return None


def _timing_useful_element_interaction(payload: Dict[str, Any], timing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(timing, dict) or not timing.get("luck_pillars_enabled"):
        return {
            "status": "not_enabled",
            "method": "useful_element_timing_interaction_v1",
            "items": [],
            "summary": "Luck Pillar interaction requires an enabled decade sequence.",
            "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
        }
    candidates = [
        row for row in payload.get("favorable") or []
        if isinstance(row, dict) and row.get("element")
    ]
    active = timing.get("active_luck_pillar") if isinstance(timing.get("active_luck_pillar"), dict) else None
    annual = timing.get("annual_pillar") if isinstance(timing.get("annual_pillar"), dict) else None
    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        element = str(candidate.get("element") or "")
        effects = [
            effect for effect in (
                _timing_layer_effect_for_element(element, "active_luck_pillar", active),
                _timing_layer_effect_for_element(element, "annual_pillar", annual),
            )
            if effect
        ]
        if not effects:
            continue
        effect_names = {str(effect.get("effect")) for effect in effects}
        if "pressures" in effect_names:
            status = "pressured_by_timing"
        elif "supplies" in effect_names:
            status = "supplied_by_timing"
        elif "supports" in effect_names:
            status = "supported_by_timing"
        else:
            status = "activated_by_timing"
        rows.append({
            "element": element,
            "role": candidate.get("role"),
            "priority": candidate.get("priority"),
            "status": status,
            "effects": effects,
            "summary": f"{element} is {status.replace('_', ' ')} through the current decade/year layer.",
        })
    return {
        "status": "active" if rows else "quiet",
        "method": "useful_element_timing_interaction_v1",
        "items": rows,
        "summary": (
            f"{len(rows)} useful-element timing interaction(s) detected."
            if rows else "No active Luck Pillar or annual layer directly supplies, supports, or pressures the favorable candidates."
        ),
        "source_basis": [LOCAL_SOURCE_BASIS[7]],
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
        "notes": [
            "Timing can modify confidence and actionability, but timing-only support does not release final Yong Shen by itself.",
        ],
    }


def _decide_yong_shen(
    payload: Dict[str, Any],
    damage_rows: List[Dict[str, Any]],
    special_screen: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    confidence = str(payload.get("confidence") or "low").lower()
    status = str(payload.get("status") or "")
    strength = str(payload.get("day_master_strength") or analysis.get("strength") or "uncertain").lower()
    base_family = _yong_shen_family_for_strength(strength)
    damage_by_element = {row.get("element"): row for row in damage_rows}
    all_candidates = [
        row for row in payload.get("favorable") or []
        if isinstance(row, dict) and row.get("element")
    ]
    qi_evaluated_candidates = [
        row for row in payload.get("favorable") or []
        if isinstance(row, dict)
        and row.get("element")
        and isinstance(row.get("integrity"), dict)
        and row.get("integrity", {}).get("qi_strength_status") == "evaluated"
        and damage_by_element.get(row.get("element"), {}).get("status") != "damaged"
    ]
    primary = (
        next((row for row in qi_evaluated_candidates if row.get("priority") == "primary"), None)
        or (qi_evaluated_candidates[0] if qi_evaluated_candidates else None)
    )
    blocked_primary = next((row for row in all_candidates if row.get("priority") == "primary"), None) or (all_candidates[0] if all_candidates else None)
    primary_damage = damage_by_element.get((blocked_primary or {}).get("element"))
    climate = payload.get("climate_adjustment") if isinstance(payload.get("climate_adjustment"), dict) else {}
    climate_candidate = _primary_climate_candidate(climate)
    special_candidate = _primary_special_candidate(special_screen)
    tong_guan = payload.get("tong_guan") if isinstance(payload.get("tong_guan"), dict) else {}
    tong_guan_candidate = (
        tong_guan.get("primary_candidate")
        if isinstance(tong_guan.get("primary_candidate"), dict)
        and tong_guan.get("primary_candidate", {}).get("decision_candidate")
        else None
    )
    climate_override_candidate = (
        climate_candidate
        if climate_candidate
        and climate_candidate.get("override_candidate")
        and climate_candidate.get("source_rule_status") in CLIMATE_SOURCE_READY_STATUSES
        and not climate_candidate.get("needs_page_image_check")
        and climate_candidate.get("element")
        and climate_candidate.get("element") != (primary or blocked_primary or {}).get("element")
        else None
    )
    special_flags = special_screen.get("flags") if isinstance(special_screen.get("flags"), list) else []
    presence_only_special_flags = [
        flag for flag in special_flags
        if isinstance(flag, dict) and flag.get("classification") == "suspected_presence_only"
    ]
    actionable_special_flags = [
        flag for flag in special_flags
        if isinstance(flag, dict) and flag.get("classification") != "suspected_presence_only"
    ]
    blocking_reasons: List[str] = []
    decision_path = base_family
    selected = primary or blocked_primary
    selected_role = selected.get("role") if isinstance(selected, dict) else None

    if status != "provisional":
        decision_path = YONG_SHEN_RULE_FAMILIES["balanced_withheld"]
        blocking_reasons.append("strength_not_decisive")
    if confidence not in {"medium", "high"}:
        decision_path = YONG_SHEN_RULE_FAMILIES["confidence_withheld"]
        blocking_reasons.append("low_recommendation_confidence")
    if actionable_special_flags and not special_candidate:
        decision_path = YONG_SHEN_RULE_FAMILIES["special_structure_withheld"]
        blocking_reasons.append("special_structure_review_required")
        if primary_damage and primary_damage.get("status") == "damaged":
            blocking_reasons.append(f"primary_candidate_{primary_damage.get('status')}")
    if status == "provisional" and not all_candidates:
        blocking_reasons.append("no_favorable_candidate")
    if special_candidate and status == "provisional":
        decision_path = YONG_SHEN_RULE_FAMILIES[str(special_candidate.get("family"))]
        selected = {
            "element": special_candidate.get("element"),
            "role": special_candidate.get("role") or special_candidate.get("type"),
            "priority": "primary",
            "integrity": {
                "availability": "structural",
                "pressure": "clear",
                "summary": special_candidate.get("reason"),
                "qi_strength_status": "structurally_classified",
            },
        }
        selected_role = selected.get("role")
    elif actionable_special_flags and status == "provisional":
        selected = blocked_primary or selected
        selected_role = selected.get("role") if isinstance(selected, dict) else None
    elif climate_override_candidate and not actionable_special_flags and status == "provisional":
        decision_path = YONG_SHEN_RULE_FAMILIES["climate_override"]
        selected = {
            "element": climate_override_candidate.get("element"),
            "role": "regulating",
            "priority": "primary",
            "integrity": {
                "availability": climate_override_candidate.get("availability"),
                "pressure": climate_override_candidate.get("pressure") or "clear",
                "summary": climate_override_candidate.get("reason"),
                "source_page_refs": climate_override_candidate.get("source_page_refs") or [],
                "qi_strength_status": climate_override_candidate.get("qi_strength_status") or "not_evaluated",
            },
        }
        selected_role = "regulating"
        if climate_override_candidate.get("availability") == "absent":
            blocking_reasons.append("climate_candidate_absent")
        if climate_override_candidate.get("pressure") == "pressured":
            blocking_reasons.append("climate_candidate_pressured")
        if climate_override_candidate.get("qi_strength_status") != "evaluated":
            blocking_reasons.append("climate_candidate_qi_strength_unresolved")
    elif primary_damage and primary_damage.get("status") == "damaged":
        alternate = next((row for row in qi_evaluated_candidates if row.get("element") != (blocked_primary or {}).get("element")), None)
        alternate_damage = damage_by_element.get((alternate or {}).get("element")) if alternate else None
        if not alternate and tong_guan_candidate and primary_damage.get("source_pattern") is True:
            decision_path = YONG_SHEN_RULE_FAMILIES["tong_guan"]
            selected = {
                "element": tong_guan_candidate.get("element"),
                "role": "Tong Guan",
                "priority": "bridge",
                "integrity": tong_guan_candidate.get("integrity") or {
                    "availability": tong_guan_candidate.get("availability"),
                    "pressure": tong_guan_candidate.get("pressure"),
                    "summary": tong_guan_candidate.get("reason"),
                },
            }
            selected_role = "Tong Guan"
        elif alternate and primary_damage.get("source_pattern") is True and (alternate_damage or {}).get("status") == "timing_assisted":
            decision_path = YONG_SHEN_RULE_FAMILIES["damaged_alternate"]
            selected = alternate
            selected_role = alternate.get("role")
            blocking_reasons.append("alternate_timing_only")
        elif alternate and primary_damage.get("source_pattern") is True:
            decision_path = YONG_SHEN_RULE_FAMILIES["damaged_alternate"]
            selected = alternate
            selected_role = alternate.get("role")
        elif alternate and primary_damage.get("status") == "damaged":
            decision_path = YONG_SHEN_RULE_FAMILIES["damage_withheld"]
            selected = alternate
            selected_role = alternate.get("role")
            blocking_reasons.append("damage_pattern_not_source_backed")
        else:
            decision_path = YONG_SHEN_RULE_FAMILIES["damage_withheld"]
            if primary_damage.get("source_pattern") is not True:
                blocking_reasons.append("damage_pattern_not_source_backed")
            blocking_reasons.append(f"primary_candidate_{primary_damage.get('status')}")
    elif primary_damage and primary_damage.get("status") == "timing_assisted":
        decision_path = YONG_SHEN_RULE_FAMILIES["timing_assisted"]
        blocking_reasons.append("timing_assisted_final_not_released")

    selected_integrity = selected.get("integrity") if isinstance(selected, dict) and isinstance(selected.get("integrity"), dict) else {}
    if (
        status == "provisional"
        and selected
        and not special_candidate
        and selected_integrity.get("qi_strength_status") != "evaluated"
    ):
        blocking_reasons.append("candidate_qi_strength_unresolved")

    source_ids = _source_ids_from_basis((payload.get("source_basis") or []) + (climate.get("source_basis") or []))
    family_key = _family_key_from_decision_path(decision_path)
    gate = yong_shen_family_gate(family_key)
    fixture_ids = gate.get("fixture_ids") or []
    if not gate.get("released") and family_key in {
        "strong_balancing",
        "weak_support",
        "climate_override",
        "dominant_element",
        "follow_structure",
        "transformation_structure",
        "damaged_alternate",
        "timing_assisted",
    }:
        blocking_reasons.append("family_fixture_gate_blocked")
    evidence = {
        "strength": {
            "label": strength,
            "support_score": analysis.get("support_score"),
            "pressure_score": analysis.get("pressure_score"),
            "model_confidence": (analysis.get("strength_model") or {}).get("confidence")
            if isinstance(analysis.get("strength_model"), dict) else None,
        },
        "climate": payload.get("climate_adjustment") or {},
        "presence": (selected or blocked_primary or {}).get("integrity") or {},
        "damage": primary_damage or {},
        "structure_selection": payload.get("structure_selection") or {},
        "special_structure": special_screen,
        "presence_only_special_flags": presence_only_special_flags,
        "actionable_special_flags": actionable_special_flags,
        "tong_guan": payload.get("tong_guan") or {},
        "fixture_gate": gate,
        "timing": payload.get("timing_interaction") or {},
    }
    source_evidence = _decision_source_evidence(
        rule_id=decision_path,
        source_ids=source_ids,
        fixture_ids=list(fixture_ids),
        claim=(
            "Final Yong Shen is allowed only when the rule family has source-backed executable chart-input assertions."
            if gate.get("released") else
            "This rule family is exposed as evidence but remains blocked until executable chart-input assertion fixtures pass."
        ),
    )

    eligible_for_final = (
        status == "provisional"
        and selected
        and confidence in {"medium", "high"}
        and not blocking_reasons
        and bool(gate.get("released"))
    )
    if eligible_for_final:
        return {
            "final_status": "final",
            "candidate_status": "final",
            "element": selected.get("element"),
            "role": selected_role,
            "rule_family": family_key,
            "decision_path": decision_path,
            "confidence": confidence,
            "reason": "This chart matches a released source-backed family with executable chart-input assertions and no configured blocker is active.",
            "blocking_reasons": [],
            "evidence": evidence,
            "source_ids": source_ids,
            "fixture_ids": list(fixture_ids),
            "source_evidence": source_evidence,
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        }

    if status == "provisional" and selected and confidence in {"medium", "high"}:
        return {
            "final_status": "withheld",
            "candidate_status": "candidate_preview",
            "element": selected.get("element"),
            "role": selected_role,
            "rule_family": family_key,
            "decision_path": decision_path,
            "confidence": confidence,
            "reason": "This is a strength-derived role candidate, but its own effective qi and the remaining release fixtures are unresolved.",
            "blocking_reasons": blocking_reasons or ["final_fixture_not_curated"],
            "evidence": evidence,
            "source_ids": source_ids,
            "fixture_ids": list(fixture_ids),
            "source_evidence": source_evidence,
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        }
    return {
        "final_status": "withheld",
        "candidate_status": "withheld",
        "element": None,
        "role": None,
        "rule_family": family_key,
        "decision_path": decision_path,
        "confidence": confidence,
        "reason": "The app does not name a final Yong Shen when strength confidence is low, the chart is balanced/uncertain, or candidate qi and damage gates are unresolved.",
        "blocking_reasons": blocking_reasons or ["final_fixture_not_curated"],
        "evidence": evidence,
        "source_ids": source_ids,
        "fixture_ids": list(fixture_ids),
        "source_evidence": source_evidence,
        "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
    }


def _finalize_useful_element_payload(
    payload: Dict[str, Any],
    *,
    analysis: Dict[str, Any],
    counts: Dict[str, int],
    day_element: str,
    day_stem_index: int,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]],
    relationships: Optional[Dict[str, Any]],
    timing: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    enriched = _with_element_integrity(payload, pillars=pillars, relationships=relationships, timing=timing)
    structure_selection = _month_command_structure_selection(day_stem_index, pillars)
    enriched["structure_selection"] = structure_selection
    damage_rows, damage_summary = _damage_assessment(enriched, counts, day_element)
    enriched["climate_adjustment"] = _climate_adjustment(
        day_stem_index,
        analysis,
        counts,
        pillars=pillars,
        relationships=relationships,
        timing=timing,
    )
    enriched["damage_assessment"] = damage_rows
    enriched["damage_summary"] = damage_summary
    enriched["tong_guan"] = _tong_guan_analysis(enriched, damage_rows, counts, day_element)
    enriched["timing_interaction"] = _timing_useful_element_interaction(enriched, timing)
    special_screen = _special_structure_screen(
        counts,
        day_element,
        str(analysis.get("strength") or "uncertain").lower(),
        pillars,
        str(STEMS[int(day_stem_index) % 10]["key"]),
    )
    enriched["special_structure_screen"] = special_screen
    enriched["useful_god"] = _decide_yong_shen(enriched, damage_rows, special_screen, analysis)
    enriched["source_evidence"] = enriched["useful_god"].get("source_evidence") or []
    notes = list(enriched.get("notes") or [])
    for note in (
        "Climate, special-structure, damaged-useful, and timing evidence are released only through executable chart-input assertion gates.",
        "Timing-assisted candidates remain evidence-only until the timing-assisted fixture family is enabled for final release.",
        "Unweighted element presence is reported as placement availability only and has no Yong Shen decision authority.",
    ):
        if note not in notes:
            notes.append(note)
    enriched["notes"] = notes
    return enriched


def build_useful_element_recommendations(
    *,
    day_stem_index: int,
    analysis: Dict[str, Any],
    balance: Dict[str, Any],
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]] = None,
    relationships: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day_stem = STEMS[int(day_stem_index) % 10]
    day_element = day_stem["element"]
    roles = _element_role_map(day_element)
    raw_presence_counts = balance.get("counts") or balance.get("total") or {}
    counts = {
        element: int(raw_presence_counts.get(element) or 0)
        for element in ELEMENTS
    }
    presence_context = {
        "model_id": balance.get("model_id") or "legacy_element_presence_counts",
        "measure": balance.get("measure") or "unweighted_presence_count",
        "counts": counts,
        "is_qi_strength": False,
        "decision_authority": "none",
        "used_for": ["placement_availability_display", "presence_only_review"],
        "not_used_for": [
            "day_master_strength",
            "candidate_qi_strength",
            "candidate_eligibility",
            "candidate_actionability",
            "effective_element_supply",
            "damage_classification",
            "dominant_or_follow_structure_classification",
        ],
    }
    strength = str(analysis.get("strength") or "uncertain").lower()
    support_score = float(analysis.get("support_score") or 0)
    pressure_score = float(analysis.get("pressure_score") or 0)
    score_gap = abs(support_score - pressure_score)
    model = analysis.get("strength_model") if isinstance(analysis.get("strength_model"), dict) else {}
    model_confidence = str(model.get("confidence") or "").lower()
    recommendation_confidence = "medium" if model_confidence in {"medium", "high"} and score_gap >= 1.5 else "low"

    source_basis = [
        LOCAL_SOURCE_BASIS[1],
        LOCAL_SOURCE_BASIS[2],
        {
            "id": "method.season_root_formation_v2",
            "label": "Season/root/formation strength check",
            "basis": "Recommendations are generated only after month season, root, and formation evidence produce a strong or weak label.",
        },
    ]

    if strength in {"strong", "very strong", "extremely strong"}:
        favorable = [
            _role_item(
                element=roles["Wealth"],
                role="Wealth",
                priority="primary",
                counts=counts,
                reason="A strong Day Master can spend strength by controlling the Wealth element.",
            ),
            _role_item(
                element=roles["Output"],
                role="Output",
                priority="secondary",
                counts=counts,
                reason="Producing the Output element drains and circulates excess Day Master strength.",
            ),
            _role_item(
                element=roles["Influence"],
                role="Influence",
                priority="conditional",
                counts=counts,
                reason="The controlling element can restrain excess strength when pressure is not already overwhelming.",
            ),
        ]
        unfavorable = [
            _role_item(
                element=roles["Companion"],
                role="Companion",
                priority="avoid",
                counts=counts,
                reason="More of the same element can increase an already strong Day Master.",
            ),
            _role_item(
                element=roles["Resource"],
                role="Resource",
                priority="avoid",
                counts=counts,
                reason="Resource produces the Day Master and may add support that the chart does not need.",
            ),
        ]
        return _finalize_useful_element_payload({
            "status": "provisional",
            "method": "season_root_formation_v2",
            "confidence": recommendation_confidence,
            "day_master_strength": strength,
            "day_master_element": day_element,
            "element_presence": presence_context,
            "favorable": favorable,
            "unfavorable": unfavorable,
            "notes": [
                "This is provisional favorable-element guidance, not a final Yong Shen determination.",
                "Special structures are screened but not classified; climate and damaged-useful checks remain provisional.",
            ],
            "source_basis": [*source_basis, LOCAL_SOURCE_BASIS[7], LOCAL_SOURCE_BASIS[8]],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        }, analysis=analysis, counts=counts, day_element=day_element, day_stem_index=day_stem_index, pillars=pillars, relationships=relationships, timing=timing)

    if strength in {"weak", "very weak", "extremely weak"}:
        favorable = [
            _role_item(
                element=roles["Resource"],
                role="Resource",
                priority="primary",
                counts=counts,
                reason="Resource produces the Day Master and can rebuild weak chart support.",
            ),
            _role_item(
                element=roles["Companion"],
                role="Companion",
                priority="secondary",
                counts=counts,
                reason="The same element reinforces a Day Master that lacks strength.",
            ),
        ]
        unfavorable = [
            _role_item(
                element=roles["Influence"],
                role="Influence",
                priority="avoid",
                counts=counts,
                reason="The controlling element can over-control a weak Day Master.",
            ),
            _role_item(
                element=roles["Output"],
                role="Output",
                priority="avoid",
                counts=counts,
                reason="Producing Output drains a Day Master that is already weak.",
            ),
            _role_item(
                element=roles["Wealth"],
                role="Wealth",
                priority="avoid",
                counts=counts,
                reason="Controlling Wealth spends strength and can burden a weak Day Master.",
            ),
        ]
        return _finalize_useful_element_payload({
            "status": "provisional",
            "method": "season_root_formation_v2",
            "confidence": recommendation_confidence,
            "day_master_strength": strength,
            "day_master_element": day_element,
            "element_presence": presence_context,
            "favorable": favorable,
            "unfavorable": unfavorable,
            "notes": [
                "This is provisional favorable-element guidance, not a final Yong Shen determination.",
                "The engine is source-gated when support and pressure evidence are close.",
            ],
            "source_basis": [*source_basis, LOCAL_SOURCE_BASIS[7], LOCAL_SOURCE_BASIS[8]],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        }, analysis=analysis, counts=counts, day_element=day_element, day_stem_index=day_stem_index, pillars=pillars, relationships=relationships, timing=timing)

    low_elements = sorted(ELEMENTS, key=lambda element: (counts.get(element, 0), element))[:2]
    return _finalize_useful_element_payload({
        "status": "withheld",
        "method": "season_root_formation_v2",
        "confidence": "low",
        "day_master_strength": strength,
        "day_master_element": day_element,
        "element_presence": presence_context,
        "favorable": [],
        "unfavorable": [],
        "candidates_to_watch": [
            {
                "element": element,
                "count": counts.get(element, 0),
                "presence_count": counts.get(element, 0),
                "presence_measure": "unweighted_presence_count",
                "qi_strength_status": "not_evaluated",
                "reason": "This element is light in the unweighted inventory; that alone does not make it useful or weak.",
            }
            for element in low_elements
        ],
        "notes": [
            "The current chart is balanced or uncertain, so the app does not name a useful element yet.",
            "Use the element presence inventory, roots, Ten Gods, and timing layers as separate evidence until strength fixtures are expanded.",
        ],
        "source_basis": [*source_basis, LOCAL_SOURCE_BASIS[7], LOCAL_SOURCE_BASIS[8]],
        "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
    }, analysis=analysis, counts=counts, day_element=day_element, day_stem_index=day_stem_index, pillars=pillars, relationships=relationships, timing=timing)


def _top_counts(rows: Iterable[Dict[str, Any]], key: str, limit: int = 3) -> List[Dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = row.get(key)
        if value:
            counter[str(value)] += 1
    return [
        {"label": label, "count": count}
        for label, count in counter.most_common(limit)
    ]


def _format_count_items(items: List[Dict[str, Any]]) -> str:
    parts = [
        f"{item.get('label')} x{item.get('count')}"
        for item in items
        if item.get("label")
    ]
    return ", ".join(parts) if parts else "none detected"


def _relationship_highlights(relationships: Dict[str, Any]) -> List[str]:
    summary = relationships.get("summary") or {}
    events = relationships.get("events") or []
    highlights: List[str] = []
    if summary.get("natal"):
        highlights.append(f"{summary.get('natal')} natal relationship code(s) are present in the fixed chart.")
    if summary.get("luck"):
        highlights.append(f"{summary.get('luck')} current Luck Pillar trigger(s) interact with the natal chart.")
    if summary.get("annual"):
        highlights.append(f"{summary.get('annual')} current-year trigger(s) interact with the natal chart.")
    if events:
        first = events[0]
        label = first.get("label") or first.get("type") or "relationship code"
        scope = first.get("scope_label") or first.get("scope") or "chart"
        highlights.append(f"First detected code: {label} in the {scope} layer.")
    return highlights


def _auxiliary_star_highlights(auxiliary_stars: Dict[str, Any]) -> List[str]:
    markers = auxiliary_stars.get("markers") if isinstance(auxiliary_stars, dict) else []
    if isinstance(markers, list) and markers:
        active = [
            marker for marker in markers
            if isinstance(marker, dict) and marker.get("marker_state") not in {"quiet", None}
        ]
        if active:
            labels = ", ".join(
                f"{marker.get('label')} ({marker.get('state_label') or marker.get('marker_state')})"
                for marker in active[:5]
            )
            return [
                f"Auxiliary markers active in checked natal/timing layers: {labels}.",
                "Use these as placement cues for attraction, movement, study, support, or virtue themes after the main chart structure is read.",
            ]
        return [
            "Auxiliary markers were calculated, but none are active in the checked natal, Luck, or annual placements.",
        ]
    peach = auxiliary_stars.get("peach_blossom") if isinstance(auxiliary_stars, dict) else {}
    if not isinstance(peach, dict) or peach.get("status") != "source_based_preview":
        return []
    highlights = [
        f"Personal Peach Blossom branch: {peach.get('target_branch', '-')} ({peach.get('target_animal', '-')}) from Day Branch {peach.get('day_branch', '-')}.",
        peach.get("summary") or "Peach Blossom activation is descriptive only.",
        "Read this as attraction, charisma, public appeal, or timing potential; placement and relationship-contact pressure decide how useful it is.",
    ]
    family = peach.get("branch_family") if isinstance(peach.get("branch_family"), dict) else {}
    if family.get("all_four_present"):
        highlights.append("All four Peach Blossom branches are present across checked layers, so the reading must stay placement-specific rather than assume benefit.")
    return highlights


def _palace_highlights(palace_context: Dict[str, Any]) -> List[str]:
    if not isinstance(palace_context, dict) or palace_context.get("status") != "source_based_preview":
        return []
    focus = palace_context.get("focus") if isinstance(palace_context.get("focus"), dict) else {}
    palaces = palace_context.get("palaces") if isinstance(palace_context.get("palaces"), list) else []
    highlights: List[str] = []
    if focus.get("summary"):
        highlights.append(str(focus["summary"]))
    touched = [
        palace for palace in palaces
        if isinstance(palace, dict) and (
            int(palace.get("relationship_event_count") or 0) > 0
            or palace.get("auxiliary_hits")
        )
    ]
    if touched:
        labels = ", ".join(
            f"{palace.get('pillar_label')} ({palace.get('domain')})"
            for palace in touched[:3]
        )
        highlights.append(f"Placement focus: {labels}.")
    else:
        highlights.append("No configured relationship-contact or auxiliary-star pressure concentrates in one palace.")
    highlights.append("Use this layer to locate where chart evidence operates; do not read a code as generic until its palace is checked.")
    return highlights


def build_interpretation(
    *,
    birth: Dict[str, Any],
    pillars: Dict[str, Optional[Dict[str, Any]]],
    day_master: Dict[str, Any],
    balance: Dict[str, Any],
    ten_gods: Dict[str, Any],
    analysis: Dict[str, Any],
    relationships: Dict[str, Any],
    timing: Dict[str, Any],
    useful_elements: Dict[str, Any],
    auxiliary_stars: Optional[Dict[str, Any]] = None,
    palace_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day_stem = day_master.get("stem") or "-"
    day_element = day_master.get("element") or "-"
    day_polarity = day_master.get("polarity") or "-"
    strength = analysis.get("strength") or "uncertain"
    strength_model = analysis.get("strength_model") if isinstance(analysis.get("strength_model"), dict) else {}
    season_model = strength_model.get("season") if isinstance(strength_model.get("season"), dict) else {}
    root_model = strength_model.get("root") if isinstance(strength_model.get("root"), dict) else {}
    formation_model = strength_model.get("formation") if isinstance(strength_model.get("formation"), dict) else {}
    month = pillars.get("month") or {}
    hour = pillars.get("hour") or {}
    totals = balance.get("total") or {}
    most_mentioned = sorted(ELEMENTS, key=lambda element: (-int(totals.get(element) or 0), element))[:2]
    least_mentioned = sorted(ELEMENTS, key=lambda element: (int(totals.get(element) or 0), element))[:2]
    visible_factors = _top_counts(ten_gods.get("visible") or [], "factor")
    hidden_factors = _top_counts(ten_gods.get("hidden") or [], "factor")
    factor_profile = ten_gods.get("factor_profile") if isinstance(ten_gods.get("factor_profile"), dict) else {}
    true_solar = birth.get("true_solar_time") if isinstance(birth.get("true_solar_time"), dict) else {}
    relationship_notes = _relationship_highlights(relationships)
    auxiliary_notes = _auxiliary_star_highlights(auxiliary_stars or {})
    palace_notes = _palace_highlights(palace_context or {})
    integrity = useful_elements.get("integrity_summary") if isinstance(useful_elements.get("integrity_summary"), dict) else {}

    sections = [
        {
            "title": "Day Master Frame",
            "items": [
                f"{day_stem} is the {day_polarity} {day_element} Day Master and remains the reference point for Ten Gods, element roles, and strength judgement.",
                f"The strength reading is {strength} with {strength_model.get('confidence', 'low')} confidence after checking season, roots, and formations.",
            ],
            "source_ids": ["local.four_pillars_strength"],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        },
        {
            "title": "Season And Roots",
            "items": [
                f"The month branch is {month.get('branch', '-')} ({month.get('branch_element', '-')}); month season is weighted before looser element counts.",
                f"Season state: {season_model.get('season', '-')} / {season_model.get('state', '-')}; root score: {root_model.get('score', '-')}; formation score: {formation_model.get('score', '-')}.",
                f"Presence cross-check only: most-mentioned elements are {', '.join(most_mentioned)}; least-mentioned elements are {', '.join(least_mentioned)}. These unweighted counts are not qi strength.",
            ],
            "source_ids": ["local.four_pillars_strength"],
            "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model"),
        },
        {
            "title": "Ten God Texture",
            "items": [
                factor_profile.get("summary") or "Five Factor texture is read before individual direct or indirect Ten God labels.",
                f"Visible factors: {_format_count_items(visible_factors)}.",
                f"Hidden factors: {_format_count_items(hidden_factors)}.",
                "The Day Master itself is the reference point, not a separate visible Ten God count.",
            ],
            "source_ids": ["local.destiny_code_five_factors", "local.four_pillars_strength"],
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        },
        {
            "title": "Hour Pillar Timing",
            "items": [
                f"The selected hour pillar is {hour.get('stem', '-')} {hour.get('branch', '-')}.",
                (
                    f"True solar time is applied for the hour pillar; correction is {true_solar.get('total_correction_minutes')} minutes."
                    if true_solar.get("applied")
                    else "Civil local time is used for the hour pillar unless true solar time is enabled and longitude is available."
                ),
            ],
            "source_ids": ["web.noaa_true_solar_time", "web.usno_equation_of_time"],
            "source_confidence": confidence_tags("computed_rule", "school_variant", "needs_validation"),
        },
        {
            "title": "Useful Element Boundary",
            "items": [
                (
                    f"Favorable elements are shown as {useful_elements.get('confidence', 'low')}-confidence provisional guidance."
                    if useful_elements.get("status") == "provisional"
                    else "A final Useful God is withheld because the current strength evidence is balanced or uncertain."
                ),
                (
                    f"Presence check: {integrity.get('favorable_present', 0)} favorable element(s) are natal, "
                    f"{integrity.get('favorable_timing_supported', 0)} are timing-supported, "
                    f"and {integrity.get('favorable_pressured', 0)} are touched by challenging relationship contacts."
                ),
                "A final Yong Shen is only shown when the strength, climate, special-structure, damage, and fixture gates are clear.",
            ],
            "source_ids": ["local.destiny_code_favorable_elements", "local.destiny_code_revealed_relationships"],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        },
    ]
    if relationship_notes:
        sections.append({
            "title": "Relationship Contacts",
            "items": relationship_notes,
            "source_ids": ["local.destiny_code_revealed_relationships"],
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        })
    if palace_notes:
        sections.append({
            "title": "Palace Context",
            "items": palace_notes,
            "source_ids": ["local.four_pillars_palace_context", "local.destiny_code_revealed_relationships"],
            "source_confidence": confidence_tags("local_source", "computed_rule"),
        })
    if auxiliary_notes:
        sections.append({
            "title": "Auxiliary Stars",
            "items": auxiliary_notes,
            "source_ids": ["local.destiny_code_peach_blossom", "local.destiny_code_revealed_peach_blossom"],
            "source_confidence": confidence_tags("local_source", "provisional_model"),
        })
    if timing.get("luck_pillars_enabled"):
        active = timing.get("active_luck_pillar") or {}
        sections.append({
            "title": "Timing Layer",
            "items": [
                f"Luck Pillars run {timing.get('direction', '-')} from the month pillar.",
                f"Active decade: {active.get('stem', '-')} {active.get('branch', '-')} ({active.get('age_label', 'not active yet')}).",
            ],
            "source_ids": ["local.four_pillars_strength"],
            "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
        })

    return {
        "status": "source_based_preview",
        "summary": f"{day_stem} {day_element} Day Master, currently reading as {strength} strength.",
        "sections": sections,
        "source_basis": list(LOCAL_SOURCE_BASIS),
        "source_confidence": confidence_tags("local_source", "computed_rule", "provisional_model", "needs_validation"),
    }
