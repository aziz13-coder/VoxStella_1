from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from astrocartography_resource_paths import resolve_astrocartography_resource_path

CITY_CATALOG_PATH = resolve_astrocartography_resource_path("city_catalog.runtime.json")
DEFAULT_ATLAS_RESOLUTION = "standard"
ATLAS_SEARCH_RESOLUTIONS: Dict[str, Dict[str, Any]] = {
    "coarse": {
        "id": "coarse",
        "label": "Coarse",
        "description": (
            "Largest metros (population 500,000+) plus capitals and first-level "
            "administrative centers regardless of population."
        ),
        "min_population": 500000,
        "population_floor_applies_to": "cities_other_than_capitals_and_first_level_admin_centers",
        "population_floor_exceptions": ["PPLC", "PPLA"],
        "candidate_limit": 3200,
        "relocation_limit": 12,
    },
    "standard": {
        "id": "standard",
        "label": "Standard",
        "description": "Balanced atlas coverage for normal PathFinder searches.",
        "min_population": 200000,
        "candidate_limit": 4000,
        "relocation_limit": 18,
    },
    "fine": {
        "id": "fine",
        "label": "Fine",
        "description": "Denser city coverage with a wider relocation shortlist.",
        "min_population": 80000,
        "candidate_limit": 6500,
        "relocation_limit": 24,
    },
    "ultra": {
        "id": "ultra",
        "label": "Ultra",
        "description": "Deepest shipped atlas scan plus live query augmentation.",
        "min_population": 15000,
        "candidate_limit": 22000,
        "relocation_limit": 28,
        "augment_live_query": True,
        "live_limit": 8,
    },
}

_COMMON_COUNTRY_ALIASES: Dict[str, Tuple[str, ...]] = {
    "AE": ("UAE", "U.A.E.", "United Arab Emirates"),
    "GB": (
        "UK",
        "U.K.",
        "Great Britain",
        "Britain",
        "United Kingdom of Great Britain and Northern Ireland",
    ),
    "SA": ("KSA", "Kingdom of Saudi Arabia"),
    "US": (
        "USA",
        "U.S.",
        "U.S.A.",
        "United States of America",
        "America",
    ),
}


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join(
        "".join(
            character if character.isalnum() else " "
            for character in decomposed
            if not unicodedata.combining(character)
        ).split()
    )


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
    return list(_city_catalog_index()["cities"])


@lru_cache(maxsize=1)
def _city_catalog_index() -> Dict[str, Any]:
    payload = load_city_catalog_payload()
    raw_cities = payload.get("cities") or []
    if not isinstance(raw_cities, list):
        raise ValueError("Astrocartography city catalog payload missing cities list")

    cities: List[Dict[str, Any]] = []
    indexed_rows: List[Tuple[Dict[str, Any], str, str]] = []
    by_geonameid: Dict[int, Dict[str, Any]] = {}
    by_exact_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    country_meta: Dict[str, Dict[str, str]] = {}
    for raw_city in raw_cities:
        if not isinstance(raw_city, dict):
            continue
        city = raw_city
        cities.append(city)
        name_norm = _normalize_text(
            str(city.get("ascii_name") or city.get("name") or "")
        )
        search_blob = _normalize_text(
            " ".join(
                [
                    str(city.get("name") or ""),
                    str(city.get("ascii_name") or ""),
                    str(city.get("country_code") or ""),
                    str(city.get("country_iso3") or ""),
                    str(city.get("country_name") or ""),
                    str(city.get("continent_name") or ""),
                    str(city.get("admin1_code") or ""),
                    str(city.get("admin1_name") or ""),
                    str(city.get("admin1_ascii_name") or ""),
                    " ".join(str(alias) for alias in (city.get("admin1_aliases") or [])),
                ]
            )
        )
        indexed_rows.append((city, name_norm, search_blob))
        exact_name_keys = {
            _normalize_text(str(city.get("name") or "")),
            _normalize_text(str(city.get("ascii_name") or "")),
        }
        for exact_name_key in exact_name_keys:
            if exact_name_key:
                by_exact_name[exact_name_key].append(city)
        try:
            geonameid = int(city.get("geonameid"))
        except (TypeError, ValueError):
            geonameid = 0
        if geonameid:
            by_geonameid[geonameid] = city

        country_code = str(city.get("country_code") or "").upper()
        if country_code and country_code not in country_meta:
            country_meta[country_code] = {
                "country_iso3": str(city.get("country_iso3") or ""),
                "country_name": str(city.get("country_name") or country_code),
                "continent_code": str(city.get("continent_code") or ""),
                "continent_name": str(city.get("continent_name") or ""),
            }

    return {
        "cities": tuple(cities),
        "indexed_rows": tuple(indexed_rows),
        "by_geonameid": by_geonameid,
        "by_exact_name": {
            key: tuple(rows)
            for key, rows in by_exact_name.items()
        },
        "country_meta": country_meta,
    }


