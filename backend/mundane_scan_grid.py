from __future__ import annotations

from typing import Any, Dict, List, Optional

from astrocartography_city_catalog import (
    ATLAS_SEARCH_RESOLUTIONS,
    DEFAULT_ATLAS_RESOLUTION,
    get_atlas_resolution_settings,
    get_country_catalog_meta,
    list_city_catalog_entries,
    normalize_atlas_resolution,
)


_THEMATIC_REGIONS: Dict[str, Dict[str, Any]] = {
    "middle_east": {
        "id": "middle_east",
        "label": "Middle East",
        "kind": "thematic",
        "summary": "Middle Eastern candidate cities using the shipped atlas catalog.",
        "country_codes": {
            "AE",
            "BH",
            "CY",
            "EG",
            "IL",
            "IQ",
            "IR",
            "JO",
            "KW",
            "LB",
            "OM",
            "PS",
            "QA",
            "SA",
            "SY",
            "TR",
            "YE",
        },
    },
    "levant": {
        "id": "levant",
        "label": "Levant",
        "kind": "thematic",
        "summary": "Levantine scan across the eastern Mediterranean and adjacent war theaters.",
        "country_codes": {
            "CY",
            "IL",
            "JO",
            "LB",
            "PS",
            "SY",
            "TR",
        },
    },
    "persian_gulf": {
        "id": "persian_gulf",
        "label": "Persian Gulf",
        "kind": "thematic",
        "summary": "Gulf-facing scan for Iran, Iraq, Arabia, and adjacent maritime approaches.",
        "country_codes": {
            "AE",
            "BH",
            "IR",
            "IQ",
            "KW",
            "OM",
            "QA",
            "SA",
        },
    },
    "north_africa": {
        "id": "north_africa",
        "label": "North Africa",
        "kind": "thematic",
        "summary": "North African scan across Mediterranean-facing public-event centers.",
        "country_codes": {
            "DZ",
            "EG",
            "LY",
            "MA",
            "SD",
            "TN",
        },
    },
    "eastern_europe": {
        "id": "eastern_europe",
        "label": "Eastern Europe",
        "kind": "thematic",
        "summary": "Eastern European scan for border-pressure, war, and state-stability cases.",
        "country_codes": {
            "AM",
            "AZ",
            "BG",
            "BY",
            "CZ",
            "EE",
            "GE",
            "HU",
            "LT",
            "LV",
            "MD",
            "PL",
            "RO",
            "RU",
            "SK",
            "UA",
        },
    },
    "east_asia": {
        "id": "east_asia",
        "label": "East Asia",
        "kind": "thematic",
        "summary": "East Asian scan for regional crisis, conflict, and state-pressure events.",
        "country_codes": {
            "CN",
            "HK",
            "JP",
            "KP",
            "KR",
            "MN",
            "MO",
            "TW",
        },
    },
}

_CONTINENT_ORDER = ["AF", "AS", "EU", "NA", "OC", "SA"]


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _city_label(city: Dict[str, Any]) -> str:
    name = str(city.get("ascii_name") or city.get("name") or "").strip()
    country = str(city.get("country_name") or city.get("country_code") or "").strip()
    if name and country:
        return f"{name}, {country}"
    return name or country or "Unknown"


def _continent_region_defs() -> List[Dict[str, Any]]:
    meta = get_country_catalog_meta()
    continents: Dict[str, Dict[str, str]] = {}
    for row in meta.values():
        continent_code = str(row.get("continent_code") or "").strip().upper()
        continent_name = str(row.get("continent_name") or "").strip()
        if not continent_code or continent_code in continents:
            continue
        continents[continent_code] = {
            "id": f"continent:{continent_code.lower()}",
            "label": continent_name or continent_code,
            "kind": "continent",
            "summary": f"Atlas-backed scan across {continent_name or continent_code}.",
            "continent_code": continent_code,
        }
    ordered: List[Dict[str, Any]] = []
    for code in _CONTINENT_ORDER:
        if code in continents:
            ordered.append(continents[code])
    for code, row in sorted(continents.items()):
        if code not in _CONTINENT_ORDER:
            ordered.append(row)
    return ordered


