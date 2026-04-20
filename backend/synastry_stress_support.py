from __future__ import annotations

import copy
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import synastry_engine
from synastry_engine import build_synastry_report


SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

PLANET_ORDER = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
    "Chiron",
)

PLANET_SPEEDS = {
    "Sun": 0.9856,
    "Moon": 13.176,
    "Mercury": 1.2,
    "Venus": 1.05,
    "Mars": 0.55,
    "Jupiter": 0.083,
    "Saturn": 0.033,
    "Uranus": 0.012,
    "Neptune": 0.006,
    "Pluto": 0.004,
    "North Node": -0.053,
    "Chiron": 0.019,
}

EXPECTED_CATEGORY_IDS = (
    "overall",
    "resonance",
    "communication",
    "attraction",
    "compatibility",
    "attachment",
    "growth",
    "friction",
    "burden",
)


def _norm360(value: float) -> float:
    return float(value) % 360.0


def _sign_from_longitude(lon: float) -> str:
    return SIGNS[int(_norm360(lon) // 30.0) % 12]


def _equal_house_cusps(ascendant: float) -> List[float]:
    base = _norm360(ascendant)
    return [round(_norm360(base + (30.0 * index)), 6) for index in range(12)]


def _longitude_in_arc(start: float, end: float, point: float) -> bool:
    start = _norm360(start)
    end = _norm360(end)
    point = _norm360(point)
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _house_of_longitude(lon: float, cusps: Sequence[float]) -> int:
    for idx in range(12):
        if _longitude_in_arc(cusps[idx], cusps[(idx + 1) % 12], lon):
            return idx + 1
    return 12


def _planet_row(name: str, lon: float, cusps: Sequence[float], speed: float) -> Dict[str, Any]:
    normalized_lon = round(_norm360(lon), 6)
    row = {
        "planet": name,
        "longitude": normalized_lon,
        "sign": _sign_from_longitude(normalized_lon),
        "house": _house_of_longitude(normalized_lon, cusps),
        "speed": round(float(speed), 6),
        "retrograde": float(speed) < 0.0,
    }
    return row


def _build_chart(seed: int, variant: int) -> Dict[str, Any]:
    rng = random.Random((seed * 1009) + (variant * 9173))
    ascendant = round(rng.uniform(0.0, 359.999), 6)
    midheaven = round(_norm360(ascendant + 90.0 + rng.uniform(-15.0, 15.0)), 6)
    cusps = _equal_house_cusps(ascendant)

    planets: List[Dict[str, Any]] = []
    cluster_anchor = _norm360(ascendant + rng.uniform(45.0, 130.0))
    cluster_mode = ((seed + variant) % 4) == 0
    for index, name in enumerate(PLANET_ORDER):
        if cluster_mode and index < 4:
            longitude = _norm360(cluster_anchor + (index * 11.0) + rng.uniform(-2.5, 2.5))
        else:
            longitude = _norm360(rng.uniform(0.0, 359.999))
        speed = PLANET_SPEEDS[name]
        if name not in {"Sun", "Moon"}:
            wobble = abs(speed) * 0.35 if speed else 0.01
            speed += rng.uniform(-wobble, wobble)
        if name in {"Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"} and rng.random() < 0.2:
            speed = -abs(speed)
        planets.append(_planet_row(name, longitude, cusps, speed))

    return {
        "ascendant": ascendant,
        "midheaven": midheaven,
        "houses": cusps,
        "planets": planets,
    }


def clone_chart_data(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(chart_data)


def make_equal_house_chart(
    ascendant: float,
    planet_longitudes: Dict[str, float],
    *,
    midheaven: Optional[float] = None,
    speed_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    cusps = _equal_house_cusps(ascendant)
    mc = _norm360(ascendant + 90.0) if midheaven is None else _norm360(midheaven)
    speeds = dict(PLANET_SPEEDS)
    speeds.update(speed_overrides or {})
    planets = [
        _planet_row(name, longitude, cusps, speeds.get(name, 0.1))
        for name, longitude in planet_longitudes.items()
    ]
    return {
        "ascendant": round(_norm360(ascendant), 6),
        "midheaven": round(mc, 6),
        "houses": cusps,
        "planets": planets,
    }


def _find_planet(chart: Dict[str, Any], name: str) -> Dict[str, Any]:
    for row in chart.get("planets") or []:
        if str(row.get("planet")) == name:
            return row
    raise KeyError(f"Missing planet row for {name}")


def _reposition_planet(chart: Dict[str, Any], name: str, longitude: float) -> None:
    cusps = chart.get("houses") or []
    row = _find_planet(chart, name)
    normalized_lon = round(_norm360(longitude), 6)
    row["longitude"] = normalized_lon
    row["sign"] = _sign_from_longitude(normalized_lon)
    row["house"] = _house_of_longitude(normalized_lon, cusps)


def _apply_seeded_contacts(seed: int, chart_a: Dict[str, Any], chart_b: Dict[str, Any]) -> None:
    sun_a = float(_find_planet(chart_a, "Sun")["longitude"])
    moon_a = float(_find_planet(chart_a, "Moon")["longitude"])
    mars_a = float(_find_planet(chart_a, "Mars")["longitude"])
    saturn_a = float(_find_planet(chart_a, "Saturn")["longitude"])
    node_a = float(_find_planet(chart_a, "North Node")["longitude"])

    _reposition_planet(chart_b, "Sun", moon_a + 120.0 + ((seed % 3) * 0.22))
    _reposition_planet(chart_b, "Venus", mars_a + ((seed % 4) * 0.18))
    _reposition_planet(chart_b, "Saturn", sun_a + 90.0 + ((seed % 5) * 0.16))
    _reposition_planet(chart_b, "North Node", saturn_a + 60.0 + ((seed % 2) * 0.35))
    _reposition_planet(chart_b, "Chiron", node_a + 180.0 - ((seed % 4) * 0.2))


def _bundle(chart_data: Dict[str, Any], seed: int, label: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bundle = {"chart_data": chart_data, "meta": {"seed": seed, "label": label}}
    chart = {
        "id": f"{label.lower()}-{seed}",
        "label": label,
        "effective_datetime": f"2026-04-{(seed % 28) + 1:02d}T12:00:00+00:00",
        "location": f"Seed {seed} {label}",
    }
    return bundle, chart


def make_seeded_pair(seed: int) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    chart_data_a = _build_chart((seed * 2) + 1, variant=0)
    chart_data_b = _build_chart((seed * 2) + 2, variant=1)
    _apply_seeded_contacts(seed, chart_data_a, chart_data_b)
    bundle_a, chart_a = _bundle(chart_data_a, seed, "Chart A")
    bundle_b, chart_b = _bundle(chart_data_b, seed, "Chart B")
    return bundle_a, bundle_b, chart_a, chart_b


def sample_chart_a() -> Dict[str, Any]:
    return {
        "ascendant": 0.0,
        "midheaven": 270.0,
        "houses": [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        "planets": [
            {"planet": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1},
            {"planet": "Moon", "longitude": 102.0, "sign": "Cancer", "house": 4},
            {"planet": "Mercury", "longitude": 70.0, "sign": "Gemini", "house": 3},
            {"planet": "Venus", "longitude": 14.0, "sign": "Aries", "house": 1},
            {"planet": "Mars", "longitude": 130.0, "sign": "Leo", "house": 5},
            {"planet": "Jupiter", "longitude": 252.0, "sign": "Sagittarius", "house": 9},
            {"planet": "Saturn", "longitude": 311.0, "sign": "Aquarius", "house": 11},
            {"planet": "Uranus", "longitude": 132.0, "sign": "Leo", "house": 5},
            {"planet": "North Node", "longitude": 188.0, "sign": "Libra", "house": 7},
            {"planet": "Chiron", "longitude": 42.0, "sign": "Taurus", "house": 2},
        ],
    }


def sample_chart_b() -> Dict[str, Any]:
    return {
        "ascendant": 180.0,
        "midheaven": 90.0,
        "houses": [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0],
        "planets": [
            {"planet": "Sun", "longitude": 132.0, "sign": "Leo", "house": 11},
            {"planet": "Moon", "longitude": 188.0, "sign": "Libra", "house": 1},
            {"planet": "Mercury", "longitude": 73.0, "sign": "Gemini", "house": 9},
            {"planet": "Venus", "longitude": 43.0, "sign": "Taurus", "house": 8},
            {"planet": "Mars", "longitude": 44.0, "sign": "Taurus", "house": 8},
            {"planet": "Jupiter", "longitude": 15.0, "sign": "Aries", "house": 7},
            {"planet": "Saturn", "longitude": 101.0, "sign": "Cancer", "house": 10},
            {"planet": "Neptune", "longitude": 102.0, "sign": "Cancer", "house": 10},
            {"planet": "Pluto", "longitude": 12.0, "sign": "Aries", "house": 7},
            {"planet": "North Node", "longitude": 311.0, "sign": "Aquarius", "house": 5},
            {"planet": "Chiron", "longitude": 14.0, "sign": "Aries", "house": 7},
        ],
    }


def build_report_from_chart_data(
    chart_data_a: Dict[str, Any],
    chart_data_b: Dict[str, Any],
    *,
    label_a: str = "Chart A",
    label_b: str = "Chart B",
    **options: Any,
) -> Dict[str, Any]:
    synastry_engine._load_catalog.cache_clear()
    bundle_a = {"chart_data": clone_chart_data(chart_data_a), "meta": {"label": label_a}}
    bundle_b = {"chart_data": clone_chart_data(chart_data_b), "meta": {"label": label_b}}
    chart_a = {"id": label_a.lower().replace(" ", "-"), "label": label_a, "effective_datetime": "2026-04-03T12:00:00+00:00", "location": label_a}
    chart_b = {"id": label_b.lower().replace(" ", "-"), "label": label_b, "effective_datetime": "2026-04-03T12:00:00+00:00", "location": label_b}
    return build_synastry_report(bundle_a, bundle_b, chart_a, chart_b, options=options or None)


def build_report_from_seed(seed: int, swap: bool = False, **options: Any) -> Dict[str, Any]:
    synastry_engine._load_catalog.cache_clear()
    bundle_a, bundle_b, chart_a, chart_b = make_seeded_pair(seed)
    if swap:
        bundle_a, bundle_b = bundle_b, bundle_a
        chart_a, chart_b = chart_b, chart_a
    return build_synastry_report(bundle_a, bundle_b, chart_a, chart_b, options=options or None)


def build_curated_report(**options: Any) -> Dict[str, Any]:
    synastry_engine._load_catalog.cache_clear()
    bundle_a = {"chart_data": sample_chart_a(), "meta": {"label": "Chart A"}}
    bundle_b = {"chart_data": sample_chart_b(), "meta": {"label": "Chart B"}}
    chart_a = {"id": "A", "label": "Chart A", "effective_datetime": "2026-04-02T10:00:00+00:00", "location": "A"}
    chart_b = {"id": "B", "label": "Chart B", "effective_datetime": "2026-04-02T10:00:00+00:00", "location": "B"}
    return build_synastry_report(bundle_a, bundle_b, chart_a, chart_b, options=options or None)


def category_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("id")): item for item in report.get("categories") or []}


def set_planet_longitude(chart_data: Dict[str, Any], name: str, longitude: float) -> None:
    _reposition_planet(chart_data, name, longitude)


def planet_longitude(chart_data: Dict[str, Any], name: str) -> float:
    return float(_find_planet(chart_data, name)["longitude"])


def find_aspect_hit(report: Dict[str, Any], point_a: str, point_b: str, aspect: str) -> Optional[Dict[str, Any]]:
    target_pair = {point_a, point_b}
    for item in report.get("aspect_links") or []:
        if {str(item.get("point_a") or ""), str(item.get("point_b") or "")} == target_pair and str(item.get("aspect") or "") == aspect:
            return item
    return None


def report_has_rule(report: Dict[str, Any], rule_id: str) -> bool:
    return str(rule_id) in set(report.get("governance", {}).get("active_rule_family_ids") or [])


def rule_evidence_deltas(report: Dict[str, Any], rule_id: str) -> List[float]:
    deltas: List[float] = []
    for category in report.get("categories") or []:
        for item in category.get("evidence_items") or []:
            if str(item.get("rule_family_id") or "") == str(rule_id):
                deltas.append(round(float(item.get("delta") or 0.0), 6))
    return sorted(deltas, reverse=True)


def load_rule_catalog() -> Dict[str, Any]:
    synastry_engine._load_catalog.cache_clear()
    return synastry_engine._load_catalog()


def canonical_aspect_signatures(report: Dict[str, Any]) -> List[Tuple[str, Tuple[str, str], float]]:
    signatures = []
    for item in report.get("aspect_links") or []:
        pair = tuple(sorted((str(item.get("point_a") or ""), str(item.get("point_b") or ""))))
        signatures.append((str(item.get("aspect") or ""), pair, round(float(item.get("orb") or 0.0), 3)))
    return sorted(signatures)


def _assert_sorted_desc(values: Iterable[float]) -> None:
    numbers = list(values)
    assert numbers == sorted(numbers, reverse=True)


def assert_report_invariants(report: Dict[str, Any]) -> None:
    assert "summary" in report
    assert "governance" in report
    assert "categories" in report
    assert "top_supportive_links" in report
    assert "top_challenging_links" in report
    assert "aspect_links" in report
    assert "sources" in report
    assert "options" in report

    categories = category_map(report)
    assert tuple(categories.keys()) == EXPECTED_CATEGORY_IDS

    for category_id in EXPECTED_CATEGORY_IDS:
        category = categories[category_id]
        score = float(category.get("score") or 0.0)
        assert math.isfinite(score)
        assert 0.0 <= score <= 100.0
        if category_id == "overall":
            components = category.get("components")
            assert isinstance(components, dict)
            for key in (
                "compatibility",
                "binding",
                "growth",
                "support_balance",
                "challenge",
                "positive_impact_total",
                "negative_impact_total",
                "reception_bonus",
                "legacy_weighted_total",
                "headline_weighted_total",
                "headline_normalized_total",
            ):
                value = float(components.get(key) or 0.0)
                assert math.isfinite(value)
            assert str(components.get("headline_model") or "").strip()
            normalization = dict(components.get("headline_normalization") or {})
            assert str(normalization.get("method") or "").strip()
            category_scores = dict(components.get("category_scores") or {})
            assert category_scores
            for key in EXPECTED_CATEGORY_IDS[1:]:
                assert math.isfinite(float(category_scores.get(key) or 0.0))
            evidence_items = category.get("evidence_items") or []
        else:
            assert category.get("polarity") in {"positive", "negative"}
            evidence_items = category.get("evidence_items") or []

        for item in evidence_items:
            assert str(item.get("detail") or "").strip()
            assert math.isfinite(float(item.get("delta") or 0.0))
            assert str(item.get("source") or "").strip()
            assert str(item.get("source_anchor") or "").strip()
            assert str(item.get("rule_family_id") or "").strip()

    summary = report["summary"]
    for key in ("overall_score", "supportive_link_count", "challenging_link_count", "mutual_reception_count"):
        assert math.isfinite(float(summary.get(key) or 0.0))
    assert isinstance(summary.get("summary_lines"), list)
    assert isinstance(summary.get("overall_components"), dict)

    governance = report["governance"]
    for key in ("active_rule_family_ids", "active_source_keys", "active_points"):
        values = list(governance.get(key) or [])
        assert values == sorted(set(values))
    assert str(governance.get("catalog_version") or "").strip()
    assert str(governance.get("orb_profile") or "").strip()

    supportive = report.get("top_supportive_links") or []
    challenging = report.get("top_challenging_links") or []
    _assert_sorted_desc(float(item.get("impact") or 0.0) for item in supportive)
    _assert_sorted_desc(float(item.get("impact") or 0.0) for item in challenging)

    for item in [*supportive, *challenging]:
        assert str(item.get("detail") or "").strip()
        assert str(item.get("source") or "").strip()
        assert str(item.get("source_anchor") or "").strip()
        assert str(item.get("rule_family_id") or "").strip()
        assert math.isfinite(float(item.get("impact") or 0.0))