def get_country_catalog_meta() -> Dict[str, Dict[str, str]]:
    return {
        code: dict(meta)
        for code, meta in _city_catalog_index()["country_meta"].items()
    }


@lru_cache(maxsize=1)
def _country_qualifier_aliases_by_code() -> Dict[str, Tuple[str, ...]]:
    aliases_by_code: Dict[str, Tuple[str, ...]] = {}
    for code, meta in _city_catalog_index()["country_meta"].items():
        aliases = {
            _normalize_text(code),
            _normalize_text(str(meta.get("country_iso3") or "")),
            _normalize_text(str(meta.get("country_name") or "")),
        }
        aliases.update(
            _normalize_text(alias)
            for alias in _COMMON_COUNTRY_ALIASES.get(code, ())
        )
        aliases_by_code[code] = tuple(sorted(alias for alias in aliases if alias))
    return aliases_by_code


@lru_cache(maxsize=1)
def _country_codes_by_qualifier_alias() -> Dict[str, Tuple[str, ...]]:
    codes_by_alias: Dict[str, List[str]] = defaultdict(list)
    for code, aliases in _country_qualifier_aliases_by_code().items():
        for alias in aliases:
            codes_by_alias[alias].append(code)
    return {
        alias: tuple(sorted(set(codes)))
        for alias, codes in codes_by_alias.items()
    }


def get_city_catalog_country_codes_for_alias(value: Any) -> Tuple[str, ...]:
    alias = _normalize_text(str(value or ""))
    if not alias:
        return ()
    return _country_codes_by_qualifier_alias().get(alias, ())


def get_city_catalog_entry_by_geonameid(value: Any) -> Optional[Dict[str, Any]]:
    raw_value = str(value or "").strip()
    if raw_value.casefold().startswith("geonames:"):
        raw_value = raw_value.split(":", 1)[1]
    try:
        geonameid = int(raw_value)
    except (TypeError, ValueError):
        return None
    city = _city_catalog_index()["by_geonameid"].get(geonameid)
    return dict(city) if isinstance(city, dict) else None


def find_exact_city_catalog_entries(name: Any) -> List[Dict[str, Any]]:
    name_norm = _normalize_text(str(name or ""))
    if not name_norm:
        return []
    lookup_keys = [name_norm]
    if name_norm.startswith("city of "):
        lookup_keys.append(name_norm.removeprefix("city of "))
    elif not name_norm.endswith(" city"):
        lookup_keys.append(f"{name_norm} city")
    rows: List[Dict[str, Any]] = []
    seen = set()
    for lookup_key in lookup_keys:
        for city in (_city_catalog_index()["by_exact_name"].get(lookup_key) or ()):
            geonameid = city.get("geonameid")
            if geonameid in seen:
                continue
            seen.add(geonameid)
            rows.append(dict(city))
    return [
        city
        for city in rows
    ]


