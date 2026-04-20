from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List, Optional

from astrocartography_resource_paths import resolve_astrocartography_resource_path

CITY_CATALOG_PATH = resolve_astrocartography_resource_path("city_catalog.runtime.json")
DEFAULT_ATLAS_RESOLUTION = "standard"
ATLAS_SEARCH_RESOLUTIONS: Dict[str, Dict[str, Any]] = {
    "coarse": {
        "id": "coarse",
        "label": "Coarse",
        "description": "Capitals, admin centers, and only the largest metros.",
        "min_population": 500000,
        "relocation_limit": 12,
    },
    "standard": {
        "id": "standard",
        "label": "Standard",
        "description": "Balanced atlas coverage for normal PathFinder searches.",
        "min_population": 200000,
        "relocation_limit": 18,
    },
    "fine": {
        "id": "fine",
        "label": "Fine",
        "description": "Denser city coverage with a wider relocation shortlist.",
        "min_population": 80000,
        "relocation_limit": 24,
    },
    "ultra": {
        "id": "ultra",
        "label": "Ultra",
        "description": "Deepest shipped atlas scan plus live query augmentation.",
        "min_population": 15000,
        "relocation_limit": 28,
        "augment_live_query": True,
        "live_limit": 8,
    },
}


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_atlas_resolution(value: Optional[str]) -> str:
    resolution = _normalize_text(value or "") or DEFAULT_ATLAS_RESOLUTION
    if resolution not in ATLAS_SEARCH_RESOLUTIONS:
        return DEFAULT_ATLAS_RESOLUTION
    return resolution


def get_atlas_resolution_settings(value: Optional[str] = None) -> Dict[str, Any]:
    resolution = normalize_atlas_resolution(value)
    return dict(ATLAS_SEARCH_RESOLUTIONS[resolution])


@lru_cache(maxsize=1)
def load_city_catalog_payload() -> Dict[str, Any]:
    payload = json.loads(CITY_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Astrocartography city catalog payload must be a JSON object")
    return payload


def list_city_catalog_entries() -> List[Dict[str, Any]]:
    payload = load_city_catalog_payload()
    cities = payload.get("cities") or []
    if not isinstance(cities, list):
        raise ValueError("Astrocartography city catalog payload missing cities list")
    return [item for item in cities if isinstance(item, dict)]


def get_country_catalog_meta() -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    for city in list_city_catalog_entries():
        country_code = str(city.get("country_code") or "").upper()
        if not country_code or country_code in meta:
            continue
        meta[country_code] = {
            "country_name": str(city.get("country_name") or country_code),
            "continent_code": str(city.get("continent_code") or ""),
            "continent_name": str(city.get("continent_name") or ""),
        }
    return meta


def search_city_catalog(
    *,
    query: Optional[str] = None,
    country_code: Optional[str] = None,
    continent_code: Optional[str] = None,
    limit: Optional[int] = None,
    resolution: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query_norm = _normalize_text(query or "")
    query_terms = [term for term in query_norm.split(" ") if term]
    country_norm = str(country_code or "").strip().upper()
    continent_norm = str(continent_code or "").strip().upper()
    resolution_settings = get_atlas_resolution_settings(resolution)
    min_population = int(resolution_settings.get("min_population") or 0)

    scored: List[Dict[str, Any]] = []
    for city in list_city_catalog_entries():
        if country_norm and str(city.get("country_code") or "").upper() != country_norm:
            continue
        if continent_norm and str(city.get("continent_code") or "").upper() != continent_norm:
            continue

        feature_code = str(city.get("feature_code") or "").upper()
        population = int(city.get("population") or 0)
        if feature_code == "PPL" and population < min_population:
            continue

        search_blob = _normalize_text(
            " ".join(
                [
                    str(city.get("name") or ""),
                    str(city.get("ascii_name") or ""),
                    str(city.get("country_name") or ""),
                    str(city.get("continent_name") or ""),
                    str(city.get("admin1_code") or ""),
                    str(city.get("timezone") or ""),
                ]
            )
        )

        if query_terms and not all(term in search_blob for term in query_terms):
            continue

        exact = 1 if query_norm and query_norm == _normalize_text(str(city.get("ascii_name") or city.get("name") or "")) else 0
        startswith = 1 if query_norm and _normalize_text(str(city.get("ascii_name") or city.get("name") or "")).startswith(query_norm) else 0
        scored.append(
            {
                **city,
                "_match_exact": exact,
                "_match_startswith": startswith,
            }
        )

    scored.sort(
        key=lambda item: (
            -int(item.get("_match_exact") or 0),
            -int(item.get("_match_startswith") or 0),
            -int(item.get("population") or 0),
            str(item.get("ascii_name") or item.get("name") or ""),
            str(item.get("country_code") or ""),
        )
    )

    out = []
    for row in scored[: max(0, int(limit)) if limit is not None else None]:
        cleaned = dict(row)
        cleaned.pop("_match_exact", None)
        cleaned.pop("_match_startswith", None)
        out.append(cleaned)
    return out
