from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

BENEFICS = {"Jupiter", "Venus", "Sun", "Moon"}
MALEFICS = {"Mars", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}


def _distance_weight(distance_km: Any, max_km: float = 500.0) -> float:
    try:
        value = max(0.0, float(distance_km))
    except Exception:
        return 0.0
    if value >= max_km:
        return 0.0
    return max(0.0, 1.0 - (value / max_km))


def _score_line_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    bodies: set[str],
    angles: Optional[set[str]] = None,
    multiplier: float = 1.0,
) -> float:
    total = 0.0
    angle_filter = {str(angle).upper() for angle in (angles or set()) if str(angle).strip()}
    for row in rows or []:
        body = str(row.get("body") or row.get("planet") or "").strip()
        angle = str(row.get("angle") or "").strip().upper()
        if body not in bodies:
            continue
        if angle_filter and angle not in angle_filter:
            continue
        total += _distance_weight(row.get("distance_km")) * float(multiplier)
    return total


def _score_crossings(
    crossings: Sequence[Dict[str, Any]],
    *,
    bodies: set[str],
    require_all: bool = False,
    multiplier: float = 1.0,
) -> float:
    total = 0.0
    for row in crossings or []:
        planets = {str(item).strip() for item in (row.get("planets") or []) if str(item).strip()}
        if not planets:
            continue
        if require_all:
            matches = planets.issubset(bodies)
        else:
            matches = bool(planets & bodies)
        if not matches:
            continue
        planet_factor = min(1.0, len(planets & bodies) / float(max(1, len(planets))))
        total += _distance_weight(row.get("distance_km")) * planet_factor * float(multiplier)
    return total


def _normalize_simple_score(raw_score: float) -> int:
    return int(round(max(0.0, min(100.0, 50.0 + (float(raw_score) * 14.0)))))


def _build_baseline_payload(
    baseline_id: str,
    label: str,
    *,
    raw_score: float,
    summary: str,
    score_polarity: str = "higher_is_better",
) -> Dict[str, Any]:
    return {
        "id": baseline_id,
        "label": label,
        "raw_score": round(float(raw_score), 4),
        "score": _normalize_simple_score(raw_score),
        "summary": summary,
        "score_polarity": score_polarity,
        "comparator_kind": "independent_heuristic",
        "independent_from_product_model": True,
    }


def _relocation_metric(relocation: Dict[str, Any], name: str) -> float:
    metrics = (relocation or {}).get("metrics") or {}
    try:
        return float(metrics.get(name) or 0.0)
    except Exception:
        return 0.0


def _score_specific_crossing_pairs(
    crossings: Sequence[Dict[str, Any]],
    *,
    pairs: Sequence[tuple[str, str]],
    multiplier: float = 1.0,
) -> float:
    total = 0.0
    normalized_pairs = {frozenset((a, b)) for a, b in pairs}
    for row in crossings or []:
        planets = {str(item).strip() for item in (row.get("planets") or []) if str(item).strip()}
        if frozenset(planets) not in normalized_pairs:
            continue
        total += _distance_weight(row.get("distance_km")) * float(multiplier)
    return total


def _score_benefic_minus_malefic(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    raw = _score_line_rows(natal_rows, bodies=BENEFICS, multiplier=1.0)
    raw -= _score_line_rows(natal_rows, bodies=MALEFICS, multiplier=1.0)
    raw += _score_crossings(natal_crossings, bodies=BENEFICS, multiplier=0.8)
    raw -= _score_crossings(natal_crossings, bodies=MALEFICS, multiplier=0.8)
    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=BENEFICS, multiplier=transit_multiplier)
        raw -= _score_line_rows(transit_rows, bodies=MALEFICS, multiplier=transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=BENEFICS, multiplier=0.8 * transit_multiplier)
        raw -= _score_crossings(transit_crossings, bodies=MALEFICS, multiplier=0.8 * transit_multiplier)
    return _build_baseline_payload(
        "benefic_minus_malefic",
        "Benefic Minus Malefic",
        raw_score=raw,
        summary="Simple benefic pressure minus malefic pressure across nearby lines and crossings.",
    )


