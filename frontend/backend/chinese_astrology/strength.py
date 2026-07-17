from __future__ import annotations

from typing import Any, Dict, List, Optional

from .curation import confidence_tags
from .tables import CONTROLS, PRODUCES, STEMS


SEASON_BY_BRANCH = dict(zip(
    ("Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai", "Zi", "Chou"),
    ("Spring", "Spring", "Spring", "Summer", "Summer", "Summer", "Autumn", "Autumn", "Autumn", "Winter", "Winter", "Winter"),
))

_SEASON_STATES = [
    ("prosperous", 4.0),
    ("strong", 3.0),
    ("weak", -1.0),
    ("very weak", -3.0),
    ("dead", -4.0),
]

SEASON_ELEMENT_STATES = {
    "Spring": dict(zip(("Wood", "Fire", "Water", "Metal", "Earth"), _SEASON_STATES[:4] + [("out of season", -2.0)])),
    "Summer": dict(zip(("Fire", "Earth", "Wood", "Water", "Metal"), _SEASON_STATES)),
    "Autumn": dict(zip(("Metal", "Water", "Earth", "Fire", "Wood"), _SEASON_STATES)),
    "Winter": dict(zip(("Water", "Wood", "Metal", "Earth", "Fire"), _SEASON_STATES)),
}

PILLAR_ROOT_WEIGHT = {
    "day": 3.0,
    "hour": 2.0,
    "month": 2.0,
    "year": 1.0,
}

HIDDEN_STEM_RANK_WEIGHT = {
    1: 1.0,
    2: 0.65,
    3: 0.35,
}

STORAGE_BRANCHES = {"Chen", "Xu", "Chou", "Wei"}

AUGIER_STRENGTH_PAGE_REF = {
    "source_id": "local.four_pillars_strength",
    "path": "output/iching_private_corpus/ba-zi-the-four-pillars-of-destiny.pages.jsonl",
    "pages": [43, 44, 45, 46, 66],
}


def _inverse_lookup(mapping: Dict[str, str], target: str) -> Optional[str]:
    for key, value in mapping.items():
        if value == target:
            return key
    return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _branch_season(branch_key: Optional[str]) -> str:
    return SEASON_BY_BRANCH.get(str(branch_key or ""), "Unknown")