def parse_city_catalog_identity_query(value: Any) -> Dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {
            "text": "",
            "city_query": "",
            "qualifiers": [],
            "has_explicit_qualifiers": False,
            "city_prefix_exact": False,
        }

    if "," in text:
        parts = [part.strip() for part in text.split(",")]
        city_query = parts[0]
        qualifiers = [part for part in parts[1:] if part]
        return {
            "text": text,
            "city_query": city_query,
            "qualifiers": qualifiers,
            "has_explicit_qualifiers": bool(qualifiers),
            "city_prefix_exact": bool(find_exact_city_catalog_entries(city_query)),
        }

    if find_exact_city_catalog_entries(text):
        return {
            "text": text,
            "city_query": text,
            "qualifiers": [],
            "has_explicit_qualifiers": False,
            "city_prefix_exact": True,
        }

    words = text.split()
    for split_at in range(len(words) - 1, 0, -1):
        city_query = " ".join(words[:split_at])
        if find_exact_city_catalog_entries(city_query):
            qualifier = " ".join(words[split_at:])
            return {
                "text": text,
                "city_query": city_query,
                "qualifiers": [qualifier],
                "has_explicit_qualifiers": True,
                "city_prefix_exact": True,
            }

    return {
        "text": text,
        "city_query": text,
        "qualifiers": [],
        "has_explicit_qualifiers": False,
        "city_prefix_exact": False,
    }


def _city_name_identity_aliases(city: Dict[str, Any]) -> Tuple[str, ...]:
    aliases = {
        _normalize_text(str(city.get("name") or "")),
        _normalize_text(str(city.get("ascii_name") or "")),
    }
    for key in ("label", "query"):
        primary = str(city.get(key) or "").split(",", 1)[0].strip()
        if primary:
            aliases.add(_normalize_text(primary))
    expanded = set(aliases)
    for alias in aliases:
        if alias:
            expanded.add(f"{alias} city")
            expanded.add(f"city of {alias}")
            if alias.endswith(" city"):
                expanded.add(alias.removesuffix(" city"))
    return tuple(sorted(alias for alias in expanded if alias))


def _city_qualifier_identity_aliases(city: Dict[str, Any]) -> Tuple[str, ...]:
    country_code = str(city.get("country_code") or "").strip().upper()
    aliases = set(_country_qualifier_aliases_by_code().get(country_code, ()))
    aliases.update(
        {
            _normalize_text(str(city.get("country_code") or "")),
            _normalize_text(str(city.get("country_iso3") or "")),
            _normalize_text(str(city.get("country_name") or "")),
            _normalize_text(str(city.get("admin1_code") or "")),
            _normalize_text(str(city.get("admin1_name") or "")),
            _normalize_text(str(city.get("admin1_ascii_name") or "")),
        }
    )
    aliases.update(
        _normalize_text(str(alias))
        for alias in (city.get("admin1_aliases") or [])
    )
    return tuple(sorted(alias for alias in aliases if alias))


def _qualifier_segment_matches_aliases(
    qualifier: Any,
    aliases: Tuple[str, ...],
) -> bool:
    qualifier_tokens = _normalize_text(str(qualifier or "")).split()
    if not qualifier_tokens:
        return False
    alias_tokens = tuple(
        tuple(alias.split())
        for alias in aliases
        if alias
    )
    reachable = {0}
    for start in range(len(qualifier_tokens)):
        if start not in reachable:
            continue
        for tokens in alias_tokens:
            end = start + len(tokens)
            if tuple(qualifier_tokens[start:end]) == tokens:
                reachable.add(end)
    return len(qualifier_tokens) in reachable


def city_catalog_candidate_matches_identity(
    city: Dict[str, Any],
    query: Any,
) -> bool:
    parsed = (
        query
        if isinstance(query, dict) and "city_query" in query
        else parse_city_catalog_identity_query(query)
    )
    city_query = _normalize_text(str(parsed.get("city_query") or ""))
    if not city_query or city_query not in _city_name_identity_aliases(city):
        return False
    qualifier_aliases = _city_qualifier_identity_aliases(city)
    return all(
        _qualifier_segment_matches_aliases(qualifier, qualifier_aliases)
        for qualifier in (parsed.get("qualifiers") or [])
    )


