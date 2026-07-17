from __future__ import annotations

from typing import Any, Dict, List, Optional

from .curation import confidence_tags


SOURCE_BASIS = [
    {
        "id": "local.four_pillars_palace_context",
        "label": "Ba Zi - The Four Pillars of Destiny",
        "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.md",
        "basis": "The four pillars are read as life-stage and domain palaces; Hour, Day, Month, and Year locate where chart evidence operates.",
    },
    {
        "id": "local.destiny_code_five_factors",
        "label": "BaZi - The Destiny Code",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-your-guide-to-the-four-pillar-of-destin.md",
        "basis": "The Five Factors map Ten God roles into Wealth, Output, Influence, Resource, and Companion topic families.",
    },
    {
        "id": "local.destiny_code_revealed_four_aspects",
        "label": "BaZi - The Destiny Code Revealed",
        "path": "output/iching_private_corpus/bazi-the-destiny-code-revealed-a-deeper-journey-into-the-four-pillars-of-destiny.md",
        "basis": "Career, wealth, relationships, and health are read through Five Factor condition, contacts, and timing rather than from one isolated sign.",
    },
    {
        "id": "public.san_ming_tong_hui_ten_gods",
        "label": "San Ming Tong Hui",
        "url": "https://ctext.org/wiki.pl?chapter=802420&if=en&remap=gb",
        "basis": "Traditional Ten God naming follows the Day Master's generating, controlling, and same-element relationships.",
    },
]

CONTEXT_REQUIREMENTS = [
    "Day Master strength",
    "useful-element direction",
    "factor visibility and hidden-stem rank",
    "pillar palace placement",
    "stem/branch contacts",
    "luck and annual activation",
]

AREA_DEFINITIONS = [
    {
        "id": "career_authority",
        "label": "Career & Authority",
        "short_label": "Career",
        "factors": ["Influence", "Output"],
        "palaces": ["month", "year"],
        "keywords": ["authority", "status", "responsibility", "work structure", "visible output"],
        "topic_basis": "Influence describes rules, pressure, authority, and status; Output shows what the person produces or performs.",
        "palace_basis": "Month locates formation, colleagues, and work-family structure; Year shows outer/public field.",
    },
    {
        "id": "wealth_assets",
        "label": "Wealth & Assets",
        "short_label": "Wealth",
        "factors": ["Wealth"],
        "palaces": ["month", "year", "day"],
        "keywords": ["money handling", "assets", "management", "capacity", "resources"],
        "topic_basis": "Wealth describes the element controlled by the Day Master: resources, management, assets, and material responsibility.",
        "palace_basis": "Month and Year show public/practical ground; Day shows how material themes enter close life.",
    },
    {
        "id": "relationships_family",
        "label": "Relationships & Family",
        "short_label": "Relationships",
        "factors": ["Wealth", "Influence", "Resource", "Companion"],
        "palaces": ["day", "month", "year"],
        "keywords": ["partner palace", "family", "parents", "siblings", "close bonds"],
        "topic_basis": "Day Branch is the partner palace; Wealth and Influence are used as spouse-star conventions when calculation sex is supplied.",
        "palace_basis": "Day locates intimate bonds; Month and Year locate parents, family formation, ancestry, and wider social background.",
    },
    {
        "id": "health_body",
        "label": "Health & Body Balance",
        "short_label": "Body",
        "factors": [],
        "palaces": ["day", "hour"],
        "keywords": ["element presence", "body correspondences", "pressure", "recovery context"],
        "topic_basis": "Traditional Five Element body correspondences are shown as symbolic context, not as medical or qi-strength findings.",
        "palace_basis": "Day and Hour give close body/private-life context; unweighted element presence only marks where symbols occur.",
    },
    {
        "id": "learning_resources",
        "label": "Learning & Support",
        "short_label": "Support",
        "factors": ["Resource"],
        "palaces": ["month", "year"],
        "keywords": ["learning", "credentials", "mentors", "protection", "support"],
        "topic_basis": "Resource describes what produces the Day Master: education, support, protection, knowledge, and help received.",
        "palace_basis": "Month and Year show formative family, schooling, mentors, and public support networks.",
    },
    {
        "id": "peers_social",
        "label": "Peers & Social Field",
        "short_label": "Peers",
        "factors": ["Companion"],
        "palaces": ["month", "year"],
        "keywords": ["peers", "siblings", "competition", "shared resources", "self-agency"],
        "topic_basis": "Companion describes same-element support and rivalry: peers, siblings, self-agency, and competition.",
        "palace_basis": "Month and Year place that peer field into colleagues, friends, siblings, and wider public contact.",
    },
    {
        "id": "children_output",
        "label": "Children & Creative Output",
        "short_label": "Output",
        "factors": ["Output"],
        "palaces": ["hour"],
        "keywords": ["children", "creative work", "expression", "skill", "future aims"],
        "topic_basis": "Output describes what the Day Master produces: speech, skill, craft, performance, and children/offspring themes.",
        "palace_basis": "Hour locates children, private aims, future direction, and later-life output.",
    },
]