def _month_season_component(day_element: str, month: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    branch_key = month.get("branch") if month else None
    season = _branch_season(branch_key)
    state, score = SEASON_ELEMENT_STATES.get(season, {}).get(day_element, ("unknown", 0.0))
    note = None
    if day_element == "Earth" and score < -1.0:
        score = -1.0
        note = "Earth is treated as transition qi; severe seasonal weakness is capped in this model."
    return {
        "season": season,
        "month_branch": branch_key,
        "state": state,
        "score": score,
        "weighted_score": round(score * 0.7, 3),
        "note": note,
        "source_basis": "Season is the primary strength authority; branch phase and timing determine whether the Day Master has usable seasonal force.",
        "source_page_refs": [AUGIER_STRENGTH_PAGE_REF],
    }


def _hidden_elements(pillar: Optional[Dict[str, Any]]) -> List[str]:
    return [
        str(item.get("element"))
        for item in ((pillar or {}).get("hidden_stems") or [])
        if isinstance(item, dict) and item.get("element")
    ]


def _hidden_stem_rows(pillar: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = (pillar or {}).get("hidden_stems") or []
    return [row for row in rows if isinstance(row, dict)]


def _root_grade(score: float, normal_root: bool, secret_root: bool) -> str:
    if normal_root and secret_root and score >= 3.5:
        return "normal_and_secret_root"
    if normal_root and score >= 2.0:
        return "normal_root"
    if secret_root and score >= 1.4:
        return "secret_root"
    if score > 0.4:
        return "minor_root"
    return "rootless"


def _same_element_root_class(pillar_name: str, branch_key: str, rank: int) -> str:
    if branch_key in STORAGE_BRANCHES and rank > 1:
        return "storage_root"
    if pillar_name == "day":
        return "normal_root"
    if pillar_name == "hour":
        return "secret_root"
    if rank == 1:
        return "branch_main_root"
    return "residual_root"


def _root_component(day_element: str, pillars: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    resource_element = _inverse_lookup(PRODUCES, day_element)
    controlling_element = _inverse_lookup(CONTROLS, day_element)
    output_element = PRODUCES[day_element]
    wealth_element = CONTROLS[day_element]
    support = 0.0
    pressure = 0.0
    evidence: List[str] = []
    normal_root = False
    secret_root = False
    root_details: List[Dict[str, Any]] = []
    same_element_root_score = 0.0
    resource_root_score = 0.0
    control_pressure_score = 0.0
    drain_pressure_score = 0.0

    for pillar_name, pillar in pillars.items():
        if not pillar:
            continue
        branch_key = str(pillar.get("branch") or "")
        hidden_rows = _hidden_stem_rows(pillar)
        hidden = _hidden_elements(pillar)
        if not hidden:
            continue
        base_weight = PILLAR_ROOT_WEIGHT.get(pillar_name, 1.0)
        same_hits = 0
        resource_hits = 0
        control_hits = 0
        drain_hits = 0
        same_score = 0.0
        resource_score = 0.0
        control_score = 0.0
        drain_score = 0.0
        for index, hidden_stem in enumerate(hidden_rows, start=1):
            hidden_element = str(hidden_stem.get("element") or "")
            rank = int(hidden_stem.get("rank") or index)
            rank_weight = HIDDEN_STEM_RANK_WEIGHT.get(rank, 0.25)
            contribution = round(base_weight * rank_weight, 3)
            if hidden_element == day_element:
                same_hits += 1
                same_score += contribution
                root_class = _same_element_root_class(pillar_name, branch_key, rank)
                root_details.append({
                    "pillar": pillar_name,
                    "branch": branch_key,
                    "stem": hidden_stem.get("key") or hidden_stem.get("stem"),
                    "element": hidden_element,
                    "rank": rank,
                    "rank_weight": rank_weight,
                    "grade": "main_root" if rank == 1 else "residual_root",
                    "root_class": root_class,
                    "support_score": contribution,
                    "relationship": "same_element_root",
                })
            elif resource_element and hidden_element == resource_element:
                resource_hits += 1
                resource_score += contribution * 0.55
                root_details.append({
                    "pillar": pillar_name,
                    "branch": branch_key,
                    "stem": hidden_stem.get("key") or hidden_stem.get("stem"),
                    "element": hidden_element,
                    "rank": rank,
                    "rank_weight": rank_weight,
                    "grade": "resource_root",
                    "root_class": "resource_root",
                    "support_score": round(contribution * 0.55, 3),
                    "relationship": "resource_feeds_root",
                })
            elif controlling_element and hidden_element == controlling_element:
                control_hits += 1
                control_score += contribution * 0.75
            elif hidden_element in {output_element, wealth_element}:
                drain_hits += 1
                drain_score += contribution * 0.35

        if same_hits:
            support += same_score
            same_element_root_score += same_score
            if pillar_name == "day":
                normal_root = True
                evidence.append(f"{pillar_name.title()} branch hides {day_element}, giving the Day Master normal root.")
            elif pillar_name == "hour":
                secret_root = True
                evidence.append(f"{pillar_name.title()} branch hides {day_element}, giving the Day Master secret root.")
            else:
                evidence.append(f"{pillar_name.title()} branch hides {day_element}, giving direct root.")
        if resource_hits:
            support += resource_score
            resource_root_score += resource_score
            evidence.append(f"{pillar_name.title()} branch hides {resource_element}, feeding the Day Master root.")
        if control_hits:
            pressure += control_score
            control_pressure_score += control_score
            evidence.append(f"{pillar_name.title()} branch hides {controlling_element}, placing control pressure on the root.")
        if drain_hits:
            pressure += drain_score
            drain_pressure_score += drain_score

    delta = support - pressure
    root_score = _clamp(delta, -4.0, 4.0)
    grade = _root_grade(root_score, normal_root, secret_root)
    return {
        "support": round(support, 3),
        "pressure": round(pressure, 3),
        "score": round(root_score, 3),
        "weighted_score": round(root_score * 0.25, 3),
        "root_grade": grade,
        "root_details": root_details,
        "same_element_root_score": round(same_element_root_score, 3),
        "resource_root_score": round(resource_root_score, 3),
        "control_pressure_score": round(control_pressure_score, 3),
        "drain_pressure_score": round(drain_pressure_score, 3),
        "normal_root": normal_root,
        "secret_root": secret_root,
        "evidence": evidence,
        "source_basis": "Hidden-stem roots are graded by pillar place and hidden-stem rank: Day branch normal root, Hour branch secret root, and lower-ranked residues count less than main qi.",
        "source_page_refs": [AUGIER_STRENGTH_PAGE_REF],
    }


def _gain_status_from_season(score: float) -> str:
    if score >= 3.0:
        return "gained"
    if score > 0:
        return "partial"
    if score < 0:
        return "lost"
    return "unknown"


def _gain_status_from_root(root: Dict[str, Any]) -> str:
    same_score = float(root.get("same_element_root_score") or 0.0)
    resource_score = float(root.get("resource_root_score") or 0.0)
    if same_score >= 2.0:
        return "gained"
    if same_score > 0:
        return "partial"
    if resource_score > 0:
        return "resource_only"
    return "rootless"


def _gain_status_from_formation(formation: Dict[str, Any]) -> str:
    score = float(formation.get("score") or 0.0)
    if score >= 1.0:
        return "gained"
    if score > 0:
        return "partial"
    if score <= -1.0:
        return "opposed"
    return "neutral"


def _strength_band(weighted_score: float, label: str) -> str:
    if weighted_score >= 2.4:
        return "too_strong"
    if weighted_score <= -2.1:
        return "too_weak"
    if -0.65 <= weighted_score <= 0.65:
        return "neutral"
    return str(label or "uncertain").replace(" ", "_")


def _root_grade_evidence(
    *,
    day_element: str,
    season: Dict[str, Any],
    root: Dict[str, Any],
    formation: Dict[str, Any],
    weighted_score: float,
    label: str,
) -> Dict[str, Any]:
    same_score = float(root.get("same_element_root_score") or 0.0)
    resource_score = float(root.get("resource_root_score") or 0.0)
    same_side_support = float(root.get("support") or 0.0) + float(formation.get("support") or 0.0)
    opposing_pressure = float(root.get("pressure") or 0.0) + float(formation.get("pressure") or 0.0)
    resource_limit_active = resource_score > 0 and same_score <= 0
    evidence_rows = [
        (
            f"De Ling: month branch {season.get('month_branch') or '-'} gives {day_element} "
            f"{season.get('state') or 'unknown'} seasonal qi."
        )
    ]
    for detail in root.get("root_details") or []:
        if not isinstance(detail, dict) or detail.get("relationship") != "same_element_root":
            continue
        evidence_rows.append(
            f"De Di: {str(detail.get('pillar') or '').title()} {detail.get('branch') or '-'} hides "
            f"{detail.get('stem') or day_element} at hidden-stem rank {detail.get('rank')}; "
            f"{str(detail.get('root_class') or 'root').replace('_', ' ')} contributes {detail.get('support_score')}."
        )
    if resource_limit_active:
        evidence_rows.append("Resource support is present, but Resource does not fully replace a real root.")
    evidence_rows.append(
        f"De Zhu: visible and branch formation support {round(float(formation.get('support') or 0.0), 3)} "
        f"against pressure {round(float(formation.get('pressure') or 0.0), 3)}."
    )
    return {
        "method": "root_grade_evidence_v1",
        "de_ling": {
            "status": _gain_status_from_season(float(season.get("score") or 0.0)),
            "season": season.get("season"),
            "month_branch": season.get("month_branch"),
            "state": season.get("state"),
            "score": season.get("score"),
            "evidence": evidence_rows[0],
        },
        "de_di": {
            "status": _gain_status_from_root(root),
            "root_grade": root.get("root_grade"),
            "normal_root": root.get("normal_root"),
            "secret_root": root.get("secret_root"),
            "same_element_root_score": round(same_score, 3),
            "resource_root_score": round(resource_score, 3),
            "evidence": "Same-element hidden-stem roots are weighted above resource support.",
        },
        "de_zhu": {
            "status": _gain_status_from_formation(formation),
            "support": formation.get("support"),
            "pressure": formation.get("pressure"),
            "evidence": evidence_rows[-1],
        },
        "same_side_support": round(same_side_support, 3),
        "opposing_pressure": round(opposing_pressure, 3),
        "resource_substitute_limit": {
            "active": resource_limit_active,
            "note": (
                "Resource does not fully replace a real root."
                if resource_limit_active
                else "Resource support remains discounted relative to same-element roots."
            ),
        },
        "strength_band": _strength_band(weighted_score, label),
        "evidence_rows": evidence_rows,
        "source_basis": (
            "Root-grade evidence separates de ling (season), de di (root/place), and de zhu "
            "visible support before the coarse strong/weak label is used."
        ),
        "source_page_refs": [AUGIER_STRENGTH_PAGE_REF],
    }


def _formation_component(day_element: str, pillars: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    resource_element = _inverse_lookup(PRODUCES, day_element)
    controlling_element = _inverse_lookup(CONTROLS, day_element)
    output_element = PRODUCES[day_element]
    wealth_element = CONTROLS[day_element]
    support = 0.0
    pressure = 0.0
    evidence: List[str] = []
    branch_elements = [
        pillar.get("branch_element")
        for pillar in pillars.values()
        if pillar and pillar.get("branch_element")
    ]

    for pillar_name, pillar in pillars.items():
        if not pillar or pillar_name == "day":
            continue
        stem_element = pillar.get("stem_element")
        if stem_element == day_element:
            support += 1.0
        elif stem_element == resource_element:
            support += 0.8
        elif stem_element == controlling_element:
            pressure += 1.0
        elif stem_element in {output_element, wealth_element}:
            pressure += 0.5

    same_branches = branch_elements.count(day_element)
    resource_branches = branch_elements.count(resource_element) if resource_element else 0
    if same_branches >= 2:
        support += 0.6
        evidence.append(f"{same_branches} branch bodies share the Day Master element.")
    if resource_branches >= 2:
        support += 0.5
        evidence.append(f"{resource_branches} branch bodies produce the Day Master element.")

    delta = support - pressure
    return {
        "support": round(support, 3),
        "pressure": round(pressure, 3),
        "score": round(_clamp(delta, -4.0, 4.0), 3),
        "weighted_score": round(_clamp(delta, -4.0, 4.0) * 0.05, 3),
        "evidence": evidence,
        "source_basis": "Formation checks what supports or pressures the Day Master across the eight palaces, visible stems, branch bodies, and hidden stems.",
        "source_page_refs": [AUGIER_STRENGTH_PAGE_REF],
    }


def evaluate_day_master_strength(
    day_stem_index: int,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    balance: Dict[str, Any],
) -> Dict[str, Any]:
    day_element = STEMS[int(day_stem_index) % 10]["element"]
    season = _month_season_component(day_element, pillars.get("month"))
    root = _root_component(day_element, pillars)
    formation = _formation_component(day_element, pillars)
    weighted_score = season["weighted_score"] + root["weighted_score"] + formation["weighted_score"]

    if weighted_score >= 1.65:
        label = "strong"
    elif weighted_score <= -1.35:
        label = "weak"
    elif -0.65 <= weighted_score <= 0.65:
        label = "balanced"
    else:
        label = "uncertain"

    support_score = max(0.0, season["score"]) + root["support"] + formation["support"]
    pressure_score = max(0.0, -season["score"]) + root["pressure"] + formation["pressure"]
    evidence = [
        f"Month branch {season.get('month_branch') or '-'} places {day_element} in {season['season']} season as {season['state']}."
    ]
    if season.get("note"):
        evidence.append(str(season["note"]))
    evidence.extend(root["evidence"][:4])
    evidence.extend(formation["evidence"][:2])
    if not root["evidence"]:
        evidence.append("No direct Day Master root was found in the hidden stems.")

    confidence = "medium"
    if abs(weighted_score) < 0.9 or label == "uncertain":
        confidence = "low"
    if abs(weighted_score) >= 2.4 and (root["normal_root"] or root["secret_root"]):
        confidence = "high"
    root_grade_evidence = _root_grade_evidence(
        day_element=day_element,
        season=season,
        root=root,
        formation=formation,
        weighted_score=weighted_score,
        label=label,
    )

    return {
        "label": label,
        "support_score": round(support_score, 3),
        "pressure_score": round(pressure_score, 3),
        "weighted_score": round(weighted_score, 3),
        "evidence": evidence,
        "method": "season_root_formation_v2",
        "model": {
            "method": "season_root_formation_v2",
            "model_id": "augier_school_heuristic_70_25_5_v1",
            "model_status": "product_defined_uncalibrated",
            "source_weighting": {"season": 0.7, "root": 0.25, "formation": 0.05},
            "architecture_provenance": (
                "Augier pp. 43-46 supplies the Season 70% / Root 25% / Formation 5% "
                "architecture and the Day normal-root / Hour secret-root distinction."
            ),
            "parameter_provenance": {
                "season_state_scores": "product_defined",
                "pillar_root_weights": {
                    "status": "product_defined",
                    "values": dict(PILLAR_ROOT_WEIGHT),
                },
                "hidden_stem_rank_weights": {
                    "status": "product_defined",
                    "values": dict(HIDDEN_STEM_RANK_WEIGHT),
                },
                "resource_control_drain_coefficients": {
                    "status": "product_defined",
                    "values": {"resource": 0.55, "control": 0.75, "drain": 0.35},
                },
                "classification_thresholds": {
                    "status": "product_defined",
                    "values": {
                        "strong_min": 1.65,
                        "weak_max": -1.35,
                        "balanced_min": -0.65,
                        "balanced_max": 0.65,
                    },
                },
            },
            "earth_reconciliation_policy": {
                "status": "school_ambiguity_product_policy",
                "rule": "Seasonal Earth scores below -1.0 are capped at -1.0.",
                "note": (
                    "The selected source's Earth prose and adjacent seasonal table conflict; "
                    "the cap is a product reconciliation, not a literal traditional constant."
                ),
            },
            "season": season,
            "root": root,
            "formation": formation,
            "root_grade_evidence": root_grade_evidence,
            "weighted_score": round(weighted_score, 3),
            "confidence": confidence,
            "source_basis": (
                "Augier supplies the 70/25/5 architecture and named root distinctions. "
                "Season values, pillar/rank weights, relationship coefficients, thresholds, "
                "and the Earth cap are explicit product-defined heuristic parameters."
            ),
            "source_keywords": [
                "Day Master",
                "season",
                "month branch",
                "normal root",
                "secret root",
                "root grade",
                "de ling",
                "de di",
                "de zhu",
                "hidden stems",
                "hidden-stem rank",
                "storage root",
                "resource does not replace root",
                "formation",
                "eight palaces",
            ],
            "source_page_refs": [AUGIER_STRENGTH_PAGE_REF],
            "source_confidence": confidence_tags("local_source", "provisional_model", "needs_validation"),
        },
        "balance_counts": balance.get("total") or {},
    }
