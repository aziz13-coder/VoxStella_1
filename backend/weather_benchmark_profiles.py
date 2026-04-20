from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import logging
from typing import Any, Dict, Iterable

from weather_benchmark_runner import DEFAULT_DATASET_PATHS, load_benchmark_cases

logger = logging.getLogger(__name__)


_DOCTRINE_KEYWORD_FAMILY_MAP: dict[str, set[str]] = {
    "flood": {"floods"},
    "floods": {"floods"},
    "hurricane": {"hurricanes"},
    "hurricanes": {"hurricanes"},
    "storms": {"hurricanes", "thunderstorms_tornadoes"},
    "tornado": {"thunderstorms_tornadoes"},
    "tornadoes": {"thunderstorms_tornadoes"},
    "thunderstorm": {"thunderstorms_tornadoes"},
    "thunderstorms": {"thunderstorms_tornadoes"},
    "hail": {"thunderstorms_tornadoes"},
    "severe_convective": {"thunderstorms_tornadoes"},
    "wind": {"wind"},
    "front": {"wind"},
    "fronts": {"wind"},
    "drought": {"drought"},
    "snow": {"snow_freezing_precipitation"},
    "freezing_rain": {"snow_freezing_precipitation"},
    "freezing_precipitation": {"snow_freezing_precipitation"},
    "blizzard": {"snow_freezing_precipitation"},
    "heat": {"temperature_extremes"},
    "cold_wave": {"temperature_extremes"},
    "temperature_extremes": {"temperature_extremes"},
    "seasonal_temperature": {"generalized_seasonal_temperature"},
}

_BRANCH_WIDE_DOCTRINE_AREAS = {"weather_framework", "weather_locality"}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _source_alignment_target_families(
    case: Dict[str, Any],
    *,
    known_families: Iterable[str],
) -> set[str]:
    families = {str(family_id or "").strip().lower() for family_id in known_families if str(family_id or "").strip()}
    if not families:
        return set()

    matched: set[str] = set()
    haystacks = [
        _normalize_text(case.get("case_id")),
        _normalize_text(case.get("doctrine_area")),
        _normalize_text(case.get("label")),
        *(_normalize_text(tag) for tag in (case.get("tags") or [])),
        *(_normalize_text(entry) for entry in (case.get("expected_conclusions") or [])),
    ]
    combined = " ".join(part for part in haystacks if part)
    for keyword, family_ids in _DOCTRINE_KEYWORD_FAMILY_MAP.items():
        if keyword in combined:
            matched.update(family_id for family_id in family_ids if family_id in families)

    doctrine_area = _normalize_text(case.get("doctrine_area"))
    if matched:
        return matched
    if doctrine_area in _BRANCH_WIDE_DOCTRINE_AREAS:
        return set(families)
    return set()


def _coverage_tier(unique_case_count: int, source_count: int) -> str:
    if unique_case_count >= 4 and source_count >= 3:
        return "broad"
    if unique_case_count >= 3 and source_count >= 2:
        return "supported"
    if unique_case_count >= 2:
        return "moderate"
    return "seeded"