def get_scan_region_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "id": "global",
            "label": "Global",
            "kind": "global",
            "summary": "Bounded scan across the shipped global city catalog.",
        },
        *_THEMATIC_REGIONS.values(),
        *_continent_region_defs(),
    ]


def describe_region(region_id: Optional[str]) -> Dict[str, Any]:
    raw = str(region_id or "").strip()
    normalized = raw.lower()
    if not normalized:
        raise ValueError("region_id is required")
    if normalized == "global":
        return {
            "id": "global",
            "label": "Global",
            "kind": "global",
            "summary": "Bounded scan across the shipped global city catalog.",
        }
    if normalized.startswith("continent:"):
        continent_code = normalized.split(":", 1)[1].strip().upper()
        if not continent_code:
            raise ValueError("continent region_id must include a code")
        for row in _continent_region_defs():
            if str(row.get("continent_code") or "").upper() == continent_code:
                return row
        raise ValueError(f"Unknown continent region: {region_id}")
    if normalized.startswith("country:"):
        country_code = normalized.split(":", 1)[1].strip().upper()
        if not country_code:
            raise ValueError("country region_id must include a code")
        meta = get_country_catalog_meta().get(country_code)
        if not meta:
            raise ValueError(f"Unknown country region: {region_id}")
        return {
            "id": f"country:{country_code.lower()}",
            "label": str(meta.get("country_name") or country_code),
            "kind": "country",
            "summary": f"Atlas-backed scan inside {meta.get('country_name') or country_code}.",
            "country_code": country_code,
        }
    thematic = _THEMATIC_REGIONS.get(normalized)
    if thematic:
        return dict(thematic)
    raise ValueError(f"Unsupported region_id: {region_id}")


def collect_region_candidates(
    region_id: str,
    *,
    resolution: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    region = describe_region(region_id)
    resolution_id = normalize_atlas_resolution(resolution)
    resolution_settings = get_atlas_resolution_settings(resolution_id)
    min_population = int(resolution_settings.get("min_population") or 0)

    def _matches(city: Dict[str, Any]) -> bool:
        if region["kind"] == "global":
            return True
        if region["kind"] == "continent":
            return str(city.get("continent_code") or "").strip().upper() == str(region.get("continent_code") or "").strip().upper()
        if region["kind"] == "country":
            return str(city.get("country_code") or "").strip().upper() == str(region.get("country_code") or "").strip().upper()
        if region["kind"] == "thematic":
            return str(city.get("country_code") or "").strip().upper() in set(region.get("country_codes") or [])
        return False

    rows: List[Dict[str, Any]] = []
    for city in list_city_catalog_entries():
        if not _matches(city):
            continue
        feature_code = str(city.get("feature_code") or "").upper()
        population = int(city.get("population") or 0)
        if feature_code == "PPL" and population < min_population:
            continue
        row = dict(city)
        row["label"] = _city_label(row)
        rows.append(row)

    rows.sort(
        key=lambda item: (
            -int(item.get("population") or 0),
            str(item.get("ascii_name") or item.get("name") or ""),
            str(item.get("country_code") or ""),
        )
    )

    effective_limit = None
    if limit is not None:
        effective_limit = max(1, int(limit))
    elif resolution_settings.get("relocation_limit") is not None:
        effective_limit = int(resolution_settings["relocation_limit"])

    if effective_limit is not None:
        rows = rows[:effective_limit]
    return rows


def get_scan_catalog() -> Dict[str, Any]:
    return {
        "regions": get_scan_region_definitions(),
        "scan_modes": [
            {
                "id": "spatial_scan",
                "label": "Spatial Scan",
                "summary": "Fixed event time; scan a region across locations only.",
            },
            {
                "id": "spatiotemporal_scan",
                "label": "Spatiotemporal Scan",
                "summary": "Scan a region across both location and time.",
            },
            {
                "id": "long_range_async_scan",
                "label": "Long-Range Async Scan",
                "summary": "Async-only long window scan with a coarser default cadence and stricter candidate budgeting.",
                "async_only": True,
            },
        ],
        "resolutions": [dict(row) for row in ATLAS_SEARCH_RESOLUTIONS.values()],
        "default_resolution": DEFAULT_ATLAS_RESOLUTION,
    }