def build_life_areas(
    *,
    ten_gods: Dict[str, Any],
    palace_context: Dict[str, Any],
    relationships: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
    element_balance: Optional[Dict[str, Any]] = None,
    pillars: Optional[Dict[str, Optional[Dict[str, Any]]]] = None,
    calculation_sex: Optional[str] = None,
) -> Dict[str, Any]:
    """Build production-facing topic areas without assigning final outcomes."""

    factor_rows = _factor_rows(ten_gods)
    palace_rows = {
        str(row.get("pillar")): row
        for row in (palace_context.get("palaces") if isinstance(palace_context, dict) else []) or []
        if isinstance(row, dict) and row.get("pillar")
    }
    timing_rows = _timing_factor_rows(timing or {})
    relationship_events = (relationships or {}).get("events") if isinstance(relationships, dict) else []
    relationship_total = len(relationship_events) if isinstance(relationship_events, list) else 0
    areas = [
        _build_area(
            definition,
            factor_rows=factor_rows,
            palace_rows=palace_rows,
            timing_rows=timing_rows,
            element_balance=element_balance or {},
            pillars=pillars or {},
            relationships=relationships or {},
            relationship_total=relationship_total,
            calculation_sex=calculation_sex,
        )
        for definition in AREA_DEFINITIONS
    ]
    emphasized = [area for area in areas if area["context_state"] in {"timing_active", "emphasized"}]
    summary = (
        f"{emphasized[0]['label']} carries the clearest topic emphasis; read it through strength, useful-element direction, and timing."
        if emphasized
        else "Life-area evidence is distributed; no single topic should be treated as dominant from the current chart layer."
    )
    return {
        "status": "source_gated_context",
        "method": "bazi_life_areas_v1",
        "summary": summary,
        "areas": areas,
        "context_requirements": [],
        "limits": [],
        "source_basis": SOURCE_BASIS,
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _factor_rows(ten_gods: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    factors: Dict[str, Dict[str, Any]] = {}
    profile = ten_gods.get("factor_profile") if isinstance(ten_gods, dict) else {}
    for row in (profile.get("factors") if isinstance(profile, dict) else []) or []:
        if not isinstance(row, dict) or not row.get("factor"):
            continue
        factor = str(row["factor"])
        factors[factor] = {
            "factor": factor,
            "element": row.get("element"),
            "visible_count": int(row.get("visible_count") or 0),
            "hidden_count": int(row.get("hidden_count") or 0),
            "total_count": int(row.get("total_count") or 0),
            "summary": row.get("summary"),
            "domain_summary": row.get("domain_summary"),
            "keywords": row.get("keywords") if isinstance(row.get("keywords"), list) else [],
            "gods": row.get("gods") if isinstance(row.get("gods"), list) else [],
        }

    for layer_name in ("visible", "hidden"):
        for row in ten_gods.get(layer_name, []) if isinstance(ten_gods, dict) else []:
            if not isinstance(row, dict) or not row.get("factor"):
                continue
            factor = str(row["factor"])
            if factor in factors:
                gods = factors[factor].setdefault("gods", [])
                if row.get("god") and row.get("god") not in gods:
                    gods.append(row["god"])
                continue
            item = factors.setdefault(
                factor,
                {
                    "factor": factor,
                    "visible_count": 0,
                    "hidden_count": 0,
                    "total_count": 0,
                    "keywords": [],
                    "gods": [],
                },
            )
            count_key = "visible_count" if layer_name == "visible" else "hidden_count"
            item[count_key] = int(item.get(count_key) or 0) + 1
            item["total_count"] = int(item.get("visible_count") or 0) + int(item.get("hidden_count") or 0)
            if row.get("god") and row.get("god") not in item["gods"]:
                item["gods"].append(row["god"])
    return factors


def _timing_factor_rows(timing: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, label in (
        ("active_luck_pillar", "Current 10-Year Luck"),
        ("annual_pillar", "Current BaZi Year"),
        ("flowing_month", "Flowing Month"),
        ("flowing_day", "Flowing Day"),
        ("flowing_hour", "Flowing Hour"),
    ):
        item = timing.get(key) if isinstance(timing, dict) else None
        pillar = item.get("pillar") if isinstance(item, dict) and isinstance(item.get("pillar"), dict) else item
        if not isinstance(pillar, dict):
            continue
        factor = pillar.get("five_factor") or pillar.get("factor")
        if not factor or factor == "Self":
            continue
        rows.append({
            "layer": key,
            "label": label,
            "factor": factor,
            "stem": pillar.get("stem"),
            "branch": pillar.get("branch"),
            "god": pillar.get("ten_god") or pillar.get("god"),
        })
    return rows


def _build_area(
    definition: Dict[str, Any],
    *,
    factor_rows: Dict[str, Dict[str, Any]],
    palace_rows: Dict[str, Dict[str, Any]],
    timing_rows: List[Dict[str, Any]],
    element_balance: Dict[str, Any],
    pillars: Dict[str, Optional[Dict[str, Any]]],
    relationships: Dict[str, Any],
    relationship_total: int,
    calculation_sex: Optional[str],
) -> Dict[str, Any]:
    factors = [factor_rows[factor] for factor in definition["factors"] if factor in factor_rows]
    palaces = [palace_rows[pillar] for pillar in definition["palaces"] if pillar in palace_rows]
    timing_hits = [row for row in timing_rows if row.get("factor") in definition["factors"]]
    contact_count = sum(int(palace.get("relationship_event_count") or 0) for palace in palaces)
    auxiliary_count = sum(int(palace.get("auxiliary_hit_count") or 0) for palace in palaces)
    factor_total = sum(int(factor.get("total_count") or 0) for factor in factors)
    visible_total = sum(int(factor.get("visible_count") or 0) for factor in factors)
    hidden_total = sum(int(factor.get("hidden_count") or 0) for factor in factors)
    score = factor_total + visible_total + contact_count + auxiliary_count + len(timing_hits)
    context_state = _context_state(score, timing_hits, contact_count)
    body_balance = _body_balance_evidence(pillars, element_balance, relationships, timing_rows) if definition["id"] == "health_body" else None
    signals = _signals(definition, factors, palaces, timing_hits, element_balance)
    if body_balance:
        signals.extend(body_balance.get("signals") or [])
    return {
        "id": definition["id"],
        "label": definition["label"],
        "short_label": definition["short_label"],
        "keywords": definition["keywords"],
        "primary_factors": definition["factors"],
        "primary_palaces": definition["palaces"],
        "context_state": context_state,
        "emphasis_score": score,
        "visible_factor_count": visible_total,
        "hidden_factor_count": hidden_total,
        "relationship_contact_count": contact_count,
        "auxiliary_hit_count": auxiliary_count,
        "timing_hit_count": len(timing_hits),
        "summary": _area_summary(
            definition,
            factors=factors,
            palaces=palaces,
            timing_hits=timing_hits,
            context_state=context_state,
            element_balance=element_balance,
            calculation_sex=calculation_sex,
            relationship_total=relationship_total,
        ),
        "guidance": _area_guidance(definition, context_state),
        "topic_basis": definition["topic_basis"],
        "palace_basis": definition["palace_basis"],
        "signals": signals,
        "body_balance": body_balance,
    }


def _context_state(score: int, timing_hits: List[Dict[str, Any]], contact_count: int) -> str:
    if timing_hits:
        return "timing_active"
    if score >= 3 or contact_count >= 2:
        return "emphasized"
    if score > 0:
        return "context_required"
    return "quiet"


def _signals(
    definition: Dict[str, Any],
    factors: List[Dict[str, Any]],
    palaces: List[Dict[str, Any]],
    timing_hits: List[Dict[str, Any]],
    element_balance: Dict[str, Any],
) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    for factor in factors:
        signals.append({
            "type": "factor",
            "label": factor.get("factor"),
            "detail": f"visible {factor.get('visible_count', 0)} / hidden {factor.get('hidden_count', 0)}",
            "tone": "role",
        })
    for palace in palaces:
        count = int(palace.get("relationship_event_count") or 0)
        signals.append({
            "type": "palace",
            "label": palace.get("pillar_label") or str(palace.get("pillar") or "").title(),
            "detail": palace.get("outer_domain") or palace.get("domain"),
            "tone": "contact" if count else "placement",
        })
    for hit in timing_hits:
        signals.append({
            "type": "timing",
            "label": hit.get("label"),
            "detail": " ".join(str(part) for part in (hit.get("stem"), hit.get("branch"), hit.get("god")) if part),
            "tone": "activation",
        })
    if definition["id"] == "health_body":
        most_present, least_present = _element_extremes(element_balance)
        if most_present:
            signals.append({"type": "element", "label": "Most mentioned", "detail": most_present, "tone": "balance"})
        if least_present:
            signals.append({"type": "element", "label": "Least mentioned", "detail": least_present, "tone": "balance"})
    return signals


def _area_summary(
    definition: Dict[str, Any],
    *,
    factors: List[Dict[str, Any]],
    palaces: List[Dict[str, Any]],
    timing_hits: List[Dict[str, Any]],
    context_state: str,
    element_balance: Dict[str, Any],
    calculation_sex: Optional[str],
    relationship_total: int,
) -> str:
    if definition["id"] == "health_body":
        most_present, least_present = _element_extremes(element_balance)
        return (
            f"Traditional body-correspondence context notes most-mentioned element {most_present or '-'} "
            f"and least-mentioned element {least_present or '-'}. "
            "These are unweighted placement counts, not qi strength, excess, deficiency, or medical findings."
        )
    factor_names = ", ".join(str(factor.get("factor")) for factor in factors) or "no primary factor"
    palace_names = ", ".join(str(palace.get("pillar_label") or palace.get("pillar")) for palace in palaces) or "no direct palace"
    timing = f" {len(timing_hits)} timing layer(s) currently repeat this topic." if timing_hits else ""
    partner = ""
    if definition["id"] == "relationships_family":
        if calculation_sex == "male":
            partner = " Male-chart spouse convention watches Wealth alongside the Day Branch."
        elif calculation_sex == "female":
            partner = " Female-chart spouse convention watches Influence alongside the Day Branch."
        else:
            partner = " Spouse-star convention needs Calculation Sex before Wealth or Influence is emphasized as partner evidence."
        if relationship_total:
            partner += f" {relationship_total} relationship-contact event(s) are available for placement review."
    if context_state == "quiet":
        return f"{definition['label']} is quiet in the currently configured factors; keep it as background until timing or contacts activate it.{partner}"
    return f"{definition['label']} is mapped through {factor_names} and the {palace_names} palace context.{timing}{partner}"


def _area_guidance(definition: Dict[str, Any], context_state: str) -> str:
    if definition["id"] == "health_body":
        return ""
    if context_state == "timing_active":
        return "Timing repeats this topic now; judge it through strength, useful-element direction, and active contacts before making a ruling."
    if context_state == "emphasized":
        return "This topic has chart emphasis. Treat it as a reading priority, not as a guaranteed outcome."
    if context_state == "context_required":
        return "Evidence exists, but favorability and outcome require strength, useful-element, and timing context."
    return "No strong chart evidence is configured for this topic yet."


BODY_CORRESPONDENCE = {
    "Wood": {"systems": ["liver-gallbladder field", "tendons"], "tone": "growth and movement"},
    "Fire": {"systems": ["heart-small-intestine field", "blood warmth"], "tone": "warmth and circulation"},
    "Earth": {"systems": ["spleen-stomach field", "flesh and digestion"], "tone": "center and transformation"},
    "Metal": {"systems": ["lung-large-intestine field", "skin and breath"], "tone": "boundary and contraction"},
    "Water": {"systems": ["kidney-bladder field", "bones and fluids"], "tone": "storage and cooling"},
}


def _body_balance_evidence(
    pillars: Dict[str, Optional[Dict[str, Any]]],
    element_balance: Dict[str, Any],
    relationships: Dict[str, Any],
    timing_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    totals = (element_balance.get("counts") or element_balance.get("total")) if isinstance(element_balance, dict) else {}
    hidden = element_balance.get("hidden_stems") if isinstance(element_balance, dict) else {}
    totals = totals if isinstance(totals, dict) else {}
    hidden = hidden if isinstance(hidden, dict) else {}
    sorted_totals = sorted(((element, int(totals.get(element) or 0)) for element in BODY_CORRESPONDENCE), key=lambda item: (-item[1], item[0]))
    most_present = [element for element, count in sorted_totals if count == sorted_totals[0][1] and count > 0] if sorted_totals else []
    least_presence_count = min((count for _, count in sorted_totals), default=0)
    least_present = [element for element, count in sorted_totals if count == least_presence_count]
    day_hour_palaces = []
    for name in ("day", "hour"):
        pillar = pillars.get(name) if isinstance(pillars, dict) else None
        if isinstance(pillar, dict):
            day_hour_palaces.append({
                "pillar": name,
                "stem": pillar.get("stem"),
                "branch": pillar.get("branch"),
                "stem_element": pillar.get("stem_element"),
                "branch_element": pillar.get("branch_element"),
                "hidden_elements": [
                    row.get("element")
                    for row in pillar.get("hidden_stems") or []
                    if isinstance(row, dict) and row.get("element")
                ],
            })
    pressure_events = []
    for event in relationships.get("events") or []:
        if not isinstance(event, dict):
            continue
        affected = {str(item) for item in event.get("affected_palaces") or []}
        if affected & {"Day", "Hour"}:
            pressure_events.append({
                "label": event.get("label") or event.get("type"),
                "type": event.get("type"),
                "scope": event.get("scope"),
                "affected_palaces": sorted(affected),
            })
    timing_hits = [
        row for row in timing_rows
        if row.get("factor") in {"Resource", "Output", "Influence"}
    ]
    correspondences = [
        {
            "element": element,
            "count": int(totals.get(element) or 0),
            "hidden_count": int(hidden.get(element) or 0),
            **BODY_CORRESPONDENCE[element],
        }
        for element in BODY_CORRESPONDENCE
    ]
    signals = []
    for element in most_present[:2]:
        signals.append({"type": "body_presence", "label": f"{element} higher presence", "detail": BODY_CORRESPONDENCE[element]["tone"], "tone": "balance"})
    for element in least_present[:2]:
        signals.append({"type": "body_presence", "label": f"{element} lower presence", "detail": BODY_CORRESPONDENCE[element]["tone"], "tone": "balance"})
    if pressure_events:
        signals.append({"type": "body_contact", "label": "Day/Hour pressure", "detail": f"{len(pressure_events)} contact(s)", "tone": "contact"})
    if timing_hits:
        signals.append({"type": "body_timing", "label": "Timing repeats body-linked factors", "detail": f"{len(timing_hits)} layer(s)", "tone": "activation"})
    return {
        "status": "source_based_preview",
        "method": "element_presence_body_context_v2",
        "element_presence_model_id": element_balance.get("model_id") or "legacy_element_presence_counts",
        "element_presence_measure": element_balance.get("measure") or "unweighted_presence_count",
        "qi_strength_inferred": False,
        "hidden_stem_counts": dict(hidden),
        "element_counts": dict(totals),
        "element_presence_high": most_present,
        "element_presence_low": least_present,
        "element_excess": [],
        "element_absence": [element for element, count in sorted_totals if count == 0],
        "element_deficiency": [],
        "symbolic_body_correspondences": correspondences,
        "day_hour_palaces": day_hour_palaces,
        "palace_pressure": pressure_events[:6],
        "timing_activation": timing_hits[:6],
        "signals": signals,
        "limits": [
            "symbolic_body_correspondence_only",
            "unweighted_presence_not_qi_strength",
            "not_medical_guidance",
        ],
        "source_page_refs": ["lu_zhiji_fate_search:pp381-382", "lu_zhiji_bazi_advanced:pp150,199"],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _element_extremes(element_balance: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    counts = element_balance.get("counts") or element_balance.get("total") or {}
    if not isinstance(counts, dict) or not counts:
        return None, None
    rows = sorted(((str(element), int(value or 0)) for element, value in counts.items()), key=lambda item: (-item[1], item[0]))
    most_present = f"{rows[0][0]} x{rows[0][1]}" if rows else None
    least_row = sorted(rows, key=lambda item: (item[1], item[0]))[0] if rows else None
    least_present = f"{least_row[0]} x{least_row[1]}" if least_row else None
    return most_present, least_present