def city_catalog_candidate_matches_keyword(
    city: Dict[str, Any],
    query: Any,
) -> bool:
    query_terms = _normalize_text(str(query or "")).split()
    if not query_terms:
        return True
    aliases = set(_city_name_identity_aliases(city))
    aliases.update(_city_qualifier_identity_aliases(city))
    aliases.update(
        {
            _normalize_text(str(city.get("continent_code") or "")),
            _normalize_text(str(city.get("continent_name") or "")),
        }
    )
    aliases.discard("")

    def _matches_term(term: str) -> bool:
        if len(term) <= 2:
            return term in aliases
        return any(
            alias.startswith(term)
            or any(token.startswith(term) for token in alias.split())
            for alias in aliases
        )

    return all(_matches_term(term) for term in query_terms)


def search_city_catalog(
    *,
    query: Optional[str] = None,
    country_code: Optional[str] = None,
    continent_code: Optional[str] = None,
    limit: Optional[int] = None,
    resolution: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query_text = str(query or "").strip()
    country_keyword_codes = get_city_catalog_country_codes_for_alias(query_text)
    parsed_identity = (
        parse_city_catalog_identity_query(query_text)
        if query_text and not country_keyword_codes
        else None
    )
    use_exact_identity = bool(
        parsed_identity
        and parsed_identity.get("city_prefix_exact")
    )
    query_norm = (
        ""
        if country_keyword_codes
        else _normalize_text(
            parsed_identity.get("city_query")
            if use_exact_identity
            else query_text
        )
    )
    query_terms = [term for term in query_norm.split(" ") if term]
    country_norm = str(country_code or "").strip().upper()
    continent_norm = str(continent_code or "").strip().upper()
    resolution_settings = get_atlas_resolution_settings(resolution)
    min_population = int(resolution_settings.get("min_population") or 0)
    candidate_limit = max(0, int(resolution_settings.get("candidate_limit") or 0))

    scored: List[Dict[str, Any]] = []
    for city, name_norm, search_blob in _city_catalog_index()["indexed_rows"]:
        if country_norm and str(city.get("country_code") or "").upper() != country_norm:
            continue
        if (
            country_keyword_codes
            and str(city.get("country_code") or "").upper() not in country_keyword_codes
        ):
            continue
        if continent_norm and str(city.get("continent_code") or "").upper() != continent_norm:
            continue

        feature_code = str(city.get("feature_code") or "").upper()
        population = int(city.get("population") or 0)
        if feature_code not in {"PPLC", "PPLA"} and population < min_population:
            continue

        if query_terms and not all(term in search_blob for term in query_terms):
            continue
        if use_exact_identity and not city_catalog_candidate_matches_identity(
            city,
            parsed_identity,
        ):
            continue
        if (
            query_text
            and not country_keyword_codes
            and not use_exact_identity
            and not city_catalog_candidate_matches_keyword(city, query_text)
        ):
            continue

        exact = 1 if query_norm and query_norm == name_norm else 0
        startswith = 1 if query_norm and name_norm.startswith(query_norm) else 0
        feature_code_priority = (
            2
            if feature_code == "PPLC"
            else (1 if feature_code == "PPLA" else 0)
        )
        scored.append(
            {
                **city,
                "_match_exact": exact,
                "_match_startswith": startswith,
                "_feature_code_priority": feature_code_priority,
            }
        )

    scored.sort(
        key=lambda item: (
            -int(item.get("_feature_code_priority") or 0),
            -int(item.get("_match_exact") or 0),
            -int(item.get("_match_startswith") or 0),
            -int(item.get("population") or 0),
            str(item.get("ascii_name") or item.get("name") or ""),
            str(item.get("country_code") or ""),
        )
    )

    effective_limit = max(0, int(limit)) if limit is not None else candidate_limit
    out = []
    for row in scored[:effective_limit]:
        cleaned = dict(row)
        cleaned.pop("_match_exact", None)
        cleaned.pop("_match_startswith", None)
        cleaned.pop("_feature_code_priority", None)
        out.append(cleaned)
    return out