@lru_cache(maxsize=1)
def build_weather_family_profiles() -> Dict[str, Dict[str, Any]]:
    try:
        cases, _ = load_benchmark_cases(DEFAULT_DATASET_PATHS)
    except FileNotFoundError as exc:
        logger.warning("Weather benchmark datasets unavailable; using seeded fallback profiles: %s", exc)
        return {}

    family_case_ids: dict[str, set[str]] = defaultdict(set)
    family_dataset_rows: Counter[str] = Counter()
    family_source_titles: dict[str, set[str]] = defaultdict(set)
    family_historical_source_titles: dict[str, set[str]] = defaultdict(set)
    family_doctrine_source_titles: dict[str, set[str]] = defaultdict(set)
    family_benchmark_types: dict[str, Counter[str]] = defaultdict(Counter)
    family_chart_basis: dict[str, Counter[str]] = defaultdict(Counter)

    for case in cases:
        if str(case.get("_dataset_kind") or "") != "historical":
            continue

        family_id = str(case.get("weather_family_id") or "").strip().lower()
        if not family_id:
            continue

        case_id = str(case.get("case_id") or "").strip()
        if case_id:
            family_case_ids[family_id].add(case_id)
        family_dataset_rows[family_id] += 1

        benchmark_type = str(case.get("benchmark_type") or "").strip().lower()
        if benchmark_type:
            family_benchmark_types[family_id][benchmark_type] += 1

        for chart_basis in case.get("chart_basis") or []:
            normalized_basis = str(chart_basis or "").strip().lower()
            if normalized_basis:
                family_chart_basis[family_id][normalized_basis] += 1

        for source in case.get("source_assertions") or []:
            if not isinstance(source, dict):
                continue
            title = str(source.get("title") or "").strip()
            if title:
                family_historical_source_titles[family_id].add(title)
                family_source_titles[family_id].add(title)

    known_families = set(family_case_ids.keys())
    family_doctrine_case_ids: dict[str, set[str]] = defaultdict(set)
    for case in cases:
        if str(case.get("_dataset_kind") or "") != "source_alignment":
            continue
        target_families = _source_alignment_target_families(case, known_families=known_families)
        if not target_families:
            continue
        source = case.get("source") or {}
        title = str(source.get("title") or "").strip()
        case_id = str(case.get("case_id") or "").strip()
        for family_id in target_families:
            if title:
                family_doctrine_source_titles[family_id].add(title)
                family_source_titles[family_id].add(title)
            if case_id:
                family_doctrine_case_ids[family_id].add(case_id)

    profiles: Dict[str, Dict[str, Any]] = {}
    for family_id, case_ids in family_case_ids.items():
        source_titles = sorted(family_source_titles.get(family_id) or [])
        historical_source_titles = sorted(family_historical_source_titles.get(family_id) or [])
        doctrine_source_titles = sorted(family_doctrine_source_titles.get(family_id) or [])
        coverage_tier = _coverage_tier(len(case_ids), len(source_titles))
        gaps: list[str] = []
        if len(source_titles) < 2:
            gaps.append("source_concentrated")
        if len(case_ids) < 3:
            gaps.append("narrow_benchmark_shape")
        profiles[family_id] = {
            "benchmark_family_id": family_id,
            "coverage_tier": coverage_tier,
            "unique_case_count": len(case_ids),
            "dataset_row_count": int(family_dataset_rows.get(family_id) or 0),
            "source_count": len(source_titles),
            "source_titles": source_titles,
            "historical_source_count": len(historical_source_titles),
            "historical_source_titles": historical_source_titles,
            "doctrine_source_count": len(doctrine_source_titles),
            "doctrine_source_titles": doctrine_source_titles,
            "doctrine_case_count": len(family_doctrine_case_ids.get(family_id) or ()),
            "benchmark_type_counts": dict(sorted((family_benchmark_types.get(family_id) or {}).items())),
            "chart_basis_counts": dict(sorted((family_chart_basis.get(family_id) or {}).items())),
            "gaps": gaps,
        }
    return profiles


def get_weather_family_profile(benchmark_family_id: str) -> Dict[str, Any]:
    family_id = str(benchmark_family_id or "").strip().lower()
    profiles = build_weather_family_profiles()
    profile = profiles.get(family_id)
    if profile:
        return dict(profile)
    return {
        "benchmark_family_id": family_id,
        "coverage_tier": "seeded",
        "unique_case_count": 0,
        "dataset_row_count": 0,
        "source_count": 0,
        "source_titles": [],
        "historical_source_count": 0,
        "historical_source_titles": [],
        "doctrine_source_count": 0,
        "doctrine_source_titles": [],
        "doctrine_case_count": 0,
        "benchmark_type_counts": {},
        "chart_basis_counts": {},
        "gaps": ["no_benchmark_rows"],
    }


def get_weather_branch_metrics() -> Dict[str, Any]:
    profiles = build_weather_family_profiles()
    coverage_counts: Counter[str] = Counter()
    for profile in profiles.values():
        coverage_counts[str(profile.get("coverage_tier") or "seeded")] += 1
    return {
        "family_profile_count": len(profiles),
        "coverage_counts": dict(sorted(coverage_counts.items())),
    }