def _score_jupiter_venus(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    core = {"Jupiter", "Venus"}
    support = {"Sun", "Mercury", "Moon"}
    raw = _score_line_rows(natal_rows, bodies=core, angles={"ASC", "MC", "DSC", "IC"}, multiplier=1.3)
    raw += _score_line_rows(natal_rows, bodies=support, multiplier=0.7)
    raw += _score_crossings(natal_crossings, bodies=core | support, multiplier=1.2)

    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=core, angles={"ASC", "MC", "DSC", "IC"}, multiplier=1.3 * transit_multiplier)
        raw += _score_line_rows(transit_rows, bodies=support, multiplier=0.7 * transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=core | support, multiplier=1.2 * transit_multiplier)

    return _build_baseline_payload(
        "jupiter_venus",
        "Jupiter Venus Heuristic",
        raw_score=raw,
        summary="Jupiter and Venus emphasis with light Sun, Mercury, and Moon support for speculative upside.",
    )


def _score_gambling_lines_only(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    core = {"Jupiter", "Venus", "Mercury", "Sun", "Moon"}
    cautions = {"Saturn", "Mars", "Neptune", "Pluto", "Uranus"}
    raw = _score_line_rows(natal_rows, bodies=core, multiplier=1.0)
    raw -= _score_line_rows(natal_rows, bodies=cautions, multiplier=0.75)
    raw += _score_crossings(natal_crossings, bodies=core, multiplier=0.9)
    raw -= _score_crossings(natal_crossings, bodies=cautions, multiplier=0.6)
    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=core, multiplier=transit_multiplier)
        raw -= _score_line_rows(transit_rows, bodies=cautions, multiplier=0.75 * transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=core, multiplier=0.9 * transit_multiplier)
        raw -= _score_crossings(transit_crossings, bodies=cautions, multiplier=0.6 * transit_multiplier)
    return _build_baseline_payload(
        "gambling_lines_only",
        "Gambling Lines Heuristic",
        raw_score=raw,
        summary="Independent benchmark heuristic using only gambling-related lines and crossings.",
    )


def _score_gambling_relocation_only(
    *,
    relocation: Dict[str, Any],
) -> Dict[str, Any]:
    raw = 1.6 * _relocation_metric(relocation, "gambling_activation")
    raw += 1.3 * _relocation_metric(relocation, "gambling_signature")
    raw += 0.8 * _relocation_metric(relocation, "speculation")
    raw += 0.6 * _relocation_metric(relocation, "money_support")
    raw -= 0.9 * _relocation_metric(relocation, "speculation_drag")
    return _build_baseline_payload(
        "gambling_relocation_only",
        "Gambling Relocation Heuristic",
        raw_score=raw,
        summary="Independent benchmark heuristic using only a compact relocation metric formula.",
    )


