"""Canonical, non-destructive schema helpers for saved Astro Clock charts.

Legacy snap records used a local wall-clock string, an IANA timezone, and a
``coords`` array.  Newer records use an aware UTC instant and explicit
latitude/longitude.  This module normalizes both formats without geocoding or
discarding the original chart payload.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo


SNAP_STORE_SCHEMA_VERSION = 2
SNAP_RECORD_SCHEMA_VERSION = 2


def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _valid_coordinate_pair(latitude: Any, longitude: Any) -> Optional[Tuple[float, float]]:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def coordinate_pair_from_value(value: Any) -> Optional[Tuple[float, float]]:
    """Read a coordinate pair from current or legacy serialized shapes."""
    if isinstance(value, dict):
        pair = _valid_coordinate_pair(value.get("latitude"), value.get("longitude"))
        if pair is not None:
            return pair
        pair = _valid_coordinate_pair(value.get("lat"), value.get("lon"))
        if pair is not None:
            return pair
        nested = value.get("coords")
        if nested is not value:
            pair = coordinate_pair_from_value(nested)
            if pair is not None:
                return pair
        timezone_info = value.get("timezone_info")
        if isinstance(timezone_info, dict):
            pair = coordinate_pair_from_value(timezone_info.get("coordinates"))
            if pair is not None:
                return pair
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _valid_coordinate_pair(value[0], value[1])
    return None


def _timezone_candidate(value: Any) -> Optional[str]:
    text = _first_text(value)
    if not text:
        return None
    # Legacy labels look like "Asia/Jerusalem (UTC+00:00)".
    candidate = text.split(" (UTC", 1)[0].strip()
    try:
        ZoneInfo(candidate)
        return candidate
    except Exception:
        return None


def timezone_name_from_values(*values: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return a valid IANA timezone and the field/value source that supplied it."""
    for source, value in values:
        timezone_name = _timezone_candidate(value)
        if timezone_name:
            return timezone_name, str(source)
    return None, None


