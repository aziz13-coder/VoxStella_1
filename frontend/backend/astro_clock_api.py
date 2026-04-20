# -*- coding: utf-8 -*-
"""
Astro Clock API blueprint (root cause fix)

Registers the actual endpoints used by the frontend under
`/api/astro-clock/*`. This replaces the previous shim so routes are
properly available without indirection.
"""

from __future__ import annotations

import csv
import copy
import hashlib
import json
import os
import sys
import logging
import threading
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from collections import Counter
from datetime import datetime, timezone, time as dt_time, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional, Tuple, List, Iterable, Set
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request, Response, stream_with_context, has_request_context
from functools import wraps

from astro_clock_engine import AstroClockEngine, AstroClockSettings, ClockMode
from planetary_hours import PlanetaryHoursCalculator, DailyPlanetaryHours, PlanetaryHour
from horary_engine.services.geolocation import safe_geocode, LocationError, TimezoneManager
from horary_engine.serialization import deserialize_chart_for_evaluation
from horary_engine.reception import TraditionalReceptionCalculator
from models import Planet
from fixed_stars import compute_fixed_star_hits, FIXED_STAR_CATALOG
from arabic_parts import compute_arabic_parts
from sect import compute_sect_info
from moon_voc_timeline import build_moon_voc_timeline
from astro_clock_metrics import compute_metrics
from cusp_aspects import compute_cusp_aspects
from planetary_aspects_precise import compute_planetary_aspects_precise
from almutens import compute_chart_almutens
from asteroids import (
    compute_asteroid_positions,
    _resolve_ephemeris_path as _resolve_synastry_ephemeris_path,
)
from moon_day import compute_moon_day
from flask import stream_with_context

try:
    from morin_aspects import (
        compute_morin_aspects,
        compute_morin_antiscia,
        compute_morin_contra_antiscia,
        compute_morin_combustion,
        compute_morin_patterns,
    )
except Exception:  # pragma: no cover - Morin optional when Swiss ephemeris missing
    compute_morin_aspects = None  # type: ignore
    compute_morin_antiscia = None  # type: ignore
    compute_morin_contra_antiscia = None  # type: ignore
    compute_morin_combustion = None  # type: ignore
    compute_morin_patterns = None  # type: ignore

logger = logging.getLogger(__name__)

astro_clock_bp = Blueprint('astro_clock', __name__, url_prefix='/api/astro-clock')

_STREAM_MAX_STEPS = max(100, int(os.environ.get("VOX_STELLA_STREAM_MAX_STEPS", "5000")))
_STREAM_MAX_WINDOW_HOURS = max(1.0, float(os.environ.get("VOX_STELLA_STREAM_MAX_WINDOW_HOURS", "720")))
_STREAM_BUFFER_ROWS = max(50, int(os.environ.get("VOX_STELLA_STREAM_BUFFER_ROWS", "750")))
_STREAM_BUFFER_PREDICTIONS = max(50, int(os.environ.get("VOX_STELLA_STREAM_BUFFER_PREDICTIONS", "500")))
_TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE = max(
    3,
    int(os.environ.get("VOX_STELLA_TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE", "32")),
)
_PD_WINDOWS_CACHE_MAX = max(16, int(os.environ.get("VOX_STELLA_PD_WINDOWS_CACHE_MAX", "128")))
_PD_WINDOWS_CACHE: Dict[Tuple[str, Tuple[int, ...], str], List[Dict[str, Any]]] = {}
_PD_WINDOWS_CACHE_LOCK = threading.RLock()
_MORIN_PAYLOAD_CACHE_MAX = max(16, int(os.environ.get("VOX_STELLA_MORIN_CACHE_MAX", "128")))
_MORIN_PAYLOAD_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_MORIN_PAYLOAD_CACHE_LOCK = threading.RLock()

_engine: Optional[AstroClockEngine] = None
_engine_lock = threading.RLock()
_traits_engine = None
_traits_engine_lock = threading.RLock()
_tz_mgr: Optional[TimezoneManager] = None
_ph_calc: Optional[PlanetaryHoursCalculator] = None
_ph_coords: Optional[Tuple[float, float]] = None
_research_sessions: Dict[str, Dict[str, Any]] = {}
_research_lock = threading.Lock()
_atlas_search_sessions: Dict[str, Dict[str, Any]] = {}
_atlas_search_lock = threading.Lock()
_ATLAS_SEARCH_SESSION_MAX = max(8, int(os.environ.get("VOX_STELLA_ATLAS_SEARCH_SESSION_MAX", "48")))
_ATLAS_SEARCH_SESSION_TTL_SECONDS = max(60.0, float(os.environ.get("VOX_STELLA_ATLAS_SEARCH_SESSION_TTL_SECONDS", "1800")))
_mundane_scan_sessions: Dict[str, Dict[str, Any]] = {}
_mundane_scan_lock = threading.Lock()
_weather_scan_sessions: Dict[str, Dict[str, Any]] = {}
_weather_scan_lock = threading.Lock()
_research_cache_dir = Path(__file__).resolve().parent / 'research' / '.cache'
_research_default_time = "23:30"
_research_default_location = "Tel Aviv, Israel"
_research_default_coords = (32.0853, 34.7818)
_research_default_tz = "Asia/Jerusalem"
_ASTRO_PERF_STACK: ContextVar[Tuple[str, ...]] = ContextVar('astro_perf_stack', default=())
_ASTRO_PERF_REQUEST: ContextVar[Optional[str]] = ContextVar('astro_perf_request', default=None)
_BUSINESS_BETA_EXTRACTION_LEVEL_DEFAULT = 67.0
_BUSINESS_BETA_EXTRACTION_MODES = {'total', 'detail'}
_BUSINESS_BETA_EXTRACTION_SCOPES = {'all', 'current', 'selected'}