def _score_gambling_no_activation_floor(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    line_payload = _score_gambling_lines_only(
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        transit_rows=transit_rows,
        transit_crossings=transit_crossings,
        transit_multiplier=transit_multiplier,
    )
    relocation_payload = _score_gambling_relocation_only(relocation=relocation)
    raw = float(line_payload.get("raw_score") or 0.0) + float(
        relocation_payload.get("raw_score") or 0.0
    )
    return _build_baseline_payload(
        "gambling_no_activation_floor",
        "Gambling Combined Heuristic",
        raw_score=raw,
        summary="Independent benchmark heuristic combining the line and relocation comparators.",
    )


def _score_malefic_pressure(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    critical = {"Mars", "Saturn", "Uranus", "Pluto"}
    diffuse = {"Neptune", "Chiron"}
    raw = _score_line_rows(natal_rows, bodies=critical, angles={"ASC", "DSC", "MC", "IC"}, multiplier=1.4)
    raw += _score_line_rows(natal_rows, bodies=diffuse, multiplier=0.8)
    raw += _score_crossings(natal_crossings, bodies=critical | diffuse, multiplier=1.25)

    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=critical, angles={"ASC", "DSC", "MC", "IC"}, multiplier=1.4 * transit_multiplier)
        raw += _score_line_rows(transit_rows, bodies=diffuse, multiplier=0.8 * transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=critical | diffuse, multiplier=1.25 * transit_multiplier)

    return _build_baseline_payload(
        "malefic_pressure",
        "Malefic Pressure",
        raw_score=raw,
        summary="Simple malefic pressure heuristic across nearby lines and crossings.",
        score_polarity="higher_is_worse",
    )


def _score_accident_pressure(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    core = {"Mars", "Uranus", "Pluto"}
    secondary = {"Saturn", "Chiron"}
    raw = _score_line_rows(natal_rows, bodies=core, angles={"ASC", "MC", "DSC"}, multiplier=1.6)
    raw += _score_line_rows(natal_rows, bodies=secondary, angles={"ASC", "MC"}, multiplier=0.8)
    raw += _score_crossings(natal_crossings, bodies=core | secondary, multiplier=1.2)
    raw += 1.8 * _relocation_metric(relocation, "health_risk")
    raw += 1.0 * _relocation_metric(relocation, "conflict_pressure")
    raw += 0.7 * _relocation_metric(relocation, "malefic_pressure")
    if transit_rows:
        raw += _score_line_rows(
            transit_rows,
            bodies=core,
            angles={"ASC", "MC", "DSC"},
            multiplier=1.6 * transit_multiplier,
        )
        raw += _score_line_rows(
            transit_rows,
            bodies=secondary,
            angles={"ASC", "MC"},
            multiplier=0.8 * transit_multiplier,
        )
    if transit_crossings:
        raw += _score_crossings(
            transit_crossings,
            bodies=core | secondary,
            multiplier=1.2 * transit_multiplier,
        )
    return _build_baseline_payload(
        "accident_pressure",
        "Accident Pressure",
        raw_score=raw,
        summary="Research comparator for acute accident-prone places using Mars/Uranus/Pluto pressure plus bodily-risk relocation metrics.",
        score_polarity="higher_is_worse",
    )


def _score_hostile_places(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    harsh = {"Mars", "Saturn", "Pluto", "Uranus"}
    softeners = {"Venus", "Jupiter", "Moon"}
    raw = _score_line_rows(natal_rows, bodies=harsh, angles={"DSC", "MC"}, multiplier=1.55)
    raw += _score_line_rows(natal_rows, bodies={"Mars", "Pluto"}, angles={"ASC"}, multiplier=1.0)
    raw -= _score_line_rows(natal_rows, bodies=softeners, angles={"DSC", "IC"}, multiplier=1.0)
    raw += _score_crossings(natal_crossings, bodies=harsh, multiplier=1.1)
    raw += _score_specific_crossing_pairs(
        natal_crossings,
        pairs=(("Mars", "Pluto"), ("Mars", "Saturn"), ("Mars", "Uranus"), ("Saturn", "Pluto")),
        multiplier=1.35,
    )
    raw += (2.4 * _relocation_metric(relocation, "conflict_pressure"))
    raw += (1.5 * _relocation_metric(relocation, "malefic_pressure"))
    raw += (0.9 * _relocation_metric(relocation, "uncertainty"))
    raw -= (1.0 * _relocation_metric(relocation, "benefic_balance"))
    raw -= (0.8 * _relocation_metric(relocation, "stability"))

    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=harsh, angles={"DSC", "MC"}, multiplier=1.55 * transit_multiplier)
        raw += _score_line_rows(transit_rows, bodies={"Mars", "Pluto"}, angles={"ASC"}, multiplier=1.0 * transit_multiplier)
        raw -= _score_line_rows(transit_rows, bodies=softeners, angles={"DSC", "IC"}, multiplier=1.0 * transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=harsh, multiplier=1.1 * transit_multiplier)
        raw += _score_specific_crossing_pairs(
            transit_crossings,
            pairs=(("Mars", "Pluto"), ("Mars", "Saturn"), ("Mars", "Uranus"), ("Saturn", "Pluto")),
            multiplier=1.35 * transit_multiplier,
        )

    return _build_baseline_payload(
        "hostile_places",
        "Hostile Places",
        raw_score=raw,
        summary="Research comparator for openly adversarial, combative, or harsh places with Mars/Saturn/Pluto conflict signatures.",
        score_polarity="higher_is_worse",
    )


def _score_drain_breakdown(
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Any]:
    drainers = {"Saturn", "Neptune", "Pluto"}
    supports = {"Jupiter", "Venus", "Sun"}
    raw = _score_line_rows(natal_rows, bodies=drainers, angles={"IC", "ASC", "MC"}, multiplier=1.45)
    raw -= _score_line_rows(natal_rows, bodies=supports, angles={"ASC", "IC", "MC"}, multiplier=0.95)
    raw += _score_crossings(natal_crossings, bodies=drainers, multiplier=1.0)
    raw += _score_specific_crossing_pairs(
        natal_crossings,
        pairs=(("Saturn", "Neptune"), ("Saturn", "Pluto"), ("Neptune", "Pluto")),
        multiplier=1.5,
    )
    raw += (2.2 * _relocation_metric(relocation, "uncertainty"))
    raw += (1.5 * _relocation_metric(relocation, "malefic_pressure"))
    raw += (0.9 * _relocation_metric(relocation, "health_risk"))
    raw -= (1.8 * _relocation_metric(relocation, "stability"))
    raw -= (1.2 * _relocation_metric(relocation, "benefic_balance"))

    if transit_rows:
        raw += _score_line_rows(transit_rows, bodies=drainers, angles={"IC", "ASC", "MC"}, multiplier=1.45 * transit_multiplier)
        raw -= _score_line_rows(transit_rows, bodies=supports, angles={"ASC", "IC", "MC"}, multiplier=0.95 * transit_multiplier)
    if transit_crossings:
        raw += _score_crossings(transit_crossings, bodies=drainers, multiplier=1.0 * transit_multiplier)
        raw += _score_specific_crossing_pairs(
            transit_crossings,
            pairs=(("Saturn", "Neptune"), ("Saturn", "Pluto"), ("Neptune", "Pluto")),
            multiplier=1.5 * transit_multiplier,
        )

    return _build_baseline_payload(
        "drain_breakdown",
        "Drain / Breakdown",
        raw_score=raw,
        summary="Research comparator for draining, structurally weakening, or breakdown-prone places using Saturn/Neptune/Pluto signatures.",
        score_polarity="higher_is_worse",
    )


def _score_split_risk_max(
    *,
    accident_pressure: Dict[str, Any],
    hostile_places: Dict[str, Any],
    drain_breakdown: Dict[str, Any],
) -> Dict[str, Any]:
    dominant = max(
        (accident_pressure, hostile_places, drain_breakdown),
        key=lambda item: float(item.get("raw_score") or 0.0),
    )
    return _build_baseline_payload(
        "split_risk_max",
        "Subtype Max",
        raw_score=float(dominant.get("raw_score") or 0.0),
        summary=f"Maximum of the accident, hostile, and drain/breakdown research comparators. Dominant subtype: {dominant.get('label')}.",
        score_polarity="higher_is_worse",
    )


def compute_case_baselines(
    goal_id: str,
    *,
    natal_rows: Sequence[Dict[str, Any]],
    natal_crossings: Sequence[Dict[str, Any]],
    relocation: Dict[str, Any],
    transit_rows: Optional[Sequence[Dict[str, Any]]] = None,
    transit_crossings: Optional[Sequence[Dict[str, Any]]] = None,
    transit_multiplier: float = 0.35,
) -> Dict[str, Dict[str, Any]]:
    baselines: Dict[str, Dict[str, Any]] = {}

    baselines["benefic_minus_malefic"] = _score_benefic_minus_malefic(
        natal_rows=natal_rows,
        natal_crossings=natal_crossings,
        transit_rows=transit_rows,
        transit_crossings=transit_crossings,
        transit_multiplier=transit_multiplier,
    )

    if goal_id == "gambling_luck":
        baselines["jupiter_venus"] = _score_jupiter_venus(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["gambling_lines_only"] = _score_gambling_lines_only(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["gambling_relocation_only"] = _score_gambling_relocation_only(
            relocation=relocation,
        )
        baselines["gambling_no_activation_floor"] = _score_gambling_no_activation_floor(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
    elif goal_id in {"health_risk", "accident_prone"}:
        baselines["malefic_pressure"] = _score_malefic_pressure(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["accident_pressure"] = _score_accident_pressure(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
    elif goal_id == "risk_pressure":
        baselines["accident_pressure"] = _score_accident_pressure(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["hostile_places"] = _score_hostile_places(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["drain_breakdown"] = _score_drain_breakdown(
            natal_rows=natal_rows,
            natal_crossings=natal_crossings,
            relocation=relocation,
            transit_rows=transit_rows,
            transit_crossings=transit_crossings,
            transit_multiplier=transit_multiplier,
        )
        baselines["split_risk_max"] = _score_split_risk_max(
            accident_pressure=baselines["accident_pressure"],
            hostile_places=baselines["hostile_places"],
            drain_breakdown=baselines["drain_breakdown"],
        )

    return baselines