def _parse_iso(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    text = _first_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _has_explicit_clock_time(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    text = _first_text(value)
    if not text:
        return False
    return bool(re.search(r"[Tt ]\d{2}:\d{2}", text))


def timezone_label_for_instant(timezone_name: Any, instant_utc: Any) -> Optional[str]:
    """Build a historical offset label from ZoneInfo at the effective instant."""
    tz_name = _timezone_candidate(timezone_name)
    instant = _parse_iso(instant_utc)
    if not tz_name or instant is None or instant.tzinfo is None:
        return None
    try:
        local = instant.astimezone(ZoneInfo(tz_name))
        offset = local.utcoffset()
    except Exception:
        return None
    if offset is None:
        return tz_name
    total_minutes = int(round(offset.total_seconds() / 60.0))
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{tz_name} (UTC{sign}{hours:02d}:{minutes:02d})"


def canonical_time_context(
    value: Any,
    timezone_name: Optional[str],
    *,
    source_field: str,
    legacy_local_wall_time: bool,
) -> Dict[str, Any]:
    """Normalize a stored time while retaining the exact interpretation policy."""
    parsed = _parse_iso(value)
    raw_value = _first_text(value)
    result: Dict[str, Any] = {
        "source_field": source_field,
        "source_value": raw_value,
        "timezone": timezone_name,
        "legacy_naive": bool(parsed is not None and parsed.tzinfo is None),
        "interpretation": None,
        "ambiguous": False,
        "instant_utc": None,
        "local_datetime": None,
    }
    if parsed is None:
        result["ambiguous"] = True
        result["interpretation"] = "invalid_or_missing"
        return result
    if not _has_explicit_clock_time(value):
        result["ambiguous"] = True
        result["interpretation"] = "date_only_missing_birth_time"
        result["wall_time_status"] = "missing_time"
        return result

    if parsed.tzinfo is not None:
        instant = parsed.astimezone(timezone.utc)
        result["interpretation"] = "aware_instant"
    elif legacy_local_wall_time and timezone_name:
        try:
            zone = ZoneInfo(timezone_name)
            candidate_rows: List[Dict[str, Any]] = []
            seen_instants = set()
            for fold in (0, 1):
                local = parsed.replace(tzinfo=zone, fold=fold)
                candidate_utc = local.astimezone(timezone.utc)
                round_trip = candidate_utc.astimezone(zone)
                candidate_key = candidate_utc.isoformat()
                if candidate_key in seen_instants:
                    continue
                seen_instants.add(candidate_key)
                candidate_rows.append({
                    "fold": fold,
                    "instant_utc": candidate_key,
                    "local_datetime": local.isoformat(),
                    "round_trip_local_datetime": round_trip.isoformat(),
                    "round_trip_matches": (
                        round_trip.replace(tzinfo=None) == parsed
                    ),
                })
            valid_rows = [
                row for row in candidate_rows if row.get("round_trip_matches")
            ]
            result["wall_time_candidates"] = candidate_rows
            if len(valid_rows) == 1:
                selected = valid_rows[0]
                instant = _parse_iso(selected["instant_utc"])
                result["interpretation"] = "legacy_local_wall_time_with_iana_zone"
                result["wall_time_status"] = "unique"
            elif len(valid_rows) > 1:
                selected = valid_rows[0]
                instant = None
                result["unresolved_candidate_instant_utc"] = selected["instant_utc"]
                result["interpretation"] = "ambiguous_repeated_local_wall_time"
                result["wall_time_status"] = "ambiguous_fold"
                result["ambiguous"] = True
            else:
                selected = candidate_rows[0]
                instant = None
                result["unresolved_candidate_instant_utc"] = selected["instant_utc"]
                result["interpretation"] = "nonexistent_local_wall_time"
                result["wall_time_status"] = "nonexistent_gap"
                result["ambiguous"] = True
            if instant is None and not result.get("ambiguous"):
                raise ValueError("could not construct UTC candidate")
        except Exception:
            instant = None
            result["unresolved_candidate_instant_utc"] = (
                parsed.replace(tzinfo=timezone.utc).isoformat()
            )
            result["interpretation"] = "legacy_naive_assumed_utc"
            result["ambiguous"] = True
    else:
        instant = None
        result["unresolved_candidate_instant_utc"] = (
            parsed.replace(tzinfo=timezone.utc).isoformat()
        )
        result["interpretation"] = "naive_assumed_utc"
        result["ambiguous"] = True

    if instant is not None:
        result["instant_utc"] = instant.isoformat()
    if timezone_name and instant is not None:
        try:
            result["local_datetime"] = instant.astimezone(ZoneInfo(timezone_name)).isoformat()
        except Exception:
            result["local_datetime"] = None
    return result


def _normalized_location(value: Any) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    return re.sub(r"\s*,\s*", ",", text)


@lru_cache(maxsize=1)
def _country_location_labels() -> frozenset[str]:
    labels = {
        "usa", "u.s.", "u.s.a.", "america", "united states",
        "united states of america", "uk", "u.k.", "great britain",
        "britain", "united kingdom", "uae", "u.a.e.",
    }
    try:
        import pytz

        labels.update(
            _normalized_location(name)
            for name in pytz.country_names.values()
            if name
        )
    except Exception:
        labels.update({
            "israel", "germany", "iran", "haiti", "iraq", "japan",
            "italy", "brazil", "netherlands", "canada", "france",
            "australia", "india", "china", "mexico",
        })
    return frozenset(labels)


_ADMIN_REGION_LOCATION_LABELS = frozenset({
    # United States states and federal district.
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "district of columbia", "florida", "georgia",
    "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
    # Canadian provinces and territories.
    "alberta", "british columbia", "manitoba", "new brunswick",
    "newfoundland and labrador", "northwest territories", "nova scotia",
    "nunavut", "ontario", "prince edward island", "quebec", "saskatchewan",
    "yukon",
    # Netherlands provinces and broad UK administrative regions seen in
    # imported data.
    "drenthe", "flevoland", "friesland", "gelderland", "groningen",
    "limburg", "north brabant", "north holland", "overijssel",
    "south holland", "utrecht", "zeeland", "england", "scotland", "wales",
    "northern ireland", "greater london",
})


def _generic_location_label(value: Any) -> bool:
    """Flag low-specificity legacy labels without guessing a replacement city."""
    text = _normalized_location(value)
    if not text:
        return True
    if any(char.isdigit() for char in text):
        return False
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) == 1:
        return (
            parts[0] in _country_location_labels()
            or parts[0] in _ADMIN_REGION_LOCATION_LABELS
        )
    if (
        len(parts) == 2
        and parts[0] in _ADMIN_REGION_LOCATION_LABELS
        and parts[1] in _country_location_labels()
    ):
        return True
    if (
        len(parts) >= 3
        and parts[0].startswith("greater ")
        and parts[-1] in _country_location_labels()
    ):
        return True
    return False


def is_generic_location_label(value: Any) -> bool:
    """Return whether a location is too broad to confirm chart coordinates."""
    return _generic_location_label(value)


def _planet_rows(chart: Any) -> List[Tuple[str, float, Optional[int]]]:
    if not isinstance(chart, dict):
        return []
    raw = chart.get("planets")
    rows: List[Dict[str, Any]] = []
    if isinstance(raw, dict):
        for name, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row.setdefault("planet", name)
            rows.append(row)
    elif isinstance(raw, list):
        rows = [row for row in raw if isinstance(row, dict)]
    normalized: List[Tuple[str, float, Optional[int]]] = []
    for row in rows:
        name = _first_text(row.get("planet"), row.get("name"))
        try:
            longitude = round(float(row.get("longitude")) % 360.0, 8)
        except (TypeError, ValueError):
            continue
        try:
            house = int(row.get("house")) if row.get("house") is not None else None
        except (TypeError, ValueError):
            house = None
        normalized.append((str(name or "").casefold(), longitude, house))
    normalized.sort()
    return normalized


def chart_fingerprint(chart: Any) -> Optional[str]:
    """Fingerprint only geometry used by comparison features."""
    if not isinstance(chart, dict):
        return None
    planets = _planet_rows(chart)
    if not planets:
        return None
    raw_cusps = chart.get("house_cusps") or chart.get("houses") or []
    cusps: List[float] = []
    if isinstance(raw_cusps, list):
        for value in raw_cusps[:12]:
            try:
                cusps.append(round(float(value) % 360.0, 8))
            except (TypeError, ValueError):
                cusps = []
                break
    payload = {
        "planets": planets,
        "cusps": cusps,
        "ascendant": chart.get("ascendant"),
        "midheaven": chart.get("midheaven"),
        "house_system_code": chart.get("house_system_code") or chart.get("house_system"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _context_fingerprint(context: Dict[str, Any]) -> str:
    payload = {
        "instant_utc": context.get("instant_utc"),
        "timezone": context.get("timezone"),
        "latitude": context.get("latitude"),
        "longitude": context.get("longitude"),
        "location": _normalized_location(context.get("location")),
        "house_system_code": context.get("house_system_code"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _context_conflict(
    field: str,
    candidates: Iterable[Tuple[str, Any]],
    selected_source: Optional[str],
) -> Optional[Dict[str, Any]]:
    rows = [
        {"source": source, "value": copy.deepcopy(value)}
        for source, value in candidates
        if value not in (None, "")
    ]
    serialized = {
        json.dumps(row["value"], sort_keys=True, default=str)
        for row in rows
    }
    if len(serialized) <= 1:
        return None
    return {
        "field": field,
        "candidates": rows,
        "selected_source": selected_source,
        "resolution": "source_precedence_without_deleting_alternatives",
    }


def canonicalize_snapshot_record(snap: Any) -> Dict[str, Any]:
    """Return a schema-v2 record while preserving every legacy payload."""
    if not isinstance(snap, dict):
        raise TypeError("Snapshot record must be an object")
    original = copy.deepcopy(snap)
    out = copy.deepcopy(snap)
    dashboard = copy.deepcopy(out.get("dashboard")) if isinstance(out.get("dashboard"), dict) else {}
    previous_schema = out.get("schema_version")
    legacy_record = previous_schema != SNAP_RECORD_SCHEMA_VERSION
    existing_context = (
        copy.deepcopy(out.get("calculation_context"))
        if isinstance(out.get("calculation_context"), dict)
        else {}
    )

    location = _first_text(out.get("location"), dashboard.get("location"))
    timezone_name, timezone_source = timezone_name_from_values(
        ("snap.timezone", out.get("timezone")),
        ("dashboard.timezone", dashboard.get("timezone")),
        ("snap.timezone_label", out.get("timezone_label")),
        ("dashboard.timezone_label", dashboard.get("timezone_label")),
    )

    time_source = (
        "snap.effective_datetime"
        if out.get("effective_datetime") not in (None, "")
        else "dashboard.timestamp"
    )
    raw_time = (
        out.get("effective_datetime")
        if time_source == "snap.effective_datetime"
        else dashboard.get("timestamp")
    )
    time_context = canonical_time_context(
        raw_time,
        timezone_name,
        source_field=time_source,
        legacy_local_wall_time=legacy_record,
    )
    if not legacy_record and isinstance(existing_context.get("time_provenance"), dict):
        preserved_time_provenance = copy.deepcopy(existing_context["time_provenance"])
        preserved_time_provenance["instant_utc"] = (
            time_context.get("instant_utc")
            or preserved_time_provenance.get("instant_utc")
        )
        preserved_time_provenance["local_datetime"] = (
            existing_context.get("local_datetime")
            or time_context.get("local_datetime")
            or preserved_time_provenance.get("local_datetime")
        )
        time_context = preserved_time_provenance
        timezone_source = existing_context.get("timezone_source") or timezone_source
    instant_utc = time_context.get("instant_utc")
    timezone_label = timezone_label_for_instant(timezone_name, instant_utc)

    coordinate_source = None
    coords = coordinate_pair_from_value({
        "latitude": out.get("latitude"),
        "longitude": out.get("longitude"),
    })
    if coords is not None:
        coordinate_source = "snap.latitude_longitude"
    if coords is None:
        coords = coordinate_pair_from_value(out.get("coords"))
        if coords is not None:
            coordinate_source = "snap.coords"
    if coords is None:
        coords = coordinate_pair_from_value({
            "latitude": dashboard.get("latitude"),
            "longitude": dashboard.get("longitude"),
        })
        if coords is not None:
            coordinate_source = "dashboard.latitude_longitude"
    if coords is None:
        coords = coordinate_pair_from_value(dashboard.get("coords"))
        if coords is not None:
            coordinate_source = "dashboard.coords"

    existing_coordinate_provenance = out.get("coordinate_provenance")
    if not isinstance(existing_coordinate_provenance, dict):
        existing_coordinate_provenance = {}
    generic_location = _generic_location_label(location)
    coordinate_provenance = {
        **copy.deepcopy(existing_coordinate_provenance),
        "source": existing_coordinate_provenance.get("source") or coordinate_source or "missing",
        "persisted_with_chart": bool(coords is not None),
        "inferred_at_read_time": False,
        "legacy_shape": (
            coordinate_source
            if legacy_record
            else existing_coordinate_provenance.get("legacy_shape")
        ),
        "location_specificity": (
            "generic_or_ambiguous"
            if generic_location
            else (
                existing_coordinate_provenance.get("location_specificity")
                or "specific"
            )
        ),
        "review_required": bool(
            coords is None
            or generic_location
            or existing_coordinate_provenance.get("review_required")
        ),
    }

    house_system = _first_text(
        out.get("house_system_code"),
        dashboard.get("house_system_code"),
        dashboard.get("house_system"),
        (out.get("chart_snapshot") or {}).get("house_system_code")
        if isinstance(out.get("chart_snapshot"), dict)
        else None,
    )

    conflicts: List[Dict[str, Any]] = []
    for conflict in (
        _context_conflict(
            "effective_datetime",
            (
                ("snap.effective_datetime", out.get("effective_datetime")),
                ("dashboard.timestamp", dashboard.get("timestamp")),
            ),
            time_source,
        ),
        _context_conflict(
            "location",
            (
                ("snap.location", out.get("location")),
                ("dashboard.location", dashboard.get("location")),
            ),
            "snap.location" if out.get("location") else "dashboard.location",
        ),
        _context_conflict(
            "timezone",
            (
                ("snap.timezone", out.get("timezone")),
                ("dashboard.timezone", dashboard.get("timezone")),
            ),
            timezone_source,
        ),
    ):
        if conflict:
            conflicts.append(conflict)

    snap_coords = coordinate_pair_from_value({
        "latitude": out.get("latitude"),
        "longitude": out.get("longitude"),
    }) or coordinate_pair_from_value(out.get("coords"))
    dashboard_coords = coordinate_pair_from_value({
        "latitude": dashboard.get("latitude"),
        "longitude": dashboard.get("longitude"),
    }) or coordinate_pair_from_value(dashboard.get("coords"))
    coordinate_conflict = _context_conflict(
        "coordinates",
        (("snap", snap_coords), ("dashboard", dashboard_coords)),
        coordinate_source,
    )
    if coordinate_conflict:
        conflicts.append(coordinate_conflict)

    chart_snapshot = out.get("chart_snapshot") if isinstance(out.get("chart_snapshot"), dict) else {}
    dashboard_chart_fingerprint = chart_fingerprint(dashboard)
    saved_chart_fingerprint = chart_fingerprint(chart_snapshot)
    if saved_chart_fingerprint and dashboard_chart_fingerprint and saved_chart_fingerprint != dashboard_chart_fingerprint:
        conflicts.append({
            "field": "chart_geometry",
            "candidates": [
                {"source": "snap.chart_snapshot", "fingerprint": saved_chart_fingerprint},
                {"source": "dashboard", "fingerprint": dashboard_chart_fingerprint},
            ],
            "selected_source": "snap.chart_snapshot",
            "resolution": "purpose_built_chart_snapshot_precedence_without_deleting_dashboard",
        })
    selected_chart_fingerprint = saved_chart_fingerprint or dashboard_chart_fingerprint

    if not legacy_record and isinstance(existing_context.get("conflicts"), list):
        combined_conflicts = copy.deepcopy(existing_context.get("conflicts") or [])
        known = {
            json.dumps(item, sort_keys=True, default=str)
            for item in combined_conflicts
            if isinstance(item, dict)
        }
        for item in conflicts:
            encoded = json.dumps(item, sort_keys=True, default=str)
            if encoded not in known:
                known.add(encoded)
                combined_conflicts.append(item)
        conflicts = combined_conflicts

    context = {
        "instant_utc": instant_utc,
        "local_datetime": time_context.get("local_datetime"),
        "timezone": timezone_name,
        "timezone_label": timezone_label,
        "timezone_source": timezone_source,
        "location": location,
        "latitude": coords[0] if coords else None,
        "longitude": coords[1] if coords else None,
        "coordinate_provenance": coordinate_provenance,
        "house_system_code": house_system,
        "time_provenance": time_context,
        "conflicts": conflicts,
        "review_required": bool(
            not timezone_name
            or time_context.get("ambiguous")
            or coordinate_provenance.get("review_required")
            or conflicts
        ),
    }
    context["context_fingerprint"] = _context_fingerprint(context)
    context["chart_fingerprint"] = selected_chart_fingerprint

    out["schema_version"] = SNAP_RECORD_SCHEMA_VERSION
    out["effective_datetime"] = instant_utc
    out["local_datetime"] = time_context.get("local_datetime")
    out["location"] = location
    out["timezone"] = timezone_name
    out["timezone_label"] = timezone_label
    out["latitude"] = coords[0] if coords else None
    out["longitude"] = coords[1] if coords else None
    out["coordinate_provenance"] = coordinate_provenance
    out["calculation_context"] = context
    out["chart_fingerprint"] = selected_chart_fingerprint

    dashboard["timestamp"] = instant_utc
    dashboard["local_datetime"] = time_context.get("local_datetime")
    dashboard["location"] = location
    dashboard["timezone"] = timezone_name
    dashboard["timezone_label"] = timezone_label
    if coords:
        dashboard["latitude"], dashboard["longitude"] = coords
    dashboard["coordinate_provenance"] = copy.deepcopy(coordinate_provenance)
    dashboard["calculation_context"] = copy.deepcopy(context)
    out["dashboard"] = dashboard

    if legacy_record:
        migration = copy.deepcopy(out.get("migration")) if isinstance(out.get("migration"), dict) else {}
        migration.update({
            "from_schema_version": previous_schema,
            "to_schema_version": SNAP_RECORD_SCHEMA_VERSION,
            "original_context": {
                "effective_datetime": original.get("effective_datetime"),
                "dashboard_timestamp": (
                    original.get("dashboard", {}).get("timestamp")
                    if isinstance(original.get("dashboard"), dict)
                    else None
                ),
                "timezone": original.get("timezone"),
                "timezone_label": original.get("timezone_label"),
                "dashboard_timezone": (
                    original.get("dashboard", {}).get("timezone")
                    if isinstance(original.get("dashboard"), dict)
                    else None
                ),
                "dashboard_timezone_label": (
                    original.get("dashboard", {}).get("timezone_label")
                    if isinstance(original.get("dashboard"), dict)
                    else None
                ),
                "coords": copy.deepcopy(original.get("coords")),
                "latitude": original.get("latitude"),
                "longitude": original.get("longitude"),
            },
            "review_required": bool(context["review_required"]),
        })
        out["migration"] = migration
    return out


def semantic_snapshot_key(snap: Dict[str, Any]) -> Optional[str]:
    context = snap.get("calculation_context") if isinstance(snap.get("calculation_context"), dict) else {}
    chart_hash = snap.get("chart_fingerprint") or context.get("chart_fingerprint")
    if not chart_hash:
        return None
    payload = {
        "instant_utc": context.get("instant_utc") or snap.get("effective_datetime"),
        "timezone": context.get("timezone") or snap.get("timezone"),
        "location": _normalized_location(context.get("location") or snap.get("location")),
        "latitude": context.get("latitude"),
        "longitude": context.get("longitude"),
        "house_system_code": context.get("house_system_code"),
        "chart_fingerprint": chart_hash,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def annotate_semantic_duplicates(snaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mark duplicate groups while keeping every user record."""
    out = [copy.deepcopy(snap) for snap in snaps]
    groups: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for index, snap in enumerate(out):
        snap.pop("duplicate_group", None)
        key = semantic_snapshot_key(snap)
        if key:
            groups.setdefault(key, []).append((index, snap))
    for semantic_key, members in groups.items():
        if len(members) < 2:
            continue
        sorted_ids = sorted(
            str(snap.get("id") or f"record-{index}")
            for index, snap in members
        )
        canonical_id = sorted_ids[0]
        for index, snap in members:
            snap_id = str(snap.get("id") or f"record-{index}")
            snap["duplicate_group"] = {
                "semantic_key": semantic_key,
                "canonical_id": canonical_id,
                "member_ids": sorted_ids,
                "is_canonical": snap_id == canonical_id,
                "records_preserved": True,
            }
    return out


def migrate_snapshot_store_document(data: Any) -> Tuple[Dict[str, Any], bool]:
    """Normalize a complete store document and return ``(document, changed)``."""
    source = copy.deepcopy(data) if isinstance(data, dict) else {"snaps": []}
    raw_snaps = source.get("snaps")
    if not isinstance(raw_snaps, list):
        raw_snaps = []
    migrated_records = [
        canonicalize_snapshot_record(snap)
        for snap in raw_snaps
        if isinstance(snap, dict)
    ]
    migrated_records = annotate_semantic_duplicates(migrated_records)
    duplicate_groups: Dict[str, Dict[str, Any]] = {}
    for snap in migrated_records:
        group = snap.get("duplicate_group")
        if isinstance(group, dict):
            duplicate_groups[str(group.get("semantic_key"))] = {
                "semantic_key": group.get("semantic_key"),
                "canonical_id": group.get("canonical_id"),
                "member_ids": group.get("member_ids"),
                "records_preserved": True,
            }

    previous_report = source.get("migration_report")
    previous_migrated = (
        int(previous_report.get("migrated_records") or 0)
        if isinstance(previous_report, dict)
        else 0
    )
    newly_migrated = sum(
        1
        for snap in raw_snaps
        if isinstance(snap, dict) and snap.get("schema_version") != SNAP_RECORD_SCHEMA_VERSION
    )
    source["schema_version"] = SNAP_STORE_SCHEMA_VERSION
    source["snaps"] = migrated_records
    stable_report = copy.deepcopy(previous_report) if isinstance(previous_report, dict) else {}
    stable_report.update({
        "schema_version": SNAP_STORE_SCHEMA_VERSION,
        "record_count": len(migrated_records),
        "migrated_records": previous_migrated + newly_migrated,
        "semantic_duplicate_groups": sorted(
            duplicate_groups.values(),
            key=lambda row: str(row.get("semantic_key") or ""),
        ),
        "duplicates_removed": 0,
    })
    source["migration_report"] = stable_report
    source.setdefault("tombstones", {})
    source.setdefault("legacy_imports", {})
    return source, source != data