def _validate_stream_scan_bounds(start_dt: datetime, end_dt: datetime, step_minutes: int) -> Tuple[Optional[int], Optional[str]]:
    """Validate stream scan ranges to prevent unbounded CPU usage."""
    if end_dt <= start_dt:
        return None, "End must be after start"
    if step_minutes < 1:
        return None, "step_minutes must be >= 1"

    span_seconds = (end_dt - start_dt).total_seconds()
    span_hours = span_seconds / 3600.0
    if span_hours > _STREAM_MAX_WINDOW_HOURS:
        return None, (
            f"Requested range exceeds max window of {_STREAM_MAX_WINDOW_HOURS:g} hours"
        )

    total_steps = int(span_seconds // (step_minutes * 60)) + 1
    if total_steps > _STREAM_MAX_STEPS:
        return None, (
            f"Requested scan would process {total_steps} steps; max is {_STREAM_MAX_STEPS}"
        )
    return max(1, total_steps), None


def _parse_local_time_bound(raw_value: Optional[str], *, label: str) -> Tuple[Optional[int], Optional[str]]:
    if raw_value in (None, '', 'null'):
        return None, None
    text = str(raw_value).strip()
    if not text or text.lower() == 'null':
        return None, None
    if ':' in text:
        parts = text.split(':', 1)
        if len(parts) != 2:
            return None, f'{label} must be an integer hour or HH:MM'
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except Exception:
            return None, f'{label} must be an integer hour or HH:MM'
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None, f'{label} must be within 00:00-23:59'
        return (hour * 60) + minute, None
    try:
        hour = int(text)
    except Exception:
        return None, f'{label} must be an integer hour or HH:MM'
    if not (0 <= hour <= 23):
        return None, f'{label} must be within 00:00-23:59'
    return hour * 60, None


def _reduce_series_rows(
    rows: List[Dict[str, Any]],
    max_rows: int,
    *,
    pinned_timestamps: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    if len(rows) <= max_rows:
        return list(rows)

    pinned_keys = {str(ts) for ts in (pinned_timestamps or []) if ts}
    keep: Dict[str, Dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        ts = str(row.get('timestamp') or row.get('timestamp_local') or '')
        if not ts:
            continue
        if idx in {0, len(rows) - 1} or ts in pinned_keys:
            keep[ts] = row

    if len(keep) >= max_rows:
        return sorted(
            keep.values(),
            key=lambda row: str(row.get('timestamp') or row.get('timestamp_local') or ''),
        )[:max_rows]

    remaining = [
        row for row in rows
        if str(row.get('timestamp') or row.get('timestamp_local') or '') not in keep
    ]
    remaining_slots = max_rows - len(keep)
    if remaining_slots > 0 and remaining:
        chunk_size = max(1, (len(remaining) + remaining_slots - 1) // remaining_slots)
        for index in range(0, len(remaining), chunk_size):
            chunk = remaining[index:index + chunk_size]
            if not chunk:
                continue
            representative = max(chunk, key=lambda row: float(row.get('score') or 0.0))
            ts = str(representative.get('timestamp') or representative.get('timestamp_local') or '')
            if ts and ts not in keep:
                keep[ts] = representative

    reduced = sorted(
        keep.values(),
        key=lambda row: str(row.get('timestamp') or row.get('timestamp_local') or ''),
    )
    if len(reduced) <= max_rows:
        return reduced

    base_keys = {
        str(row.get('timestamp') or row.get('timestamp_local') or '')
        for row in reduced
        if str(row.get('timestamp') or row.get('timestamp_local') or '') in pinned_keys
    }
    base_keys.update(
        str(row.get('timestamp') or row.get('timestamp_local') or '')
        for row in reduced[:1] + reduced[-1:]
        if str(row.get('timestamp') or row.get('timestamp_local') or '')
    )
    base_rows = [
        row for row in reduced
        if str(row.get('timestamp') or row.get('timestamp_local') or '') in base_keys
    ]
    base_lookup = {
        str(row.get('timestamp') or row.get('timestamp_local') or ''): row
        for row in base_rows
    }
    filler_rows = [
        row for row in reduced
        if str(row.get('timestamp') or row.get('timestamp_local') or '') not in base_lookup
    ]
    filler_slots = max(0, max_rows - len(base_lookup))
    if filler_slots <= 0:
        return sorted(base_lookup.values(), key=lambda row: str(row.get('timestamp') or row.get('timestamp_local') or ''))[:max_rows]

    filler = _reduce_series_rows(filler_rows, filler_slots, pinned_timestamps=())
    combined: Dict[str, Dict[str, Any]] = dict(base_lookup)
    for row in filler:
        ts = str(row.get('timestamp') or row.get('timestamp_local') or '')
        if ts and ts not in combined:
            combined[ts] = row
    return sorted(
        combined.values(),
        key=lambda row: str(row.get('timestamp') or row.get('timestamp_local') or ''),
    )[:max_rows]


def _row_timestamp_key(row: Dict[str, Any]) -> str:
    return str(row.get('timestamp') or row.get('timestamp_local') or '')


def _row_timestamp_value(row: Dict[str, Any]) -> Optional[datetime]:
    raw = row.get('timestamp') or row.get('timestamp_local')
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except Exception:
        return None


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if result == result and result not in {float('inf'), float('-inf')} else default
    except Exception:
        return default


def _parse_business_beta_level_percent(raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except Exception:
        return _BUSINESS_BETA_EXTRACTION_LEVEL_DEFAULT
    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return value


def _resolve_business_beta_line_selection(
    line_order: List[str],
    *,
    scope: str,
    current_line_id: Optional[str] = None,
    selected_line_ids: Optional[Iterable[str]] = None,
) -> List[str]:
    available = [str(line_id) for line_id in line_order if str(line_id).strip()]
    if not available:
        return []
    current_key = str(current_line_id or '').strip()
    selected_keys = [str(line_id).strip() for line_id in (selected_line_ids or []) if str(line_id).strip()]
    if scope == 'current':
        return [current_key] if current_key in available else [available[0]]
    if scope == 'selected':
        kept = [line_id for line_id in selected_keys if line_id in available]
        return kept or list(available)
    return list(available)


def _extract_business_beta_periods(
    rows: List[Dict[str, Any]],
    *,
    step_td: timedelta,
    display_mode: str,
    scope: str,
    level_percent: float,
    current_line_id: Optional[str] = None,
    selected_line_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    copied_rows = [copy.deepcopy(row) for row in rows if isinstance(row, dict)]
    line_order: List[str] = []
    line_stats_map: Dict[str, Dict[str, Any]] = {}

    for row in copied_rows:
        for line in list(row.get('lines') or []):
            if not isinstance(line, dict):
                continue
            line_id = str(line.get('id') or '').strip()
            if not line_id:
                continue
            if line_id not in line_order:
                line_order.append(line_id)
            score = _coerce_float(line.get('score'))
            favorable = _coerce_float(line.get('favorable'), max(score, 0.0))
            tense = _coerce_float(line.get('tense'), max(-score, 0.0))
            line['favorable'] = round(favorable, 2)
            line['tense'] = round(tense, 2)
            stats = line_stats_map.setdefault(
                line_id,
                {
                    'id': line_id,
                    'label': str(line.get('label') or line_id),
                    'kind': str(line.get('kind') or 'line'),
                    'fmax': score,
                    'fmin': score,
                },
            )
            stats['fmax'] = max(_coerce_float(stats.get('fmax')), score)
            stats['fmin'] = min(_coerce_float(stats.get('fmin')), score)

    for stats in line_stats_map.values():
        amplitude = max(_coerce_float(stats.get('fmax')), abs(_coerce_float(stats.get('fmin'))))
        stats['threshold'] = round(amplitude * (level_percent / 100.0), 2)
        stats['amplitude'] = round(amplitude, 2)

    resolved_scope = scope if scope in _BUSINESS_BETA_EXTRACTION_SCOPES else 'all'
    resolved_mode = display_mode if display_mode in _BUSINESS_BETA_EXTRACTION_MODES else 'total'
    resolved_selected_line_ids = _resolve_business_beta_line_selection(
        line_order,
        scope=resolved_scope,
        current_line_id=current_line_id,
        selected_line_ids=selected_line_ids,
    )

    extraction_rows: List[Dict[str, Any]] = []
    period_rows: List[Dict[str, Any]] = []
    step_seconds = max(60.0, float(step_td.total_seconds() or 0.0))

    for row in copied_rows:
        aggregate_score = _coerce_float(row.get('score'))
        row['aggregate_score'] = round(aggregate_score, 2)
        row_lookup = {
            str(line.get('id') or '').strip(): line
            for line in list(row.get('lines') or [])
            if isinstance(line, dict) and str(line.get('id') or '').strip()
        }

        selected_metric_total = 0.0
        selected_threshold_total = 0.0
        line_states: List[Dict[str, Any]] = []
        row_passes = bool(resolved_selected_line_ids)

        for line_id in resolved_selected_line_ids:
            stats = line_stats_map.get(line_id) or {}
            line = row_lookup.get(line_id)
            line_score = _coerce_float((line or {}).get('score'))
            favorable = _coerce_float((line or {}).get('favorable'), max(line_score, 0.0))
            tense = _coerce_float((line or {}).get('tense'), max(-line_score, 0.0))
            threshold = _coerce_float(stats.get('threshold'))
            metric = line_score if resolved_mode == 'total' else favorable
            passed = bool(line) and metric >= threshold
            selected_metric_total += metric
            selected_threshold_total += threshold
            if not passed:
                row_passes = False
            line_states.append(
                {
                    'id': line_id,
                    'label': str(stats.get('label') or line_id),
                    'kind': str(stats.get('kind') or 'line'),
                    'score': round(line_score, 2),
                    'favorable': round(favorable, 2),
                    'tense': round(tense, 2),
                    'threshold': round(threshold, 2),
                    'metric': round(metric, 2),
                    'passed': passed,
                }
            )

        row['score'] = round(selected_metric_total, 2) if resolved_selected_line_ids else round(aggregate_score, 2)
        row['business_beta_pass'] = bool(row_passes)
        row['business_beta_line_states'] = line_states
        row['business_beta_selected_line_ids'] = list(resolved_selected_line_ids)
        row['business_beta_selected_threshold'] = round(selected_threshold_total, 2)
        extraction_rows.append(row)
        if row_passes:
            period_rows.append(row)

    periods: List[Dict[str, Any]] = []
    current_period: Optional[Dict[str, Any]] = None
    last_dt: Optional[datetime] = None

    for row in period_rows:
        row_dt = _row_timestamp_value(row)
        starts_new_period = (
            current_period is None
            or row_dt is None
            or last_dt is None
            or (row_dt - last_dt).total_seconds() > (step_seconds * 1.5)
        )
        if starts_new_period:
            current_period = {
                'rows': [],
            }
            periods.append(current_period)
        current_period['rows'].append(row)
        last_dt = row_dt

    period_payloads: List[Dict[str, Any]] = []
    for index, period in enumerate(periods, start=1):
        period_rows_list = list(period.get('rows') or [])
        if not period_rows_list:
            continue
        ranked_rows = sorted(
            period_rows_list,
            key=lambda item: (-_coerce_float(item.get('score')), _row_timestamp_key(item)),
        )
        best_row = ranked_rows[0]
        start_row = period_rows_list[0]
        end_row = period_rows_list[-1]
        period_payloads.append(
            {
                'id': f'business-beta-period:{index}',
                'start': start_row.get('timestamp'),
                'start_local': start_row.get('timestamp_local'),
                'end': end_row.get('timestamp'),
                'end_local': end_row.get('timestamp_local'),
                'best_timestamp': best_row.get('timestamp'),
                'best_timestamp_local': best_row.get('timestamp_local'),
                'best_score': round(_coerce_float(best_row.get('score')), 2),
                'row_count': len(period_rows_list),
                'selected_line_ids': list(resolved_selected_line_ids),
            }
        )

    top_rows = [
        next(
            (
                row for row in extraction_rows
                if _row_timestamp_key(row) == str(period.get('best_timestamp') or '')
            ),
            None,
        )
        for period in sorted(period_payloads, key=lambda item: (-_coerce_float(item.get('best_score')), str(item.get('best_timestamp') or '')))
    ]
    top_rows = [row for row in top_rows if isinstance(row, dict)]

    return {
        'rows': extraction_rows,
        'top_rows': top_rows,
        'periods': period_payloads,
        'line_stats': [line_stats_map[line_id] for line_id in line_order if line_id in line_stats_map],
        'selected_line_ids': list(resolved_selected_line_ids),
        'display_mode': resolved_mode,
        'scope': resolved_scope,
        'level_percent': round(level_percent, 2),
        'passing_row_count': len(period_rows),
        'period_count': len(period_payloads),
    }


def _engine_instance() -> AstroClockEngine:
    global _engine
    if _engine is None:
        _engine = AstroClockEngine()
    return _engine


def _traits_engine_instance():
    global _traits_engine
    if _traits_engine is None:
        with _traits_engine_lock:
            if _traits_engine is None:
                from traits.engine import TraitEngine

                _traits_engine = TraitEngine()
    return _traits_engine


def _tz_instance() -> TimezoneManager:
    global _tz_mgr
    if _tz_mgr is None:
        _tz_mgr = TimezoneManager()
    return _tz_mgr


def _ph_instance(lat: float, lon: float) -> PlanetaryHoursCalculator:
    global _ph_calc, _ph_coords
    if _ph_calc is None or _ph_coords != (lat, lon):
        _ph_calc = PlanetaryHoursCalculator(latitude=lat, longitude=lon)
        _ph_coords = (lat, lon)
    return _ph_calc


def _research_mode_enabled() -> bool:
    """Enable research mode only when explicitly allowed in development."""

    def _truthy(value: Optional[str]) -> bool:
        return (value or "").strip().lower() in {"1", "true", "yes"}

    disable_flag = os.environ.get('VOX_STELLA_DISABLE_RESEARCH') or os.environ.get('VOX_STELLA_RESEARCH_DISABLED')
    if _truthy(disable_flag):
        return False

    explicit_enable = os.environ.get('VOX_STELLA_ENABLE_RESEARCH')
    if explicit_enable is not None:
        return _truthy(explicit_enable)

    is_packaged = getattr(sys, "frozen", False) or _truthy(os.environ.get("APP_IS_PACKAGED"))
    if is_packaged:
        return False

    env_name = (os.environ.get("FLASK_ENV") or "").strip().lower()
    return env_name in {"dev", "development", "local", "test", "testing"}


def _ensure_research_cache_dir() -> Path:
    _research_cache_dir.mkdir(parents=True, exist_ok=True)
    return _research_cache_dir


def _research_session_id(path: str, time_str: str, location: str, row_limit: Optional[int]) -> str:
    raw = f"{path}|{time_str}|{location}|{row_limit or ''}"
    return hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()


def _parse_time_str(time_str: Optional[str]) -> dt_time:
    s = (time_str or _research_default_time).strip()
    for fmt in ("%H:%M", "%H.%M", "%I:%M %p", "%I.%M %p"):
        try:
            t = datetime.strptime(s, fmt).time()
            return t
        except Exception:
            continue
    # Default to 23:30 Israel time
    return dt_time(23, 30)


def _safe_research_path(path_str: str) -> Path:
    base = Path(__file__).resolve().parent.parent  # repo/backend root
    p = Path(path_str)
    if not p.is_absolute():
        p = base / p
    try:
        p.resolve().relative_to(base)
    except Exception:
        raise ValueError("Invalid path")
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p


def _to_jsonable(obj):
    from enum import Enum
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, Enum):
        return getattr(obj, 'value', str(obj))
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    try:
        return str(obj)
    except Exception:
        return None


def _truthy_env(value: Optional[str]) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _astro_perf_enabled() -> bool:
    return (
        _truthy_env(os.environ.get('VOX_STELLA_ASTRO_PERF'))
        or _truthy_env(os.environ.get('VOX_STELLA_ASTRO_TIMINGS'))
    )


@contextmanager
def _astro_perf_span(name: str, **meta: Any):
    if not _astro_perf_enabled():
        yield
        return

    request_token = None
    request_id = _ASTRO_PERF_REQUEST.get()
    if not request_id:
        request_id = uuid4().hex[:8]
        request_token = _ASTRO_PERF_REQUEST.set(request_id)

    stack = _ASTRO_PERF_STACK.get()
    stack_token = _ASTRO_PERF_STACK.set(stack + (name,))
    started = perf_counter()
    try:
        yield
    finally:
        duration_ms = (perf_counter() - started) * 1000.0
        fields = [
            f"request={request_id}",
            f"depth={len(stack)}",
            f"span={name}",
            f"duration_ms={duration_ms:.2f}",
        ]
        if has_request_context():
            try:
                fields.insert(1, f"path={request.path}")
            except Exception:
                pass
        clean_meta = {k: v for k, v in meta.items() if v is not None}
        if clean_meta:
            try:
                meta_json = json.dumps(_to_jsonable(clean_meta), sort_keys=True, ensure_ascii=False)
                fields.append(f"meta={meta_json}")
            except Exception:
                pass
        logger.info("[astro-perf] %s", " ".join(fields))
        _ASTRO_PERF_STACK.reset(stack_token)
        if request_token is not None:
            _ASTRO_PERF_REQUEST.reset(request_token)


def _json_ok(data: Dict[str, Any]) -> Response:
    return jsonify({'success': True, 'data': _to_jsonable(data)})


def _safe_astrocartography_optional_payload(
    label: str,
    builder,
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        payload = builder()
        if isinstance(payload, dict):
            return payload
    except Exception:
        logger.exception("Astrocartography optional payload failed: %s", label)
    return copy.deepcopy(fallback)


def _reception_summary_label(reception_type: Optional[str]) -> str:
    key = str(reception_type or 'none').strip().lower()
    if key == 'mutual_rulership':
        return 'Mutual domicile reception'
    if key == 'mutual_exaltation':
        return 'Mutual exaltation reception'
    if key == 'mutual_term':
        return 'Mutual term reception'
    if key == 'mutual_face':
        return 'Mutual face reception'
    if key == 'mixed_reception':
        return 'Mixed reception'
    if key == 'unilateral':
        return 'Unilateral reception'
    return 'No reception'


def _build_reception_summary(
    mutual: Optional[List[Dict[str, Any]]],
    unilateral: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    mutual_list = mutual if isinstance(mutual, list) else []
    unilateral_list = unilateral if isinstance(unilateral, list) else []

    if mutual_list:
        ranked = sorted(
            mutual_list,
            key=lambda item: (
                -int(item.get('strength') or 0),
                str(item.get('type') or ''),
                str(item.get('p1') or ''),
                str(item.get('p2') or ''),
            ),
        )
        top = ranked[0]
        summary_type = str(top.get('type') or 'mixed_reception')
    elif unilateral_list:
        summary_type = 'unilateral'
    else:
        summary_type = 'none'

    return {
        'type': summary_type,
        'display_text': _reception_summary_label(summary_type),
        'mutual_count': len(mutual_list),
        'unilateral_count': len(unilateral_list),
    }


def _normalize_chart_data_for_receptions(source_cd: Any) -> Dict[str, Any]:
    if isinstance(source_cd, str):
        try:
            source_cd = json.loads(source_cd)
        except Exception:
            source_cd = {}
    if not isinstance(source_cd, dict):
        return {}

    allowed = {'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn'}
    normalized = dict(source_cd)

    pls = normalized.get('planets')
    if isinstance(pls, list):
        try:
            planet_map = {}
            for p in pls:
                if not isinstance(p, dict):
                    continue
                nm = p.get('planet') or p.get('name')
                if nm in allowed:
                    planet_map[str(nm)] = {k: v for k, v in p.items() if k not in ('planet', 'name')}
            normalized['planets'] = planet_map
        except Exception:
            pass
    elif isinstance(pls, dict):
        try:
            normalized['planets'] = {k: v for k, v in pls.items() if k in allowed and isinstance(v, dict)}
        except Exception:
            pass

    try:
        asp = normalized.get('aspects')
        if isinstance(asp, list):
            clean = []
            for a in asp:
                if not isinstance(a, dict):
                    continue
                p1 = str(a.get('planet1') or a.get('p1') or '')
                p2 = str(a.get('planet2') or a.get('p2') or '')
                if p1 in allowed and p2 in allowed:
                    clean.append(a)
            normalized['aspects'] = clean
    except Exception:
        pass

    try:
        hr = normalized.get('house_rulers')
        if isinstance(hr, dict):
            allowed_map = {p.lower(): p for p in allowed}
            clean_hr = {}
            for h, r in hr.items():
                if not isinstance(r, str):
                    continue
                letters_only = ''.join(ch for ch in r if ch.isalpha()).lower()
                if letters_only in allowed_map:
                    clean_hr[str(h)] = allowed_map[letters_only]
            normalized['house_rulers'] = clean_hr
    except Exception:
        pass

    try:
        allowed_planets = {p.lower() for p in allowed}
        if isinstance(normalized.get('moon_last_aspect'), dict):
            last_planet = str(normalized['moon_last_aspect'].get('planet', '')).replace(' ', '_').lower()
            if last_planet not in allowed_planets:
                normalized['moon_last_aspect'] = None
        if isinstance(normalized.get('moon_next_aspect'), dict):
            next_planet = str(normalized['moon_next_aspect'].get('planet', '')).replace(' ', '_').lower()
            if next_planet not in allowed_planets:
                normalized['moon_next_aspect'] = None
    except Exception:
        pass

    return normalized


def _extract_receptions_payload(chart: Any) -> Dict[str, Any]:
    chart_dict = chart if isinstance(chart, dict) else {}
    source_cd = _extract_chart_data_from_result(chart_dict) if chart_dict else {}
    details = chart_dict.get('reception_details') or (source_cd.get('reception_details') if isinstance(source_cd, dict) else None)

    mutual: List[Dict[str, Any]] = []
    top_unilateral: List[Dict[str, Any]] = []

    if isinstance(details, dict):
        for m in details.get('mutual_receptions', []) or []:
            if isinstance(m, dict):
                mutual.append({
                    'p1': m.get('planet1') or m.get('a') or '—',
                    'p2': m.get('planet2') or m.get('b') or '—',
                    'type': m.get('type') or 'mutual_reception',
                    'strength': m.get('strength') or m.get('score') or 0,
                })
        for u in details.get('one_way_receptions', []) or []:
            if isinstance(u, dict):
                top_unilateral.append({
                    'receiving': u.get('receiver') or '—',
                    'received': u.get('received') or '—',
                    'dignities': list(u.get('dignity', [])) if isinstance(u.get('dignity'), list) else ([u.get('dignity')] if u.get('dignity') else []),
                    'strength': u.get('strength') or 0,
                })

    if not mutual and not top_unilateral:
        try:
            chart_obj = _extract_internal_chart_from_result(chart_dict) if chart_dict else None
            if chart_obj is None:
                normalized_cd = _normalize_chart_data_for_receptions(source_cd)
                chart_obj = deserialize_chart_for_evaluation(normalized_cd) if normalized_cd else None
            if chart_obj is not None:
                calc = TraditionalReceptionCalculator()
                classical = [Planet.SUN, Planet.MOON, Planet.MERCURY, Planet.VENUS, Planet.MARS, Planet.JUPITER, Planet.SATURN]
                tmp_mutual: List[Tuple[str, str, str, int]] = []
                tmp_uni: List[Tuple[str, str, List[str], int]] = []
                for i in range(len(classical)):
                    for j in range(i + 1, len(classical)):
                        a = classical[i]
                        b = classical[j]
                        comp = calc.calculate_comprehensive_reception(chart_obj, a, b)
                        rtype = comp.get('type') or 'none'
                        if rtype in ('mutual_rulership', 'mutual_exaltation', 'mutual_term', 'mutual_face', 'mixed_reception'):
                            tmp_mutual.append((a.value, b.value, rtype, int(comp.get('traditional_strength') or 0)))
                        dir1 = calc.does_planet_receive(chart_obj, a, b)
                        if dir1.get('has_reception'):
                            tmp_uni.append((a.value, b.value, list(dir1.get('dignities') or []), int(dir1.get('reception_strength') or 0)))
                        dir2 = calc.does_planet_receive(chart_obj, b, a)
                        if dir2.get('has_reception'):
                            tmp_uni.append((b.value, a.value, list(dir2.get('dignities') or []), int(dir2.get('reception_strength') or 0)))

                seen_pairs = set()
                for p1, p2, rtype, strength in sorted(tmp_mutual, key=lambda item: (-item[3], item[0], item[1])):
                    key = (min(p1, p2), max(p1, p2), rtype)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    mutual.append({'p1': p1, 'p2': p2, 'type': rtype, 'strength': strength})

                for receiving, received, dignities, strength in sorted(tmp_uni, key=lambda item: (-item[3], item[0], item[1]))[:8]:
                    top_unilateral.append({
                        'receiving': receiving,
                        'received': received,
                        'dignities': dignities,
                        'strength': strength,
                    })
        except Exception as exc:
            logger.warning("Reception analysis fallback failed: %s", exc)

    return {
        'traditional_reception': _build_reception_summary(mutual, top_unilateral),
        'mutual': mutual,
        'top_unilateral': top_unilateral,
    }


def _direction_summary(hit: Dict[str, Any]) -> Optional[str]:
    conc = hit.get('concordance') or {}
    matches = conc.get('direction_matches') or []
    if not matches:
        return None
    first = matches[0]
    label = first.get('label') or ''
    ts = first.get('timestamp')
    if ts:
        return f"{label} @ {ts}"
    return str(label) if label else None


_EVENT_CANDIDATES = [
    'promotion','recognition','business_deal','contract_signing','communication_breakthrough','romantic_connection','romance','marriage','reconciliation',
    'financial_gain','financial_loss','injury_risk','accident_risk','public_recognition','parties_celebrations','opportunity_received',
    'protection_granted','delay_obstruction','illness_chronic','fall_from_power','authority_problems','domestic_happiness','family_joy',
    'domestic_disruption','family_problems','miscommunication','excess_problems','structure_established','discipline_rewarded','authority_earned',
    'honor_award','new_job','job_loss','inheritance','salary_increase',
    'degree_completion','exam_success','exam_failure','enrollment_admission',
    'accident_major','near_death_experience','attack_violence','fire_burn','drowning_submersion','fall_from_height',
    'publication','artistic_success','discovery_breakthrough','loss_of_possessions','reputation_damage',
    'property_value_increase','property_value_decrease','speculation_gain','speculation_loss','inheritance_windfall','shared_resource_loss',
    'spiritual_awakening','religious_conversion','pilgrimage','mystical_experience',
    'lawsuit','legal_victory','legal_defeat','legal_resolution','settlement','arrest_imprisonment',
    'illness_acute','injury_accident','surgery','hospitalization','recovery_health','fever',
    'demotion','business_success','business_failure','retirement',
    'birth_of_child','birth_self','death_natural','death_violent','death_of_family','short_journey','long_journey',
    'partnership_strengthened','partnership_strained','pregnancy','engagement','divorce','separation','betrayal',
    'investment_success','investment_loss','bankruptcy','theft_fraud','family_celebration','family_conflict','moving_home','purchase_property','relocation_permanent','travel_accident',
    'death_threat_high','death_threat_moderate','severe_illness_onset','life_threatening_accident','chronic_illness_development','sudden_health_crisis','recovery_period','vitality_strengthening',
    'exceptional_honor_received','career_elevation','disgrace_or_scandal','career_setback_major','professional_recognition','power_increase','loss_of_authority','public_humiliation',
    'major_wealth_acquisition','unexpected_financial_gain','inheritance_received','major_financial_loss','bankruptcy_risk','debt_crisis',
    'marriage_likely','significant_partnership','divorce_or_separation','relationship_crisis','harmonious_relationship_period','childbirth','loss_of_child',
    'major_lawsuit_initiated','imprisonment_risk','violent_confrontation','warfare_involvement','enemy_attack',
    'major_journey_fortunate','travel_misfortune','foreign_residence','exile_or_forced_travel',
    'intellectual_breakthrough','educational_achievement','mental_confusion_period','church_honors',
    'fateful_day_benefic','fateful_day_malefic','eclipse_activation','syzygy_critical','station_on_sensitive_point','lights_conjunction_malefic',
    'slow_planet_transit','stationary_planet_transit','retrograde_malefic','multiple_determination','cardinal_cusp_involvement','luminary_participation','dormant_direction_activated','revolution_amplified','youth_recklessness_danger','elder_health_crisis'
]

_CRISIS_EVENT_TYPES: Set[str] = {
    'war_declaration_offensive',
    'war_response_defensive',
    'internal_conflict_war',
    'warfare_involvement',
    'enemy_attack',
    'violent_confrontation',
    'attack_violence',
    'accident_major',
    'near_death_experience',
    'life_threatening_accident',
    'death_violent',
    'death_natural',
    'death_of_family',
    'death_threat_high',
    'death_threat_moderate',
    'fire_burn',
    'drowning_submersion',
    'fall_from_height',
    'injury_accident',
    'travel_accident',
    'arrest_imprisonment',
}
_CRISIS_LIFE_AREAS: Set[str] = {
    'conflict',
    'danger',
    'death',
    'health',
    'hidden_enemies',
    'prison',
    'secrets',
}
_EVENT_TYPE_PRIMARY_AREAS: Dict[str, Set[str]] = {
    'promotion': {'honors'},
    'recognition': {'honors'},
    'public_recognition': {'honors'},
    'honor_award': {'honors'},
    'authority_earned': {'honors'},
    'structure_established': {'honors'},
    'opportunity_received': {'life', 'honors', 'wealth'},
    'protection_granted': {'life', 'health', 'honors'},
    'financial_gain': {'wealth', 'money'},
    'financial_loss': {'wealth', 'money'},
    'financial_windfall': {'wealth', 'money'},
    'salary_increase': {'wealth', 'money', 'honors'},
    'speculation_gain': {'wealth', 'money'},
    'speculation_loss': {'wealth', 'money'},
    'inheritance_windfall': {'wealth', 'money'},
    'shared_resource_loss': {'wealth', 'money', 'death'},
    'property_value_increase': {'wealth', 'home'},
    'property_value_decrease': {'wealth', 'home'},
    'marriage': {'marriage', 'relationships'},
    'marriage_likely': {'marriage', 'relationships'},
    'significant_partnership': {'marriage', 'relationships'},
    'reconciliation': {'relationships', 'marriage'},
    'romantic_connection': {'relationships', 'marriage'},
    'relationship_crisis': {'relationships', 'conflict'},
    'partnership_strained': {'relationships', 'conflict'},
    'partnership_strengthened': {'relationships', 'marriage'},
    'lawsuit': {'conflict'},
    'legal_victory': {'conflict'},
    'legal_defeat': {'conflict'},
    'legal_resolution': {'conflict'},
    'settlement': {'conflict'},
    'major_lawsuit_initiated': {'conflict'},
    'attack_violence': {'conflict', 'danger'},
    'violent_confrontation': {'conflict', 'danger'},
    'enemy_attack': {'conflict', 'danger'},
    'war_declaration_offensive': {'conflict', 'danger'},
    'war_response_defensive': {'conflict', 'danger'},
    'internal_conflict_war': {'conflict', 'danger'},
    'warfare_involvement': {'conflict', 'danger'},
    'arrest_imprisonment': {'prison', 'hidden_enemies', 'secrets'},
    'accident_major': {'danger', 'death'},
    'near_death_experience': {'danger', 'death'},
    'life_threatening_accident': {'danger', 'death'},
    'drowning_submersion': {'danger', 'death'},
    'fire_burn': {'danger', 'death'},
    'fall_from_height': {'danger', 'death'},
    'injury_accident': {'danger', 'health'},
    'travel_accident': {'danger', 'death'},
    'death_natural': {'death'},
    'death_violent': {'death', 'danger'},
    'death_of_family': {'death'},
    'death_threat_high': {'danger', 'death'},
    'death_threat_moderate': {'danger', 'death'},
    'severe_illness_onset': {'health', 'danger'},
    'sudden_health_crisis': {'health', 'danger'},
}

_EVENT_TYPE_AREA_WEIGHTS: Dict[str, Dict[str, float]] = {
    'opportunity_received': {
        'life': 0.65,
        'honors': 1.0,
        'wealth': 1.0,
    },
    'protection_granted': {
        'life': 0.7,
        'health': 1.0,
        'honors': 1.0,
    },
}


def _prediction_factors(pred: Dict[str, Any]) -> Dict[str, Any]:
    factors = pred.get('factors')
    return factors if isinstance(factors, dict) else {}


def _prediction_life_area(pred: Dict[str, Any]) -> Optional[str]:
    area = pred.get('life_area')
    if not isinstance(area, str):
        return None
    return area.strip().lower()


def _prediction_domain_alignment(pred: Dict[str, Any]) -> float:
    event_type = str(pred.get('event_type') or '').strip().lower()
    life_area = _prediction_life_area(pred)
    if not event_type or not life_area:
        return 0.0
    weighted = _EVENT_TYPE_AREA_WEIGHTS.get(event_type)
    if weighted and life_area in weighted:
        return float(weighted[life_area])
    allowed = _EVENT_TYPE_PRIMARY_AREAS.get(event_type)
    if allowed and life_area in allowed:
        return 1.0
    if event_type in _CRISIS_EVENT_TYPES and life_area in _CRISIS_LIFE_AREAS:
        return 0.8
    return 0.0


def _prediction_crisis_focus(pred: Dict[str, Any]) -> float:
    event_type = str(pred.get('event_type') or '').strip().lower()
    life_area = _prediction_life_area(pred)
    if event_type not in _CRISIS_EVENT_TYPES or life_area not in _CRISIS_LIFE_AREAS:
        return 0.0
    factors = _prediction_factors(pred)
    transit = str(factors.get('transit') or '').strip().lower()
    direction = str(factors.get('direction') or '').strip().lower()
    focus = 0.0
    if any(marker in transit for marker in ('mars', 'saturn')):
        focus += 0.35
    if any(marker in transit for marker in (' asc', 'asc', ' mc', 'mc', ' dsc', 'dsc', ' ic', 'ic')):
        focus += 0.45
    if direction:
        focus += 0.2
    return round(min(1.0, focus), 3)


def _prediction_sort_key(pred: Dict[str, Any]) -> Tuple[float, float, float, float, float, float, str]:
    factors = _prediction_factors(pred)
    try:
        det_strength = abs(float(factors.get('determination_strength') or 0.0))
    except Exception:
        det_strength = 0.0
    try:
        significance = float(factors.get('significance') or 0.0)
    except Exception:
        significance = 0.0
    try:
        probability = float(pred.get('probability') or 0.0)
    except Exception:
        probability = 0.0
    try:
        score = float(pred.get('score') or 0.0)
    except Exception:
        score = 0.0
    event_type = str(pred.get('event_type') or '').strip()
    domain_alignment = _prediction_domain_alignment(pred)
    crisis_focus = _prediction_crisis_focus(pred)
    substantive_event = 1.0 if (event_type and (score > 0.0 or probability > 0.0 or significance > 0.0 or det_strength > 0.0)) else 0.0
    return (
        -domain_alignment,
        -crisis_focus,
        -score,
        -probability,
        -det_strength,
        -substantive_event,
        event_type,
    )


def _prediction_numeric(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _prediction_keyword_tokens(pred: Dict[str, Any]) -> List[str]:
    tokens: List[str] = []
    seen: Set[str] = set()

    def _push(raw: Any) -> None:
        if isinstance(raw, str):
            token = raw.strip().lower()
            if token and token not in seen:
                seen.add(token)
                tokens.append(token)
        elif isinstance(raw, (list, tuple, set)):
            for item in raw:
                _push(item)

    _push(pred.get('event_type'))
    _push(pred.get('life_area'))
    _push(pred.get('tags') or [])
    factors = _prediction_factors(pred)
    _push(factors.get('laws'))
    return tokens


def _predictor_occurrence_support(pred: Dict[str, Any]) -> float:
    factors = _prediction_factors(pred)
    domain_alignment = _prediction_domain_alignment(pred)
    crisis_focus = _prediction_crisis_focus(pred)
    probability = max(0.0, min(1.0, _prediction_numeric(pred.get('probability'))))
    score = max(0.0, _prediction_numeric(pred.get('score')))
    det_strength = abs(_prediction_numeric(factors.get('determination_strength')))
    significance = abs(_prediction_numeric(factors.get('significance')))
    event_type = str(pred.get('event_type') or '').strip()
    substantive_event = 1.0 if (
        event_type
        and (
            score > 0.0
            or probability > 0.0
            or significance > 0.0
            or det_strength > 0.0
        )
    ) else 0.0
    return round(
        (30.0 * domain_alignment)
        + (12.0 * crisis_focus)
        + (20.0 * substantive_event)
        + (25.0 * probability)
        + (0.4 * significance)
        + (0.8 * det_strength)
        + (0.15 * score),
        3,
    )


def _predictor_window_gap_minutes(step_minutes: Optional[int]) -> float:
    try:
        step = max(1, int(step_minutes or 60))
    except Exception:
        step = 60
    # Allow one skipped sample inside a broader support phase, but split
    # genuinely disconnected recurrences into separate predictor windows.
    return float(step) * 2.5


def _parse_predictor_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


def _select_dominant_occurrence(occurrences: List[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(occurrences, list) or not occurrences:
        return None
    ordered = sorted(occurrences, key=lambda occ: str(occ.get('date') or ''))
    max_support = max(_prediction_numeric(occ.get('support_score')) for occ in ordered)
    strongest = [
        occ for occ in ordered
        if abs(_prediction_numeric(occ.get('support_score')) - max_support) <= 0.05
    ]
    if not strongest:
        return ordered[0].get('date')
    if len(strongest) == 1:
        return strongest[0].get('date')
    max_score = max(_prediction_numeric(occ.get('score')) for occ in strongest)
    highest_score_band = [
        occ for occ in strongest
        if abs(_prediction_numeric(occ.get('score')) - max_score) <= 0.05
    ]
    representative_band = highest_score_band or strongest
    representative = representative_band[len(representative_band) // 2]
    return representative.get('date')


def _prediction_group_key(pred: Dict[str, Any]) -> str:
    factors = _prediction_factors(pred)
    return '|'.join([
        str(pred.get('event_type') or '').strip(),
        str(pred.get('life_area') or '').strip(),
        str(pred.get('label') or '').strip(),
        str(pred.get('description') or '').strip(),
        str(factors.get('transit') or '').strip(),
    ])


def _prediction_family_key(item: Dict[str, Any]) -> str:
    return '|'.join([
        str(item.get('event_type') or '').strip(),
        str(item.get('life_area') or '').strip(),
    ])


def _predictor_group_merge_key(item: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    return (
        _prediction_family_key(item),
        str(item.get('start') or ''),
        str(item.get('end') or ''),
        str(item.get('dominant_timestamp') or ''),
        str(item.get('count') or ''),
    )


def _row_peak_sort_key(row: Dict[str, Any]) -> Tuple[float, float, float, float, float, float, float, float]:
    predictions = row.get('predictions') if isinstance(row, dict) else None
    best_prediction = predictions[0] if isinstance(predictions, list) and predictions else {}
    pred = best_prediction if isinstance(best_prediction, dict) else {}
    prediction_key = _prediction_sort_key(pred)
    try:
        step_score = float(row.get('step_score') or 0.0)
    except Exception:
        step_score = 0.0
    localization_score = _prediction_numeric(row.get('localization_score'))
    try:
        count = float(row.get('count') or 0.0)
    except Exception:
        count = 0.0
    return (
        -step_score,
        -localization_score,
        -count,
        prediction_key[0],
        prediction_key[1],
        prediction_key[2],
        prediction_key[3],
        prediction_key[4],
    )


def _row_localization_score(row: Dict[str, Any]) -> float:
    if not isinstance(row, dict):
        return 0.0
    predictions = row.get('predictions')
    if not isinstance(predictions, list) or not predictions:
        return 0.0
    supports = sorted(
        (_predictor_occurrence_support(pred) for pred in predictions if isinstance(pred, dict)),
        reverse=True,
    )
    if not supports:
        return 0.0
    best = supports[0]
    second = supports[1] if len(supports) > 1 else 0.0
    third = supports[2] if len(supports) > 2 else 0.0
    return round(best + (0.35 * second) + (0.15 * third), 3)


def _apply_row_localization(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return row
    raw_step = _prediction_numeric(row.get('raw_step_score'))
    if raw_step <= 0.0:
        raw_step = _prediction_numeric(row.get('step_score'))
    localization = _row_localization_score(row)
    row['raw_step_score'] = round(raw_step, 3)
    row['localization_score'] = localization
    row['step_score'] = round(raw_step + localization, 3)
    return row


def _row_matches_prediction_group(row: Dict[str, Any], group: Dict[str, Any]) -> bool:
    if not isinstance(row, dict) or not isinstance(group, dict):
        return False
    predictions = row.get('predictions')
    if not isinstance(predictions, list):
        return False
    group_event = str(group.get('event_type') or '').strip()
    group_area = str(group.get('life_area') or '').strip()
    group_desc = str(group.get('description') or group.get('label') or '').strip()
    group_transit = str(group.get('transit') or '').strip()
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
        if group_event and str(pred.get('event_type') or '').strip() != group_event:
            continue
        if group_area and str(pred.get('life_area') or '').strip() != group_area:
            continue
        pred_desc = str(pred.get('description') or pred.get('label') or '').strip()
        pred_transit = str(_prediction_factors(pred).get('transit') or '').strip()
        if group_transit and pred_transit == group_transit:
            return True
        if group_desc and pred_desc == group_desc:
            return True
        if group_event and group_area:
            return True
    return False


def _apply_group_window_localization(
    series: List[Dict[str, Any]],
    grouped_predictions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(series, list) or not isinstance(grouped_predictions, list):
        return series

    def _window_proximity(
        row_dt: Optional[datetime],
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
        dominant_dt: Optional[datetime],
    ) -> float:
        if row_dt is None:
            return 0.0
        if start_dt is None or end_dt is None or end_dt <= start_dt:
            if dominant_dt is None:
                return 0.0
            return 1.0 if row_dt == dominant_dt else 0.0
        span_minutes = max(1.0, (end_dt - start_dt).total_seconds() / 60.0)
        midpoint_dt = start_dt + ((end_dt - start_dt) / 2)
        half_span_minutes = max(1.0, span_minutes / 2.0)
        mid_distance = abs((row_dt - midpoint_dt).total_seconds()) / 60.0
        midpoint_proximity = max(0.0, 1.0 - min(1.0, mid_distance / half_span_minutes))
        if dominant_dt is None:
            return midpoint_proximity
        dominant_distance = abs((row_dt - dominant_dt).total_seconds()) / 60.0
        dominant_proximity = max(0.0, 1.0 - min(1.0, dominant_distance / span_minutes))
        return round((midpoint_proximity + dominant_proximity) / 2.0, 6)

    parsed_bounds: List[Tuple[Dict[str, Any], Optional[datetime], Optional[datetime], Optional[datetime], float]] = []
    for group in grouped_predictions:
        if not isinstance(group, dict):
            continue
        start_dt = _parse_predictor_iso(group.get('start'))
        end_dt = _parse_predictor_iso(group.get('end'))
        dominant_dt = _parse_predictor_iso(group.get('dominant_timestamp'))
        density = _prediction_numeric(group.get('support_density'))
        if density <= 0.0:
            continue
        parsed_bounds.append((group, start_dt, end_dt, dominant_dt, density))

    for row in series:
        if not isinstance(row, dict):
            continue
        row_dt = _parse_predictor_iso(row.get('timestamp'))
        window_bonus = 0.0
        for group, start_dt, end_dt, dominant_dt, density in parsed_bounds:
            if row_dt is None:
                continue
            if start_dt is not None and row_dt < start_dt:
                continue
            if end_dt is not None and row_dt > end_dt:
                continue
            if not _row_matches_prediction_group(row, group):
                continue
            proximity = _window_proximity(row_dt, start_dt, end_dt, dominant_dt)
            # Window support should act as a localization nudge, not overpower
            # the row's own score/localization. Weight rows near the middle of
            # a support window and near the dominant occurrence, instead of
            # flooding the whole window with the same large bonus.
            bonus = density * (0.12 + (0.48 * proximity))
            window_bonus = max(window_bonus, bonus)
        row['window_localization_score'] = round(window_bonus, 3)
        row['step_score'] = round(
            _prediction_numeric(row.get('raw_step_score'))
            + _prediction_numeric(row.get('localization_score'))
            + _prediction_numeric(row.get('window_localization_score')),
            3,
        )
    return series


def _serialize_peak_rows(peaks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        'timestamp': row.get('timestamp'),
        'count': row.get('count'),
        'step_score': row.get('step_score'),
        'raw_step_score': row.get('raw_step_score'),
        'localization_score': row.get('localization_score'),
        'window_localization_score': row.get('window_localization_score'),
        'tone': row.get('tone'),
        'event_type': ((row.get('_predictor_peak_summary') or {}).get('event_type')),
        'life_area': ((row.get('_predictor_peak_summary') or {}).get('life_area')),
        'description': ((row.get('_predictor_peak_summary') or {}).get('description')),
        'transit': ((row.get('_predictor_peak_summary') or {}).get('transit')),
        'support_score': ((row.get('_predictor_peak_summary') or {}).get('support_score')),
        'keyword_tokens': ((row.get('_predictor_peak_summary') or {}).get('keyword_tokens') or []),
    } for row in peaks]


def _build_peak_rows(
    series: List[Dict[str, Any]],
    limit: int = 10,
    step_epsilon: float = 0.05,
    count_band: float = 4.0,
) -> List[Dict[str, Any]]:
    if not isinstance(series, list) or not series:
        return []

    plateaus: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    current_score: Optional[float] = None
    current_min_count: Optional[float] = None
    current_max_count: Optional[float] = None

    for row in series:
        if not isinstance(row, dict):
            continue
        try:
            step_score = float(row.get('step_score') or 0.0)
        except Exception:
            step_score = 0.0
        try:
            count = float(row.get('count') or 0.0)
        except Exception:
            count = 0.0
        next_min = count if current_min_count is None else min(current_min_count, count)
        next_max = count if current_max_count is None else max(current_max_count, count)
        same_score_band = current_group and current_score is not None and abs(step_score - current_score) <= step_epsilon
        stable_count_band = current_group and (next_max - next_min) <= count_band
        if same_score_band and stable_count_band:
            current_group.append(row)
            current_min_count = next_min
            current_max_count = next_max
        else:
            if current_group:
                plateaus.append(current_group)
            current_group = [row]
            current_score = step_score
            current_min_count = count
            current_max_count = count

    if current_group:
        plateaus.append(current_group)

    candidates: List[Dict[str, Any]] = []
    for group in plateaus:
        if not group:
            continue
        def _group_count(row: Dict[str, Any]) -> float:
            try:
                return float(row.get('count') or 0.0)
            except Exception:
                return 0.0

        max_count = max(_group_count(row) for row in group)
        peak_rows = [row for row in group if abs(_group_count(row) - max_count) <= 1e-9]
        rep_group = peak_rows or group
        mid_index = len(rep_group) // 2
        rep = rep_group[mid_index]
        if isinstance(rep, dict):
            candidates.append(rep)

    return sorted(candidates, key=_row_peak_sort_key)[:max(1, int(limit or 10))]


def _collect_tokens(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for val in values:
        if isinstance(val, str):
            token = val.strip().lower()
            if token:
                out.append(token)
        elif isinstance(val, (list, tuple, set)):
            for item in val:
                if isinstance(item, str):
                    token = item.strip().lower()
                    if token:
                        out.append(token)
    return out


def _derive_event_type(hit: Dict[str, Any], pred: Dict[str, Any]) -> Optional[str]:
    if pred.get('eventType'):
        return pred.get('eventType')
    tokens: List[str] = []
    tokens.extend(_collect_tokens(pred.get('tags') or []))
    tokens.extend(_collect_tokens(hit.get('prediction_tags') or []))
    tokens.extend(_collect_tokens(hit.get('keywords') or []))
    tokens.extend(_collect_tokens(hit.get('enriched_keywords') or []))
    life_area = pred.get('lifeArea') or hit.get('life_area')
    if isinstance(life_area, str):
        tokens.append(life_area.strip().lower())
    for ev in _EVENT_CANDIDATES:
        if ev in tokens:
            return ev
    return None


def _prediction_from_hit(hit: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    conc = hit.get('concordance') or {}
    pred = hit.get('prediction') or {}
    target = str(hit.get('target_label') or hit.get('natal') or '')
    event_type = _derive_event_type(hit, pred)
    life_area = pred.get('lifeArea') or hit.get('life_area')
    probability = float(conc.get('overall_concordance') or 0.0)
    score_val = pred.get('score')
    if score_val is None:
        score_val = hit.get('prediction_score')
    score = round(float(score_val), 1) if score_val is not None else None
    tags = [str(t) for t in (pred.get('tags') or hit.get('prediction_tags') or []) if t]
    transiting = hit.get('transiting')
    aspect = hit.get('aspect')
    label = pred.get('label')
    if not label and transiting and aspect and target:
        label = f"{transiting} {aspect} {target}"
    description = pred.get('description')
    if not description:
        if label:
            description = label
        else:
            description = None
    factors: Dict[str, Any] = {
        'direction': _direction_summary(hit),
        'solar_revolution': conc.get('solar_score'),
        'lunar_revolution': conc.get('lunar_score'),
        'transit': f"{hit.get('transiting')} {hit.get('aspect')} {target}",
        'concordance_score': conc.get('overall_score'),
        'multipliers': conc.get('multipliers'),
        'laws': [law for law in (hit.get('laws_applied') or []) if law and law.get('applies')],
    }
    factors['determination_strength'] = hit.get('determination_strength')
    factors['significance'] = hit.get('significance')
    factors['passIndex'] = hit.get('passIndex')
    return {
        'date': timestamp,
        'event_type': event_type,
        'life_area': life_area,
        'probability': round(probability, 3),
        'label': label,
        'description': description,
        'score': score,
        'tags': tags,
        'factors': factors,
    }


def _predictions_from_hits(hits: List[Dict[str, Any]], timestamp: str) -> List[Dict[str, Any]]:
    if not isinstance(hits, list):
        return []
    predictions = [_prediction_from_hit(hit, timestamp) for hit in hits]
    return sorted(predictions, key=_prediction_sort_key)


def _retry_enrich_transit_hits(
    natal_cd: Dict[str, Any],
    hits: List[Dict[str, Any]],
    timestamp_iso: str,
    *,
    pd_windows: Optional[List[Dict[str, Any]]] = None,
    sig_beta: Optional[bool] = None,
    observer_location: Optional[str] = None,
    observer_timezone: Optional[str] = None,
    context_out: Optional[Dict[str, Any]] = None,
    route_label: str = "astro-clock/transits",
) -> List[Dict[str, Any]]:
    """Enrich transit hits, retrying without PD/context if the richer pass fails."""
    if not isinstance(hits, list) or not hits:
        return hits

    from transits_morin import enrich_hits_with_concordance

    try:
        return enrich_hits_with_concordance(
            natal_cd,
            hits,
            timestamp_iso,
            pd_windows=pd_windows or [],
            use_new_significance=sig_beta,
            observer_location=observer_location,
            observer_timezone=observer_timezone,
            context_out=context_out,
        )
    except Exception:
        logger.exception(
            "[astro-clock] Concordance enrichment failed for %s; retrying without PD/context.",
            route_label,
        )

    fallback_context: Optional[Dict[str, Any]] = {} if isinstance(context_out, dict) else None
    try:
        enriched = enrich_hits_with_concordance(
            natal_cd,
            hits,
            timestamp_iso,
            pd_windows=[],
            use_new_significance=sig_beta,
            observer_location=observer_location,
            observer_timezone=observer_timezone,
            context_out=fallback_context,
        )
        if isinstance(context_out, dict):
            context_out.clear()
            if isinstance(fallback_context, dict):
                context_out.update(fallback_context)
        return enriched
    except Exception:
        logger.exception(
            "[astro-clock] Concordance enrichment fallback failed for %s; returning raw hits.",
            route_label,
        )
        if isinstance(context_out, dict):
            context_out.clear()
        return hits


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _resolve_natal_datetime(
    natal_meta: Optional[Dict[str, Any]],
    args: Any,
) -> Optional[datetime]:
    meta_ts = None
    try:
        meta_ts = (natal_meta or {}).get("timestamp")
    except Exception:
        meta_ts = None
    if not meta_ts and args is not None:
        try:
            meta_ts = args.get("natal_datetime")
        except Exception:
            meta_ts = None
    return _parse_iso_datetime(meta_ts)


def _pd_windows_cache_key(
    natal_dt: datetime,
    natal_cd: Dict[str, Any],
    years: Iterable[int],
) -> Tuple[str, Tuple[int, ...], str]:
    years_key = tuple(sorted({int(year) for year in years}))
    try:
        encoded = json.dumps(natal_cd, sort_keys=True, default=str, separators=(",", ":"))
    except Exception:
        encoded = repr(natal_cd)
    chart_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return (natal_dt.isoformat(), years_key, chart_hash)


def _compute_pd_windows_for_years(
    natal_cd: Dict[str, Any],
    natal_meta: Optional[Dict[str, Any]],
    args: Any,
    years: Iterable[int],
    *,
    route_label: str,
) -> List[Dict[str, Any]]:
    years_key = tuple(sorted({int(year) for year in years}))
    if not years_key:
        return []

    natal_dt = _resolve_natal_datetime(natal_meta, args)
    if natal_dt is None:
        return []

    cache_key = _pd_windows_cache_key(natal_dt, natal_cd, years_key)
    with _PD_WINDOWS_CACHE_LOCK:
        cached = _PD_WINDOWS_CACHE.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)

    try:
        from primary_directions import compute_primary_direction_windows
    except Exception:
        logger.exception("[astro-clock] PD window import failed for %s.", route_label)
        return []

    pd_windows: List[Dict[str, Any]] = []
    for year in years_key:
        try:
            pd_windows.extend(compute_primary_direction_windows(natal_dt, year, natal_cd))
        except Exception:
            logger.exception("[astro-clock] PD window derivation failed for %s year %s.", route_label, year)

    with _PD_WINDOWS_CACHE_LOCK:
        _PD_WINDOWS_CACHE[cache_key] = copy.deepcopy(pd_windows)
        while len(_PD_WINDOWS_CACHE) > _PD_WINDOWS_CACHE_MAX:
            _PD_WINDOWS_CACHE.pop(next(iter(_PD_WINDOWS_CACHE)))

    return pd_windows


def _empty_morin_dashboard_payload() -> Dict[str, Any]:
    return {
        'morin_aspects': [],
        'morin_antiscia': [],
        'morin_contra_antiscia': [],
        'morin_combustion': [],
        'morin_patterns': {},
    }


def _morin_dashboard_cache_key(chart_data: Dict[str, Any], ts_iso: str) -> Tuple[str, str]:
    try:
        encoded = json.dumps(_to_jsonable(chart_data), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        encoded = repr(chart_data)
    chart_hash = hashlib.sha256(encoded.encode("utf-8", errors="ignore")).hexdigest()
    return (ts_iso, chart_hash)


def _compute_morin_dashboard_payload(chart_data: Dict[str, Any], ts_iso: Optional[str]) -> Dict[str, Any]:
    payload = _empty_morin_dashboard_payload()
    if not ts_iso:
        return payload

    cache_key = _morin_dashboard_cache_key(chart_data, ts_iso)
    with _MORIN_PAYLOAD_CACHE_LOCK:
        cached = _MORIN_PAYLOAD_CACHE.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)

    if compute_morin_aspects:
        try:
            payload['morin_aspects'] = _dedupe_aspect_rows(compute_morin_aspects(chart_data, ts_iso) or [])  # type: ignore[operator]
        except Exception:
            logger.exception("Failed to compute Morin aspects for dashboard")
            payload['morin_aspects'] = []
    if compute_morin_antiscia:
        try:
            payload['morin_antiscia'] = compute_morin_antiscia(ts_iso) or []  # type: ignore[operator]
        except Exception:
            logger.exception("Failed to compute Morin antiscia for dashboard")
            payload['morin_antiscia'] = []
    if compute_morin_contra_antiscia:
        try:
            payload['morin_contra_antiscia'] = compute_morin_contra_antiscia(ts_iso) or []  # type: ignore[operator]
        except Exception:
            logger.exception("Failed to compute Morin contra-antiscia for dashboard")
            payload['morin_contra_antiscia'] = []
    if compute_morin_combustion:
        try:
            payload['morin_combustion'] = compute_morin_combustion(chart_data, ts_iso) or []  # type: ignore[operator]
        except Exception:
            logger.exception("Failed to compute Morin combustion for dashboard")
            payload['morin_combustion'] = []
    if compute_morin_patterns and payload['morin_aspects']:
        try:
            payload['morin_patterns'] = compute_morin_patterns(chart_data, ts_iso, payload['morin_aspects']) or {}  # type: ignore[operator]
        except Exception:
            logger.exception("Failed to compute Morin patterns for dashboard")
            payload['morin_patterns'] = {}

    with _MORIN_PAYLOAD_CACHE_LOCK:
        _MORIN_PAYLOAD_CACHE[cache_key] = copy.deepcopy(payload)
        while len(_MORIN_PAYLOAD_CACHE) > _MORIN_PAYLOAD_CACHE_MAX:
            _MORIN_PAYLOAD_CACHE.pop(next(iter(_MORIN_PAYLOAD_CACHE)))

    return payload


def _summarize_predictor_window(
    seed: Dict[str, Any],
    cluster_predictions: List[Dict[str, Any]],
    step_minutes: Optional[int] = 60,
    cluster_index: int = 0,
) -> Dict[str, Any]:
    occurrences: List[Dict[str, Any]] = []
    keyword_tokens: List[str] = []
    tags: List[str] = []
    support_total = 0.0
    probability_total = 0.0
    score_total = 0.0
    probability_max = 0.0
    score_max = 0.0
    determination_strength_max = 0.0
    significance_max = 0.0
    domain_alignment_max = 0.0

    for pred in cluster_predictions:
        if not isinstance(pred, dict):
            continue
        factors = _prediction_factors(pred)
        support = _predictor_occurrence_support(pred)
        occurrence = {
            'date': pred.get('date'),
            'probability': _prediction_numeric(pred.get('probability')),
            'score': _prediction_numeric(pred.get('score')),
            'support_score': support,
        }
        occurrences.append(occurrence)
        support_total += support
        probability_total += occurrence['probability']
        score_total += occurrence['score']
        probability_max = max(probability_max, occurrence['probability'])
        score_max = max(score_max, occurrence['score'])
        determination_strength_max = max(
            determination_strength_max,
            abs(_prediction_numeric(factors.get('determination_strength'))),
        )
        significance_max = max(
            significance_max,
            abs(_prediction_numeric(factors.get('significance'))),
        )
        domain_alignment_max = max(
            domain_alignment_max,
            _prediction_domain_alignment(pred),
        )
        for tag in pred.get('tags') or []:
            tag_str = str(tag or '').strip()
            if tag_str and tag_str not in tags:
                tags.append(tag_str)
        for token in _prediction_keyword_tokens(pred):
            if token not in keyword_tokens:
                keyword_tokens.append(token)

    occurrences.sort(key=lambda occ: str(occ.get('date') or ''))
    dominant_timestamp = _select_dominant_occurrence(occurrences)
    count = max(1, len(occurrences))
    start = occurrences[0].get('date') if occurrences else None
    end = occurrences[-1].get('date') if occurrences else None
    start_dt = _parse_predictor_iso(start)
    end_dt = _parse_predictor_iso(end)
    try:
        step = max(1, int(step_minutes or 60))
    except Exception:
        step = 60
    window_span_minutes = 0.0
    if start_dt is not None and end_dt is not None and end_dt >= start_dt:
        window_span_minutes = max(0.0, (end_dt - start_dt).total_seconds() / 60.0)
    window_steps = max(1.0, (window_span_minutes / float(step)) + 1.0)
    support_density = round(support_total / window_steps, 3)
    support_focus = round(
        ((support_total * support_density) ** 0.5)
        if support_total > 0.0 and support_density > 0.0
        else max(support_total, support_density),
        3,
    )

    return {
        'event_type': seed.get('event_type'),
        'life_area': seed.get('life_area'),
        'label': seed.get('label'),
        'description': seed.get('description'),
        'transit': seed.get('transit'),
        'dominant_transit': seed.get('transit'),
        'tags': tags,
        'keyword_tokens': keyword_tokens,
        'occurrences': occurrences,
        'count': count,
        'start': start,
        'end': end,
        'window_start': start,
        'window_end': end,
        'first_seen': start,
        'last_seen': end,
        'dominant_timestamp': dominant_timestamp,
        'support_score': round(support_total, 3),
        'support_density': support_density,
        'support_focus': support_focus,
        'probability_max': probability_max,
        'max_probability': probability_max,
        'probability_mean': round(probability_total / count, 3),
        'score_max': score_max,
        'max_score': score_max,
        'score_mean': round(score_total / count, 3),
        'determination_strength_max': determination_strength_max,
        'significance_max': significance_max,
        'domain_alignment_max': domain_alignment_max,
        'window_span_minutes': round(window_span_minutes, 3),
        'window_steps': round(window_steps, 3),
        'cluster_index': cluster_index,
        'supporting_labels': [seed.get('label')] if seed.get('label') else [],
        'supporting_transits': [seed.get('transit')] if seed.get('transit') else [],
    }


def _predictor_group_sort_key(item: Dict[str, Any]) -> Tuple[float, float, float, float, float, float, float, str, str]:
    return (
        -_prediction_numeric(item.get('support_focus')),
        -_prediction_numeric(item.get('support_density')),
        -_prediction_numeric(item.get('support_score')),
        -_prediction_numeric(item.get('domain_alignment_max')),
        -_prediction_numeric(item.get('probability_mean')),
        -_prediction_numeric(item.get('determination_strength_max')),
        -_prediction_numeric(item.get('significance_max')),
        str(item.get('event_type') or ''),
        str(item.get('transit') or ''),
    )


def _merge_predictor_groups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clusters: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for item in groups:
        if not isinstance(item, dict):
            continue
        clusters.setdefault(_predictor_group_merge_key(item), []).append(item)

    merged: List[Dict[str, Any]] = []
    for items in clusters.values():
        if len(items) == 1:
            item = dict(items[0])
            item.setdefault('supporting_labels', [item.get('label')] if item.get('label') else [])
            item.setdefault('supporting_transits', [item.get('transit')] if item.get('transit') else [])
            merged.append(item)
            continue

        ordered = sorted(items, key=_predictor_group_sort_key)
        primary = dict(ordered[0])
        supporting_labels: List[str] = []
        supporting_transits: List[str] = []
        tags: List[str] = []
        keyword_tokens: List[str] = []
        for item in ordered:
            label = str(item.get('label') or '').strip()
            if label and label not in supporting_labels:
                supporting_labels.append(label)
            transit = str(item.get('transit') or item.get('dominant_transit') or '').strip()
            if transit and transit not in supporting_transits:
                supporting_transits.append(transit)
            for tag in item.get('tags') or []:
                tag_str = str(tag or '').strip()
                if tag_str and tag_str not in tags:
                    tags.append(tag_str)
            for token in item.get('keyword_tokens') or []:
                tok = str(token or '').strip()
                if tok and tok not in keyword_tokens:
                    keyword_tokens.append(tok)

        primary['tags'] = tags
        primary['keyword_tokens'] = keyword_tokens
        primary['supporting_labels'] = supporting_labels
        primary['supporting_transits'] = supporting_transits
        primary['dominant_transit'] = primary.get('transit') or (supporting_transits[0] if supporting_transits else None)
        merged.append(primary)

    return merged


def _select_diverse_predictor_groups(groups: List[Dict[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
    ordered = sorted(groups, key=_predictor_group_sort_key)
    max_items = max(1, int(limit or 12))
    selected: List[Dict[str, Any]] = []
    used_families: set[str] = set()

    for item in ordered:
        family_key = _prediction_family_key(item)
        if family_key in used_families:
            continue
        selected.append(item)
        used_families.add(family_key)
        if len(selected) >= max_items:
            return selected

    for item in ordered:
        if item in selected:
            continue
        selected.append(item)
        if len(selected) >= max_items:
            break
    return selected


def _aggregate_predictor_predictions(
    predictions: List[Dict[str, Any]],
    limit: int = 12,
    step_minutes: Optional[int] = 60,
) -> List[Dict[str, Any]]:
    if not isinstance(predictions, list) or not predictions:
        return []

    grouped: Dict[str, Dict[str, Any]] = {}
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
        key = _prediction_group_key(pred)
        if not key:
            continue
        group = grouped.get(key)
        if group is None:
            factors = _prediction_factors(pred)
            group = {
                'event_type': pred.get('event_type'),
                'life_area': pred.get('life_area'),
                'label': pred.get('label'),
                'description': pred.get('description'),
                'transit': factors.get('transit') or pred.get('label') or pred.get('description'),
                'predictions': [],
            }
            grouped[key] = group
        group['predictions'].append(pred)

    result: List[Dict[str, Any]] = []
    gap_minutes = _predictor_window_gap_minutes(step_minutes)
    for seed in grouped.values():
        sorted_predictions = sorted(
            [pred for pred in (seed.get('predictions') or []) if isinstance(pred, dict)],
            key=lambda pred: str(pred.get('date') or ''),
        )
        cluster: List[Dict[str, Any]] = []
        prev_dt: Optional[datetime] = None
        cluster_index = 0

        def _flush_cluster() -> None:
            nonlocal cluster_index, cluster
            if not cluster:
                return
            result.append(
                _summarize_predictor_window(
                    seed,
                    cluster,
                    step_minutes=step_minutes,
                    cluster_index=cluster_index,
                )
            )
            cluster_index += 1
            cluster = []

        for pred in sorted_predictions:
            current_dt = _parse_predictor_iso(pred.get('date'))
            should_split = False
            if cluster and current_dt is not None and prev_dt is not None:
                gap = (current_dt - prev_dt).total_seconds() / 60.0
                should_split = gap > gap_minutes
            if should_split:
                _flush_cluster()
            cluster.append(pred)
            if current_dt is not None:
                prev_dt = current_dt
        _flush_cluster()

    result = _merge_predictor_groups(result)
    result = _select_diverse_predictor_groups(result, limit=max(1, int(limit or 12)))
    result.sort(
        key=lambda item: (
            *_predictor_group_sort_key(item),
            -_prediction_numeric(item.get('score_max')),
            _prediction_numeric(item.get('window_span_minutes')),
            -_prediction_numeric(item.get('count')),
        )
    )
    return result[:max(1, int(limit or 12))]


def _predictor_peak_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    predictions = row.get('predictions') if isinstance(row, dict) else None
    groups = _aggregate_predictor_predictions(predictions if isinstance(predictions, list) else [], limit=3)
    primary = groups[0] if groups else {}
    return {
        'event_type': primary.get('event_type'),
        'life_area': primary.get('life_area'),
        'description': primary.get('description') or primary.get('label'),
        'transit': primary.get('transit'),
        'support_focus': _prediction_numeric(primary.get('support_focus')),
        'support_score': _prediction_numeric(primary.get('support_score')),
        'domain_alignment': _prediction_numeric(primary.get('domain_alignment_max')),
        'probability': _prediction_numeric(primary.get('probability_max')),
        'keyword_tokens': list(primary.get('keyword_tokens') or primary.get('tags') or []),
    }


def _predictor_peak_sort_key(row: Dict[str, Any]) -> Tuple[float, float, float, float, float, str, str]:
    summary = _predictor_peak_summary(row)
    try:
        step_score = float(row.get('step_score') or 0.0)
    except Exception:
        step_score = 0.0
    try:
        count = float(row.get('count') or 0.0)
    except Exception:
        count = 0.0
    return (
        -_prediction_numeric(summary.get('support_focus')),
        -_prediction_numeric(summary.get('support_score')),
        -_prediction_numeric(summary.get('domain_alignment')),
        -_prediction_numeric(summary.get('probability')),
        -step_score,
        -count,
        str(summary.get('event_type') or ''),
        str(row.get('timestamp') or ''),
    )


def _build_predictor_peak_rows(
    series: List[Dict[str, Any]],
    limit: int = 10,
    step_epsilon: float = 0.05,
    count_band: float = 4.0,
) -> List[Dict[str, Any]]:
    if not isinstance(series, list) or not series:
        return []

    plateaus: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    current_score: Optional[float] = None
    current_min_count: Optional[float] = None
    current_max_count: Optional[float] = None

    for row in series:
        if not isinstance(row, dict):
            continue
        try:
            step_score = float(row.get('step_score') or 0.0)
        except Exception:
            step_score = 0.0
        try:
            count = float(row.get('count') or 0.0)
        except Exception:
            count = 0.0
        next_min = count if current_min_count is None else min(current_min_count, count)
        next_max = count if current_max_count is None else max(current_max_count, count)
        same_score_band = current_group and current_score is not None and abs(step_score - current_score) <= step_epsilon
        stable_count_band = current_group and (next_max - next_min) <= count_band
        if same_score_band and stable_count_band:
            current_group.append(row)
            current_min_count = next_min
            current_max_count = next_max
        else:
            if current_group:
                plateaus.append(current_group)
            current_group = [row]
            current_score = step_score
            current_min_count = count
            current_max_count = count

    if current_group:
        plateaus.append(current_group)

    candidates: List[Dict[str, Any]] = []
    for group in plateaus:
        if not group:
            continue
        representative = sorted(group, key=_predictor_peak_sort_key)[0]
        if isinstance(representative, dict):
            summary = _predictor_peak_summary(representative)
            representative = dict(representative)
            representative['_predictor_peak_summary'] = summary
            candidates.append(representative)
    ordered_candidates = sorted(candidates, key=_predictor_peak_sort_key)
    parsed_times = [
        _parse_predictor_iso(row.get('timestamp'))
        for row in ordered_candidates
        if isinstance(row, dict)
    ]
    deltas = []
    for earlier, later in zip(parsed_times, parsed_times[1:]):
        if earlier is None or later is None:
            continue
        delta_minutes = abs((later - earlier).total_seconds()) / 60.0
        if delta_minutes > 0.0:
            deltas.append(delta_minutes)
    inferred_step = min(deltas) if deltas else 60.0
    min_peak_gap_minutes = max(480.0, inferred_step * 4.0)

    selected: List[Dict[str, Any]] = []
    selected_times: List[datetime] = []
    for candidate in ordered_candidates:
        candidate_dt = _parse_predictor_iso(candidate.get('timestamp'))
        if candidate_dt is not None and any(
            abs((candidate_dt - chosen_dt).total_seconds()) / 60.0 < min_peak_gap_minutes
            for chosen_dt in selected_times
        ):
            continue
        selected.append(candidate)
        if candidate_dt is not None:
            selected_times.append(candidate_dt)
        if len(selected) >= max(1, int(limit or 10)):
            break

    return selected


def _row_prediction_hits(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(row, dict):
        return []
    pred_hits = row.pop('_prediction_hits', None)
    if isinstance(pred_hits, list):
        return pred_hits
    top_hits = row.get('top')
    return top_hits if isinstance(top_hits, list) else []


def _error_handler(f):
    @wraps(f)
    def _w(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except LocationError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            incident_id = uuid4().hex[:12]
            logger.exception("Astro Clock API error [incident=%s]: %s", incident_id, e)
            return jsonify({
                'success': False,
                'error': 'internal_error',
                'detail': 'An internal server error occurred.',
                'incident_id': incident_id,
            }), 500
    return _w


def _serialize_planetary_hour(hour: PlanetaryHour) -> Dict[str, Any]:
    return {
        'hour_number': hour.hour_number,
        'ruling_planet': getattr(hour.ruling_planet, 'value', str(hour.ruling_planet)),
        'start_time': hour.start_time.isoformat(),
        'end_time': hour.end_time.isoformat(),
        'duration_minutes': hour.duration_minutes,
        'is_day_hour': hour.is_day_hour,
    }


def _serialize_daily_hours(daily: DailyPlanetaryHours) -> Dict[str, Any]:
    return {
        'date': daily.date.isoformat(),
        'day_ruler': getattr(daily.day_ruler, 'value', str(daily.day_ruler)),
        'sunrise': daily.sunrise.isoformat(),
        'sunset': daily.sunset.isoformat(),
        'hours': [_serialize_planetary_hour(h) for h in daily.hours],
        'current_hour': _serialize_planetary_hour(daily.current_hour) if daily.current_hour else None,
    }


def _serialize_real_time(data) -> Dict[str, Any]:
    # chart_result may be dict or string
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    return {
        'timestamp': data.timestamp.isoformat(),
        'settings': {
            'mode': getattr(data.settings.mode, 'value', str(data.settings.mode)),
            'location': data.settings.location,
            'custom_time': data.settings.custom_time.isoformat() if data.settings.custom_time else None,
            'timezone': data.settings.timezone,
        },
        'chart_data': chart.get('chart_data', {}),
        'moon_state': getattr(data, 'moon_state', None) and {
            'position': {
                'longitude': data.moon_state.position.longitude,
                'sign': getattr(getattr(data.moon_state.position, 'sign', object()), 'sign_name', None),
                'house': data.moon_state.position.house,
            },
            'void_of_course': data.moon_state.void_of_course,
            'last_aspect': data.moon_state.last_aspect,
            'next_aspect': data.moon_state.next_aspect,
            'void_duration_hours': data.moon_state.void_duration,
        },
        'dispositor_chains': {k: {
            'dispositor': getattr(v, 'dispositor', None),
            'final_dispositor': getattr(v, 'final_dispositor', None),
            'mutual_reception': bool(getattr(v, 'mutual_reception', False)),
            'reception_partner': getattr(v, 'reception_partner', None),
            'chain': list(getattr(v, 'chain', []) or []),
        } for k, v in (getattr(data, 'dispositor_chains', {}) or {}).items()},
        'current_aspects': getattr(data, 'current_aspects', []),
    }


def _normalized_planet_rows(planets: Any) -> List[Dict[str, Any]]:
    if isinstance(planets, dict):
        norm: List[Dict[str, Any]] = []
        for name, info in planets.items():
            if isinstance(info, dict):
                row = dict(info)
                row.setdefault('planet', name)
                norm.append(row)
        return norm
    if isinstance(planets, list):
        return [dict(row) for row in planets if isinstance(row, dict)]
    return []


def _synastry_chart_snapshot_from_chart_data(chart_data: Any) -> Dict[str, Any]:
    if not isinstance(chart_data, dict):
        return {}
    snapshot: Dict[str, Any] = {}
    planets = _normalized_planet_rows(chart_data.get('planets'))
    if planets:
        snapshot['planets'] = copy.deepcopy(planets)
    house_cusps = chart_data.get('houses') or chart_data.get('house_cusps') or []
    if isinstance(house_cusps, list) and house_cusps:
        snapshot['house_cusps'] = copy.deepcopy(house_cusps[:12])
    for key in ('ascendant', 'midheaven', 'house_system_code'):
        value = chart_data.get(key)
        if value is not None:
            snapshot[key] = value
    house_rulers = chart_data.get('house_rulers')
    if isinstance(house_rulers, dict) and house_rulers:
        snapshot['house_rulers'] = copy.deepcopy(house_rulers)
    almutens = chart_data.get('almutens')
    if isinstance(almutens, dict) and almutens:
        snapshot['almutens'] = copy.deepcopy(almutens)
    return snapshot


def _synastry_chart_snapshot_from_dashboard(dashboard: Any) -> Dict[str, Any]:
    if not isinstance(dashboard, dict):
        return {}
    snapshot: Dict[str, Any] = {}
    planets = _normalized_planet_rows(dashboard.get('planets'))
    if planets:
        snapshot['planets'] = copy.deepcopy(planets)
    house_cusps = dashboard.get('house_cusps') or dashboard.get('houses') or []
    if isinstance(house_cusps, list) and house_cusps:
        snapshot['house_cusps'] = copy.deepcopy(house_cusps[:12])
    for key in ('ascendant', 'midheaven', 'house_system_code'):
        value = dashboard.get(key)
        if value is not None:
            snapshot[key] = value
    house_rulers = dashboard.get('house_rulers')
    if isinstance(house_rulers, dict) and house_rulers:
        snapshot['house_rulers'] = copy.deepcopy(house_rulers)
    almutens = dashboard.get('almutens')
    if isinstance(almutens, dict) and almutens:
        snapshot['almutens'] = copy.deepcopy(almutens)
    return snapshot


def _has_synastry_chart_snapshot(chart_data: Any) -> bool:
    if not isinstance(chart_data, dict):
        return False
    return bool(_normalized_planet_rows(chart_data.get('planets')))


def _normalize_synastry_profile_hint(value: Any) -> Optional[str]:
    raw = str(value or '').strip().lower()
    if raw in {'f', 'female', 'feminine', 'woman', 'girl'}:
        return 'feminine'
    if raw in {'m', 'male', 'masculine', 'man', 'boy'}:
        return 'masculine'
    return None


def _extract_synastry_profile_hint(*sources: Any) -> Optional[str]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ('profile_hint', 'profile', 'sex', 'gender'):
            hint = _normalize_synastry_profile_hint(source.get(key))
            if hint:
                return hint
        for key in ('person', 'subject', 'native', 'birth_data', 'chart_meta', 'metadata', 'meta'):
            nested = source.get(key)
            if not isinstance(nested, dict):
                continue
            hint = _extract_synastry_profile_hint(nested)
            if hint:
                return hint
    return None


def _compact_dashboard(data) -> Dict[str, Any]:
    # Reduced payload useful for the Astro Clock dashboard
    rt = _serialize_real_time(data)
    cd = rt.get('chart_data') or {}
    rt['planets'] = _normalized_planet_rows(cd.get('planets'))
    return rt


def _dedupe_aspect_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _identity(row: Dict[str, Any]) -> Optional[Tuple[Tuple[str, str], str]]:
        try:
            p1 = str(row.get('planet1') or '').strip()
            p2 = str(row.get('planet2') or '').strip()
            aspect = str(row.get('aspect') or '').strip().lower()
        except Exception:
            return None
        if not (p1 and p2 and aspect):
            return None
        return tuple(sorted((p1, p2))), aspect

    def _rank(row: Dict[str, Any]) -> Tuple[float, int]:
        try:
            orb = abs(float(row.get('orb', 9999) or 9999))
        except Exception:
            orb = 9999.0
        detail_keys = ('max_orb', 'allowed_orb', 'phase', 'direction', 'partile', 'complete_platic', 'severity')
        richness = sum(1 for key in detail_keys if row.get(key) not in (None, '', False))
        return orb, -richness

    chosen: Dict[Tuple[Tuple[str, str], str], Dict[str, Any]] = {}
    passthrough: List[Dict[str, Any]] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        key = _identity(row)
        if key is None:
            passthrough.append(row)
            continue
        prev = chosen.get(key)
        if prev is None or _rank(row) < _rank(prev):
            chosen[key] = row

    ordered = list(chosen.values()) + passthrough
    ordered.sort(key=_rank)
    return ordered


def _top_aspects_from_runtime(rt: Dict[str, Any], cd: Dict[str, Any]) -> List[Dict[str, Any]]:
    aspects_raw: List[Dict[str, Any]] = []
    try:
        a_top = rt.get('current_aspects') or []
        if isinstance(a_top, list) and a_top:
            aspects_raw = [a for a in a_top if isinstance(a, dict)]
        else:
            a2 = cd.get('aspects')
            if isinstance(a2, list):
                aspects_raw = [a for a in a2 if isinstance(a, dict)]
    except Exception:
        aspects_raw = []
    try:
        return _dedupe_aspect_rows(aspects_raw)[:3]
    except Exception:
        return aspects_raw[:3]


def _solar_conditions_from_chart(planets: List[Dict[str, Any]], cd: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    solar_conditions = {'cazimi': [], 'combustion': [], 'under_beams': [], 'free': []}
    try:
        summary = cd.get('solar_conditions_summary') if isinstance(cd, dict) else None
        if isinstance(summary, dict):
            for item in (summary.get('cazimi_planets') or []):
                solar_conditions['cazimi'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                    'exact_cazimi': item.get('exact_cazimi', False),
                })
            for item in (summary.get('combusted_planets') or []):
                solar_conditions['combustion'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                    'traditional_exception': item.get('traditional_exception', False),
                })
            for item in (summary.get('under_beams_planets') or []):
                solar_conditions['under_beams'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                })
            for item in (summary.get('free_planets') or []):
                pname = item.get('planet') or item.get('name')
                if pname:
                    solar_conditions['free'].append({'planet': pname})
            return solar_conditions

        for p in planets:
            sc = p.get('solar_condition') if isinstance(p, dict) else None
            if not isinstance(sc, dict):
                if p.get('planet'):
                    solar_conditions['free'].append({'planet': p.get('planet')})
                continue
            cond = str(sc.get('condition') or '').lower()
            entry = {
                'planet': p.get('planet'),
                'dignity_effect': sc.get('dignity_effect'),
                'distance_from_sun': sc.get('distance_from_sun'),
                'exact_cazimi': sc.get('exact_cazimi'),
                'traditional_exception': sc.get('traditional_exception'),
            }
            if 'cazimi' in cond:
                solar_conditions['cazimi'].append(entry)
            elif 'combust' in cond:
                solar_conditions['combustion'].append(entry)
            elif 'beam' in cond:
                solar_conditions['under_beams'].append(entry)
            elif p.get('planet'):
                solar_conditions['free'].append({'planet': p.get('planet')})
    except Exception:
        pass
    return solar_conditions


def _timezone_label_from_chart_data(cd: Dict[str, Any]) -> Optional[str]:
    try:
        tzinfo = cd.get('timezone_info') if isinstance(cd, dict) else None
        if not isinstance(tzinfo, dict):
            return None
        tz_name = tzinfo.get('timezone')
        local_iso = tzinfo.get('local_time')
        utc_iso = tzinfo.get('utc_time')
        if not (tz_name and local_iso and utc_iso):
            return None
        loc_dt = datetime.fromisoformat(str(local_iso).replace('Z', '+00:00'))
        utc_dt = datetime.fromisoformat(str(utc_iso).replace('Z', '+00:00'))
        delta_min = int((loc_dt - utc_dt).total_seconds() // 60)
        sign = '+' if delta_min >= 0 else '-'
        hh = abs(delta_min) // 60
        mm = abs(delta_min) % 60
        return f"{tz_name} (UTC{sign}{hh:02d}:{mm:02d})"
    except Exception:
        return None


def _lightweight_receptions_payload(chart_result: Dict[str, Any], cd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        details = chart_result.get('reception_details') or (cd.get('reception_details') if isinstance(cd, dict) else None)
        if not isinstance(details, dict):
            return None
    except Exception:
        return None
    return _extract_receptions_payload(chart_result)


def _build_traits_chart_snapshot(data, rt: Dict[str, Any], cd: Dict[str, Any], special_degrees: List[str]) -> Dict[str, Any]:
    active_settings = getattr(data, 'settings', None)
    active_location = getattr(active_settings, 'location', None)
    active_timezone = getattr(active_settings, 'timezone', None)
    planets = rt.get('planets') if isinstance(rt.get('planets'), list) else []
    moon_state = rt.get('moon_state') if isinstance(rt.get('moon_state'), dict) else {}
    moon = None
    try:
        mp = next((p for p in planets if p.get('planet') == 'Moon'), None)
        if mp:
            moon = {
                'void_of_course': bool(moon_state.get('void_of_course')),
                'sign': mp.get('sign'),
                'longitude': mp.get('longitude'),
                'house': mp.get('house'),
                'last_aspect': moon_state.get('last_aspect'),
                'next_aspect': moon_state.get('next_aspect'),
            }
    except Exception:
        moon = None

    return {
        'timestamp': rt.get('timestamp'),
        'location': active_location,
        'timezone': active_timezone,
        'timezone_label': _timezone_label_from_chart_data(cd),
        'house_system': getattr(active_settings, 'house_system_code', None),
        'ascendant': cd.get('ascendant'),
        'midheaven': cd.get('midheaven'),
        'planets': planets,
        'moon': moon,
        'moon_timeline': None,
        'solar_conditions': _solar_conditions_from_chart(planets, cd),
        'top_aspects': _top_aspects_from_runtime(rt, cd),
        'morin_aspects': [],
        'fixed_star_hits': [],
        'house_cusps': cd.get('houses') or cd.get('house_cusps') or [],
        'house_rulers': cd.get('house_rulers') or {},
        'receptions': _lightweight_receptions_payload(
            data.chart_result if isinstance(data.chart_result, dict) else {},
            cd,
        ),
        'special_degrees': special_degrees,
        'morin_patterns': None,
    }


@astro_clock_bp.route('/current', methods=['GET'])
@_error_handler
def get_current():
    with _astro_perf_span('route.current'):
        eng = _engine_instance()
        with _astro_perf_span('route.current.get_current_data'):
            data = eng.get_current_data()
        with _astro_perf_span('route.current.serialize'):
            payload = _serialize_real_time(data)
    return _json_ok(payload)


def _build_dashboard_payload(
    eng: AstroClockEngine,
    data,
    include_modern: bool = False,
    include_morin: bool = False,
    special_degrees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    with _astro_perf_span(
        'helper.build_dashboard_payload.setup',
        include_modern=include_modern,
        include_morin=include_morin,
    ):
        rt = _serialize_real_time(data)
        cd = rt.get('chart_data') or {}
        try:
            chart_result = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
        except Exception:
            chart_result = {}
        active_settings = getattr(data, 'settings', None)
        active_location = getattr(active_settings, 'location', None) or eng.settings.location
        active_timezone = getattr(active_settings, 'timezone', None) or eng.settings.timezone
    # Normalize planets list for tiles
    planets = cd.get('planets') or []
    if isinstance(planets, dict):
        norm = []
        for name, info in planets.items():
            if isinstance(info, dict):
                p = dict(info)
                p.setdefault('planet', name)
                norm.append(p)
        planets = norm
    elif isinstance(planets, list):
        planets = [p for p in planets if isinstance(p, dict)]
    else:
        planets = []

    # Moon block
    moon = None
    try:
        mp = next((p for p in planets if p.get('planet') == 'Moon'), None)
        # Determine VoC with robust fallbacks: engine moon_state -> chart_data.considerations -> top-level result.considerations
        voc_flag = bool(rt.get('moon_state', {}).get('void_of_course'))
        if not voc_flag:
            try:
                voc_flag = bool((cd.get('considerations') or {}).get('moon_void')) if isinstance(cd, dict) else False
            except Exception:
                pass
        if not voc_flag:
            try:
                raw = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
                voc_flag = bool((raw.get('considerations') or {}).get('moon_void')) if isinstance(raw, dict) else False
            except Exception:
                pass
        if mp:
            moon = {
                'void_of_course': voc_flag,
                'sign': mp.get('sign'),
                'longitude': mp.get('longitude'),
                'house': mp.get('house'),
                'last_aspect': rt.get('moon_state', {}).get('last_aspect'),
                'next_aspect': rt.get('moon_state', {}).get('next_aspect'),
            }
    except Exception:
        moon = None

    # Moon VoC timeline (prefer engine's moon_state; fallback to chart_data or top-level result)
    moon_timeline = None
    try:
        mp = next((p for p in planets if p.get('planet') == 'Moon'), None)
        # Use the same robust VoC flag as above
        try:
            in_voc = bool(moon.get('void_of_course')) if isinstance(moon, dict) else bool(rt.get('moon_state', {}).get('void_of_course'))
        except Exception:
            in_voc = bool(rt.get('moon_state', {}).get('void_of_course'))
        deg_in_sign = (mp or {}).get('degree_in_sign')
        speed = (mp or {}).get('speed')
        next_aspect_payload = rt.get('moon_state', {}).get('next_aspect')
        if not next_aspect_payload:
            nas = cd.get('moon_next_aspect') if isinstance(cd, dict) else None
            if isinstance(nas, dict):
                # Ensure minimal keys used by timeline helper
                next_aspect_payload = {
                    'planet': nas.get('planet'),
                    'aspect': nas.get('aspect'),
                    'perfection_eta_days': nas.get('perfection_eta_days'),
                }
        # Fallback to top-level result if not present in chart_data
        if not next_aspect_payload:
            try:
                raw = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
            except Exception:
                raw = {}
            if isinstance(raw, dict) and isinstance(raw.get('moon_next_aspect'), dict):
                mna = raw.get('moon_next_aspect')
                next_aspect_payload = {
                    'planet': mna.get('planet'),
                    'aspect': mna.get('aspect'),
                    'perfection_eta_days': mna.get('perfection_eta_days'),
                }
        moon_timeline = build_moon_voc_timeline(cd, in_voc, deg_in_sign, speed, next_aspect_payload)
    except Exception:
        moon_timeline = None

    # Aspects summary (tightest + top 3 by orb).
    # Standard mode now prefers the precise aspect engine so the compact card
    # and the aspect-analysis modal read from the same source.
    aspects_raw = []
    try:
        a_top = rt.get('current_aspects') or []
        if isinstance(a_top, list) and a_top:
            aspects_raw = a_top
        else:
            a2 = cd.get('aspects')
            if isinstance(a2, list):
                aspects_raw = a2
    except Exception:
        aspects_raw = []
    planetary_aspects_precise = []
    try:
        ts_iso = rt.get('timestamp') or data.timestamp.isoformat()
        planetary_aspects_precise = _dedupe_aspect_rows(
            compute_planetary_aspects_precise(
                cd,
                ts_iso,
                include_modern=include_modern,
            ) or []
        )
    except Exception:
        planetary_aspects_precise = []
    top_aspects = []
    tightest = None
    try:
        aspects_sorted = planetary_aspects_precise or _dedupe_aspect_rows(aspects_raw)
        tightest = aspects_sorted[0] if aspects_sorted else None
        top_aspects = aspects_sorted[:3]
    except Exception:
        pass

    # Fixed stars (Sun/Moon and cusps)
    with _astro_perf_span('helper.build_dashboard_payload.fixed_stars'):
        try:
            fixed_star_hits = compute_fixed_star_hits(cd, orb_deg=1.0, check_planets=['Sun','Moon'], include_cusps=True)
        except Exception:
            fixed_star_hits = []

    # Arabic Lots
    with _astro_perf_span('helper.build_dashboard_payload.arabic_parts'):
        try:
            arabic_parts = compute_arabic_parts(cd)
        except Exception:
            arabic_parts = {}

    # Solar conditions: prefer engine-provided summary; fallback to per-planet solar_condition
    solar_conditions = {'cazimi': [], 'combustion': [], 'under_beams': [], 'free': []}
    try:
        summary = cd.get('solar_conditions_summary') if isinstance(cd, dict) else None
        if isinstance(summary, dict):
            for item in (summary.get('cazimi_planets') or []):
                solar_conditions['cazimi'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                    'exact_cazimi': item.get('exact_cazimi', False),
                })
            for item in (summary.get('combusted_planets') or []):
                solar_conditions['combustion'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                    'traditional_exception': item.get('traditional_exception', False),
                })
            for item in (summary.get('under_beams_planets') or []):
                solar_conditions['under_beams'].append({
                    'planet': item.get('planet') or item.get('name'),
                    'dignity_effect': item.get('dignity_effect'),
                    'distance_from_sun': item.get('distance_from_sun'),
                })
            for item in (summary.get('free_planets') or []):
                pname = item.get('planet') or item.get('name')
                if pname:
                    solar_conditions['free'].append({'planet': pname})
        else:
            # Fallback: infer from per-planet fields
            for p in planets:
                sc = p.get('solar_condition') if isinstance(p, dict) else None
                if not isinstance(sc, dict):
                    if p.get('planet'):
                        solar_conditions['free'].append({'planet': p.get('planet')})
                    continue
                cond = str(sc.get('condition') or '').lower()
                entry = {
                    'planet': p.get('planet'),
                    'dignity_effect': sc.get('dignity_effect'),
                    'distance_from_sun': sc.get('distance_from_sun'),
                    'exact_cazimi': sc.get('exact_cazimi'),
                    'traditional_exception': sc.get('traditional_exception'),
                }
                if 'cazimi' in cond:
                    solar_conditions['cazimi'].append(entry)
                elif 'combust' in cond:
                    solar_conditions['combustion'].append(entry)
                elif 'beam' in cond:
                    solar_conditions['under_beams'].append(entry)
                else:
                    if p.get('planet'):
                        solar_conditions['free'].append({'planet': p.get('planet')})
    except Exception:
        solar_conditions = {'cazimi': [], 'combustion': [], 'under_beams': [], 'free': []}

    # Sect
    with _astro_perf_span('helper.build_dashboard_payload.sect'):
        try:
            sect = compute_sect_info(cd)
        except Exception:
            sect = None

    # Cusp Aspects (≤ 1° to planets) — ensure we have a real timezone for forward sampling
    with _astro_perf_span('helper.build_dashboard_payload.cusp_aspects'):
        try:
            ts_for_cs = rt.get('timestamp')
            loc_for_cs = active_location
            tz_for_cs = active_timezone
            if _is_placeholder_tz(tz_for_cs) and loc_for_cs:
                coords = _ensure_coords_for_location(loc_for_cs, settings_hint=active_settings)
                if coords:
                    try:
                        lat, lon = coords
                        guess = _tz_instance().get_timezone_for_location(lat, lon)
                        if guess:
                            tz_for_cs = guess
                    except Exception:
                        pass
            cs_coords = _coords_from_settings(active_settings)
            if cs_coords is None and loc_for_cs:
                cs_coords = _ensure_coords_for_location(loc_for_cs, settings_hint=active_settings)
            future_chart_data = _future_cusp_phase_chart_data(
                ts_for_cs,
                location=loc_for_cs,
                timezone_name=tz_for_cs,
                latitude=(cs_coords[0] if cs_coords else None),
                longitude=(cs_coords[1] if cs_coords else None),
                house_system_code=(cd.get('house_system_code') if isinstance(cd, dict) else None),
            )
            cusp_aspects = compute_cusp_aspects(
                cd,
                include_modern=include_modern,
                orb_deg=1.0,
                timestamp_iso=ts_for_cs,
                location=loc_for_cs,
                timezone=tz_for_cs,
                latitude=(cs_coords[0] if cs_coords else None),
                longitude=(cs_coords[1] if cs_coords else None),
                house_system_code=(cd.get('house_system_code') if isinstance(cd, dict) else None),
                future_chart_data=future_chart_data,
            )
        except Exception:
            cusp_aspects = {}

    # Dispositors
    dispositors = {}
    try:
        for k, chain in (rt.get('dispositor_chains') or {}).items():
            dispositors[k] = {
                'dispositor': chain.get('dispositor'),
                'chain': list(chain.get('chain') or []),
                'final_dispositor': chain.get('final_dispositor'),
                'mutual_reception': bool(chain.get('mutual_reception')),
                'reception_partner': chain.get('reception_partner'),
            }
    except Exception:
        dispositors = {}

    # Timezone label
    timezone_label = None
    try:
        tzinfo = cd.get('timezone_info') if isinstance(cd, dict) else None
        if isinstance(tzinfo, dict):
            tz_name = tzinfo.get('timezone')
            local_iso = tzinfo.get('local_time')
            utc_iso = tzinfo.get('utc_time')
            if tz_name and local_iso and utc_iso:
                from datetime import datetime as _dt
                loc_dt = _dt.fromisoformat(local_iso.replace('Z','+00:00'))
                utc_dt = _dt.fromisoformat(utc_iso.replace('Z','+00:00'))
                delta_min = int((loc_dt - utc_dt).total_seconds() // 60)
                sign = '+' if delta_min >= 0 else '-'
                hh = abs(delta_min)//60; mm = abs(delta_min)%60
                timezone_label = f"{tz_name} (UTC{sign}{hh:02d}:{mm:02d})"
    except Exception:
        timezone_label = None

    # Special degrees pass-through for Metrics tile caption
    if special_degrees is None:
        special_degrees = _normalize_special_degree_tokens(request.args.getlist('special_degree'))
    else:
        special_degrees = _normalize_special_degree_tokens(special_degrees)

    # Influence & Afflictions metrics for Metrics tile
    with _astro_perf_span('helper.build_dashboard_payload.metrics'):
        try:
            metrics_chart_data = cd
            if isinstance(cd, dict) and arabic_parts:
                metrics_chart_data = dict(cd)
                metrics_chart_data['arabic_parts'] = arabic_parts
            metrics = compute_metrics(metrics_chart_data, timestamp_iso=rt.get('timestamp'), special_degrees=special_degrees)
        except Exception:
            metrics = None

    with _astro_perf_span('helper.build_dashboard_payload.almutens'):
        try:
            almutens = compute_chart_almutens(cd)
        except Exception:
            logger.exception("Failed to compute dashboard almutens")
            almutens = {"items": [], "points": {}, "display_order": [], "sect": None}

    with _astro_perf_span('helper.build_dashboard_payload.asteroids'):
        try:
            asteroid_timestamp = rt.get('timestamp') or data.timestamp.isoformat()
            asteroids = compute_asteroid_positions(cd, asteroid_timestamp)
        except Exception:
            logger.exception("Failed to compute dashboard asteroids")
            asteroids = {
                "items": [],
                "missing": [],
                "status": "unavailable",
                "message": "Asteroid data is unavailable.",
                "ephemeris_available": False,
            }

    morin_payload = _empty_morin_dashboard_payload()
    if include_morin:
        with _astro_perf_span('helper.build_dashboard_payload.morin'):
            ts_iso = None
            try:
                ts_iso = data.timestamp.isoformat()
            except Exception:
                ts_iso = rt.get('timestamp')
            morin_payload = _compute_morin_dashboard_payload(cd, ts_iso)

    with _astro_perf_span('helper.build_dashboard_payload.receptions'):
        receptions = _extract_receptions_payload(chart_result)

    payload = {
        'timestamp': data.timestamp.isoformat(),
        'location': active_location,
        'timezone': active_timezone,
        'timezone_label': timezone_label,
        'planets': planets,
        'moon': moon,
        'moon_timeline': moon_timeline,
        'solar_conditions': solar_conditions,
        'tightest_aspect': tightest,
        'top_aspects': top_aspects,
        'planetary_aspects_precise': planetary_aspects_precise,
        'fixed_star_hits': fixed_star_hits,
        'arabic_parts': arabic_parts,
        'sect': sect,
        'dispositors': dispositors,
        'cusp_aspects': cusp_aspects,
        'house_cusps': cd.get('houses') or cd.get('house_cusps') or [],
        'house_rulers': cd.get('house_rulers') or {},
        'receptions': receptions,
        'special_degrees': special_degrees,
        'metrics': metrics,
        'almutens': almutens,
        'asteroids': asteroids,
        'morin_aspects': morin_payload['morin_aspects'],
        'morin_antiscia': morin_payload['morin_antiscia'],
        'morin_contra_antiscia': morin_payload['morin_contra_antiscia'],
        'morin_combustion': morin_payload['morin_combustion'],
        'morin_patterns': morin_payload['morin_patterns'],
        # Additional Morin payloads gated by include_morin flag
    }
    return payload


@astro_clock_bp.route('/dashboard', methods=['GET'])
@_error_handler
def get_dashboard():
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    include_morin = (request.args.get('morin', '0').lower() in {'1','true','yes'})
    with _astro_perf_span(
        'route.dashboard',
        include_modern=include_modern,
        include_morin=include_morin,
    ):
        eng = _engine_instance()
        data, _active_settings = _data_for_request_clock_context(eng)
        payload = _build_dashboard_payload(
            eng,
            data,
            include_modern=include_modern,
            include_morin=include_morin,
        )
    return _json_ok(payload)


def _is_placeholder_tz(t: Optional[str]) -> bool:
    if not t:
        return True
    s = str(t).strip()
    return s in ("UTC", "Etc/UTC", "Etc/GMT", "GMT")


def _normalize_location_key(location: Optional[str]) -> str:
    return " ".join(str(location or "").strip().lower().split())


def _default_coords_for_location(location: Optional[str]) -> Optional[Tuple[float, float]]:
    normalized = _normalize_location_key(location)
    if normalized in {"greenwich", "greenwich uk", "greenwich, uk"}:
        return (51.4769, -0.0005)
    return None


def _coords_from_settings(settings: Optional[AstroClockSettings]) -> Optional[Tuple[float, float]]:
    if settings is None:
        return None
    lat = getattr(settings, "latitude", None)
    lon = getattr(settings, "longitude", None)
    if lat is None or lon is None:
        return None
    try:
        return (float(lat), float(lon))
    except Exception:
        return None


def _coords_from_request_args(args: Any, *, strict: bool = False) -> Optional[Tuple[float, float]]:
    if args is None:
        return None
    q_lat = args.get('latitude')
    q_lon = args.get('longitude')
    if q_lat is None and q_lon is None:
        return None
    if q_lat is None or q_lon is None:
        if strict:
            raise LocationError('latitude and longitude must be provided together')
        return None
    try:
        lat = float(q_lat)
    except Exception as exc:
        if strict:
            raise LocationError('Invalid latitude') from exc
        return None
    try:
        lon = float(q_lon)
    except Exception as exc:
        if strict:
            raise LocationError('Invalid longitude') from exc
        return None
    if not (-90.0 <= lat <= 90.0):
        if strict:
            raise LocationError('Invalid latitude')
        return None
    if not (-180.0 <= lon <= 180.0):
        if strict:
            raise LocationError('Invalid longitude')
        return None
    return (lat, lon)


def _settings_match_location(settings: Optional[AstroClockSettings], location: Optional[str]) -> bool:
    if settings is None or not location:
        return False
    return _normalize_location_key(getattr(settings, "location", None)) == _normalize_location_key(location)


def _normalize_special_degree_tokens(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        raw = [raw]
    elif not isinstance(raw, (list, tuple, set)):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for item in raw:
        tok = str(item or "").strip()
        if not tok:
            continue
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok)
    return out


def _parse_iso_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def _resolve_timezone_for_context(
    timezone_name: Optional[str],
    location: Optional[str],
    *,
    coords: Optional[Tuple[float, float]] = None,
) -> Optional[str]:
    tz = str(timezone_name).strip() if timezone_name is not None else None
    if tz and (not _is_placeholder_tz(tz)):
        try:
            ZoneInfo(tz)
            return tz
        except Exception:
            tz = None
    if coords is None and location:
        coords = _ensure_coords_for_location(location)
    if coords:
        try:
            lat, lon = coords
            guess = _tz_instance().get_timezone_for_location(lat, lon)
            if guess:
                return guess
        except Exception:
            pass
    return tz or None


def _normalize_manual_datetime(
    dt_raw: Any,
    *,
    timezone_name: Optional[str],
    location: Optional[str],
) -> Tuple[Optional[datetime], Optional[str]]:
    if dt_raw in (None, "", "null"):
        resolved_tz = _resolve_timezone_for_context(timezone_name, location)
        return None, resolved_tz

    parsed = _parse_iso_datetime(dt_raw)
    resolved_tz = _resolve_timezone_for_context(timezone_name, location)

    if parsed.tzinfo is not None:
        normalized = parsed.astimezone(timezone.utc)
        return normalized, (resolved_tz or "UTC")

    if resolved_tz:
        try:
            local_dt = parsed.replace(tzinfo=ZoneInfo(resolved_tz))
            return local_dt.astimezone(timezone.utc), resolved_tz
        except Exception:
            pass

    return parsed.replace(tzinfo=timezone.utc), "UTC"


def _localize(dt: datetime, tz: Optional[str]) -> datetime:
    target_tz = None
    try:
        if tz:
            target_tz = ZoneInfo(str(tz).strip())
    except Exception:
        target_tz = None

    if dt.tzinfo is None:
        if target_tz is not None:
            return dt.replace(tzinfo=target_tz)
        return dt.replace(tzinfo=timezone.utc)

    if target_tz is not None:
        try:
            return dt.astimezone(target_tz)
        except Exception:
            pass
    return dt


def _ensure_coords_for_location(
    location: Optional[str],
    settings_hint: Optional[AstroClockSettings] = None,
) -> Optional[Tuple[float, float]]:
    if not location:
        return None
    default_coords = _default_coords_for_location(location)
    if default_coords is not None:
        return default_coords
    for candidate in (
        settings_hint,
        getattr(_engine, "settings", None) if _engine is not None else None,
    ):
        if _settings_match_location(candidate, location):
            coords = _coords_from_settings(candidate)
            if coords:
                return coords
    try:
        lat, lon, _ = safe_geocode(location)
        return (lat, lon)
    except Exception:
        return None


@astro_clock_bp.route('/planetary-hours', methods=['GET'])
@_error_handler
def get_planetary_hours():
    eng = _engine_instance()
    data, active_settings = _data_for_request_clock_context(eng)
    target_dt: Optional[datetime] = None
    date_str = request.args.get('date')
    datetime_str = request.args.get('datetime')
    if datetime_str:
        try:
            target_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid datetime'}), 400
    elif date_str:
        try:
            target_dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid date'}), 400
    if target_dt is None:
        target_dt = data.timestamp if getattr(data, 'timestamp', None) else eng.get_effective_datetime()

    active_location = getattr(active_settings, 'location', None) or eng.settings.location
    active_timezone = getattr(active_settings, 'timezone', None) or eng.settings.timezone
    coords = _ensure_coords_for_location(active_location, settings_hint=active_settings)
    if coords is None:
        # Use engine-set coords if available, else default to Greenwich
        lat = float(getattr(active_settings, 'latitude', None)) if getattr(active_settings, 'latitude', None) is not None else 51.4769
        lon = float(getattr(active_settings, 'longitude', None)) if getattr(active_settings, 'longitude', None) is not None else -0.0005
    else:
        lat, lon = coords
    calc = _ph_instance(lat, lon)
    tz = active_timezone
    if _is_placeholder_tz(tz) and (lat is not None and lon is not None):
        try:
            guess = _tz_instance().get_timezone_for_location(lat, lon)
            if guess:
                tz = guess
        except Exception:
            pass
    target_local = _localize(target_dt, tz)
    daily = calc.calculate_daily_hours(target_local.date())
    # try locate current hour
    try:
        daily.current_hour = calc.get_current_planetary_hour(target_local)
    except Exception:
        pass
    return _json_ok(_serialize_daily_hours(daily))


# Snaps (minimal): use filesystem JSON store (same API surface)
from snaps_store import SnapStore
_snap_store: Optional[SnapStore] = None


def _snap_store_path() -> Path:
    """Resolve a user-writable snap storage path."""
    explicit_dir = (os.environ.get("HORARY_DATA_DIR") or "").strip()
    if explicit_dir:
        base = Path(explicit_dir)
    else:
        local_appdata = (os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or "").strip()
        if local_appdata:
            base = Path(local_appdata) / "VoxStella" / "backend"
        else:
            base = Path(tempfile.gettempdir()) / "VoxStella" / "backend"
    return base / "snaps_store.json"


def _snaps() -> SnapStore:
    global _snap_store
    if _snap_store is None:
        try:
            max_snaps = int(os.environ.get("HORARY_MAX_SNAPS", "500"))
        except Exception:
            max_snaps = 500
        _snap_store = SnapStore(str(_snap_store_path()), max_snaps=max_snaps)
    return _snap_store


@astro_clock_bp.route('/snap', methods=['POST'])
@_error_handler
def create_snap():
    eng = _engine_instance()
    data = eng.get_current_data()
    payload = request.get_json() or {}
    label = payload.get('label') or 'Snapshot'
    include_modern = bool(payload.get('include_modern'))
    special_degrees = _normalize_special_degree_tokens(payload.get('special_degrees'))
    dash = _build_dashboard_payload(eng, data, include_modern=include_modern, special_degrees=special_degrees)
    chart_result = data.chart_result
    if isinstance(chart_result, str):
        try:
            chart_result = json.loads(chart_result)
        except Exception:
            chart_result = {}
    chart_snapshot = _synastry_chart_snapshot_from_chart_data(
        _extract_chart_data_from_result(chart_result if isinstance(chart_result, dict) else {})
    )
    profile_hint = _extract_synastry_profile_hint(
        payload,
        chart_result if isinstance(chart_result, dict) else {},
        chart_snapshot,
    )
    active_settings = getattr(data, 'settings', None)
    active_location = getattr(active_settings, 'location', None) or eng.settings.location
    active_timezone = getattr(active_settings, 'timezone', None) or eng.settings.timezone

    # Summary for listing/search
    # Planetary hour ruler
    hour_ruler = None
    try:
        coords = _ensure_coords_for_location(active_location, settings_hint=active_settings)
        if coords:
            lat, lon = coords
            calc = _ph_instance(lat, lon)
            cur = calc.get_current_planetary_hour(_localize(data.timestamp, active_timezone))
            hour_ruler = getattr(cur.ruling_planet, 'value', None) if cur else None
    except Exception:
        pass
    # Moon sign
    moon_sign = None
    try:
        m = next((p for p in dash.get('planets', []) if p.get('planet')=='Moon'), None)
        if m:
            moon_sign = m.get('sign')
    except Exception:
        pass
    # Sect summary
    sect_info = None
    try:
        sect_info = compute_sect_info(dash)
    except Exception:
        sect_info = None

    from uuid import uuid4
    snap = {
        'id': str(uuid4()),
        'label': label,
        'effective_datetime': data.timestamp.isoformat(),
        'location': active_location,
        'special_degrees': special_degrees,
        'summary': {
            'hour_ruler': hour_ruler,
            'moon_sign': moon_sign,
            'chart_sect': (sect_info or {}).get('chart_sect'),
            'sect_light': (sect_info or {}).get('sect_light'),
            'profile_hint': profile_hint,
        },
        'chart_snapshot': chart_snapshot,
        'dashboard': dash,
    }
    if profile_hint:
        snap['profile_hint'] = profile_hint
    store = _snaps()
    store.add(snap)
    return _json_ok({'id': snap['id'], 'label': label})


@astro_clock_bp.route('/snaps', methods=['GET'])
@_error_handler
def list_snaps():
    store = _snaps()
    items = []
    for snap in store.list():
        dashboard = snap.get('dashboard') if isinstance(snap, dict) else {}
        items.append({
            'id': snap.get('id'),
            'label': snap.get('label'),
            'effective_datetime': snap.get('effective_datetime'),
            'location': snap.get('location'),
            'summary': {
                **(snap.get('summary') or {}),
                'profile_hint': snap.get('profile_hint') or (snap.get('summary') or {}).get('profile_hint'),
            },
            'special_degrees': snap.get('special_degrees') or [],
            'dashboard': {
                'timezone': (dashboard or {}).get('timezone'),
                'timezone_label': (dashboard or {}).get('timezone_label'),
            },
        })
    # Frontend expects success flag and top-level items
    from flask import jsonify as _j
    return _j({'success': True, 'items': items})


@astro_clock_bp.route('/snaps/<snap_id>', methods=['GET'])
@_error_handler
def get_snap(snap_id: str):
    store = _snaps()
    snap = store.get(snap_id)
    if not snap:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'snap': snap})


@astro_clock_bp.route('/snaps/<snap_id>', methods=['DELETE'])
@_error_handler
def delete_snap(snap_id: str):
    store = _snaps()
    ok = store.delete(snap_id)
    return jsonify({'success': True, 'ok': bool(ok)})


@astro_clock_bp.route('/mode', methods=['POST'])
@_error_handler
def set_mode():
    eng = _engine_instance()
    payload = request.get_json() or {}
    mode = str(payload.get('mode') or '').lower()
    if mode not in {'realtime', 'manual', 'paused'}:
        return jsonify({'success': False, 'error': 'Invalid mode'}), 400
    with _engine_lock:
        if mode == 'manual':
            dt = payload.get('datetime')
            tz = payload.get('timezone')
            loc = payload.get('location')
            house_code = payload.get('house_system_code') or payload.get('house_system')
            try:
                target_location = loc or eng.settings.location
                coords = (
                    _coords_from_settings(eng.settings)
                    if _settings_match_location(eng.settings, target_location)
                    else None
                )
                if coords is None and target_location:
                    coords = _ensure_coords_for_location(target_location)
                custom, resolved_tz = _normalize_manual_datetime(
                    dt,
                    timezone_name=_resolve_timezone_for_context(tz, target_location, coords=coords),
                    location=target_location,
                )
            except Exception:
                return jsonify({'success': False, 'error': 'Invalid datetime'}), 400
            # Honor house system preference if provided
            try:
                if house_code:
                    eng.update_settings(house_system_code=house_code)
            except Exception:
                pass
            eng.set_mode(
                eng.settings.mode.__class__.MANUAL,
                location=(loc or eng.settings.location),
                custom_time=custom,
                timezone=(resolved_tz or tz or eng.settings.timezone),
                latitude=(coords[0] if coords else None),
                longitude=(coords[1] if coords else None),
            )
        elif mode == 'paused':
            eng.pause_at_current_time()
        else:
            # Realtime: allow updating location/timezone consistently
            loc = payload.get('location')
            tz = payload.get('timezone')
            house_code = payload.get('house_system_code') or payload.get('house_system')
            try:
                if house_code:
                    eng.update_settings(house_system_code=house_code)
            except Exception:
                pass
            if loc or tz:
                try:
                    realtime_location = loc or eng.settings.location
                    coords = (
                        _coords_from_settings(eng.settings)
                        if _settings_match_location(eng.settings, realtime_location)
                        else None
                    )
                    if coords is None and realtime_location:
                        coords = _ensure_coords_for_location(realtime_location)
                    realtime_tz = _resolve_timezone_for_context(tz, realtime_location, coords=coords) or eng.settings.timezone
                    eng.set_mode(
                        eng.settings.mode.__class__.REALTIME,
                        location=realtime_location,
                        timezone=realtime_tz,
                        latitude=(coords[0] if coords else None),
                        longitude=(coords[1] if coords else None),
                    )
                except Exception:
                    eng.resume_realtime()
            else:
                eng.resume_realtime()
    return _json_ok({'mode': eng.settings.mode.value})


@astro_clock_bp.route('/location', methods=['POST'])
@_error_handler
def set_location():
    payload = request.get_json() or {}
    loc = payload.get('location')
    if not loc:
        return jsonify({'success': False, 'error': 'location is required'}), 400
    eng = _engine_instance()
    with _engine_lock:
        eng.update_settings(location=loc)
    # refresh planetary hours coordinates cache
    coords = _ensure_coords_for_location(loc)
    if coords:
        try:
            lat, lon = coords
            with _engine_lock:
                eng.update_settings(latitude=lat, longitude=lon)
        except Exception:
            pass
    return _json_ok({'location': eng.settings.location})


@astro_clock_bp.route('/receptions', methods=['GET'])
@_error_handler
def get_receptions():
    """Return a compact receptions summary for the dashboard tile.

    If the horary engine didn't include detailed reception structures,
    compute them on the fly from the serialized chart using the
    TraditionalReceptionCalculator so dev parity matches packaged builds.
    """
    eng = _engine_instance()
    data = eng.get_current_data()
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    return _json_ok(_extract_receptions_payload(chart))


@astro_clock_bp.route('/compass', methods=['GET'])
@_error_handler
def get_compass():
    """Approximate compass bearings for planets based on chart longitudes.

    We align Ascendant to 90° (East) and rotate ecliptic longitudes into a
    simple compass frame (0=N at top). This is a visualization aid for the
    dashboard and not a true horizon projection.
    """
    include_modern = (request.args.get('include_modern', '0').lower() in {'1', 'true', 'yes'})
    eng = _engine_instance()
    data = eng.get_current_data()
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    cd = chart.get('chart_data', {}) if isinstance(chart, dict) else {}
    asc = float(cd.get('ascendant') or 0.0)
    planets = cd.get('planets') or {}
    # normalize to dict mapping
    if isinstance(planets, list):
        pm = {}
        for p in planets:
            try:
                pm[p.get('planet')] = p
            except Exception:
                continue
        planets = pm
    out = []
    classical = {'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn'}
    for name, info in planets.items():
        if not include_modern and name not in classical:
            continue
        try:
            lon = float(info.get('longitude') or 0.0)
        except Exception:
            lon = 0.0
        # Rotate so Asc is East (90°). Compass is 0=N at top.
        az = (lon - asc + 90.0) % 360.0
        out.append({'planet': name, 'azimuth_deg': az})
    return _json_ok({'azimuths': out, 'ascendant': asc})


@astro_clock_bp.route('/stream', methods=['GET'])
def stream_ticks():
    """Minimal SSE stream for live dashboard updates."""
    @stream_with_context
    def _gen():
        import time
        # Send a first payload immediately
        payload = {'tick': datetime.now(timezone.utc).isoformat()}
        yield f"data: {json.dumps(payload)}\n\n"
        # Light heartbeat for a short period; clients may reconnect
        for _ in range(15):
            time.sleep(1)
            payload = {'tick': datetime.now(timezone.utc).isoformat()}
            yield f"data: {json.dumps(payload)}\n\n"
    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    return Response(_gen(), headers=headers)


__all__ = ['astro_clock_bp']


# ---------- Feature Endpoints: Traits, Transits, Context, Forensic, Election ----------

def _extract_chart_data_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    try:
        cd = result.get('chart_data')
        if isinstance(cd, str):
            cd = json.loads(cd)
        return cd if isinstance(cd, dict) else {}
    except Exception:
        return {}


def _extract_internal_chart_from_result(result: Dict[str, Any]) -> Optional[Any]:
    try:
        raw_chart = result.get('_raw_chart')
        return raw_chart if raw_chart is not None else None
    except Exception:
        return None


def _build_chart_bundle(result: Any, meta: Dict[str, Any]) -> Dict[str, Any]:
    chart_result = result
    if isinstance(chart_result, str):
        try:
            chart_result = json.loads(chart_result)
        except Exception:
            chart_result = {}
    if not isinstance(chart_result, dict):
        chart_result = {}
    return {
        'chart_result': chart_result,
        'chart_data': _extract_chart_data_from_result(chart_result),
        'meta': meta,
        'raw_chart': _extract_internal_chart_from_result(chart_result),
    }


def _future_cusp_phase_chart_data(
    timestamp_iso: Optional[str],
    *,
    location: Optional[str],
    timezone_name: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    house_system_code: Optional[str],
    dt_hours: float = 0.5,
) -> Optional[Dict[str, Any]]:
    if not timestamp_iso:
        return None
    try:
        base_dt = datetime.fromisoformat(str(timestamp_iso).replace('Z', '+00:00'))
    except Exception:
        return None

    future_dt = base_dt + timedelta(hours=float(dt_hours or 0.5))
    with _astro_perf_span(
        'helper.future_cusp_phase_chart_data',
        dt_hours=float(dt_hours or 0.5),
        house_system_code=house_system_code,
    ):
        try:
            bundle = _compute_chart_bundle_for(
                future_dt.isoformat(),
                location,
                timezone_name,
                house_system_code=house_system_code,
                latitude=latitude,
                longitude=longitude,
            )
        except Exception:
            return None
    chart_data = bundle.get('chart_data') or {}
    return chart_data if isinstance(chart_data, dict) else None


def _compute_chart_bundle_for(dt_iso: Optional[str], location: Optional[str], timezone: Optional[str],
                              house_system_code: Optional[str] = None,
                              latitude: Optional[float] = None,
                              longitude: Optional[float] = None) -> Dict[str, Any]:
    """Return an internal chart bundle for a given datetime/location.

    This keeps the public `(chart_data, meta)` contract stable while allowing
    same-process callers to retain the raw chart object when the horary engine
    produced one.
    """
    with _astro_perf_span(
        'helper.compute_chart_bundle_for',
        has_datetime=bool(dt_iso),
        has_location=bool(location),
        has_timezone=bool(timezone),
        house_system_code=house_system_code,
    ):
        eng = _engine_instance()
        resolved_location = location or eng.settings.location
        resolved_coords = None
        if latitude is not None and longitude is not None:
            try:
                resolved_coords = (float(latitude), float(longitude))
            except Exception:
                resolved_coords = None
        if resolved_coords is None:
            resolved_coords = (
                _coords_from_settings(eng.settings)
                if _settings_match_location(eng.settings, resolved_location)
                else None
            )
        if resolved_coords is None and resolved_location:
            resolved_coords = _ensure_coords_for_location(resolved_location)
        resolved_tz = _resolve_timezone_for_context(timezone, resolved_location, coords=resolved_coords)
        custom = None
        parsed_tz = None
        if dt_iso:
            try:
                custom, parsed_tz = _normalize_manual_datetime(
                    dt_iso,
                    timezone_name=resolved_tz,
                    location=resolved_location,
                )
            except Exception:
                custom = None
                parsed_tz = None
        tz = resolved_tz or parsed_tz
        local = AstroClockSettings(
            mode=ClockMode.MANUAL if custom else ClockMode.REALTIME,
            location=resolved_location,
            custom_time=custom,
            timezone=tz or eng.settings.timezone,
            latitude=(resolved_coords[0] if resolved_coords else None),
            longitude=(resolved_coords[1] if resolved_coords else None),
            paused_at=None,
            house_system_code=house_system_code or getattr(eng.settings, 'house_system_code', None),
        )
        with _astro_perf_span('helper.compute_chart_bundle_for.get_current_data'):
            with _engine_lock:
                data = eng.get_current_data(settings=local)
    tz_name = local.timezone
    try:
        ts_local = _localize(data.timestamp, tz_name)
    except Exception:
        ts_local = data.timestamp
        if ts_local.tzinfo is None:
            from datetime import timezone as _dt_timezone
            ts_local = ts_local.replace(tzinfo=_dt_timezone.utc)
    meta = {
        'timestamp': ts_local.isoformat(),
        'location': local.location,
        'timezone': tz_name,
        'latitude': (resolved_coords[0] if resolved_coords else None),
        'longitude': (resolved_coords[1] if resolved_coords else None),
    }
    return _build_chart_bundle(getattr(data, 'chart_result', {}), meta)


def _compute_chart_for(dt_iso: Optional[str], location: Optional[str], timezone: Optional[str],
                       house_system_code: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (chart_data, meta) for a given datetime/location using the engine, without mutating global state.

    meta contains: {'timestamp': iso, 'location': str, 'timezone': str}
    """
    bundle = _compute_chart_bundle_for(dt_iso, location, timezone, house_system_code=house_system_code)
    return bundle.get('chart_data') or {}, bundle.get('meta') or {}


_SYN_AUGMENT_SIGN_NAMES = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
_SYN_AUGMENT_POINT_IDS = {
    "Uranus": "URANUS",
    "Neptune": "NEPTUNE",
    "Pluto": "PLUTO",
    "Chiron": "CHIRON",
}


def _synastry_sign_name_from_longitude(lon: float) -> str:
    idx = int((float(lon) % 360.0) // 30.0) % 12
    return _SYN_AUGMENT_SIGN_NAMES[idx]


def _synastry_house_cusps(chart_data: Dict[str, Any]) -> List[float]:
    raw = chart_data.get('houses') or chart_data.get('house_cusps') or []
    if not isinstance(raw, list):
        return []
    out: List[float] = []
    for item in raw[:12]:
        try:
            out.append(float(item) % 360.0)
        except Exception:
            continue
    return out


def _synastry_longitude_in_arc(start: float, end: float, point: float) -> bool:
    start = float(start) % 360.0
    end = float(end) % 360.0
    point = float(point) % 360.0
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def _synastry_house_for_longitude(lon: float, cusps: List[float]) -> Optional[int]:
    if len(cusps) < 12:
        return None
    for idx in range(12):
        if _synastry_longitude_in_arc(cusps[idx], cusps[(idx + 1) % 12], lon):
            return idx + 1
    return None


def _configure_synastry_ephemeris_path(swe_module: Any) -> None:
    try:
        swe_module.set_ephe_path(_resolve_synastry_ephemeris_path() or '')
    except Exception:
        pass


def _synastry_point_capability(meta: Dict[str, Any]) -> Dict[str, bool]:
    try:
        import swisseph as _swe  # type: ignore
        timestamp = str((meta or {}).get('timestamp') or '').strip()
        if not timestamp:
            return {"modern_supported": False, "chiron_supported": False}
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        hour_decimal = (
            dt_utc.hour
            + (dt_utc.minute / 60.0)
            + (dt_utc.second / 3600.0)
            + (dt_utc.microsecond / 3_600_000_000.0)
        )
        jd_ut = _swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal, _swe.GREG_CAL)
        _configure_synastry_ephemeris_path(_swe)

        modern_supported = True
        for key in ("URANUS", "NEPTUNE", "PLUTO"):
            point_id = getattr(_swe, key, None)
            if point_id is None:
                modern_supported = False
                break
            try:
                _swe.calc_ut(jd_ut, point_id, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
            except Exception:
                modern_supported = False
                break

        chiron_supported = False
        point_id = getattr(_swe, "CHIRON", None)
        if point_id is not None:
            try:
                _swe.calc_ut(jd_ut, point_id, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
                chiron_supported = True
            except Exception:
                chiron_supported = False
        return {
            "modern_supported": bool(modern_supported),
            "chiron_supported": bool(chiron_supported),
        }
    except Exception:
        return {"modern_supported": False, "chiron_supported": False}


def _extend_chart_data_for_synastry(
    chart_data: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    include_modern: bool,
    include_chiron: bool,
) -> Dict[str, Any]:
    if not include_modern and not include_chiron:
        return chart_data

    try:
        import swisseph as _swe  # type: ignore
    except Exception:
        return chart_data

    timestamp = str((meta or {}).get('timestamp') or '').strip()
    if not timestamp:
        return chart_data

    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        hour_decimal = (
            dt_utc.hour
            + (dt_utc.minute / 60.0)
            + (dt_utc.second / 3600.0)
            + (dt_utc.microsecond / 3_600_000_000.0)
        )
        jd_ut = _swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal, _swe.GREG_CAL)
        _configure_synastry_ephemeris_path(_swe)
    except Exception:
        return chart_data

    out = copy.deepcopy(chart_data if isinstance(chart_data, dict) else {})
    planets = out.get('planets')
    if isinstance(planets, dict):
        existing_names = {str(name).strip() for name in planets.keys()}
    elif isinstance(planets, list):
        existing_names = {
            str((row or {}).get('planet') or (row or {}).get('name') or '').strip()
            for row in planets
            if isinstance(row, dict)
        }
    else:
        planets = {}
        out['planets'] = planets
        existing_names = set()

    targets: List[str] = []
    if include_modern:
        targets.extend(["Uranus", "Neptune", "Pluto"])
    if include_chiron:
        targets.append("Chiron")

    cusps = _synastry_house_cusps(out)
    flags = _swe.FLG_SWIEPH | _swe.FLG_SPEED

    def _upsert(name: str, payload: Dict[str, Any]) -> None:
        nonlocal planets
        if isinstance(planets, dict):
            planets[name] = payload
            return
        if isinstance(planets, list):
            for idx, row in enumerate(planets):
                if not isinstance(row, dict):
                    continue
                row_name = str(row.get('planet') or row.get('name') or '').strip()
                if row_name == name:
                    merged = dict(payload)
                    merged['planet'] = name
                    planets[idx] = merged
                    return
            merged = dict(payload)
            merged['planet'] = name
            planets.append(merged)

    for name in targets:
        if name in existing_names:
            continue
        swe_key = _SYN_AUGMENT_POINT_IDS.get(name)
        point_id = getattr(_swe, swe_key, None) if swe_key else None
        if point_id is None:
            continue
        try:
            pos, _ = _swe.calc_ut(jd_ut, point_id, flags)
        except Exception:
            continue
        lon = float(pos[0]) % 360.0
        lat = float(pos[1])
        speed = float(pos[3]) if len(pos) > 3 else 0.0
        payload = {
            'longitude': lon,
            'latitude': lat,
            'house': _synastry_house_for_longitude(lon, cusps),
            'sign': _synastry_sign_name_from_longitude(lon),
            'dignity_score': 0,
            'essential_dignity': 0,
            'accidental_dignity': 0,
            'retrograde': speed < 0.0,
            'speed': speed,
            'degree_in_sign': lon % 30.0,
        }
        _upsert(name, payload)

    return out


def _extend_chart_data_for_marriage_beta(
    chart_data: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    include_moon_day: bool,
) -> Dict[str, Any]:
    out = _extend_chart_data_for_synastry(
        chart_data,
        meta,
        include_modern=True,
        include_chiron=False,
    )

    timestamp = str((meta or {}).get('timestamp') or '').strip()
    if not isinstance(out, dict):
        out = {}

    def _upsert_planet(name: str, payload: Dict[str, Any]) -> None:
        planets = out.get('planets')
        merged = dict(payload or {})
        merged.setdefault('planet', name)
        if isinstance(planets, dict):
            row = dict(merged)
            row.pop('planet', None)
            planets[name] = row
            return
        if isinstance(planets, list):
            for idx, row in enumerate(planets):
                if not isinstance(row, dict):
                    continue
                row_name = str(row.get('planet') or row.get('name') or '').strip()
                if row_name != name:
                    continue
                planets[idx] = merged
                return
            planets.append(merged)
            return
        row = dict(merged)
        row.pop('planet', None)
        out['planets'] = {name: row}

    try:
        asteroids_payload = compute_asteroid_positions(out, timestamp)
    except Exception:
        asteroids_payload = None

    if isinstance(asteroids_payload, dict):
        out['beta_asteroids'] = asteroids_payload
        for item in asteroids_payload.get('items') or []:
            if not isinstance(item, dict):
                continue
            if str(item.get('name') or '').strip() != 'Proserpina':
                continue
            _upsert_planet(
                'Proserpina',
                {
                    'planet': 'Proserpina',
                    'longitude': item.get('longitude'),
                    'latitude': item.get('latitude'),
                    'house': item.get('house'),
                    'sign': item.get('sign'),
                    'degree_in_sign': item.get('degree_in_sign'),
                    'retrograde': item.get('retrograde'),
                    'speed': item.get('speed'),
                    'tier': item.get('tier'),
                    'galaxy_body_id': item.get('galaxy_body_id'),
                },
            )
            break

    if include_moon_day:
        try:
            moon_day = compute_moon_day(out)
        except Exception:
            moon_day = None
        if isinstance(moon_day, dict) and moon_day:
            out['moon_day'] = moon_day

    try:
        if timestamp:
            out['planetary_aspects_precise'] = _dedupe_aspect_rows(
                compute_planetary_aspects_precise(
                    out,
                    timestamp,
                    include_modern=False,
                )
            )
    except Exception:
        pass

    return out


def _data_for_request_clock_context(eng: AstroClockEngine):
    """Resolve Astro Clock data for the current request without mutating engine state."""
    q_mode = str(request.args.get('mode') or '').strip().lower()
    q_dt = request.args.get('datetime')
    q_loc = request.args.get('location')
    q_tz = request.args.get('timezone')
    q_house = request.args.get('house_system_code') or request.args.get('house_system')
    q_coords = _coords_from_request_args(request.args, strict=True)

    use_override = bool(q_mode or q_dt or q_loc or q_tz or q_house or q_coords)
    with _astro_perf_span(
        'helper.data_for_request_clock_context',
        override=use_override,
        mode=q_mode or None,
        has_datetime=bool(q_dt),
        has_location=bool(q_loc),
        has_timezone=bool(q_tz),
        has_house=bool(q_house),
        has_coords=bool(q_coords),
    ):
        if not use_override:
            with _astro_perf_span('helper.data_for_request_clock_context.live_snapshot'):
                data = eng.get_current_data()
            active_settings = getattr(data, 'settings', None) or eng.settings
            return data, active_settings

        prev = eng.settings
        local_location = q_loc or prev.location
        local_coords = q_coords
        if local_coords is None:
            local_coords = _coords_from_settings(prev) if _settings_match_location(prev, local_location) else None
        if q_tz is not None or q_loc or q_coords:
            with _astro_perf_span('helper.data_for_request_clock_context.resolve_location_timezone'):
                if local_coords is None and local_location:
                    local_coords = _ensure_coords_for_location(local_location)
                local_tz = _resolve_timezone_for_context(q_tz, local_location, coords=local_coords) or prev.timezone
        else:
            local_tz = prev.timezone
        custom_override = prev.custom_time
        paused_override = prev.paused_at
        mode_override = prev.mode

        if q_mode == 'manual':
            mode_override = ClockMode.MANUAL
        elif q_mode == 'realtime':
            mode_override = ClockMode.REALTIME
        elif q_mode == 'paused':
            mode_override = ClockMode.PAUSED

        if q_dt:
            with _astro_perf_span('helper.data_for_request_clock_context.normalize_manual_datetime'):
                custom_override, normalized_tz = _normalize_manual_datetime(
                    q_dt,
                    timezone_name=q_tz,
                    location=local_location,
                )
            local_tz = normalized_tz or local_tz
            if q_mode != 'paused':
                mode_override = ClockMode.MANUAL

        if mode_override == ClockMode.REALTIME:
            custom_override = None
            paused_override = None
        elif mode_override == ClockMode.MANUAL:
            paused_override = None

        local = AstroClockSettings(
            mode=mode_override,
            location=local_location,
            custom_time=custom_override,
            timezone=local_tz,
            latitude=(local_coords[0] if local_coords else None),
            longitude=(local_coords[1] if local_coords else None),
            paused_at=paused_override,
            house_system_code=q_house or getattr(prev, 'house_system_code', None),
        )
        if local.mode == ClockMode.MANUAL and local.location and not local.timezone:
            with _astro_perf_span('helper.data_for_request_clock_context.infer_manual_timezone'):
                coords = local_coords or _ensure_coords_for_location(local.location, settings_hint=local)
                if coords:
                    lat, lon = coords
                    guess = _tz_instance().get_timezone_for_location(lat, lon)
                    if guess:
                        local.timezone = guess

        with _astro_perf_span('helper.data_for_request_clock_context.get_current_data'):
            data = eng.get_current_data(settings=local)
        active_settings = getattr(data, 'settings', None) or local
        return data, active_settings


def _mundane_active_clock_context() -> Dict[str, Any]:
    eng = _engine_instance()
    data, active_settings = _data_for_request_clock_context(eng)
    timestamp = getattr(data, 'timestamp', None)
    if isinstance(timestamp, datetime):
        timestamp = _localize(timestamp, getattr(active_settings, 'timezone', None)).isoformat()
    else:
        timestamp = datetime.now(timezone.utc).isoformat()
    coords = _coords_from_settings(active_settings)
    mode_value = getattr(getattr(active_settings, 'mode', None), 'value', None)
    if mode_value is None and getattr(active_settings, 'mode', None) is not None:
        mode_value = str(getattr(active_settings, 'mode'))
    return {
        'timestamp': timestamp,
        'location': getattr(active_settings, 'location', None),
        'timezone': getattr(active_settings, 'timezone', None),
        'mode': mode_value,
        'house_system_code': getattr(active_settings, 'house_system_code', None),
        'latitude': (coords[0] if coords else None),
        'longitude': (coords[1] if coords else None),
    }


def _mundane_bundle_resolver(
    dt_iso: str,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    return _compute_chart_bundle_for(
        dt_iso,
        location,
        timezone_name,
        house_system_code=house_system_code,
        latitude=latitude,
        longitude=longitude,
    )


def _weather_active_clock_context() -> Dict[str, Any]:
    return _mundane_active_clock_context()


def _weather_bundle_resolver(
    dt_iso: str,
    location: Optional[str],
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    bundle = _compute_chart_bundle_for(
        dt_iso,
        location,
        timezone_name,
        house_system_code=house_system_code,
        latitude=latitude,
        longitude=longitude,
    )
    bundle["chart_data"] = _extend_chart_data_for_synastry(
        bundle.get("chart_data") or {},
        bundle.get("meta") or {},
        include_modern=True,
        include_chiron=False,
    )
    return bundle


def _natal_from_query(args) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve natal chart_data from query params: use snap if provided, else use natal_* params."""
    bundle = _natal_bundle_from_query(args)
    return bundle.get('chart_data') or {}, bundle.get('meta') or {}


def _bundle_from_snap_id(
    snap_id: str,
    *,
    house_system_code: Optional[str] = None,
    missing_error: str = 'Snap not found',
) -> Dict[str, Any]:
    snap = _snaps().get(snap_id)
    if not snap:
        raise ValueError(missing_error)
    dt = snap.get('effective_datetime')
    loc = snap.get('location')
    tz = snap.get('timezone')
    return _compute_chart_bundle_for(dt, loc, tz, house_system_code=house_system_code)


def _natal_bundle_from_query(args) -> Dict[str, Any]:
    """Resolve an internal natal chart bundle from query params."""
    snap_id = args.get('natal_snap_id')
    if snap_id:
        house = args.get('house_system_code') or None
        return _bundle_from_snap_id(snap_id, house_system_code=house, missing_error='Natal snap not found')
    nat_dt = args.get('natal_datetime')
    nat_loc = args.get('natal_location')
    nat_tz = args.get('natal_timezone')
    house = args.get('house_system_code') or None
    if not nat_dt or not nat_loc:
        raise ValueError('natal_datetime and natal_location required')
    return _compute_chart_bundle_for(nat_dt, nat_loc, nat_tz, house_system_code=house)


def _transit_bundle_from_query(args, natal_meta: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    transit_dt = args.get('transit_datetime')
    if not transit_dt:
        return None
    fallback_meta = natal_meta or {}
    transit_loc = args.get('transit_location') or fallback_meta.get('location')
    transit_tz = args.get('transit_timezone') or fallback_meta.get('timezone')
    house = args.get('house_system_code') or None
    return _compute_chart_bundle_for(transit_dt, transit_loc, transit_tz, house_system_code=house)


def _astrocartography_target_analysis(
    *,
    target_location: str,
    resolved_name: str,
    latitude: float,
    longitude: float,
    natal_meta: Dict[str, Any],
    natal_lines_payload: Dict[str, Any],
    house_system_code: Optional[str],
    goal_id: Optional[str] = None,
    transit_lines_payload: Optional[Dict[str, Any]] = None,
    transit_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_paran_candidates_for_point,
        build_delineation_report,
        build_intersection_workspace,
        build_location_reading,
        build_local_space_workspace,
        crossing_candidates_for_point,
    )
    from astrocartography_goal_engine import (
        evaluate_goal_model,
        extract_relocation_features,
        summarize_relocation_features,
    )
    from astrocartography_goal_models import get_goal_model

    target_payload = {
        'label': resolved_name or target_location,
        'query': target_location,
        'latitude': round(float(latitude), 6),
        'longitude': round(float(longitude), 6),
    }
    natal_reading = build_location_reading(
        natal_lines_payload.get('lines') or [],
        float(latitude),
        float(longitude),
        primary_radius_km=PRIMARY_READING_RADIUS_KM,
        extended_radius_km=EXTENDED_READING_RADIUS_KM,
    )
    natal_crossings = crossing_candidates_for_point(
        natal_lines_payload.get('lines') or [],
        float(latitude),
        float(longitude),
        nearest_rows=natal_reading.get('nearest_lines') or [],
        max_distance_km=EXTENDED_READING_RADIUS_KM,
    )
    natal_intersections = build_intersection_workspace(
        natal_lines_payload.get('lines') or [],
        float(latitude),
        float(longitude),
        nearest_rows=natal_reading.get('nearest_lines') or [],
        max_distance_km=1200.0,
    )
    natal_local_space = build_local_space_workspace(
        str(natal_meta.get('timestamp') or ''),
        float(latitude),
        float(longitude),
        bodies=natal_lines_payload.get('bodies') or None,
    )
    natal_parans = build_paran_candidates_for_point(
        str(natal_meta.get('timestamp') or ''),
        float(latitude),
        float(longitude),
        bodies=natal_lines_payload.get('bodies') or None,
    )

    result: Dict[str, Any] = {
        'target': target_payload,
        'natal': {
            'meta': natal_meta,
            'nearest_lines': natal_reading.get('nearest_lines') or [],
            'reading': natal_reading,
            'crossings': natal_crossings,
            'intersections': natal_intersections,
            'parans': natal_parans,
            'local_space': natal_local_space,
        },
    }

    transit_reading = None
    transit_crossings = None
    transit_intersections = None
    transit_parans = None
    transit_local_space = None
    if transit_lines_payload and transit_meta:
        transit_reading = build_location_reading(
            transit_lines_payload.get('lines') or [],
            float(latitude),
            float(longitude),
            primary_radius_km=PRIMARY_READING_RADIUS_KM,
            extended_radius_km=EXTENDED_READING_RADIUS_KM,
        )
        transit_crossings = crossing_candidates_for_point(
            transit_lines_payload.get('lines') or [],
            float(latitude),
            float(longitude),
            nearest_rows=transit_reading.get('nearest_lines') or [],
            max_distance_km=EXTENDED_READING_RADIUS_KM,
        )
        transit_intersections = build_intersection_workspace(
            transit_lines_payload.get('lines') or [],
            float(latitude),
            float(longitude),
            nearest_rows=transit_reading.get('nearest_lines') or [],
            max_distance_km=1200.0,
        )
        transit_local_space = build_local_space_workspace(
            str(transit_meta.get('timestamp') or ''),
            float(latitude),
            float(longitude),
            bodies=transit_lines_payload.get('bodies') or None,
        )
        transit_parans = build_paran_candidates_for_point(
            str(transit_meta.get('timestamp') or ''),
            float(latitude),
            float(longitude),
            bodies=transit_lines_payload.get('bodies') or None,
        )
        result['transit'] = {
            'meta': transit_meta,
            'nearest_lines': transit_reading.get('nearest_lines') or [],
            'reading': transit_reading,
            'crossings': transit_crossings,
            'intersections': transit_intersections,
            'parans': transit_parans,
            'local_space': transit_local_space,
        }

    relocation_bundle = _compute_chart_bundle_for(
        str(natal_meta.get('timestamp') or ''),
        resolved_name or target_location,
        None,
        house_system_code=house_system_code,
    )
    relocation_features = extract_relocation_features(relocation_bundle.get('chart_data') or {})
    relocation_summary = summarize_relocation_features(relocation_features)
    result['relocation'] = {
        'meta': relocation_bundle.get('meta') or {},
        'summary': relocation_summary,
    }

    goal_eval = None
    if goal_id:
        goal_model = get_goal_model(goal_id)
        goal_eval = evaluate_goal_model(
            goal_id,
            natal_rows=natal_reading.get('nearest_lines') or [],
            natal_crossings=natal_crossings,
            relocation=relocation_features,
            transit_rows=(transit_reading.get('nearest_lines') or []) if transit_reading else None,
            transit_crossings=transit_crossings,
        )
        result['goal'] = {
            'id': goal_model.get('id'),
            'label': goal_model.get('label'),
            'summary': goal_model.get('summary'),
        }
        result['location_score'] = goal_eval

    result['report'] = build_delineation_report(
        target_label=resolved_name or target_location,
        natal_reading=natal_reading,
        natal_intersections=natal_intersections,
        natal_parans=natal_parans,
        natal_local_space=natal_local_space,
        relocation_summary=relocation_summary,
        goal_evaluation=goal_eval,
        transit_reading=transit_reading,
        transit_intersections=transit_intersections,
        transit_parans=transit_parans,
        transit_local_space=transit_local_space,
    )

    return result


@astro_clock_bp.route('/astrocartography/map', methods=['GET'])
@_error_handler
def astrocartography_map():
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_astrocartography_lines,
        build_global_paran_tracks,
    )

    bundle = _natal_bundle_from_query(request.args)
    natal_meta = bundle.get('meta') or {}
    bodies = request.args.getlist('body') or None
    angles = request.args.getlist('angle') or None
    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
    empty_global_parans = {
        'headline': 'Global paran corridors are unavailable in the current runtime.',
        'orb_deg': 1.0,
        'latitude_step_deg': 2,
        'track_count': 0,
        'lead_track': None,
        'tracks': [],
        'degraded': True,
    }

    response: Dict[str, Any] = {
        'natal': natal_meta,
        'filters': {
            'bodies': natal_lines.get('bodies') or [],
            'angles': natal_lines.get('angles') or [],
        },
        'map': {
            'natal_lines': natal_lines.get('lines') or [],
            'global_parans': _safe_astrocartography_optional_payload(
                'natal_global_parans',
                lambda: build_global_paran_tracks(
                    str(natal_meta.get('timestamp') or ''),
                    bodies=natal_lines.get('bodies') or None,
                ),
                empty_global_parans,
            ),
        },
        'defaults': {
            'primary_radius_km': int(PRIMARY_READING_RADIUS_KM),
            'extended_radius_km': int(EXTENDED_READING_RADIUS_KM),
        },
    }

    transit_bundle = _transit_bundle_from_query(request.args, natal_meta=natal_meta)
    if transit_bundle:
        transit_meta = transit_bundle.get('meta') or {}
        transit_lines = build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        response['transit'] = transit_meta
        response['map']['transit_lines'] = transit_lines.get('lines') or []
        response['map']['transit_global_parans'] = _safe_astrocartography_optional_payload(
            'transit_global_parans',
            lambda: build_global_paran_tracks(
                str(transit_meta.get('timestamp') or ''),
                bodies=transit_lines.get('bodies') or None,
            ),
            empty_global_parans,
        )

    return _json_ok(response)


@astro_clock_bp.route('/astrocartography/location', methods=['GET'])
@_error_handler
def astrocartography_location():
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_astrocartography_lines,
    )

    target_location = str(request.args.get('target_location') or '').strip()
    if not target_location:
        raise ValueError('target_location is required')

    lat, lon, resolved_name = safe_geocode(target_location)
    bundle = _natal_bundle_from_query(request.args)
    natal_meta = bundle.get('meta') or {}
    bodies = request.args.getlist('body') or None
    angles = request.args.getlist('angle') or None
    house_system_code = request.args.get('house_system_code') or None
    goal_id = str(request.args.get('goal_id') or '').strip().lower() or None
    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)

    response: Dict[str, Any] = {
        'distance_policy': {
            'primary_radius_km': int(PRIMARY_READING_RADIUS_KM),
            'extended_radius_km': int(EXTENDED_READING_RADIUS_KM),
        },
    }

    transit_bundle = _transit_bundle_from_query(request.args, natal_meta=natal_meta)
    transit_meta = (transit_bundle.get('meta') or {}) if transit_bundle else None
    transit_lines = (
        build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        if transit_meta else None
    )
    response.update(
        _astrocartography_target_analysis(
            target_location=target_location,
            resolved_name=resolved_name or target_location,
            latitude=float(lat),
            longitude=float(lon),
            natal_meta=natal_meta,
            natal_lines_payload=natal_lines,
            house_system_code=house_system_code,
            goal_id=goal_id,
            transit_lines_payload=transit_lines,
            transit_meta=transit_meta,
        )
    )

    return _json_ok(response)


@astro_clock_bp.route('/astrocartography/goals', methods=['GET'])
@_error_handler
def astrocartography_goals():
    from astrocartography_goal_engine import list_goal_model_summaries

    return _json_ok({'goals': list_goal_model_summaries()})


@astro_clock_bp.route('/astrocartography/compare', methods=['GET'])
@_error_handler
def astrocartography_compare():
    from astrocartography_atlas_engine import build_location_score_sort_key
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_astrocartography_lines,
    )

    target_locations = [str(value or '').strip() for value in request.args.getlist('target_location') if str(value or '').strip()]
    if len(target_locations) < 2:
        raise ValueError('At least two target_location values are required')
    if len(target_locations) > 8:
        raise ValueError('A maximum of 8 target_location values is supported')

    bundle = _natal_bundle_from_query(request.args)
    natal_meta = bundle.get('meta') or {}
    bodies = request.args.getlist('body') or None
    angles = request.args.getlist('angle') or None
    house_system_code = request.args.get('house_system_code') or None
    goal_id = str(request.args.get('goal_id') or '').strip().lower() or None

    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
    transit_bundle = _transit_bundle_from_query(request.args, natal_meta=natal_meta)
    transit_meta = (transit_bundle.get('meta') or {}) if transit_bundle else None
    transit_lines = (
        build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        if transit_meta else None
    )

    targets: List[Dict[str, Any]] = []
    for target_location in target_locations:
        lat, lon, resolved_name = safe_geocode(target_location)
        analysis = _astrocartography_target_analysis(
            target_location=target_location,
            resolved_name=resolved_name or target_location,
            latitude=float(lat),
            longitude=float(lon),
            natal_meta=natal_meta,
            natal_lines_payload=natal_lines,
            house_system_code=house_system_code,
            goal_id=goal_id,
            transit_lines_payload=transit_lines,
            transit_meta=transit_meta,
        )
        targets.append(analysis)

    ranking = sorted(
        [
            {
                'label': (item.get('target') or {}).get('label'),
                'query': (item.get('target') or {}).get('query'),
                'score': ((item.get('location_score') or {}).get('score')),
                'raw_score': ((item.get('location_score') or {}).get('raw_score')),
                'top_supports': ((item.get('location_score') or {}).get('top_supports') or [])[:2],
                'top_cautions': ((item.get('location_score') or {}).get('top_cautions') or [])[:2],
            }
            for item in targets
        ],
        key=lambda item: build_location_score_sort_key(
            {
                'raw_score': item.get('raw_score'),
                'score': item.get('score'),
            },
            label=item.get('label') or '',
        ),
    )
    for idx, item in enumerate(ranking, start=1):
        item['rank'] = idx

    response: Dict[str, Any] = {
        'distance_policy': {
            'primary_radius_km': int(PRIMARY_READING_RADIUS_KM),
            'extended_radius_km': int(EXTENDED_READING_RADIUS_KM),
        },
        'targets': targets,
        'ranking': ranking,
    }
    if goal_id and targets:
        response['goal'] = targets[0].get('goal')
    return _json_ok(response)


def _astrocartography_param_list(params: Any, singular_key: str, plural_key: Optional[str] = None) -> List[str]:
    values: List[str] = []
    if hasattr(params, 'getlist'):
        try:
            values = [str(item).strip() for item in (params.getlist(singular_key) or []) if str(item).strip()]
        except Exception:
            values = []
        if values:
            return values
        if plural_key:
            try:
                values = [str(item).strip() for item in (params.getlist(plural_key) or []) if str(item).strip()]
            except Exception:
                values = []
            if values:
                return values

    raw = None
    try:
        raw = params.get(singular_key)
    except Exception:
        raw = None
    if raw is None and plural_key:
        try:
            raw = params.get(plural_key)
        except Exception:
            raw = None

    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).strip()
    return [text] if text else []


class _AtlasSearchCancelled(RuntimeError):
    pass


def _atlas_search_session_is_terminal(session: Optional[Dict[str, Any]]) -> bool:
    if not session:
        return False
    return bool(session.get('ready') or session.get('failed') or session.get('cancelled'))


def _prune_atlas_search_sessions_locked(now: Optional[float] = None) -> None:
    current_time = now if now is not None else perf_counter()
    expired_ids = []
    for session_id, session in list(_atlas_search_sessions.items()):
        if not _atlas_search_session_is_terminal(session):
            continue
        updated_at = float(session.get('updated_at') or session.get('created_at') or current_time)
        if (current_time - updated_at) >= _ATLAS_SEARCH_SESSION_TTL_SECONDS:
            expired_ids.append(session_id)
    for session_id in expired_ids:
        _atlas_search_sessions.pop(session_id, None)

    if len(_atlas_search_sessions) <= _ATLAS_SEARCH_SESSION_MAX:
        return

    removable = []
    for session_id, session in _atlas_search_sessions.items():
        if not _atlas_search_session_is_terminal(session):
            continue
        updated_at = float(session.get('updated_at') or session.get('created_at') or current_time)
        removable.append((updated_at, session_id))
    removable.sort()
    for _, session_id in removable:
        if len(_atlas_search_sessions) <= _ATLAS_SEARCH_SESSION_MAX:
            break
        _atlas_search_sessions.pop(session_id, None)


def _atlas_search_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _atlas_search_lock:
        _prune_atlas_search_sessions_locked()
        return copy.deepcopy(_atlas_search_sessions.get(session_id) or {})


def _atlas_search_cancel_requested(session_id: str) -> bool:
    with _atlas_search_lock:
        _prune_atlas_search_sessions_locked()
        session = _atlas_search_sessions.get(session_id) or {}
        return bool(session.get('cancel_requested'))


def _raise_if_atlas_search_cancelled(session_id: str) -> None:
    if _atlas_search_cancel_requested(session_id):
        raise _AtlasSearchCancelled('Atlas search cancelled')


def _request_atlas_search_cancel(session_id: str) -> Dict[str, Any]:
    with _atlas_search_lock:
        _prune_atlas_search_sessions_locked()
        session = _atlas_search_sessions.get(session_id)
        if session is None:
            return {}
        current_time = perf_counter()
        session.setdefault('session_id', session_id)
        session.setdefault('created_at', current_time)
        session['updated_at'] = current_time
        if not _atlas_search_session_is_terminal(session):
            session.update({
                'cancel_requested': True,
                'stage': 'cancelling',
                'message': 'Cancelling atlas search',
            })
        return copy.deepcopy(session)


def _atlas_search_progress_payload(session_id: str) -> Dict[str, Any]:
    sess = _atlas_search_session_snapshot(session_id)
    cancelled = bool(sess.get('cancelled'))
    failed = bool(sess.get('failed'))

    return {
        'session_id': session_id,
        'ready': bool(sess.get('ready')),
        'failed': failed,
        'cancelled': cancelled,
        'cancel_requested': bool(sess.get('cancel_requested')),
        'percent': max(0.0, min(1.0, float(sess.get('percent') or 0.0))),
        'stage': str(sess.get('stage') or 'pending'),
        'message': str(sess.get('message') or ''),
        'done': int(sess.get('done') or 0),
        'total': int(sess.get('total') or 0),
        'candidate_count': sess.get('candidate_count'),
        'catalog_candidate_count': sess.get('catalog_candidate_count'),
        'live_candidate_count': sess.get('live_candidate_count'),
        'shortlisted_count': sess.get('shortlisted_count'),
        'viable_count': sess.get('viable_count'),
        'error': str(sess.get('error') or '') if (failed or cancelled) else '',
    }


def _update_atlas_search_session(session_id: str, **updates: Any) -> None:
    with _atlas_search_lock:
        _prune_atlas_search_sessions_locked()
        current_time = perf_counter()
        session = _atlas_search_sessions.get(session_id)
        if session is None:
            session = {
                'session_id': session_id,
                'created_at': current_time,
            }
            _atlas_search_sessions[session_id] = session
        session.update(updates)
        session.setdefault('created_at', current_time)
        session['updated_at'] = current_time


def _run_astrocartography_atlas_search(params: Any, *, progress_callback=None, should_continue=None) -> Dict[str, Any]:
    from astrocartography_atlas_engine import describe_goal_search_filters, rank_atlas_cities_for_goal
    from astrocartography_goal_models import get_goal_model
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_astrocartography_lines,
    )

    def _check_should_continue() -> None:
        if should_continue is None:
            return
        should_continue()

    goal_id = str(params.get('goal_id') or '').strip().lower()
    if not goal_id:
        raise ValueError('goal_id is required')

    query_text = str(params.get('query') or '').strip()
    country_code = str(params.get('country_code') or '').strip().upper()
    continent_code = str(params.get('continent_code') or '').strip().upper()
    resolution = str(params.get('resolution') or '').strip().lower() or 'standard'
    try:
        limit = int(params.get('limit') or 8)
    except Exception:
        limit = 8
    limit = max(1, min(limit, 20))

    _check_should_continue()
    if progress_callback is not None:
        progress_callback({
            'stage': 'prepare_chart',
            'percent': 0.02,
            'message': 'Preparing natal chart and filters',
        })

    bundle = _natal_bundle_from_query(params)
    natal_meta = bundle.get('meta') or {}
    selected_bodies = _astrocartography_param_list(params, 'body', 'bodies') or None
    selected_angles = _astrocartography_param_list(params, 'angle', 'angles') or None
    house_system_code = params.get('house_system_code') or None
    filter_meta = describe_goal_search_filters(
        goal_id,
        selected_bodies=selected_bodies,
        selected_angles=selected_angles,
    )
    relevant_bodies = filter_meta.get('bodies') or []
    relevant_angles = filter_meta.get('angles') or []
    if not filter_meta.get('goal_has_signature'):
        raise ValueError('Selected goal model is not configured for atlas-search line filtering yet')
    if filter_meta.get('excluded_by_filters'):
        raise ValueError("Current body/angle filters exclude the selected goal model's atlas signature")

    _check_should_continue()
    if progress_callback is not None:
        progress_callback({
            'stage': 'prepare_chart',
            'percent': 0.08,
            'message': 'Building natal astrocartography lines',
        })

    natal_lines = build_astrocartography_lines(
        str(natal_meta.get('timestamp') or ''),
        bodies=relevant_bodies,
        angles=relevant_angles,
    )

    _check_should_continue()
    transit_bundle = _transit_bundle_from_query(params, natal_meta=natal_meta)
    transit_meta = (transit_bundle.get('meta') or {}) if transit_bundle else None
    transit_lines = None
    if transit_meta:
        _check_should_continue()
        if progress_callback is not None:
            progress_callback({
                'stage': 'prepare_chart',
                'percent': 0.12,
                'message': 'Building transit overlay lines',
            })
        transit_lines = build_astrocartography_lines(
            str(transit_meta.get('timestamp') or ''),
            bodies=relevant_bodies,
            angles=relevant_angles,
        )

    def _resolve_relocation_bundle(item: Dict[str, Any]) -> Dict[str, Any]:
        target = item.get('target') or {}
        atlas_city = item.get('atlas_city') or {}
        return _compute_chart_bundle_for(
            str(natal_meta.get('timestamp') or ''),
            str(target.get('query') or target.get('label') or ''),
            atlas_city.get('timezone') or None,
            house_system_code=house_system_code,
        )

    def _atlas_progress(payload: Dict[str, Any]) -> None:
        _check_should_continue()
        if progress_callback is None:
            return
        inner = max(0.0, min(1.0, float(payload.get('percent') or 0.0)))
        forwarded = dict(payload)
        forwarded['percent'] = 0.15 + (inner * 0.8)
        progress_callback(forwarded)

    _check_should_continue()
    search_result = rank_atlas_cities_for_goal(
        goal_id=goal_id,
        natal_lines=natal_lines.get('lines') or [],
        transit_lines=(transit_lines.get('lines') or []) if transit_lines else None,
        query=query_text or None,
        country_code=country_code or None,
        continent_code=continent_code or None,
        resolution=resolution,
        limit=limit,
        relocation_bundle_resolver=_resolve_relocation_bundle,
        progress_callback=_atlas_progress,
        should_continue=_check_should_continue,
    )

    _check_should_continue()
    if progress_callback is not None:
        progress_callback({
            'stage': 'finalize_response',
            'percent': 0.98,
            'message': 'Preparing final atlas response',
            'candidate_count': search_result.get('candidate_count'),
            'shortlisted_count': search_result.get('shortlisted_count'),
            'viable_count': search_result.get('viable_count'),
        })

    goal_model = get_goal_model(goal_id)
    response: Dict[str, Any] = {
        'goal': {
            'id': goal_model.get('id'),
            'label': goal_model.get('label'),
            'summary': goal_model.get('summary'),
        },
        'natal': natal_meta,
        'filters': {
            'bodies': relevant_bodies,
            'angles': relevant_angles,
        },
        'distance_policy': {
            'primary_radius_km': int(PRIMARY_READING_RADIUS_KM),
            'extended_radius_km': int(EXTENDED_READING_RADIUS_KM),
        },
        'atlas': {
            'query': search_result.get('query') or {},
            'resolution': search_result.get('resolution') or {},
            'catalog_candidate_count': search_result.get('catalog_candidate_count'),
            'live_candidate_count': search_result.get('live_candidate_count'),
            'used_live_augmentation': search_result.get('used_live_augmentation'),
            'candidate_count': search_result.get('candidate_count'),
            'shortlisted_count': search_result.get('shortlisted_count'),
            'viable_count': search_result.get('viable_count'),
            'signal_floor_raw_score': search_result.get('signal_floor_raw_score'),
        },
        'results': search_result.get('results') or [],
        'ranking': search_result.get('ranking') or [],
    }
    if transit_meta:
        response['transit'] = transit_meta
    _check_should_continue()
    return response


@astro_clock_bp.route('/astrocartography/atlas-search', methods=['GET'])
@_error_handler
def astrocartography_atlas_search():
    return _json_ok(_run_astrocartography_atlas_search(request.args))


@astro_clock_bp.route('/astrocartography/atlas-search/start', methods=['POST'])
@_error_handler
def astrocartography_atlas_search_start():
    body = request.get_json(force=True, silent=True) or {}
    session_id = str(uuid4())
    _update_atlas_search_session(
        session_id,
        ready=False,
        failed=False,
        cancelled=False,
        cancel_requested=False,
        percent=0.0,
        stage='queued',
        message='Atlas search queued',
        done=0,
        total=0,
    )

    def _worker() -> None:
        try:
            _raise_if_atlas_search_cancelled(session_id)
            _update_atlas_search_session(
                session_id,
                stage='prepare_chart',
                message='Preparing natal chart and filters',
                percent=0.02,
            )
            result = _run_astrocartography_atlas_search(
                body,
                progress_callback=lambda payload: _update_atlas_search_session(session_id, **payload),
                should_continue=lambda: _raise_if_atlas_search_cancelled(session_id),
            )
            _raise_if_atlas_search_cancelled(session_id)
            _update_atlas_search_session(
                session_id,
                ready=True,
                failed=False,
                cancelled=False,
                cancel_requested=False,
                percent=1.0,
                stage='ready',
                message='Atlas search complete',
                result=result,
            )
        except _AtlasSearchCancelled:
            _update_atlas_search_session(
                session_id,
                ready=True,
                failed=False,
                cancelled=True,
                cancel_requested=False,
                percent=1.0,
                stage='cancelled',
                message='Atlas search cancelled',
                error='Atlas search cancelled',
                result=None,
            )
        except Exception as exc:
            logger.exception('Astrocartography atlas search session failed: %s', session_id)
            _update_atlas_search_session(
                session_id,
                ready=False,
                failed=True,
                cancelled=False,
                cancel_requested=False,
                stage='failed',
                message='Atlas search failed',
                error=str(exc),
            )

    thread = threading.Thread(target=_worker, name=f'astrocartography-atlas-{session_id[:8]}', daemon=True)
    thread.start()
    return _json_ok({'session_id': session_id, 'progress': _atlas_search_progress_payload(session_id)})


@astro_clock_bp.route('/astrocartography/atlas-search/cancel', methods=['POST'])
@_error_handler
def astrocartography_atlas_search_cancel():
    body = request.get_json(force=True, silent=True) or {}
    session_id = str(body.get('session_id') or body.get('sessionId') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _request_atlas_search_cancel(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Atlas search session not found'}), 404
    return _json_ok({'session_id': session_id, 'progress': _atlas_search_progress_payload(session_id)})


@astro_clock_bp.route('/astrocartography/atlas-search/progress', methods=['GET'])
@_error_handler
def astrocartography_atlas_search_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    return _json_ok(_atlas_search_progress_payload(session_id))


@astro_clock_bp.route('/astrocartography/atlas-search/result', methods=['GET'])
@_error_handler
def astrocartography_atlas_search_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _atlas_search_session_snapshot(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Atlas search session not found'}), 404
    payload: Dict[str, Any] = {
        'session_id': session_id,
        'ready': bool(session.get('ready')),
        'failed': bool(session.get('failed')),
        'cancelled': bool(session.get('cancelled')),
        'progress': _atlas_search_progress_payload(session_id),
    }
    if session.get('failed') or session.get('cancelled'):
        payload['error'] = str(session.get('error') or ('Atlas search cancelled' if session.get('cancelled') else 'Atlas search failed'))
    if session.get('ready') and session.get('result') is not None:
        payload['result'] = session.get('result')
    return _json_ok(payload)


def _mundane_scan_progress_payload(session_id: str) -> Dict[str, Any]:
    sess = _mundane_scan_session_snapshot(session_id)

    counts = sess.get('counts') or {}
    return {
        'session_id': session_id,
        'ready': bool(sess.get('ready')),
        'failed': bool(sess.get('failed')),
        'percent': max(0.0, min(1.0, float(sess.get('percent') or 0.0))),
        'stage': str(sess.get('stage') or 'pending'),
        'message': str(sess.get('message') or ''),
        'done': int(sess.get('done') or 0),
        'total': int(sess.get('total') or 0),
        'candidate_count': sess.get('candidate_count'),
        'time_slices': sess.get('time_slices'),
        'kept_cells': sess.get('kept_cells'),
        'returned': sess.get('returned'),
        'failures': sess.get('failures') if sess.get('ready') or sess.get('failed') else counts.get('failures'),
        'error': str(sess.get('error') or '') if sess.get('failed') else '',
    }


def _update_mundane_scan_session(session_id: str, **updates: Any) -> None:
    with _mundane_scan_lock:
        session = _mundane_scan_sessions.get(session_id)
        if session is None:
            session = {'session_id': session_id}
            _mundane_scan_sessions[session_id] = session
        session.update(updates)


def _mundane_scan_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _mundane_scan_lock:
        session = _mundane_scan_sessions.get(session_id) or {}
        serializable = {
            key: value
            for key, value in session.items()
            if key != 'thread'
        }
    return copy.deepcopy(serializable)


def _weather_scan_progress_payload(session_id: str) -> Dict[str, Any]:
    sess = _weather_scan_session_snapshot(session_id)

    counts = sess.get('counts') or {}
    return {
        'session_id': session_id,
        'ready': bool(sess.get('ready')),
        'failed': bool(sess.get('failed')),
        'percent': max(0.0, min(1.0, float(sess.get('percent') or 0.0))),
        'stage': str(sess.get('stage') or 'pending'),
        'message': str(sess.get('message') or ''),
        'done': int(sess.get('done') or 0),
        'total': int(sess.get('total') or 0),
        'counts': counts,
        'candidate_count': sess.get('candidate_count', counts.get('candidate_count')),
        'time_slices': sess.get('time_slices', counts.get('time_slices')),
        'evaluated': sess.get('evaluated', counts.get('evaluated')),
        'returned': sess.get('returned', counts.get('returned')),
    }


def _update_weather_scan_session(session_id: str, **updates: Any) -> None:
    with _weather_scan_lock:
        session = _weather_scan_sessions.get(session_id)
        if session is None:
            session = {'session_id': session_id}
            _weather_scan_sessions[session_id] = session
        session.update(updates)


def _weather_scan_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _weather_scan_lock:
        session = _weather_scan_sessions.get(session_id) or {}
        serializable = {
            key: value
            for key, value in session.items()
            if key != 'thread'
        }
    return copy.deepcopy(serializable)


@astro_clock_bp.route('/mundane/chart-types', methods=['GET'])
@_error_handler
def mundane_chart_types():
    from mundane_service import get_runtime_catalog

    payload = get_runtime_catalog()
    payload['research_mode'] = True
    payload['runtime_scope'] = 'computed_chart_context'
    return _json_ok(payload)


@astro_clock_bp.route('/mundane/context/resolve', methods=['GET'])
@_error_handler
def mundane_context_resolve():
    from mundane_models import ActiveClockContext
    from mundane_service import build_context_request, resolve_context

    try:
        request_model = build_context_request(request.args, require_domain=False)
        active_clock = ActiveClockContext(**_mundane_active_clock_context())
        resolved = resolve_context(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_mundane_bundle_resolver,
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    return _json_ok({
        'context': resolved.to_dict(),
        'runtime_scope': 'computed_chart_context',
    })


@astro_clock_bp.route('/mundane/analyze', methods=['GET'])
@_error_handler
def mundane_analyze():
    from mundane_models import ActiveClockContext
    from mundane_service import analyze_context, build_context_request, resolve_context

    try:
        request_model = build_context_request(request.args, require_domain=True)
        active_clock = ActiveClockContext(**_mundane_active_clock_context())
        resolved = resolve_context(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_mundane_bundle_resolver,
        )
        analysis = analyze_context(resolved)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    payload = analysis.to_dict()
    payload['runtime_scope'] = 'computed_chart_context'
    return _json_ok(payload)


@astro_clock_bp.route('/weather/catalog', methods=['GET'])
@_error_handler
def weather_catalog():
    from weather_service import get_runtime_catalog

    payload = get_runtime_catalog()
    payload['research_mode'] = True
    payload['runtime_scope'] = 'seed_weather_runtime'
    return _json_ok(payload)


@astro_clock_bp.route('/weather/context/resolve', methods=['GET'])
@_error_handler
def weather_context_resolve():
    from mundane_models import ActiveClockContext
    from weather_service import build_weather_request, resolve_weather_context

    try:
        request_model = build_weather_request(request.args)
        active_clock = ActiveClockContext(**_weather_active_clock_context())
        resolved = resolve_weather_context(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_weather_bundle_resolver,
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    return _json_ok({
        'context': resolved.to_dict(),
        'runtime_scope': 'seed_weather_runtime',
    })


@astro_clock_bp.route('/weather/analyze', methods=['GET'])
@_error_handler
def weather_analyze():
    from mundane_models import ActiveClockContext
    from weather_service import analyze_weather_context, build_weather_request, resolve_weather_context

    try:
        request_model = build_weather_request(request.args)
        active_clock = ActiveClockContext(**_weather_active_clock_context())
        resolved = resolve_weather_context(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_weather_bundle_resolver,
        )
        analysis = analyze_weather_context(resolved)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    payload = analysis.to_dict()
    payload['runtime_scope'] = 'seed_weather_runtime'
    return _json_ok(payload)


@astro_clock_bp.route('/weather/scan/catalog', methods=['GET'])
@_error_handler
def weather_scan_catalog():
    from weather_scan_service import get_weather_scan_catalog

    payload = get_weather_scan_catalog()
    payload['research_mode'] = True
    payload['runtime_scope'] = 'seed_weather_scan'
    return _json_ok(payload)


@astro_clock_bp.route('/weather/scan/run', methods=['GET'])
@_error_handler
def weather_scan_run():
    from mundane_models import ActiveClockContext
    from weather_scan_service import build_weather_scan_request, run_weather_scan

    try:
        request_model = build_weather_scan_request(request.args)
        active_clock = ActiveClockContext(**_weather_active_clock_context())
        result = run_weather_scan(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_weather_bundle_resolver,
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    return _json_ok(result)


@astro_clock_bp.route('/weather/scan/start', methods=['POST'])
@_error_handler
def weather_scan_start():
    from mundane_models import ActiveClockContext
    from weather_scan_service import build_weather_scan_request, run_weather_scan

    body = request.get_json(force=True, silent=True) or {}
    try:
        request_model = build_weather_scan_request(body)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    session_id = str(uuid4())
    active_clock_payload = _weather_active_clock_context()

    _update_weather_scan_session(
        session_id,
        ready=False,
        failed=False,
        percent=0.0,
        stage='queued',
        message='Weather scan queued',
        done=0,
        total=0,
    )

    def _worker() -> None:
        try:
            active_clock = ActiveClockContext(**active_clock_payload)

            def _progress(payload: Dict[str, Any]) -> None:
                _update_weather_scan_session(session_id, **payload)

            result = run_weather_scan(
                request_model,
                active_clock=active_clock,
                bundle_resolver=_weather_bundle_resolver,
                progress_callback=_progress,
            )
            counts = result.get('counts') or {}
            _update_weather_scan_session(
                session_id,
                ready=True,
                failed=False,
                percent=1.0,
                stage='complete',
                message='Weather scan complete',
                result=result,
                counts=counts,
                candidate_count=counts.get('candidate_count'),
                time_slices=counts.get('time_slices'),
                evaluated=counts.get('evaluated'),
                returned=counts.get('returned'),
                done=counts.get('evaluated'),
                total=counts.get('evaluated'),
            )
        except Exception as exc:
            _update_weather_scan_session(
                session_id,
                ready=False,
                failed=True,
                percent=1.0,
                stage='failed',
                message='Weather scan failed',
                error=str(exc),
            )

    thread = threading.Thread(target=_worker, name=f'weather-scan-{session_id[:8]}', daemon=True)
    with _weather_scan_lock:
        _weather_scan_sessions[session_id]['thread'] = thread
    thread.start()
    return _json_ok({'session_id': session_id, 'progress': _weather_scan_progress_payload(session_id)})


@astro_clock_bp.route('/weather/scan/progress', methods=['GET'])
@_error_handler
def weather_scan_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    return _json_ok(_weather_scan_progress_payload(session_id))


@astro_clock_bp.route('/weather/scan/result', methods=['GET'])
@_error_handler
def weather_scan_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _weather_scan_session_snapshot(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Weather scan session not found'}), 404
    payload: Dict[str, Any] = {
        'session_id': session_id,
        'ready': bool(session.get('ready')),
        'failed': bool(session.get('failed')),
        'progress': _weather_scan_progress_payload(session_id),
    }
    if session.get('failed'):
        payload['error'] = str(session.get('error') or 'Weather scan failed')
    if session.get('ready') and session.get('result') is not None:
        payload['result'] = session.get('result')
    return _json_ok(payload)


@astro_clock_bp.route('/mundane/scan/regions', methods=['GET'])
@_error_handler
def mundane_scan_regions():
    from mundane_scan_service import get_scan_runtime_catalog
    from mundane_service import get_runtime_catalog

    payload = get_scan_runtime_catalog()
    runtime_catalog = get_runtime_catalog()
    payload['chart_types'] = [
        row for row in runtime_catalog.get('chart_types') or []
        if str((row or {}).get('id') or '').strip().lower() in set(payload.get('supported_chart_types') or [])
    ]
    payload['domains'] = runtime_catalog.get('domains') or []
    payload['context_types'] = runtime_catalog.get('context_types') or []
    payload['polities'] = runtime_catalog.get('polities') or []
    payload['research_mode'] = True
    payload['runtime_scope'] = 'computed_chart_context'
    return _json_ok(payload)


@astro_clock_bp.route('/mundane/scan/run', methods=['GET'])
@_error_handler
def mundane_scan_run():
    from mundane_models import ActiveClockContext
    from mundane_scan_service import build_scan_request, run_scan

    try:
        request_model = build_scan_request(request.args)
        if str(getattr(request_model, "scan_mode", "") or "").strip().lower() == "long_range_async_scan":
            raise ValueError("long_range_async_scan is async-only; use /api/astro-clock/mundane/scan/start")
        include_series = str(request.args.get('include_series') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
        active_clock = ActiveClockContext(**_mundane_active_clock_context())
        result = run_scan(
            request_model,
            active_clock=active_clock,
            bundle_resolver=_mundane_bundle_resolver,
            include_series=include_series,
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    return _json_ok(result)


@astro_clock_bp.route('/mundane/scan/start', methods=['POST'])
@_error_handler
def mundane_scan_start():
    from mundane_models import ActiveClockContext
    from mundane_scan_service import build_scan_request, run_scan

    body = request.get_json(force=True, silent=True) or {}
    try:
        request_model = build_scan_request(body)
        include_series = str(body.get('include_series') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    session_id = str(uuid4())
    active_clock_payload = _mundane_active_clock_context()

    _update_mundane_scan_session(
        session_id,
        ready=False,
        failed=False,
        percent=0.0,
        stage='queued',
        message='Mundane scan queued',
        done=0,
        total=0,
    )

    def _worker() -> None:
        try:
            active_clock = ActiveClockContext(**active_clock_payload)

            def _progress(payload: Dict[str, Any]) -> None:
                _update_mundane_scan_session(session_id, **payload)

            result = run_scan(
                request_model,
                active_clock=active_clock,
                bundle_resolver=_mundane_bundle_resolver,
                progress_callback=_progress,
                include_series=include_series,
            )
            counts = result.get('counts') or {}
            _update_mundane_scan_session(
                session_id,
                ready=True,
                failed=False,
                percent=1.0,
                stage='complete',
                message='Mundane scan complete',
                result=result,
                counts=counts,
                candidate_count=counts.get('candidate_locations'),
                time_slices=counts.get('time_slices'),
                kept_cells=counts.get('kept_cells'),
                returned=counts.get('returned'),
                failures=counts.get('failures'),
            )
        except Exception as exc:
            _update_mundane_scan_session(
                session_id,
                ready=False,
                failed=True,
                percent=1.0,
                stage='failed',
                message='Mundane scan failed',
                error=str(exc),
            )

    thread = threading.Thread(target=_worker, name=f'mundane-scan-{session_id[:8]}', daemon=True)
    with _mundane_scan_lock:
        _mundane_scan_sessions[session_id]['thread'] = thread
    thread.start()
    return _json_ok({'session_id': session_id, 'progress': _mundane_scan_progress_payload(session_id)})


@astro_clock_bp.route('/mundane/scan/progress', methods=['GET'])
@_error_handler
def mundane_scan_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    return _json_ok(_mundane_scan_progress_payload(session_id))


@astro_clock_bp.route('/mundane/scan/result', methods=['GET'])
@_error_handler
def mundane_scan_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _mundane_scan_session_snapshot(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Mundane scan session not found'}), 404
    payload: Dict[str, Any] = {
        'session_id': session_id,
        'ready': bool(session.get('ready')),
        'failed': bool(session.get('failed')),
        'progress': _mundane_scan_progress_payload(session_id),
    }
    if session.get('failed'):
        payload['error'] = str(session.get('error') or 'Mundane scan failed')
    if session.get('ready') and session.get('result') is not None:
        payload['result'] = session.get('result')
    return _json_ok(payload)


def _synastry_bundle_from_snap_id(snap_id: str, house_system_code: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    snap = _snaps().get(snap_id)
    if not snap:
        raise ValueError('Synastry snap not found')
    dashboard = snap.get('dashboard') if isinstance(snap.get('dashboard'), dict) else {}
    dt = snap.get('effective_datetime') or dashboard.get('timestamp')
    loc = snap.get('location') or dashboard.get('location')
    saved_chart = _synastry_chart_snapshot_from_dashboard(dashboard)
    saved_chart.update(_synastry_chart_snapshot_from_chart_data(snap.get('chart_snapshot')))

    if _has_synastry_chart_snapshot(saved_chart):
        bundle = {
            'chart_result': {},
            'chart_data': saved_chart,
            'meta': {
                'timestamp': dashboard.get('timestamp') or dt,
                'location': dashboard.get('location') or loc,
                'timezone': dashboard.get('timezone') or snap.get('timezone'),
            },
            'raw_chart': None,
        }
    else:
        if not dt or not loc:
            raise ValueError('Synastry snap is missing datetime or location')
        bundle = _compute_chart_bundle_for(dt, loc, dashboard.get('timezone') or None, house_system_code=house_system_code)
    chart_meta = {
        'id': snap.get('id'),
        'label': snap.get('label') or 'Snapshot',
        'effective_datetime': dt,
        'location': loc,
        'timezone': (bundle.get('meta') or {}).get('timezone'),
        'profile_hint': snap.get('profile_hint') or (snap.get('summary') or {}).get('profile_hint'),
    }
    bundle.setdefault('meta', {})
    if chart_meta.get('profile_hint'):
        bundle['meta']['profile_hint'] = chart_meta.get('profile_hint')
    return bundle, chart_meta


@astro_clock_bp.route('/synastry', methods=['GET'])
@_error_handler
def synastry_compute():
    """Compute a snap-to-snap synastry report.

    Required query params:
      snap_a_id
      snap_b_id
    Optional:
      engine_id
      profile_a
      profile_b
      house_system_code
      include_modern
      include_nodes
      include_chiron
      orb_profile
    """
    from synastry_multi_engine import build_synastry_engine_report

    snap_a_id = str(request.args.get('snap_a_id') or '').strip()
    snap_b_id = str(request.args.get('snap_b_id') or '').strip()
    engine_id = str(request.args.get('engine_id') or 'memo').strip().lower()
    profile_a = str(request.args.get('profile_a') or 'blended').strip().lower()
    profile_b = str(request.args.get('profile_b') or 'blended').strip().lower()
    house_system_code = request.args.get('house_system_code') or None
    include_modern = (request.args.get('include_modern', '1').lower() in {'1', 'true', 'yes', 'on'})
    include_nodes = (request.args.get('include_nodes', '1').lower() in {'1', 'true', 'yes', 'on'})
    include_chiron = (request.args.get('include_chiron', '0').lower() in {'1', 'true', 'yes', 'on'})
    orb_profile = str(request.args.get('orb_profile') or 'balanced').strip().lower()
    if not snap_a_id or not snap_b_id:
        raise ValueError('snap_a_id and snap_b_id are required')
    if snap_a_id == snap_b_id:
        raise ValueError('Select two different snaps for synastry')

    with _astro_perf_span(
        'route.synastry',
        engine_id=engine_id,
        include_modern=include_modern,
        include_nodes=include_nodes,
        include_chiron=include_chiron,
        orb_profile=orb_profile,
    ):
        with _astro_perf_span('route.synastry.load_bundle_a'):
            bundle_a, chart_a = _synastry_bundle_from_snap_id(snap_a_id, house_system_code=house_system_code)
        with _astro_perf_span('route.synastry.load_bundle_b'):
            bundle_b, chart_b = _synastry_bundle_from_snap_id(snap_b_id, house_system_code=house_system_code)
        with _astro_perf_span('route.synastry.point_capability'):
            point_capability_a = _synastry_point_capability(bundle_a.get('meta') or {})
            point_capability_b = _synastry_point_capability(bundle_b.get('meta') or {})
        with _astro_perf_span('route.synastry.extend_chart_data'):
            bundle_a['chart_data'] = _extend_chart_data_for_synastry(
                bundle_a.get('chart_data') or {},
                bundle_a.get('meta') or {},
                include_modern=bool(include_modern and point_capability_a.get('modern_supported')),
                include_chiron=bool(include_chiron and point_capability_a.get('chiron_supported')),
            )
            bundle_b['chart_data'] = _extend_chart_data_for_synastry(
                bundle_b.get('chart_data') or {},
                bundle_b.get('meta') or {},
                include_modern=bool(include_modern and point_capability_b.get('modern_supported')),
                include_chiron=bool(include_chiron and point_capability_b.get('chiron_supported')),
            )

        with _astro_perf_span('route.synastry.build_report'):
            report = build_synastry_engine_report(
                bundle_a,
                bundle_b,
                chart_a,
                chart_b,
                options={
                    'include_modern': include_modern,
                    'include_nodes': include_nodes,
                    'include_chiron': include_chiron,
                    'orb_profile': orb_profile,
                },
                engine_id=engine_id,
                profile_a=profile_a,
                profile_b=profile_b,
            )
    report.setdefault('governance', {})
    report['governance']['point_capability'] = {
        'modern_supported': bool(point_capability_a.get('modern_supported') and point_capability_b.get('modern_supported')),
        'chiron_supported': bool(point_capability_a.get('chiron_supported') and point_capability_b.get('chiron_supported')),
    }
    return _json_ok(report)


@astro_clock_bp.route('/traits/profile', methods=['GET'])
@_error_handler
def traits_profile():
    """Return a trait profile built from current chart metrics and house influences.

    Query params:
      special_degree: repeated tokens such as "25 Leo" to include in metrics
    """
    with _astro_perf_span('route.traits_profile'):
        eng = _engine_instance()
        data, _active_settings = _data_for_request_clock_context(eng)
        with _astro_perf_span('route.traits_profile.compact_dashboard'):
            rt = _compact_dashboard(data)
            cd = _extract_chart_data_from_result(data.chart_result if isinstance(data.chart_result, dict) else {})
        try:
            special_degrees = _normalize_special_degree_tokens(request.args.getlist('special_degree'))
        except Exception:
            special_degrees = []
        with _astro_perf_span('route.traits_profile.metrics'):
            try:
                metrics_chart_data = cd
                arabic_parts = compute_arabic_parts(cd) if isinstance(cd, dict) else {}
                if isinstance(cd, dict) and arabic_parts:
                    metrics_chart_data = dict(cd)
                    metrics_chart_data['arabic_parts'] = arabic_parts
                metrics = compute_metrics(metrics_chart_data, timestamp_iso=rt.get('timestamp'), special_degrees=special_degrees)
            except Exception:
                metrics = {}
        with _astro_perf_span('route.traits_profile.house_influences'):
            try:
                from house_influence import compute_house_influences
                house_infl = compute_house_influences(cd, metrics)
            except Exception:
                house_infl = {'houses': []}

        # Compute sect (for traits) and attach light sect summary onto metrics (optional)
        try:
            sect_info = compute_sect_info(cd)
        except Exception:
            sect_info = None
        try:
            if isinstance(metrics, dict) and sect_info:
                metrics.setdefault('sect', sect_info)
        except Exception:
            pass

        # Build per-planet area scores from house influence to support Morin-style determinations in traits
        # Shape: { planet: { area_label: normalized_score_0_1 } }
        with _astro_perf_span('route.traits_profile.planet_area_scores'):
            try:
                try:
                    from determinations import _house_domain_map as _hm
                    house_to_area = _hm()
                except Exception:
                    house_to_area = {1:'life',2:'wealth',3:'short_travel',4:'home',5:'children',6:'health',7:'relationships',8:'death',9:'belief',10:'honors',11:'friends',12:'secrets'}
                raw: Dict[str, Dict[str, float]] = {}
                for hrow in (house_infl or {}).get('houses', []) or []:
                    try:
                        hnum = int(hrow.get('house'))
                    except Exception:
                        continue
                    area = house_to_area.get(hnum)
                    if not area:
                        continue
                    for inf in (hrow.get('influences') or []):
                        try:
                            p = str(inf.get('planet') or '')
                            if not p:
                                continue
                            val = float(inf.get('value') or 0.0)
                            if val == 0.0:
                                continue
                            raw.setdefault(p, {})[area] = raw.get(p, {}).get(area, 0.0) + val
                        except Exception:
                            continue
                norm: Dict[str, Dict[str, float]] = {}
                for p, amap in raw.items():
                    try:
                        mx = max(abs(v) for v in amap.values()) if amap else 0.0
                        if mx <= 0:
                            continue
                        norm[p] = {k: round(v / mx, 4) for k, v in amap.items()}
                    except Exception:
                        continue
                if isinstance(metrics, dict):
                    metrics.setdefault('planet_area_scores', norm)
            except Exception:
                pass

        with _astro_perf_span('route.traits_profile.evaluate'):
            try:
                engine = _traits_engine_instance()
                profile = engine.evaluate(metrics)
            except Exception:
                profile = {'summary': None, 'top_traits': [], 'traits': [], 'guidance': []}

        with _astro_perf_span('route.traits_profile.chart_snapshot'):
            chart_snapshot = _build_traits_chart_snapshot(data, rt, cd, special_degrees)

    return _json_ok({
        'summary': profile.get('summary'),
        'special_degrees': special_degrees,
        'sect': sect_info,
        'receptions': chart_snapshot.get('receptions'),
        'morin_patterns': chart_snapshot.get('morin_patterns'),
        'house_influences': house_infl,
        'top_traits': profile.get('top_traits') or [],
        'summary_traits': profile.get('summary_traits') or [],
        'top_traits_by_polarity': profile.get('top_traits_by_polarity') or {},
        'traits': profile.get('traits') or [],
        'guidance': profile.get('guidance') or [],
        'trait_enrichment_meta': profile.get('trait_enrichment_meta') or {},
        'chart_snapshot': chart_snapshot,
    })


@astro_clock_bp.route('/determinations', methods=['GET'])
@_error_handler
def determinations_endpoint():
    """Return Determination objects (Spec Step 1) for the current or ad-hoc natal chart.

    Accepts same natal context as /transits: either a saved snap via `natal_snap_id`
    or explicit `natal_datetime`, `natal_location`, optional `natal_timezone`, and `house_system_code`.
    Optional: include_modern=1 to include modern planets.
    """
    from determinations import compute_determinations
    natal_cd, natal_meta = _natal_from_query(request.args)
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    # Compute
    out = compute_determinations(natal_cd, include_modern=include_modern)
    return _json_ok({'natal': natal_meta, **out})


@astro_clock_bp.route('/transits', methods=['GET'])
@_error_handler
def transits_compute():
    """Compute Morin-style transits for a single timestamp.

    Accepts natal context via snap or natal_* params. Optional toggles mirror frontend.
    """
    from transits_morin import compute_morin_transits_to_natal
    # Resolve natal chart_data
    natal_cd, natal_meta = _natal_from_query(request.args)
    # Transit timestamp: explicit or current engine time
    ts = request.args.get('transit_datetime')
    if not ts:
        ts = datetime.now(timezone.utc).isoformat()
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    hits = compute_morin_transits_to_natal(
        natal_cd,
        ts,
        dt_hours=0.5,
        include_modern=include_modern,
        natal_include_modern=natal_include_modern,
        include_cusps=include_cusps,
        include_antiscia=include_antiscia,
        include_lots=include_lots,
        focus_houses=focus_houses or None,
        focus_planets=focus_planets or None,
        sensitive_houses=sensitive_houses or None,
        sensitive_planets=sensitive_planets or None,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
    )
    revolution_context: Dict[str, Any] = {}
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}
    target_dt = _parse_iso_datetime(ts)
    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        [target_dt.year] if target_dt is not None else [],
        route_label='transits/exact',
    )
    hits = _retry_enrich_transit_hits(
        natal_cd,
        hits,
        ts,
        pd_windows=pd_windows,
        sig_beta=sig_beta,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
        context_out=revolution_context,
        route_label='transits/exact',
    )
    predictions = _predictions_from_hits(hits or [], ts)
    return _json_ok({
        'natal': natal_meta,
        'transit_timestamp': ts,
        'transits': hits,
        'predictions': predictions,
        'revolutions': revolution_context,
    })


@astro_clock_bp.route('/transits/window', methods=['GET'])
@_error_handler
def transits_window():
    """Scan a window and return time-series of top Morin transit hits.

    Returns { series: [...], peaks: [...], context_window: {start,end}, natal: {...} }
    """
    from transits_morin import scan_morin_transits_window
    natal_cd, natal_meta = _natal_from_query(request.args)
    start = request.args.get('start')
    end = request.args.get('end')
    # Fallback to center + range_hours
    if not (start and end):
        center = request.args.get('center')
        rng = float(request.args.get('range_hours', '12') or 12)
        if center:
            try:
                from datetime import timedelta
                dt = datetime.fromisoformat(center.replace('Z', '+00:00'))
                a = (dt - timedelta(hours=rng/2)).isoformat()
                b = (dt + timedelta(hours=rng/2)).isoformat()
                start, end = a, b
            except Exception:
                pass
    if not (start and end):
        return jsonify({'success': False, 'error': 'start/end or center/range_hours required'}), 400
    step = int(request.args.get('step_minutes', '60') or 60)
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    # Filters
    flt_transiting = request.args.getlist('transiting') or None
    flt_natal = request.args.getlist('natal') or None
    flt_aspects = request.args.getlist('aspect') or None

    # Optional context filters for PD/SA/Progressions
    pd_start = request.args.get('pd_start')
    pd_end = request.args.get('pd_end')
    sa_start = request.args.get('sa_start')
    sa_end = request.args.get('sa_end')
    prog_start = request.args.get('prog_start')
    prog_end = request.args.get('prog_end')

    # A/B toggle: ?sig_beta=0/1 to switch significance formula
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        [dt.year for dt in (start_dt, end_dt) if dt is not None],
        route_label='transits/window',
    )

    series = scan_morin_transits_window(
        natal_cd,
        start,
        end,
        step_minutes=step,
        prediction_n_per_step=_TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE,
        include_modern=include_modern,
        natal_include_modern=natal_include_modern,
        include_cusps=include_cusps,
        include_antiscia=include_antiscia,
        include_lots=include_lots,
        focus_houses=focus_houses or None,
        focus_planets=focus_planets or None,
        sensitive_houses=sensitive_houses or None,
        sensitive_planets=sensitive_planets or None,
        flt_transiting=flt_transiting,
        flt_natal=flt_natal,
        flt_aspects=flt_aspects,
        pd_windows=pd_windows,
        use_new_significance=sig_beta,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
    )
    # Apply context filtering if any context window provided
    try:
        from datetime import datetime as _dt
        ctx_ranges = []
        def _norm_iso(x):
            return str(x).replace('Z','+00:00') if x else None
        def _to_dt(x):
            try:
                return _dt.fromisoformat(_norm_iso(x)) if x else None
            except Exception:
                return None
        for a,b in ((pd_start, pd_end), (sa_start, sa_end), (prog_start, prog_end)):
            A = _to_dt(a); B = _to_dt(b)
            if A and B and B > A:
                ctx_ranges.append((A,B))
        if ctx_ranges:
            def _in_any(ts):
                try:
                    t = _dt.fromisoformat(str(ts).replace('Z','+00:00'))
                except Exception:
                    return False
                for (A,B) in ctx_ranges:
                    if A <= t <= B:
                        return True
                return False
            series = [row for row in series if _in_any(row.get('timestamp'))]
    except Exception:
        pass
    all_predictions: List[Dict[str, Any]] = []
    for row in series:
        ts_iso = str(row.get('timestamp') or '')
        row_predictions = _predictions_from_hits(_row_prediction_hits(row), ts_iso)
        row['predictions'] = row_predictions
        _apply_row_localization(row)
        all_predictions.extend(row_predictions)
    grouped_predictions = _aggregate_predictor_predictions(
        all_predictions,
        limit=max(25, min(len(all_predictions) or 0, 64)),
        step_minutes=step,
    )
    _apply_group_window_localization(series, grouped_predictions)
    # Peak rows should represent localized plateaus rather than only the globally strongest rows.
    peaks = []
    try:
        peaks = _build_predictor_peak_rows(series, limit=10)
    except Exception:
        peaks = []
    ranked_predictions = sorted(all_predictions, key=_prediction_sort_key)
    return _json_ok({
        'series': series,
        'peaks': _serialize_peak_rows(peaks),
        'context_window': {'start': start, 'end': end},
        'natal': natal_meta,
        'predictions': ranked_predictions[:50],
        'prediction_card': None,
        'context_filters': {
            'pd': {'start': pd_start, 'end': pd_end} if (pd_start and pd_end) else None,
            'sa': {'start': sa_start, 'end': sa_end} if (sa_start and sa_end) else None,
            'prog': {'start': prog_start, 'end': prog_end} if (prog_start and prog_end) else None,
        },
    })


@astro_clock_bp.route('/predictor', methods=['GET'])
@_error_handler
def transits_predictor():
    """Generate ranked event predictions across a window using enriched transit scans."""
    from transits_morin import scan_morin_transits_window
    natal_cd, natal_meta = _natal_from_query(request.args)
    start = request.args.get('start')
    end = request.args.get('end')
    if not (start and end):
        return jsonify({'success': False, 'error': 'start and end parameters are required'}), 400
    step = int(request.args.get('step_minutes', '60') or 60)
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    flt_transiting = request.args.getlist('transiting') or None
    flt_natal = request.args.getlist('natal') or None
    flt_aspects = request.args.getlist('aspect') or None
    pd_start = request.args.get('pd_start')
    pd_end = request.args.get('pd_end')
    sa_start = request.args.get('sa_start')
    sa_end = request.args.get('sa_end')
    prog_start = request.args.get('prog_start')
    prog_end = request.args.get('prog_end')

    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

    observer_location = request.args.get('location') or natal_meta.get('location')
    observer_timezone = request.args.get('timezone') or natal_meta.get('timezone')

    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        range(min(start_dt.year, end_dt.year), max(start_dt.year, end_dt.year) + 1) if (start_dt and end_dt) else [],
        route_label='transits/predictor',
    )

    series = scan_morin_transits_window(
        natal_cd,
        start,
        end,
        step_minutes=step,
        prediction_n_per_step=_TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE,
        include_modern=include_modern,
        natal_include_modern=natal_include_modern,
        include_cusps=include_cusps,
        include_antiscia=include_antiscia,
        include_lots=include_lots,
        focus_houses=focus_houses or None,
        focus_planets=focus_planets or None,
        sensitive_houses=sensitive_houses or None,
        sensitive_planets=sensitive_planets or None,
        flt_transiting=flt_transiting,
        flt_natal=flt_natal,
        flt_aspects=flt_aspects,
        pd_windows=pd_windows,
        use_new_significance=sig_beta,
        observer_location=observer_location,
        observer_timezone=observer_timezone,
    )

    # Apply optional context windows (PD/SA/Progressions) if provided.
    try:
        def _parse_ctx_iso(val: Optional[str]):
            if not val:
                return None
            try:
                return datetime.fromisoformat(str(val).replace('Z', '+00:00'))
            except Exception:
                return None

        ctx_ranges: List[Tuple[datetime, datetime]] = []
        for a, b in ((pd_start, pd_end), (sa_start, sa_end), (prog_start, prog_end)):
            A = _parse_ctx_iso(a)
            B = _parse_ctx_iso(b)
            if A and B and B > A:
                ctx_ranges.append((A, B))
        if ctx_ranges:
            def _in_any(ts_value):
                try:
                    t = datetime.fromisoformat(str(ts_value).replace('Z', '+00:00'))
                except Exception:
                    return False
                for A, B in ctx_ranges:
                    if A <= t <= B:
                        return True
                return False
            series = [row for row in series if _in_any(row.get('timestamp'))]
    except Exception:
        pass

    # Attach predictions per row and collect aggregate list
    all_predictions: List[Dict[str, Any]] = []
    for row in series:
        ts_iso = str(row.get('timestamp') or '')
        row_predictions = _predictions_from_hits(_row_prediction_hits(row), ts_iso)
        row['predictions'] = row_predictions
        _apply_row_localization(row)
        all_predictions.extend(row_predictions)

    grouped_predictions = _aggregate_predictor_predictions(
        all_predictions,
        limit=max(25, min(len(all_predictions) or 0, 64)),
        step_minutes=step,
    )
    _apply_group_window_localization(series, grouped_predictions)

    # Predictor peaks should prefer the strongest event-family row inside a flat plateau,
    # not just the globally strongest generic activity row.
    try:
        peaks = _build_predictor_peak_rows(series, limit=10)
    except Exception:
        peaks = []

    limit = int(request.args.get('limit', '40') or 40)
    ranked_predictions = sorted(all_predictions, key=_prediction_sort_key)
    grouped_predictions = grouped_predictions[:max(5, limit)]
    include_series = str(request.args.get('include_series', '0')).lower() in {'1','true','yes'}

    payload = {
        'natal': natal_meta,
        'window': {'start': start, 'end': end},
        'step_minutes': step,
        'observer': {'location': observer_location, 'timezone': observer_timezone},
        'context_filters': {
            'pd': {'start': pd_start, 'end': pd_end} if (pd_start and pd_end) else None,
            'sa': {'start': sa_start, 'end': sa_end} if (sa_start and sa_end) else None,
            'prog': {'start': prog_start, 'end': prog_end} if (prog_start and prog_end) else None,
        },
        'predictions': ranked_predictions[:max(1, limit)],
        'prediction_groups': grouped_predictions[:max(1, min(limit, 12))],
        'peaks': _serialize_peak_rows(peaks),
    }
    if include_series:
        payload['series'] = series
    return _json_ok(payload)


@astro_clock_bp.route('/transits/window/stream', methods=['GET'])
@_error_handler
def transits_window_stream():
    """Stream progress while scanning a window. Emits SSE events:

    - {type:'progress', step, total, progress, timestamp, row}
    - {type:'done', series, peaks, context_window, natal}
    """
    from transits_morin import _prepare_natal_context as _prep_ctx  # type: ignore
    from transits_morin import compute_morin_transits_to_natal  # type: ignore
    from transits_morin import enrich_hits_with_concordance
    import json as _json
    natal_cd, natal_meta = _natal_from_query(request.args)
    start = request.args.get('start')
    end = request.args.get('end')
    if not (start and end):
        return jsonify({'success': False, 'error': 'start/end required'}), 400
    step = int(request.args.get('step_minutes', '60') or 60)
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    # Filters
    flt_transiting = request.args.getlist('transiting') or None
    flt_natal = request.args.getlist('natal') or None
    flt_aspects = request.args.getlist('aspect') or None

    pd_start = request.args.get('pd_start')
    pd_end = request.args.get('pd_end')
    sa_start = request.args.get('sa_start')
    sa_end = request.args.get('sa_end')
    prog_start = request.args.get('prog_start')
    prog_end = request.args.get('prog_end')

    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    if start_dt is None or end_dt is None:
        return jsonify({'success': False, 'error': 'Invalid start/end'}), 400

    validated_total_steps, bounds_error = _validate_stream_scan_bounds(start_dt, end_dt, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400

    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        range(min(start_dt.year, end_dt.year), max(start_dt.year, end_dt.year) + 1),
        route_label='transits/window/stream',
    )

    # A/B toggle: ?sig_beta=0/1 to switch significance formula
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

    def _parse_ctx_iso(val: Optional[str]):
        if not val:
            return None
        try:
            return datetime.fromisoformat(str(val).replace('Z', '+00:00'))
        except Exception:
            return None

    ctx_ranges: List[Tuple[datetime, datetime]] = []
    for a, b in ((pd_start, pd_end), (sa_start, sa_end), (prog_start, prog_end)):
        A = _parse_ctx_iso(a)
        B = _parse_ctx_iso(b)
        if A and B and B > A:
            ctx_ranges.append((A, B))

    context_filters = {
        'pd': {'start': pd_start, 'end': pd_end} if (pd_start and pd_end) else None,
        'sa': {'start': sa_start, 'end': sa_end} if (sa_start and sa_end) else None,
        'prog': {'start': prog_start, 'end': prog_end} if (prog_start and prog_end) else None,
    }
    try:
        series_limit = int(request.args.get('series_limit', str(_STREAM_BUFFER_ROWS)) or _STREAM_BUFFER_ROWS)
    except Exception:
        series_limit = _STREAM_BUFFER_ROWS
    series_limit = max(25, min(series_limit, _STREAM_MAX_STEPS))
    prediction_buffer_limit = max(25, _STREAM_BUFFER_PREDICTIONS)

    def _sse():
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        sdt = start_dt
        edt = end_dt
        total = validated_total_steps or 1
        ctx = _prep_ctx(
            natal_cd,
            include_cusps=include_cusps,
            include_antiscia=include_antiscia,
            include_lots=include_lots,
            sensitive_houses=(sensitive_houses or None),
            sensitive_planets=(sensitive_planets or None),
            natal_include_modern=natal_include_modern,
        )
        cur = sdt
        delta = _td(minutes=step)
        series = []
        series_dropped = 0
        rows_total = 0
        retro_pass_tracker: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        all_predictions: List[Dict[str, Any]] = []
        total_predictions = 0

        for i in range(total):
            ts_iso = cur.replace(tzinfo=cur.tzinfo or _tz.utc).isoformat()
            hits = compute_morin_transits_to_natal(
                natal_cd,
                ts_iso,
                dt_hours=0.5,
                planet_names=None,
                include_modern=include_modern,
                natal_include_modern=natal_include_modern,
                include_cusps=include_cusps,
                include_antiscia=include_antiscia,
                include_lots=include_lots,
                focus_houses=(focus_houses or None),
                focus_planets=(focus_planets or None),
                sensitive_houses=(sensitive_houses or None),
                sensitive_planets=(sensitive_planets or None),
                observer_location=natal_meta.get('location'),
                observer_timezone=natal_meta.get('timezone'),
                _prepared_ctx=ctx,
            )
            if flt_transiting:
                hits = [h for h in hits if str(h.get('transiting')) in flt_transiting]
            if flt_natal:
                hits = [h for h in hits if str(h.get('natal')) in flt_natal]
            if flt_aspects:
                hits = [h for h in hits if str(h.get('aspect')) in flt_aspects]
            hits = _retry_enrich_transit_hits(
                natal_cd,
                hits,
                ts_iso,
                pd_windows=pd_windows,
                sig_beta=sig_beta,
                observer_location=natal_meta.get('location'),
                observer_timezone=natal_meta.get('timezone'),
                route_label='transits/window/stream',
            )
            for h in hits:
                key = (
                    str(h.get('transiting') or ''),
                    str(h.get('target_label') or h.get('natal') or ''),
                    str(h.get('aspect') or ''),
                )
                phase = str(h.get('phase') or '')
                info = retro_pass_tracker.get(key)
                if info:
                    count = info['count']
                    if info.get('last_phase') == 'separating' and phase == 'applying':
                        count += 1
                else:
                    count = 1
                retro_pass_tracker[key] = {'count': count, 'last_phase': phase}
                h['passIndex'] = count
            # pick top planets & points
            top_n = 3
            prediction_n = max(top_n, _TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE)
            top_planets = [h for h in hits if str(h.get('target_type')) == 'planet'][:top_n]
            top_points = [h for h in hits if str(h.get('target_type')) != 'planet'][:top_n]
            prediction_planets = [h for h in hits if str(h.get('target_type')) == 'planet'][:prediction_n]
            prediction_points = [h for h in hits if str(h.get('target_type')) != 'planet'][:prediction_n]
            try:
                step_signif = sum(float(h.get('significance') or 0.0) for h in (top_planets + top_points))
            except Exception:
                step_signif = sum(float(h.get('score') or 0.0) for h in (top_planets + top_points))
            # Aggregate step tone from top hits if available
            def _step_tone(hits_list):
                try:
                    scores = [float(h.get('tone_score') or 0.0) for h in hits_list]
                    if not scores:
                        return 'mixed'
                    avg = sum(scores)/len(scores)
                    if avg >= 0.8:
                        return 'positive'
                    if avg <= -0.8:
                        return 'negative'
                    return 'mixed'
                except Exception:
                    return 'mixed'
            row = {
                'timestamp': ts_iso,
                'count': len(hits),
                'top': (top_planets + top_points),
                'top_planets': top_planets,
                'top_cusps': top_points,
                'step_score': round(float(step_signif), 3),
                'tone': _step_tone(top_planets + top_points),
            }
            include_row = True
            if ctx_ranges:
                try:
                    t_dt = _dt.fromisoformat(ts_iso.replace('Z', '+00:00'))
                    include_row = any(A <= t_dt <= B for (A, B) in ctx_ranges)
                except Exception:
                    include_row = False
            if include_row:
                row_predictions = _predictions_from_hits((prediction_planets + prediction_points), ts_iso)
                row['predictions'] = row_predictions
                _apply_row_localization(row)
                total_predictions += len(row_predictions)
                all_predictions.extend(row_predictions)
                if len(all_predictions) > prediction_buffer_limit:
                    all_predictions = sorted(all_predictions, key=_prediction_sort_key)[:prediction_buffer_limit]
                series.append(row)
                rows_total += 1
                if len(series) > series_limit:
                    overflow = len(series) - series_limit
                    del series[:overflow]
                    series_dropped += overflow
            else:
                row = None
            progress = (i + 1) / float(total)
            evt = {'type': 'progress', 'step': i + 1, 'total': total, 'progress': progress, 'timestamp': ts_iso, 'row': row}
            yield f"data: {_json.dumps(evt)}\n\n"
            cur = cur + delta
            if cur > edt:
                break
        # Peaks
        grouped_predictions = _aggregate_predictor_predictions(
            all_predictions,
            limit=max(25, min(len(all_predictions) or 0, 64)),
            step_minutes=step,
        )
        _apply_group_window_localization(series, grouped_predictions)
        try:
            peaks = _build_predictor_peak_rows(series, limit=10)
        except Exception:
            peaks = []
        ranked_predictions = sorted(all_predictions, key=_prediction_sort_key)
        done = {
            'type': 'done',
            'series': series,
            'peaks': _serialize_peak_rows(peaks),
            'context_window': {'start': start, 'end': end},
            'natal': natal_meta,
            'predictions': ranked_predictions[:50],
            'context_filters': context_filters,
            'stream_stats': {
                'series_total': rows_total,
                'series_retained': len(series),
                'series_dropped': series_dropped,
                'predictions_total': total_predictions,
                'predictions_retained': len(all_predictions),
                'predictions_dropped': max(0, total_predictions - len(all_predictions)),
            },
        }
        yield f"data: {_json.dumps(done)}\n\n"

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    return Response(stream_with_context(_sse()), headers=headers)


@astro_clock_bp.route('/transits/export', methods=['GET'])
@_error_handler
def transits_export_csv():
    from io import StringIO
    from flask import Response as _Resp
    from transits_morin import compute_morin_transits_to_natal
    natal_cd, natal_meta = _natal_from_query(request.args)
    ts = request.args.get('transit_datetime') or datetime.now(timezone.utc).isoformat()
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    flt_transiting = request.args.getlist('transiting') or None
    flt_natal = request.args.getlist('natal') or None
    flt_aspects = request.args.getlist('aspect') or None
    hits = compute_morin_transits_to_natal(
        natal_cd, ts, include_modern=include_modern, natal_include_modern=natal_include_modern,
        include_cusps=include_cusps, include_antiscia=include_antiscia, include_lots=include_lots,
        focus_houses=focus_houses or None,
        focus_planets=focus_planets or None,
        sensitive_houses=sensitive_houses or None,
        sensitive_planets=sensitive_planets or None,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
    )
    # Enrich for determination strength + concordance (optional)
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}
    target_dt = _parse_iso_datetime(ts)
    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        [target_dt.year] if target_dt is not None else [],
        route_label='transits/export',
    )
    hits = _retry_enrich_transit_hits(
        natal_cd,
        hits,
        ts,
        pd_windows=pd_windows,
        sig_beta=sig_beta,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
        route_label='transits/export',
    )
    if flt_transiting:
        hits = [h for h in hits if str(h.get('transiting')) in flt_transiting]
    if flt_natal:
        hits = [h for h in hits if str(h.get('natal')) in flt_natal or str(h.get('target_label')) in flt_natal]
    if flt_aspects:
        hits = [h for h in hits if str(h.get('aspect')) in flt_aspects]
    out = StringIO()
    header = ['Timestamp','Transiting','Natal','Aspect','Orb','MaxOrb','Phase','Partile','CompletePlatic','Score','Quality','DeterminationStrength']
    out.write(','.join(header) + '\n')
    for h in hits:
        row = [
            ts,
            str(h.get('transiting','')),
            str(h.get('natal') or h.get('target_label') or ''),
            str(h.get('aspect','')),
            str(h.get('orb','')),
            str(h.get('max_orb','')),
            str(h.get('phase','')),
            '1' if h.get('partile') else '0',
            '1' if h.get('complete_platic') else '0',
            str(h.get('score','')),
            str(h.get('quality','')),
            str(h.get('determination_strength','')),
        ]
        out.write(','.join(str(x).replace(',', ';') for x in row) + '\n')
    csv = out.getvalue()
    return _Resp(csv, headers={
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="transits.csv"'
    })


@astro_clock_bp.route('/transits/window/export', methods=['GET'])
@_error_handler
def transits_window_export_csv():
    from io import StringIO
    from flask import Response as _Resp
    from transits_morin import scan_morin_transits_window
    natal_cd, natal_meta = _natal_from_query(request.args)
    start = request.args.get('start')
    end = request.args.get('end')
    if not (start and end):
        center = request.args.get('center')
        range_hours_raw = request.args.get('range_hours', '12')
        try:
            range_hours = float(range_hours_raw or 12.0)
        except Exception:
            range_hours = 12.0
        if center:
            try:
                from datetime import timedelta
                center_dt = datetime.fromisoformat(str(center).replace('Z', '+00:00'))
                start = (center_dt - timedelta(hours=range_hours / 2.0)).isoformat()
                end = (center_dt + timedelta(hours=range_hours / 2.0)).isoformat()
            except Exception:
                start = start or None
                end = end or None
    if not (start and end):
        return jsonify({'success': False, 'error': 'start/end or center/range_hours required'}), 400
    step = int(request.args.get('step_minutes', '60') or 60)
    include_modern = (request.args.get('include_modern', '0').lower() in {'1','true','yes'})
    natal_include_modern = (request.args.get('include_natal_modern', '0').lower() in {'1','true','yes'})
    include_cusps = (request.args.get('include_cusps', '0').lower() in {'1','true','yes'})
    include_antiscia = (request.args.get('include_antiscia', '0').lower() in {'1','true','yes'})
    include_lots = (request.args.get('include_lots', '0').lower() in {'1','true','yes'})
    focus_houses = [int(x) for x in request.args.getlist('focus_house') if x and str(x).isdigit()]
    focus_planets = [str(x) for x in request.args.getlist('focus_planet') if str(x).strip()]
    sensitive_houses = [int(x) for x in request.args.getlist('sensitive_house') if x and str(x).isdigit()]
    sensitive_planets = [str(x) for x in request.args.getlist('sensitive_planet') if str(x).strip()]
    flt_transiting = request.args.getlist('transiting') or None
    flt_natal = request.args.getlist('natal') or None
    flt_aspects = request.args.getlist('aspect') or None
    pd_start = request.args.get('pd_start')
    pd_end = request.args.get('pd_end')
    sa_start = request.args.get('sa_start')
    sa_end = request.args.get('sa_end')
    prog_start = request.args.get('prog_start')
    prog_end = request.args.get('prog_end')
    # A/B toggle via ?sig_beta=0/1
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    pd_windows = _compute_pd_windows_for_years(
        natal_cd,
        natal_meta,
        request.args,
        [dt.year for dt in (start_dt, end_dt) if dt is not None],
        route_label='transits/window/export',
    )

    series = scan_morin_transits_window(
        natal_cd, start, end, step_minutes=step,
        include_modern=include_modern, natal_include_modern=natal_include_modern,
        include_cusps=include_cusps, include_antiscia=include_antiscia, include_lots=include_lots,
        focus_houses=focus_houses or None,
        focus_planets=focus_planets or None,
        sensitive_houses=sensitive_houses or None,
        sensitive_planets=sensitive_planets or None,
        flt_transiting=flt_transiting,
        flt_natal=flt_natal,
        flt_aspects=flt_aspects,
        pd_windows=pd_windows,
        use_new_significance=sig_beta,
        observer_location=natal_meta.get('location'),
        observer_timezone=natal_meta.get('timezone'),
    )
    try:
        def _parse_ctx_iso(val: Optional[str]):
            if not val:
                return None
            try:
                return datetime.fromisoformat(str(val).replace('Z', '+00:00'))
            except Exception:
                return None

        ctx_ranges: List[Tuple[datetime, datetime]] = []
        for a, b in ((pd_start, pd_end), (sa_start, sa_end), (prog_start, prog_end)):
            A = _parse_ctx_iso(a)
            B = _parse_ctx_iso(b)
            if A and B and B > A:
                ctx_ranges.append((A, B))
        if ctx_ranges:
            def _in_any(ts_value):
                try:
                    t = datetime.fromisoformat(str(ts_value).replace('Z', '+00:00'))
                except Exception:
                    return False
                for A, B in ctx_ranges:
                    if A <= t <= B:
                        return True
                return False
            series = [row for row in series if _in_any(row.get('timestamp'))]
    except Exception:
        pass
    out = StringIO()
    header = ['Timestamp','TopCount','Transiting','Natal','Aspect','Orb','Score','Quality','DeterminationStrength']
    out.write(','.join(header) + '\n')
    for row in series:
        ts = row.get('timestamp','')
        tops = row.get('top') or []
        if not tops:
            out.write(','.join([ts, '0','','','','','','','']) + '\n')
        for h in tops:
            out.write(','.join([
                ts,
                str(len(tops)),
                str(h.get('transiting','')),
                str(h.get('natal') or h.get('target_label') or ''),
                str(h.get('aspect','')),
                str(h.get('orb','')),
                str(h.get('score','')),
                str(h.get('quality','')),
                str(h.get('determination_strength','')),
            ]) + '\n')
    csv = out.getvalue()
    return _Resp(csv, headers={
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="transits_window.csv"'
    })


@astro_clock_bp.route('/context/auto', methods=['GET'])
@_error_handler
def auto_context():
    """Suggest context windows (PD via Solar Arc, Progressions) and focus hints.

    Accepts natal snap or natal_*; optional: year, anchor_start/anchor_end/anchor_center (ISO).
    """
    from context_layers import (
        compute_solar_arc_windows, compute_progressed_planet_windows, suggest_focus_from_natal
    )
    try:
        from primary_directions import compute_primary_direction_windows
    except Exception:
        compute_primary_direction_windows = None  # type: ignore
    # Swiss Ephemeris availability (for clearer status)
    try:
        import swisseph as _swe  # type: ignore
        _swe_ok = True
    except Exception:
        _swe_ok = False
    natal_cd, natal_meta = _natal_from_query(request.args)
    # Year preference: anchor -> provided -> current
    year = None
    for key in ('anchor_center','anchor_start','anchor_end'):
        val = request.args.get(key)
        if val:
            try:
                year = datetime.fromisoformat(val.replace('Z','+00:00')).year
                break
            except Exception:
                continue
    if year is None:
        try:
            year = int(request.args.get('year', '0') or 0)
        except Exception:
            year = 0
    if not year:
        year = datetime.now(timezone.utc).year
    # Anchor helpers
    def _parse_iso(x):
        if not x:
            return None
        try:
            return datetime.fromisoformat(str(x).replace('Z','+00:00'))
        except Exception:
            return None
    anchor_start = request.args.get('anchor_start')
    anchor_end = request.args.get('anchor_end')
    anchor_center = request.args.get('anchor_center')
    anchor_start_dt = _parse_iso(anchor_start)
    anchor_end_dt = _parse_iso(anchor_end)
    anchor_center_dt = _parse_iso(anchor_center)

    # Natal datetime for progressed calculations — derive from natal metadata if present
    natal_dt = None
    try:
        iso = request.args.get('natal_datetime') or request.args.get('anchor_center') or natal_meta.get('timestamp')
        if iso:
            natal_dt = datetime.fromisoformat(iso.replace('Z','+00:00'))
    except Exception:
        natal_dt = None
    pd = []
    sa = []
    prog = []
    pd_status = 'ok'
    sa_status = 'ok'
    prog_status = 'ok'
    try:
        if not _swe_ok:
            # Without Swiss Ephemeris, none of the contexts can be computed
            pd = []; sa = []; prog = []
            pd_status = sa_status = prog_status = 'swe_missing'
        elif natal_dt:
            sa = compute_solar_arc_windows(natal_dt, year, natal_cd)
            sa_status = 'ok' if sa else 'no_events_this_year'
            prog = compute_progressed_planet_windows(natal_dt, year, natal_cd)
            prog_status = 'ok' if prog else 'no_events_this_year'
            # Proper PD windows when module available; fallback to SA when not
            if compute_primary_direction_windows:
                try:
                    pd = compute_primary_direction_windows(natal_dt, year, natal_cd)
                    pd_status = 'ok' if pd else 'no_events_this_year'
                except Exception:
                    pd = []
                    pd_status = 'error'
            else:
                # Fallback: copy SA windows and tag method for clarity
                pd = []
                for w in (sa or []):
                    try:
                        ww = dict(w)
                        item = dict(ww.get('item') or {})
                        item['method'] = 'sa_fallback'
                        ww['item'] = item
                        pd.append(ww)
                    except Exception:
                        continue
                pd_status = 'pd_import_failed' if not pd else 'pd_import_failed'
        else:
            pd = []; sa = []; prog = []
            pd_status = sa_status = prog_status = 'no_natal'
    except Exception:
        pd = []; sa = []; prog = []
        # Keep best-effort statuses if set above; otherwise generic error
        if pd_status == 'ok':
            pd_status = 'error'
        if sa_status == 'ok':
            sa_status = 'error'
        if prog_status == 'ok':
            prog_status = 'error'

    # Selection utilities (nearest to anchor or overlapping anchor range)
    def _choose_window(windows):
        if not windows:
            return None
        # Prefer overlap with anchor range
        if anchor_start_dt and anchor_end_dt and anchor_end_dt > anchor_start_dt:
            overlapping = []
            for w in windows:
                try:
                    s = _parse_iso(w.get('start')); e = _parse_iso(w.get('end'))
                    if s and e and e > s and not (e < anchor_start_dt or s > anchor_end_dt):
                        overlapping.append((s, e, w))
                except Exception:
                    continue
            if overlapping:
                # If multiple overlap, prefer one closest to anchor_center if provided
                if anchor_center_dt:
                    overlapping.sort(key=lambda t: abs(( (t[0]+(t[1]-t[0])/2) - anchor_center_dt ).total_seconds()))
                return overlapping[0][2]
        # Else pick nearest to anchor_center
        if anchor_center_dt:
            scored = []
            for w in windows:
                try:
                    s = _parse_iso(w.get('start')); e = _parse_iso(w.get('end'))
                    if s and e and e > s:
                        mid = s + (e - s)/2
                        scored.append((abs((mid - anchor_center_dt).total_seconds()), w))
                except Exception:
                    continue
            if scored:
                scored.sort(key=lambda t: t[0])
                return scored[0][1]
        # Fallback: first
        return windows[0]
    # Choose selected PD/SA/Progression windows (use outer mapping for progressions when available)
    pd_selected = _choose_window(pd)
    sa_selected = _choose_window(sa)
    # For progressions, prefer outer_* fields when present for selection
    def _windows_for_prog_outer(lst):
        out = []
        for w in (lst or []):
            s = w.get('outer_start') or w.get('start')
            e = w.get('outer_end') or w.get('end')
            ww = dict(w)
            ww['start'] = s
            ww['end'] = e
            out.append(ww)
        return out
    prog_outer_list = _windows_for_prog_outer(prog)
    prog_selected_outer = _choose_window(prog_outer_list)

    # Focus suggestions
    try:
        houses, planets = suggest_focus_from_natal(natal_cd)
    except Exception:
        houses, planets = [1,10], []
    try:
        from transits_context_maturity import get_transits_context_maturity
        context_maturity = get_transits_context_maturity()
    except Exception:
        context_maturity = {}
    out = {
        'natal': natal_meta,
        'pd_windows': pd,
        'sa_windows': sa,
        'progression_windows': prog,
        'progression_windows_outer': prog_outer_list,
        'pd_selected': pd_selected,
        'sa_selected': sa_selected,
        'prog_window': prog_selected_outer or (prog[0] if prog else None),
        'focus_houses': houses,
        'focus_planets': planets,
        'context_maturity': context_maturity,
        'status': {
            'pd': pd_status,
            'sa': sa_status,
            'prog': prog_status,
        }
    }
    return _json_ok(out)


@astro_clock_bp.route('/forensic', methods=['GET'])
@_error_handler
def forensic_analysis():
    """Knowledge-based forensic analysis on the current (or ad-hoc) chart.

    Optional query: mode, datetime, location, timezone, latitude, longitude,
    abduction=1, origin="lat,lon", line_zones=1, corridor_deg
    """
    q_mode = str(request.args.get('mode') or '').strip().lower()
    if q_mode and q_mode not in {'realtime', 'manual', 'paused'}:
        return jsonify({'success': False, 'error': 'Invalid mode'}), 400

    with _astro_perf_span('route.forensic.prepare_chart', mode=q_mode or None):
        eng = _engine_instance()
        data, _active_settings = _data_for_request_clock_context(eng)
        dash = _build_dashboard_payload(eng, data, include_modern=True)

        # Enrich with all aspects from chart_result if present
        with _astro_perf_span('route.forensic.expand_chart'):
            try:
                chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
            except Exception:
                chart = {}
            cd = chart.get('chart_data') if isinstance(chart, dict) else {}
            try:
                if isinstance(cd, str):
                    cd = json.loads(cd)
            except Exception:
                cd = {}
            # Ensure forensic extraction can evaluate all aspect links (not only top/tightest dashboard summary).
            try:
                all_aspects = []
                if isinstance(chart, dict):
                    top_aspects = chart.get('aspects')
                    if isinstance(top_aspects, list):
                        all_aspects = [a for a in top_aspects if isinstance(a, dict)]
                if not all_aspects and isinstance(cd, dict):
                    cd_aspects = cd.get('aspects')
                    if isinstance(cd_aspects, list):
                        all_aspects = [a for a in cd_aspects if isinstance(a, dict)]
                if all_aspects:
                    dash['all_aspects'] = all_aspects
            except Exception:
                pass

    # Feature extraction and rule evaluation
    from forensic.features import extract_features, compute_dominance
    from forensic.survivability import compute_survivability
    from forensic.engine import load_knowledge, load_planetary_meanings, load_dictionary
    with _astro_perf_span('route.forensic.evaluate_knowledge'):
        knowledge_dir = os.path.join(os.path.dirname(__file__), 'forensic', 'knowledge')
        try:
            rules = load_knowledge(knowledge_dir)
        except Exception:
            rules = []
        features = extract_features(dash)
        try:
            from forensic.engine import evaluate
            findings = evaluate(features, rules)
        except Exception:
            findings = []
        dominance = compute_dominance(features)

    # Receptions (mutual + top unilateral) for relationship analysis
    receptions = { 'mutual': [], 'top_unilateral': [] }
    try:
        details = chart.get('reception_details') or (cd.get('reception_details') if isinstance(cd, dict) else None)
        mutual: List[Dict[str, Any]] = []
        top_unilateral: List[Dict[str, Any]] = []
        if isinstance(details, dict):
            for m in details.get('mutual_receptions', []) or []:
                if isinstance(m, dict):
                    mutual.append({
                        'p1': m.get('planet1') or m.get('a') or '—',
                        'p2': m.get('planet2') or m.get('b') or '—',
                        'type': m.get('type') or 'mutual_reception',
                        'strength': m.get('strength') or m.get('score') or 0,
                    })
            for u in (details.get('one_way_receptions') or []):
                if isinstance(u, dict):
                    top_unilateral.append({
                        'receiving': u.get('receiver') or '—',
                        'received': u.get('received') or '—',
                        'dignities': list(u.get('dignity', [])) if isinstance(u.get('dignity'), list) else ([u.get('dignity')] if u.get('dignity') else []),
                        'strength': u.get('strength') or 0,
                    })
        if not mutual and not top_unilateral:
            # Fallback: compute from chart_data
            try:
                chart_obj = _extract_internal_chart_from_result(chart) if isinstance(chart, dict) else None
                source_cd = cd
                if chart_obj is None:
                    if isinstance(source_cd, str):
                        source_cd = json.loads(source_cd)
                    if not isinstance(source_cd, dict):
                        source_cd = {}
                    # Normalize planets for deserializer (classical only)
                    pls = source_cd.get('planets')
                    allowed = {'Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn'}
                    if isinstance(pls, list):
                        d = {}
                        for p in pls:
                            if not isinstance(p, dict):
                                continue
                            nm = p.get('planet') or p.get('name')
                            if nm in allowed:
                                d[str(nm)] = {k: v for k, v in p.items() if k not in ('planet','name')}
                        source_cd['planets'] = d
                    elif isinstance(pls, dict):
                        source_cd['planets'] = {k: v for k, v in pls.items() if k in allowed and isinstance(v, dict)}
                    # Sanitize aspects
                    asp = source_cd.get('aspects')
                    if isinstance(asp, list):
                        clean = []
                        for a in asp:
                            if not isinstance(a, dict):
                                continue
                            p1 = str(a.get('planet1') or a.get('p1') or '')
                            p2 = str(a.get('planet2') or a.get('p2') or '')
                            if p1 in allowed and p2 in allowed:
                                clean.append(a)
                        source_cd['aspects'] = clean
                    chart_obj = deserialize_chart_for_evaluation(source_cd) if isinstance(source_cd, dict) else None
                if chart_obj is not None:
                    calc = TraditionalReceptionCalculator()
                    classical = [Planet.SUN, Planet.MOON, Planet.MERCURY, Planet.VENUS, Planet.MARS, Planet.JUPITER, Planet.SATURN]
                    tmp_mutual: List[Tuple[str, str, str, int]] = []
                    tmp_uni: List[Tuple[str, str, List[str], int]] = []
                    for i in range(len(classical)):
                        for j in range(i+1, len(classical)):
                            a = classical[i]; b = classical[j]
                            comp = calc.calculate_comprehensive_reception(chart_obj, a, b)
                            rtype = comp.get('type') or 'none'
                            if rtype in ('mutual_rulership','mutual_exaltation','mutual_term','mutual_face','mixed_reception'):
                                strength = int(comp.get('traditional_strength') or 0)
                                tmp_mutual.append((a.value, b.value, rtype, strength))
                            dir1 = calc.does_planet_receive(chart_obj, a, b)
                            if dir1.get('has_reception'):
                                tmp_uni.append((a.value, b.value, list(dir1.get('dignities') or []), int(dir1.get('reception_strength') or 0)))
                            dir2 = calc.does_planet_receive(chart_obj, b, a)
                            if dir2.get('has_reception'):
                                tmp_uni.append((b.value, a.value, list(dir2.get('dignities') or []), int(dir2.get('reception_strength') or 0)))
                    seen_pairs = set()
                    for p1, p2, t, s in sorted(tmp_mutual, key=lambda x: (-x[3], x[0], x[1])):
                        key = (min(p1, p2), max(p1, p2), t)
                        if key in seen_pairs:
                            continue
                        seen_pairs.add(key)
                        mutual.append({'p1': p1, 'p2': p2, 'type': t, 'strength': s})
                    for rcv, rec, digs, s in sorted(tmp_uni, key=lambda x: (-x[3], x[0], x[1]))[:8]:
                        top_unilateral.append({'receiving': rcv, 'received': rec, 'dignities': digs, 'strength': s})
            except Exception:
                mutual, top_unilateral = [], []
        receptions = { 'mutual': mutual, 'top_unilateral': top_unilateral }
    except Exception:
        receptions = { 'mutual': [], 'top_unilateral': [] }

    # Relationship star hits: fixed-star conjunctions to ASC/DSC rulers (<=1°)
    relationship_star_hits = {}
    try:
        rulers = (features.get('house_rulers') or {}) if isinstance(features, dict) else {}
        def _planet_lon(name: Optional[str]) -> Optional[float]:
            try:
                if not name:
                    return None
                return float((features.get('planets') or {}).get(name, {}).get('longitude'))
            except Exception:
                return None
        def _hits_for_lon(lon: Optional[float]) -> List[Dict[str, Any]]:
            if lon is None:
                return []
            out: List[Dict[str, Any]] = []
            try:
                L = float(lon) % 360.0
            except Exception:
                return []
            def _ang(a: float, b: float) -> float:
                d = abs((a - b) % 360.0)
                return d if d <= 180.0 else 360.0 - d
            for star in FIXED_STAR_CATALOG:
                try:
                    sL = float(star.get('longitude')) % 360.0
                    d = _ang(L, sL)
                    if d <= 1.0:
                        out.append({
                            'name': star.get('name'),
                            'constellation': star.get('constellation'),
                            'star_longitude': sL,
                            'target_longitude': L,
                            'orb_deg': round(d, 3),
                        })
                except Exception:
                    continue
            out.sort(key=lambda h: h.get('orb_deg', 999))
            return out
        asc_ruler = rulers.get('1') or rulers.get(1)
        dsc_ruler = rulers.get('7') or rulers.get(7)
        relationship_star_hits = {
            'asc_ruler': _hits_for_lon(_planet_lon(asc_ruler)),
            'dsc_ruler': _hits_for_lon(_planet_lon(dsc_ruler)),
        }
    except Exception:
        relationship_star_hits = {}

    # Dictionaries
    planetary_meanings = load_planetary_meanings(knowledge_dir)
    def _ld(name):
        try:
            return load_dictionary(knowledge_dir, name)
        except Exception:
            return {}
    house_meanings = _ld('house_meanings.yaml')
    fixed_star_meanings = _ld('fixed_star_meanings.yaml')
    aspect_meanings = _ld('aspect_meanings.yaml')
    perpetrator_profiles = _ld('perpetrator_profiles.yaml')
    degree_special = _ld('degree_special.yaml')
    witness_accomplice = _ld('witness_accomplice.yaml')
    ic_sign_meanings = _ld('ic_sign_meanings.yaml')
    ic_ruler_house_meanings = _ld('ic_ruler_house_meanings.yaml')
    ic_planet_in_4th = _ld('ic_planet_in_4th.yaml')

    # Extract light mediation hints from serialized chart
    def _extract_light_mediation(chart_obj: Dict[str, Any]) -> Dict[str, Any]:
        info = { 'translation': False, 'collection': False, 'translator': None, 'collector': None, 'evidence': [] }
        try:
            texts: List[str] = []
            rs = chart_obj.get('reasoning') or []
            for r in rs:
                if isinstance(r, str):
                    texts.append(r.lower())
                elif isinstance(r, dict):
                    txt = str(r.get('rule') or r.get('key') or r.get('stage') or '')
                    if txt:
                        texts.append(txt.lower())
            rv1 = (chart_obj.get('reasoning_v1') or {}).get('entries') or []
            for e in rv1:
                txt = str(e.get('rule') or e.get('stage') or '')
                if txt:
                    texts.append(txt.lower())
            blob = "\n".join(texts)
            if 'translation of light' in blob or ('translation' in blob and 'light' in blob):
                info['translation'] = True; info['evidence'].append('reasoning: translation of light')
            if 'collection of light' in blob or ('collection' in blob and 'light' in blob):
                info['collection'] = True; info['evidence'].append('reasoning: collection of light')
            # Shallow scan for explicit translator/collector keys anywhere
            def _walk(o):
                if isinstance(o, dict):
                    for k,v in o.items():
                        kl = str(k).lower()
                        if kl == 'translator' and v and not info['translator']:
                            info['translator'] = v if isinstance(v, str) else getattr(v,'value',None) or str(v)
                        if kl == 'collector' and v and not info['collector']:
                            info['collector'] = v if isinstance(v, str) else getattr(v,'value',None) or str(v)
                        _walk(v)
                elif isinstance(o, list):
                    for it in o: _walk(it)
            _walk(chart_obj)
        except Exception:
            pass
        return info

    light_mediation = _extract_light_mediation(chart if isinstance(chart, dict) else {})

    # Roll up finding categories before composing dependent summaries.
    try:
        cats: Dict[str, int] = {}
        for f in findings:
            c = f.get('category') or 'General'
            cats[c] = cats.get(c, 0) + 1
    except Exception:
        cats = {}

    survival_case_type = str(request.args.get('case_type') or 'general').strip().lower()
    try:
        survivability = compute_survivability(
            features,
            findings=findings,
            categories=cats,
            case_type=survival_case_type,
        )
    except Exception:
        survivability = {
            'level': 'Moderate',
            'score': 0.0,
            'case_type': 'general',
            'victim_significators': [],
            'breakdown': {
                'vitality': 0.0,
                'support': 0.0,
                'moon': 0.0,
                'danger': 0.0,
                'fatal_pressure': 0.0,
            },
            'evidence': {
                'vitality': [],
                'support': [],
                'moon': [],
                'danger': [],
                'fatal_pressure': [],
            },
            'note': 'Survivability summary unavailable.',
        }

    out = {
        'success': True,
        'timestamp': dash.get('timestamp'),
        'location': dash.get('location'),
        'timezone_label': dash.get('timezone_label'),
        'moon': dash.get('moon'),
        'moon_timeline': dash.get('moon_timeline'),
        'categories': cats,
        'findings': findings,
        # Knowledge dictionaries and lookups
        'planetary_meanings': planetary_meanings,
        'house_meanings': house_meanings,
        'fixed_star_meanings': fixed_star_meanings,
        'aspect_meanings': aspect_meanings,
        'perpetrator_profiles': perpetrator_profiles,
        'degree_special': degree_special,
        'witness_accomplice': witness_accomplice,
        'ic_sign_meanings': ic_sign_meanings,
        'ic_ruler_house_meanings': ic_ruler_house_meanings,
        'ic_planet_in_4th': ic_planet_in_4th,
        'abduction_location': _ld('abduction_location.yaml'),
        # Derived
        'light_mediation': light_mediation,
        'features': features,
        'dominance': dominance,
        'survivability': survivability,
        'receptions': receptions,
        'relationship_star_hits': relationship_star_hits,
    }

    # Optional abduction local-space mapping
    abd = (request.args.get('abduction','0').lower() in {'1','true','yes'})
    if abd:
        try:
            origin_str = request.args.get('origin') or ''
            lat, lon = None, None
            origin_source = None
            if ',' in origin_str:
                a, b = origin_str.split(',', 1)
                lat = float(a.strip()); lon = float(b.strip())
                origin_source = 'query_origin'
            if lat is None or lon is None:
                coords = _coords_from_request_args(request.args, strict=False)
                if coords:
                    lat, lon = coords
                    origin_source = 'query_coordinates'
            if lat is None or lon is None:
                coords = _coords_from_settings(getattr(data, 'settings', None))
                if coords:
                    lat, lon = coords
                    origin_source = 'settings_coordinates'
            if lat is None or lon is None:
                # derive from engine settings/location
                coords = _ensure_coords_for_location(
                    dash.get('location'),
                    settings_hint=getattr(data, 'settings', None),
                )
                if coords:
                    lat, lon = coords
                    origin_source = 'geocoded_location'
            if lat is not None and lon is not None:
                from forensic.local_space import compute_local_space
                roles = {}
                try:
                    # Map rulers from extracted features
                    rulers = (features.get('house_rulers') or {})
                    roles['H1_ruler'] = str(rulers.get('1') or rulers.get(1) or '')
                    roles['H7_ruler'] = str(rulers.get('7') or rulers.get(7) or '')
                    roles['H3_ruler'] = str(rulers.get('3') or rulers.get(3) or '')
                    roles['H9_ruler'] = str(rulers.get('9') or rulers.get(9) or '')
                    roles['H12_ruler'] = str(rulers.get('12') or rulers.get(12) or '')
                except Exception:
                    roles = {}
                planets = [p for p in [roles.get('H1_ruler'), roles.get('H3_ruler'), roles.get('H7_ruler'), roles.get('H9_ruler'), roles.get('H12_ruler'), 'Moon'] if p]
                altaz = compute_local_space(dash.get('timestamp'), float(lat), float(lon), planets)
                bearings = []
                for role, pname in roles.items():
                    if not pname: continue
                    try:
                        az = altaz.get(pname, {}).get('azimuth_deg')
                        al = altaz.get(pname, {}).get('altitude_deg')
                        if az is not None:
                            item = {'planet': pname, 'azimuth_deg': float(az), 'role': role}
                            if al is not None:
                                item['altitude_deg'] = float(al)
                            bearings.append(item)
                    except Exception:
                        continue
                # Always include Moon bearing
                try:
                    if 'Moon' in altaz and all(b.get('role') != 'Moon' for b in bearings):
                        m = altaz['Moon']
                        mitem = {'planet':'Moon', 'azimuth_deg': float(m.get('azimuth_deg')), 'role':'Moon'}
                        if m.get('altitude_deg') is not None:
                            mitem['altitude_deg'] = float(m.get('altitude_deg'))
                        bearings.append(mitem)
                except Exception:
                    pass
                line_zones = (request.args.get('line_zones','0').lower() in {'1','true','yes'})
                corridor = float(request.args.get('corridor_deg','6') or 6)
                out['abduction_map'] = {
                    'origin': {'lat': lat, 'lon': lon},
                    'origin_source': origin_source,
                    'bearings': bearings,
                    'line_zones': bool(line_zones),
                    'corridor_deg': corridor,
                }
        except Exception:
            # Non-fatal
            pass

    from flask import jsonify as _j
    return _j(out)


@astro_clock_bp.route('/election/validate', methods=['GET'])
def election_validate():
    matter = (request.args.get('matter') or 'marriage').strip().lower()
    marriage_algorithm = (request.args.get('marriage_algorithm') or 'alpha').strip().lower()
    business_algorithm = (request.args.get('business_algorithm') or 'alpha').strip().lower()
    start = request.args.get('start')
    end = request.args.get('end')
    location = request.args.get('location')
    timezone_name = request.args.get('timezone')
    step_minutes = request.args.get('step_minutes')
    weekday_mode = (request.args.get('weekday_mode') or '').strip().lower()
    hour_start = request.args.get('hour_start')
    hour_end = request.args.get('hour_end')
    participant_snap_ids = [str(item).strip() for item in request.args.getlist('participant_snap_id') if str(item).strip()]
    unique_participant_snap_ids = list(dict.fromkeys(participant_snap_ids))

    if not (start and end and location):
        return jsonify({'success': False, 'error': 'start, end, and location are required'}), 400

    if weekday_mode and weekday_mode not in {'all', 'custom', 'none'}:
        return jsonify({'success': False, 'error': 'weekday_mode must be all, custom, or none'}), 400

    hour_start_val, hour_start_error = _parse_local_time_bound(hour_start, label='hour_start')
    if hour_start_error:
        return jsonify({'success': False, 'error': hour_start_error}), 400
    hour_end_val, hour_end_error = _parse_local_time_bound(hour_end, label='hour_end')
    if hour_end_error:
        return jsonify({'success': False, 'error': hour_end_error}), 400
    try:
        step = int(step_minutes) if step_minutes not in (None, '', 'null') else 60
    except Exception:
        return jsonify({'success': False, 'error': 'step_minutes must be an integer >= 1'}), 400

    if hour_start_val is not None and hour_end_val is not None and hour_start_val > hour_end_val:
        return jsonify({'success': False, 'error': 'hour_end must be after hour_start'}), 400

    try:
        sdt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        edt = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid start/end'}), 400
    if edt <= sdt:
        return jsonify({'success': False, 'error': 'End must be after start'}), 400

    # Ensure location is known (best-effort)
    try:
        coords = _ensure_coords_for_location(location)
        if coords is None:
            raise ValueError('Unknown location')
    except Exception:
        return jsonify({'success': False, 'error': 'Unable to resolve location'}), 400

    try:
        sdt, start_tz = _normalize_manual_datetime(
            start,
            timezone_name=timezone_name,
            location=location,
        )
        edt, _ = _normalize_manual_datetime(
            end,
            timezone_name=(start_tz or timezone_name),
            location=location,
        )
        if sdt is None or edt is None:
            raise ValueError('Missing start/end')
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid start/end'}), 400
    validated_total_steps, bounds_error = _validate_stream_scan_bounds(sdt, edt, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400

    # Gender parameter validation (informational only)
    if matter in {'conception', 'fertility'}:
        g_raw = (request.args.get('gender') or '').strip().lower()
        if g_raw and g_raw not in {'male', 'boy', 'masculine', 'female', 'girl', 'feminine'}:
            return jsonify({'success': False, 'error': 'gender must be male or female when provided'}), 400

    if matter == 'marriage':
        if marriage_algorithm not in {'alpha', 'beta'}:
            return jsonify({'success': False, 'error': 'marriage_algorithm must be alpha or beta'}), 400
        if marriage_algorithm == 'beta':
            participant_a_snap_id = (request.args.get('participant_a_snap_id') or '').strip()
            participant_b_snap_id = (request.args.get('participant_b_snap_id') or '').strip()
            if not participant_a_snap_id or not participant_b_snap_id:
                return jsonify({'success': False, 'error': 'Beta marriage requires participant_a_snap_id and participant_b_snap_id'}), 400
            if participant_a_snap_id == participant_b_snap_id:
                return jsonify({'success': False, 'error': 'Beta marriage requires two different participant snaps'}), 400
            house = request.args.get('house_system_code') or None
            try:
                _bundle_from_snap_id(participant_a_snap_id, house_system_code=house, missing_error='Participant A snap not found')
                _bundle_from_snap_id(participant_b_snap_id, house_system_code=house, missing_error='Participant B snap not found')
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
    if matter == 'business':
        if business_algorithm not in {'alpha', 'beta'}:
            return jsonify({'success': False, 'error': 'business_algorithm must be alpha or beta'}), 400
        if business_algorithm == 'beta':
            if not unique_participant_snap_ids:
                return jsonify({'success': False, 'error': 'Beta business requires at least one participant_snap_id'}), 400
            if len(unique_participant_snap_ids) != len(participant_snap_ids):
                return jsonify({'success': False, 'error': 'Beta business requires unique participant snaps'}), 400
            house = request.args.get('house_system_code') or None
            try:
                for idx, snap_id in enumerate(unique_participant_snap_ids, start=1):
                    _bundle_from_snap_id(
                        snap_id,
                        house_system_code=house,
                        missing_error=f'Business participant {idx} snap not found',
                    )
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400

    return jsonify({'success': True})


@astro_clock_bp.route('/election/suggest/stream', methods=['GET'])
def election_suggest_stream():
    """Stream election suggestions over a time window via SSE.

    Computes a score at each step and emits a final result with top items.
    """
    matter = (request.args.get('matter') or 'marriage').strip().lower()
    marriage_algorithm = (request.args.get('marriage_algorithm') or 'alpha').strip().lower()
    business_algorithm = (request.args.get('business_algorithm') or 'alpha').strip().lower()
    start = request.args.get('start')
    end = request.args.get('end')
    location = request.args.get('location')
    timezone_name = request.args.get('timezone')
    house_system_code = request.args.get('house_system_code') or None
    step = int(request.args.get('step_minutes', '60') or 60)
    limit = int(request.args.get('limit', '15') or 15)
    include_series = (request.args.get('include_series', '1').lower() in {'1', 'true', 'yes'})
    natal_snap = request.args.get('natal_snap_id')
    natal_datetime = request.args.get('natal_datetime')
    natal_location = request.args.get('natal_location')
    participant_a_snap_id = (request.args.get('participant_a_snap_id') or '').strip()
    participant_b_snap_id = (request.args.get('participant_b_snap_id') or '').strip()
    participant_snap_ids = [str(item).strip() for item in request.args.getlist('participant_snap_id') if str(item).strip()]
    unique_participant_snap_ids = list(dict.fromkeys(participant_snap_ids))
    business_beta_display_mode = (request.args.get('business_beta_display_mode') or 'total').strip().lower()
    business_beta_scope = (request.args.get('business_beta_scope') or 'all').strip().lower()
    business_beta_current_line_id = (request.args.get('business_beta_current_line_id') or '').strip()
    business_beta_selected_line_ids = [
        str(item).strip()
        for item in request.args.getlist('business_beta_selected_line_id')
        if str(item).strip()
    ]
    business_beta_level_percent = _parse_business_beta_level_percent(
        request.args.get('business_beta_level_percent', str(_BUSINESS_BETA_EXTRACTION_LEVEL_DEFAULT))
    )
    include_sr_lr = (request.args.get('include_sr_lr','0').lower() in {'1','true','yes'})
    # Optional filters: weekdays and hour ranges
    weekday_mode = (request.args.get('weekday_mode') or '').strip().lower()
    weekdays_raw = [w.strip().lower() for w in request.args.getlist('weekday') if str(w).strip()]
    hour_start = request.args.get('hour_start')
    hour_end = request.args.get('hour_end')
    hour_start, hour_start_error = _parse_local_time_bound(hour_start, label='hour_start')
    hour_end, hour_end_error = _parse_local_time_bound(hour_end, label='hour_end')

    if not (start and end and location):
        return jsonify({'success': False, 'error': 'start, end, and location are required'}), 400
    if matter == 'marriage' and marriage_algorithm not in {'alpha', 'beta'}:
        return jsonify({'success': False, 'error': 'marriage_algorithm must be alpha or beta'}), 400
    if matter == 'business' and business_algorithm not in {'alpha', 'beta'}:
        return jsonify({'success': False, 'error': 'business_algorithm must be alpha or beta'}), 400
    if matter == 'business' and business_algorithm == 'beta':
        if business_beta_display_mode not in _BUSINESS_BETA_EXTRACTION_MODES:
            return jsonify({'success': False, 'error': 'business_beta_display_mode must be total or detail'}), 400
        if business_beta_scope not in _BUSINESS_BETA_EXTRACTION_SCOPES:
            return jsonify({'success': False, 'error': 'business_beta_scope must be all, current, or selected'}), 400
    if weekday_mode and weekday_mode not in {'all', 'custom', 'none'}:
        return jsonify({'success': False, 'error': 'weekday_mode must be all, custom, or none'}), 400
    if hour_start_error:
        return jsonify({'success': False, 'error': hour_start_error}), 400
    if hour_end_error:
        return jsonify({'success': False, 'error': hour_end_error}), 400
    if hour_start is not None and hour_end is not None and hour_start > hour_end:
        return jsonify({'success': False, 'error': 'hour_end must be after hour_start'}), 400

    # Choose model scorer
    from election import (
        score_marriage_election, score_marriage_beta_election, score_surgery_election, score_contract_election,
        score_business_election, score_business_beta_election, score_journey_election, score_haircut_election,
        score_viral_content_election, score_legal_election, score_battle_election,
        score_conception_election, score_beautification_election,
    )
    def _scorer(cd: Dict[str,Any], opts: Dict[str,Any]):
        natal_hits = opts.get('natal_hits')
        if matter == 'surgery':
            return score_surgery_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'contract':
            return score_contract_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'business':
            if business_algorithm == 'beta':
                return score_business_beta_election(cd, natal_hits=natal_hits, options=opts)
            return score_business_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'journey':
            return score_journey_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'haircut':
            return score_haircut_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'legal':
            return score_legal_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'beautification':
            return score_beautification_election(cd, natal_hits=natal_hits, options=opts)
        if matter in {'viral', 'viral_content', 'viral-content', 'viralpublish'}:
            return score_viral_content_election(cd, natal_hits=natal_hits, options=opts)
        if matter in {'battle', 'combat', 'war'}:
            return score_battle_election(cd, natal_hits=natal_hits, options=opts)
        if matter in {'conception', 'fertility'}:
            return score_conception_election(cd, natal_hits=natal_hits, options=opts)
        if matter == 'marriage' and marriage_algorithm == 'beta':
            return score_marriage_beta_election(cd, natal_hits=natal_hits, options=opts)
        return score_marriage_election(cd, natal_hits=natal_hits, options=opts)

    # Natal context (optional) for enhancements
    natal_cd = None
    participant_mode_active = (
        (matter == 'marriage' and marriage_algorithm == 'beta')
        or (matter == 'business' and business_algorithm == 'beta')
    )
    if not participant_mode_active and (natal_snap or natal_datetime or natal_location):
        try:
            natal_cd, _nm = _natal_from_query(request.args)
        except Exception:
            natal_cd = None
    # Additional natal helpers
    natal_cusps = None
    try:
        if natal_cd and isinstance(natal_cd, dict):
            hc = natal_cd.get('houses') or natal_cd.get('house_cusps')
            if isinstance(hc, list) and len(hc) >= 12:
                natal_cusps = hc[:12]
    except Exception:
        natal_cusps = None

    # SR/LR containers (computed after we parse start/end below)
    sr_windows: List[Tuple[datetime, datetime]] = []
    lr_list: List[datetime] = []

    participant_a_bundle: Optional[Dict[str, Any]] = None
    participant_b_bundle: Optional[Dict[str, Any]] = None
    participant_a_cd: Optional[Dict[str, Any]] = None
    participant_b_cd: Optional[Dict[str, Any]] = None
    business_participants: List[Dict[str, Any]] = []
    if matter == 'marriage' and marriage_algorithm == 'beta':
        if not participant_a_snap_id or not participant_b_snap_id:
            return jsonify({'success': False, 'error': 'Beta marriage requires participant_a_snap_id and participant_b_snap_id'}), 400
        if participant_a_snap_id == participant_b_snap_id:
            return jsonify({'success': False, 'error': 'Beta marriage requires two different participant snaps'}), 400
        try:
            participant_a_bundle = _bundle_from_snap_id(
                participant_a_snap_id,
                house_system_code=house_system_code,
                missing_error='Participant A snap not found',
            )
            participant_b_bundle = _bundle_from_snap_id(
                participant_b_snap_id,
                house_system_code=house_system_code,
                missing_error='Participant B snap not found',
            )
            participant_a_bundle['chart_data'] = _extend_chart_data_for_marriage_beta(
                participant_a_bundle.get('chart_data') or {},
                participant_a_bundle.get('meta') or {},
                include_moon_day=False,
            )
            participant_b_bundle['chart_data'] = _extend_chart_data_for_marriage_beta(
                participant_b_bundle.get('chart_data') or {},
                participant_b_bundle.get('meta') or {},
                include_moon_day=False,
            )
            participant_a_cd = participant_a_bundle.get('chart_data') or {}
            participant_b_cd = participant_b_bundle.get('chart_data') or {}
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
    if matter == 'business' and business_algorithm == 'beta':
        if not unique_participant_snap_ids:
            return jsonify({'success': False, 'error': 'Beta business requires at least one participant_snap_id'}), 400
        if len(unique_participant_snap_ids) != len(participant_snap_ids):
            return jsonify({'success': False, 'error': 'Beta business requires unique participant snaps'}), 400
        try:
            for idx, snap_id in enumerate(unique_participant_snap_ids, start=1):
                snap = _snaps().get(snap_id) or {}
                bundle = _bundle_from_snap_id(
                    snap_id,
                    house_system_code=house_system_code,
                    missing_error=f'Business participant {idx} snap not found',
                )
                bundle['chart_data'] = _extend_chart_data_for_marriage_beta(
                    bundle.get('chart_data') or {},
                    bundle.get('meta') or {},
                    include_moon_day=False,
                )
                label = (
                    str(snap.get('label') or '').strip()
                    or str(snap.get('location') or '').strip()
                    or f'Founder {idx}'
                )
                business_participants.append(
                    {
                        'snap_id': snap_id,
                        'label': label,
                        'chart_data': bundle.get('chart_data') or {},
                        'meta': bundle.get('meta') or {},
                        'precision_class': 'certified',
                        'precision_safe': True,
                        'precision_source': 'business_beta_certified_override',
                    }
                )
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

    # Resolve timezone from location if missing
    tz = timezone_name
    if not tz:
        coords = _ensure_coords_for_location(location)
        if coords:
            lat, lon = coords
            try:
                tz = _tz_instance().get_timezone_for_location(lat, lon)
            except Exception:
                tz = None

    # Iterate window
    try:
        sdt, start_tz = _normalize_manual_datetime(
            start,
            timezone_name=tz,
            location=location,
        )
        edt, end_tz = _normalize_manual_datetime(
            end,
            timezone_name=(start_tz or tz),
            location=location,
        )
        if sdt is None or edt is None:
            raise ValueError('Missing start/end')
        if not tz:
            tz = end_tz or start_tz or tz
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid start/end'}), 400
    if edt <= sdt:
        return jsonify({'success': False, 'error': 'End must be after start'}), 400
    scan_zone = None
    try:
        scan_zone = ZoneInfo(tz) if tz else ZoneInfo('UTC')
        if not tz:
            tz = 'UTC'
    except Exception:
        scan_zone = ZoneInfo('UTC')
        tz = 'UTC'
    validated_total_steps, bounds_error = _validate_stream_scan_bounds(sdt, edt, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
    try:
        series_limit = int(request.args.get('series_limit', str(_STREAM_BUFFER_ROWS)) or _STREAM_BUFFER_ROWS)
    except Exception:
        series_limit = _STREAM_BUFFER_ROWS
    series_limit = max(25, min(series_limit, _STREAM_MAX_STEPS))
    top_buffer_limit = max(50, limit * 8)

    # Now that start/end are parsed, compute SR/LR context if requested and natal provided
    try:
        if include_sr_lr and natal_cd and isinstance(natal_cd, dict):
            nat_pl = natal_cd.get('planets') or {}
            nat_sun = None; nat_moon = None
            try:
                if isinstance(nat_pl, dict):
                    rowS = nat_pl.get('Sun'); rowM = nat_pl.get('Moon')
                    if isinstance(rowS, dict) and rowS.get('longitude') is not None:
                        nat_sun = float(rowS.get('longitude'))
                    if isinstance(rowM, dict) and rowM.get('longitude') is not None:
                        nat_moon = float(rowM.get('longitude'))
                elif isinstance(nat_pl, list):
                    for r in nat_pl:
                        if not isinstance(r, dict):
                            continue
                        nm = str(r.get('planet') or '')
                        if nm == 'Sun' and r.get('longitude') is not None:
                            nat_sun = float(r.get('longitude'))
                        elif nm == 'Moon' and r.get('longitude') is not None:
                            nat_moon = float(r.get('longitude'))
            except Exception:
                nat_sun = None; nat_moon = None
            # Compute SR (±3 days) for all years covered by scan window
            if nat_sun is not None:
                try:
                    from context_layers import compute_solar_return_timestamp
                    sdt_local = sdt.astimezone(scan_zone)
                    edt_local = edt.astimezone(scan_zone)
                    y0 = sdt_local.year; y1 = edt_local.year
                    if y1 < y0:
                        y0, y1 = y1, y0
                    from datetime import timedelta as _td
                    for yy in range(y0, y1+1):
                        ts_sr = compute_solar_return_timestamp(nat_sun, yy)
                        if ts_sr is not None:
                            a = ts_sr - _td(days=3)
                            b = ts_sr + _td(days=3)
                            sr_windows.append((a, b))
                except Exception:
                    sr_windows = []
            # Compute LR times for all years covered by window
            if nat_moon is not None:
                try:
                    from context_layers import compute_lunar_return_timestamps
                    sdt_local = sdt.astimezone(scan_zone)
                    edt_local = edt.astimezone(scan_zone)
                    y0 = sdt_local.year; y1 = edt_local.year
                    if y1 < y0:
                        y0, y1 = y1, y0
                    lst: List[datetime] = []
                    for yy in range(y0, y1+1):
                        lst.extend(list(compute_lunar_return_timestamps(nat_moon, yy) or []))
                    lr_list = sorted(lst)
                except Exception:
                    lr_list = []
    except Exception:
        sr_windows = []; lr_list = []

    from datetime import timedelta
    step_td = timedelta(minutes=max(1, step))
    eng = _engine_instance()
    # Model-specific options from query
    def _model_options():
        opts: Dict[str, Any] = {}
        # Common toggles
        if request.args.get('include_fixed_stars', '').lower() in {'1','true','yes'}:
            opts['include_fixed_stars'] = True
        if request.args.get('include_lunation_screen', '').lower() in {'1','true','yes'}:
            opts['include_lunation_screen'] = True
        # Contract
        pref_fixed_raw = request.args.get('prefer_fixed_asc')
        if pref_fixed_raw is not None:
            val = str(pref_fixed_raw).strip().lower()
            opts['prefer_fixed_asc'] = val in {'1','true','yes'}
        if request.args.get('saturn_binding_ok') is not None:
            sbo = request.args.get('saturn_binding_ok')
            opts['saturn_binding_ok'] = False if str(sbo).lower() in {'0','false','no'} else True
        try:
            mdd = request.args.get('min_mercury_direct_days')
            if mdd is not None:
                opts['min_mercury_direct_days'] = int(mdd)
        except Exception:
            pass
        cm = request.args.get('contract_mode')
        if cm: opts['contract_mode'] = cm
        # Business
        if request.args.get('include_traditional_timing','').lower() in {'1','true','yes'}:
            opts['include_traditional_timing'] = True
        bm = request.args.get('business_mode')
        if bm: opts['business_mode'] = bm
        if request.args.get('emphasize_commerce','').lower() in {'1','true','yes'}:
            opts['emphasize_commerce'] = True
        # Journey
        jt = request.args.get('journey_type')
        if jt: opts['journey_type'] = jt
        # Conception sex focus
        if matter in {'conception', 'fertility'}:
            g_raw = (request.args.get('gender') or '').strip().lower()
            if g_raw in {'male', 'boy', 'masculine'}:
                opts['gender'] = 'male'
            elif g_raw in {'female', 'girl', 'feminine'}:
                opts['gender'] = 'female'
        # Battle
        if matter in {'battle', 'combat', 'war'}:
            act = request.args.get('action_type') or request.args.get('battle_action')
            if act:
                opts['action_type'] = act
        # Haircut
        if matter == 'haircut':
            hg = request.args.get('hair_goal')
            if hg: opts['hair_goal'] = hg
        if matter == 'beautification':
            bp_vals: List[str] = []
            bp_param = request.args.get('body_parts')
            if bp_param:
                bp_vals.extend([s.strip() for s in bp_param.split(',') if s.strip()])
            for item in request.args.getlist('body_part'):
                if isinstance(item, str) and item.strip():
                    bp_vals.append(item.strip())
            if bp_vals:
                opts['body_parts'] = bp_vals
            bs_vals: List[str] = []
            bs_param = request.args.get('body_signs')
            if bs_param:
                bs_vals.extend([s.strip() for s in bs_param.split(',') if s.strip()])
            for item in request.args.getlist('body_sign'):
                if isinstance(item, str) and item.strip():
                    bs_vals.append(item.strip())
            if bs_vals:
                opts['body_signs'] = bs_vals
            pt = request.args.get('procedure_type')
            if pt:
                opts['procedure_type'] = pt
        if matter == 'legal':
            la = request.args.get('legal_action')
            if la:
                opts['legal_action'] = la
        # Surgery
        sg = request.args.get('surgery_sign')
        if sg: opts['surgery_sign'] = sg
        proc = request.args.get('procedure')
        if proc: opts['procedure'] = proc
        if request.args.get('strict_surgery_never_rules') is not None:
            ssnr = request.args.get('strict_surgery_never_rules')
            opts['strict_surgery_never_rules'] = False if str(ssnr).lower() in {'0','false','no'} else True
        # Surgery: strict eclipse window options
        if request.args.get('strict_eclipse_window','').lower() in {'1','true','yes'}:
            opts['strict_eclipse_window'] = True
        try:
            edeg = request.args.get('eclipse_window_deg') or request.args.get('strict_eclipse_deg')
            if edeg is not None:
                opts['eclipse_window_deg'] = float(edeg)
        except Exception:
            pass
        # Natal supports
        if natal_cd is not None:
            opts['natal_cd'] = natal_cd
        if natal_cusps is not None:
            opts['natal_cusps'] = natal_cusps
        if matter == 'marriage':
            opts['marriage_algorithm'] = marriage_algorithm
        if matter == 'business':
            opts['business_algorithm'] = business_algorithm
            if business_algorithm == 'beta':
                opts['include_traditional_timing'] = True
                opts.pop('include_fixed_stars', None)
                opts.pop('include_lunation_screen', None)
                opts.pop('emphasize_commerce', None)
                opts.pop('business_mode', None)
                opts['business_beta_certified_participants'] = True
        if participant_a_cd is not None:
            opts['participant_a_cd'] = participant_a_cd
            opts['participant_a_meta'] = (participant_a_bundle or {}).get('meta') or {}
            opts['participant_a_snap_id'] = participant_a_snap_id
        if participant_b_cd is not None:
            opts['participant_b_cd'] = participant_b_cd
            opts['participant_b_meta'] = (participant_b_bundle or {}).get('meta') or {}
            opts['participant_b_snap_id'] = participant_b_snap_id
        if business_participants:
            opts['business_participants'] = business_participants
            opts['participant_snap_ids'] = [item.get('snap_id') for item in business_participants if item.get('snap_id')]
        # SR/LR context if requested
        if include_sr_lr and natal_cd is not None:
            if sr_windows:
                opts['sr_windows'] = sr_windows
            if lr_list:
                opts['lr_list'] = lr_list
        if tz:
            opts['timezone'] = tz
        return opts

    # Weekday map (Python Mon=0..Sun=6); input uses sun..sat
    weekday_filter_active = False
    weekday_idx: Set[int] = set()
    if weekday_mode == 'none':
        weekday_filter_active = True
    elif weekday_mode == 'custom' or weekdays_raw:
        m = {'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
        weekday_idx = set(m.get(w, None) for w in weekdays_raw)
        weekday_idx.discard(None)
        weekday_filter_active = True

    def _generate():
        attempted = 0
        kept_total = 0
        all_series_rows: List[Dict[str, Any]] = []
        top_candidates: List[Dict[str, Any]] = []
        series_dropped = 0
        t = sdt
        total_steps = validated_total_steps or 1
        # Prepare planetary hours calculator if traditional timing requested
        ph_calc = None
        coords = None
        try:
            if (
                include_sr_lr
                or request.args.get('include_traditional_timing','').lower() in {'1','true','yes'}
                or (matter == 'business' and business_algorithm == 'beta')
            ):
                coords = _ensure_coords_for_location(location)
                if coords:
                    lat, lon = coords
                    ph_calc = _ph_instance(lat, lon)
        except Exception:
            ph_calc = None
        while t <= edt:
            # Filter by weekday/hour if provided (use local time at tz)
            try:
                t_local = t.astimezone(scan_zone)
                minute_of_day = (t_local.hour * 60) + t_local.minute
                if weekday_filter_active and (not weekday_idx or t_local.weekday() not in weekday_idx):
                    # Progress update even if skipped
                    yield f"data: {json.dumps({'type':'progress','progress':min(1.0, max(0.0, ((t - sdt).total_seconds() / ((edt - sdt).total_seconds() or 1))))})}\n\n"
                    t = t + step_td
                    continue
                if (hour_start is not None) and (minute_of_day < hour_start):
                    yield f"data: {json.dumps({'type':'progress','progress':min(1.0, max(0.0, ((t - sdt).total_seconds() / ((edt - sdt).total_seconds() or 1))))})}\n\n"
                    t = t + step_td
                    continue
                if (hour_end is not None) and (minute_of_day > hour_end):
                    yield f"data: {json.dumps({'type':'progress','progress':min(1.0, max(0.0, ((t - sdt).total_seconds() / ((edt - sdt).total_seconds() or 1))))})}\n\n"
                    t = t + step_td
                    continue
            except Exception:
                pass
            attempted += 1
            # Compute chart at t for location
            try:
                cd, meta = _compute_chart_for(t.isoformat(), location, tz, house_system_code)
                if (
                    (matter == 'marriage' and marriage_algorithm == 'beta')
                    or (matter == 'business' and business_algorithm == 'beta')
                ):
                    cd = _extend_chart_data_for_marriage_beta(
                        cd,
                        meta,
                        include_moon_day=True,
                    )
                opts = _model_options()
                opts['current_timestamp'] = t
                opts['event_meta'] = meta
                # Attach planetary day/hour rulers when requested and available
                try:
                    if opts.get('include_traditional_timing') and ph_calc is not None and tz:
                        # compute day ruler and current planetary hour at local time
                        t_local = t.astimezone(scan_zone)
                        daily = ph_calc.calculate_daily_hours(t_local.date())
                        cur_hour = ph_calc.get_current_planetary_hour(t_local)
                        if daily and getattr(daily, 'day_ruler', None):
                            dr = getattr(daily.day_ruler, 'value', None) or str(daily.day_ruler)
                            if dr: opts['day_ruler'] = dr
                        if cur_hour and getattr(cur_hour, 'ruling_planet', None):
                            hr = getattr(cur_hour.ruling_planet, 'value', None) or str(cur_hour.ruling_planet)
                            if hr: opts['hour_ruler'] = hr
                except Exception:
                    pass
                # Directions/transits proxy: include top natal transit hits at t when natal provided & requested
                if include_sr_lr and natal_cd is not None:
                    try:
                        from transits_morin import compute_morin_transits_to_natal
                        hits = compute_morin_transits_to_natal(
                            natal_cd,
                            t.isoformat(),
                            dt_hours=0.5,
                            include_modern=False,
                            natal_include_modern=False,
                            include_cusps=False,
                            include_antiscia=False,
                            include_lots=False,
                            focus_houses=None,
                            focus_planets=None,
                            sensitive_houses=None,
                            sensitive_planets=None,
                            observer_location=location,
                            observer_timezone=tz,
                        )
                        # Limit to top ~12 to bound payload
                        opts['natal_hits'] = hits[:12] if isinstance(hits, list) else []
                    except Exception:
                        opts['natal_hits'] = []
                sc = _scorer(cd, opts)
                # Normalize score object (dataclass Score: value/tags)
                score_val = 0.0
                tags = []
                pros = []
                cautions = []
                line_rows = []
                try:
                    if sc is None:
                        score_val = 0.0; tags = []; pros = []; cautions = []; line_rows = []
                    elif isinstance(sc, (int, float)):
                        score_val = float(sc); tags = []; pros = []; cautions = []; line_rows = []
                    elif isinstance(sc, dict):
                        score_val = float(sc.get('value') if sc.get('value') is not None else sc.get('score') or 0.0)
                        tags = list(sc.get('tags') or [])
                        pros = list(sc.get('pros') or [])
                        cautions = list(sc.get('cautions') or [])
                        line_rows = [dict(item) for item in list(sc.get('lines') or []) if isinstance(item, dict)]
                    else:
                        # dataclass: Score(value, tags, pros?, cautions?)
                        v = getattr(sc, 'value', None)
                        if v is None:
                            v = getattr(sc, 'score', 0.0)
                        score_val = float(v or 0.0)
                        tags = list(getattr(sc, 'tags', []) or [])
                        pros = list(getattr(sc, 'pros', []) or [])
                        cautions = list(getattr(sc, 'cautions', []) or [])
                        line_rows = [dict(item) for item in list(getattr(sc, 'lines', []) or []) if isinstance(item, dict)]
                except Exception:
                    score_val = 0.0; tags = []; pros = []; cautions = []; line_rows = []
                row = {
                    'timestamp': t.isoformat(),
                    'timestamp_local': meta.get('timestamp'),
                    'score': score_val,
                    'tags': tags,
                }
                if pros:
                    row['pros'] = pros
                if cautions:
                    row['cautions'] = cautions
                if line_rows:
                    row['lines'] = line_rows
                kept_total += 1
                top_candidates.append(row)
                if len(top_candidates) > top_buffer_limit:
                    top_candidates = sorted(
                        top_candidates,
                        key=lambda r: float(r.get('score') or 0.0),
                        reverse=True,
                    )[:top_buffer_limit]
                if include_series or (matter == 'business' and business_algorithm == 'beta'):
                    all_series_rows.append(row)
            except Exception:
                # Skip step on error
                pass
            # Progress event
            try:
                prog = min(1.0, max(0.0, ((t - sdt).total_seconds() / ((edt - sdt).total_seconds() or 1))))
            except Exception:
                prog = 0.0
            yield f"data: {json.dumps({'type':'progress','progress':prog})}\n\n"
            t = t + step_td
        extraction_payload: Optional[Dict[str, Any]] = None
        series_source_rows = list(all_series_rows)
        if matter == 'business' and business_algorithm == 'beta':
            extraction_payload = _extract_business_beta_periods(
                series_source_rows,
                step_td=step_td,
                display_mode=business_beta_display_mode,
                scope=business_beta_scope,
                level_percent=business_beta_level_percent,
                current_line_id=business_beta_current_line_id or None,
                selected_line_ids=business_beta_selected_line_ids,
            )
            series_source_rows = list(extraction_payload.get('rows') or [])
            top = list(extraction_payload.get('top_rows') or [])[:limit]
        else:
            top = sorted(top_candidates, key=lambda r: float(r.get('score') or 0.0), reverse=True)[:limit]

        series_rows: List[Dict[str, Any]] = []
        if include_series:
            series_rows = _reduce_series_rows(
                series_source_rows,
                series_limit,
                pinned_timestamps=[str(row.get('timestamp') or '') for row in top],
            )
            series_dropped = max(0, len(series_source_rows) - len(series_rows))
        payload = {
            'top': top,
            'matter': matter,
            'location': location,
            'timezone': tz,
            'stats': {
                'attempted': attempted,
                'kept_total': kept_total,
                'failed': attempted - kept_total,
                'series_total': len(series_source_rows) if include_series else 0,
                'series_retained': len(series_rows) if include_series else 0,
                'series_dropped': series_dropped if include_series else 0,
            },
        }
        if include_series:
            payload['series'] = series_rows
        if matter == 'marriage':
            payload['marriage_algorithm'] = marriage_algorithm
            if marriage_algorithm == 'beta':
                payload['participants'] = {
                    'participant_a_snap_id': participant_a_snap_id,
                    'participant_b_snap_id': participant_b_snap_id,
                }
        if matter == 'business':
            payload['business_algorithm'] = business_algorithm
            if business_algorithm == 'beta':
                payload['participants'] = {
                    'participant_snap_ids': [item.get('snap_id') for item in business_participants if item.get('snap_id')],
                    'items': [
                        {
                            'snap_id': item.get('snap_id'),
                            'label': item.get('label'),
                        }
                        for item in business_participants
                    ],
                    'certified_assumption': True,
                    'precision_note': 'Selected founder-owner charts are treated as certified for Ascendant-based business beta fit in this scan.',
                }
                if extraction_payload is not None:
                    payload['business_beta_extraction'] = {
                        'display_mode': extraction_payload.get('display_mode'),
                        'scope': extraction_payload.get('scope'),
                        'level_percent': extraction_payload.get('level_percent'),
                        'selected_line_ids': extraction_payload.get('selected_line_ids') or [],
                        'current_line_id': (extraction_payload.get('selected_line_ids') or [None])[0]
                        if extraction_payload.get('scope') == 'current'
                        else None,
                        'line_stats': extraction_payload.get('line_stats') or [],
                        'passing_row_count': extraction_payload.get('passing_row_count') or 0,
                        'period_count': extraction_payload.get('period_count') or 0,
                        'certified_assumption': True,
                    }
                    payload['business_beta_periods'] = extraction_payload.get('periods') or []
        yield f"data: {json.dumps({'type':'done','data':payload})}\n\n"

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    return Response(stream_with_context(_generate()), headers=headers)


# ---------- Research Mode (Dev-only Lotto analysis) ----------

def _research_progress_payload(session_id: str) -> Dict[str, Any]:
    with _research_lock:
        sess = _research_sessions.get(session_id) or {}
        done = int(sess.get('done') or 0)
        total = int(sess.get('total') or 0)
        ready = bool(sess.get('ready'))
        percent = 1.0 if ready and total else (float(done) / float(total) if total else 0.0)
        payload = {
            'ready': ready,
            'done': done,
            'total': total,
            'percent': percent,
        }
        if sess.get('workers') is not None:
            payload['workers'] = sess.get('workers')
        if sess.get('source'):
            payload['source'] = sess.get('source')
        if sess.get('error'):
            payload['error'] = sess.get('error')
        if sess.get('aborted'):
            payload['aborted'] = True
        return payload


def _load_cached_rows(cache_path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(cache_path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            rows = data.get('rows') or []
            if isinstance(rows, list):
                return rows
    except Exception:
        pass
    return []


def _count_csv_rows(csv_path: Path) -> int:
    try:
        with csv_path.open(encoding='cp1255', newline='') as f:
            reader = csv.reader(f)
            # subtract header row
            return max(0, sum(1 for _ in reader) - 1)
    except Exception:
        return 0


def _compute_chart_for_research(dt_iso: str, location: str, tz_name: str, eng: Optional[AstroClockEngine], coords: Optional[Tuple[float, float]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    loc = location or _research_default_location
    tz = _resolve_timezone_for_context(tz_name or _research_default_tz, loc) or _research_default_tz
    custom = None
    try:
        custom, normalized_tz = _normalize_manual_datetime(
            dt_iso,
            timezone_name=tz,
            location=loc,
        )
        tz = normalized_tz or tz
    except Exception:
        custom = None
    engine = eng or AstroClockEngine()
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location=loc,
        custom_time=custom,
        timezone=tz,
        house_system_code=getattr(engine.settings, 'house_system_code', None),
    )
    if coords is None:
        coords = _ensure_coords_for_location(loc)
    if coords:
        settings.latitude, settings.longitude = coords
    data = engine.get_current_data(settings=settings)
    cd = _extract_chart_data_from_result(data.chart_result if hasattr(data, 'chart_result') else {})
    try:
        ts_local = _localize(data.timestamp, tz)
    except Exception:
        ts_local = data.timestamp
        try:
            if ts_local.tzinfo is None:
                ts_local = ts_local.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    meta = {
        'timestamp': ts_local.isoformat() if ts_local else dt_iso,
        'location': loc,
        'timezone': tz,
    }
    return cd, meta


def _extract_planet_directions(chart_data: Dict[str, Any]) -> Dict[str, str]:
    """Return {'Planet': 'D'|'R'} using retrograde/speed hints; defaults to 'D'."""
    directions: Dict[str, str] = {}
    planets = chart_data.get('planets') or {}
    items: List[Dict[str, Any]] = []
    if isinstance(planets, dict):
        items = [dict(v, planet=k) for k, v in planets.items() if isinstance(v, dict)]
    elif isinstance(planets, list):
        items = [p for p in planets if isinstance(p, dict)]
    for p in items:
        name = str(p.get('planet') or '').strip()
        if not name:
            continue
        ret = p.get('retrograde')
        if ret is None and p.get('speed') is not None:
            try:
                ret = float(p.get('speed')) < 0
            except Exception:
                ret = False
        directions[name] = 'R' if ret else 'D'
    return directions


def _compute_final_dispositors(planet_signs: Dict[str, str]) -> Dict[str, str]:
    """Compute simple classical final dispositors for each planet."""
    rulers = {
        'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon',
        'Leo': 'Sun', 'Virgo': 'Mercury', 'Libra': 'Venus', 'Scorpio': 'Mars',
        'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter',
    }
    result: Dict[str, str] = {}
    for planet, sign in (planet_signs or {}).items():
        current = planet
        seen = set()
        cur_sign = sign
        final = None
        for _ in range(len(planet_signs) + 2):
            if current in seen:
                final = current
                break
            seen.add(current)
            ruler = rulers.get(cur_sign)
            if not ruler:
                final = current
                break
            final = ruler
            # Move to ruler's sign if available, else stop
            next_sign = planet_signs.get(ruler)
            if not next_sign:
                break
            current, cur_sign = ruler, next_sign
        if final:
            result[planet] = final
    return result


def _respect_order(balance: Dict[str, Any], order: List[str]) -> bool:
    if not balance or not order:
        return True
    vals = {k: float(balance.get(k, 0.0) or 0.0) for k in balance.keys()}
    for i in range(len(order) - 1):
        a, b = order[i], order[i + 1]
        if vals.get(a, 0.0) < vals.get(b, 0.0):
            return False
    return True


def _top_key(balance: Dict[str, Any]) -> Optional[str]:
    if not isinstance(balance, dict) or not balance:
        return None
    return max(balance.items(), key=lambda kv: float(kv[1] or 0.0))[0]


def _matches_filters(row: Dict[str, Any], filt: Dict[str, Any]) -> bool:
    if not filt:
        return True
    metrics = row.get('metrics') or {}
    # Element/modalities
    eb = metrics.get('element_balance') or {}
    mb = metrics.get('modality_balance') or {}
    if filt.get('topElement') and _top_key(eb) != filt.get('topElement'):
        return False
    for z in filt.get('zeroElements') or []:
        if float(eb.get(z, 0.0) or 0.0) > 0.0:
            return False
    if filt.get('topModality') and _top_key(mb) != filt.get('topModality'):
        return False
    for z in filt.get('zeroModalities') or []:
        if float(mb.get(z, 0.0) or 0.0) > 0.0:
            return False
    if filt.get('elementOrder') and not _respect_order(eb, filt.get('elementOrder')):
        return False
    if filt.get('modalityOrder') and not _respect_order(mb, filt.get('modalityOrder')):
        return False

    psigns = metrics.get('planet_signs') or {}
    pdeg = metrics.get('planet_deg_in_sign') or {}
    plon = metrics.get('planet_longitudes') or {}
    phouses = metrics.get('planet_houses') or {}
    house_rulers = metrics.get('house_rulers') or {}
    receptions = metrics.get('receptions') or {}
    pdir = metrics.get('planet_direction') or {}
    finals = metrics.get('final_dispositor')
    if not finals:
        finals = _compute_final_dispositors(psigns) if psigns else {}

    # Planet positions/sign/degree/abs longitude
    for pf in filt.get('positions') or []:
        planet = pf.get('planet')
        if not planet:
            continue
        sign_req = pf.get('sign')
        if sign_req and psigns.get(planet) != sign_req:
            return False
        if pf.get('min_deg') is not None:
            if float(pdeg.get(planet, -999)) < float(pf.get('min_deg')):
                return False
        if pf.get('max_deg') is not None:
            if float(pdeg.get(planet, 999)) > float(pf.get('max_deg')):
                return False
        if pf.get('lon_min') is not None:
            if float(plon.get(planet, -9999)) < float(pf.get('lon_min')):
                return False
        if pf.get('lon_max') is not None:
            if float(plon.get(planet, 9999)) > float(pf.get('lon_max')):
                return False
    # Planet in houses
    for hp in filt.get('housePositions') or []:
        planet = hp.get('planet')
        houses = hp.get('in') or hp.get('houses') or []
        if planet and houses:
            if int(phouses.get(planet, -1)) not in [int(h) for h in houses]:
                return False
    # Ruler in house filters
    for rh in filt.get('rulerInHouse') or []:
        cusp = str(rh.get('cusp'))
        target = int(rh.get('in_house')) if rh.get('in_house') is not None else None
        if cusp and target is not None:
            if int(house_rulers.get(cusp, -1)) != target:
                return False
    # Reception filters
    recs = receptions if isinstance(receptions, dict) else {}
    mutuals = recs.get('mutual') or []
    unilats = recs.get('top_unilateral') or []
    for pair in filt.get('receptions', {}).get('mutual_pairs') or []:
        a, b = pair[0], pair[1] if len(pair) > 1 else None
        if not a or not b:
            continue
        if not any(
            ((m.get('p1') == a and m.get('p2') == b) or (m.get('p1') == b and m.get('p2') == a))
            for m in mutuals if isinstance(m, dict)
        ):
            return False
    for uni in filt.get('receptions', {}).get('unilateral') or []:
        recv = uni.get('receiving')
        recd = uni.get('received')
        if not recv or not recd:
            continue
        if not any(
            (u.get('receiving') == recv and u.get('received') == recd)
            for u in unilats if isinstance(u, dict)
        ):
            return False
    # Direction filters
    for d in filt.get('directions') or []:
        planet = d.get('planet')
        desired = d.get('direction')
        if not planet or desired not in ('D', 'R', 'direct', 'retrograde'):
            continue
        val = pdir.get(planet) or 'D'
        if desired.lower().startswith('r'):
            if val != 'R':
                return False
        else:
            if val == 'R':
                return False
    # Final dispositor filters
    for fd in filt.get('finalDispositors') or []:
        planet = fd.get('planet')
        target = fd.get('final') or fd.get('dispositor')
        if planet and target:
            if finals.get(planet) != target:
                return False
    return True


def _build_distribution(all_rows: List[Dict[str, Any]], matched_rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    def _collect(rows: List[Dict[str, Any]]) -> Counter:
        c = Counter()
        for r in rows:
            vals = r.get(key) or []
            # For power numbers we only care about the first entry (power number)
            if key == 'power' and isinstance(vals, list) and vals:
                vals = [vals[0]]
            for v in vals:
                try:
                    n = int(v)
                    c[str(n)] += 1
                except Exception:
                    continue
        return c
    base = _collect(all_rows)
    inf = _collect(matched_rows)
    base_total = sum(base.values()) or 1
    inf_total = sum(inf.values()) or 1
    base_pct = {k: (v / base_total) for k, v in base.items()}
    inf_pct = {k: (v / inf_total) for k, v in inf.items()}
    return {
        'baseline': dict(base),
        'in_filter': dict(inf),
        'baseline_pct': base_pct,
        'in_filter_pct': inf_pct,
    }


def _start_research_compile(body: Dict[str, Any], force: bool = False) -> Tuple[str, Dict[str, Any]]:
    path = body.get('path') or 'backend/Lotto(10).csv'
    defaults = body.get('defaults') or {}
    time_str = defaults.get('time') or _research_default_time
    location = defaults.get('location') or _research_default_location
    tz_hint = defaults.get('timezone') or defaults.get('tz')
    row_limit = body.get('rowLimit')
    session_id = _research_session_id(path, time_str, location, row_limit)
    csv_path = _safe_research_path(path)
    cache_dir = _ensure_research_cache_dir()
    cache_path = cache_dir / f"{session_id}.json"

    if cache_path.exists() and not force:
        rows = _load_cached_rows(cache_path)
        with _research_lock:
            _research_sessions[session_id] = {
                'ready': True,
                'done': len(rows),
                'total': len(rows),
                'percent': 1.0,
                'workers': 0,
                'source': 'cache',
                'cache_path': str(cache_path),
            }
        return session_id, _research_progress_payload(session_id)

    # Avoid duplicate workers
    with _research_lock:
        sess = _research_sessions.get(session_id)
        if sess and sess.get('thread') and sess['thread'].is_alive():
            return session_id, _research_progress_payload(session_id)

    total_rows = _count_csv_rows(csv_path)
    with _research_lock:
        _research_sessions[session_id] = {
            'ready': False,
            'done': 0,
            'total': total_rows,
            'aborted': False,
            'workers': 1,
            'source': 'compiled',
            'cache_path': str(cache_path),
        }

    def _worker():
        eng = AstroClockEngine()
        t_obj = _parse_time_str(time_str)
        tz_name = tz_hint or _research_default_tz
        coords = _ensure_coords_for_location(location)
        if not coords and location.strip().lower() == _research_default_location.lower():
            coords = _research_default_coords
        try:
            if coords:
                guess = _tz_instance().get_timezone_for_location(coords[0], coords[1])
                if guess:
                    tz_name = guess
        except Exception:
            pass
        results: List[Dict[str, Any]] = []
        try:
            with csv_path.open(encoding='cp1255', newline='') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    with _research_lock:
                        sess = _research_sessions.get(session_id) or {}
                        if sess.get('aborted'):
                            break
                    if row_limit and len(results) >= int(row_limit):
                        break
                    date_val = row.get('תאריך') or row.get('date')
                    if not date_val:
                        continue
                    try:
                        d = datetime.strptime(date_val.strip(), "%d/%m/%Y").date()
                    except Exception:
                        continue
                    try:
                        t_local = datetime.combine(d, t_obj, tzinfo=ZoneInfo(tz_name))
                    except Exception:
                        t_local = datetime.combine(d, t_obj).replace(tzinfo=timezone.utc)
                    iso_local = t_local.isoformat()
                    numbers = [row.get(str(i), '').strip() for i in range(1, 7)]
                    power_vals = [row.get('power number', '').strip(), (row.get('Winner') or row.get('Winner2') or '').strip()]
                    try:
                        chart_data, meta = _compute_chart_for_research(iso_local, location, tz_name, eng, coords=coords)
                        metrics = compute_metrics(chart_data, meta.get('timestamp'), special_degrees=None)
                        # Enrich with direction and final dispositors for filtering
                        try:
                            dirs = _extract_planet_directions(chart_data)
                            if dirs:
                                metrics['planet_direction'] = dirs
                        except Exception:
                            pass
                        try:
                            finals = _compute_final_dispositors(metrics.get('planet_signs') or {})
                            if finals:
                                metrics['final_dispositor'] = finals
                        except Exception:
                            pass
                    except Exception:
                        metrics = {}
                    results.append({
                        'date': date_val,
                        'numbers': [n for n in numbers if n],
                        'power': [p for p in power_vals if p != ''],
                        'metrics': metrics,
                    })
                    with _research_lock:
                        sess = _research_sessions.get(session_id) or {}
                        sess['done'] = len(results)
                        sess['total'] = sess.get('total') or total_rows
        except Exception as e:
            with _research_lock:
                sess = _research_sessions.get(session_id) or {}
                sess['error'] = str(e)
        finally:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({'rows': results}, ensure_ascii=False), encoding='utf-8')
            with _research_lock:
                sess = _research_sessions.get(session_id) or {}
                if not sess.get('aborted'):
                    sess['ready'] = True
                    sess['source'] = sess.get('source') or 'compiled'
                    sess['done'] = len(results)
                    sess['total'] = len(results) or sess.get('total') or total_rows

    t = threading.Thread(target=_worker, name=f"research-compile-{session_id[:8]}", daemon=True)
    with _research_lock:
        _research_sessions[session_id]['thread'] = t
    t.start()
    return session_id, _research_progress_payload(session_id)


@astro_clock_bp.route('/research/lotto/compile/start', methods=['POST'])
@_error_handler
def research_compile_start():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    force = bool(body.get('force'))
    session_id, progress = _start_research_compile(body, force=force)
    return _json_ok({'session_id': session_id, 'progress': progress, 'cached': progress.get('ready') and progress.get('source') == 'cache'})


@astro_clock_bp.route('/research/lotto/compile', methods=['POST'])
@_error_handler
def research_compile():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    session_id, progress = _start_research_compile(body, force=bool(body.get('force')))
    return _json_ok({'session_id': session_id, 'progress': progress})


@astro_clock_bp.route('/research/lotto/progress', methods=['GET'])
@_error_handler
def research_progress():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    sid = request.args.get('session_id') or request.args.get('sid')
    if not sid:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    return _json_ok(_research_progress_payload(sid))


@astro_clock_bp.route('/research/lotto/stop', methods=['POST'])
@_error_handler
def research_stop():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    sid = body.get('sessionId') or body.get('session_id')
    if not sid:
        return jsonify({'success': False, 'error': 'sessionId required'}), 400
    with _research_lock:
        sess = _research_sessions.get(sid) or {}
        sess['aborted'] = True
    return _json_ok({'session_id': sid, 'progress': _research_progress_payload(sid)})


@astro_clock_bp.route('/research/lotto/analyze', methods=['POST'])
@_error_handler
def research_analyze():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    sid = body.get('sessionId') or body.get('session_id')
    filt = body.get('filter') or {}
    row_limit = body.get('rowLimit')
    if not sid:
        return jsonify({'success': False, 'error': 'sessionId required'}), 400
    with _research_lock:
        sess = _research_sessions.get(sid)
    cache_path = None
    if sess and sess.get('cache_path'):
        cache_path = Path(sess['cache_path'])
    else:
        # fallback to lookup by id
        cache_path = _ensure_research_cache_dir() / f"{sid}.json"
    if not cache_path.exists():
        return jsonify({'success': False, 'error': 'No cache for session'}), 400
    rows_all = _load_cached_rows(cache_path)
    if row_limit:
        try:
            rows_all = rows_all[: int(row_limit)]
        except Exception:
            pass
    matched = [r for r in rows_all if _matches_filters(r, filt)]
    numbers = _build_distribution(rows_all, matched, key='numbers')
    power = _build_distribution(rows_all, matched, key='power')
    return _json_ok({
        'rows_processed': len(rows_all),
        'rows_matched': len(matched),
        'numbers': numbers,
        'power': power,
    })
