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
import inspect
import json
import math
import os
import queue
import sys
import logging
import threading
import tempfile
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from collections import Counter
from datetime import datetime, timezone, time as dt_time, timedelta
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple, List, Iterable, Set
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request, Response, stream_with_context, has_request_context
from functools import lru_cache, wraps

from astro_clock_engine import AstroClockEngine, AstroClockSettings, ClockMode
from astro_dispositors import (
    calculate_dispositor_chains,
    compute_final_dispositors as compute_classical_final_dispositors,
)
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
from astro_clock_points import compute_symbolic_points_payload
from research_lab import (
    analyze_research_snapshots,
    build_run_id,
    generate_matched_control_rows,
    list_evaluator_catalog,
    normalize_chart_rows,
)

POINTS_HOUSE_SYSTEM_CODE = 'P'
from asteroids import (
    compute_asteroid_positions,
    _resolve_ephemeris_path as _resolve_synastry_ephemeris_path,
)
from swisseph_state import (
    require_swisseph,
    swisseph_ephemeris_path,
    swisseph_lock,
)
from snapshot_schema import (
    SNAP_RECORD_SCHEMA_VERSION,
    canonical_time_context,
    canonicalize_snapshot_record,
    coordinate_pair_from_value,
    is_generic_location_label,
    timezone_label_for_instant,
)
from moon_day import compute_moon_day
from election_models.lunar_fertility import (
    SwissEphemerisAdapter as LunarFertilityEphemerisAdapter,
    group_lunar_fertility_periods,
    normalize_consider_mode as normalize_lunar_fertility_consider_mode,
    scan_lunar_fertility_windows,
)
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
_ELECTION_REFERENCE_MAX_STEPS = max(
    _STREAM_MAX_STEPS,
    int(os.environ.get("VOX_STELLA_ELECTION_REFERENCE_MAX_STEPS", "43201")),
)
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
_MUNDANE_SCAN_SESSION_MAX = max(8, int(os.environ.get("VOX_STELLA_MUNDANE_SCAN_SESSION_MAX", "48")))
_MUNDANE_SCAN_SESSION_TTL_SECONDS = max(60.0, float(os.environ.get("VOX_STELLA_MUNDANE_SCAN_SESSION_TTL_SECONDS", "1800")))
_weather_scan_sessions: Dict[str, Dict[str, Any]] = {}
_weather_scan_lock = threading.Lock()
_WEATHER_SCAN_SESSION_MAX = max(8, int(os.environ.get("VOX_STELLA_WEATHER_SCAN_SESSION_MAX", "48")))
_WEATHER_SCAN_SESSION_TTL_SECONDS = max(60.0, float(os.environ.get("VOX_STELLA_WEATHER_SCAN_SESSION_TTL_SECONDS", "1800")))
_RESEARCH_SESSION_MAX = max(8, int(os.environ.get("VOX_STELLA_RESEARCH_SESSION_MAX", "48")))
_RESEARCH_SESSION_TTL_SECONDS = max(60.0, float(os.environ.get("VOX_STELLA_RESEARCH_SESSION_TTL_SECONDS", "3600")))
_BACKGROUND_WORKER_COUNT = max(1, min(8, int(os.environ.get("VOX_STELLA_BACKGROUND_WORKERS", "2"))))
_BACKGROUND_QUEUE_MAX = max(1, min(64, int(os.environ.get("VOX_STELLA_BACKGROUND_QUEUE_MAX", "4"))))
_research_cache_dir = Path(__file__).resolve().parent / 'research' / '.cache'
_research_default_time = "23:30"
_research_default_location = "Tel Aviv, Israel"
_research_default_tz = "Asia/Jerusalem"
_ASTRO_PERF_STACK: ContextVar[Tuple[str, ...]] = ContextVar('astro_perf_stack', default=())
_ASTRO_PERF_REQUEST: ContextVar[Optional[str]] = ContextVar('astro_perf_request', default=None)
_BUSINESS_BETA_EXTRACTION_LEVEL_DEFAULT = 67.0
_BUSINESS_BETA_EXTRACTION_MODES = {'total', 'detail'}
_BUSINESS_BETA_EXTRACTION_SCOPES = {'all', 'current', 'selected'}
_MARRIAGE_BETA_EXTRACTION_LEVEL_DEFAULT = 67.0
_MARRIAGE_BETA_EXTRACTION_MODES = _BUSINESS_BETA_EXTRACTION_MODES
_MARRIAGE_BETA_EXTRACTION_SCOPES = _BUSINESS_BETA_EXTRACTION_SCOPES
_ESTATE_EXTRACTION_LEVEL_DEFAULT = 67.0
_ESTATE_EXTRACTION_MODES = _BUSINESS_BETA_EXTRACTION_MODES
_ESTATE_EXTRACTION_SCOPES = _BUSINESS_BETA_EXTRACTION_SCOPES
_LUNAR_FERTILITY_LEVEL_DEFAULT = 33.0
_ELECTION_MATTER_ALIASES = {
    'marriage': 'marriage',
    'surgery': 'surgery',
    'business': 'business',
    'estate': 'estate',
    'contract': 'contract',
    'journey': 'journey',
    'haircut': 'haircut',
    'beautification': 'beautification',
    'conception': 'conception',
    'fertility': 'conception',
    'lunar_fertility': 'lunar_fertility',
    'viral': 'viral',
    'viral_content': 'viral',
    'viral-content': 'viral',
    'viralpublish': 'viral',
    'battle': 'battle',
    'combat': 'battle',
    'war': 'battle',
    'legal': 'legal',
}
_BACKGROUND_STOP = object()


class _BoundedDaemonExecutor:
    """Small process-local worker pool with bounded queued work.

    Jobs and their session state are intentionally restart-volatile: daemon
    workers never keep the packaged backend alive during shutdown.
    """

    def __init__(self, max_workers: int, max_queue: int):
        self.max_workers = max(1, int(max_workers))
        self.max_queue = max(1, int(max_queue))
        self._queue: queue.Queue = queue.Queue(maxsize=self.max_queue)
        self._start_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._started = False
        self._closed = False
        self._workers: List[threading.Thread] = []
        self._stats = {
            'accepted': 0,
            'rejected': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
        }

    def _ensure_started(self) -> None:
        if self._started or self._closed:
            return
        with self._start_lock:
            if self._started or self._closed:
                return
            for index in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker,
                    name=f'astro-background-{index + 1}',
                    daemon=True,
                )
                worker.start()
                self._workers.append(worker)
            self._started = True

    def _worker(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                if self._closed:
                    return
                continue
            if item is _BACKGROUND_STOP:
                self._queue.task_done()
                return
            job_name, callback = item
            with self._stats_lock:
                self._stats['running'] += 1
            try:
                callback()
            except Exception:
                with self._stats_lock:
                    self._stats['failed'] += 1
                logger.exception("Unhandled Astro Clock background job failure: %s", job_name)
            finally:
                with self._stats_lock:
                    self._stats['running'] -= 1
                    self._stats['completed'] += 1
                self._queue.task_done()

    def submit(self, job_name: str, callback) -> bool:
        self._ensure_started()
        with self._start_lock:
            if self._closed:
                with self._stats_lock:
                    self._stats['rejected'] += 1
                return False
            try:
                self._queue.put_nowait((str(job_name), callback))
            except queue.Full:
                with self._stats_lock:
                    self._stats['rejected'] += 1
                return False
        with self._stats_lock:
            self._stats['accepted'] += 1
        return True

    def shutdown(self, *, wait: bool = False) -> None:
        with self._start_lock:
            if self._closed:
                workers = list(self._workers)
            else:
                self._closed = True
                workers = list(self._workers)
                for _ in workers:
                    try:
                        self._queue.put_nowait(_BACKGROUND_STOP)
                    except queue.Full:
                        break
        if wait:
            for worker in workers:
                worker.join(timeout=2.0)

    def snapshot(self) -> Dict[str, Any]:
        with self._stats_lock:
            stats = dict(self._stats)
        return {
            **stats,
            'workers': self.max_workers,
            'queue_capacity': self.max_queue,
            'queued': self._queue.qsize(),
            'closed': self._closed,
        }


_previous_background_executor = globals().get('_background_executor')
if _previous_background_executor is not None:
    try:
        _previous_background_executor.shutdown(wait=False)
    except Exception:
        logger.exception("Failed to close previous Astro Clock background executor")


_background_executor = _BoundedDaemonExecutor(
    _BACKGROUND_WORKER_COUNT,
    _BACKGROUND_QUEUE_MAX,
)


class _BackgroundCapacityError(RuntimeError):
    pass


class LocalTimeResolutionError(ValueError):
    """Stable error contract for ambiguous, nonexistent, or mismatched local time."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        timezone_name: Optional[str],
        input_value: Any,
        wall_time_status: Optional[str] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.timezone_name = timezone_name
        self.input_value = str(input_value) if input_value is not None else None
        self.wall_time_status = wall_time_status
        self.candidates = copy.deepcopy(candidates or [])

    def to_payload(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'message': str(self),
            'input': self.input_value,
            'timezone': self.timezone_name,
            'wall_time_status': self.wall_time_status,
            'candidates': copy.deepcopy(self.candidates),
        }


def _submit_background_job(job_name: str, callback) -> bool:
    return _background_executor.submit(job_name, callback)


def _background_runtime_payload(
    workflow: str,
    *,
    session_max: int,
    session_ttl_seconds: float,
) -> Dict[str, Any]:
    return {
        'workflow': workflow,
        'session_persistence': 'process_memory',
        'restart_volatile': True,
        'session_max': int(session_max),
        'terminal_session_ttl_seconds': float(session_ttl_seconds),
        'executor': _background_executor.snapshot(),
    }


def _prune_terminal_sessions_locked(
    sessions: Dict[str, Dict[str, Any]],
    *,
    is_terminal,
    max_sessions: int,
    ttl_seconds: float,
    now: Optional[float] = None,
    reserve: int = 0,
) -> bool:
    current_time = now if now is not None else perf_counter()
    expired_ids = []
    for session_id, session in list(sessions.items()):
        if not is_terminal(session):
            continue
        updated_at = float(session.get('updated_at') or session.get('created_at') or current_time)
        if (current_time - updated_at) >= ttl_seconds:
            expired_ids.append(session_id)
    for session_id in expired_ids:
        sessions.pop(session_id, None)

    target_size = max(0, int(max_sessions) - max(0, int(reserve)))
    removable = []
    for session_id, session in sessions.items():
        if not is_terminal(session):
            continue
        updated_at = float(session.get('updated_at') or session.get('created_at') or current_time)
        removable.append((updated_at, session_id))
    removable.sort()
    for _, session_id in removable:
        if len(sessions) <= target_size:
            break
        sessions.pop(session_id, None)
    return len(sessions) <= target_size


def _initialize_background_session(
    sessions: Dict[str, Dict[str, Any]],
    lock: threading.Lock,
    session_id: str,
    initial: Dict[str, Any],
    *,
    is_terminal,
    max_sessions: int,
    ttl_seconds: float,
) -> bool:
    with lock:
        now = perf_counter()
        has_capacity = _prune_terminal_sessions_locked(
            sessions,
            is_terminal=is_terminal,
            max_sessions=max_sessions,
            ttl_seconds=ttl_seconds,
            now=now,
            reserve=1,
        )
        if not has_capacity:
            return False
        sessions[session_id] = {
            'session_id': session_id,
            'created_at': now,
            'updated_at': now,
            **initial,
        }
        return True


def _session_store_metrics(
    sessions: Dict[str, Dict[str, Any]],
    lock: threading.Lock,
    *,
    prune_locked,
    is_terminal,
) -> Dict[str, int]:
    with lock:
        prune_locked()
        values = list(sessions.values())
        terminal = sum(1 for session in values if is_terminal(session))
        return {
            'total': len(values),
            'active': len(values) - terminal,
            'terminal': terminal,
        }


def _background_busy_response(workflow: str):
    return jsonify({
        'success': False,
        'error': f'{workflow} background capacity is full; retry later',
        'retryable': True,
        'runtime': {
            'session_persistence': 'process_memory',
            'restart_volatile': True,
            'executor': _background_executor.snapshot(),
        },
    }), 503


def _missing_volatile_session_response(workflow: str):
    return jsonify({
        'success': False,
        'error': f'{workflow} session not found; process-local sessions are lost when the backend restarts',
        'restart_volatile': True,
    }), 404


def _validate_transit_scan_bounds(
    start_dt: datetime,
    end_dt: datetime,
    step_minutes: int,
    *,
    max_steps: Optional[int] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """Validate transit scan ranges to prevent unbounded CPU usage."""
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
    effective_max_steps = _STREAM_MAX_STEPS if max_steps is None else max(1, int(max_steps))
    if total_steps > effective_max_steps:
        return None, (
            f"Requested scan would process {total_steps} steps; max is {effective_max_steps}"
        )
    return max(1, total_steps), None


def _validate_stream_scan_bounds(
    start_dt: datetime,
    end_dt: datetime,
    step_minutes: int,
    *,
    max_steps: Optional[int] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """Backward-compatible wrapper for callers that still use the old name."""
    return _validate_transit_scan_bounds(
        start_dt,
        end_dt,
        step_minutes,
        max_steps=max_steps,
    )


def _parse_transit_scan_datetime(value: Any, label: str) -> Tuple[Optional[datetime], Optional[str]]:
    if value in (None, "", "null"):
        return None, f"{label} is required"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed, None
    except Exception:
        return None, f"Invalid {label}"


def _parse_transit_context_ranges(
    raw_ranges: Iterable[Tuple[str, Any, Any]],
) -> Tuple[List[Tuple[datetime, datetime]], Optional[str]]:
    """Validate optional transit context windows as timezone-aware instants."""
    parsed_ranges: List[Tuple[datetime, datetime]] = []
    for label, raw_start, raw_end in raw_ranges:
        has_start = raw_start not in (None, "", "null")
        has_end = raw_end not in (None, "", "null")
        if not has_start and not has_end:
            continue
        if not (has_start and has_end):
            return [], f"{label}_start and {label}_end must be provided together"
        start_dt, start_error = _parse_transit_scan_datetime(raw_start, f"{label}_start")
        if start_error:
            return [], start_error
        end_dt, end_error = _parse_transit_scan_datetime(raw_end, f"{label}_end")
        if end_error:
            return [], end_error
        assert start_dt is not None and end_dt is not None
        if end_dt <= start_dt:
            return [], f"{label}_end must be after {label}_start"
        parsed_ranges.append((start_dt, end_dt))
    return parsed_ranges, None


def _filter_transit_series_to_context_ranges(
    series: List[Dict[str, Any]],
    context_ranges: List[Tuple[datetime, datetime]],
) -> List[Dict[str, Any]]:
    """Keep rows inside at least one enabled, validated context window."""
    if not context_ranges:
        return series
    filtered: List[Dict[str, Any]] = []
    for row in series:
        row_dt, row_error = _parse_transit_scan_datetime(
            row.get("timestamp") if isinstance(row, dict) else None,
            "series timestamp",
        )
        if row_error or row_dt is None:
            continue
        if any(start_dt <= row_dt <= end_dt for start_dt, end_dt in context_ranges):
            filtered.append(row)
    return filtered


def _parse_transit_scan_step(value: Any, default: int = 60) -> Tuple[Optional[int], Optional[str]]:
    raw = default if value in (None, "", "null") else value
    try:
        step = int(raw)
    except Exception:
        return None, "Invalid step_minutes"
    if step < 1:
        return None, "step_minutes must be >= 1"
    return step, None


def _parse_transit_range_hours(value: Any, default: float = 12.0) -> Tuple[Optional[float], Optional[str]]:
    raw = default if value in (None, "", "null") else value
    try:
        hours = float(raw)
    except Exception:
        return None, "Invalid range_hours"
    if hours <= 0:
        return None, "range_hours must be > 0"
    return hours, None


def _parse_transit_limit(value: Any, default: int = 40, max_value: int = 200) -> Tuple[Optional[int], Optional[str]]:
    raw = default if value in (None, "", "null") else value
    try:
        limit = int(raw)
    except Exception:
        return None, "Invalid limit"
    if limit < 1:
        return None, "limit must be >= 1"
    return min(limit, max_value), None


def _parse_election_matter(value: Any) -> Tuple[Optional[str], Optional[str]]:
    raw = str(value or 'marriage').strip().lower()
    matter = _ELECTION_MATTER_ALIASES.get(raw)
    if matter is None:
        allowed = ', '.join(sorted(set(_ELECTION_MATTER_ALIASES.values())))
        return None, f"Unknown election matter '{raw}'. Allowed matters: {allowed}"
    return matter, None


def _election_reference_model(
    matter: str,
    marriage_algorithm: str,
    business_algorithm: str,
) -> bool:
    return bool(
        (matter == 'marriage' and marriage_algorithm == 'beta')
        or (matter == 'business' and business_algorithm == 'beta')
        or matter == 'estate'
    )


def _election_model_metadata(
    matter: str,
    *,
    marriage_algorithm: str = 'alpha',
    business_algorithm: str = 'alpha',
    natal_context_applied: bool = False,
    reference_parity: bool = False,
    step_minutes: int = 60,
) -> Dict[str, Any]:
    if matter == 'marriage':
        variant = 'beta' if marriage_algorithm == 'beta' else 'alpha'
    elif matter == 'business':
        variant = 'beta' if business_algorithm == 'beta' else 'alpha'
    else:
        variant = 'default'
    model_id = f'{matter}:{variant}'
    source_profiles = {
        'marriage:alpha': ('historical-primary', 'Morin Book 26 + Bonatti Treatise 7'),
        'marriage:beta': ('recovered-reference', 'Galaxy Electioner marriage workflow'),
        'surgery:default': ('historical-primary', 'Morin Book 26 + Bonatti Treatise 7'),
        'business:alpha': ('traditional-synthesis', 'Morin-derived business election synthesis'),
        'business:beta': ('recovered-reference', 'Galaxy Electioner business workflow'),
        'estate:default': ('recovered-reference', 'Galaxy Electioner estate workflow'),
        'contract:default': ('traditional-synthesis', 'traditional Mercury/Moon/7th-house synthesis'),
        'journey:default': ('historical-primary', 'Morin Book 26 + Bonatti Treatise 7'),
        'haircut:default': ('historical-primary', 'Bonatti Treatise 7 haircut rules'),
        'beautification:default': ('modern-heuristic', 'modern cosmetic-election analogy'),
        'conception:default': ('traditional-synthesis', 'Bonatti Treatise 7 conception rules'),
        'lunar_fertility:default': ('recovered-reference', 'Galaxy SkyLiner Jonas workflow'),
        'viral:default': ('modern-heuristic', 'modern house-signification analogy'),
        'battle:default': ('historical-primary', 'Morin Book 26 battle rules'),
        'legal:default': ('historical-primary', 'Bonatti Treatise 7 legal-contest rules'),
    }
    source_profile, source_basis = source_profiles.get(
        model_id,
        ('traditional-synthesis', 'repository election synthesis'),
    )
    return {
        'id': model_id,
        'version': '2026.07.31.1',
        'source_profile': source_profile,
        'source_basis': source_basis,
        'score_semantics': 'ordinal_within_model_run',
        'cross_model_comparable': False,
        'natal_mode': 'optional',
        'natal_context_applied': bool(natal_context_applied),
        'scan_mode': 'reference_1m' if reference_parity else 'standard',
        'step_minutes': int(step_minutes),
        'medical_use': False,
    }


def _mercury_direct_station_times(
    start_dt: datetime,
    end_dt: datetime,
) -> List[datetime]:
    """Return Mercury direct-station instants needed by a contract scan.

    The search starts 120 days before the window so a direct Mercury at the
    first scan point still has an exact station age.
    """
    try:
        swe = require_swisseph()
    except Exception:
        return []
    start_utc = (
        start_dt.replace(tzinfo=timezone.utc)
        if start_dt.tzinfo is None
        else start_dt.astimezone(timezone.utc)
    )
    end_utc = (
        end_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None
        else end_dt.astimezone(timezone.utc)
    )
    search_start = start_utc - timedelta(days=120)
    search_end = end_utc + timedelta(days=1)
    hour = (
        search_start.hour
        + search_start.minute / 60.0
        + search_start.second / 3600.0
    )
    try:
        start_jd = swe.julday(
            search_start.year,
            search_start.month,
            search_start.day,
            hour,
            getattr(swe, 'GREG_CAL', 1),
        )
        span_days = (search_end - search_start).total_seconds() / 86400.0
        end_jd = start_jd + span_days
        flags = getattr(swe, 'FLG_SWIEPH', 2) | getattr(swe, 'FLG_SPEED', 256)
        mercury_id = getattr(swe, 'MERCURY')
        path = _resolve_synastry_ephemeris_path()
        stations: List[datetime] = []
        step_days = 0.25
        with swisseph_lock():
            with swisseph_ephemeris_path(path, swe_module=swe):
                previous_jd = start_jd
                previous_speed = float(swe.calc_ut(previous_jd, mercury_id, flags)[0][3])
                current_jd = previous_jd + step_days
                while current_jd <= end_jd:
                    current_speed = float(swe.calc_ut(current_jd, mercury_id, flags)[0][3])
                    if previous_speed < 0.0 <= current_speed:
                        left = previous_jd
                        right = current_jd
                        left_speed = previous_speed
                        for _ in range(24):
                            middle = (left + right) / 2.0
                            middle_speed = float(swe.calc_ut(middle, mercury_id, flags)[0][3])
                            if left_speed < 0.0 <= middle_speed:
                                right = middle
                            else:
                                left = middle
                                left_speed = middle_speed
                        station_jd = (left + right) / 2.0
                        stations.append(
                            search_start + timedelta(days=station_jd - start_jd)
                        )
                    previous_jd = current_jd
                    previous_speed = current_speed
                    current_jd += step_days
        return stations
    except Exception:
        logger.exception('Unable to calculate Mercury direct-station timeline')
        return []


def _validate_transit_scan_request_bounds(
    start: Any,
    end: Any,
    step_minutes: int,
) -> Tuple[Optional[datetime], Optional[datetime], Optional[int], Optional[str]]:
    start_dt, start_error = _parse_transit_scan_datetime(start, "start")
    if start_error:
        return None, None, None, start_error
    end_dt, end_error = _parse_transit_scan_datetime(end, "end")
    if end_error:
        return None, None, None, end_error
    total_steps, bounds_error = _validate_transit_scan_bounds(start_dt, end_dt, step_minutes)
    if bounds_error:
        return start_dt, end_dt, None, bounds_error
    return start_dt, end_dt, total_steps, None


def _apply_transit_hit_filters(
    hits: List[Dict[str, Any]],
    flt_transiting: Optional[List[str]] = None,
    flt_natal: Optional[List[str]] = None,
    flt_aspects: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    filtered = list(hits or [])
    if flt_transiting:
        allowed = {str(item) for item in flt_transiting}
        filtered = [h for h in filtered if str(h.get('transiting')) in allowed]
    if flt_natal:
        allowed = {str(item) for item in flt_natal}
        filtered = [
            h for h in filtered
            if str(h.get('natal')) in allowed or str(h.get('target_label')) in allowed
        ]
    if flt_aspects:
        allowed = {str(item) for item in flt_aspects}
        filtered = [h for h in filtered if str(h.get('aspect')) in allowed]
    return filtered


def _sort_transit_hits_for_display(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep the transit engine's domain-aware priority order intact.

    The enrichment pipeline already emits a deliberate order that balances
    direct planet hits, angles, cusps, and antiscia. Re-sorting only by raw
    significance lets high-scoring generic rows crowd out lower-significance
    but domain-specific signals such as marriage or conflict. Predictor rows
    have their own explicit ranking and do not depend on this order.
    """
    return list(hits or [])


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


def _parse_marriage_beta_level_percent(raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except Exception:
        return _MARRIAGE_BETA_EXTRACTION_LEVEL_DEFAULT
    return max(0.0, min(100.0, value))


def _parse_estate_level_percent(raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except Exception:
        return _ESTATE_EXTRACTION_LEVEL_DEFAULT
    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return value


def _parse_lunar_fertility_level_percent(raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except Exception:
        return _LUNAR_FERTILITY_LEVEL_DEFAULT
    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return value


def _lunar_fertility_ephemeris_adapter() -> LunarFertilityEphemerisAdapter:
    return LunarFertilityEphemerisAdapter(
        ephemeris_path=_resolve_synastry_ephemeris_path()
    )


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
    row_prefix: str = 'business_beta',
    period_id_prefix: str = 'business-beta-period',
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
        row[f'{row_prefix}_pass'] = bool(row_passes)
        row[f'{row_prefix}_line_states'] = line_states
        row[f'{row_prefix}_selected_line_ids'] = list(resolved_selected_line_ids)
        row[f'{row_prefix}_selected_threshold'] = round(selected_threshold_total, 2)
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
                'id': f'{period_id_prefix}:{index}',
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


def _extract_estate_periods(
    rows: List[Dict[str, Any]],
    *,
    step_td: timedelta,
    display_mode: str,
    scope: str,
    level_percent: float,
    current_line_id: Optional[str] = None,
    selected_line_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    return _extract_business_beta_periods(
        rows,
        step_td=step_td,
        display_mode=display_mode,
        scope=scope,
        level_percent=level_percent,
        current_line_id=current_line_id,
        selected_line_ids=selected_line_ids,
        row_prefix='estate',
        period_id_prefix='estate-period',
    )


def _extract_marriage_beta_periods(
    rows: List[Dict[str, Any]],
    *,
    step_td: timedelta,
    display_mode: str,
    scope: str,
    level_percent: float,
    current_line_id: Optional[str] = None,
    selected_line_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    return _extract_business_beta_periods(
        rows,
        step_td=step_td,
        display_mode=display_mode,
        scope=scope,
        level_percent=level_percent,
        current_line_id=current_line_id,
        selected_line_ids=selected_line_ids,
        row_prefix='marriage_beta',
        period_id_prefix='marriage-beta-period',
    )


def _engine_instance() -> AstroClockEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
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


def _evaluate_traits_profile(engine: Any, metrics: Dict[str, Any], summary_context: str) -> Dict[str, Any]:
    evaluate = getattr(engine, 'evaluate')
    try:
        params = inspect.signature(evaluate).parameters
        supports_summary_context = (
            'summary_context' in params
            or any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values())
        )
    except (TypeError, ValueError):
        supports_summary_context = True

    if supports_summary_context:
        profile = evaluate(metrics, summary_context=summary_context)
    else:
        profile = evaluate(metrics)

    return profile if isinstance(profile, dict) else {}


def _tz_instance() -> TimezoneManager:
    global _tz_mgr
    if _tz_mgr is None:
        with _engine_lock:
            if _tz_mgr is None:
                _tz_mgr = TimezoneManager()
    return _tz_mgr


def _ph_instance(lat: float, lon: float) -> PlanetaryHoursCalculator:
    global _ph_calc, _ph_coords
    with _engine_lock:
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
    if event_type and not _prediction_is_supported_event(pred, event_type):
        return 0.0
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


def _prediction_is_supported_event(pred: Dict[str, Any], event_type: Optional[str] = None) -> bool:
    """Respect explicit evidence metadata while preserving legacy inputs."""
    raw = pred.get('is_event_prediction')
    if raw is None:
        raw = pred.get('isEventPrediction')
    if isinstance(raw, bool):
        return raw
    if raw is not None:
        return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}
    evidence_level = str(pred.get('evidence_level') or pred.get('evidenceLevel') or '').strip().lower()
    if evidence_level:
        return evidence_level in {'supported', 'corroborated'}
    return bool(str(event_type or pred.get('event_type') or '').strip())


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
    substantive_event = 1.0 if (
        event_type
        and _prediction_is_supported_event(pred, event_type)
        and (score > 0.0 or probability > 0.0 or significance > 0.0 or det_strength > 0.0)
    ) else 0.0
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
        and _prediction_is_supported_event(pred, event_type)
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
    rule_support = float(conc.get('overall_concordance') or 0.0)
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
    evidence_level = str(pred.get('evidenceLevel') or '')
    is_event_prediction = _prediction_is_supported_event(
        {
            'event_type': event_type,
            'evidence_level': evidence_level,
            'is_event_prediction': pred.get('isEventPrediction'),
        },
        event_type,
    )
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
        # Backward-compatible alias. This is rule concordance, not an
        # empirical or calibrated event probability.
        'probability': round(rule_support, 3),
        'rule_support': round(rule_support, 3),
        'probability_basis': 'morin_rule_concordance',
        'is_statistical_probability': False,
        'evidence_level': evidence_level or None,
        'is_event_prediction': bool(event_type) and is_event_prediction,
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
    registry_context: Optional[Dict[str, Any]] = None,
    route_label: str = "astro-clock/transits",
) -> List[Dict[str, Any]]:
    """Enrich transit hits, retrying without PD/context if the richer pass fails."""
    if not isinstance(hits, list) or not hits:
        return hits

    from transits_morin import enrich_hits_with_concordance

    registry_snapshot = None
    if isinstance(registry_context, dict):
        try:
            registry_snapshot = copy.deepcopy(registry_context)
        except Exception:
            registry_snapshot = None

    def _restore_registry_context() -> None:
        if isinstance(registry_context, dict) and isinstance(registry_snapshot, dict):
            registry_context.clear()
            registry_context.update(copy.deepcopy(registry_snapshot))

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
            registry_context=registry_context,
        )
    except Exception:
        logger.exception(
            "[astro-clock] Concordance enrichment failed for %s; retrying without PD/context.",
            route_label,
        )
        _restore_registry_context()

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
            registry_context=registry_context,
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
        _restore_registry_context()
        if isinstance(context_out, dict):
            context_out.clear()
        return hits


def _parse_optional_iso_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"none", "null"}:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
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
    return _parse_optional_iso_datetime(meta_ts)


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
            'rule_support': _prediction_numeric(
                pred.get('rule_support')
                if pred.get('rule_support') is not None
                else pred.get('probability')
            ),
            'probability_basis': pred.get('probability_basis') or 'morin_rule_concordance',
            'is_statistical_probability': False,
            'evidence_level': pred.get('evidence_level'),
            'is_event_prediction': _prediction_is_supported_event(pred),
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
        'rule_concordance_max': probability_max,
        'rule_concordance_mean': round(probability_total / count, 3),
        'probability_basis': 'morin_rule_concordance',
        'is_statistical_probability': False,
        'evidence_level': next(
            (
                level
                for level in ('corroborated', 'supported', 'theme_only')
                if any(
                    isinstance(pred, dict)
                    and str(pred.get('evidence_level') or '') == level
                    for pred in cluster_predictions
                )
            ),
            'theme_only',
        ),
        'is_event_prediction': any(
            isinstance(pred, dict) and _prediction_is_supported_event(pred)
            for pred in cluster_predictions
        ),
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


def _predictor_peak_identity(row: Dict[str, Any]) -> Tuple[str, str, str]:
    summary = row.get('_predictor_peak_summary') if isinstance(row, dict) else None
    if not isinstance(summary, dict):
        summary = _predictor_peak_summary(row if isinstance(row, dict) else {})
    return (
        str(summary.get('event_type') or '').strip().lower(),
        str(summary.get('life_area') or '').strip().lower(),
        str(summary.get('transit') or summary.get('description') or '').strip().lower(),
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
    selected_identity_times: List[Tuple[Tuple[str, str, str], Optional[datetime]]] = []
    selected_support_signatures: Set[Tuple[Tuple[str, str, str], float, float]] = set()
    for candidate in ordered_candidates:
        identity = _predictor_peak_identity(candidate)
        candidate_dt = _parse_predictor_iso(candidate.get('timestamp'))
        if any(identity):
            summary = candidate.get('_predictor_peak_summary')
            if not isinstance(summary, dict):
                summary = _predictor_peak_summary(candidate)
            support_signature = (
                identity,
                round(_prediction_numeric(summary.get('support_focus')), 3),
                round(_prediction_numeric(summary.get('support_score')), 3),
            )
            if support_signature in selected_support_signatures:
                continue
            same_identity = [
                chosen_dt
                for chosen_identity, chosen_dt in selected_identity_times
                if chosen_identity == identity
            ]
            if candidate_dt is None:
                if same_identity:
                    continue
            elif any(
                chosen_dt is None
                or abs((candidate_dt - chosen_dt).total_seconds()) / 60.0 < min_peak_gap_minutes
                for chosen_dt in same_identity
            ):
                continue
        elif candidate_dt is not None and any(
            abs((candidate_dt - chosen_dt).total_seconds()) / 60.0 < min_peak_gap_minutes
            for chosen_dt in selected_times
        ):
            continue
        selected.append(candidate)
        if any(identity):
            selected_identity_times.append((identity, candidate_dt))
            selected_support_signatures.add(support_signature)
        if candidate_dt is not None:
            selected_times.append(candidate_dt)
        if len(selected) >= max(1, int(limit or 10)):
            break

    return selected


def _predictor_group_peak_summary(group: Dict[str, Any]) -> Dict[str, Any]:
    occurrences = group.get('occurrences') if isinstance(group, dict) else []
    dominant_timestamp = str(group.get('dominant_timestamp') or '') if isinstance(group, dict) else ''
    support_score = 0.0
    if isinstance(occurrences, list) and occurrences:
        dominant_occurrence = None
        for occ in occurrences:
            if isinstance(occ, dict) and dominant_timestamp and str(occ.get('date') or '') == dominant_timestamp:
                dominant_occurrence = occ
                break
        if dominant_occurrence is None:
            dominant_occurrence = max(
                (occ for occ in occurrences if isinstance(occ, dict)),
                key=lambda occ: _prediction_numeric(occ.get('support_score')),
                default=None,
            )
        if isinstance(dominant_occurrence, dict):
            support_score = _prediction_numeric(dominant_occurrence.get('support_score'))
    if support_score <= 0.0:
        support_score = _prediction_numeric(group.get('support_density'))

    return {
        'event_type': group.get('event_type'),
        'life_area': group.get('life_area'),
        'description': group.get('description') or group.get('label'),
        'transit': group.get('transit') or group.get('dominant_transit'),
        'support_focus': _prediction_numeric(group.get('support_focus')),
        'support_score': support_score,
        'domain_alignment': _prediction_numeric(group.get('domain_alignment_max')),
        'probability': _prediction_numeric(group.get('probability_max')),
        'keyword_tokens': list(group.get('keyword_tokens') or group.get('tags') or []),
    }


def _build_predictor_group_peak_rows(
    series: List[Dict[str, Any]],
    grouped_predictions: List[Dict[str, Any]],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    if not isinstance(grouped_predictions, list) or not grouped_predictions:
        return []

    safe_series = [row for row in series if isinstance(row, dict)] if isinstance(series, list) else []
    selected: List[Dict[str, Any]] = []
    selected_identities: Set[Tuple[str, str, str]] = set()

    for group in sorted((g for g in grouped_predictions if isinstance(g, dict)), key=_predictor_group_sort_key):
        summary = _predictor_group_peak_summary(group)
        identity = (
            str(summary.get('event_type') or '').strip().lower(),
            str(summary.get('life_area') or '').strip().lower(),
            str(summary.get('transit') or summary.get('description') or '').strip().lower(),
        )
        if any(identity) and identity in selected_identities:
            continue

        dominant_dt = _parse_predictor_iso(group.get('dominant_timestamp'))
        start_dt = _parse_predictor_iso(group.get('start') or group.get('window_start'))
        end_dt = _parse_predictor_iso(group.get('end') or group.get('window_end'))
        target_dt = dominant_dt
        if target_dt is None and start_dt is not None and end_dt is not None:
            target_dt = start_dt + ((end_dt - start_dt) / 2)

        matching_rows = [row for row in safe_series if _row_matches_prediction_group(row, group)]
        candidate_rows = matching_rows or safe_series
        representative: Dict[str, Any]
        if candidate_rows:
            def _distance_key(row: Dict[str, Any]) -> Tuple[float, Tuple[float, float, float, float, float, str, str]]:
                row_dt = _parse_predictor_iso(row.get('timestamp'))
                if target_dt is None or row_dt is None:
                    distance = float('inf')
                else:
                    distance = abs((row_dt - target_dt).total_seconds())
                return (distance, _predictor_peak_sort_key(row))

            representative = dict(sorted(candidate_rows, key=_distance_key)[0])
        else:
            representative = {
                'timestamp': group.get('dominant_timestamp') or group.get('start') or group.get('window_start'),
                'count': group.get('count'),
                'step_score': group.get('support_focus') or group.get('support_score'),
                'tone': 'mixed',
            }
        representative['_predictor_peak_summary'] = summary
        selected.append(representative)
        if any(identity):
            selected_identities.add(identity)
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
        except LocalTimeResolutionError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'error_code': e.code,
                'time_resolution': e.to_payload(),
            }), 400
        except LocationError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except ValueError as e:
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
            'terminal_type': getattr(v, 'terminal_type', None),
            'has_final_dispositor': bool(getattr(v, 'has_final_dispositor', False)),
            'cycle': list(getattr(v, 'cycle', []) or []),
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


def _build_dispositors_payload(rt: Dict[str, Any], chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_dispositor_chains = (rt or {}).get('dispositor_chains') or {}
    try:
        planet_rows_for_dispositors = _normalized_planet_rows(chart_data.get('planets')) if isinstance(chart_data, dict) else []
        if planet_rows_for_dispositors:
            raw_dispositor_chains = calculate_dispositor_chains(planet_rows_for_dispositors)
    except Exception:
        raw_dispositor_chains = (rt or {}).get('dispositor_chains') or {}

    def _chain_get(chain_obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(chain_obj, dict):
            return chain_obj.get(key, default)
        return getattr(chain_obj, key, default)

    return {
        k: {
            'dispositor': _chain_get(chain, 'dispositor'),
            'chain': list(_chain_get(chain, 'chain', []) or []),
            'final_dispositor': _chain_get(chain, 'final_dispositor'),
            'mutual_reception': bool(_chain_get(chain, 'mutual_reception', False)),
            'reception_partner': _chain_get(chain, 'reception_partner'),
            'terminal_type': _chain_get(chain, 'terminal_type'),
            'has_final_dispositor': bool(_chain_get(chain, 'has_final_dispositor', False)),
            'cycle': list(_chain_get(chain, 'cycle', []) or []),
        }
        for k, chain in raw_dispositor_chains.items()
    }


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


def _snap_coordinate_pair(*sources: Any) -> Optional[Tuple[float, float]]:
    for source in sources:
        coords = _coords_from_request_args(source)
        if coords is not None:
            return coords
        coords = coordinate_pair_from_value(source)
        if coords is not None:
            return coords
    return None


def _dashboard_from_snap_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    dashboard = payload.get('dashboard')
    if not isinstance(dashboard, dict):
        return None
    if not (
        dashboard.get('timestamp')
        or _normalized_planet_rows(dashboard.get('planets'))
        or dashboard.get('house_cusps')
        or dashboard.get('houses')
    ):
        return None
    return copy.deepcopy(dashboard)


def _normalize_snap_certification_payload(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    payload = copy.deepcopy(value)
    payload['kind'] = 'birth_time_certification'
    payload['status'] = _first_nonempty_text(payload.get('status'), 'insufficient_data')
    payload['confidence'] = _first_nonempty_text(payload.get('confidence'), 'none')
    return payload


def _snap_certification_summary(certification: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(certification, dict):
        return None
    selected = certification.get('selected_candidate')
    if not isinstance(selected, dict):
        selected = {}
    summary = {
        'kind': 'birth_time_certification',
        'status': _first_nonempty_text(certification.get('status'), 'insufficient_data'),
        'confidence': _first_nonempty_text(certification.get('confidence'), 'none'),
    }
    strength = selected.get('strength')
    if strength is not None:
        try:
            summary['strength'] = float(strength)
        except (TypeError, ValueError):
            pass
    return summary


def _timestamp_from_snap_dashboard(
    dashboard: Optional[Dict[str, Any]],
    active_settings: Optional[AstroClockSettings],
    eng: AstroClockEngine,
) -> datetime:
    custom = getattr(active_settings, 'custom_time', None)
    if isinstance(custom, datetime):
        if custom.tzinfo is None:
            return custom.replace(tzinfo=timezone.utc)
        return custom.astimezone(timezone.utc)
    if isinstance(dashboard, dict):
        for key in ('timestamp', 'effective_datetime'):
            raw = dashboard.get(key)
            if raw in (None, '', 'null'):
                continue
            try:
                parsed = _parse_iso_datetime(raw)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except Exception:
                pass
    try:
        effective = eng.get_effective_datetime()
        if isinstance(effective, datetime):
            if effective.tzinfo is None:
                return effective.replace(tzinfo=timezone.utc)
            return effective.astimezone(timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)


def _chart_result_from_snap_dashboard(dashboard: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    chart_data = _synastry_chart_snapshot_from_dashboard(dashboard or {})
    house_cusps = chart_data.get('house_cusps')
    if house_cusps and 'houses' not in chart_data:
        chart_data['houses'] = copy.deepcopy(house_cusps)
    return {'chart_data': chart_data}


def _apply_snap_dashboard_context(
    dashboard: Dict[str, Any],
    timestamp: datetime,
    active_settings: Optional[AstroClockSettings],
) -> Dict[str, Any]:
    out = copy.deepcopy(dashboard)
    out['timestamp'] = timestamp.isoformat()
    if active_settings is not None:
        location = getattr(active_settings, 'location', None)
        timezone_name = getattr(active_settings, 'timezone', None)
        house_system = getattr(active_settings, 'house_system_code', None)
        coords = _coords_from_settings(active_settings)
        if location:
            out['location'] = location
        if timezone_name:
            out['timezone'] = timezone_name
            out['timezone_label'] = (
                timezone_label_for_instant(timezone_name, timestamp.isoformat())
                or timezone_name
            )
        if house_system:
            out['house_system_code'] = house_system
        if coords:
            out['latitude'], out['longitude'] = coords
    return out


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


def _house_area_map_for_traits() -> Dict[int, str]:
    try:
        from determinations import _house_domain_map as _hm

        return _hm()
    except Exception:
        return {
            1: 'life',
            2: 'wealth',
            3: 'short_travel',
            4: 'home',
            5: 'children',
            6: 'health',
            7: 'relationships',
            8: 'death',
            9: 'belief',
            10: 'honors',
            11: 'friends',
            12: 'secrets',
        }


def _build_planet_area_scores_from_house_influences(
    house_infl: Dict[str, Any],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]]]:
    """Return Morin determination scores for TraitEngine planet_area rules.

    The score is intentionally not a decorative per-planet max.  A planet-area
    route must be strong in two ways:
      - relative: the area is important for that planet's own determinations;
      - absolute: the area has real weight compared with the chart's strongest
        planet-area determination.

    score = sqrt(relative_strength * absolute_strength)
    """
    house_to_area = _house_area_map_for_traits()
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
                planet = str(inf.get('planet') or '').strip()
                if not planet:
                    continue
                value = abs(float(inf.get('value') or 0.0))
                if value <= 0.0:
                    continue
                raw.setdefault(planet, {})[area] = raw.get(planet, {}).get(area, 0.0) + value
            except Exception:
                continue

    global_max = 0.0
    for area_map in raw.values():
        for value in area_map.values():
            global_max = max(global_max, abs(float(value or 0.0)))
    if global_max <= 0.0:
        return {}, {}

    scores: Dict[str, Dict[str, float]] = {}
    details: Dict[str, Dict[str, Dict[str, float]]] = {}
    for planet, area_map in raw.items():
        try:
            planet_max = max(abs(float(v or 0.0)) for v in area_map.values())
        except Exception:
            planet_max = 0.0
        if planet_max <= 0.0:
            continue
        for area, raw_value in area_map.items():
            try:
                value = abs(float(raw_value or 0.0))
                relative = max(0.0, min(1.0, value / planet_max))
                absolute = max(0.0, min(1.0, value / global_max))
                score = math.sqrt(relative * absolute) if relative > 0.0 and absolute > 0.0 else 0.0
                scores.setdefault(planet, {})[area] = round(score, 4)
                details.setdefault(planet, {})[area] = {
                    'score': round(score, 4),
                    'relative_strength': round(relative, 4),
                    'absolute_strength': round(absolute, 4),
                    'raw_value': round(value, 4),
                }
            except Exception:
                continue
    return scores, details


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


def _normalize_aspect_rows_for_forensic(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        if not row.get('aspect') and row.get('type'):
            row['aspect'] = row.get('type')
        if 'applying' not in row and row.get('phase') is not None:
            row['applying'] = str(row.get('phase') or '').strip().lower() == 'applying'
        normalized.append(row)
    return normalized


_HEALTHCARE_CONTEXT_TOKENS = {
    "hospital",
    "hospitals",
    "clinic",
    "clinics",
    "medical",
    "healthcare",
    "infirmary",
    "ward",
    "nicu",
    "neonatal",
    "maternity",
    "nursing",
    "nurse",
    "nurses",
    "doctor",
    "doctors",
    "physician",
    "physicians",
    "hospice",
}
_CAREGIVER_CONTEXT_TOKENS = {
    "caregiver",
    "caregivers",
    "caretaker",
    "caretakers",
    "childcare",
    "daycare",
    "nursery",
    "nanny",
    "babysitter",
    "babysitting",
    "housekeeper",
    "maid",
    "servant",
    "servants",
}
_HEALTHCARE_CONTEXT_PHRASES = {
    "care home",
    "children's hospital",
    "childrens hospital",
    "emergency department",
    "intensive care",
    "special care baby unit",
    "health centre",
    "health center",
    "medical centre",
    "medical center",
}


def _context_tokens(*values: Any) -> Set[str]:
    text = " ".join(str(value or "").lower() for value in values if value is not None)
    for char in ",.;:/\\()[]{}\"'`|+-_":
        text = text.replace(char, " ")
    return {part.strip() for part in text.split() if part.strip()}


def _contains_context_phrase(phrases: Set[str], *values: Any) -> bool:
    blob = " ".join(str(value or "").lower() for value in values if value is not None)
    return any(phrase in blob for phrase in phrases)


def _infer_forensic_case_context(case_type: str, dashboard: Dict[str, Any], settings: Any = None) -> Dict[str, Any]:
    child_case = bool(case_type == 'child')
    adult_female_case = bool(case_type == 'adult_female')
    values = [
        request.args.get('location') if has_request_context() else None,
        request.args.get('context') if has_request_context() else None,
        request.args.get('case_context') if has_request_context() else None,
        request.args.get('case_notes') if has_request_context() else None,
        request.args.get('notes') if has_request_context() else None,
        dashboard.get('location') if isinstance(dashboard, dict) else None,
        dashboard.get('timezone_label') if isinstance(dashboard, dict) else None,
        getattr(settings, 'location', None),
    ]
    tokens = _context_tokens(*values)
    healthcare_context = bool(
        tokens & _HEALTHCARE_CONTEXT_TOKENS
        or _contains_context_phrase(_HEALTHCARE_CONTEXT_PHRASES, *values)
    )
    caregiver_context = bool(tokens & _CAREGIVER_CONTEXT_TOKENS)
    if has_request_context():
        healthcare_context = healthcare_context or _truthy_env(request.args.get('healthcare_context'))
        caregiver_context = caregiver_context or _truthy_env(request.args.get('caregiver_context'))
    institutional_care_context = healthcare_context or caregiver_context
    return {
        'case_type': case_type,
        'child_case': child_case,
        'adult_female_case': adult_female_case,
        'healthcare_context': healthcare_context,
        'caregiver_context': caregiver_context,
        'institutional_care_context': institutional_care_context,
        'healthcare_child_context': bool(child_case and institutional_care_context),
    }


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


def _timezone_label_from_parts(tz_name: Any, local_iso: Any, utc_iso: Any = None) -> Optional[str]:
    if not tz_name:
        return None
    if utc_iso:
        canonical = timezone_label_for_instant(tz_name, utc_iso)
        if canonical:
            return canonical
    try:
        loc_dt = datetime.fromisoformat(str(local_iso).replace('Z', '+00:00'))
        if loc_dt.tzinfo is not None:
            canonical = timezone_label_for_instant(
                tz_name,
                loc_dt.astimezone(timezone.utc).isoformat(),
            )
            if canonical:
                return canonical
        delta = loc_dt.utcoffset()
        if delta is None:
            return str(tz_name)
        delta_min = int(round(delta.total_seconds() / 60.0))
        sign = '+' if delta_min >= 0 else '-'
        hh = abs(delta_min) // 60
        mm = abs(delta_min) % 60
        return f"{tz_name} (UTC{sign}{hh:02d}:{mm:02d})"
    except Exception:
        return None


def _timezone_label_from_chart_data(cd: Dict[str, Any]) -> Optional[str]:
    try:
        tzinfo = cd.get('timezone_info') if isinstance(cd, dict) else None
        if not isinstance(tzinfo, dict):
            return None
        return _timezone_label_from_parts(
            tzinfo.get('timezone'),
            tzinfo.get('local_time'),
            tzinfo.get('utc_time'),
        )
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


def _build_traits_chart_snapshot(
    data,
    rt: Dict[str, Any],
    cd: Dict[str, Any],
    special_degrees: List[str],
    dashboard_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    active_settings = getattr(data, 'settings', None)
    active_location = getattr(active_settings, 'location', None)
    active_timezone = getattr(active_settings, 'timezone', None)
    dashboard = dashboard_payload if isinstance(dashboard_payload, dict) else {}

    def dashboard_list(key: str) -> Optional[List[Any]]:
        value = dashboard.get(key)
        return copy.deepcopy(value) if isinstance(value, list) else None

    def dashboard_dict(key: str) -> Optional[Dict[str, Any]]:
        value = dashboard.get(key)
        return copy.deepcopy(value) if isinstance(value, dict) else None

    planets = dashboard_list('planets')
    if planets is None:
        planets = rt.get('planets') if isinstance(rt.get('planets'), list) else []

    moon_state = rt.get('moon_state') if isinstance(rt.get('moon_state'), dict) else {}
    moon = dashboard_dict('moon')
    try:
        if moon is None:
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

    solar_conditions = dashboard_dict('solar_conditions')
    if solar_conditions is None:
        solar_conditions = _solar_conditions_from_chart(planets, cd)

    top_aspects = dashboard_list('top_aspects')
    if top_aspects is None:
        top_aspects = _top_aspects_from_runtime(rt, cd)

    house_cusps = dashboard_list('house_cusps')
    if house_cusps is None:
        house_cusps = cd.get('houses') or cd.get('house_cusps') or []

    house_rulers = dashboard_dict('house_rulers')
    if house_rulers is None:
        house_rulers = cd.get('house_rulers') or {}

    receptions = dashboard_dict('receptions')
    if receptions is None:
        receptions = _lightweight_receptions_payload(
            data.chart_result if isinstance(data.chart_result, dict) else {},
            cd,
        ) or {}

    special_degree_snapshot = dashboard_list('special_degrees')
    if special_degree_snapshot is None:
        special_degree_snapshot = special_degrees

    return {
        'timestamp': dashboard.get('timestamp') or rt.get('timestamp'),
        'location': dashboard.get('location') or active_location,
        'timezone': dashboard.get('timezone') or active_timezone,
        'timezone_label': dashboard.get('timezone_label') or _timezone_label_from_chart_data(cd),
        'house_system': (
            dashboard.get('house_system')
            or dashboard.get('house_system_code')
            or getattr(active_settings, 'house_system_code', None)
        ),
        'ascendant': dashboard.get('ascendant') if dashboard.get('ascendant') is not None else cd.get('ascendant'),
        'midheaven': dashboard.get('midheaven') if dashboard.get('midheaven') is not None else cd.get('midheaven'),
        'planets': planets,
        'moon': moon,
        'moon_timeline': dashboard_dict('moon_timeline'),
        'solar_conditions': solar_conditions,
        'top_aspects': top_aspects,
        'morin_aspects': dashboard_list('morin_aspects') or [],
        'fixed_star_hits': dashboard_list('fixed_star_hits') or [],
        'house_cusps': house_cusps,
        'house_rulers': house_rulers,
        'receptions': receptions,
        'special_degrees': special_degree_snapshot,
        'morin_patterns': dashboard_dict('morin_patterns') or {},
    }


@astro_clock_bp.route('/current', methods=['GET'])
@_error_handler
def get_current():
    with _astro_perf_span('route.current'):
        eng = _engine_instance()
        with _astro_perf_span('route.current.get_current_data'):
            data, _active_settings = _data_for_optional_confirmed_snap(eng)
        with _astro_perf_span('route.current.serialize'):
            payload = _serialize_real_time(data)
    return _json_ok(payload)


def _build_dashboard_payload(
    eng: AstroClockEngine,
    data,
    include_modern: bool = False,
    include_morin: bool = False,
    special_degrees: Optional[List[str]] = None,
    extend_modern_chart_data: bool = True,
) -> Dict[str, Any]:
    with _astro_perf_span(
        'helper.build_dashboard_payload.setup',
        include_modern=include_modern,
        include_morin=include_morin,
    ):
        rt = _serialize_real_time(data)
        cd = rt.get('chart_data') or {}
        if isinstance(cd, dict) and include_modern and extend_modern_chart_data:
            ts_iso = rt.get('timestamp')
            if not ts_iso:
                try:
                    ts_iso = data.timestamp.isoformat()
                except Exception:
                    ts_iso = None
            cd = _extend_chart_data_for_synastry(
                cd,
                {'timestamp': ts_iso},
                include_modern=True,
                include_chiron=False,
            )
        try:
            chart_result = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
        except Exception:
            chart_result = {}
        active_settings = getattr(data, 'settings', None)
        active_location = getattr(active_settings, 'location', None) or eng.settings.location
        active_timezone = getattr(active_settings, 'timezone', None) or eng.settings.timezone
        active_coords = _coords_from_settings(active_settings)
        if active_coords is None:
            active_coords = _coords_from_chart_data(cd)
        if active_coords is None and active_location:
            active_coords = _ensure_coords_for_location(active_location, settings_hint=active_settings)
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
        dispositors = _build_dispositors_payload(rt, cd)
    except Exception:
        dispositors = {}

    # Timezone label
    timezone_label = None
    try:
        tzinfo = cd.get('timezone_info') if isinstance(cd, dict) else None
        if isinstance(tzinfo, dict):
            timezone_label = _timezone_label_from_parts(
                tzinfo.get('timezone'),
                tzinfo.get('local_time'),
                tzinfo.get('utc_time'),
            )
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

    with _astro_perf_span('helper.build_dashboard_payload.compass'):
        try:
            compass = _build_local_space_compass_payload(
                cd,
                getattr(data, 'timestamp', None),
                active_settings,
                include_modern=include_modern,
            )
        except (LocationError, ValueError):
            compass = None
        except Exception:
            logger.exception("Failed to compute dashboard compass payload")
            compass = None

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
        'latitude': (active_coords[0] if active_coords else None),
        'longitude': (active_coords[1] if active_coords else None),
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
        'ascendant': cd.get('ascendant'),
        'midheaven': cd.get('midheaven'),
        'house_cusps': cd.get('houses') or cd.get('house_cusps') or [],
        'house_rulers': cd.get('house_rulers') or {},
        'receptions': receptions,
        'special_degrees': special_degrees,
        'metrics': metrics,
        'almutens': almutens,
        'asteroids': asteroids,
        'compass': compass,
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
        data, _active_settings = _data_for_optional_confirmed_snap(eng)
        payload = _build_dashboard_payload(
            eng,
            data,
            include_modern=include_modern,
            include_morin=include_morin,
        )
    return _json_ok(payload)


@astro_clock_bp.route('/points/degree-hits', methods=['GET'])
@_error_handler
def get_points_degree_hits():
    with _astro_perf_span('route.points_degree_hits'):
        eng = _engine_instance()
        data, active_settings = _data_for_optional_confirmed_snap(
            eng,
            house_system_override=POINTS_HOUSE_SYSTEM_CODE,
        )
        rt = _serialize_real_time(data)
        cd = rt.get('chart_data') or {}
        ts_iso = rt.get('timestamp')
        if isinstance(cd, dict):
            cd = _extend_chart_data_for_points(cd, ts_iso)
            cd = _with_points_exact_geometry(cd, _points_raw_chart(data))
        coords = _coords_from_settings(active_settings)
        house_system = POINTS_HOUSE_SYSTEM_CODE
        payload = compute_symbolic_points_payload(
            cd,
            timestamp_iso=ts_iso,
            sex_code=request.args.get('sex_code'),
            latitude=(coords[0] if coords else None),
            longitude=(coords[1] if coords else None),
            house_system=house_system,
        )
    return _json_ok(payload)


def _points_raw_chart(data: Any) -> Any:
    chart_result = getattr(data, 'chart_result', None)
    if isinstance(chart_result, dict):
        return chart_result.get('_raw_chart')
    return None


def _points_raw_value(raw_chart: Any, *names: str) -> Any:
    if raw_chart is None:
        return None
    for name in names:
        if isinstance(raw_chart, dict) and name in raw_chart:
            return raw_chart.get(name)
        value = getattr(raw_chart, name, None)
        if value is not None:
            return value
    return None


def _points_finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except Exception:
        return None
    return number if math.isfinite(number) else None


def _points_exact_float_list(value: Any) -> List[float]:
    if not isinstance(value, (list, tuple)):
        return []
    out: List[float] = []
    for item in value[:12]:
        number = _points_finite_float(item)
        if number is None:
            return []
        out.append(number)
    return out if len(out) == 12 else []


def _with_points_exact_geometry(chart_data: Dict[str, Any], raw_chart: Any) -> Dict[str, Any]:
    out = dict(chart_data or {})
    exact_houses = _points_exact_float_list(_points_raw_value(raw_chart, 'houses', 'house_cusps'))
    if exact_houses:
        out['house_cusps_exact'] = list(exact_houses)
        out['houses_exact'] = list(exact_houses)

    ascendant = _points_finite_float(_points_raw_value(raw_chart, 'ascendant', 'asc'))
    if ascendant is None and exact_houses:
        ascendant = exact_houses[0]
    if ascendant is not None:
        out['ascendant_exact'] = ascendant

    midheaven = _points_finite_float(_points_raw_value(raw_chart, 'midheaven', 'mc', 'medium_coeli'))
    if midheaven is None and exact_houses:
        midheaven = exact_houses[9]
    if midheaven is not None:
        out['midheaven_exact'] = midheaven

    return out


def _extend_chart_data_for_points(chart_data: Dict[str, Any], timestamp_iso: Optional[str]) -> Dict[str, Any]:
    out = _extend_chart_data_for_synastry(
        chart_data,
        {'timestamp': timestamp_iso},
        include_modern=True,
        include_chiron=True,
    )

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
                if row_name == name:
                    planets[idx] = merged
                    return
            planets.append(merged)
            return
        row = dict(merged)
        row.pop('planet', None)
        out['planets'] = {name: row}

    try:
        asteroids_payload = compute_asteroid_positions(out, timestamp_iso, include_point_dependencies=True)
    except Exception:
        asteroids_payload = None
    if isinstance(asteroids_payload, dict):
        out['points_asteroids'] = asteroids_payload
        for item in asteroids_payload.get('items') or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name') or '').strip()
            if name not in {'Ceres', 'Pallas', 'Juno', 'Vesta', 'Proserpina', 'Eros', 'Lilith', 'Selena'}:
                continue
            _upsert_planet(
                name,
                {
                    'planet': name,
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
    return out


def _is_placeholder_tz(t: Optional[str]) -> bool:
    if not t:
        return True
    s = str(t).strip()
    return s in ("UTC", "Etc/UTC", "Etc/GMT", "GMT")


def _valid_explicit_timezone(timezone_name: Optional[str]) -> Optional[str]:
    tz = str(timezone_name).strip() if timezone_name is not None else ""
    if not tz or _is_placeholder_tz(tz):
        return None
    try:
        ZoneInfo(tz)
        return tz
    except Exception:
        return None


def _valid_confirmation_timezone(timezone_name: Optional[str]) -> Optional[str]:
    """Validate an explicitly supplied IANA zone, including UTC-family zones."""
    tz = str(timezone_name).strip() if timezone_name is not None else ''
    if not tz:
        return None
    try:
        ZoneInfo(tz)
        return tz
    except Exception:
        return None


def _normalize_location_key(location: Optional[str]) -> str:
    return " ".join(str(location or "").strip().lower().split())


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


def _coords_from_chart_data(chart_data: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(chart_data, dict):
        return None
    try:
        tz_info = chart_data.get("timezone_info")
        coords = tz_info.get("coordinates") if isinstance(tz_info, dict) else None
        if not isinstance(coords, dict):
            return None
        lat = float(coords.get("latitude"))
        lon = float(coords.get("longitude"))
    except Exception:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return (lat, lon)


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
    lookup_coords: bool = True,
) -> Optional[str]:
    tz = str(timezone_name).strip() if timezone_name is not None else None
    if tz and (not _is_placeholder_tz(tz)):
        try:
            ZoneInfo(tz)
            return tz
        except Exception:
            tz = None
    if coords is None and location and lookup_coords:
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


def _time_resolution_candidates(context: Any) -> List[Dict[str, Any]]:
    if not isinstance(context, dict):
        return []
    candidates: List[Dict[str, Any]] = []
    for row in context.get('wall_time_candidates') or []:
        if not isinstance(row, dict):
            continue
        local_datetime = row.get('local_datetime')
        utc_offset = None
        try:
            local_parsed = _parse_iso_datetime(local_datetime)
            offset = local_parsed.utcoffset()
            if offset is not None:
                total_minutes = int(offset.total_seconds() // 60)
                sign = '+' if total_minutes >= 0 else '-'
                hours, minutes = divmod(abs(total_minutes), 60)
                utc_offset = f'{sign}{hours:02d}:{minutes:02d}'
        except Exception:
            pass
        candidates.append({
            'fold': row.get('fold'),
            'local_datetime': local_datetime,
            'utc_offset': utc_offset,
            'instant_utc': row.get('instant_utc'),
            'valid': bool(row.get('round_trip_matches')),
        })
    return candidates


def _strict_confirmed_local_time_context(
    dt_raw: Any,
    timezone_name: str,
    *,
    source_field: str = 'local_datetime',
) -> Dict[str, Any]:
    """Resolve a local civil time without guessing through DST or bad offsets."""
    context = canonical_time_context(
        dt_raw,
        timezone_name,
        source_field=source_field,
        legacy_local_wall_time=True,
    )
    status = context.get('wall_time_status')
    candidates = _time_resolution_candidates(context)
    if status == 'missing_time':
        raise LocalTimeResolutionError(
            'local_datetime must include an explicit time (YYYY-MM-DDTHH:MM).',
            code='missing_local_time',
            timezone_name=timezone_name,
            input_value=dt_raw,
            wall_time_status=status,
            candidates=candidates,
        )

    try:
        parsed = _parse_iso_datetime(dt_raw)
    except Exception as exc:
        raise LocalTimeResolutionError(
            'local_datetime must be a valid ISO-8601 date and time.',
            code='invalid_local_datetime',
            timezone_name=timezone_name,
            input_value=dt_raw,
            wall_time_status=status,
            candidates=candidates,
        ) from exc

    if parsed.tzinfo is None:
        if context.get('ambiguous'):
            code = (
                'ambiguous_local_time'
                if status == 'ambiguous_fold'
                else (
                    'nonexistent_local_time'
                    if status == 'nonexistent_gap'
                    else 'invalid_local_datetime'
                )
            )
            message = {
                'ambiguous_local_time': (
                    f'Local time {dt_raw} occurs twice in {timezone_name}. '
                    'Provide an offset-aware local_datetime using one of the listed offsets.'
                ),
                'nonexistent_local_time': (
                    f'Local time {dt_raw} does not exist in {timezone_name} because '
                    'of a daylight-saving transition.'
                ),
                'invalid_local_datetime': (
                    'local_datetime must be a valid ISO-8601 date and time.'
                ),
            }[code]
            raise LocalTimeResolutionError(
                message,
                code=code,
                timezone_name=timezone_name,
                input_value=dt_raw,
                wall_time_status=status,
                candidates=candidates,
            )
        if not context.get('instant_utc'):
            raise LocalTimeResolutionError(
                'local_datetime could not be resolved in the supplied timezone.',
                code='invalid_local_datetime',
                timezone_name=timezone_name,
                input_value=dt_raw,
                wall_time_status=status,
                candidates=candidates,
            )
        return context

    # An aware confirmed-local value must describe the same wall clock and
    # offset that the supplied IANA zone had at that instant.  This lets an
    # explicit offset select either side of a repeated fall-back hour.
    wall_context = canonical_time_context(
        parsed.replace(tzinfo=None),
        timezone_name,
        source_field=source_field,
        legacy_local_wall_time=True,
    )
    wall_candidates = _time_resolution_candidates(wall_context)
    input_instant = parsed.astimezone(timezone.utc).isoformat()
    matching = [
        row
        for row in wall_candidates
        if row.get('valid') and row.get('instant_utc') == input_instant
    ]
    if not matching:
        valid_candidates = [row for row in wall_candidates if row.get('valid')]
        wall_status = wall_context.get('wall_time_status')
        if not valid_candidates and wall_status == 'nonexistent_gap':
            code = 'nonexistent_local_time'
            message = (
                f'Local time {parsed.replace(tzinfo=None).isoformat()} does not exist '
                f'in {timezone_name} because of a daylight-saving transition.'
            )
        else:
            code = 'timezone_offset_mismatch'
            message = (
                'The UTC offset in local_datetime does not match the supplied '
                f'IANA timezone ({timezone_name}) at that local wall time.'
            )
        raise LocalTimeResolutionError(
            message,
            code=code,
            timezone_name=timezone_name,
            input_value=dt_raw,
            wall_time_status=wall_status,
            candidates=wall_candidates,
        )

    selected = matching[0]
    aware_context = canonical_time_context(
        parsed,
        timezone_name,
        source_field=source_field,
        legacy_local_wall_time=False,
    )
    aware_context.update({
        'interpretation': 'confirmed_local_civil_time_with_iana_zone',
        'wall_time_status': (
            'ambiguous_fold_resolved_by_offset'
            if len([row for row in wall_candidates if row.get('valid')]) > 1
            else 'unique'
        ),
        'wall_time_candidates': copy.deepcopy(
            wall_context.get('wall_time_candidates') or []
        ),
        'selected_fold': selected.get('fold'),
        'supplied_utc_offset': selected.get('utc_offset'),
    })
    return aware_context


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

    strict_timezone = resolved_tz or 'UTC'
    context = _strict_confirmed_local_time_context(
        dt_raw,
        strict_timezone,
        source_field='datetime',
    )
    instant = _parse_iso_datetime(context.get('instant_utc'))
    return instant.astimezone(timezone.utc), strict_timezone


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
    *,
    trust_settings: bool = True,
) -> Optional[Tuple[float, float]]:
    if not location:
        return None
    if trust_settings:
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


def _legacy_snap_coords_from_location(location: Optional[str]) -> Optional[Tuple[float, float]]:
    """SNAP_COMPAT_READER: only resolve old saved snaps/charts that predate lat/lon storage."""
    return _ensure_coords_for_location(location, trust_settings=False)


@astro_clock_bp.route('/planetary-hours', methods=['GET'])
@_error_handler
def get_planetary_hours():
    eng = _engine_instance()
    data, active_settings = _data_for_optional_confirmed_snap(eng)
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
        if active_location:
            raise LocationError(f"Unable to resolve location for planetary hours: {active_location}")
        raise LocationError("Planetary hours require a resolved location")
    else:
        lat, lon = coords
    calc = _ph_instance(lat, lon)
    tz = _resolve_timezone_for_context(
        active_timezone,
        active_location,
        coords=(lat, lon),
    ) or 'UTC'
    target_local = _localize(target_dt, tz)
    daily = calc.calculate_daily_hours_for_local_date(target_local.date(), tz)
    # try locate current hour
    try:
        daily.current_hour = calc.get_planetary_hour_for_local_datetime(target_local, tz)
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
        return Path(explicit_dir) / "snaps_store.json"
    local_appdata = (os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or "").strip()
    if local_appdata:
        base = Path(local_appdata) / "VoxStella"
    else:
        base = Path(tempfile.gettempdir()) / "VoxStella"
    return base / "backend" / "snaps_store.json"


def _legacy_snap_store_path() -> Optional[Path]:
    """Return the pre-backend-subfolder snap store path for migration."""
    if (os.environ.get("HORARY_DATA_DIR") or "").strip():
        return None
    local_appdata = (os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or "").strip()
    if local_appdata:
        base = Path(local_appdata) / "VoxStella"
    else:
        base = Path(tempfile.gettempdir()) / "VoxStella"
    return base / "snaps_store.json"


def _snaps() -> SnapStore:
    global _snap_store
    if _snap_store is None:
        try:
            max_snaps = int(os.environ.get("HORARY_MAX_SNAPS", "500"))
        except Exception:
            max_snaps = 500
        snap_path = _snap_store_path()
        store = SnapStore(str(snap_path), max_snaps=max_snaps, auto_migrate=True)
        legacy_path = _legacy_snap_store_path()
        if legacy_path and legacy_path != snap_path and legacy_path.exists():
            try:
                store.import_legacy(str(legacy_path))
            except Exception as exc:
                logger.warning(
                    "Legacy Astro Clock snaps were not imported because the source "
                    "could not be preserved safely: %s",
                    exc,
                )
        _snap_store = store
    return _snap_store


def preview_snap_store_migration(*, include_document: bool = False) -> Dict[str, Any]:
    """Dry-run the real store migration without changing the snap document."""
    snap_path = _snap_store_path()
    if not snap_path.exists():
        empty_document = {
            'schema_version': SNAP_RECORD_SCHEMA_VERSION,
            'snaps': [],
            'tombstones': {},
            'legacy_imports': {},
        }
        preview = {
            'changed': False,
            'path': str(snap_path),
            'from_schema_version': None,
            'to_schema_version': SNAP_RECORD_SCHEMA_VERSION,
            'report': {
                'record_count': 0,
                'migrated_records': 0,
                'semantic_duplicate_groups': [],
                'duplicates_removed': 0,
            },
            'review_required_ids': [],
        }
        if include_document:
            preview['document'] = empty_document
        return preview
    store = SnapStore(str(snap_path), auto_migrate=False)
    return store.preview_migration(include_document=include_document)


def initialize_snap_store_migration() -> Dict[str, Any]:
    """Initialize, back up, migrate, and import the user snap store."""
    store = _snaps()
    return store.migration_report()


def _settings_for_payload_clock_context(
    eng: AstroClockEngine,
    payload: Any,
) -> Tuple[AstroClockSettings, bool]:
    """Resolve POST body clock settings without generating a chart."""
    body = payload if isinstance(payload, dict) else {}
    q_mode = str(body.get('mode') or '').strip().lower()
    q_dt = body.get('datetime')
    q_loc = body.get('location')
    q_tz = body.get('timezone')
    q_house = body.get('house_system_code') or body.get('house_system') or body.get('houseSystem')
    q_coords = _coords_from_request_args(body, strict=True)

    use_override = bool(q_mode or q_dt or q_loc or q_tz or q_house or q_coords)
    with _engine_lock:
        prev = copy.copy(eng.settings)
    if not use_override:
        return prev, False

    local_location = q_loc or prev.location
    location_changed = bool(q_loc) and not _settings_match_location(prev, local_location)
    local_coords = q_coords
    explicit_tz = _valid_explicit_timezone(q_tz)
    if local_coords is None:
        if q_loc and not explicit_tz:
            local_coords = _ensure_coords_for_location(local_location, trust_settings=False)
        else:
            local_coords = _coords_from_settings(prev) if _settings_match_location(prev, local_location) else None
    if q_tz is not None or q_loc or q_coords:
        if local_coords is None and local_location and not explicit_tz and not (q_tz and not _is_placeholder_tz(q_tz)):
            local_coords = _ensure_coords_for_location(local_location, trust_settings=not bool(q_loc))
        local_tz = _resolve_timezone_for_context(
            q_tz,
            local_location,
            coords=local_coords,
            lookup_coords=False,
        ) or (None if location_changed else prev.timezone)
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
        custom_override, normalized_tz = _normalize_manual_datetime(
            q_dt,
            timezone_name=local_tz or q_tz,
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
        coords = local_coords or _ensure_coords_for_location(
            local.location,
            settings_hint=local,
            trust_settings=not bool(q_loc),
        )
        if coords:
            lat, lon = coords
            guess = _tz_instance().get_timezone_for_location(lat, lon)
            if guess:
                local.timezone = guess

    return local, True


def _data_for_payload_clock_context(eng: AstroClockEngine, payload: Any):
    """Resolve Astro Clock data from a POST body without mutating engine state."""
    local, use_override = _settings_for_payload_clock_context(eng, payload)
    if not use_override:
        data = eng.get_current_data()
        active_settings = getattr(data, 'settings', None) or eng.settings
        return data, active_settings

    data = eng.get_current_data(settings=local)
    active_settings = getattr(data, 'settings', None) or local
    return data, active_settings


@astro_clock_bp.route('/snap', methods=['POST'])
@_error_handler
def create_snap():
    eng = _engine_instance()
    payload = request.get_json() or {}
    payload_dashboard = _dashboard_from_snap_payload(payload)
    certification_payload = _normalize_snap_certification_payload(
        payload.get('certification')
        or ((payload_dashboard or {}).get('certification') if isinstance(payload_dashboard, dict) else None)
    )
    try:
        if payload_dashboard is not None:
            active_settings, _use_override = _settings_for_payload_clock_context(eng, payload)
            timestamp = _timestamp_from_snap_dashboard(payload_dashboard, active_settings, eng)
            dash = _apply_snap_dashboard_context(payload_dashboard, timestamp, active_settings)
            chart_result = _chart_result_from_snap_dashboard(dash)
            data = SimpleNamespace(
                timestamp=timestamp,
                settings=active_settings,
                chart_result=chart_result,
                moon_state=None,
                dispositor_chains={},
                current_aspects=[],
            )
        else:
            data, active_settings = _data_for_payload_clock_context(eng, payload)
    except LocationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    label = payload.get('label') or 'Snapshot'
    include_modern = bool(payload.get('include_modern'))
    special_degrees = _normalize_special_degree_tokens(payload.get('special_degrees'))
    if payload_dashboard is None:
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
    else:
        chart_snapshot = _synastry_chart_snapshot_from_dashboard(dash)
    if certification_payload:
        dash['certification'] = copy.deepcopy(certification_payload)
    certification_summary = _snap_certification_summary(certification_payload)
    profile_hint = _extract_synastry_profile_hint(
        payload,
        chart_result if isinstance(chart_result, dict) else {},
        chart_snapshot,
    )
    active_location = getattr(active_settings, 'location', None) or eng.settings.location
    active_timezone = getattr(active_settings, 'timezone', None) or eng.settings.timezone
    payload_coords = _snap_coordinate_pair(payload)
    dashboard_coords = _snap_coordinate_pair(payload_dashboard) if payload_dashboard else None
    active_coords = _coords_from_settings(active_settings)
    coordinate_origin = None
    if payload_coords is not None:
        coordinate_origin = 'request_coordinates'
    elif dashboard_coords is not None:
        coordinate_origin = 'applied_dashboard'
    elif active_coords is not None:
        coordinate_origin = 'runtime_chart_context'
    if active_coords is None and active_location:
        active_coords = _ensure_coords_for_location(active_location, settings_hint=active_settings)
        if active_coords is not None:
            coordinate_origin = 'geocoder'
    coordinate_provenance = {
        'source': coordinate_origin or 'missing',
        'persisted_with_chart': bool(active_coords is not None),
        'inferred_at_read_time': False,
        'inferred_during_calculation': coordinate_origin == 'geocoder',
        'review_required': active_coords is None,
    }

    # Summary for listing/search
    # Planetary hour ruler
    hour_ruler = None
    try:
        coords = active_coords
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
    summary = {
        'hour_ruler': hour_ruler,
        'moon_sign': moon_sign,
        'chart_sect': (sect_info or {}).get('chart_sect'),
        'sect_light': (sect_info or {}).get('sect_light'),
        'profile_hint': profile_hint,
    }
    if certification_summary:
        summary['certification'] = certification_summary

    snap = {
        'schema_version': SNAP_RECORD_SCHEMA_VERSION,
        'id': str(uuid4()),
        'label': label,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'effective_datetime': (
            data.timestamp.astimezone(timezone.utc).isoformat()
            if getattr(data.timestamp, 'tzinfo', None) is not None
            else data.timestamp.replace(tzinfo=timezone.utc).isoformat()
        ),
        'location': active_location,
        'timezone': active_timezone,
        'timezone_label': (
            timezone_label_for_instant(active_timezone, data.timestamp)
            or dash.get('timezone_label')
        ),
        'latitude': (active_coords[0] if active_coords else None),
        'longitude': (active_coords[1] if active_coords else None),
        'coordinate_provenance': coordinate_provenance,
        'special_degrees': special_degrees,
        'summary': summary,
        'chart_snapshot': chart_snapshot,
        'dashboard': dash,
    }
    if profile_hint:
        snap['profile_hint'] = profile_hint
    if certification_payload:
        snap['certification'] = certification_payload
    snap = canonicalize_snapshot_record(snap)
    store = _snaps()
    idempotency_key = str(
        payload.get('idempotency_key')
        or request.headers.get('Idempotency-Key')
        or ''
    ).strip() or None
    add_method = getattr(store, 'add')
    supports_idempotency = False
    try:
        supports_idempotency = 'idempotency_key' in inspect.signature(add_method).parameters
    except Exception:
        supports_idempotency = False
    stored_snap = (
        add_method(snap, idempotency_key=idempotency_key)
        if supports_idempotency
        else add_method(snap)
    )
    if not isinstance(stored_snap, dict):
        stored_snap = snap
    return _json_ok({
        'id': stored_snap.get('id') or snap['id'],
        'label': stored_snap.get('label') or label,
        'schema_version': stored_snap.get('schema_version'),
        'effective_datetime': stored_snap.get('effective_datetime'),
        'local_datetime': stored_snap.get('local_datetime'),
    })


@astro_clock_bp.route('/snaps', methods=['GET'])
@_error_handler
def list_snaps():
    store = _snaps()
    items = []
    for raw_snap in store.list():
        snap = _hydrate_snap_payload(raw_snap, infer_coordinates=False)
        if not snap:
            continue
        dashboard = snap.get('dashboard') if isinstance(snap, dict) else {}
        timezone_value = snap.get('timezone') or (dashboard or {}).get('timezone')
        timezone_label = snap.get('timezone_label') or (dashboard or {}).get('timezone_label')
        latitude = snap.get('latitude')
        longitude = snap.get('longitude')
        certification_payload = _normalize_snap_certification_payload(
            snap.get('certification') or (dashboard or {}).get('certification')
        )
        certification_summary = (snap.get('summary') or {}).get('certification') or _snap_certification_summary(certification_payload)
        summary = {
            **(snap.get('summary') or {}),
            'profile_hint': snap.get('profile_hint') or (snap.get('summary') or {}).get('profile_hint'),
        }
        if certification_summary:
            summary['certification'] = certification_summary
        items.append({
            'id': snap.get('id'),
            'label': snap.get('label'),
            'schema_version': snap.get('schema_version'),
            'effective_datetime': snap.get('effective_datetime'),
            'local_datetime': snap.get('local_datetime'),
            'location': snap.get('location'),
            'timezone': timezone_value,
            'timezone_label': timezone_label,
            'coordinate_provenance': snap.get('coordinate_provenance'),
            'calculation_context': snap.get('calculation_context'),
            'resolved_context': snap.get('resolved_context'),
            'duplicate_group': snap.get('duplicate_group'),
            'superseded_by': snap.get('superseded_by'),
            'summary': summary,
            'special_degrees': snap.get('special_degrees') or [],
            'dashboard': {
                'timezone': timezone_value,
                'timezone_label': timezone_label,
                'latitude': latitude if latitude is not None else (dashboard or {}).get('latitude'),
                'longitude': longitude if longitude is not None else (dashboard or {}).get('longitude'),
            },
        })
    # Frontend expects success flag and top-level items
    from flask import jsonify as _j
    migration_report = (
        store.migration_report()
        if callable(getattr(store, 'migration_report', None))
        else {}
    )
    return _j({
        'success': True,
        'items': items,
        'migration_report': migration_report,
    })


def _hydrate_snap_payload(
    snap: Any,
    *,
    infer_coordinates: bool = True,
) -> Optional[Dict[str, Any]]:
    if not isinstance(snap, dict):
        return None
    hydrated = canonicalize_snapshot_record(snap)
    dashboard = hydrated.get('dashboard') if isinstance(hydrated.get('dashboard'), dict) else {}
    dashboard = dict(dashboard)

    timestamp_value = hydrated.get('effective_datetime') or dashboard.get('timestamp')
    location_value = hydrated.get('location') or dashboard.get('location')
    coords = _snap_coordinate_pair(hydrated, dashboard)
    coordinate_provenance = dict(hydrated.get('coordinate_provenance') or {})
    saved_coords = coords is not None and bool(
        coordinate_provenance.get('persisted_with_chart', True)
    )
    inferred_coords = None
    if coords is None and location_value and infer_coordinates:
        inferred_coords = _legacy_snap_coords_from_location(location_value)
        coords = inferred_coords
        if inferred_coords is not None:
            coordinate_provenance = {
                'source': 'inferred_from_saved_location',
                'persisted_with_chart': False,
                'inferred_at_read_time': True,
                'location_specificity': (
                    (hydrated.get('coordinate_provenance') or {}).get('location_specificity')
                    or 'unknown'
                ),
                'review_required': True,
            }

    timezone_value = hydrated.get('timezone') or dashboard.get('timezone')
    if not timezone_value and infer_coordinates:
        timezone_value = _resolve_timezone_for_context(
            None,
            location_value,
            coords=coords,
            lookup_coords=infer_coordinates,
        )
    timezone_label = (
        timezone_label_for_instant(timezone_value, timestamp_value)
        if timezone_value and timestamp_value
        else None
    ) or timezone_value
    certification_payload = _normalize_snap_certification_payload(
        hydrated.get('certification') or dashboard.get('certification')
    )

    hydrated['effective_datetime'] = timestamp_value
    hydrated['location'] = location_value
    hydrated['timezone'] = timezone_value
    hydrated['timezone_label'] = timezone_label
    hydrated['latitude'] = float(coords[0]) if coords else None
    hydrated['longitude'] = float(coords[1]) if coords else None
    hydrated['coordinate_provenance'] = coordinate_provenance
    resolved_context = dict(hydrated.get('resolved_context') or {})
    resolved_context.update({
        'latitude': float(coords[0]) if coords else None,
        'longitude': float(coords[1]) if coords else None,
        'timezone': timezone_value,
        'timezone_label': timezone_label,
        'coordinate_provenance': copy.deepcopy(coordinate_provenance),
        'chart_native': bool(saved_coords),
    })
    hydrated['resolved_context'] = resolved_context
    dashboard['timestamp'] = dashboard.get('timestamp') or timestamp_value
    dashboard['location'] = dashboard.get('location') or location_value
    dashboard['timezone'] = timezone_value
    dashboard['timezone_label'] = timezone_label
    if saved_coords:
        dashboard['latitude'] = float(coords[0])
        dashboard['longitude'] = float(coords[1])
        dashboard['coordinate_provenance'] = copy.deepcopy(coordinate_provenance)
    if certification_payload:
        hydrated['certification'] = certification_payload
        dashboard['certification'] = certification_payload
        summary = dict(hydrated.get('summary') or {})
        summary.setdefault('certification', _snap_certification_summary(certification_payload))
        hydrated['summary'] = summary
    hydrated['dashboard'] = dashboard
    return hydrated


def _saved_snap_context_blocking_reasons(snap: Any) -> List[str]:
    """Return reasons a saved chart is unsafe to reuse for a fresh calculation."""
    if not isinstance(snap, dict):
        return ['saved chart context is unavailable']

    context = (
        snap.get('calculation_context')
        if isinstance(snap.get('calculation_context'), dict)
        else {}
    )
    time_provenance = (
        context.get('time_provenance')
        if isinstance(context.get('time_provenance'), dict)
        else {}
    )
    coordinate_provenance = (
        snap.get('coordinate_provenance')
        if isinstance(snap.get('coordinate_provenance'), dict)
        else (
            context.get('coordinate_provenance')
            if isinstance(context.get('coordinate_provenance'), dict)
            else {}
        )
    )

    reasons: List[str] = []
    if str(snap.get('superseded_by') or '').strip():
        reasons.append('saved chart was superseded by a corrected copy')
    if context.get('review_required'):
        reasons.append('legacy place/time context still requires review')
    if time_provenance.get('ambiguous'):
        reasons.append('birth time is ambiguous or nonexistent in the saved timezone')

    timezone_name = context.get('timezone') or snap.get('timezone')
    try:
        ZoneInfo(str(timezone_name).strip()) if timezone_name else None
        valid_timezone = bool(timezone_name)
    except Exception:
        valid_timezone = False
    if not valid_timezone:
        reasons.append('saved birth context has no valid IANA timezone')

    instant_raw = context.get('instant_utc') or snap.get('effective_datetime')
    try:
        instant = _parse_iso_datetime(instant_raw) if instant_raw else None
    except Exception:
        instant = None
    if instant is None or instant.tzinfo is None:
        reasons.append('saved birth time has no confirmed UTC instant')

    coords = _snap_coordinate_pair(snap, snap.get('dashboard'))
    coordinates_persisted = (
        coordinate_provenance.get('persisted_with_chart') is True
        if 'persisted_with_chart' in coordinate_provenance
        else coords is not None
    )
    if (
        coords is None
        or not coordinates_persisted
        or coordinate_provenance.get('inferred_at_read_time')
        or coordinate_provenance.get('review_required')
    ):
        reasons.append('birth coordinates were not confirmed with the saved chart')

    return list(dict.fromkeys(reasons))


def _require_confirmed_saved_snap_context(
    snap: Any,
    *,
    feature_label: str,
) -> None:
    """Prevent uncertain migrated context from silently driving a new model."""
    reasons = _saved_snap_context_blocking_reasons(snap)
    if not reasons:
        return
    raise ValueError(
        f"{feature_label} cannot use this saved chart because "
        f"{'; '.join(reasons)}. Confirm/correct the saved context first with "
        "the specific birthplace, saved coordinates, local civil time, and "
        "IANA timezone."
    )


@astro_clock_bp.route('/snaps/<snap_id>', methods=['GET'])
@_error_handler
def get_snap(snap_id: str):
    store = _snaps()
    snap = _hydrate_snap_payload(store.get(snap_id), infer_coordinates=False)
    if not snap:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'snap': snap})


def _recast_snap_summary(
    bundle: Dict[str, Any],
    *,
    instant_utc: datetime,
    timezone_name: str,
    latitude: float,
    longitude: float,
    profile_hint: Optional[str],
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Rebuild every summary value that is valid for the replacement chart."""
    chart_data = (
        bundle.get('chart_data')
        if isinstance(bundle.get('chart_data'), dict)
        else {}
    )
    planets = _normalized_planet_rows(chart_data.get('planets'))
    moon = next(
        (
            row for row in planets
            if str(row.get('planet') or row.get('name') or '').strip().lower()
            == 'moon'
        ),
        None,
    )
    moon_sign = moon.get('sign') if isinstance(moon, dict) else None
    if not moon_sign and isinstance(moon, dict):
        try:
            sign_names = (
                'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius',
                'Pisces',
            )
            moon_sign = sign_names[int(float(moon.get('longitude')) % 360 // 30)]
        except Exception:
            moon_sign = None

    sect_info = None
    try:
        sect_info = compute_sect_info(chart_data)
    except Exception:
        sect_info = None

    hour_ruler = None
    try:
        local_datetime = instant_utc.astimezone(ZoneInfo(timezone_name))
        planetary_hour = _ph_instance(latitude, longitude).get_current_planetary_hour(
            local_datetime
        )
        if planetary_hour:
            hour_ruler = getattr(planetary_hour.ruling_planet, 'value', None)
    except Exception:
        hour_ruler = None

    return {
        'hour_ruler': hour_ruler,
        'moon_sign': moon_sign,
        'chart_sect': (sect_info or {}).get('chart_sect'),
        'sect_light': (sect_info or {}).get('sect_light'),
        'profile_hint': profile_hint,
        'recast_context_status': 'recomputed',
    }, profile_hint


def recast_snap_with_confirmed_context(
    snap_id: str,
    *,
    local_datetime: Any,
    timezone_name: str,
    location: str,
    latitude: float,
    longitude: float,
    house_system_code: str = 'R',
    include_modern: bool = True,
    include_chiron: bool = True,
    persist: bool = False,
) -> Dict[str, Any]:
    """Build a coherent replacement snap from explicitly confirmed context.

    ``persist=False`` is a dry run.  When persistence is requested the legacy
    record is preserved and marked ``superseded_by``; it is never overwritten.
    """
    store = _snaps()
    raw_snap = store.get(snap_id)
    if not isinstance(raw_snap, dict):
        raise ValueError('Saved snap not found')
    confirmed_location = str(location or '').strip()
    if not confirmed_location:
        raise ValueError('A specific confirmed location is required')
    if is_generic_location_label(confirmed_location):
        raise ValueError(
            'A specific city or place is required. A country or broad region '
            'cannot confirm birth coordinates.'
        )
    coords = _coords_from_request_args({
        'latitude': latitude,
        'longitude': longitude,
    }, strict=True)
    if coords is None:
        raise ValueError('Confirmed latitude and longitude are required')
    valid_timezone = _valid_confirmation_timezone(timezone_name)
    if not valid_timezone:
        raise ValueError('A valid IANA timezone is required for context confirmation')
    confirmed_time = _strict_confirmed_local_time_context(
        local_datetime,
        valid_timezone,
        source_field='confirmed_local_datetime',
    )
    instant_utc = _parse_iso_datetime(confirmed_time.get('instant_utc'))
    if instant_utc is None:
        raise ValueError('A confirmed local date and time is required')
    resolved_timezone = valid_timezone
    local_aware = instant_utc.astimezone(ZoneInfo(resolved_timezone))
    effective_house_system = (
        _validated_astrocartography_house_system_code(
            house_system_code,
            default='R',
        )
        or 'R'
    )
    bundle = _compute_chart_bundle_for(
        instant_utc.isoformat(),
        confirmed_location,
        resolved_timezone,
        house_system_code=effective_house_system,
        latitude=coords[0],
        longitude=coords[1],
        include_modern=include_modern,
        include_chiron=include_chiron,
    )
    chart_data = copy.deepcopy(bundle.get('chart_data') or {})
    chart_snapshot = _synastry_chart_snapshot_from_chart_data(chart_data)
    chart_snapshot['house_system_code'] = effective_house_system
    dashboard = {
        'timestamp': instant_utc.isoformat(),
        'local_datetime': local_aware.isoformat(),
        'location': confirmed_location,
        'timezone': resolved_timezone,
        'timezone_label': timezone_label_for_instant(
            resolved_timezone,
            instant_utc,
        ),
        'latitude': coords[0],
        'longitude': coords[1],
        'house_system_code': effective_house_system,
        'planets': copy.deepcopy(chart_snapshot.get('planets') or []),
        'house_cusps': copy.deepcopy(chart_snapshot.get('house_cusps') or []),
        'ascendant': chart_snapshot.get('ascendant'),
        'midheaven': chart_snapshot.get('midheaven'),
        'house_rulers': copy.deepcopy(chart_snapshot.get('house_rulers') or {}),
    }
    replacement_profile_hint = _extract_synastry_profile_hint(
        raw_snap,
        raw_snap.get('summary'),
    )
    replacement_special_degrees = _normalize_special_degree_tokens(
        raw_snap.get('special_degrees')
    )
    replacement_summary, replacement_profile_hint = _recast_snap_summary(
        bundle,
        instant_utc=instant_utc,
        timezone_name=resolved_timezone,
        latitude=coords[0],
        longitude=coords[1],
        profile_hint=replacement_profile_hint,
    )
    original_label = str(raw_snap.get('label') or 'Snapshot').strip()
    replacement = {
        'schema_version': SNAP_RECORD_SCHEMA_VERSION,
        'id': str(uuid4()),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'label': f'{original_label} (confirmed context)',
        'effective_datetime': instant_utc.isoformat(),
        'local_datetime': local_aware.isoformat(),
        'location': confirmed_location,
        'timezone': resolved_timezone,
        'timezone_label': dashboard['timezone_label'],
        'latitude': coords[0],
        'longitude': coords[1],
        'coordinate_provenance': {
            'source': 'user_confirmed_context_override',
            'persisted_with_chart': True,
            'inferred_at_read_time': False,
            'inferred_during_calculation': False,
            'location_specificity': 'specific',
            'review_required': False,
        },
        'calculation_context': {
            'instant_utc': instant_utc.isoformat(),
            'local_datetime': local_aware.isoformat(),
            'timezone': resolved_timezone,
            'timezone_label': dashboard['timezone_label'],
            'timezone_source': 'user_confirmed_context_override',
            'location': confirmed_location,
            'latitude': coords[0],
            'longitude': coords[1],
            'house_system_code': effective_house_system,
            'coordinate_provenance': {
                'source': 'user_confirmed_context_override',
                'persisted_with_chart': True,
                'inferred_at_read_time': False,
                'review_required': False,
            },
            'time_provenance': {
                **confirmed_time,
                'interpretation': 'confirmed_local_civil_time_with_iana_zone',
            },
            'conflicts': [],
            'review_required': False,
        },
        'special_degrees': replacement_special_degrees,
        'summary': replacement_summary,
        'chart_snapshot': chart_snapshot,
        'dashboard': dashboard,
        'recast_provenance': {
            'kind': 'confirmed_context_recast',
            'source_snap_id': snap_id,
            'engine': 'Swiss Ephemeris',
            'all_planets_houses_and_angles_recomputed_together': True,
            'legacy_source_preserved': True,
            'recomputed_fields': [
                'summary.hour_ruler',
                'summary.moon_sign',
                'summary.chart_sect',
                'summary.sect_light',
            ],
            'invalidated_fields': {
                'certification': (
                    'not carried because the certified birth context changed'
                ),
            },
            'preserved_user_metadata': {
                'special_degrees': bool(replacement_special_degrees),
                'profile_hint': bool(replacement_profile_hint),
            },
        },
    }
    if replacement_profile_hint:
        replacement['profile_hint'] = replacement_profile_hint
    replacement = canonicalize_snapshot_record(replacement)
    if persist:
        add_replacement = getattr(store, 'add_replacement', None)
        if not callable(add_replacement):
            raise RuntimeError('The configured snapshot store cannot preserve a replacement safely')
        return add_replacement(snap_id, replacement)
    return replacement


@astro_clock_bp.route('/snaps/<snap_id>/confirm-context', methods=['POST'])
@_error_handler
def confirm_snap_context(snap_id: str):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise ValueError('JSON object body is required')
    persist = _truthy_payload_flag(payload.get('persist'))
    replacement = recast_snap_with_confirmed_context(
        snap_id,
        local_datetime=payload.get('local_datetime') or payload.get('datetime'),
        timezone_name=str(payload.get('timezone') or '').strip(),
        location=str(payload.get('location') or '').strip(),
        latitude=payload.get('latitude'),
        longitude=payload.get('longitude'),
        house_system_code=str(
            payload.get('house_system_code')
            or payload.get('house_system')
            or 'R'
        ).strip(),
        include_modern=payload.get('include_modern', True) is not False,
        include_chiron=payload.get('include_chiron', True) is not False,
        persist=persist,
    )
    return _json_ok({
        'persisted': persist,
        'original_snap_id': snap_id,
        'original_preserved': True,
        'replacement': replacement,
    })


def _first_nonempty_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _truthy_payload_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _chinese_astrology_birth_context(payload: Dict[str, Any]):
    from chinese_astrology import BirthContext

    body = payload if isinstance(payload, dict) else {}
    nested_birth = body.get('birth') if isinstance(body.get('birth'), dict) else {}
    snap_id = _first_nonempty_text(
        body.get('snap_id'),
        body.get('natal_snap_id'),
        nested_birth.get('snap_id'),
        request.args.get('snap_id'),
        request.args.get('natal_snap_id'),
    )
    snap = None
    source = 'direct_input'
    snap_label = None
    if snap_id:
        snap = _hydrate_snap_payload(
            _snaps().get(snap_id),
            infer_coordinates=False,
        )
        if not snap:
            raise ValueError('Saved snap not found')
        _require_confirmed_saved_snap_context(
            snap,
            feature_label='Chinese Astrology',
        )
        source = 'saved_snap'
        snap_label = _first_nonempty_text(snap.get('label'), snap.get('id'), 'Saved snap')

    dashboard = snap.get('dashboard') if isinstance(snap, dict) and isinstance(snap.get('dashboard'), dict) else {}
    dt_raw = _first_nonempty_text(
        snap.get('effective_datetime') if snap else None,
        dashboard.get('timestamp') if snap else None,
        body.get('datetime'),
        body.get('birth_datetime'),
        body.get('natal_datetime'),
        nested_birth.get('datetime'),
    )
    time_raw = _first_nonempty_text(
        body.get('time'),
        body.get('birth_time'),
        body.get('natal_time'),
        nested_birth.get('time'),
    )
    date_raw = _first_nonempty_text(
        body.get('date'),
        body.get('birth_date'),
        body.get('natal_date'),
        nested_birth.get('date'),
    )
    hour_known = True
    if not dt_raw:
        if not date_raw:
            raise ValueError('Birth date/time or saved snap is required')
        hour_known = bool(time_raw)
        dt_raw = f"{date_raw}T{time_raw or '12:00'}"

    location = _first_nonempty_text(
        snap.get('location') if snap else None,
        dashboard.get('location') if snap else None,
        body.get('location'),
        body.get('birth_location'),
        body.get('natal_location'),
        nested_birth.get('location'),
    )
    timezone_name = _first_nonempty_text(
        snap.get('timezone') if snap else None,
        dashboard.get('timezone') if snap else None,
        snap.get('timezone_label') if snap else None,
        dashboard.get('timezone_label') if snap else None,
        body.get('timezone'),
        body.get('birth_timezone'),
        body.get('natal_timezone'),
        nested_birth.get('timezone'),
    )
    coords = None
    if snap:
        coords = _coords_from_request_args(snap) or _coords_from_request_args(dashboard)
    if coords is None:
        coords = _coords_from_request_args(body, strict=False) or _coords_from_request_args(nested_birth, strict=False)
    if coords is not None:
        timezone_name = _resolve_timezone_for_context(
            timezone_name,
            location,
            coords=coords,
            lookup_coords=False,
        ) or timezone_name

    dt_utc, resolved_timezone = _normalize_manual_datetime(
        dt_raw,
        timezone_name=timezone_name,
        location=location,
    )
    if dt_utc is None:
        raise ValueError('Birth date/time is required')
    timezone_final = resolved_timezone or timezone_name or 'UTC'
    time_precision = _first_nonempty_text(
        snap.get('time_precision') if snap else None,
        body.get('time_precision'),
        nested_birth.get('time_precision'),
    ) or ('exact' if hour_known else 'unknown')
    if str(time_precision).strip().lower() == 'unknown':
        hour_known = False

    calculation_sex = _first_nonempty_text(
        body.get('calculation_sex'),
        body.get('sex'),
        body.get('gender'),
        nested_birth.get('calculation_sex'),
    )
    solar_time_mode = _first_nonempty_text(
        body.get('solar_time_mode'),
        body.get('hour_time_mode'),
        nested_birth.get('solar_time_mode'),
        nested_birth.get('hour_time_mode'),
    )
    use_true_solar_time = (
        _truthy_payload_flag(body.get('use_true_solar_time'))
        or _truthy_payload_flag(body.get('true_solar_time'))
        or _truthy_payload_flag(nested_birth.get('use_true_solar_time'))
        or str(solar_time_mode or '').strip().lower() in {
            'true_solar',
            'true_solar_time',
            'real_solar',
            'real_solar_time',
            'rst',
        }
    )
    day_boundary_rule = _first_nonempty_text(
        body.get('day_boundary_rule'),
        body.get('day_boundary'),
        nested_birth.get('day_boundary_rule'),
        nested_birth.get('day_boundary'),
    )
    if _truthy_payload_flag(body.get('true_solar_day_boundary')) or _truthy_payload_flag(nested_birth.get('true_solar_day_boundary')):
        day_boundary_rule = 'true_solar_midnight'
    hour_pillar_variant = _first_nonempty_text(
        body.get('hour_pillar_variant'),
        body.get('zi_hour_rule'),
        body.get('late_zi_rule'),
        nested_birth.get('hour_pillar_variant'),
        nested_birth.get('zi_hour_rule'),
    )
    if _truthy_payload_flag(body.get('late_zi_next_day')) or _truthy_payload_flag(nested_birth.get('late_zi_next_day')):
        hour_pillar_variant = 'late_zi_next_day'
    luck_direction_rule = _first_nonempty_text(
        body.get('luck_direction_rule'),
        body.get('luck_pillar_direction_rule'),
        nested_birth.get('luck_direction_rule'),
        nested_birth.get('luck_pillar_direction_rule'),
    )
    if coords is None and (use_true_solar_time or str(day_boundary_rule or '').strip().lower() in {'true_solar', 'true_solar_midnight', 'true_solar_date'}) and location:
        coords = _ensure_coords_for_location(location, trust_settings=False)
        if coords is not None:
            timezone_name = _resolve_timezone_for_context(
                timezone_name,
                location,
                coords=coords,
                lookup_coords=False,
            ) or timezone_name
            timezone_final = timezone_name or timezone_final

    missing_inputs: List[Dict[str, str]] = []
    if _truthy_payload_flag(body.get('include_luck_pillars')) and not calculation_sex:
        missing_inputs.append({
            'field': 'calculation_sex',
            'message': 'Calculation sex is required before Luck Pillars can be generated.',
        })

    return BirthContext(
        dt_utc=dt_utc,
        timezone=timezone_final,
        location=location,
        latitude=(coords[0] if coords else None),
        longitude=(coords[1] if coords else None),
        time_precision=str(time_precision),
        source=source,
        source_snap_id=snap_id,
        snap_label=snap_label,
        calculation_sex=calculation_sex,
        include_luck_pillars=_truthy_payload_flag(body.get('include_luck_pillars')),
        use_true_solar_time=use_true_solar_time,
        day_boundary_rule=day_boundary_rule or 'civil_midnight',
        hour_pillar_variant=hour_pillar_variant or 'standard_zi_hour',
        luck_direction_rule=luck_direction_rule or 'year_stem_polarity',
        hour_known=hour_known,
        missing_inputs=tuple(missing_inputs),
    )


def _chinese_astrology_solar_term_error_response(exc, *, participant=None):
    error_payload = exc.to_payload()
    if participant in {'primary', 'relationship'}:
        error_payload = {**error_payload, 'participant': participant}
    return jsonify({
        'success': False,
        'error': error_payload['code'],
        'detail': str(exc),
        'participant': participant if participant in {'primary', 'relationship'} else None,
        'calculation_error': error_payload,
    }), 503


@astro_clock_bp.route('/chinese-astrology/bazi', methods=['POST'])
@_error_handler
def chinese_astrology_bazi():
    from chinese_astrology import SolarTermCalculationError, build_bazi_profile

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({'success': False, 'error': 'JSON object body is required'}), 400
    try:
        context = _chinese_astrology_birth_context(payload)
        profile = build_bazi_profile(context)
    except SolarTermCalculationError as exc:
        return _chinese_astrology_solar_term_error_response(exc)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except LocationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    return _json_ok(profile)


@astro_clock_bp.route('/chinese-astrology/compatibility', methods=['POST'])
@_error_handler
def chinese_astrology_compatibility():
    from chinese_astrology import SolarTermCalculationError, analyze_pair_relationships, build_bazi_profile

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({'success': False, 'error': 'JSON object body is required'}), 400

    primary_snap_id = _first_nonempty_text(
        payload.get('primary_snap_id'),
        payload.get('snap_a_id'),
        payload.get('participant_a_snap_id'),
        payload.get('snap_id'),
        payload.get('natal_snap_id'),
        request.args.get('primary_snap_id'),
        request.args.get('snap_a_id'),
        request.args.get('participant_a_snap_id'),
    )
    relationship_snap_id = _first_nonempty_text(
        payload.get('relationship_snap_id'),
        payload.get('comparison_snap_id'),
        payload.get('snap_b_id'),
        payload.get('participant_b_snap_id'),
        request.args.get('relationship_snap_id'),
        request.args.get('comparison_snap_id'),
        request.args.get('snap_b_id'),
        request.args.get('participant_b_snap_id'),
    )
    relationship_context = _first_nonempty_text(
        payload.get('relationship_context'),
        payload.get('pair_context'),
        payload.get('relationship_type'),
        request.args.get('relationship_context'),
        request.args.get('pair_context'),
        request.args.get('relationship_type'),
    ) or 'general'
    legacy_calculation_sex = _first_nonempty_text(
        payload.get('calculation_sex'),
        payload.get('sex'),
        payload.get('gender'),
    )
    primary_calculation_sex = _first_nonempty_text(
        payload.get('primary_calculation_sex'),
        payload.get('primary_sex'),
        payload.get('participant_a_calculation_sex'),
        legacy_calculation_sex,
    )
    relationship_calculation_sex = _first_nonempty_text(
        payload.get('relationship_calculation_sex'),
        payload.get('relationship_sex'),
        payload.get('participant_b_calculation_sex'),
        legacy_calculation_sex,
    )
    primary_birth = payload.get('primary') if isinstance(payload.get('primary'), dict) else None
    relationship_birth = payload.get('relationship') if isinstance(payload.get('relationship'), dict) else None
    explicit_pair = primary_birth is not None and relationship_birth is not None
    if (primary_birth is None) != (relationship_birth is None):
        return jsonify({
            'success': False,
            'error': 'Both primary and relationship birth inputs are required for explicit compatibility',
        }), 400
    if not explicit_pair and (not primary_snap_id or not relationship_snap_id):
        return jsonify({
            'success': False,
            'error': 'Provide two explicit birth inputs or two saved snaps for Chinese Astrology compatibility',
        }), 400
    if not explicit_pair and str(primary_snap_id) == str(relationship_snap_id):
        return jsonify({'success': False, 'error': 'Choose two different saved snaps for Chinese Astrology compatibility'}), 400

    solar_term_participant = 'primary'
    try:
        if explicit_pair:
            primary_payload = {
                **payload,
                'birth': primary_birth,
                'snap_id': '',
                'natal_snap_id': '',
                'calculation_sex': primary_calculation_sex,
            }
            relationship_payload = {
                **payload,
                'birth': relationship_birth,
                'snap_id': '',
                'natal_snap_id': '',
                'calculation_sex': relationship_calculation_sex,
            }
        else:
            primary_payload = {
                **payload,
                'snap_id': primary_snap_id,
                'natal_snap_id': primary_snap_id,
                'calculation_sex': primary_calculation_sex,
            }
            relationship_payload = {
                **payload,
                'snap_id': relationship_snap_id,
                'natal_snap_id': relationship_snap_id,
                'calculation_sex': relationship_calculation_sex,
            }
        primary_profile = build_bazi_profile(_chinese_astrology_birth_context(primary_payload))
        solar_term_participant = 'relationship'
        relationship_profile = build_bazi_profile(_chinese_astrology_birth_context(relationship_payload))
        solar_term_participant = None
        compatibility = analyze_pair_relationships(
            primary_profile,
            relationship_profile,
            relationship_context=relationship_context,
        )
    except SolarTermCalculationError as exc:
        return _chinese_astrology_solar_term_error_response(
            exc,
            participant=solar_term_participant,
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except LocationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    return _json_ok({
        'primary': primary_profile,
        'relationship': relationship_profile,
        'compatibility': compatibility,
    })


@astro_clock_bp.route('/chinese-astrology/iching-oracle', methods=['POST'])
@_error_handler
def chinese_astrology_iching_oracle():
    from chinese_astrology import cast_iching_oracle

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({'success': False, 'error': 'JSON object body is required'}), 400
    try:
        oracle = cast_iching_oracle(
            question=payload.get('question') or '',
            method=payload.get('method') or payload.get('casting_method') or 'coins',
            lines=payload.get('lines'),
            coins=payload.get('coins'),
            seed=payload.get('seed'),
            coin_value_scheme=payload.get('coin_value_scheme') or payload.get('coinValueScheme') or 'heads_2_tails_3',
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    return _json_ok({'oracle': oracle})


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
    try:
        requested_coords = _coords_from_request_args(payload, strict=True)
    except LocationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    with _engine_lock:
        if mode == 'manual':
            dt = payload.get('datetime')
            tz = payload.get('timezone')
            loc = payload.get('location')
            house_code = payload.get('house_system_code') or payload.get('house_system')
            try:
                target_location = loc or eng.settings.location
                location_changed = bool(loc) and not _settings_match_location(eng.settings, target_location)
                coords = requested_coords
                coords_lookup_attempted = False
                explicit_tz = _valid_explicit_timezone(tz)
                if coords is None:
                    if loc and not explicit_tz:
                        coords_lookup_attempted = True
                        coords = _ensure_coords_for_location(target_location, trust_settings=False)
                    else:
                        coords = (
                            _coords_from_settings(eng.settings)
                            if _settings_match_location(eng.settings, target_location)
                            else None
                        )
                if coords is None and target_location and not explicit_tz and not (tz and not _is_placeholder_tz(tz)):
                    coords_lookup_attempted = True
                    coords = _ensure_coords_for_location(target_location, trust_settings=not bool(loc))
                resolved_tz = _resolve_timezone_for_context(
                    tz,
                    target_location,
                    coords=coords,
                    lookup_coords=False,
                )
                if coords is None and target_location and not resolved_tz and not coords_lookup_attempted:
                    coords = _ensure_coords_for_location(target_location, trust_settings=not bool(loc))
                    resolved_tz = _resolve_timezone_for_context(
                        tz,
                        target_location,
                        coords=coords,
                        lookup_coords=False,
                    )
                custom, resolved_tz = _normalize_manual_datetime(
                    dt,
                    timezone_name=resolved_tz,
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
                timezone=(resolved_tz or tz or (None if location_changed else eng.settings.timezone)),
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
            if loc or tz or requested_coords is not None:
                try:
                    realtime_location = loc or eng.settings.location
                    location_changed = bool(loc) and not _settings_match_location(eng.settings, realtime_location)
                    coords = requested_coords
                    coords_lookup_attempted = False
                    explicit_tz = _valid_explicit_timezone(tz)
                    if coords is None:
                        if loc and not explicit_tz:
                            coords_lookup_attempted = True
                            coords = _ensure_coords_for_location(realtime_location, trust_settings=False)
                        else:
                            coords = (
                                _coords_from_settings(eng.settings)
                                if _settings_match_location(eng.settings, realtime_location)
                                else None
                            )
                    if coords is None and realtime_location and not explicit_tz and not (tz and not _is_placeholder_tz(tz)):
                        coords_lookup_attempted = True
                        coords = _ensure_coords_for_location(realtime_location, trust_settings=not bool(loc))
                    realtime_tz = _resolve_timezone_for_context(
                        tz,
                        realtime_location,
                        coords=coords,
                        lookup_coords=False,
                    )
                    if coords is None and realtime_location and not realtime_tz and not coords_lookup_attempted:
                        coords = _ensure_coords_for_location(realtime_location, trust_settings=not bool(loc))
                        realtime_tz = _resolve_timezone_for_context(
                            tz,
                            realtime_location,
                            coords=coords,
                            lookup_coords=False,
                        )
                    realtime_tz = realtime_tz or (None if location_changed else eng.settings.timezone)
                    eng.set_mode(
                        eng.settings.mode.__class__.REALTIME,
                        location=realtime_location,
                        timezone=realtime_tz,
                        latitude=(coords[0] if coords else None),
                        longitude=(coords[1] if coords else None),
                    )
                except Exception as exc:
                    return jsonify({'success': False, 'error': str(exc) or 'Unable to update realtime location'}), 400
            else:
                eng.resume_realtime()
        updated_mode = eng.settings.mode.value
    return _json_ok({'mode': updated_mode})


@astro_clock_bp.route('/location', methods=['POST'])
@_error_handler
def set_location():
    payload = request.get_json() or {}
    loc = payload.get('location')
    if not loc:
        return jsonify({'success': False, 'error': 'location is required'}), 400
    eng = _engine_instance()
    # Resolve outside the shared-state critical section, then commit the
    # location, coordinates, and timezone as one coherent settings update.
    coords = _ensure_coords_for_location(loc, trust_settings=False)
    resolved_tz = None
    if coords:
        try:
            lat, lon = coords
            resolved_tz = _tz_instance().get_timezone_for_location(lat, lon)
        except Exception:
            coords = None
            resolved_tz = None
    with _engine_lock:
        eng.update_settings(
            location=loc,
            latitude=(coords[0] if coords else None),
            longitude=(coords[1] if coords else None),
            timezone=resolved_tz,
        )
        updated_location = eng.settings.location
        updated_timezone = eng.settings.timezone
    return _json_ok({
        'location': updated_location,
        'timezone': updated_timezone,
        'latitude': (coords[0] if coords else None),
        'longitude': (coords[1] if coords else None),
    })


@astro_clock_bp.route('/receptions', methods=['GET'])
@_error_handler
def get_receptions():
    """Return a compact receptions summary for the dashboard tile.

    If the horary engine didn't include detailed reception structures,
    compute them on the fly from the serialized chart using the
    TraditionalReceptionCalculator so dev parity matches packaged builds.
    """
    eng = _engine_instance()
    data, _active_settings = _data_for_optional_confirmed_snap(eng)
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    return _json_ok(_extract_receptions_payload(chart))


def _data_for_optional_confirmed_snap(
    eng: AstroClockEngine,
    *,
    house_system_override: Optional[str] = None,
) -> Tuple[Any, AstroClockSettings]:
    snap_id = str(request.args.get('snap_id') or '').strip()
    if not snap_id:
        if house_system_override is None:
            return _data_for_request_clock_context(eng)
        return _data_for_request_clock_context(
            eng,
            house_system_override=house_system_override,
        )
    bundle = _bundle_from_snap_id(
        snap_id,
        house_system_code=_validated_astrocartography_house_system_code(
            house_system_override
            or request.args.get('house_system_code')
            or request.args.get('house_system')
        ),
        missing_error='Saved snap not found',
    )
    meta = bundle.get('meta') if isinstance(bundle.get('meta'), dict) else {}
    chart_data = (
        bundle.get('chart_data')
        if isinstance(bundle.get('chart_data'), dict)
        else {}
    )
    chart_result = (
        dict(bundle.get('chart_result'))
        if isinstance(bundle.get('chart_result'), dict)
        else {}
    )
    chart_result['chart_data'] = copy.deepcopy(chart_data)
    if bundle.get('raw_chart') is not None:
        chart_result['_raw_chart'] = bundle.get('raw_chart')
    timestamp_raw = meta.get('timestamp') or meta.get('instant_utc')
    timestamp = _parse_iso_datetime(timestamp_raw)
    if timestamp.tzinfo is None:
        raise ValueError('Saved snap is missing a confirmed UTC instant')
    settings = AstroClockSettings(
        mode=ClockMode.MANUAL,
        location=meta.get('location'),
        custom_time=timestamp.astimezone(timezone.utc),
        timezone=meta.get('timezone'),
        latitude=meta.get('latitude'),
        longitude=meta.get('longitude'),
        paused_at=None,
        house_system_code=meta.get('house_system_code'),
    )
    data = SimpleNamespace(
        timestamp=timestamp.astimezone(timezone.utc),
        settings=settings,
        chart_result=chart_result,
        moon_state=None,
        dispositor_chains={},
        current_aspects=[],
    )
    return data, settings


def _directional_chart_data_for_scope(
    chart_data: Any,
    timestamp: Any,
    *,
    include_modern: bool,
) -> Dict[str, Any]:
    source = chart_data if isinstance(chart_data, dict) else {}
    if not include_modern:
        return source
    timestamp_iso = _directional_timestamp_iso(
        timestamp,
        label='Directional modern-body extension',
    )
    extended = _extend_chart_data_for_synastry(
        source,
        {'timestamp': timestamp_iso},
        include_modern=True,
        include_chiron=False,
    )
    return extended if isinstance(extended, dict) else source


@astro_clock_bp.route('/compass', methods=['GET'])
@_error_handler
def get_compass():
    """Return local-space compass bearings for the active chart context."""
    include_modern = (request.args.get('include_modern', '0').lower() in {'1', 'true', 'yes'})
    eng = _engine_instance()
    data, active_settings = _data_for_optional_confirmed_snap(eng)
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    cd = chart.get('chart_data', {}) if isinstance(chart, dict) else {}
    try:
        cd = _directional_chart_data_for_scope(
            cd,
            getattr(data, 'timestamp', None),
            include_modern=include_modern,
        )
        payload = _build_local_space_compass_payload(
            cd,
            getattr(data, 'timestamp', None),
            active_settings,
            include_modern=include_modern,
        )
    except (LocationError, ValueError) as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception:
        logger.exception('Failed to compute local-space compass bearings')
        return jsonify({'success': False, 'error': 'Local-space calculation is unavailable'}), 503
    return _json_ok(payload)


@astro_clock_bp.route('/directional-3d', methods=['GET'])
@_error_handler
def get_directional_3d():
    """Return geometry rows for the advanced Directional chart view."""
    include_modern = (request.args.get('include_modern', '0').lower() in {'1', 'true', 'yes'})
    eng = _engine_instance()
    data, active_settings = _data_for_optional_confirmed_snap(eng)
    try:
        chart = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
    except Exception:
        chart = {}
    cd = chart.get('chart_data', {}) if isinstance(chart, dict) else {}
    try:
        cd = _directional_chart_data_for_scope(
            cd,
            getattr(data, 'timestamp', None),
            include_modern=include_modern,
        )
        payload = _build_directional_3d_payload(
            cd,
            getattr(data, 'timestamp', None),
            active_settings,
            include_modern=include_modern,
        )
    except (LocationError, ValueError) as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception:
        logger.exception('Failed to compute Directional 3D geometry')
        return jsonify({'success': False, 'error': 'Directional 3D calculation is unavailable'}), 503
    return _json_ok(payload)


@astro_clock_bp.route('/certification/rectify', methods=['POST'])
@_error_handler
def birth_time_certification_rectify():
    """Run a birth-time rectification scan for certification review."""
    body = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return jsonify({'success': False, 'error': 'JSON object body is required'}), 400
    snap_id = str(body.get('snap_id') or '').strip()
    if snap_id:
        snap = _hydrate_snap_payload(
            _snaps().get(snap_id),
            infer_coordinates=False,
        )
        if not snap:
            return jsonify({'success': False, 'error': 'Saved snap not found'}), 400
        _require_confirmed_saved_snap_context(
            snap,
            feature_label='Birth Certification',
        )
    try:
        from birth_certification import rectify_birth_time_from_payload

        payload = rectify_birth_time_from_payload(body)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except RuntimeError as exc:
        logger.exception('Birth-time certification calculation unavailable')
        return jsonify({'success': False, 'error': str(exc)}), 503
    return _json_ok(payload)


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
                              longitude: Optional[float] = None,
                              include_modern: bool = False,
                              include_chiron: bool = False) -> Dict[str, Any]:
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
        with _engine_lock:
            default_settings = copy.copy(eng.settings)
        resolved_location = location or default_settings.location
        resolved_coords = None
        if latitude is not None and longitude is not None:
            try:
                resolved_coords = (float(latitude), float(longitude))
            except Exception:
                resolved_coords = None
        if resolved_coords is None:
            resolved_coords = (
                _coords_from_settings(default_settings)
                if _settings_match_location(default_settings, resolved_location)
                else None
            )
        resolved_tz = _resolve_timezone_for_context(timezone, resolved_location, coords=resolved_coords)
        if resolved_coords is None and resolved_location and not resolved_tz:
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
            except Exception as exc:
                raise ValueError(
                    f"Invalid datetime: {dt_iso!r}. An ISO-8601 date and time is required."
                ) from exc
            if custom is None:
                raise ValueError(
                    f"Invalid datetime: {dt_iso!r}. An ISO-8601 date and time is required."
                )
        tz = resolved_tz or parsed_tz
        local = AstroClockSettings(
            mode=ClockMode.MANUAL if custom else ClockMode.REALTIME,
            location=resolved_location,
            custom_time=custom,
            timezone=tz or default_settings.timezone,
            latitude=(resolved_coords[0] if resolved_coords else None),
            longitude=(resolved_coords[1] if resolved_coords else None),
            paused_at=None,
            house_system_code=house_system_code or getattr(default_settings, 'house_system_code', None),
        )
        with _astro_perf_span('helper.compute_chart_bundle_for.get_current_data'):
            with _engine_lock:
                data = eng.get_current_data(settings=local)
        if resolved_coords is None:
            try:
                chart_result = data.chart_result if isinstance(data.chart_result, dict) else json.loads(data.chart_result)
            except Exception:
                chart_result = {}
            resolved_coords = _coords_from_chart_data(_extract_chart_data_from_result(chart_result))
            if resolved_coords:
                local.latitude = resolved_coords[0]
                local.longitude = resolved_coords[1]
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
    bundle = _build_chart_bundle(getattr(data, 'chart_result', {}), meta)
    if include_modern or include_chiron:
        bundle['chart_data'] = _extend_chart_data_for_synastry(
            bundle.get('chart_data') or {},
            bundle.get('meta') or meta,
            include_modern=include_modern,
            include_chiron=include_chiron,
        )
    return bundle


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


@contextmanager
def _configure_synastry_ephemeris_path(swe_module: Any):
    with swisseph_ephemeris_path(
        _resolve_synastry_ephemeris_path() or '',
        swe_module=swe_module,
    ):
        yield


def _synastry_utc_instant_from_meta(meta: Dict[str, Any]) -> Optional[datetime]:
    context = (meta or {}).get('calculation_context')
    if not isinstance(context, dict):
        context = {}
    time_provenance = context.get('time_provenance')
    if isinstance(time_provenance, dict) and time_provenance.get('ambiguous'):
        return None
    timestamp = str(
        context.get('instant_utc')
        or (meta or {}).get('instant_utc')
        or (meta or {}).get('timestamp')
        or ''
    ).strip()
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except Exception:
        return None
    # A naive legacy timestamp has no single astronomical meaning.  Do not
    # silently treat it as UTC and mix newly calculated points into a chart
    # that may have been cast from local civil time.
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _synastry_point_capability(meta: Dict[str, Any]) -> Dict[str, bool]:
    try:
        _swe = require_swisseph()
        dt_utc = _synastry_utc_instant_from_meta(meta)
        if dt_utc is None:
            return {"modern_supported": False, "chiron_supported": False}
        hour_decimal = (
            dt_utc.hour
            + (dt_utc.minute / 60.0)
            + (dt_utc.second / 3600.0)
            + (dt_utc.microsecond / 3_600_000_000.0)
        )
        jd_ut = _swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal, _swe.GREG_CAL)
        with _configure_synastry_ephemeris_path(_swe):
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
        _swe = require_swisseph()
    except Exception:
        return chart_data

    try:
        dt_utc = _synastry_utc_instant_from_meta(meta)
        if dt_utc is None:
            return chart_data
        hour_decimal = (
            dt_utc.hour
            + (dt_utc.minute / 60.0)
            + (dt_utc.second / 3600.0)
            + (dt_utc.microsecond / 3_600_000_000.0)
        )
        jd_ut = _swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal, _swe.GREG_CAL)
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

    with _configure_synastry_ephemeris_path(_swe):
        for name in targets:
            if name in existing_names:
                continue
            swe_key = _SYN_AUGMENT_POINT_IDS.get(name)
            point_id = getattr(_swe, swe_key, None) if swe_key else None
            pos = None
            returned_flags = None
            calculation_source = (
                "swiss-ephemeris-asteroid-file"
                if name == "Chiron"
                else "swiss_ephemeris"
            )
            calculation_accuracy = "ephemeris"
            calculation_degraded = False
            if point_id is not None:
                try:
                    pos, returned_flags = _swe.calc_ut(jd_ut, point_id, flags)
                except Exception:
                    pos = None
            if pos is None:
                fallback_position = None
                if name == "Chiron":
                    try:
                        from astrocartography_service import fallback_chiron_ecliptic_position
                        fallback_position = fallback_chiron_ecliptic_position(jd_ut)
                    except Exception:
                        fallback_position = None
                if not fallback_position:
                    continue
                lon = float(fallback_position.get("longitude") or 0.0) % 360.0
                lat = float(fallback_position.get("latitude") or 0.0)
                speed = float(fallback_position.get("speed") or 0.0)
                calculation_source = "jpl_mean_orbital_elements_fallback"
                calculation_accuracy = "low_precision_approximation"
                calculation_degraded = True
            else:
                lon = float(pos[0]) % 360.0
                lat = float(pos[1])
                speed = float(pos[3]) if len(pos) > 3 else 0.0
            if calculation_degraded:
                ephemeris_engine = "orbital_elements"
            elif (
                returned_flags is not None
                and int(returned_flags) & int(getattr(_swe, "FLG_MOSEPH", 4))
            ):
                calculation_source = "moshier"
                ephemeris_engine = "moshier"
            elif (
                returned_flags is not None
                and int(returned_flags) & int(getattr(_swe, "FLG_JPLEPH", 1))
            ):
                calculation_source = "jpl_ephemeris"
                ephemeris_engine = "jpl"
            else:
                ephemeris_engine = "swiss_ephemeris"
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
                'calculation_provenance': {
                    'source': calculation_source,
                    'ephemeris_engine': ephemeris_engine,
                    'returned_flags': int(returned_flags) if returned_flags is not None else None,
                    'accuracy': calculation_accuracy,
                    'degraded': calculation_degraded,
                    'ranking_eligible': not calculation_degraded,
                },
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


def _data_for_request_clock_context(eng: AstroClockEngine, *, house_system_override: Optional[str] = None):
    """Resolve Astro Clock data for the current request without mutating engine state."""
    q_mode = str(request.args.get('mode') or '').strip().lower()
    q_dt = request.args.get('datetime')
    q_loc = request.args.get('location')
    q_tz = request.args.get('timezone')
    q_house = house_system_override or request.args.get('house_system_code') or request.args.get('house_system')
    q_coords = _coords_from_request_args(request.args, strict=True)
    if q_coords is not None and q_loc and abs(q_coords[0]) < 1e-9 and abs(q_coords[1]) < 1e-9:
        resolved_coords = _ensure_coords_for_location(q_loc, trust_settings=False)
        if resolved_coords is not None:
            q_coords = resolved_coords

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

        with _engine_lock:
            prev = copy.copy(eng.settings)
        local_location = q_loc or prev.location
        location_changed = bool(q_loc) and not _settings_match_location(prev, local_location)
        local_coords = q_coords
        explicit_tz = _valid_explicit_timezone(q_tz)
        if local_coords is None:
            if q_loc and not explicit_tz:
                local_coords = _ensure_coords_for_location(local_location, trust_settings=False)
            else:
                local_coords = _coords_from_settings(prev) if _settings_match_location(prev, local_location) else None
        explicit_clock_context = q_tz is not None or q_loc or q_coords
        resolved_context_tz = None
        if explicit_clock_context:
            with _astro_perf_span('helper.data_for_request_clock_context.resolve_location_timezone'):
                if local_coords is None and local_location and not explicit_tz and not (q_tz and not _is_placeholder_tz(q_tz)):
                    local_coords = _ensure_coords_for_location(local_location, trust_settings=not bool(q_loc))
                resolved_context_tz = _resolve_timezone_for_context(
                    q_tz,
                    local_location,
                    coords=local_coords,
                )
                local_tz = resolved_context_tz or (None if location_changed else prev.timezone)
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
            normalization_tz = resolved_context_tz or q_tz
            if not explicit_clock_context:
                normalization_tz = local_tz
            with _astro_perf_span('helper.data_for_request_clock_context.normalize_manual_datetime'):
                custom_override, normalized_tz = _normalize_manual_datetime(
                    q_dt,
                    timezone_name=normalization_tz,
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
                coords = local_coords or _ensure_coords_for_location(
                    local.location,
                    settings_hint=local,
                    trust_settings=not bool(q_loc),
                )
                if coords:
                    lat, lon = coords
                    guess = _tz_instance().get_timezone_for_location(lat, lon)
                    if guess:
                        local.timezone = guess

        with _astro_perf_span('helper.data_for_request_clock_context.get_current_data'):
            data = eng.get_current_data(settings=local)
        active_settings = getattr(data, 'settings', None) or local
        return data, active_settings


def _select_compass_planets(
    chart_data: Optional[Dict[str, Any]],
    *,
    include_modern: bool = False,
) -> Tuple[Optional[float], List[Tuple[str, Dict[str, Any]]]]:
    cd = chart_data if isinstance(chart_data, dict) else {}
    asc = _directional_number(cd.get('ascendant'))
    planets = cd.get('planets') or {}
    if isinstance(planets, list):
        planet_map: Dict[str, Dict[str, Any]] = {}
        for row in planets:
            if not isinstance(row, dict):
                continue
            name = str(row.get('planet') or '').strip()
            if not name:
                continue
            planet_map[name] = row
        planets = planet_map
    selected = _select_directional_planets(planets, include_modern=include_modern)
    return asc, selected


def _build_local_space_compass_payload(
    chart_data: Optional[Dict[str, Any]],
    timestamp: Any,
    active_settings: Optional[AstroClockSettings],
    *,
    include_modern: bool = False,
) -> Dict[str, Any]:
    asc, selected = _select_compass_planets(chart_data, include_modern=include_modern)
    if not selected:
        return {
            'azimuths': [],
            'ascendant': asc,
            'source': 'local_space',
            'has_altitude': True,
            'body_policy': _directional_body_policy(include_modern, returned_names=[]),
        }

    timestamp_iso = _directional_timestamp_iso(timestamp, label='Compass')

    coords = _resolve_directional_observer_coords(active_settings)
    if coords is None:
        raise LocationError('Compass requires chart coordinates')

    try:
        from forensic.local_space import compute_local_space

        altaz = compute_local_space(
            timestamp_iso,
            float(coords[0]),
            float(coords[1]),
            [name for name, _info in selected],
        )
    except Exception as exc:
        raise RuntimeError('Local-space calculation is unavailable') from exc

    local_rows = []
    for name, info in selected:
        payload = altaz.get(name)
        if not isinstance(payload, dict):
            continue
        azimuth = _directional_number(payload.get('azimuth_deg'))
        if azimuth is None:
            continue
        item = {
            'planet': name,
            'azimuth_deg': _directional_wrap_degrees(azimuth),
        }
        altitude = _directional_number(payload.get('altitude_deg'))
        if altitude is not None:
            item['altitude_deg'] = altitude
        right_ascension = _directional_number(payload.get('right_ascension_deg'))
        declination = _directional_number(payload.get('declination_deg'))
        if right_ascension is not None and declination is not None:
            item['right_ascension_deg'] = _directional_wrap_degrees(right_ascension)
            item['declination_deg'] = declination
        try:
            item['longitude_deg'] = float(info.get('longitude'))
        except Exception:
            pass
        local_rows.append(item)

    if not local_rows:
        raise RuntimeError('Local-space calculation returned no bearings')

    return {
        'azimuths': local_rows,
        'ascendant': asc,
        'latitude': float(coords[0]),
        'longitude': float(coords[1]),
        'source': 'local_space',
        'has_altitude': any('altitude_deg' in row for row in local_rows),
        'body_policy': _directional_body_policy(
            include_modern,
            returned_names=[row['planet'] for row in local_rows],
        ),
    }


DIRECTIONAL_3D_DEFAULT_ROTATION = 9.0
DIRECTIONAL_3D_DEFAULT_TILT = 19.0
DIRECTIONAL_TRADITIONAL_BODIES: Tuple[str, ...] = (
    'Sun',
    'Moon',
    'Mercury',
    'Venus',
    'Mars',
    'Jupiter',
    'Saturn',
)
DIRECTIONAL_MODERN_BODIES: Tuple[str, ...] = (
    'Uranus',
    'Neptune',
    'Pluto',
)
DIRECTIONAL_EXCLUDED_POINTS: Tuple[str, ...] = (
    'Chiron',
    'North Node',
    'South Node',
    'True Node',
)
DIRECTIONAL_3D_SYMBOLS: Dict[str, str] = {
    'Sun': '☉',
    'Moon': '☽',
    'Mercury': '☿',
    'Venus': '♀',
    'Mars': '♂',
    'Jupiter': '♃',
    'Saturn': '♄',
    'Uranus': '♅',
    'Neptune': '♆',
    'Pluto': '♇',
    'Chiron': '⚷',
    'North Node': '☊',
    'South Node': '☋',
}
DIRECTIONAL_3D_SWISSEPH_KEYS: Dict[str, str] = {
    'Sun': 'SUN',
    'Moon': 'MOON',
    'Mercury': 'MERCURY',
    'Venus': 'VENUS',
    'Mars': 'MARS',
    'Jupiter': 'JUPITER',
    'Saturn': 'SATURN',
    'Uranus': 'URANUS',
    'Neptune': 'NEPTUNE',
    'Pluto': 'PLUTO',
    'Chiron': 'CHIRON',
    'North Node': 'MEAN_NODE',
    'True Node': 'TRUE_NODE',
}


def _directional_body_policy(
    include_modern: bool,
    *,
    returned_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    eligible = list(DIRECTIONAL_TRADITIONAL_BODIES)
    if include_modern:
        eligible.extend(DIRECTIONAL_MODERN_BODIES)
    included = (
        list(eligible)
        if returned_names is None
        else [name for name in eligible if name in set(returned_names)]
    )
    return {
        'scope': 'traditional_plus_modern' if include_modern else 'traditional',
        'included': included,
        'eligible': eligible,
        'traditional': list(DIRECTIONAL_TRADITIONAL_BODIES),
        'modern': list(DIRECTIONAL_MODERN_BODIES),
        'excluded_points': list(DIRECTIONAL_EXCLUDED_POINTS),
    }


def _select_directional_planets(
    planets: Any,
    *,
    include_modern: bool,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Apply the shared Compass/Directional body policy in stable display order.

    The modern switch adds Uranus, Neptune, and Pluto. Nodes and Chiron are
    deliberately outside this switch because the local-space provider does not
    guarantee a matching topocentric position for them.
    """
    policy_names = _directional_body_policy(include_modern)['eligible']
    canonical_by_key = {name.casefold(): name for name in policy_names}
    found: Dict[str, Dict[str, Any]] = {}
    if isinstance(planets, dict):
        iterable = planets.items()
    elif isinstance(planets, list):
        iterable = []
        for row in planets:
            if not isinstance(row, dict):
                continue
            iterable.append((row.get('planet') or row.get('name') or row.get('object'), row))
    else:
        iterable = []
    for raw_name, info in iterable:
        if not isinstance(info, dict):
            continue
        if info.get('bnotuse') is True or info.get('not_use') is True or info.get('usable') is False:
            continue
        clean_name = str(raw_name or '').strip()
        canonical = canonical_by_key.get(clean_name.casefold())
        if canonical is not None:
            found[canonical] = info
    return [(name, found[name]) for name in policy_names if name in found]


def _directional_number(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, str) and not value.strip():
        return default
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _directional_round(value: Any, places: int = 3, default: Optional[float] = None) -> Optional[float]:
    number = _directional_number(value, default)
    if number is None:
        return None
    return round(number, places)


def _directional_wrap_degrees(value: float) -> float:
    wrapped = math.fmod(float(value), 360.0)
    if wrapped < 0:
        wrapped += 360.0
    return wrapped


def _directional_timestamp_iso(timestamp: Any, *, label: str) -> str:
    if isinstance(timestamp, datetime):
        dt = timestamp
    elif timestamp:
        text = str(timestamp)
        if text.endswith('Z'):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except Exception as exc:
            raise ValueError(f'{label} requires a valid chart timestamp') from exc
    else:
        raise ValueError(f'{label} requires an active chart timestamp')
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f'{label} requires a timezone-aware chart timestamp')
    return dt.astimezone(timezone.utc).isoformat()


def _directional_jd_ut(timestamp_iso: str) -> float:
    try:
        _swe = require_swisseph()
    except Exception as exc:
        raise RuntimeError('Swiss Ephemeris is unavailable') from exc
    dt = datetime.fromisoformat(str(timestamp_iso).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    hour_decimal = (
        dt_utc.hour
        + (dt_utc.minute / 60.0)
        + (dt_utc.second / 3600.0)
        + (dt_utc.microsecond / 3_600_000_000.0)
    )
    return float(_swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour_decimal, getattr(_swe, 'GREG_CAL', 1)))


def _directional_mean_obliquity_from_jd(jd_ut: float) -> float:
    # Fallback only: use a mean-obliquity polynomial when no chart/JD
    # obliquity service is available.
    t = (float(jd_ut) - 2451545.0) / 36525.0
    seconds = 21.448 - (46.8150 * t) - (0.00059 * t * t) + (0.001813 * t * t * t)
    return 23.0 + (26.0 / 60.0) + (seconds / 3600.0)


def _directional_chart_obliquity(chart_data: Optional[Dict[str, Any]], timestamp_iso: str) -> Tuple[float, str]:
    cd = chart_data if isinstance(chart_data, dict) else {}
    candidates: List[Any] = [
        cd.get('obliquity'),
        cd.get('true_obliquity'),
        cd.get('mean_obliquity'),
        cd.get('epsilon'),
    ]
    for nested_key in ('astronomy', 'ephemeris', 'chart_info'):
        nested = cd.get(nested_key)
        if isinstance(nested, dict):
            candidates.extend([
                nested.get('obliquity'),
                nested.get('true_obliquity'),
                nested.get('mean_obliquity'),
                nested.get('epsilon'),
            ])
    for value in candidates:
        number = _directional_number(value)
        if number is not None and 0.0 < abs(number) < 90.0:
            return float(number), 'chart'

    try:
        _swe = require_swisseph()

        jd_ut = _directional_jd_ut(timestamp_iso)
        with _configure_synastry_ephemeris_path(_swe):
            result, _flags = _swe.calc_ut(jd_ut, getattr(_swe, 'ECL_NUT', -1))
        if result and len(result) > 0:
            number = _directional_number(result[0])
            if number is not None and 0.0 < abs(number) < 90.0:
                return float(number), 'swisseph'
    except Exception:
        pass

    try:
        return _directional_mean_obliquity_from_jd(_directional_jd_ut(timestamp_iso)), 'mean_formula'
    except Exception:
        return 23.4392911, 'mean_formula'


def _directional_ecliptic_to_equatorial(
    longitude_deg: float,
    latitude_deg: float,
    obliquity_deg: float,
) -> Tuple[float, float]:
    lon = math.radians(_directional_wrap_degrees(longitude_deg))
    lat = math.radians(float(latitude_deg))
    eps = math.radians(float(obliquity_deg))
    right_ascension = math.atan2(
        math.sin(lon) * math.cos(eps) - math.tan(lat) * math.sin(eps),
        math.cos(lon),
    )
    declination = math.asin(
        math.sin(lat) * math.cos(eps) + math.cos(lat) * math.sin(eps) * math.sin(lon)
    )
    return _directional_wrap_degrees(math.degrees(right_ascension)), math.degrees(declination)


def _directional_ecliptic_to_equatorial_with_rates(
    longitude_deg: float,
    latitude_deg: float,
    longitude_speed_deg: float,
    latitude_speed_deg: float,
    obliquity_deg: float,
) -> Tuple[float, float, float, float]:
    lon = math.radians(_directional_wrap_degrees(longitude_deg))
    lat = math.radians(float(latitude_deg))
    lon_speed = math.radians(float(longitude_speed_deg))
    lat_speed = math.radians(float(latitude_speed_deg))
    eps = math.radians(float(obliquity_deg))

    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)
    cos_lon = math.cos(lon)
    sin_lon = math.sin(lon)
    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)

    x = cos_lat * cos_lon
    y = cos_lat * sin_lon
    z = sin_lat

    equ_x = x
    equ_y = (y * cos_eps) - (z * sin_eps)
    equ_z = (y * sin_eps) + (z * cos_eps)

    dx = (-sin_lat * lat_speed * cos_lon) - (cos_lat * sin_lon * lon_speed)
    dy = (-sin_lat * lat_speed * sin_lon) + (cos_lat * cos_lon * lon_speed)
    dz = cos_lat * lat_speed

    d_equ_x = dx
    d_equ_y = (dy * cos_eps) - (dz * sin_eps)
    d_equ_z = (dy * sin_eps) + (dz * cos_eps)

    ra_denominator = (equ_x * equ_x) + (equ_y * equ_y)
    if ra_denominator <= 1e-15:
        ra_speed = 0.0
    else:
        ra_speed = (equ_x * d_equ_y - equ_y * d_equ_x) / ra_denominator

    dec_denominator = math.sqrt(max(1e-15, 1.0 - (equ_z * equ_z)))
    dec_speed = d_equ_z / dec_denominator
    right_ascension = math.atan2(equ_y, equ_x)
    declination = math.asin(max(-1.0, min(1.0, equ_z)))
    return (
        _directional_wrap_degrees(math.degrees(right_ascension)),
        math.degrees(declination),
        math.degrees(ra_speed),
        math.degrees(dec_speed),
    )


def _directional_horizontal_from_equatorial(
    timestamp_iso: str,
    observer_latitude: float,
    observer_longitude: float,
    right_ascension_deg: float,
    declination_deg: float,
) -> Tuple[float, float]:
    try:
        from forensic.local_space import _az_alt_from_ra_dec, _jd_ut_from_iso, _lst_hours

        jd_ut = _jd_ut_from_iso(timestamp_iso)
        sidereal_hours = _lst_hours(jd_ut, observer_longitude)
        horizontal = _az_alt_from_ra_dec(
            right_ascension_deg / 15.0,
            declination_deg,
            observer_latitude,
            sidereal_hours,
        )
        return (
            _directional_wrap_degrees(horizontal.get('azimuth_deg')),
            float(horizontal['altitude_deg']),
        )
    except Exception as exc:
        raise RuntimeError('Directional 3D horizon coordinates are unavailable') from exc


def _directional_horizontal_from_ecliptic(
    timestamp_iso: str,
    observer_latitude: float,
    observer_longitude: float,
    ecliptic_longitude_deg: float,
    ecliptic_latitude_deg: float,
    obliquity_deg: float,
) -> Tuple[float, float, str]:
    try:
        _swe = require_swisseph()

        jd_ut = _directional_jd_ut(timestamp_iso)
        with swisseph_lock():
            result = _swe.azalt(
                jd_ut,
                getattr(_swe, 'ECL2HOR', 0),
                (float(observer_longitude), float(observer_latitude), 0.0),
                0.0,
                0.0,
                (
                    _directional_wrap_degrees(ecliptic_longitude_deg),
                    float(ecliptic_latitude_deg),
                    1.0,
                ),
            )
        altitude = result[1] if len(result) > 1 else result[2]
        # swe.azalt reports 0° at South and increases toward West. The public
        # Directional/Compass contract is the navigation convention:
        # 0° North, 90° East, 180° South, 270° West.
        azimuth = _directional_wrap_degrees(float(result[0]) + 180.0)
        return azimuth, float(altitude), 'swisseph_azalt'
    except Exception:
        equ_longitude, equ_latitude = _directional_ecliptic_to_equatorial(
            ecliptic_longitude_deg,
            ecliptic_latitude_deg,
            obliquity_deg,
        )
        hor_longitude, hor_latitude = _directional_horizontal_from_equatorial(
            timestamp_iso,
            observer_latitude,
            observer_longitude,
            equ_longitude,
            equ_latitude,
        )
        return hor_longitude, hor_latitude, 'equatorial_fallback'


def _directional_shift_timestamp_iso(timestamp_iso: str, delta_seconds: float) -> str:
    dt = datetime.fromisoformat(str(timestamp_iso).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.astimezone(timezone.utc) + timedelta(seconds=float(delta_seconds))).isoformat()


def _directional_signed_degree_delta(end_degrees: float, start_degrees: float) -> float:
    return ((_directional_wrap_degrees(end_degrees) - _directional_wrap_degrees(start_degrees) + 540.0) % 360.0) - 180.0


def _directional_horizontal_rates_from_ecliptic(
    timestamp_iso: str,
    observer_latitude: float,
    observer_longitude: float,
    ecliptic_longitude_deg: float,
    ecliptic_latitude_deg: float,
    ecliptic_longitude_speed: float,
    ecliptic_latitude_speed: Optional[float],
    obliquity_deg: float,
    object_type: str,
) -> Tuple[Optional[float], Optional[float], str, str]:
    if object_type == 'cusp':
        return None, None, 'unavailable', 'unavailable'

    step_seconds = 300.0
    step_days = step_seconds / 86400.0
    latitude_speed = float(ecliptic_latitude_speed) if ecliptic_latitude_speed is not None else 0.0
    before_timestamp = _directional_shift_timestamp_iso(timestamp_iso, -step_seconds)
    after_timestamp = _directional_shift_timestamp_iso(timestamp_iso, step_seconds)
    try:
        before_longitude, before_latitude, _before_source = _directional_horizontal_from_ecliptic(
            before_timestamp,
            observer_latitude,
            observer_longitude,
            ecliptic_longitude_deg - (float(ecliptic_longitude_speed) * step_days),
            ecliptic_latitude_deg - (latitude_speed * step_days),
            obliquity_deg,
        )
        after_longitude, after_latitude, _after_source = _directional_horizontal_from_ecliptic(
            after_timestamp,
            observer_latitude,
            observer_longitude,
            ecliptic_longitude_deg + (float(ecliptic_longitude_speed) * step_days),
            ecliptic_latitude_deg + (latitude_speed * step_days),
            obliquity_deg,
        )
    except Exception:
        return None, None, 'unavailable', 'unavailable'

    divisor_days = 2.0 * step_days
    longitude_rate = _directional_signed_degree_delta(after_longitude, before_longitude) / divisor_days
    latitude_rate = (float(after_latitude) - float(before_latitude)) / divisor_days
    return longitude_rate, latitude_rate, 'finite_difference', 'finite_difference'


def _directional_equatorial_from_swiss(
    name: str,
    timestamp_iso: str,
) -> Optional[Tuple[float, float, Optional[float], Optional[float]]]:
    swe_key = DIRECTIONAL_3D_SWISSEPH_KEYS.get(str(name or '').strip())
    if not swe_key:
        return None
    try:
        _swe = require_swisseph()

        point_id = getattr(_swe, swe_key, None)
        if point_id is None:
            return None
        jd_ut = _directional_jd_ut(timestamp_iso)
        flags = (
            getattr(_swe, 'FLG_SWIEPH', getattr(_swe, 'SEFLG_SWIEPH', 2))
            | getattr(_swe, 'FLG_SPEED', getattr(_swe, 'SEFLG_SPEED', 256))
            | getattr(_swe, 'FLG_EQUATORIAL', getattr(_swe, 'SEFLG_EQUATORIAL', 2048))
        )
        with _configure_synastry_ephemeris_path(_swe):
            pos, _ret = _swe.calc_ut(jd_ut, point_id, flags)
        return (
            _directional_wrap_degrees(float(pos[0])),
            float(pos[1]),
            float(pos[3]) if len(pos) > 3 else None,
            float(pos[4]) if len(pos) > 4 else None,
        )
    except Exception:
        return None


def _directional_equatorial_from_fields(info: Dict[str, Any]) -> Optional[Tuple[float, float, Optional[float], Optional[float]]]:
    equ_longitude = None
    equ_latitude = None
    for key in ('equatorial_longitude', 'equ_longitude', 'equ_lon', 'right_ascension', 'ra'):
        number = _directional_number(info.get(key))
        if number is not None:
            equ_longitude = number
            break
    for key in ('equatorial_latitude', 'equ_latitude', 'equ_lat', 'declination', 'dec'):
        number = _directional_number(info.get(key))
        if number is not None:
            equ_latitude = number
            break
    if equ_longitude is None or equ_latitude is None:
        return None
    equ_speed = None
    for key in ('equatorial_speed', 'equ_speed', 'ra_speed', 'right_ascension_speed'):
        equ_speed = _directional_number(info.get(key))
        if equ_speed is not None:
            break
    equ_latitude_speed = None
    for key in ('equatorial_latitude_speed', 'equ_latitude_speed', 'equ_lat_speed', 'declination_speed', 'dec_speed'):
        equ_latitude_speed = _directional_number(info.get(key))
        if equ_latitude_speed is not None:
            break
    return _directional_wrap_degrees(equ_longitude), float(equ_latitude), equ_speed, equ_latitude_speed


def _directional_ecliptic_latitude_speed_from_fields(info: Dict[str, Any]) -> Optional[float]:
    for key in ('latitude_speed', 'ecliptic_latitude_speed', 'lat_speed', 'latspeed', 'betaspeed', 'beta_speed'):
        number = _directional_number(info.get(key))
        if number is not None:
            return number
    return None


def _directional_unit_vector(longitude_deg: Any, latitude_deg: Any) -> Optional[Dict[str, float]]:
    longitude = _directional_number(longitude_deg)
    latitude = _directional_number(latitude_deg)
    if longitude is None or latitude is None:
        return None
    lon_radians = math.radians(_directional_wrap_degrees(longitude))
    lat_radians = math.radians(latitude)
    cos_latitude = math.cos(lat_radians)
    return {
        'x': round(cos_latitude * math.cos(lon_radians), 9),
        'y': round(cos_latitude * math.sin(lon_radians), 9),
        'z': round(math.sin(lat_radians), 9),
    }


def _directional_rate_from_horizontal_samples(
    before: Optional[Dict[str, Any]],
    after: Optional[Dict[str, Any]],
    *,
    step_seconds: float,
) -> Tuple[Optional[float], Optional[float], str, str]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return None, None, 'unavailable', 'unavailable'
    before_azimuth = _directional_number(before.get('azimuth_deg'))
    before_altitude = _directional_number(before.get('altitude_deg'))
    after_azimuth = _directional_number(after.get('azimuth_deg'))
    after_altitude = _directional_number(after.get('altitude_deg'))
    if None in (before_azimuth, before_altitude, after_azimuth, after_altitude):
        return None, None, 'unavailable', 'unavailable'
    if not (-90.0 <= before_altitude <= 90.0 and -90.0 <= after_altitude <= 90.0):
        return None, None, 'unavailable', 'unavailable'
    divisor_days = (2.0 * float(step_seconds)) / 86400.0
    return (
        _directional_signed_degree_delta(after_azimuth, before_azimuth) / divisor_days,
        (float(after_altitude) - float(before_altitude)) / divisor_days,
        'topocentric_finite_difference',
        'topocentric_finite_difference',
    )


def _directional_coordinate_triplet(
    longitude_deg: float,
    latitude_deg: Optional[float],
    speed: Optional[float],
    *,
    object_id: str,
    name: str,
    info: Optional[Dict[str, Any]],
    object_type: str,
    ecliptic_speed_source: str,
    ecliptic_latitude_speed: Optional[float],
    timestamp_iso: str,
    observer_latitude: float,
    observer_longitude: float,
    obliquity_deg: float,
    horizontal_samples: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
    eql_longitude = _directional_wrap_degrees(longitude_deg)
    eql_latitude = _directional_number(latitude_deg)
    eql_speed = _directional_number(speed)
    equ_longitude: Optional[float] = None
    equ_latitude: Optional[float] = None
    equ_speed: Optional[float] = None
    equ_latitude_speed: Optional[float] = None
    equ_speed_provider = None
    equ_latitude_speed_provider = None
    data_gaps: List[Dict[str, str]] = []
    if object_type == 'cusp':
        equ_longitude, equ_latitude = _directional_ecliptic_to_equatorial(
            eql_longitude,
            0.0,
            obliquity_deg,
        )
        equ_source = 'derived_from_ecliptic'
        equ_speed_source = 'unavailable'
        equ_latitude_speed_source = 'unavailable'
        eql_source = 'house_cusp'
        eql_speed_source = 'unavailable'
    else:
        equ_values = _directional_equatorial_from_fields(info or {})
        if equ_values is None:
            if eql_latitude is None:
                swiss_values = _directional_equatorial_from_swiss(name, timestamp_iso)
                if swiss_values is not None:
                    equ_longitude, equ_latitude, swiss_speed, swiss_latitude_speed = swiss_values
                    equ_source = 'swisseph'
                    equ_speed = float(swiss_speed) if swiss_speed is not None else None
                    equ_speed_source = 'native' if swiss_speed is not None else 'unavailable'
                    equ_speed_provider = 'swisseph' if swiss_speed is not None else None
                    equ_latitude_speed = float(swiss_latitude_speed) if swiss_latitude_speed is not None else None
                    equ_latitude_speed_source = 'native' if swiss_latitude_speed is not None else 'unavailable'
                    equ_latitude_speed_provider = 'swisseph' if swiss_latitude_speed is not None else None
                else:
                    equ_source = 'unavailable'
                    equ_speed_source = 'unavailable'
                    equ_latitude_speed_source = 'unavailable'
                data_gaps.append({
                    'code': 'ecliptic_latitude_unavailable',
                    'object_id': object_id,
                    'object': str(name),
                })
            elif eql_speed is not None and ecliptic_latitude_speed is not None:
                equ_source = 'derived_from_ecliptic'
                equ_longitude, equ_latitude, equ_speed, equ_latitude_speed = _directional_ecliptic_to_equatorial_with_rates(
                    eql_longitude,
                    eql_latitude,
                    eql_speed,
                    ecliptic_latitude_speed,
                    obliquity_deg,
                )
                equ_speed_source = 'derived'
                equ_latitude_speed_source = 'derived'
            else:
                equ_source = 'derived_from_ecliptic'
                equ_longitude, equ_latitude = _directional_ecliptic_to_equatorial(
                    eql_longitude,
                    eql_latitude,
                    obliquity_deg,
                )
                swiss_values = _directional_equatorial_from_swiss(name, timestamp_iso)
                if swiss_values is not None:
                    _swiss_longitude, _swiss_latitude, swiss_speed, swiss_latitude_speed = swiss_values
                    equ_speed = float(swiss_speed) if swiss_speed is not None else None
                    equ_speed_source = 'native' if swiss_speed is not None else 'unavailable'
                    equ_speed_provider = 'swisseph' if swiss_speed is not None else None
                    equ_latitude_speed = float(swiss_latitude_speed) if swiss_latitude_speed is not None else None
                    equ_latitude_speed_source = 'native' if swiss_latitude_speed is not None else 'unavailable'
                    equ_latitude_speed_provider = 'swisseph' if swiss_latitude_speed is not None else None
                else:
                    equ_speed_source = 'unavailable'
                    equ_latitude_speed_source = 'unavailable'
        else:
            equ_longitude, equ_latitude, maybe_speed, maybe_latitude_speed = equ_values
            equ_source = 'chart_equatorial'
            swiss_values = None
            if maybe_speed is not None:
                equ_speed = float(maybe_speed)
                equ_speed_source = 'native'
            else:
                swiss_values = _directional_equatorial_from_swiss(name, timestamp_iso)
                if swiss_values is not None:
                    _swiss_longitude, _swiss_latitude, swiss_speed, swiss_latitude_speed = swiss_values
                    equ_speed = float(swiss_speed) if swiss_speed is not None else None
                    equ_speed_source = 'native' if swiss_speed is not None else 'unavailable'
                    equ_speed_provider = 'swisseph' if swiss_speed is not None else None
                    if maybe_latitude_speed is None:
                        equ_latitude_speed = float(swiss_latitude_speed) if swiss_latitude_speed is not None else None
                        equ_latitude_speed_source = 'native' if swiss_latitude_speed is not None else 'unavailable'
                        equ_latitude_speed_provider = 'swisseph' if swiss_latitude_speed is not None else None
                else:
                    equ_speed_source = 'unavailable'
            if maybe_latitude_speed is not None:
                equ_latitude_speed = float(maybe_latitude_speed)
                equ_latitude_speed_source = 'native'
            elif swiss_values is None:
                equ_latitude_speed = None
                equ_latitude_speed_source = 'unavailable'
        eql_source = 'chart_ecliptic'
        eql_speed_source = ecliptic_speed_source or 'unavailable'
        if equ_speed_source == 'unavailable':
            data_gaps.append({
                'code': 'equatorial_speed_unavailable',
                'object_id': object_id,
                'object': str(name),
            })
    horizontal_samples = horizontal_samples if isinstance(horizontal_samples, dict) else {}
    current_horizontal = horizontal_samples.get('current')
    current_azimuth = (
        _directional_number(current_horizontal.get('azimuth_deg'))
        if isinstance(current_horizontal, dict)
        else None
    )
    current_altitude = (
        _directional_number(current_horizontal.get('altitude_deg'))
        if isinstance(current_horizontal, dict)
        else None
    )
    valid_current_horizontal = bool(
        current_azimuth is not None
        and current_altitude is not None
        and -90.0 <= current_altitude <= 90.0
    )
    if object_type == 'planet' and valid_current_horizontal:
        hor_longitude = _directional_wrap_degrees(current_azimuth)
        hor_latitude = current_altitude
        hor_source = 'topocentric_local_space'
        hor_speed, hor_latitude_speed, hor_speed_source, hor_latitude_speed_source = (
            _directional_rate_from_horizontal_samples(
                horizontal_samples.get('before'),
                horizontal_samples.get('after'),
                step_seconds=300.0,
            )
        )
    elif object_type == 'cusp':
        hor_longitude, hor_latitude, hor_source = _directional_horizontal_from_ecliptic(
            timestamp_iso,
            observer_latitude,
            observer_longitude,
            eql_longitude,
            0.0,
            obliquity_deg,
        )
        hor_speed = None
        hor_latitude_speed = None
        hor_speed_source = 'unavailable'
        hor_latitude_speed_source = 'unavailable'
    else:
        hor_longitude = None
        hor_latitude = None
        hor_speed = None
        hor_latitude_speed = None
        hor_source = 'unavailable'
        hor_speed_source = 'unavailable'
        hor_latitude_speed_source = 'unavailable'
        data_gaps.append({
            'code': 'topocentric_horizon_unavailable',
            'object_id': object_id,
            'object': str(name),
        })
    equ_meta = {
        'source': equ_source,
        'speed_source': equ_speed_source,
        'latitude_speed_source': equ_latitude_speed_source,
    }
    if equ_speed_provider:
        equ_meta['speed_provider'] = equ_speed_provider
    if equ_latitude_speed_provider:
        equ_meta['latitude_speed_provider'] = equ_latitude_speed_provider
    return (
        {
            'longitude': _directional_round(eql_longitude, 3, None),
            'latitude': _directional_round(eql_latitude, 3, None),
            'speed': _directional_round(eql_speed, 3, None),
        },
        {
            'longitude': _directional_round(equ_longitude, 3, None),
            'latitude': _directional_round(equ_latitude, 3, None),
            'speed': _directional_round(equ_speed, 3, None),
            'latitude_speed': _directional_round(equ_latitude_speed, 3, None),
        },
        {
            'longitude': _directional_round(hor_longitude, 3, None),
            'latitude': _directional_round(hor_latitude, 3, None),
            'speed': _directional_round(hor_speed, 3, None),
            'latitude_speed': _directional_round(hor_latitude_speed, 3, None),
        },
        {
            'EQL': {
                'source': eql_source,
                'speed_source': eql_speed_source,
            },
            'EQU': {
                **equ_meta,
            },
            'HOR': {
                'source': hor_source,
                'speed_source': hor_speed_source,
                'latitude_speed_source': hor_latitude_speed_source,
            },
        },
        data_gaps,
    )


def _directional_object_row(
    *,
    object_id: str,
    object_index: int,
    name: str,
    symbol: str,
    object_type: str,
    info: Optional[Dict[str, Any]],
    longitude_deg: float,
    latitude_deg: Optional[float],
    speed: Optional[float],
    ecliptic_speed_source: str,
    ecliptic_latitude_speed: Optional[float],
    bfull: bool,
    timestamp_iso: str,
    observer_latitude: float,
    observer_longitude: float,
    obliquity_deg: float,
    horizontal_samples: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    eql, equ, hor, coordinate_meta, data_gaps = _directional_coordinate_triplet(
        longitude_deg,
        latitude_deg,
        speed,
        object_id=object_id,
        name=name,
        info=info,
        object_type=object_type,
        ecliptic_speed_source=ecliptic_speed_source,
        ecliptic_latitude_speed=ecliptic_latitude_speed,
        timestamp_iso=timestamp_iso,
        observer_latitude=observer_latitude,
        observer_longitude=observer_longitude,
        obliquity_deg=obliquity_deg,
        horizontal_samples=horizontal_samples,
    )
    vectors = {
        'EQL': _directional_unit_vector(eql.get('longitude'), eql.get('latitude')),
        'EQU': _directional_unit_vector(equ.get('longitude'), equ.get('latitude')),
        'HOR': _directional_unit_vector(hor.get('longitude'), hor.get('latitude')),
    }
    current_horizontal = (horizontal_samples or {}).get('current') if isinstance(horizontal_samples, dict) else None
    reference_vector = None
    if isinstance(current_horizontal, dict):
        reference_vector = _directional_unit_vector(
            current_horizontal.get('right_ascension_deg'),
            current_horizontal.get('declination_deg'),
        )
    return {
        'object_id': object_id,
        'object_index': object_index,
        'name': name,
        'symbol': symbol,
        'object_type': object_type,
        'buse': True,
        'bfull': bool(bfull),
        'EQL': eql,
        'EQU': equ,
        'HOR': hor,
        'vectors': vectors,
        'reference_vector': reference_vector,
        'coordinate_meta': coordinate_meta,
        '_data_gaps': data_gaps,
    }


def _chart_house_cusps(chart_data: Optional[Dict[str, Any]]) -> List[Tuple[int, float]]:
    cd = chart_data if isinstance(chart_data, dict) else {}
    raw_cusps = cd.get('house_cusps') or cd.get('houses') or []
    if isinstance(raw_cusps, dict):
        values = []
        for index in range(1, 13):
            string_value = raw_cusps.get(str(index))
            values.append(string_value if string_value is not None else raw_cusps.get(index))
    else:
        values = list(raw_cusps) if isinstance(raw_cusps, (list, tuple)) else []
    cusps: List[Tuple[int, float]] = []
    for index, value in enumerate(values[:12], start=1):
        number = _directional_number(value)
        if number is not None:
            cusps.append((index, number))
    return cusps


def _directional_planet_entries(
    chart_data: Optional[Dict[str, Any]],
    *,
    include_modern: bool = False,
) -> List[Tuple[str, Dict[str, Any]]]:
    cd = chart_data if isinstance(chart_data, dict) else {}
    planets = cd.get('planets') or {}
    return _select_directional_planets(planets, include_modern=include_modern)


def _valid_directional_observer_coords(coords: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    latitude = _directional_number(coords[0])
    longitude = _directional_number(coords[1])
    if latitude is None or longitude is None:
        return None
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None
    return float(latitude), float(longitude)


def _resolve_directional_observer_coords(
    active_settings: Optional[AstroClockSettings],
) -> Optional[Tuple[float, float]]:
    location = str(getattr(active_settings, 'location', None) or '').strip()
    stored = _valid_directional_observer_coords(_coords_from_settings(active_settings))
    stored_is_legacy_zero = bool(
        stored is not None
        and abs(stored[0]) < 1e-9
        and abs(stored[1]) < 1e-9
        and location
    )
    if stored is not None and not stored_is_legacy_zero:
        return stored
    if location:
        resolved = _valid_directional_observer_coords(
            _ensure_coords_for_location(
                location,
                settings_hint=active_settings,
                trust_settings=False,
            )
        )
        if resolved is not None and not (
            abs(resolved[0]) < 1e-9 and abs(resolved[1]) < 1e-9
        ):
            return resolved
    return None if stored_is_legacy_zero or stored is None else stored


def _directional_coords_from_context(
    active_settings: Optional[AstroClockSettings],
) -> Optional[Tuple[float, float]]:
    return _resolve_directional_observer_coords(active_settings)


def _directional_topocentric_samples(
    timestamp_iso: str,
    latitude: float,
    longitude: float,
    body_names: List[str],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    if not body_names:
        return {'current': {}, 'before': {}, 'after': {}}
    try:
        from forensic.local_space import compute_local_space

        current = compute_local_space(timestamp_iso, latitude, longitude, body_names)
    except Exception as exc:
        raise RuntimeError('Directional 3D topocentric calculation is unavailable') from exc
    if not current:
        raise RuntimeError('Directional 3D topocentric calculation returned no positions')
    samples: Dict[str, Dict[str, Dict[str, Any]]] = {
        'current': current,
        'before': {},
        'after': {},
    }
    for sample_name, seconds in (('before', -300.0), ('after', 300.0)):
        try:
            sample_timestamp = _directional_shift_timestamp_iso(timestamp_iso, seconds)
            samples[sample_name] = compute_local_space(
                sample_timestamp,
                latitude,
                longitude,
                body_names,
            )
        except Exception:
            samples[sample_name] = {}
    return samples


def _directional_frame_context(
    timestamp_iso: str,
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    local_sidereal_degrees: Optional[float] = None
    try:
        from forensic.local_space import _jd_ut_from_iso, _lst_hours

        local_sidereal_degrees = _directional_wrap_degrees(
            _lst_hours(_jd_ut_from_iso(timestamp_iso), longitude) * 15.0
        )
    except Exception:
        pass
    return {
        'observer_frame': 'topocentric',
        'azimuth_convention': 'north_zero_eastward',
        'altitude_convention': 'degrees_above_horizon',
        'ecliptic_frame': 'geocentric_chart',
        'equatorial_frame': 'geocentric_chart',
        'horizon_frame': 'topocentric_observer',
        'local_sidereal_time_deg': _directional_round(local_sidereal_degrees, 6, None),
        'latitude': _directional_round(latitude, 6, None),
        'longitude': _directional_round(longitude, 6, None),
    }


def _build_directional_3d_payload(
    chart_data: Optional[Dict[str, Any]],
    timestamp: Any,
    active_settings: Optional[AstroClockSettings],
    *,
    include_modern: bool = False,
) -> Dict[str, Any]:
    timestamp_iso = _directional_timestamp_iso(timestamp, label='Directional 3D')
    coords = _directional_coords_from_context(active_settings)
    if coords is None:
        raise LocationError('Directional 3D requires chart coordinates')

    latitude = float(coords[0])
    longitude = float(coords[1])
    obliquity, obliquity_source = _directional_chart_obliquity(chart_data, timestamp_iso)
    selected_planets = _directional_planet_entries(chart_data, include_modern=include_modern)
    body_names = [name for name, _info in selected_planets]
    topocentric_samples = _directional_topocentric_samples(
        timestamp_iso,
        latitude,
        longitude,
        body_names,
    )
    rows: List[Dict[str, Any]] = []
    data_gaps: List[Dict[str, str]] = []
    object_index = 0

    for name, info in selected_planets:
        ecliptic_longitude = _directional_number(info.get('longitude'))
        if ecliptic_longitude is None:
            continue
        ecliptic_latitude = _directional_number(info.get('latitude'))
        speed = _directional_number(info.get('speed')) if info.get('speed') is not None else None
        ecliptic_speed_source = 'native' if speed is not None else ''
        if speed is None:
            speed = _directional_number(info.get('lonspeed')) if info.get('lonspeed') is not None else None
            ecliptic_speed_source = 'native' if speed is not None else ''
        if speed is None:
            ecliptic_speed_source = 'unavailable'
        ecliptic_latitude_speed = _directional_ecliptic_latitude_speed_from_fields(info)
        row = _directional_object_row(
            object_id=f'planet:{name}',
            object_index=object_index,
            name=name,
            symbol=DIRECTIONAL_3D_SYMBOLS.get(name, name[:2].strip() or name),
            object_type='planet',
            info=info,
            longitude_deg=ecliptic_longitude,
            latitude_deg=ecliptic_latitude,
            speed=speed,
            ecliptic_speed_source=ecliptic_speed_source,
            ecliptic_latitude_speed=ecliptic_latitude_speed,
            bfull=True,
            timestamp_iso=timestamp_iso,
            observer_latitude=latitude,
            observer_longitude=longitude,
            obliquity_deg=obliquity,
            horizontal_samples={
                'current': topocentric_samples['current'].get(name),
                'before': topocentric_samples['before'].get(name),
                'after': topocentric_samples['after'].get(name),
            },
        )
        data_gaps.extend(row.pop('_data_gaps', []))
        rows.append(row)
        object_index += 1

    for house_index, cusp_longitude in _chart_house_cusps(chart_data):
        row = _directional_object_row(
            object_id=f'house:{house_index}',
            object_index=object_index,
            name=f'House {house_index}',
            symbol=f'H{house_index}',
            object_type='cusp',
            info={},
            longitude_deg=cusp_longitude,
            latitude_deg=0.0,
            speed=None,
            ecliptic_speed_source='unavailable',
            ecliptic_latitude_speed=None,
            bfull=False,
            timestamp_iso=timestamp_iso,
            observer_latitude=latitude,
            observer_longitude=longitude,
            obliquity_deg=obliquity,
        )
        data_gaps.extend(row.pop('_data_gaps', []))
        rows.append(row)
        object_index += 1

    cd = chart_data if isinstance(chart_data, dict) else {}
    requested_house_system = str(
        getattr(active_settings, 'house_system_code', None)
        or cd.get('house_system_requested')
        or cd.get('house_system_code')
        or cd.get('house_system')
        or ''
    ).strip()
    chart_house_system = cd.get('house_system_effective') or cd.get('house_system_code') or cd.get('house_system')
    effective_house_system = str(chart_house_system or requested_house_system).strip()
    house_system_source = 'chart' if chart_house_system else 'request'
    polar_region = abs(latitude) >= (90.0 - abs(obliquity))

    return {
        'systems': ['EQL', 'EQU', 'HOR'],
        'body_policy': _directional_body_policy(
            include_modern,
            returned_names=[
                row['name']
                for row in rows
                if row.get('object_type') == 'planet'
            ],
        ),
        'frame_context': _directional_frame_context(timestamp_iso, latitude, longitude),
        'chart_info': {
            'utc_datetime': timestamp_iso,
            'latitude': _directional_round(latitude, 6, 0.0),
            'longitude': _directional_round(longitude, 6, 0.0),
            'rotation': DIRECTIONAL_3D_DEFAULT_ROTATION,
            'tilt': DIRECTIONAL_3D_DEFAULT_TILT,
            'house_system': effective_house_system,
            'house_system_requested': requested_house_system,
            'house_system_effective': effective_house_system,
            'house_system_source': house_system_source,
            'house_system_adjusted': bool(
                requested_house_system
                and effective_house_system
                and requested_house_system.upper() != effective_house_system.upper()
            ),
            'house_system_safety_override': False,
            'polar_region': polar_region,
            'obliquity': _directional_round(obliquity, 6, 23.439291),
            'obliquity_source': obliquity_source,
            'data_gaps': data_gaps,
        },
        'objects': rows,
    }


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


ASTROCARTOGRAPHY_INTERSECTION_RADIUS_KM = 1200.0
ASTROCARTOGRAPHY_PARAN_RADIUS_KM = 1200.0
ASTROCARTOGRAPHY_LOCAL_PARAN_ORB_DEG = 2.0
ASTROCARTOGRAPHY_GLOBAL_PARAN_ORB_DEG = 1.0
ASTROCARTOGRAPHY_LOCAL_PARAN_DISPLAY_LIMIT = 12
ASTROCARTOGRAPHY_GLOBAL_PARAN_DISPLAY_LIMIT = 24
ASTROCARTOGRAPHY_PARAN_FILTER_SCAN_LIMIT = 10_000
ASTROCARTOGRAPHY_DISTANCE_POLICY_VERSION = "2026-07-18"
ASTROCARTOGRAPHY_SUPPORTED_HOUSE_SYSTEM_CODES = frozenset(
    {"R", "P", "E", "W", "O", "C", "K", "T"}
)


def _validated_astrocartography_house_system_code(
    value: Any,
    *,
    default: Optional[str] = None,
) -> Optional[str]:
    if value in (None, ""):
        return default
    effective = str(value).strip().upper()
    try:
        encoded = effective.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("house_system_code must be a one-character Swiss Ephemeris code") from exc
    if len(encoded) != 1:
        raise ValueError("house_system_code must be a one-character Swiss Ephemeris code")
    if effective not in ASTROCARTOGRAPHY_SUPPORTED_HOUSE_SYSTEM_CODES:
        supported = ", ".join(sorted(ASTROCARTOGRAPHY_SUPPORTED_HOUSE_SYSTEM_CODES))
        raise ValueError(
            f"Unsupported house_system_code {effective!r}; supported codes are {supported}"
        )
    return effective


def _astrocartography_distance_policy() -> Dict[str, Any]:
    from astrocartography_service import (
        EXTENDED_READING_RADIUS_KM,
        PRIMARY_READING_RADIUS_KM,
    )

    return {
        "version": ASTROCARTOGRAPHY_DISTANCE_POLICY_VERSION,
        "units": "kilometres",
        "primary_radius_km": float(PRIMARY_READING_RADIUS_KM),
        "extended_radius_km": float(EXTENDED_READING_RADIUS_KM),
        "line_primary_radius_km": float(PRIMARY_READING_RADIUS_KM),
        "line_extended_radius_km": float(EXTENDED_READING_RADIUS_KM),
        "crossing_radius_km": float(EXTENDED_READING_RADIUS_KM),
        "intersection_radius_km": float(ASTROCARTOGRAPHY_INTERSECTION_RADIUS_KM),
        "local_paran_radius_km": float(ASTROCARTOGRAPHY_PARAN_RADIUS_KM),
        "local_paran_orb_deg": float(ASTROCARTOGRAPHY_LOCAL_PARAN_ORB_DEG),
        "global_paran_orb_deg": float(ASTROCARTOGRAPHY_GLOBAL_PARAN_ORB_DEG),
        "policy": "continuous_distance_falloff_with_named_display_bands",
        "warnings": [
            "Distance bands are interpretive display ranges, not physical boundaries.",
            "Birth-time uncertainty can move angular lines across these bands.",
        ],
    }


def _optional_nonnegative_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
        return None
    return parsed


def _datetime_span_minutes(start: Any, end: Any) -> Optional[float]:
    if not start or not end:
        return None
    start_text = str(start).strip()
    end_text = str(end).strip()
    if (
        ":" in start_text
        and ":" in end_text
        and all(separator not in start_text for separator in ("T", "t", " "))
        and all(separator not in end_text for separator in ("T", "t", " "))
    ):
        try:
            start_time = dt_time.fromisoformat(start_text)
            end_time = dt_time.fromisoformat(end_text)
            start_minutes = (
                (start_time.hour * 60.0)
                + start_time.minute
                + (start_time.second / 60.0)
                + (start_time.microsecond / 60_000_000.0)
            )
            end_minutes = (
                (end_time.hour * 60.0)
                + end_time.minute
                + (end_time.second / 60.0)
                + (end_time.microsecond / 60_000_000.0)
            )
            return max(0.0, end_minutes - start_minutes)
        except Exception:
            return None
    try:
        start_dt = _parse_iso_datetime(start)
        end_dt = _parse_iso_datetime(end)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        return max(0.0, (end_dt.astimezone(timezone.utc) - start_dt.astimezone(timezone.utc)).total_seconds() / 60.0)
    except Exception:
        return None


def _astrocartography_birth_time_quality(
    *,
    certification: Optional[Dict[str, Any]] = None,
    source_status: Optional[str] = None,
    uncertainty_minutes: Any = None,
) -> Dict[str, Any]:
    certification_payload = _normalize_snap_certification_payload(certification)
    status = str(
        (certification_payload or {}).get("status")
        or source_status
        or "user_entered_time"
    ).strip().lower()
    confidence = str((certification_payload or {}).get("confidence") or "").strip().lower()
    birth_meta = (certification_payload or {}).get("birth")
    if not isinstance(birth_meta, dict):
        birth_meta = {}
    source_time_status = str(
        source_status
        or birth_meta.get("source_time_status")
        or ""
    ).strip().lower()
    explicit_uncertainty = _optional_nonnegative_float(uncertainty_minutes)
    search_meta = (certification_payload or {}).get("search")
    if not isinstance(search_meta, dict):
        search_meta = {}
    search_window_minutes = _datetime_span_minutes(
        search_meta.get("start_time"),
        search_meta.get("end_time"),
    )
    certified_tokens = {"aa", "record", "certificate", "family_exact", "certified", "certified_source"}
    unknown_tokens = {
        "unknown",
        "time_unknown",
        "unknown_time",
        "unresolved",
        "unresolved_rectification",
        "insufficient_data",
    }
    approximate_tokens = {"approximate", "estimated", "rounded", "low", "none"}
    certified_time = status in certified_tokens or source_time_status in certified_tokens
    # A rectification search range describes what was tested; it is not an
    # error band around the selected candidate. Only a declared uncertainty
    # may reduce ranking resolution.
    effective_uncertainty = explicit_uncertainty

    warnings: List[str] = []

    if certified_time:
        ranking_eligible = True
        ranking_eligibility = "confirmed"
        confidence = confidence or "high"
    elif status == "rectified_candidate":
        ranking_eligible = effective_uncertainty is None or effective_uncertainty <= 5.0
        ranking_eligibility = "provisional" if ranking_eligible else "regional_only"
        confidence = confidence or "medium"
        warnings.append(
            "The selected time is a rectified candidate rather than an externally certified birth time."
        )
    elif status in unknown_tokens or source_time_status in unknown_tokens:
        ranking_eligible = False
        ranking_eligibility = "ineligible_unknown_time"
        confidence = confidence or "none"
        warnings.append(
            "City ranking is unavailable because the birth time is unknown or unresolved."
        )
    elif (
        status in approximate_tokens
        or source_time_status in approximate_tokens
        or (effective_uncertainty is not None and effective_uncertainty > 5.0)
    ):
        ranking_eligible = bool(effective_uncertainty is not None and effective_uncertainty <= 5.0)
        ranking_eligibility = "provisional" if ranking_eligible else "regional_only"
        confidence = confidence or "low"
        warnings.append(
            "The declared birth-time uncertainty is too wide for stable city-level ranking."
            if not ranking_eligible
            else "The ranking remains provisional because the birth time is approximate."
        )
    else:
        ranking_eligible = True
        ranking_eligibility = "provisional"
        confidence = confidence or "user_entered"
        warnings.append(
            "The birth time has not been externally certified; city ranks are provisional."
        )

    if (
        effective_uncertainty is not None
        and effective_uncertainty > 15.0
        and ranking_eligibility != "ineligible_unknown_time"
    ):
        ranking_eligible = False
        ranking_eligibility = "ineligible_low_resolution"
        warnings.append(
            "Birth-time uncertainty exceeds 15 minutes, so only broad regional map review is appropriate."
        )

    payload: Dict[str, Any] = {
        "kind": "birth_time_quality",
        "status": status,
        "confidence": confidence,
        "source_time_status": source_time_status or None,
        "uncertainty_minutes": (
            round(float(explicit_uncertainty), 3)
            if explicit_uncertainty is not None
            else None
        ),
        "effective_uncertainty_minutes": (
            round(float(effective_uncertainty), 3)
            if effective_uncertainty is not None
            else None
        ),
        "search_window_minutes": (
            round(float(search_window_minutes), 3)
            if search_window_minutes is not None
            else None
        ),
        "ranking_eligible": bool(ranking_eligible),
        "ranking_eligibility": ranking_eligibility,
        "warnings": list(dict.fromkeys(warnings)),
    }
    if certification_payload:
        payload["certification"] = _snap_certification_summary(certification_payload)
    return payload


def _attach_astrocartography_birth_time_quality(
    bundle: Dict[str, Any],
    *,
    certification: Optional[Dict[str, Any]] = None,
    source_status: Optional[str] = None,
    uncertainty_minutes: Any = None,
) -> Dict[str, Any]:
    quality = _astrocartography_birth_time_quality(
        certification=certification,
        source_status=source_status,
        uncertainty_minutes=uncertainty_minutes,
    )
    meta = dict(bundle.get("meta") or {})
    meta["birth_time"] = quality
    bundle["meta"] = meta
    bundle["birth_time"] = quality
    if certification:
        bundle["certification"] = copy.deepcopy(certification)
    return bundle


def _election_precision_from_saved_bundle(bundle: Any) -> Dict[str, Any]:
    """Translate persisted birth-time quality into election model precision."""
    payload = bundle if isinstance(bundle, dict) else {}
    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    quality = (
        payload.get('birth_time')
        if isinstance(payload.get('birth_time'), dict)
        else (
            meta.get('birth_time')
            if isinstance(meta.get('birth_time'), dict)
            else {}
        )
    )
    status = str(quality.get('status') or '').strip().lower()
    eligibility = str(
        quality.get('ranking_eligibility') or ''
    ).strip().lower()
    precision_safe = bool(quality.get('ranking_eligible'))
    if status in {
        'aa', 'record', 'certificate', 'family_exact', 'certified',
        'certified_source',
    }:
        precision_class = 'certified'
    elif status == 'rectified_candidate' and precision_safe:
        precision_class = 'timed'
    elif precision_safe:
        precision_class = 'known_time'
    else:
        precision_class = status or 'unknown'
    return {
        'precision_class': precision_class,
        'precision_safe': precision_safe,
        'precision_source': (
            f'saved_birth_time_quality:{eligibility or "unclassified"}'
        ),
    }


def _astrocartography_birth_time_sample_contexts(
    bundle: Dict[str, Any],
    *,
    bodies: Optional[Iterable[str]],
    angles: Optional[Iterable[str]],
    house_system_code: Optional[str],
    include_chart_data: bool,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from astrocartography_service import build_astrocartography_lines
    from astrocartography_uncertainty import (
        build_birth_time_sampling_plan,
        shift_iso_timestamp,
    )

    natal_meta = bundle.get("meta") or {}
    birth_time_quality = natal_meta.get("birth_time")
    if not isinstance(birth_time_quality, dict):
        return {
            "status": "not_sampled",
            "method": "bounded_symmetric_time_grid_v1",
            "reason": "Birth-time quality metadata is unavailable.",
            "samples": [],
        }, []
    sampling_plan = build_birth_time_sampling_plan(birth_time_quality)
    timestamp = str(natal_meta.get("timestamp") or "").strip()
    if not timestamp or not sampling_plan.get("samples"):
        return sampling_plan, []

    contexts: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for sample in sampling_plan.get("samples") or []:
        offset_minutes = float(sample.get("offset_minutes") or 0.0)
        shifted_timestamp = shift_iso_timestamp(timestamp, offset_minutes)
        timezone_name = str(natal_meta.get("timezone") or "").strip()
        if timezone_name:
            try:
                shifted_timestamp = (
                    _parse_iso_datetime(shifted_timestamp)
                    .astimezone(ZoneInfo(timezone_name))
                    .isoformat()
                )
            except Exception:
                pass
        try:
            lines_payload = build_astrocartography_lines(
                shifted_timestamp,
                bodies=bodies,
                angles=angles,
            )
        except Exception as exc:
            failures.append(
                {
                    "id": sample.get("id"),
                    "offset_minutes": sample.get("offset_minutes"),
                    "stage": "line_geometry",
                    "error": str(exc) or "Alternate-time line calculation failed.",
                }
            )
            continue
        sample_meta = {
            **natal_meta,
            "timestamp": shifted_timestamp,
            "birth_time": copy.deepcopy(natal_meta.get("birth_time") or {}),
        }
        chart_data: Dict[str, Any] = {}
        if include_chart_data:
            try:
                shifted_bundle = _compute_chart_bundle_for(
                    shifted_timestamp,
                    natal_meta.get("location"),
                    natal_meta.get("timezone"),
                    house_system_code=house_system_code,
                    latitude=natal_meta.get("latitude"),
                    longitude=natal_meta.get("longitude"),
                    include_modern=True,
                    include_chiron=True,
                )
            except Exception as exc:
                failures.append(
                    {
                        "id": sample.get("id"),
                        "offset_minutes": sample.get("offset_minutes"),
                        "stage": "relocated_chart_source",
                        "error": str(exc) or "Alternate-time chart calculation failed.",
                    }
                )
                continue
            chart_data = shifted_bundle.get("chart_data") or {}
            shifted_meta = shifted_bundle.get("meta") or {}
            sample_meta = {
                **sample_meta,
                **shifted_meta,
                "birth_time": copy.deepcopy(natal_meta.get("birth_time") or {}),
            }
        contexts.append(
            {
                **sample,
                "timestamp": shifted_timestamp,
                "meta": sample_meta,
                "chart_data": chart_data,
                "lines_payload": lines_payload,
            }
        )
    prepared_plan = {
        **sampling_plan,
        "status": (
            (
                "prepared_partial"
                if contexts
                else "failed"
            )
            if failures
            else sampling_plan.get("status")
        ),
        "prepared_sample_count": len(contexts),
        "requested_sample_count": len(sampling_plan.get("samples") or []),
        "coverage_complete": len(contexts) == len(sampling_plan.get("samples") or []),
        "failures": failures,
        "preparation_warning": (
            "One or more alternate-time calculations failed; sampled envelopes and score ranges are incomplete."
            if failures
            else None
        ),
        "samples": [
            {
                "id": sample.get("id"),
                "position": sample.get("position"),
                "offset_minutes": sample.get("offset_minutes"),
                "timestamp": sample.get("timestamp"),
            }
            for sample in contexts
        ],
    }
    return prepared_plan, contexts


def _astrocartography_filter_selection(args: Any) -> Tuple[Optional[List[str]], Optional[List[str]], Dict[str, Any]]:
    from astrocartography_service import DEFAULT_ANGLES, DEFAULT_BODIES

    def _raw_values(singular: str, plural: str) -> List[str]:
        if hasattr(args, "getlist"):
            values = list(args.getlist(singular))
            if not values:
                values = list(args.getlist(plural))
        elif isinstance(args, dict):
            raw = args.get(singular)
            if raw in (None, "", []):
                raw = args.get(plural)
            values = list(raw) if isinstance(raw, (list, tuple, set)) else ([raw] if raw not in (None, "") else [])
        else:
            values = []
        out: List[str] = []
        for value in values:
            if isinstance(value, str) and "," in value:
                out.extend(part.strip() for part in value.split(",") if part.strip())
            elif value not in (None, ""):
                out.append(str(value))
        return out

    raw_bodies = _raw_values("body", "bodies")
    raw_angles = _raw_values("angle", "angles")
    body_lookup = {str(name).strip().lower(): str(name) for name in DEFAULT_BODIES}
    angle_lookup = {str(name).strip().upper(): str(name).strip().upper() for name in DEFAULT_ANGLES}

    bodies: List[str] = []
    invalid_bodies: List[str] = []
    for raw in raw_bodies:
        token = str(raw or "").strip()
        canonical = body_lookup.get(token.lower())
        if canonical is None:
            invalid_bodies.append(token)
        elif canonical not in bodies:
            bodies.append(canonical)

    angles: List[str] = []
    invalid_angles: List[str] = []
    for raw in raw_angles:
        token = str(raw or "").strip().upper()
        canonical = angle_lookup.get(token)
        if canonical is None:
            invalid_angles.append(str(raw or "").strip())
        elif canonical not in angles:
            angles.append(canonical)

    if invalid_bodies:
        raise ValueError(f"Unsupported astrocartography body filter: {', '.join(invalid_bodies)}")
    if invalid_angles:
        raise ValueError(f"Unsupported astrocartography angle filter: {', '.join(invalid_angles)}")

    effective_bodies = bodies or None
    effective_angles = angles or None
    return effective_bodies, effective_angles, {
        "requested_bodies": raw_bodies,
        "requested_angles": raw_angles,
        "effective_bodies": bodies or list(DEFAULT_BODIES),
        "effective_angles": angles or list(DEFAULT_ANGLES),
        "paran_angle_policy": "both_angular_events_must_match_the_effective_angle_filter",
    }


def _filter_astrocartography_parans(
    payload: Dict[str, Any],
    *,
    angles: Optional[Iterable[str]],
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    allowed = {str(value or "").strip().upper() for value in (angles or []) if str(value or "").strip()}
    out = copy.deepcopy(payload)
    if not allowed:
        out["angle_filter"] = {"effective_angles": ["MC", "IC", "ASC", "DSC"], "applied": False}
        return out

    collection_key = "tracks" if isinstance(out.get("tracks"), list) else "items"
    rows = out.get(collection_key) or []
    filtered = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("angle_a") or "").upper() in allowed
        and str(row.get("angle_b") or "").upper() in allowed
    ]
    matched_count = len(filtered)
    if limit is not None:
        filtered = filtered[: max(1, int(limit))]
    out[collection_key] = filtered
    count_key = "track_count" if collection_key == "tracks" else "count"
    lead_key = "lead_track" if collection_key == "tracks" else "lead_paran"
    out[count_key] = matched_count
    out["returned_count"] = len(filtered)
    out[lead_key] = filtered[0] if filtered else None
    out["angle_filter"] = {
        "effective_angles": sorted(allowed),
        "applied": True,
        "policy": "both_angular_events_must_match",
    }
    if filtered:
        label = str(filtered[0].get("label") or "The lead paran")
        out["headline"] = (
            f"{label} is the clearest global paran corridor in the active map."
            if collection_key == "tracks"
            else f"{label} is the clearest nearby paran."
        )
    else:
        out["headline"] = "No parans match the active body and angle filters."
    return out


def _astrocartography_angular_event_registry(
    *,
    crossings: Any,
    intersections: Any,
    parans: Any,
) -> Dict[str, Any]:
    intersection_rows: List[Any] = []
    if isinstance(intersections, dict):
        if isinstance(intersections.get("items"), list):
            intersection_rows.extend(intersections.get("items") or [])
        else:
            intersection_rows.extend(intersections.get("primary_crossings") or [])
            intersection_rows.extend(intersections.get("blend_candidates") or [])
    elif isinstance(intersections, list):
        intersection_rows.extend(intersections)

    sections = {
        "crossings": crossings if isinstance(crossings, list) else [],
        "intersections": intersection_rows,
        "parans": (
            (parans or {}).get("items") or []
            if isinstance(parans, dict)
            else (parans if isinstance(parans, list) else [])
        ),
    }
    registry: Dict[str, Dict[str, Any]] = {}
    for section, rows in sections.items():
        for row in rows:
            if not isinstance(row, dict):
                continue
            canonical_id = str(row.get("canonical_event_id") or "").strip()
            if not canonical_id:
                continue
            event = registry.setdefault(
                canonical_id,
                {
                    "canonical_event_id": canonical_id,
                    "presentations": [],
                },
            )
            event["presentations"].append(
                {
                    "section": section,
                    "id": row.get("id"),
                    "event_kind": row.get("event_kind") or row.get("kind"),
                    "label": row.get("label"),
                }
            )
    events = sorted(registry.values(), key=lambda item: str(item.get("canonical_event_id") or ""))
    return {
        "policy": "canonical_event_id_is_counted_once; presentations_remain_available_for_display",
        "event_count": len(events),
        "duplicate_presentation_count": sum(max(0, len(item["presentations"]) - 1) for item in events),
        "events": events,
    }


def _astrocartography_ephemeris_provenance(
    timestamp_iso: str,
    *,
    bodies: Optional[Iterable[str]],
) -> Dict[str, Any]:
    from astrocartography_service import body_calculation_provenance

    selected_bodies = [str(value or "").strip() for value in (bodies or []) if str(value or "").strip()]
    payload: Dict[str, Any] = {
        "engine": "Swiss Ephemeris",
        "frame": "geocentric_equatorial",
        "degraded": False,
        "body_sources": {},
        "warnings": [],
    }
    for body in selected_bodies:
        payload["body_sources"][body] = {
            **body_calculation_provenance(body),
            "source": "swiss_ephemeris",
            "accuracy": "ephemeris",
            "degraded": False,
            "ranking_eligible": True,
        }
    if "Chiron" not in selected_bodies:
        return payload

    try:
        _swe = require_swisseph()
        dt = _parse_iso_datetime(timestamp_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        hour = dt.hour + (dt.minute / 60.0) + (dt.second / 3600.0) + (dt.microsecond / 3_600_000_000.0)
        jd_ut = _swe.julday(dt.year, dt.month, dt.day, hour, _swe.GREG_CAL)
        flags = _swe.FLG_SWIEPH | _swe.FLG_EQUATORIAL
        with _configure_synastry_ephemeris_path(_swe):
            with swisseph_lock():
                _swe.calc_ut(jd_ut, _swe.CHIRON, flags)
    except Exception:
        payload["degraded"] = True
        payload["body_sources"]["Chiron"] = {
            **body_calculation_provenance("Chiron"),
            "source": "jpl_mean_orbital_elements_fallback",
            "accuracy": "low_precision_approximation",
            "degraded": True,
            "ranking_eligible": False,
        }
        payload["warnings"].append(
            "Chiron used a low-precision orbital approximation because its Swiss Ephemeris file was unavailable; Chiron is excluded from ranking eligibility."
        )
    return payload


def _astrocartography_calculation_metadata(
    lines_payload: Dict[str, Any],
    *,
    timestamp_iso: str,
) -> Dict[str, Any]:
    from astrocartography_service import body_calculation_provenance

    geometry = copy.deepcopy(lines_payload.get("calculation") or {})
    service_bodies = geometry.get("bodies") if isinstance(geometry, dict) else None
    if isinstance(service_bodies, dict) and service_bodies:
        body_sources: Dict[str, Dict[str, Any]] = {}
        for body, record in service_bodies.items():
            if not isinstance(record, dict):
                continue
            body_name = str(body)
            body_metadata = body_calculation_provenance(body_name)
            body_sources[body_name] = {
                **body_metadata,
                "source": record.get("position_source") or record.get("ephemeris_engine"),
                "ephemeris_engine": record.get("ephemeris_engine"),
                "returned_flags": record.get("returned_flags"),
                "accuracy": record.get("accuracy") or "ephemeris",
                "degraded": bool(record.get("degraded")),
                "ranking_eligible": bool(
                    record.get("ranking_eligible", not bool(record.get("degraded")))
                ),
                "object_type": record.get("object_type")
                or body_metadata.get("object_type"),
                "node_type": record.get("node_type")
                or body_metadata.get("node_type"),
                "node_polarity": record.get("node_polarity")
                or body_metadata.get("node_polarity"),
                "astrocartography_scope": record.get("astrocartography_scope")
                or body_metadata.get("astrocartography_scope"),
                "extension_status": record.get("extension_status")
                or body_metadata.get("extension_status"),
                "doctrine_scope": record.get("doctrine_scope")
                or body_metadata.get("doctrine_scope"),
                "ranking_eligibility_scope": record.get("ranking_eligibility_scope")
                or body_metadata.get("ranking_eligibility_scope"),
                "extension_note": record.get("extension_note")
                or body_metadata.get("extension_note"),
            }
            body_sources[body_name] = {
                key: value
                for key, value in body_sources[body_name].items()
                if value is not None
            }
        ephemeris = {
            "engine": "Swiss Ephemeris",
            "frame": geometry.get("coordinate_frame") or "geocentric_equatorial",
            "degraded": any(bool(record.get("degraded")) for record in body_sources.values()),
            "body_sources": body_sources,
            "warnings": list(geometry.get("warnings") or []),
        }
    else:
        ephemeris = _astrocartography_ephemeris_provenance(
            timestamp_iso,
            bodies=lines_payload.get("bodies") or [],
        )
    geometry_warnings = list(geometry.get("warnings") or []) if isinstance(geometry, dict) else []
    return {
        **ephemeris,
        "geometry": geometry,
        "degraded": bool(ephemeris.get("degraded") or (geometry or {}).get("degraded")),
        "warnings": list(dict.fromkeys(
            list(ephemeris.get("warnings") or []) + geometry_warnings
        )),
    }


def _ranking_eligible_astrocartography_lines(lines_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    provenance = lines_payload.get("provenance") or {}
    body_sources = provenance.get("body_sources") or {}
    return [
        line
        for line in (lines_payload.get("lines") or [])
        if (body_sources.get(line.get("body")) or {}).get("ranking_eligible", True)
    ]


def _ranking_eligible_relocation_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(chart_data if isinstance(chart_data, dict) else {})
    planets = out.get("planets")
    if isinstance(planets, dict):
        out["planets"] = {
            name: payload
            for name, payload in planets.items()
            if not isinstance(payload, dict)
            or (payload.get("calculation_provenance") or {}).get("ranking_eligible", True)
        }
    elif isinstance(planets, list):
        out["planets"] = [
            payload
            for payload in planets
            if not isinstance(payload, dict)
            or (payload.get("calculation_provenance") or {}).get("ranking_eligible", True)
        ]
    return out


def _target_candidate_id(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("candidate_id", "id", "geonameid"):
        value = payload.get(key)
        if value not in (None, ""):
            if key == "geonameid":
                return f"geonames:{value}"
            return str(value)
    return None


def _validated_target_coordinates(latitude: Any, longitude: Any) -> Tuple[float, float]:
    if latitude in (None, "") or longitude in (None, ""):
        raise LocationError("target_latitude and target_longitude must be provided together")
    try:
        lat = float(latitude)
    except (TypeError, ValueError) as exc:
        raise LocationError("Invalid target_latitude") from exc
    try:
        lon = float(longitude)
    except (TypeError, ValueError) as exc:
        raise LocationError("Invalid target_longitude") from exc
    if not math.isfinite(lat) or not -90.0 <= lat <= 90.0:
        raise LocationError("Invalid target_latitude")
    if not math.isfinite(lon) or not -180.0 <= lon <= 180.0:
        raise LocationError("Invalid target_longitude")
    return lat, lon


def _target_coordinate_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat_a = math.radians(float(latitude_a))
    lat_b = math.radians(float(latitude_b))
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(float(longitude_b) - float(longitude_a))
    haversine = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2.0) ** 2
    )
    return 6371.0088 * 2.0 * math.asin(min(1.0, math.sqrt(haversine)))


def _normalized_location_identity_text(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join(
        "".join(
            character if character.isalnum() else " "
            for character in decomposed
            if not unicodedata.combining(character)
        ).split()
    )


def _normalized_astrocartography_target_id(
    value: Any,
    *,
    allow_custom: bool,
) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        return f"geonames:{int(text)}"
    if text.casefold().startswith("geonames:"):
        geonameid = text.split(":", 1)[1].strip()
        if not geonameid.isdigit():
            raise LocationError("Invalid GeoNames target_id")
        return f"geonames:{int(geonameid)}"
    if allow_custom:
        return text
    raise LocationError(
        "A non-GeoNames target_id requires exact target_latitude and target_longitude."
    )


def _astrocartography_catalog_target(
    target_location: str,
    *,
    target_id: Any = None,
) -> Optional[Dict[str, Any]]:
    from astrocartography_city_catalog import (
        city_catalog_candidate_matches_identity,
        find_exact_city_catalog_entries,
        get_city_catalog_entry_by_geonameid,
        parse_city_catalog_identity_query,
    )

    text = str(target_location or "").strip()
    if not text:
        return None

    parsed = parse_city_catalog_identity_query(text)
    normalized_target_id = _normalized_astrocartography_target_id(
        target_id,
        allow_custom=False,
    )
    if normalized_target_id:
        city = get_city_catalog_entry_by_geonameid(normalized_target_id)
        if city is None:
            raise LocationError(
                f"GeoNames target_id '{normalized_target_id}' is not present in the bundled city catalog."
            )
        if not city_catalog_candidate_matches_identity(city, parsed):
            raise LocationError(
                f"Location '{text}' does not match GeoNames target_id '{normalized_target_id}'."
            )
        exact_candidates = [city]
        identity_status = "id_exact"
        ambiguity: Dict[str, Any] = {
            "candidate_count": 1,
            "auto_selected": False,
        }
    else:
        exact_candidates = [
            city
            for city in find_exact_city_catalog_entries(parsed.get("city_query"))
            if city_catalog_candidate_matches_identity(city, parsed)
        ]
        exact_candidates.sort(
            key=lambda city: (
                -int(city.get("population") or 0),
                str(city.get("country_code") or ""),
                str(city.get("admin1_code") or ""),
                int(city.get("geonameid") or 0),
            )
        )
        if not exact_candidates:
            if parsed.get("has_explicit_qualifiers") or parsed.get("city_prefix_exact"):
                raise LocationError(
                    f"Location qualifiers do not match a bundled city catalog record: '{text}'."
                )
            return None

        identity_status = (
            "qualified_exact"
            if parsed.get("has_explicit_qualifiers")
            else "unqualified_exact"
        )
        ambiguity = {
            "candidate_count": len(exact_candidates),
            "auto_selected": False,
        }
        if len(exact_candidates) > 1:
            top_population = max(0, int(exact_candidates[0].get("population") or 0))
            second_population = max(0, int(exact_candidates[1].get("population") or 0))
            dominance_ratio = (
                float("inf")
                if top_population > 0 and second_population == 0
                else (
                    float(top_population) / float(second_population)
                    if second_population > 0
                    else 0.0
                )
            )
            ambiguity["dominance_ratio"] = (
                None if not math.isfinite(dominance_ratio) else round(dominance_ratio, 3)
            )
            if dominance_ratio < 5.0:
                raise LocationError(
                    f"Location '{text}' is ambiguous in the bundled city catalog; "
                    "provide a country/region, a GeoNames target_id, or exact coordinates."
                )
            identity_status = "population_dominant"
            ambiguity["auto_selected"] = True
            ambiguity["policy_threshold_ratio"] = 5.0

        city = exact_candidates[0]

    try:
        latitude = float(city.get("latitude"))
        longitude = float(city.get("longitude"))
    except (TypeError, ValueError):
        return None
    return {
        "candidate_id": _target_candidate_id(city),
        "query": text,
        "label": str(
            city.get("label")
            or city.get("query")
            or parsed.get("city_query")
        ),
        "latitude": latitude,
        "longitude": longitude,
        "coordinate_source": "bundled_geonames_catalog",
        "identity": {
            "status": identity_status,
            "policy": "exact_city_and_structured_qualifier_match",
            "city_query": parsed.get("city_query"),
            "qualifiers": list(parsed.get("qualifiers") or []),
            "country_code": str(city.get("country_code") or ""),
            "country_name": str(city.get("country_name") or ""),
            "admin1_code": str(city.get("admin1_code") or ""),
            "admin1_name": str(city.get("admin1_name") or ""),
            "admin1_aliases": [
                str(alias)
                for alias in (city.get("admin1_aliases") or [])
                if str(alias).strip()
            ],
            "ambiguity": ambiguity,
        },
    }


def _resolve_astrocartography_target(
    target_location: str,
    *,
    target_id: Any = None,
    target_latitude: Any = None,
    target_longitude: Any = None,
) -> Dict[str, Any]:
    has_lat = target_latitude not in (None, "")
    has_lon = target_longitude not in (None, "")
    if has_lat or has_lon:
        latitude, longitude = _validated_target_coordinates(target_latitude, target_longitude)
        candidate_id = _normalized_astrocartography_target_id(
            target_id,
            allow_custom=True,
        )
        identity_status = "request_coordinates"
        identity_policy = "caller_supplied_exact_coordinates"
        identity_validation: Dict[str, Any] = {}
        if candidate_id and candidate_id.startswith("geonames:"):
            from astrocartography_city_catalog import (
                city_catalog_candidate_matches_identity,
                get_city_catalog_entry_by_geonameid,
                parse_city_catalog_identity_query,
            )

            catalog_city = get_city_catalog_entry_by_geonameid(candidate_id)
            if catalog_city is None:
                raise LocationError(
                    f"GeoNames target_id '{candidate_id}' is not present in the bundled city catalog."
                )
            parsed = parse_city_catalog_identity_query(target_location)
            if not city_catalog_candidate_matches_identity(catalog_city, parsed):
                raise LocationError(
                    f"Location '{target_location}' does not match GeoNames target_id '{candidate_id}'."
                )
            coordinate_distance_km = _target_coordinate_distance_km(
                latitude,
                longitude,
                float(catalog_city.get("latitude")),
                float(catalog_city.get("longitude")),
            )
            coordinate_tolerance_km = 2.0
            if coordinate_distance_km > coordinate_tolerance_km:
                raise LocationError(
                    f"Coordinates for GeoNames target_id '{candidate_id}' differ from the bundled "
                    f"catalog by {coordinate_distance_km:.1f} km; provide matching coordinates "
                    "or use a custom target_id."
                )
            identity_status = "request_coordinates_id_validated"
            identity_policy = "caller_coordinates_with_geonames_identity_validation"
            identity_validation = {
                "geonames_coordinate_distance_km": round(coordinate_distance_km, 3),
                "geonames_coordinate_tolerance_km": coordinate_tolerance_km,
            }
        return {
            "candidate_id": candidate_id,
            "query": target_location,
            "label": target_location,
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_source": "atlas_candidate" if candidate_id else "request_coordinates",
            "identity": {
                "status": identity_status,
                "policy": identity_policy,
                "ambiguity": {
                    "candidate_count": 1,
                    "auto_selected": False,
                },
                **identity_validation,
            },
        }
    catalog_target = _astrocartography_catalog_target(
        target_location,
        target_id=target_id,
    )
    if catalog_target:
        return catalog_target

    from astrocartography_city_catalog import parse_city_catalog_identity_query

    parsed = parse_city_catalog_identity_query(target_location)
    if parsed.get("has_explicit_qualifiers"):
        raise LocationError(
            f"Location qualifiers could not be validated for '{target_location}'; provide exact coordinates."
        )
    latitude, longitude, resolved_name = safe_geocode(target_location)
    query_primary = _normalized_location_identity_text(
        parsed.get("city_query")
    )
    resolved_primary = _normalized_location_identity_text(
        str(resolved_name or "").split(",", 1)[0]
    )
    if (
        query_primary
        and resolved_primary
        and resolved_primary not in {
            query_primary,
            f"{query_primary} city",
            f"city of {query_primary}",
        }
    ):
        raise LocationError(
            f"Location '{target_location}' resolved to an unrelated catalog city ('{resolved_name}'); provide a country or exact coordinates."
        )
    return {
        "candidate_id": None,
        "query": target_location,
        "label": resolved_name or target_location,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "coordinate_source": "geocoder",
        "identity": {
            "status": "geocoder_exact",
            "policy": "exact_primary_city_match",
            "ambiguity": {
                "candidate_count": 1,
                "auto_selected": False,
            },
        },
    }


_RELOCATION_SIGN_RULERS = (
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
)


def _relocation_house_for_longitude(longitude: Any, cusps: List[float]) -> Optional[int]:
    try:
        point = float(longitude) % 360.0
    except (TypeError, ValueError):
        return None
    if len(cusps) < 12:
        return None
    for index in range(12):
        start = float(cusps[index]) % 360.0
        end = float(cusps[(index + 1) % 12]) % 360.0
        if start <= end:
            matched = start <= point < end
        else:
            matched = point >= start or point < end
        if matched:
            return index + 1
    return None


def _relocation_failure_payload(
    exc: Exception,
    *,
    latitude: float,
    longitude: float,
    house_system_code: str,
    coordinate_source: Optional[str] = None,
) -> Dict[str, Any]:
    messages: List[str] = []
    current: Optional[BaseException] = exc
    while current is not None and len(messages) < 8:
        message = str(current).strip()
        if message:
            messages.append(message)
        current = current.__cause__ or current.__context__
    house_failure = any("house" in message.lower() for message in messages)
    return {
        "available": False,
        "relocation_unavailable": True,
        "chart_data": {},
        "meta": {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "house_system_code": house_system_code,
        },
        "error": {
            "code": "polar_house_calculation_unavailable" if house_failure else "relocation_calculation_failed",
            "message": (
                f"The requested {house_system_code} house system is unavailable at this latitude."
                if house_failure
                else "The relocated chart could not be calculated for this candidate."
            ),
        },
        "provenance": {
            "engine": "Swiss Ephemeris",
            "calculation": "relocated_houses_from_natal_planet_positions",
            "house_system_code": house_system_code,
            "house_system_substituted": False,
            "coordinate_source": coordinate_source,
            "degraded": True,
        },
        "warnings": [
            "No alternate house system was substituted; line evidence remains available, but relocation-dependent scoring is unavailable."
        ],
    }


def _compute_relocation_chart_bundle(
    *,
    natal_chart_data: Dict[str, Any],
    natal_meta: Dict[str, Any],
    target_label: str,
    latitude: float,
    longitude: float,
    timezone_name: Optional[str],
    house_system_code: Optional[str],
    coordinate_source: str,
) -> Dict[str, Any]:
    timestamp = str(natal_meta.get("timestamp") or "").strip()
    if not timestamp:
        raise ValueError("A valid natal datetime is required for a relocated chart")
    dt = _parse_iso_datetime(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)

    effective_house_system = _validated_astrocartography_house_system_code(
        house_system_code or natal_chart_data.get("house_system_code"),
        default="R",
    )
    assert effective_house_system is not None
    encoded_house_system = effective_house_system.encode("ascii")

    try:
        _swe = require_swisseph()
        hour = dt.hour + (dt.minute / 60.0) + (dt.second / 3600.0) + (dt.microsecond / 3_600_000_000.0)
        jd_ut = _swe.julday(dt.year, dt.month, dt.day, hour, _swe.GREG_CAL)
        with swisseph_lock():
            house_values, ascmc = _swe.houses(
                jd_ut,
                float(latitude),
                float(longitude),
                encoded_house_system,
            )
        cusps = [float(value) % 360.0 for value in house_values]
        if len(cusps) != 12 or len(ascmc) < 2:
            raise RuntimeError("Swiss Ephemeris returned incomplete house data")
    except Exception as exc:
        return _relocation_failure_payload(
            exc,
            latitude=float(latitude),
            longitude=float(longitude),
            house_system_code=effective_house_system,
            coordinate_source=coordinate_source,
        )

    relocated = _extend_chart_data_for_synastry(
        copy.deepcopy(natal_chart_data if isinstance(natal_chart_data, dict) else {}),
        natal_meta,
        include_modern=True,
        include_chiron=True,
    )
    planets = relocated.get("planets")
    if isinstance(planets, dict):
        for payload in planets.values():
            if not isinstance(payload, dict):
                continue
            house = _relocation_house_for_longitude(payload.get("longitude"), cusps)
            if house is not None:
                payload["house"] = house
    elif isinstance(planets, list):
        for payload in planets:
            if not isinstance(payload, dict):
                continue
            house = _relocation_house_for_longitude(payload.get("longitude"), cusps)
            if house is not None:
                payload["house"] = house

    house_rulers = {
        str(index + 1): _RELOCATION_SIGN_RULERS[int(float(cusp) // 30.0) % 12]
        for index, cusp in enumerate(cusps)
    }
    relocated["houses"] = cusps
    relocated["house_cusps"] = list(cusps)
    relocated["ascendant"] = float(ascmc[0]) % 360.0
    relocated["midheaven"] = float(ascmc[1]) % 360.0
    relocated["house_rulers"] = house_rulers
    relocated["house_system_code"] = effective_house_system
    birth_time_quality = natal_meta.get("birth_time") or {}
    declared_uncertainty = birth_time_quality.get("uncertainty_minutes")
    if declared_uncertainty is None:
        declared_uncertainty = birth_time_quality.get("effective_uncertainty_minutes")
    if declared_uncertainty is not None:
        relocated["birth_time_uncertainty_minutes"] = declared_uncertainty
    else:
        eligibility = str(birth_time_quality.get("ranking_eligibility") or "").strip().lower()
        confidence_label = str(birth_time_quality.get("confidence") or "").strip().lower()
        if eligibility.startswith("ineligible"):
            relocated["birth_time_confidence"] = 0.2
        elif eligibility == "confirmed":
            relocated["birth_time_confidence"] = 1.0 if confidence_label == "high" else 0.95
        elif eligibility == "regional_only":
            relocated["birth_time_confidence"] = 0.55
        else:
            relocated["birth_time_confidence"] = 0.8
    relocated["birth_time_accuracy"] = birth_time_quality.get("status")
    relocated["birth_time_unknown"] = not bool(birth_time_quality.get("ranking_eligible", True))
    tz_info = dict(relocated.get("timezone_info") or {})
    tz_info["timezone"] = timezone_name
    tz_info["coordinates"] = {
        "latitude": float(latitude),
        "longitude": float(longitude),
    }
    relocated["timezone_info"] = tz_info
    planet_sources: Dict[str, Dict[str, Any]] = {}
    if isinstance(planets, dict):
        planet_rows = planets.items()
    elif isinstance(planets, list):
        planet_rows = (
            (
                str(payload.get("planet") or payload.get("name") or "").strip(),
                payload,
            )
            for payload in planets
            if isinstance(payload, dict)
        )
    else:
        planet_rows = []
    for name, payload in planet_rows:
        calculation = payload.get("calculation_provenance") if isinstance(payload, dict) else None
        if name and isinstance(calculation, dict):
            planet_sources[str(name)] = copy.deepcopy(calculation)

    calculation_degraded = any(
        bool(source.get("degraded"))
        for source in planet_sources.values()
    )
    relocation_warnings: List[str] = []
    if not timezone_name:
        relocation_warnings.append(
            "The target timezone could not be resolved; relocated houses still use the exact natal UTC instant and target coordinates."
        )
    if calculation_degraded:
        relocation_warnings.append(
            "Low-precision supplemental planet positions remain visible with provenance but are excluded from relocation ranking."
        )
    meta = {
        "timestamp": timestamp,
        "location": target_label,
        "timezone": timezone_name,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "coordinate_source": coordinate_source,
        "house_system_code": effective_house_system,
    }
    provenance = {
        "engine": "Swiss Ephemeris",
        "calculation": "relocated_houses_from_natal_planet_positions",
        "house_system_code": effective_house_system,
        "house_system_substituted": False,
        "coordinate_source": coordinate_source,
        "degraded": calculation_degraded,
        "planet_sources": planet_sources,
        "warnings": relocation_warnings,
    }
    return {
        "available": True,
        "relocation_unavailable": False,
        "chart_data": relocated,
        "meta": meta,
        "provenance": provenance,
        "warnings": relocation_warnings,
    }


def _natal_from_query(args) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve natal chart_data from query params: use snap if provided, else use natal_* params."""
    bundle = _natal_bundle_from_query(args)
    return bundle.get('chart_data') or {}, bundle.get('meta') or {}


def _require_astrocartography_datetime_with_time(value: Any, *, field_name: str) -> None:
    if isinstance(value, datetime):
        return
    text = str(value or "").strip()
    has_iso_time = (
        len(text) >= 16
        and text[10] in {"T", "t", " "}
        and text[11:13].isdigit()
        and text[13] == ":"
        and text[14:16].isdigit()
    )
    if not has_iso_time:
        raise ValueError(
            f"{field_name} must include an ISO-8601 date and explicit time (YYYY-MM-DDTHH:MM)"
        )


def _bundle_from_snap_id(
    snap_id: str,
    *,
    house_system_code: Optional[str] = None,
    missing_error: str = 'Snap not found',
) -> Dict[str, Any]:
    snap = _hydrate_snap_payload(
        _snaps().get(snap_id),
        infer_coordinates=False,
    )
    if not snap:
        raise ValueError(missing_error)
    _require_confirmed_saved_snap_context(
        snap,
        feature_label='This place/time-sensitive calculation',
    )
    dt = snap.get('effective_datetime')
    loc = snap.get('location')
    tz = snap.get('timezone')
    if not dt:
        raise ValueError("Natal snap is missing a valid birth datetime")
    if not loc:
        raise ValueError("Natal snap is missing a birth location")
    _require_astrocartography_datetime_with_time(
        dt,
        field_name="Natal snap birth datetime",
    )
    bundle = _compute_chart_bundle_for(
        dt,
        loc,
        tz,
        house_system_code=house_system_code,
        latitude=snap.get('latitude'),
        longitude=snap.get('longitude'),
    )
    meta = dict(bundle.get("meta") or {})
    coordinate_provenance = dict(snap.get("coordinate_provenance") or {})
    coordinates_persisted = bool(
        coordinate_provenance.get("persisted_with_chart")
        if "persisted_with_chart" in coordinate_provenance
        else (
            snap.get("latitude") is not None
            and snap.get("longitude") is not None
        )
    )
    meta["coordinate_provenance"] = coordinate_provenance
    meta["coordinate_source"] = (
        "saved_snap"
        if coordinates_persisted
        else "resolved_saved_location"
    )
    bundle["meta"] = meta
    certification = _normalize_snap_certification_payload(
        snap.get("certification")
        or ((snap.get("dashboard") or {}).get("certification") if isinstance(snap.get("dashboard"), dict) else None)
    )
    source_status = None
    if isinstance(certification, dict):
        birth_meta = certification.get("birth")
        if isinstance(birth_meta, dict):
            source_status = birth_meta.get("source_time_status")
    return _attach_astrocartography_birth_time_quality(
        bundle,
        certification=certification,
        source_status=source_status,
        uncertainty_minutes=snap.get("birth_time_uncertainty_minutes"),
    )


def _natal_bundle_from_query(args) -> Dict[str, Any]:
    """Resolve an internal natal chart bundle from query params."""
    snap_id = args.get('natal_snap_id')
    if snap_id:
        house = _validated_astrocartography_house_system_code(
            args.get('house_system_code'),
        )
        return _bundle_from_snap_id(snap_id, house_system_code=house, missing_error='Natal snap not found')
    nat_dt = args.get('natal_datetime')
    nat_loc = args.get('natal_location')
    nat_tz = args.get('natal_timezone')
    house = _validated_astrocartography_house_system_code(
        args.get('house_system_code'),
    )
    if not nat_dt or not nat_loc:
        raise ValueError('natal_datetime and natal_location required')
    _require_astrocartography_datetime_with_time(
        nat_dt,
        field_name="natal_datetime",
    )
    coords = _coords_from_request_args(args)
    bundle = _compute_chart_bundle_for(
        nat_dt,
        nat_loc,
        nat_tz,
        house_system_code=house,
        latitude=(coords[0] if coords else None),
        longitude=(coords[1] if coords else None),
    )
    meta = dict(bundle.get("meta") or {})
    meta["coordinate_source"] = "request_coordinates" if coords else "geocoder"
    bundle["meta"] = meta
    uncertainty_value = args.get("natal_time_uncertainty_minutes")
    if uncertainty_value in (None, ""):
        uncertainty_value = args.get("natal_time_accuracy_minutes")
    return _attach_astrocartography_birth_time_quality(
        bundle,
        source_status=(
            args.get("natal_time_status")
            or args.get("natal_source_time_status")
        ),
        uncertainty_minutes=uncertainty_value,
    )


def _transit_bundle_from_query(args, natal_meta: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    transit_dt = args.get('transit_datetime')
    if not transit_dt:
        return None
    fallback_meta = natal_meta or {}
    transit_loc = args.get('transit_location') or fallback_meta.get('location')
    transit_tz = args.get('transit_timezone') or fallback_meta.get('timezone')
    house = args.get('house_system_code') or None
    coords = None
    if (
        transit_loc
        and fallback_meta.get('location')
        and _normalize_location_key(transit_loc) == _normalize_location_key(fallback_meta.get('location'))
    ):
        try:
            lat = fallback_meta.get('latitude')
            lon = fallback_meta.get('longitude')
            if lat is not None and lon is not None:
                coords = (float(lat), float(lon))
        except Exception:
            coords = None
    return _compute_chart_bundle_for(
        transit_dt,
        transit_loc,
        transit_tz,
        house_system_code=house,
        latitude=(coords[0] if coords else None),
        longitude=(coords[1] if coords else None),
    )


def _astrocartography_target_analysis(
    *,
    target_location: str,
    resolved_name: str,
    latitude: float,
    longitude: float,
    natal_meta: Dict[str, Any],
    natal_lines_payload: Dict[str, Any],
    house_system_code: Optional[str],
    natal_chart_data: Optional[Dict[str, Any]] = None,
    target_id: Optional[str] = None,
    coordinate_source: str = "geocoder",
    target_identity: Optional[Dict[str, Any]] = None,
    target_timezone: Optional[str] = None,
    goal_id: Optional[str] = None,
    transit_lines_payload: Optional[Dict[str, Any]] = None,
    transit_meta: Optional[Dict[str, Any]] = None,
    birth_time_sampling_plan: Optional[Dict[str, Any]] = None,
    natal_time_samples: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from astrocartography_service import (
        PRIMARY_READING_RADIUS_KM,
        EXTENDED_READING_RADIUS_KM,
        build_paran_candidates_for_point,
        build_delineation_report,
        build_goal_scoring_context,
        build_intersection_workspace,
        build_location_reading,
        build_local_space_workspace,
        crossing_candidates_for_point,
    )
    from astrocartography_goal_engine import (
        evaluate_goal_model,
        extract_relocation_features,
        goal_model_score_polarity,
        summarize_relocation_features,
    )
    from astrocartography_goal_models import get_goal_model
    from astrocartography_uncertainty import attach_birth_time_sample_evaluations

    target_payload = {
        'candidate_id': target_id,
        'label': resolved_name or target_location,
        'query': target_location,
        'latitude': round(float(latitude), 6),
        'longitude': round(float(longitude), 6),
        'coordinate_source': coordinate_source,
    }
    if target_identity:
        target_payload["identity"] = copy.deepcopy(target_identity)
    distance_policy = _astrocartography_distance_policy()
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
        max_distance_km=distance_policy["intersection_radius_km"],
    )
    natal_origin_lat = natal_meta.get("latitude")
    natal_origin_lon = natal_meta.get("longitude")
    natal_local_space: Dict[str, Any]
    try:
        natal_origin_lat = float(natal_origin_lat)
        natal_origin_lon = float(natal_origin_lon)
        natal_local_space = build_local_space_workspace(
            str(natal_meta.get('timestamp') or ''),
            natal_origin_lat,
            natal_origin_lon,
            bodies=natal_lines_payload.get('bodies') or None,
        )
        natal_local_space = {
            **(natal_local_space or {}),
            "origin": {
                "kind": "birthplace",
                "label": natal_meta.get("location"),
                "latitude": natal_origin_lat,
                "longitude": natal_origin_lon,
                "coordinate_source": natal_meta.get("coordinate_source"),
            },
            "origin_kind": "birthplace",
            "degraded": False,
        }
    except Exception as exc:
        natal_local_space = {
            "available": False,
            "origin_kind": "birthplace",
            "degraded": True,
            "error": "Natal Local Space is unavailable because birthplace coordinates were not resolved.",
            "warnings": [str(exc)] if str(exc) else [],
        }
    natal_parans = build_paran_candidates_for_point(
        str(natal_meta.get('timestamp') or ''),
        float(latitude),
        float(longitude),
        bodies=natal_lines_payload.get('bodies') or None,
        limit=ASTROCARTOGRAPHY_PARAN_FILTER_SCAN_LIMIT,
        max_distance_km=distance_policy["local_paran_radius_km"],
        orb_deg=distance_policy["local_paran_orb_deg"],
    )
    natal_parans = _filter_astrocartography_parans(
        natal_parans,
        angles=natal_lines_payload.get("angles"),
        limit=ASTROCARTOGRAPHY_LOCAL_PARAN_DISPLAY_LIMIT,
    )
    natal_provenance = natal_lines_payload.get("provenance") or _astrocartography_ephemeris_provenance(
        str(natal_meta.get("timestamp") or ""),
        bodies=natal_lines_payload.get("bodies") or [],
    )

    result: Dict[str, Any] = {
        'target': target_payload,
        'birth_time': natal_meta.get("birth_time"),
        'distance_policy': distance_policy,
        'calculation': {
            "natal": natal_provenance,
            "degraded": bool((natal_provenance or {}).get("degraded")),
            "warnings": list((natal_provenance or {}).get("warnings") or []),
        },
        'natal': {
            'meta': natal_meta,
            'nearest_lines': natal_reading.get('nearest_lines') or [],
            'reading': natal_reading,
            'crossings': natal_crossings,
            'intersections': natal_intersections,
            'parans': natal_parans,
            'local_space': natal_local_space,
            'angular_events': _astrocartography_angular_event_registry(
                crossings=natal_crossings,
                intersections=natal_intersections,
                parans=natal_parans,
            ),
        },
    }
    if target_identity:
        result["calculation"]["target_resolution"] = copy.deepcopy(target_identity)
    result["provenance"] = result["calculation"]

    transit_reading = None
    transit_scoring = None
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
            max_distance_km=distance_policy["intersection_radius_km"],
        )
        transit_local_space = build_local_space_workspace(
            str(transit_meta.get('timestamp') or ''),
            float(latitude),
            float(longitude),
            bodies=transit_lines_payload.get('bodies') or None,
        )
        transit_local_space = {
            **(transit_local_space or {}),
            "origin": {
                "kind": "transit_target",
                "label": resolved_name or target_location,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "coordinate_source": coordinate_source,
            },
            "origin_kind": "transit_target",
        }
        transit_parans = build_paran_candidates_for_point(
            str(transit_meta.get('timestamp') or ''),
            float(latitude),
            float(longitude),
            bodies=transit_lines_payload.get('bodies') or None,
            limit=ASTROCARTOGRAPHY_PARAN_FILTER_SCAN_LIMIT,
            max_distance_km=distance_policy["local_paran_radius_km"],
            orb_deg=distance_policy["local_paran_orb_deg"],
        )
        transit_parans = _filter_astrocartography_parans(
            transit_parans,
            angles=transit_lines_payload.get("angles"),
            limit=ASTROCARTOGRAPHY_LOCAL_PARAN_DISPLAY_LIMIT,
        )
        result['transit'] = {
            'meta': transit_meta,
            'nearest_lines': transit_reading.get('nearest_lines') or [],
            'reading': transit_reading,
            'crossings': transit_crossings,
            'intersections': transit_intersections,
            'parans': transit_parans,
            'local_space': transit_local_space,
            'angular_events': _astrocartography_angular_event_registry(
                crossings=transit_crossings,
                intersections=transit_intersections,
                parans=transit_parans,
            ),
        }
        transit_provenance = (
            transit_lines_payload.get("provenance")
            or _astrocartography_ephemeris_provenance(
                str(transit_meta.get("timestamp") or ""),
                bodies=transit_lines_payload.get("bodies") or [],
            )
        )
        result["calculation"]["transit"] = transit_provenance
        result["calculation"]["degraded"] = bool(
            result["calculation"].get("degraded")
            or transit_provenance.get("degraded")
        )
        result["calculation"]["warnings"] = list(dict.fromkeys(
            list(result["calculation"].get("warnings") or [])
            + list(transit_provenance.get("warnings") or [])
        ))

    if isinstance(natal_chart_data, dict) and natal_chart_data:
        relocation_bundle = _compute_relocation_chart_bundle(
            natal_chart_data=natal_chart_data,
            natal_meta=natal_meta,
            target_label=resolved_name or target_location,
            latitude=float(latitude),
            longitude=float(longitude),
            timezone_name=target_timezone,
            house_system_code=house_system_code,
            coordinate_source=coordinate_source,
        )
    else:
        try:
            fallback_bundle = _compute_chart_bundle_for(
                str(natal_meta.get('timestamp') or ''),
                resolved_name or target_location,
                target_timezone,
                house_system_code=house_system_code,
                latitude=float(latitude),
                longitude=float(longitude),
                include_modern=True,
                include_chiron=True,
            )
            relocation_bundle = {
                **fallback_bundle,
                "available": True,
                "relocation_unavailable": False,
                "provenance": {
                    "engine": "full_chart_engine",
                    "calculation": "relocated_chart",
                    "house_system_code": house_system_code,
                    "house_system_substituted": False,
                    "coordinate_source": coordinate_source,
                    "degraded": False,
                    "warnings": [],
                },
                "warnings": [],
            }
        except Exception as exc:
            relocation_bundle = _relocation_failure_payload(
                exc,
                latitude=float(latitude),
                longitude=float(longitude),
                house_system_code=str(house_system_code or "R"),
                coordinate_source=coordinate_source,
            )

    relocated_local_space = build_local_space_workspace(
        str(natal_meta.get('timestamp') or ''),
        float(latitude),
        float(longitude),
        bodies=natal_lines_payload.get('bodies') or None,
    )
    relocated_local_space = {
        **(relocated_local_space or {}),
        "origin": {
            "kind": "relocated_target",
            "label": resolved_name or target_location,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "coordinate_source": coordinate_source,
        },
        "origin_kind": "relocated_target",
    }
    if relocation_bundle.get("available") is False:
        relocation_features = {
            "planet_houses": {},
            "planet_angles": {},
            "house_occupancy": {},
            "metrics": {},
        }
        relocation_summary: Dict[str, Any] = {}
        result['relocation'] = {
            "available": False,
            "relocation_unavailable": True,
            'meta': relocation_bundle.get('meta') or {},
            "error": relocation_bundle.get("error"),
            "warnings": relocation_bundle.get("warnings") or [],
            "provenance": relocation_bundle.get("provenance") or {},
            "local_space": relocated_local_space,
        }
    else:
        relocation_features = extract_relocation_features(
            _ranking_eligible_relocation_chart(relocation_bundle.get('chart_data') or {})
        )
        relocation_summary = summarize_relocation_features(relocation_features)
        result['relocation'] = {
            "available": True,
            "relocation_unavailable": False,
            'meta': relocation_bundle.get('meta') or {},
            "chart": relocation_bundle.get("chart_data") or {},
            'summary': relocation_summary,
            "provenance": relocation_bundle.get("provenance") or {},
            "warnings": relocation_bundle.get("warnings") or [],
            "local_space": relocated_local_space,
        }

    relocation_provenance = relocation_bundle.get("provenance") or {}
    result["calculation"]["relocation"] = relocation_provenance
    result["calculation"]["degraded"] = bool(
        result["calculation"].get("degraded")
        or relocation_provenance.get("degraded")
        or relocation_bundle.get("available") is False
    )
    result["calculation"]["warnings"] = list(dict.fromkeys(
        list(result["calculation"].get("warnings") or [])
        + list(relocation_provenance.get("warnings") or [])
        + list(relocation_bundle.get("warnings") or [])
    ))

    goal_eval = None
    if goal_id:
        natal_scoring = build_goal_scoring_context(
            _ranking_eligible_astrocartography_lines(natal_lines_payload),
            float(latitude),
            float(longitude),
            primary_radius_km=PRIMARY_READING_RADIUS_KM,
            extended_radius_km=EXTENDED_READING_RADIUS_KM,
        )
        if transit_lines_payload and transit_meta:
            transit_scoring = build_goal_scoring_context(
                _ranking_eligible_astrocartography_lines(transit_lines_payload),
                float(latitude),
                float(longitude),
                primary_radius_km=PRIMARY_READING_RADIUS_KM,
                extended_radius_km=EXTENDED_READING_RADIUS_KM,
            )
        goal_model = get_goal_model(goal_id)
        goal_eval = evaluate_goal_model(
            goal_id,
            natal_rows=natal_scoring.get('nearest_lines') or [],
            natal_crossings=natal_scoring.get('crossings') or [],
            relocation=relocation_features,
            transit_rows=(transit_scoring.get('nearest_lines') or []) if transit_scoring else None,
            transit_crossings=(transit_scoring.get('crossings') or []) if transit_scoring else None,
        )
        sample_evaluations: List[Dict[str, Any]] = []
        for sample in natal_time_samples or []:
            sample_lines_payload = sample.get("lines_payload") or {}
            sample_scoring = build_goal_scoring_context(
                _ranking_eligible_astrocartography_lines(sample_lines_payload),
                float(latitude),
                float(longitude),
                primary_radius_km=PRIMARY_READING_RADIUS_KM,
                extended_radius_km=EXTENDED_READING_RADIUS_KM,
            )
            sample_relocation_bundle = _compute_relocation_chart_bundle(
                natal_chart_data=sample.get("chart_data") or {},
                natal_meta=sample.get("meta") or {},
                target_label=resolved_name or target_location,
                latitude=float(latitude),
                longitude=float(longitude),
                timezone_name=target_timezone,
                house_system_code=house_system_code,
                coordinate_source=coordinate_source,
            )
            if sample_relocation_bundle.get("available") is False:
                sample_relocation_features = {
                    "planet_houses": {},
                    "planet_angles": {},
                    "house_occupancy": {},
                    "metrics": {},
                }
            else:
                sample_relocation_features = extract_relocation_features(
                    _ranking_eligible_relocation_chart(
                        sample_relocation_bundle.get("chart_data") or {}
                    )
                )
            sample_goal_eval = evaluate_goal_model(
                goal_id,
                natal_rows=sample_scoring.get("nearest_lines") or [],
                natal_crossings=sample_scoring.get("crossings") or [],
                relocation=sample_relocation_features,
                transit_rows=(transit_scoring.get("nearest_lines") or []) if transit_scoring else None,
                transit_crossings=(transit_scoring.get("crossings") or []) if transit_scoring else None,
            )
            lead_line = (sample_scoring.get("nearest_lines") or [{}])[0] or {}
            sample_evaluations.append(
                {
                    "id": sample.get("id"),
                    "position": sample.get("position"),
                    "offset_minutes": sample.get("offset_minutes"),
                    "timestamp": sample.get("timestamp"),
                    "evaluation": sample_goal_eval,
                    "lead_line": lead_line.get("label"),
                    "lead_line_distance_km": lead_line.get("distance_km"),
                    "relocation_available": sample_relocation_bundle.get("available", True),
                }
            )
        goal_eval = attach_birth_time_sample_evaluations(
            goal_eval,
            sampling_plan=birth_time_sampling_plan or {},
            sample_evaluations=sample_evaluations,
        )
        goal_eval["ranking_eligible"] = bool(
            goal_eval.get("ranking_eligible", True)
            and
            (natal_meta.get("birth_time") or {}).get("ranking_eligible", True)
            and relocation_bundle.get("available", True)
        )
        goal_eval["ranking_warnings"] = list(dict.fromkeys(
            list(goal_eval.get("ranking_warnings") or [])
            + list((natal_meta.get("birth_time") or {}).get("warnings") or [])
            + list((natal_provenance or {}).get("warnings") or [])
            + list(relocation_bundle.get("warnings") or [])
        ))
        result['goal'] = {
            'id': goal_model.get('id'),
            'label': goal_model.get('label'),
            'summary': goal_model.get('summary'),
            'score_polarity': goal_model_score_polarity(goal_model),
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
    bodies, angles, filter_policy = _astrocartography_filter_selection(request.args)
    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
    natal_provenance = _astrocartography_calculation_metadata(
        natal_lines,
        timestamp_iso=str(natal_meta.get("timestamp") or ""),
    )
    natal_lines["provenance"] = natal_provenance
    for line in natal_lines.get("lines") or []:
        body_provenance = (natal_provenance.get("body_sources") or {}).get(line.get("body"))
        if body_provenance:
            line["calculation_provenance"] = body_provenance
    birth_time_sampling_plan, natal_time_samples = _astrocartography_birth_time_sample_contexts(
        bundle,
        bodies=natal_lines.get("bodies") or bodies,
        angles=natal_lines.get("angles") or angles,
        house_system_code=_validated_astrocartography_house_system_code(
            request.args.get("house_system_code"),
        ),
        include_chart_data=False,
    )
    from astrocartography_uncertainty import summarize_line_uncertainty_corridors
    line_uncertainty = summarize_line_uncertainty_corridors(
        natal_lines,
        sampling_plan=birth_time_sampling_plan,
        sample_line_payloads=natal_time_samples,
    )
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
        'birth_time': natal_meta.get("birth_time"),
        'birth_time_sampling': birth_time_sampling_plan,
        'calculation': {
            "natal": natal_provenance,
            "degraded": bool(natal_provenance.get("degraded")),
            "warnings": natal_provenance.get("warnings") or [],
        },
        'filters': {
            'bodies': natal_lines.get('bodies') or [],
            'angles': natal_lines.get('angles') or [],
            'policy': filter_policy,
        },
        'map': {
            'natal_lines': natal_lines.get('lines') or [],
            'natal_line_uncertainty': line_uncertainty,
            'global_parans': _filter_astrocartography_parans(
                _safe_astrocartography_optional_payload(
                    'natal_global_parans',
                    lambda: build_global_paran_tracks(
                        str(natal_meta.get('timestamp') or ''),
                        bodies=natal_lines.get('bodies') or None,
                        orb_deg=ASTROCARTOGRAPHY_GLOBAL_PARAN_ORB_DEG,
                        limit=ASTROCARTOGRAPHY_PARAN_FILTER_SCAN_LIMIT,
                    ),
                    empty_global_parans,
                ),
                angles=natal_lines.get("angles"),
                limit=ASTROCARTOGRAPHY_GLOBAL_PARAN_DISPLAY_LIMIT,
            ),
        },
        'distance_policy': _astrocartography_distance_policy(),
        'defaults': {
            'primary_radius_km': int(PRIMARY_READING_RADIUS_KM),
            'extended_radius_km': int(EXTENDED_READING_RADIUS_KM),
            'distance_policy_version': ASTROCARTOGRAPHY_DISTANCE_POLICY_VERSION,
        },
    }

    transit_bundle = _transit_bundle_from_query(request.args, natal_meta=natal_meta)
    if transit_bundle:
        transit_meta = transit_bundle.get('meta') or {}
        transit_lines = build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        transit_provenance = _astrocartography_calculation_metadata(
            transit_lines,
            timestamp_iso=str(transit_meta.get("timestamp") or ""),
        )
        for line in transit_lines.get("lines") or []:
            body_provenance = (transit_provenance.get("body_sources") or {}).get(line.get("body"))
            if body_provenance:
                line["calculation_provenance"] = body_provenance
        response['transit'] = transit_meta
        response['calculation']['transit'] = transit_provenance
        response['calculation']['degraded'] = bool(
            response['calculation']['degraded'] or transit_provenance.get("degraded")
        )
        response['calculation']['warnings'] = list(dict.fromkeys(
            list(response['calculation']['warnings'])
            + list(transit_provenance.get("warnings") or [])
        ))
        response['map']['transit_lines'] = transit_lines.get('lines') or []
        response['map']['transit_global_parans'] = _filter_astrocartography_parans(
            _safe_astrocartography_optional_payload(
                'transit_global_parans',
                lambda: build_global_paran_tracks(
                    str(transit_meta.get('timestamp') or ''),
                    bodies=transit_lines.get('bodies') or None,
                    orb_deg=ASTROCARTOGRAPHY_GLOBAL_PARAN_ORB_DEG,
                    limit=ASTROCARTOGRAPHY_PARAN_FILTER_SCAN_LIMIT,
                ),
                empty_global_parans,
            ),
            angles=transit_lines.get("angles"),
            limit=ASTROCARTOGRAPHY_GLOBAL_PARAN_DISPLAY_LIMIT,
        )

    response["provenance"] = response["calculation"]
    return _json_ok(response)


def _validate_astrocartography_goal_filters(
    goal_id: Optional[str],
    *,
    bodies: Optional[List[str]],
    angles: Optional[List[str]],
) -> None:
    from astrocartography_service import DEFAULT_ANGLES, DEFAULT_BODIES

    supported_bodies = set(DEFAULT_BODIES)
    supported_angles = set(DEFAULT_ANGLES)
    invalid_bodies = [str(value) for value in (bodies or []) if str(value) not in supported_bodies]
    invalid_angles = [str(value) for value in (angles or []) if str(value).upper() not in supported_angles]
    if invalid_bodies:
        raise ValueError(f"Unsupported astrocartography body filter: {', '.join(invalid_bodies)}")
    if invalid_angles:
        raise ValueError(f"Unsupported astrocartography angle filter: {', '.join(invalid_angles)}")
    if not goal_id:
        return
    from astrocartography_atlas_engine import describe_goal_search_filters

    filter_meta = describe_goal_search_filters(
        goal_id,
        selected_bodies=bodies,
        selected_angles=angles,
    )
    if filter_meta.get('excluded_by_filters'):
        raise ValueError("Current body/angle filters exclude the selected goal model's atlas signature")


def _build_astrocartography_location_payload(args: Any) -> Dict[str, Any]:
    from astrocartography_service import (
        build_astrocartography_lines,
    )

    target_location = str(args.get('target_location') or '').strip()
    if not target_location:
        raise ValueError('target_location is required')

    bodies, angles, filter_policy = _astrocartography_filter_selection(args)
    target = _resolve_astrocartography_target(
        target_location,
        target_id=args.get("target_id"),
        target_latitude=args.get("target_latitude"),
        target_longitude=args.get("target_longitude"),
    )
    target_timezone = (
        args.get("target_timezone")
        or _resolve_timezone_for_context(
            None,
            str(target.get("label") or target_location),
            coords=(float(target["latitude"]), float(target["longitude"])),
            lookup_coords=False,
        )
    )
    bundle = _natal_bundle_from_query(args)
    natal_meta = bundle.get('meta') or {}
    house_system_code = _validated_astrocartography_house_system_code(
        args.get('house_system_code'),
    )
    goal_id = str(args.get('goal_id') or '').strip().lower() or None
    _validate_astrocartography_goal_filters(goal_id, bodies=bodies, angles=angles)
    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
    natal_lines["provenance"] = _astrocartography_calculation_metadata(
        natal_lines,
        timestamp_iso=str(natal_meta.get("timestamp") or ""),
    )
    birth_time_sampling_plan, natal_time_samples = _astrocartography_birth_time_sample_contexts(
        bundle,
        bodies=natal_lines.get("bodies") or bodies,
        angles=natal_lines.get("angles") or angles,
        house_system_code=house_system_code,
        include_chart_data=bool(goal_id),
    )

    response: Dict[str, Any] = {
        'birth_time': natal_meta.get("birth_time"),
        'birth_time_sampling': birth_time_sampling_plan,
        'distance_policy': _astrocartography_distance_policy(),
        'filters': {
            "bodies": natal_lines.get("bodies") or [],
            "angles": natal_lines.get("angles") or [],
            "policy": filter_policy,
        },
    }

    transit_bundle = _transit_bundle_from_query(args, natal_meta=natal_meta)
    transit_meta = (transit_bundle.get('meta') or {}) if transit_bundle else None
    transit_lines = (
        build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        if transit_meta else None
    )
    if transit_lines and transit_meta:
        transit_lines["provenance"] = _astrocartography_calculation_metadata(
            transit_lines,
            timestamp_iso=str(transit_meta.get("timestamp") or ""),
        )
    response.update(
        _astrocartography_target_analysis(
            target_location=target_location,
            resolved_name=str(target.get("label") or target_location),
            latitude=float(target["latitude"]),
            longitude=float(target["longitude"]),
            natal_meta=natal_meta,
            natal_lines_payload=natal_lines,
            house_system_code=house_system_code,
            natal_chart_data=bundle.get("chart_data") or {},
            target_id=target.get("candidate_id"),
            coordinate_source=str(target.get("coordinate_source") or "geocoder"),
            target_identity=target.get("identity"),
            target_timezone=target_timezone or None,
            goal_id=goal_id,
            transit_lines_payload=transit_lines,
            transit_meta=transit_meta,
            birth_time_sampling_plan=birth_time_sampling_plan,
            natal_time_samples=natal_time_samples,
        )
    )
    from astrocartography_uncertainty import summarize_line_uncertainty_corridors
    response.setdefault("natal", {})["line_uncertainty"] = summarize_line_uncertainty_corridors(
        natal_lines,
        sampling_plan=birth_time_sampling_plan,
        sample_line_payloads=natal_time_samples,
    )
    return response


@astro_clock_bp.route('/astrocartography/location', methods=['GET'])
@_error_handler
def astrocartography_location():
    return _json_ok(_build_astrocartography_location_payload(request.args))


@astro_clock_bp.route('/astrocartography/relocation', methods=['GET'])
@_error_handler
def astrocartography_relocation():
    payload = _build_astrocartography_location_payload(request.args)
    response: Dict[str, Any] = {
        "target": payload.get("target"),
        "birth_time": payload.get("birth_time"),
        "distance_policy": payload.get("distance_policy"),
        "calculation": payload.get("calculation"),
        "relocation": payload.get("relocation"),
    }
    if payload.get("goal"):
        response["goal"] = payload.get("goal")
    if payload.get("location_score"):
        response["location_score"] = payload.get("location_score")
    response["provenance"] = response["calculation"]
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
    from astrocartography_goal_engine import get_goal_score_polarity
    from astrocartography_service import build_astrocartography_lines

    target_locations = [str(value or '').strip() for value in request.args.getlist('target_location') if str(value or '').strip()]
    if len(target_locations) < 2:
        raise ValueError('At least two target_location values are required')
    if len(target_locations) > 8:
        raise ValueError('A maximum of 8 target_location values is supported')

    bundle = _natal_bundle_from_query(request.args)
    natal_meta = bundle.get('meta') or {}
    bodies, angles, filter_policy = _astrocartography_filter_selection(request.args)
    house_system_code = _validated_astrocartography_house_system_code(
        request.args.get('house_system_code'),
    )
    goal_id = str(request.args.get('goal_id') or '').strip().lower() or None
    _validate_astrocartography_goal_filters(goal_id, bodies=bodies, angles=angles)
    score_polarity = get_goal_score_polarity(goal_id) if goal_id else 'higher_is_better'

    natal_lines = build_astrocartography_lines(str(natal_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
    natal_lines["provenance"] = _astrocartography_calculation_metadata(
        natal_lines,
        timestamp_iso=str(natal_meta.get("timestamp") or ""),
    )
    birth_time_sampling_plan, natal_time_samples = _astrocartography_birth_time_sample_contexts(
        bundle,
        bodies=natal_lines.get("bodies") or bodies,
        angles=natal_lines.get("angles") or angles,
        house_system_code=house_system_code,
        include_chart_data=bool(goal_id),
    )
    transit_bundle = _transit_bundle_from_query(request.args, natal_meta=natal_meta)
    transit_meta = (transit_bundle.get('meta') or {}) if transit_bundle else None
    transit_lines = (
        build_astrocartography_lines(str(transit_meta.get('timestamp') or ''), bodies=bodies, angles=angles)
        if transit_meta else None
    )
    if transit_lines and transit_meta:
        transit_lines["provenance"] = _astrocartography_calculation_metadata(
            transit_lines,
            timestamp_iso=str(transit_meta.get("timestamp") or ""),
        )

    target_ids = request.args.getlist("target_id")
    target_latitudes = request.args.getlist("target_latitude")
    target_longitudes = request.args.getlist("target_longitude")
    target_timezones = request.args.getlist("target_timezone")
    has_coordinates = bool(target_latitudes or target_longitudes)
    if has_coordinates and (
        len(target_latitudes) != len(target_locations)
        or len(target_longitudes) != len(target_locations)
    ):
        raise ValueError(
            "Compare coordinates must include one target_latitude and target_longitude for every target_location"
        )
    for label, values in (
        ("target_id", target_ids),
        ("target_timezone", target_timezones),
    ):
        if values and len(values) != len(target_locations):
            raise ValueError(f"Compare {label} values must align with every target_location")

    targets: List[Dict[str, Any]] = []
    for index, target_location in enumerate(target_locations):
        target = _resolve_astrocartography_target(
            target_location,
            target_id=(target_ids[index] if target_ids else None),
            target_latitude=(target_latitudes[index] if has_coordinates else None),
            target_longitude=(target_longitudes[index] if has_coordinates else None),
        )
        target_timezone = (
            target_timezones[index]
            if target_timezones
            else _resolve_timezone_for_context(
                None,
                str(target.get("label") or target_location),
                coords=(float(target["latitude"]), float(target["longitude"])),
                lookup_coords=False,
            )
        )
        analysis = _astrocartography_target_analysis(
            target_location=target_location,
            resolved_name=str(target.get("label") or target_location),
            latitude=float(target["latitude"]),
            longitude=float(target["longitude"]),
            natal_meta=natal_meta,
            natal_lines_payload=natal_lines,
            house_system_code=house_system_code,
            natal_chart_data=bundle.get("chart_data") or {},
            target_id=target.get("candidate_id"),
            coordinate_source=str(target.get("coordinate_source") or "geocoder"),
            target_identity=target.get("identity"),
            target_timezone=target_timezone or None,
            goal_id=goal_id,
            transit_lines_payload=transit_lines,
            transit_meta=transit_meta,
            birth_time_sampling_plan=birth_time_sampling_plan,
            natal_time_samples=natal_time_samples,
        )
        targets.append(analysis)

    birth_time_quality = natal_meta.get("birth_time") or {}
    ranking_candidates = [
        item
        for item in targets
        if (item.get("location_score") or {}).get("ranking_eligible", True)
    ]
    from astrocartography_uncertainty import apply_cross_location_rank_stability
    rank_stability = (
        apply_cross_location_rank_stability(
            ranking_candidates,
            score_polarity=score_polarity,
            top_k=len(ranking_candidates),
            scope_candidate_count=len(targets),
        )
        if goal_id
        else {
            "status": "not_applicable",
            "reason": "A selected goal is required before locations can be ranked.",
            "candidate_count": len(targets),
        }
    )
    for item in targets:
        if item in ranking_candidates:
            continue
        location_score = item.get("location_score")
        if isinstance(location_score, dict):
            location_score["rank_stability"] = {
                "status": "not_applicable",
                "reason": "This location is not eligible for ranking.",
            }
    ranking = sorted(
        [
            {
                'candidate_id': (item.get('target') or {}).get('candidate_id'),
                'label': (item.get('target') or {}).get('label'),
                'query': (item.get('target') or {}).get('query'),
                'latitude': (item.get('target') or {}).get('latitude'),
                'longitude': (item.get('target') or {}).get('longitude'),
                'coordinate_source': (item.get('target') or {}).get('coordinate_source'),
                'score': ((item.get('location_score') or {}).get('score')),
                'raw_score': ((item.get('location_score') or {}).get('raw_score')),
                'evidence_strength': ((item.get('location_score') or {}).get('evidence_strength')),
                'interpretation_status': ((item.get('location_score') or {}).get('interpretation_status')),
                'ranking_eligible': ((item.get('location_score') or {}).get('ranking_eligible', True)),
                'uncertainty': ((item.get('location_score') or {}).get('uncertainty') or {}),
                'rank_stability': ((item.get('location_score') or {}).get('rank_stability') or {}),
                'top_supports': ((item.get('location_score') or {}).get('top_supports') or [])[:2],
                'top_cautions': ((item.get('location_score') or {}).get('top_cautions') or [])[:2],
            }
            for item in ranking_candidates
        ],
        key=lambda item: build_location_score_sort_key(
            {
                'raw_score': item.get('raw_score'),
                'score': item.get('score'),
            },
            label=item.get('label') or '',
            score_polarity=score_polarity,
        ),
    )
    for idx, item in enumerate(ranking, start=1):
        item['rank'] = idx

    response: Dict[str, Any] = {
        'birth_time': birth_time_quality,
        'birth_time_sampling': birth_time_sampling_plan,
        'ranking_eligible': bool(birth_time_quality.get("ranking_eligible", True)),
        'rank_stability': rank_stability,
        'calculation': {
            "natal": natal_lines.get("provenance") or {},
            "transit": (transit_lines or {}).get("provenance") if transit_lines else None,
            "degraded": bool(
                (natal_lines.get("provenance") or {}).get("degraded")
                or ((transit_lines or {}).get("provenance") or {}).get("degraded")
            ),
            "warnings": list(dict.fromkeys(
                list((natal_lines.get("provenance") or {}).get("warnings") or [])
                + list(((transit_lines or {}).get("provenance") or {}).get("warnings") or [])
            )),
        },
        'distance_policy': _astrocartography_distance_policy(),
        'filters': {
            "bodies": natal_lines.get("bodies") or [],
            "angles": natal_lines.get("angles") or [],
            "policy": filter_policy,
        },
        'targets': targets,
        'ranking': ranking if birth_time_quality.get("ranking_eligible", True) else [],
    }
    if goal_id and targets:
        response['goal'] = targets[0].get('goal')
    response["provenance"] = response["calculation"]
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
    _prune_terminal_sessions_locked(
        _atlas_search_sessions,
        is_terminal=_atlas_search_session_is_terminal,
        max_sessions=_ATLAS_SEARCH_SESSION_MAX,
        ttl_seconds=_ATLAS_SEARCH_SESSION_TTL_SECONDS,
        now=now,
    )


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
        'runtime': _background_runtime_payload(
            'astrocartography_atlas_search',
            session_max=_ATLAS_SEARCH_SESSION_MAX,
            session_ttl_seconds=_ATLAS_SEARCH_SESSION_TTL_SECONDS,
        ),
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
    from astrocartography_service import build_astrocartography_lines

    def _check_should_continue() -> None:
        if should_continue is None:
            return
        should_continue()

    goal_id = str(params.get('goal_id') or '').strip().lower()
    if not goal_id:
        raise ValueError(
            'goal_id is required for ranked atlas search; use the map or a '
            'single-location reading for a neutral, unranked overview'
        )

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
    birth_time_quality = natal_meta.get("birth_time") or {}
    if not birth_time_quality.get("ranking_eligible", True):
        raise ValueError(
            "City ranking is unavailable for this birth-time quality; provide a certified, rectified, or sufficiently precise birth time."
        )
    selected_bodies, selected_angles, selection_policy = _astrocartography_filter_selection(params)
    house_system_code = _validated_astrocartography_house_system_code(
        params.get('house_system_code'),
    )
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
    natal_provenance = _astrocartography_calculation_metadata(
        natal_lines,
        timestamp_iso=str(natal_meta.get("timestamp") or ""),
    )
    natal_lines["provenance"] = natal_provenance
    birth_time_sampling_plan, natal_time_samples = _astrocartography_birth_time_sample_contexts(
        bundle,
        bodies=relevant_bodies,
        angles=relevant_angles,
        house_system_code=house_system_code,
        include_chart_data=True,
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
        transit_lines["provenance"] = _astrocartography_calculation_metadata(
            transit_lines,
            timestamp_iso=str(transit_meta.get("timestamp") or ""),
        )

    relocation_natal_chart_data = _extend_chart_data_for_synastry(
        bundle.get("chart_data") or {},
        natal_meta,
        include_modern=True,
        include_chiron=True,
    )

    def _resolve_relocation_bundle(item: Dict[str, Any]) -> Dict[str, Any]:
        target = item.get('target') or {}
        atlas_city = item.get('atlas_city') or {}
        try:
            target_lat = float(target.get('latitude'))
            target_lon = float(target.get('longitude'))
        except Exception:
            target_lat = None
            target_lon = None
        if target_lat is None or target_lon is None:
            return {
                "available": False,
                "relocation_unavailable": True,
                "chart_data": {},
                "error": {
                    "code": "candidate_coordinates_missing",
                    "message": "Exact atlas candidate coordinates are missing.",
                },
                "warnings": ["The candidate was retained with line-only evidence."],
            }
        return _compute_relocation_chart_bundle(
            natal_chart_data=relocation_natal_chart_data,
            natal_meta=natal_meta,
            target_label=str(target.get('label') or target.get('query') or ''),
            latitude=target_lat,
            longitude=target_lon,
            timezone_name=atlas_city.get('timezone') or None,
            house_system_code=house_system_code,
            coordinate_source=str(target.get("coordinate_source") or "atlas_candidate"),
        )

    atlas_time_samples: List[Dict[str, Any]] = []
    for sample in natal_time_samples:
        sample_chart_data = _extend_chart_data_for_synastry(
            sample.get("chart_data") or {},
            sample.get("meta") or {},
            include_modern=True,
            include_chiron=True,
        )
        sample_meta = sample.get("meta") or {}

        def _sample_relocation_resolver(
            item: Dict[str, Any],
            *,
            _sample_chart_data: Dict[str, Any] = sample_chart_data,
            _sample_meta: Dict[str, Any] = sample_meta,
        ) -> Dict[str, Any]:
            target = item.get("target") or {}
            atlas_city = item.get("atlas_city") or {}
            try:
                target_lat = float(target.get("latitude"))
                target_lon = float(target.get("longitude"))
            except Exception:
                return {
                    "available": False,
                    "relocation_unavailable": True,
                    "chart_data": {},
                    "error": {
                        "code": "candidate_coordinates_missing",
                        "message": "Exact atlas candidate coordinates are missing.",
                    },
                    "warnings": ["The uncertainty sample was retained with line-only evidence."],
                }
            return _compute_relocation_chart_bundle(
                natal_chart_data=_sample_chart_data,
                natal_meta=_sample_meta,
                target_label=str(target.get("label") or target.get("query") or ""),
                latitude=target_lat,
                longitude=target_lon,
                timezone_name=atlas_city.get("timezone") or None,
                house_system_code=house_system_code,
                coordinate_source=str(target.get("coordinate_source") or "atlas_candidate"),
            )

        atlas_time_samples.append(
            {
                "id": sample.get("id"),
                "position": sample.get("position"),
                "offset_minutes": sample.get("offset_minutes"),
                "timestamp": sample.get("timestamp"),
                "natal_lines": _ranking_eligible_astrocartography_lines(
                    sample.get("lines_payload") or {}
                ),
                "relocation_bundle_resolver": _sample_relocation_resolver,
            }
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
        natal_lines=_ranking_eligible_astrocartography_lines(natal_lines),
        transit_lines=(
            _ranking_eligible_astrocartography_lines(transit_lines)
            if transit_lines else None
        ),
        query=query_text or None,
        country_code=country_code or None,
        continent_code=continent_code or None,
        resolution=resolution,
        limit=limit,
        relocation_bundle_resolver=_resolve_relocation_bundle,
        progress_callback=_atlas_progress,
        should_continue=_check_should_continue,
        birth_time_sampling_plan=birth_time_sampling_plan,
        birth_time_samples=atlas_time_samples,
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
            'score_polarity': search_result.get('score_polarity') or 'higher_is_better',
            'selection_required_for_ranking': True,
        },
        'natal': natal_meta,
        'birth_time': birth_time_quality,
        'birth_time_sampling': search_result.get("birth_time_sampling") or birth_time_sampling_plan,
        'ranking_eligible': True,
        'calculation': {
            "natal": natal_provenance,
            "transit": (transit_lines or {}).get("provenance") if transit_lines else None,
            "degraded": bool(
                natal_provenance.get("degraded")
                or ((transit_lines or {}).get("provenance") or {}).get("degraded")
            ),
            "warnings": list(dict.fromkeys(
                list(natal_provenance.get("warnings") or [])
                + list(((transit_lines or {}).get("provenance") or {}).get("warnings") or [])
            )),
        },
        'filters': {
            'bodies': relevant_bodies,
            'angles': relevant_angles,
            'policy': selection_policy,
        },
        'distance_policy': _astrocartography_distance_policy(),
        'atlas': {
            'query': search_result.get('query') or {},
            'resolution': search_result.get('resolution') or {},
            'candidate_pool_policy': search_result.get('candidate_pool_policy') or {},
            'catalog_candidate_count': search_result.get('catalog_candidate_count'),
            'live_candidate_count': search_result.get('live_candidate_count'),
            'used_live_augmentation': search_result.get('used_live_augmentation'),
            'candidate_count': search_result.get('candidate_count'),
            'shortlisted_count': search_result.get('shortlisted_count'),
            'viable_count': search_result.get('viable_count'),
            'signal_floor_raw_score': search_result.get('signal_floor_raw_score'),
            'score_polarity': search_result.get('score_polarity') or 'higher_is_better',
            'shortlist_strategy': search_result.get('shortlist_strategy'),
            'relocation_unavailable_count': search_result.get('relocation_unavailable_count', 0),
            'relocation_unavailable': search_result.get('relocation_unavailable') or [],
            'ranking_eligibility': birth_time_quality.get("ranking_eligibility"),
            'ranking_mode': search_result.get('ranking_mode') or 'goal_specific_astrology',
            'ranking_basis': search_result.get('ranking_basis') or {},
            'practical_context': search_result.get('practical_context') or {},
            'goal_selection': search_result.get('goal_selection') or {},
            'geographic_diversity': search_result.get('geographic_diversity') or {},
            'birth_time_sampling': search_result.get('birth_time_sampling') or birth_time_sampling_plan,
            'rank_stability': search_result.get('rank_stability') or {},
        },
        'results': search_result.get('results') or [],
        'ranking': search_result.get('ranking') or [],
    }
    if transit_meta:
        response['transit'] = transit_meta
    response["provenance"] = response["calculation"]
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
    initialized = _initialize_background_session(
        _atlas_search_sessions,
        _atlas_search_lock,
        session_id,
        {
            'ready': False,
            'failed': False,
            'cancelled': False,
            'cancel_requested': False,
            'percent': 0.0,
            'stage': 'queued',
            'message': 'Atlas search queued',
            'done': 0,
            'total': 0,
        },
        is_terminal=_atlas_search_session_is_terminal,
        max_sessions=_ATLAS_SEARCH_SESSION_MAX,
        ttl_seconds=_ATLAS_SEARCH_SESSION_TTL_SECONDS,
    )
    if not initialized:
        return _background_busy_response('Astrocartography atlas search')

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

    if not _submit_background_job(f'astrocartography-atlas-{session_id[:8]}', _worker):
        _update_atlas_search_session(
            session_id,
            ready=False,
            failed=True,
            stage='failed',
            message='Atlas search could not be queued',
            error='Background capacity is full; retry later',
        )
        return _background_busy_response('Astrocartography atlas search')
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
        return _missing_volatile_session_response('Astrocartography atlas search')
    return _json_ok({'session_id': session_id, 'progress': _atlas_search_progress_payload(session_id)})


@astro_clock_bp.route('/astrocartography/atlas-search/progress', methods=['GET'])
@_error_handler
def astrocartography_atlas_search_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    if not _atlas_search_session_snapshot(session_id):
        return _missing_volatile_session_response('Astrocartography atlas search')
    return _json_ok(_atlas_search_progress_payload(session_id))


@astro_clock_bp.route('/astrocartography/atlas-search/result', methods=['GET'])
@_error_handler
def astrocartography_atlas_search_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _atlas_search_session_snapshot(session_id)
    if not session:
        return _missing_volatile_session_response('Astrocartography atlas search')
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
        'runtime': _background_runtime_payload(
            'mundane_scan',
            session_max=_MUNDANE_SCAN_SESSION_MAX,
            session_ttl_seconds=_MUNDANE_SCAN_SESSION_TTL_SECONDS,
        ),
    }


def _mundane_scan_session_is_terminal(session: Optional[Dict[str, Any]]) -> bool:
    return bool(session and (session.get('ready') or session.get('failed')))


def _prune_mundane_scan_sessions_locked(now: Optional[float] = None) -> None:
    _prune_terminal_sessions_locked(
        _mundane_scan_sessions,
        is_terminal=_mundane_scan_session_is_terminal,
        max_sessions=_MUNDANE_SCAN_SESSION_MAX,
        ttl_seconds=_MUNDANE_SCAN_SESSION_TTL_SECONDS,
        now=now,
    )


def _update_mundane_scan_session(session_id: str, **updates: Any) -> None:
    with _mundane_scan_lock:
        now = perf_counter()
        _prune_mundane_scan_sessions_locked(now)
        session = _mundane_scan_sessions.get(session_id)
        if session is None:
            session = {'session_id': session_id, 'created_at': now}
            _mundane_scan_sessions[session_id] = session
        session.update(updates)
        session['updated_at'] = now


def _mundane_scan_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _mundane_scan_lock:
        _prune_mundane_scan_sessions_locked()
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
        'error': str(sess.get('error') or '') if sess.get('failed') else '',
        'runtime': _background_runtime_payload(
            'weather_scan',
            session_max=_WEATHER_SCAN_SESSION_MAX,
            session_ttl_seconds=_WEATHER_SCAN_SESSION_TTL_SECONDS,
        ),
    }


def _weather_scan_session_is_terminal(session: Dict[str, Any]) -> bool:
    return bool(session.get('ready') or session.get('failed'))


def _prune_weather_scan_sessions_locked(now: Optional[float] = None) -> None:
    _prune_terminal_sessions_locked(
        _weather_scan_sessions,
        is_terminal=_weather_scan_session_is_terminal,
        max_sessions=_WEATHER_SCAN_SESSION_MAX,
        ttl_seconds=_WEATHER_SCAN_SESSION_TTL_SECONDS,
        now=now,
    )


def _update_weather_scan_session(session_id: str, **updates: Any) -> None:
    with _weather_scan_lock:
        now = perf_counter()
        session = _weather_scan_sessions.get(session_id)
        if session is None:
            session = {'session_id': session_id, 'created_at': now}
            _weather_scan_sessions[session_id] = session
        session.update(updates)
        session['updated_at'] = now
        _prune_weather_scan_sessions_locked(now)


def _weather_scan_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _weather_scan_lock:
        _prune_weather_scan_sessions_locked()
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

    initialized = _initialize_background_session(
        _weather_scan_sessions,
        _weather_scan_lock,
        session_id,
        {
            'ready': False,
            'failed': False,
            'percent': 0.0,
            'stage': 'queued',
            'message': 'Weather scan queued',
            'done': 0,
            'total': 0,
        },
        is_terminal=_weather_scan_session_is_terminal,
        max_sessions=_WEATHER_SCAN_SESSION_MAX,
        ttl_seconds=_WEATHER_SCAN_SESSION_TTL_SECONDS,
    )
    if not initialized:
        return _background_busy_response('Weather scan')

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

    if not _submit_background_job(f'weather-scan-{session_id[:8]}', _worker):
        _update_weather_scan_session(
            session_id,
            ready=False,
            failed=True,
            percent=1.0,
            stage='failed',
            message='Weather scan could not be queued',
            error='Background capacity is full; retry later',
        )
        return _background_busy_response('Weather scan')
    return _json_ok({'session_id': session_id, 'progress': _weather_scan_progress_payload(session_id)})


@astro_clock_bp.route('/weather/scan/progress', methods=['GET'])
@_error_handler
def weather_scan_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    if not _weather_scan_session_snapshot(session_id):
        return _missing_volatile_session_response('Weather scan')
    return _json_ok(_weather_scan_progress_payload(session_id))


@astro_clock_bp.route('/weather/scan/result', methods=['GET'])
@_error_handler
def weather_scan_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _weather_scan_session_snapshot(session_id)
    if not session:
        return _missing_volatile_session_response('Weather scan')
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

    initialized = _initialize_background_session(
        _mundane_scan_sessions,
        _mundane_scan_lock,
        session_id,
        {
            'ready': False,
            'failed': False,
            'percent': 0.0,
            'stage': 'queued',
            'message': 'Mundane scan queued',
            'done': 0,
            'total': 0,
        },
        is_terminal=_mundane_scan_session_is_terminal,
        max_sessions=_MUNDANE_SCAN_SESSION_MAX,
        ttl_seconds=_MUNDANE_SCAN_SESSION_TTL_SECONDS,
    )
    if not initialized:
        return _background_busy_response('Mundane scan')

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

    if not _submit_background_job(f'mundane-scan-{session_id[:8]}', _worker):
        _update_mundane_scan_session(
            session_id,
            ready=False,
            failed=True,
            percent=1.0,
            stage='failed',
            message='Mundane scan could not be queued',
            error='Background capacity is full; retry later',
        )
        return _background_busy_response('Mundane scan')
    return _json_ok({'session_id': session_id, 'progress': _mundane_scan_progress_payload(session_id)})


@astro_clock_bp.route('/mundane/scan/progress', methods=['GET'])
@_error_handler
def mundane_scan_progress():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    if not _mundane_scan_session_snapshot(session_id):
        return _missing_volatile_session_response('Mundane scan')
    return _json_ok(_mundane_scan_progress_payload(session_id))


@astro_clock_bp.route('/mundane/scan/result', methods=['GET'])
@_error_handler
def mundane_scan_result():
    session_id = str(request.args.get('session_id') or request.args.get('sid') or '').strip()
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    session = _mundane_scan_session_snapshot(session_id)
    if not session:
        return _missing_volatile_session_response('Mundane scan')
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


def _cohere_saved_synastry_chart(
    chart_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Make saved planet houses agree with the one frozen cusp set."""
    out = copy.deepcopy(chart_data if isinstance(chart_data, dict) else {})
    cusps = _synastry_house_cusps(out)
    changes: List[Dict[str, Any]] = []
    if len(cusps) != 12:
        return out, changes
    out['house_cusps'] = list(cusps)
    out['houses'] = list(cusps)
    if out.get('ascendant') is None:
        out['ascendant'] = cusps[0]
    if out.get('midheaven') is None:
        out['midheaven'] = cusps[9]

    planets = out.get('planets')
    if isinstance(planets, dict):
        rows = [
            (str(name), payload)
            for name, payload in planets.items()
            if isinstance(payload, dict)
        ]
    elif isinstance(planets, list):
        rows = [
            (str(row.get('planet') or row.get('name') or ''), row)
            for row in planets
            if isinstance(row, dict)
        ]
    else:
        rows = []
    for name, row in rows:
        try:
            longitude = float(row.get('longitude'))
        except (TypeError, ValueError):
            continue
        derived_house = _synastry_house_for_longitude(longitude, cusps)
        if derived_house is None:
            continue
        previous_house = row.get('house')
        try:
            previous_value = int(previous_house) if previous_house is not None else None
        except (TypeError, ValueError):
            previous_value = None
        if previous_value != derived_house:
            changes.append({
                'planet': name,
                'stored_house': previous_house,
                'cusp_derived_house': derived_house,
                'resolution': 'frozen_cusp_set',
            })
        row['house'] = derived_house
    return out, changes


def _synastry_bundle_from_snap_id(snap_id: str, house_system_code: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    raw_snap = _snaps().get(snap_id)
    if not isinstance(raw_snap, dict):
        raise ValueError('Synastry snap not found')
    snap = _hydrate_snap_payload(raw_snap, infer_coordinates=False)
    if not snap:
        raise ValueError('Synastry snap not found')
    _require_confirmed_saved_snap_context(
        snap,
        feature_label='Synastry',
    )
    dashboard = snap.get('dashboard') if isinstance(snap.get('dashboard'), dict) else {}
    dt = snap.get('effective_datetime') or dashboard.get('timestamp')
    loc = snap.get('location') or dashboard.get('location')
    tz = snap.get('timezone') or dashboard.get('timezone')
    coords = _snap_coordinate_pair(snap, dashboard)
    calculation_context = (
        copy.deepcopy(snap.get('calculation_context'))
        if isinstance(snap.get('calculation_context'), dict)
        else {}
    )
    coordinate_provenance = dict(snap.get('coordinate_provenance') or {})
    saved_chart = _synastry_chart_snapshot_from_dashboard(dashboard)
    saved_chart.update(_synastry_chart_snapshot_from_chart_data(snap.get('chart_snapshot')))
    saved_chart, house_consistency_changes = _cohere_saved_synastry_chart(saved_chart)
    context_warnings: List[str] = []
    if calculation_context.get('review_required'):
        context_warnings.append(
            'This saved chart uses migrated legacy context that requires place/time review.'
        )
    if house_consistency_changes:
        context_warnings.append(
            'Stored planet-house labels were derived again from the frozen cusp set to keep the chart internally consistent.'
        )

    if _has_synastry_chart_snapshot(saved_chart):
        saved_house_system = str(
            saved_chart.get('house_system_code')
            or dashboard.get('house_system_code')
            or dashboard.get('house_system')
            or calculation_context.get('house_system_code')
            or ''
        ).strip().upper()
        requested_house_system = str(house_system_code or '').strip().upper()
        can_recast_house_system = bool(
            requested_house_system
            and requested_house_system != saved_house_system
            and coords is not None
            and coordinate_provenance.get('persisted_with_chart')
            and dt
            and loc
        )
        if can_recast_house_system:
            _require_confirmed_saved_snap_context(
                snap,
                feature_label='Synastry house-system recasting',
            )
            bundle = _compute_chart_bundle_for(
                dt,
                loc,
                tz or None,
                house_system_code=requested_house_system,
                latitude=coords[0],
                longitude=coords[1],
            )
            bundle.setdefault('meta', {})
            bundle['meta']['context_recast'] = {
                'reason': 'requested_house_system_differs_from_frozen_chart',
                'from_house_system_code': saved_house_system or None,
                'to_house_system_code': requested_house_system,
            }
        else:
            if requested_house_system and requested_house_system != saved_house_system:
                context_warnings.append(
                    'The requested house-system override was not applied because the frozen chart lacks confirmed chart-native coordinates.'
                )
            bundle = {
                'chart_result': {},
                'chart_data': saved_chart,
                'meta': {
                    'timestamp': dt,
                    'instant_utc': dt,
                    'location': loc,
                    'timezone': tz,
                    'latitude': (coords[0] if coords else None),
                    'longitude': (coords[1] if coords else None),
                },
                'raw_chart': None,
            }
    else:
        if not dt or not loc:
            raise ValueError('Synastry snap is missing datetime or location')
        _require_confirmed_saved_snap_context(
            snap,
            feature_label='Synastry recasting',
        )
        bundle = _compute_chart_bundle_for(
            dt,
            loc,
            tz or None,
            house_system_code=house_system_code,
            latitude=(coords[0] if coords else None),
            longitude=(coords[1] if coords else None),
        )
        bundle.setdefault('meta', {})
        if coords is None:
            coordinate_provenance = {
                'source': 'recomputed_from_saved_location',
                'persisted_with_chart': False,
                'inferred_at_read_time': True,
                'review_required': True,
            }
            context_warnings.append(
                'The legacy snap had no frozen chart or saved coordinates, so the entire chart was recomputed from its saved location.'
            )
    bundle.setdefault('meta', {})
    bundle['meta'].update({
        'timestamp': dt,
        'instant_utc': dt,
        'calculation_context': calculation_context,
        'coordinate_provenance': coordinate_provenance,
        'context_warnings': context_warnings,
        'house_consistency_changes': house_consistency_changes,
    })
    chart_meta = {
        'id': snap.get('id'),
        'label': snap.get('label') or 'Snapshot',
        'effective_datetime': dt,
        'local_datetime': snap.get('local_datetime'),
        'location': loc,
        'timezone': (bundle.get('meta') or {}).get('timezone'),
        'coordinate_provenance': coordinate_provenance,
        'calculation_context': calculation_context,
        'context_warnings': context_warnings,
        'profile_hint': snap.get('profile_hint') or (snap.get('summary') or {}).get('profile_hint'),
    }
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
    report['governance']['saved_chart_context'] = {
        'chart_a': {
            'review_required': bool(
                ((chart_a.get('calculation_context') or {}).get('review_required'))
            ),
            'warnings': chart_a.get('context_warnings') or [],
            'coordinate_provenance': chart_a.get('coordinate_provenance') or {},
        },
        'chart_b': {
            'review_required': bool(
                ((chart_b.get('calculation_context') or {}).get('review_required'))
            ),
            'warnings': chart_b.get('context_warnings') or [],
            'coordinate_provenance': chart_b.get('coordinate_provenance') or {},
        },
    }
    return _json_ok(report)


@astro_clock_bp.route('/traits/profile', methods=['GET'])
@_error_handler
def traits_profile():
    """Return a trait profile built from current chart metrics and house influences.

    Query params:
      special_degree: repeated tokens such as "25 Leo" to include in metrics
      summary_context: optional summary ranking context; supports public_figure_biography
    """
    with _astro_perf_span('route.traits_profile'):
        eng = _engine_instance()
        data, _active_settings = _data_for_optional_confirmed_snap(eng)
        with _astro_perf_span('route.traits_profile.compact_dashboard'):
            rt = _compact_dashboard(data)
            cd = _extract_chart_data_from_result(data.chart_result if isinstance(data.chart_result, dict) else {})
        try:
            special_degrees = _normalize_special_degree_tokens(request.args.getlist('special_degree'))
        except Exception:
            special_degrees = []
        summary_context = str(request.args.get('summary_context') or 'default').strip() or 'default'
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
                norm, norm_details = _build_planet_area_scores_from_house_influences(house_infl)
                if isinstance(metrics, dict):
                    metrics.setdefault('planet_area_scores', norm)
                    metrics.setdefault('planet_area_score_details', norm_details)
            except Exception:
                pass

        with _astro_perf_span('route.traits_profile.evaluate'):
            try:
                engine = _traits_engine_instance()
                profile = _evaluate_traits_profile(engine, metrics, summary_context)
            except Exception as exc:
                logger.exception("Trait profile evaluation failed: %s", exc)
                profile = {'summary': None, 'top_traits': [], 'traits': [], 'guidance': []}

        with _astro_perf_span('route.traits_profile.chart_snapshot'):
            try:
                dashboard_payload = _build_dashboard_payload(
                    eng,
                    data,
                    include_morin=True,
                    special_degrees=special_degrees,
                )
            except Exception as exc:
                logger.exception("Trait profile dashboard snapshot failed: %s", exc)
                dashboard_payload = None
            chart_snapshot = _build_traits_chart_snapshot(
                data,
                rt,
                cd,
                special_degrees,
                dashboard_payload=dashboard_payload,
            )

    return _json_ok({
        'summary': profile.get('summary'),
        'special_degrees': special_degrees,
        'sect': sect_info,
        'receptions': chart_snapshot.get('receptions') or {},
        'morin_patterns': chart_snapshot.get('morin_patterns') or {},
        'house_influences': house_infl,
        'top_traits': profile.get('top_traits') or [],
        'summary_traits': profile.get('summary_traits') or [],
        'top_traits_by_polarity': profile.get('top_traits_by_polarity') or {},
        'traits': profile.get('traits') or [],
        'guidance': profile.get('guidance') or [],
        'trait_enrichment_meta': profile.get('trait_enrichment_meta') or {},
        'summary_context': summary_context,
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
    target_dt, timestamp_error = _parse_transit_scan_datetime(ts, 'transit_datetime')
    if timestamp_error:
        return jsonify({'success': False, 'error': timestamp_error}), 400
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
    hits = _apply_transit_hit_filters(hits, flt_transiting, flt_natal, flt_aspects)
    hits = _sort_transit_hits_for_display(hits)
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
        rng, range_error = _parse_transit_range_hours(request.args.get('range_hours', '12'))
        if range_error:
            return jsonify({'success': False, 'error': range_error}), 400
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
    step, step_error = _parse_transit_scan_step(request.args.get('step_minutes', '60'))
    if step_error:
        return jsonify({'success': False, 'error': step_error}), 400
    start_dt, end_dt, _total_steps, bounds_error = _validate_transit_scan_request_bounds(start, end, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
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
    context_ranges, context_error = _parse_transit_context_ranges((
        ('pd', pd_start, pd_end),
        ('sa', sa_start, sa_end),
        ('prog', prog_start, prog_end),
    ))
    if context_error:
        return jsonify({'success': False, 'error': context_error}), 400

    # A/B toggle: ?sig_beta=0/1 to switch significance formula
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

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
    series = _filter_transit_series_to_context_ranges(series, context_ranges)
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
    step, step_error = _parse_transit_scan_step(request.args.get('step_minutes', '60'))
    if step_error:
        return jsonify({'success': False, 'error': step_error}), 400
    start_dt, end_dt, _total_steps, bounds_error = _validate_transit_scan_request_bounds(start, end, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
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
    context_ranges, context_error = _parse_transit_context_ranges((
        ('pd', pd_start, pd_end),
        ('sa', sa_start, sa_end),
        ('prog', prog_start, prog_end),
    ))
    if context_error:
        return jsonify({'success': False, 'error': context_error}), 400

    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

    observer_location = request.args.get('location') or natal_meta.get('location')
    observer_timezone = request.args.get('timezone') or natal_meta.get('timezone')

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

    series = _filter_transit_series_to_context_ranges(series, context_ranges)

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
        peaks = _build_predictor_group_peak_rows(series, grouped_predictions, limit=10)
    except Exception:
        peaks = []

    limit, limit_error = _parse_transit_limit(request.args.get('limit', '40'), default=40)
    if limit_error:
        return jsonify({'success': False, 'error': limit_error}), 400
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
    from transits_morin import _new_transit_registry_context  # type: ignore
    from transits_morin import _select_morin_transit_step_candidates  # type: ignore
    from transits_morin import compute_morin_transits_to_natal  # type: ignore
    import json as _json
    natal_cd, natal_meta = _natal_from_query(request.args)
    start = request.args.get('start')
    end = request.args.get('end')
    if not (start and end):
        return jsonify({'success': False, 'error': 'start/end required'}), 400
    step, step_error = _parse_transit_scan_step(request.args.get('step_minutes', '60'))
    if step_error:
        return jsonify({'success': False, 'error': step_error}), 400
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

    start_dt, end_dt, validated_total_steps, bounds_error = _validate_transit_scan_request_bounds(start, end, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
    context_ranges, context_error = _parse_transit_context_ranges((
        ('pd', pd_start, pd_end),
        ('sa', sa_start, sa_end),
        ('prog', prog_start, prog_end),
    ))
    if context_error:
        return jsonify({'success': False, 'error': context_error}), 400

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
        from datetime import timedelta as _td, timezone as _tz
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
        registry_context = _new_transit_registry_context()
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
            hits = _apply_transit_hit_filters(hits, flt_transiting, flt_natal, flt_aspects)
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
            # Enrich the complete active set once, matching the HTTP window scan.
            # Candidate limits affect presentation only; simultaneous-transit
            # analysis must see the same sky regardless of transport.
            enriched_hits = _retry_enrich_transit_hits(
                natal_cd,
                [dict(hit) for hit in hits],
                ts_iso,
                pd_windows=pd_windows,
                sig_beta=sig_beta,
                observer_location=natal_meta.get('location'),
                observer_timezone=natal_meta.get('timezone'),
                registry_context=registry_context,
                route_label='transits/window/stream',
            )
            top_n = 3
            prediction_n = max(top_n, _TRANSIT_WINDOW_PREDICTION_HITS_PER_TYPE)
            top_hits, prediction_hits = _select_morin_transit_step_candidates(
                enriched_hits,
                top_n_per_type=top_n,
                prediction_n_per_type=prediction_n,
            )
            top_planets = [h for h in top_hits if str(h.get('target_type')) == 'planet']
            top_points = [h for h in top_hits if str(h.get('target_type')) != 'planet']
            try:
                step_signif = sum(float(h.get('significance') or 0.0) for h in top_hits)
            except Exception:
                step_signif = sum(float(h.get('score') or 0.0) for h in top_hits)
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
                'tone': _step_tone(top_hits),
            }
            include_row = True
            if context_ranges:
                include_row = bool(
                    _filter_transit_series_to_context_ranges([row], context_ranges)
                )
            if include_row:
                row_predictions = _predictions_from_hits(prediction_hits, ts_iso)
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
    target_dt, timestamp_error = _parse_transit_scan_datetime(ts, 'transit_datetime')
    if timestamp_error:
        return jsonify({'success': False, 'error': timestamp_error}), 400
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
    hits = _apply_transit_hit_filters(hits, flt_transiting, flt_natal, flt_aspects)
    hits = _sort_transit_hits_for_display(hits)
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
        range_hours, range_error = _parse_transit_range_hours(request.args.get('range_hours', '12'))
        if range_error:
            return jsonify({'success': False, 'error': range_error}), 400
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
    step, step_error = _parse_transit_scan_step(request.args.get('step_minutes', '60'))
    if step_error:
        return jsonify({'success': False, 'error': step_error}), 400
    start_dt, end_dt, _total_steps, bounds_error = _validate_transit_scan_request_bounds(start, end, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
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
    context_ranges, context_error = _parse_transit_context_ranges((
        ('pd', pd_start, pd_end),
        ('sa', sa_start, sa_end),
        ('prog', prog_start, prog_end),
    ))
    if context_error:
        return jsonify({'success': False, 'error': context_error}), 400
    # A/B toggle via ?sig_beta=0/1
    sig_raw = request.args.get('sig_beta')
    sig_beta = None
    if sig_raw is not None:
        sig_beta = str(sig_raw).lower() in {'1','true','yes','new','beta'}

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
    series = _filter_transit_series_to_context_ranges(series, context_ranges)
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
        _swe = require_swisseph()
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


_FORENSIC_INTERPRETATION_METADATA = {
    'method': 'astrological_symbolic_rule_interpretation',
    'scientifically_validated_for_forensic_use': False,
    'is_statistical_probability': False,
    'intended_use': 'symbolic_research_only',
    'prohibited_inferences': [
        'identity',
        'physical_or_behavioral_profile',
        'investigative_guilt',
        'real_world_location',
        'survival_or_outcome_probability',
    ],
    'warning': (
        'Do not use this output as evidence or as the basis for identification, '
        'search deployment, accusations, or safety and outcome decisions.'
    ),
}


def _forensic_default_house_system_override() -> Optional[str]:
    """Return the forensic default only for an unsnapped, implicit request.

    Explicit query choices remain authoritative. Saved snaps retain their own
    confirmed house system unless the caller explicitly requests a recompute.
    """
    explicit = request.args.get('house_system_code') or request.args.get('house_system')
    if explicit or str(request.args.get('snap_id') or '').strip():
        return None
    from forensic.house_system import DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE

    return DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE


def _forensic_interpretation_metadata(
    active_settings: Any,
    *,
    default_applied: bool,
) -> Dict[str, Any]:
    from forensic.house_system import (
        DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
        FORENSIC_HOUSE_SYSTEM_LABELS,
        FORENSIC_HOUSE_SYSTEM_SELECTION_BASIS,
    )

    metadata = copy.deepcopy(_FORENSIC_INTERPRETATION_METADATA)
    explicit = request.args.get('house_system_code') or request.args.get('house_system')
    effective = str(getattr(active_settings, 'house_system_code', None) or '').strip().upper()
    if explicit:
        source = 'request_override'
    elif str(request.args.get('snap_id') or '').strip():
        source = 'saved_snap'
    elif default_applied:
        source = 'forensic_default'
    else:
        source = 'active_clock_context'
    metadata['house_system'] = {
        'default_code': DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE,
        'default_label': FORENSIC_HOUSE_SYSTEM_LABELS[DEFAULT_FORENSIC_HOUSE_SYSTEM_CODE],
        'effective_code': effective or None,
        'effective_label': FORENSIC_HOUSE_SYSTEM_LABELS.get(effective),
        'source': source,
        'development_selection': dict(FORENSIC_HOUSE_SYSTEM_SELECTION_BASIS),
    }
    return metadata


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
    survival_case_type = str(request.args.get('case_type') or 'general').strip().lower()
    if survival_case_type not in {'child', 'adult_female', 'general'}:
        return jsonify({'success': False, 'error': 'Invalid case_type'}), 400
    abd_requested = (request.args.get('abduction','0').lower() in {'1','true','yes'})
    parsed_abduction_origin = None
    parsed_corridor_deg = 6.0
    origin_str = request.args.get('origin') or ''
    if abd_requested and origin_str.strip():
        if ',' not in origin_str:
            return jsonify({'success': False, 'error': 'Invalid origin coordinates'}), 400
        try:
            a, b = origin_str.split(',', 1)
            parsed_abduction_origin = (float(a.strip()), float(b.strip()))
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid origin coordinates'}), 400
        if not (-90.0 <= parsed_abduction_origin[0] <= 90.0) or not (-180.0 <= parsed_abduction_origin[1] <= 180.0):
            return jsonify({'success': False, 'error': 'Invalid origin coordinates'}), 400
    if abd_requested:
        corridor_raw = request.args.get('corridor_deg')
        if corridor_raw is not None and str(corridor_raw).strip():
            try:
                parsed_corridor_deg = float(str(corridor_raw).strip())
            except Exception:
                return jsonify({'success': False, 'error': 'Invalid corridor_deg'}), 400
            if not math.isfinite(parsed_corridor_deg) or not (0 < parsed_corridor_deg <= 180):
                return jsonify({'success': False, 'error': 'Invalid corridor_deg'}), 400

    with _astro_perf_span('route.forensic.prepare_chart', mode=q_mode or None):
        eng = _engine_instance()
        forensic_house_override = _forensic_default_house_system_override()
        if forensic_house_override:
            data, _active_settings = _data_for_optional_confirmed_snap(
                eng,
                house_system_override=forensic_house_override,
            )
        else:
            data, _active_settings = _data_for_optional_confirmed_snap(eng)
        dash = _build_dashboard_payload(
            eng,
            data,
            include_morin=True,
            include_modern=True,
            extend_modern_chart_data=True,
        )

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
                        all_aspects.extend(a for a in top_aspects if isinstance(a, dict))
                if isinstance(cd, dict):
                    cd_aspects = cd.get('aspects')
                    if isinstance(cd_aspects, list):
                        all_aspects.extend(a for a in cd_aspects if isinstance(a, dict))
                precise_aspects = dash.get('planetary_aspects_precise')
                if isinstance(precise_aspects, list):
                    all_aspects.extend(a for a in precise_aspects if isinstance(a, dict))
                if all_aspects:
                    dash['all_aspects'] = _dedupe_aspect_rows(_normalize_aspect_rows_for_forensic(all_aspects))
            except Exception:
                pass

    # Feature extraction and rule evaluation
    from forensic.features import extract_features, compute_dominance
    from forensic.relationship_status import compute_relationship_status
    from forensic.secondary_factors import compute_secondary_factor_analysis
    from forensic.survivability import compute_survivability
    from forensic.axis_assessment import assess_axes
    from forensic.engine import load_knowledge, load_planetary_meanings, load_dictionary
    with _astro_perf_span('route.forensic.evaluate_knowledge'):
        knowledge_dir = os.path.join(os.path.dirname(__file__), 'forensic', 'knowledge')
        try:
            rules = load_knowledge(knowledge_dir)
        except Exception as exc:
            logger.exception("Forensic knowledge rules could not be loaded: %s", exc)
            return jsonify({
                'success': False,
                'error': 'forensic_rule_engine_unavailable',
                'detail': 'Forensic knowledge rules could not be loaded.',
            }), 500
        features = extract_features(dash)
        secondary_factors_arg = request.args.get('secondary_factors')
        secondary_factors_requested = True if secondary_factors_arg is None else str(secondary_factors_arg).strip().lower() in {'1', 'true', 'yes'}
        try:
            features['case_context'] = _infer_forensic_case_context(
                survival_case_type,
                dash if isinstance(dash, dict) else {},
                getattr(data, 'settings', None),
            )
        except Exception:
            pass
        try:
            from forensic.engine import evaluate
            findings = evaluate(features, rules)
        except Exception as exc:
            logger.exception("Forensic knowledge evaluation failed: %s", exc)
            return jsonify({
                'success': False,
                'error': 'forensic_rule_engine_unavailable',
                'detail': 'Forensic knowledge evaluation failed.',
            }), 500
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
    degree_special = _ld('degree_special.yaml')
    witness_accomplice = _ld('witness_accomplice.yaml')
    ic_sign_meanings = _ld('ic_sign_meanings.yaml')
    ic_ruler_house_meanings = _ld('ic_ruler_house_meanings.yaml')
    ic_planet_in_4th = _ld('ic_planet_in_4th.yaml')
    asc_ruler_house_meanings = _ld('asc_ruler_house_meanings.yaml')
    asc_ruler_placement = {}
    try:
        houses_payload = (features.get('houses') or {}) if isinstance(features, dict) else {}
        first_ruler = houses_payload.get('first_ruler')
        first_house = houses_payload.get('first_ruler_house')
        try:
            first_house_int = int(first_house) if first_house is not None else None
        except Exception:
            first_house_int = None
        meaning = asc_ruler_house_meanings.get(str(first_house_int)) if first_house_int is not None else {}
        meaning = meaning if isinstance(meaning, dict) else {}
        if first_ruler or first_house_int is not None:
            asc_ruler_placement = {
                'ruler': first_ruler,
                'house': first_house_int,
                'label': meaning.get('label') or (f'H{first_house_int}' if first_house_int is not None else ''),
                'summary': meaning.get('summary') or '',
                'cues': list(meaning.get('cues') or []) if isinstance(meaning.get('cues'), list) else [],
                'risk_tone': meaning.get('risk_tone') or '',
                'source': meaning.get('source') or '',
                'scoring_effect': 'descriptive_only',
            }
        features['asc_ruler_placement'] = asc_ruler_placement
    except Exception:
        asc_ruler_placement = {}

    # Extract light mediation hints from serialized chart
    def _extract_light_mediation(chart_obj: Dict[str, Any], dashboard_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        info = {
            'translation': False,
            'collection': False,
            'prohibition': False,
            'translator': None,
            'collector': None,
            'prohibitor': None,
            'denial_type': None,
            'target': None,
            'mode': None,
            'participants': [],
            'legs': [],
            'from_leg': None,
            'to_leg': None,
            'favorable': None,
            'challenge_reasons': [],
            'evidence': [],
        }
        def _add_participant(value):
            try:
                if value is None:
                    return
                if isinstance(value, str):
                    text = value.strip()
                    if text and text not in info['participants']:
                        info['participants'].append(text)
                    return
                if isinstance(value, dict):
                    for key in (
                        'planet',
                        'name',
                        'from',
                        'middle',
                        'to',
                        'target',
                        'translator',
                        'collector',
                        'prohibitor',
                        'frustrating',
                        'frustrated',
                        'swift_extreme',
                        'receiving_extreme',
                    ):
                        _add_participant(value.get(key))
                    _add_participant(value.get('participants'))
                    _add_participant(value.get('collected'))
                    return
                if isinstance(value, (list, tuple, set)):
                    for item in value:
                        _add_participant(item)
            except Exception:
                pass
        def _add_leg(value):
            try:
                if isinstance(value, dict):
                    if any(key in value for key in ('aspect', 'orb', 'phase', 'partile', 'complete_platic')):
                        leg = dict(value)
                        signature = (
                            str(leg.get('aspect') or '').lower(),
                            str(leg.get('orb') or ''),
                            str(leg.get('phase') or '').lower(),
                        )
                        existing = {
                            (
                                str(item.get('aspect') or '').lower(),
                                str(item.get('orb') or ''),
                                str(item.get('phase') or '').lower(),
                            )
                            for item in info['legs']
                            if isinstance(item, dict)
                        }
                        if signature not in existing:
                            info['legs'].append(leg)
                    return
                if isinstance(value, (list, tuple, set)):
                    for item in value:
                        _add_leg(item)
            except Exception:
                pass
        def _copy_quality_metadata(source):
            try:
                if not isinstance(source, dict):
                    return
                if info['favorable'] is None and 'favorable' in source:
                    info['favorable'] = source.get('favorable')
                for key in ('challenge_reasons', 'negative_reasons', 'challenges'):
                    raw = source.get(key)
                    if isinstance(raw, list):
                        for item in raw:
                            if item and item not in info['challenge_reasons']:
                                info['challenge_reasons'].append(item)
                    elif raw and raw not in info['challenge_reasons']:
                        info['challenge_reasons'].append(raw)
                for key in ('reception', 'reception_data'):
                    if key in source and key not in info:
                        info[key] = source.get(key)
            except Exception:
                pass
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
                        if kl == 'prohibitor' and v and not info['prohibitor']:
                            info['prohibitor'] = v if isinstance(v, str) else getattr(v,'value',None) or str(v)
                        if kl in {'participants', 'from', 'middle', 'to', 'target', 'collected'}:
                            _add_participant(v)
                        _walk(v)
                elif isinstance(o, list):
                    for it in o: _walk(it)
            _walk(chart_obj)
            patterns = (dashboard_obj or {}).get('morin_patterns') if isinstance(dashboard_obj, dict) else None
            if isinstance(patterns, dict):
                translations = patterns.get('translation') or []
                if isinstance(translations, list) and translations:
                    first_translation = next((item for item in translations if isinstance(item, dict)), None)
                    if first_translation:
                        info['translation'] = True
                        if not info['translator']:
                            info['translator'] = first_translation.get('middle') or first_translation.get('translator')
                        if isinstance(first_translation.get('from_leg'), dict):
                            info['from_leg'] = dict(first_translation.get('from_leg') or {})
                            _add_leg(info['from_leg'])
                        if isinstance(first_translation.get('to_leg'), dict):
                            info['to_leg'] = dict(first_translation.get('to_leg') or {})
                            _add_leg(info['to_leg'])
                        _add_leg(first_translation.get('legs'))
                        _copy_quality_metadata(first_translation)
                        _add_participant(first_translation.get('from'))
                        _add_participant(first_translation.get('middle'))
                        _add_participant(first_translation.get('to'))
                        info['evidence'].append('morin_patterns: translation')
                collections = patterns.get('collection') or []
                if isinstance(collections, list) and collections:
                    first_collection = next((item for item in collections if isinstance(item, dict)), None)
                    if first_collection:
                        info['collection'] = True
                        if not info['collector']:
                            info['collector'] = first_collection.get('collector')
                        if not info['mode']:
                            info['mode'] = first_collection.get('mode')
                        _add_leg(first_collection.get('legs'))
                        _copy_quality_metadata(first_collection)
                        _add_participant(first_collection.get('collector'))
                        _add_participant(first_collection.get('collected'))
                        info['evidence'].append('morin_patterns: collection')
                frustrations = patterns.get('frustration') or []
                if isinstance(frustrations, list) and frustrations:
                    first_frustration = next((item for item in frustrations if isinstance(item, dict)), None)
                    if first_frustration:
                        info['prohibition'] = True
                        info['denial_type'] = 'frustration'
                        info['favorable'] = False
                        if not info['prohibitor']:
                            info['prohibitor'] = first_frustration.get('frustrating')
                        if not info['target']:
                            info['target'] = first_frustration.get('target')
                        if 'frustration' not in info['challenge_reasons']:
                            info['challenge_reasons'].append('frustration')
                        _add_participant(first_frustration.get('frustrated'))
                        _add_participant(first_frustration.get('target'))
                        _add_participant(first_frustration.get('frustrating'))
                        info['evidence'].append('morin_patterns: frustration')
                preemptions = patterns.get('preemptive_transfer') or []
                if isinstance(preemptions, list) and preemptions:
                    first_preemption = next((item for item in preemptions if isinstance(item, dict)), None)
                    if first_preemption and not info['prohibition']:
                        info['prohibition'] = True
                        info['denial_type'] = 'preemptive_transfer'
                        info['favorable'] = False
                        if not info['prohibitor']:
                            info['prohibitor'] = first_preemption.get('swift_extreme')
                        if not info['target']:
                            info['target'] = first_preemption.get('receiving_extreme')
                        if 'preemptive_transfer' not in info['challenge_reasons']:
                            info['challenge_reasons'].append('preemptive_transfer')
                        _add_participant(first_preemption.get('swift_extreme'))
                        _add_participant(first_preemption.get('middle'))
                        _add_participant(first_preemption.get('receiving_extreme'))
                        info['evidence'].append('morin_patterns: preemptive_transfer')
        except Exception:
            pass
        return info

    light_mediation = _extract_light_mediation(chart if isinstance(chart, dict) else {}, dash if isinstance(dash, dict) else {})
    try:
        features['light_mediation'] = light_mediation
    except Exception:
        pass

    try:
        secondary_factor_analysis = compute_secondary_factor_analysis(features, degree_special)
        if isinstance(secondary_factor_analysis, dict):
            secondary_factor_analysis['enabled'] = bool(secondary_factors_requested)
    except Exception:
        secondary_factor_analysis = {
            'enabled': bool(secondary_factors_requested),
            'findings': [],
            'axis_hints': [],
            'relationship_score_delta': {},
            'survivability_delta': {'fatal_pressure': 0.0, 'recovery_support': 0.0, 'net_score': 0.0},
            'evidence': [],
        }
    try:
        features['secondary_factor_analysis'] = secondary_factor_analysis
    except Exception:
        pass

    def _rollup_categories(findings_list):
        try:
            out: Dict[str, int] = {}
            for f in findings_list:
                c = f.get('category') or 'General'
                out[c] = out.get(c, 0) + 1
            return out
        except Exception:
            return {}

    scoring_findings = [
        finding
        for finding in (findings or [])
        if isinstance(finding, dict) and finding.get('scoring_eligible', True) is not False
    ]
    scoring_cats = _rollup_categories(scoring_findings)
    display_findings = list(findings or [])
    axis_assessment = assess_axes(display_findings)

    # Keep asteroid/special-degree testimony as auxiliary analysis, not core
    # findings, unless a later benchmark proves axis-level benefit.
    try:
        cats: Dict[str, int] = {}
        for f in display_findings:
            c = f.get('category') or 'General'
            cats[c] = cats.get(c, 0) + 1
    except Exception:
        cats = {}

    try:
        survivability = compute_survivability(
            features,
            findings=scoring_findings,
            categories=scoring_cats,
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

    try:
        relationship_status = compute_relationship_status(
            features,
            findings=scoring_findings,
            categories=scoring_cats,
            receptions=receptions,
            light_mediation=light_mediation,
        )
    except Exception:
        relationship_status = {
            'primary_label': 'stranger_public',
            'labels': ['stranger_public'],
            'scores': {},
            'confidence': 'Low',
            'evidence': {},
            'light_mediation_component': {},
        }

    out = {
        'success': True,
        'analysis_metadata': _forensic_interpretation_metadata(
            _active_settings,
            default_applied=bool(forensic_house_override),
        ),
        'timestamp': dash.get('timestamp'),
        'location': dash.get('location'),
        'timezone_label': dash.get('timezone_label'),
        'moon': dash.get('moon'),
        'moon_timeline': dash.get('moon_timeline'),
        'categories': cats,
        'scoring_categories': scoring_cats,
        'findings': display_findings,
        'axis_assessment': axis_assessment,
        # Knowledge dictionaries and lookups
        'planetary_meanings': planetary_meanings,
        'house_meanings': house_meanings,
        'fixed_star_meanings': fixed_star_meanings,
        'aspect_meanings': aspect_meanings,
        'degree_special': degree_special,
        'witness_accomplice': witness_accomplice,
        'ic_sign_meanings': ic_sign_meanings,
        'ic_ruler_house_meanings': ic_ruler_house_meanings,
        'ic_planet_in_4th': ic_planet_in_4th,
        'asc_ruler_house_meanings': asc_ruler_house_meanings,
        'abduction_location': _ld('abduction_location.yaml'),
        # Derived
        'light_mediation': light_mediation,
        'secondary_factor_analysis': secondary_factor_analysis,
        'features': features,
        'dominance': dominance,
        'survivability': survivability,
        'relationship_status': relationship_status,
        'receptions': receptions,
        'relationship_star_hits': relationship_star_hits,
        'asc_ruler_placement': asc_ruler_placement,
    }

    # Optional abduction local-space mapping
    abd = abd_requested
    if abd:
        try:
            lat, lon = parsed_abduction_origin if parsed_abduction_origin else (None, None)
            origin_source = 'query_origin' if parsed_abduction_origin else None
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
                corridor = parsed_corridor_deg
                out['abduction_map'] = {
                    'origin': {'lat': lat, 'lon': lon},
                    'origin_source': origin_source,
                    'bearings': bearings,
                    'line_zones': bool(line_zones),
                    'corridor_deg': corridor,
                }
        except Exception as exc:
            out['abduction_map_error'] = str(exc) or 'Abduction map unavailable'

    from flask import jsonify as _j
    return _j(out)


@astro_clock_bp.route('/election/validate', methods=['GET'])
def election_validate():
    matter, matter_error = _parse_election_matter(request.args.get('matter'))
    if matter_error:
        return jsonify({'success': False, 'error': matter_error}), 400
    assert matter is not None
    marriage_algorithm = (request.args.get('marriage_algorithm') or 'alpha').strip().lower()
    business_algorithm = (request.args.get('business_algorithm') or 'alpha').strip().lower()
    reference_parity = request.args.get('reference_parity', '0').lower() in {'1', 'true', 'yes'}
    estate_direction = (request.args.get('estate_direction') or request.args.get('direction') or 'buy').strip().lower()
    lunar_fertility_consider_mode_raw = request.args.get('consider_mode') or 'phase_and_antiphase'
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
    estate_participant_snap_ids = [
        str(item).strip()
        for item in request.args.getlist('estate_participant_snap_id')
        if str(item).strip()
    ]
    estate_participant_snap_id = (
        estate_participant_snap_ids[0]
        if estate_participant_snap_ids
        else (unique_participant_snap_ids[0] if unique_participant_snap_ids else '')
    )

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
    if reference_parity:
        if not _election_reference_model(matter, marriage_algorithm, business_algorithm):
            return jsonify({
                'success': False,
                'error': 'reference_parity is available only for Marriage Beta, Business Beta, and Estate',
            }), 400
        step = 1
    _, limit_error = _parse_transit_limit(
        request.args.get('limit', '15'),
        default=15,
        max_value=200,
    )
    if limit_error:
        return jsonify({'success': False, 'error': limit_error}), 400

    if hour_start_val is not None and hour_end_val is not None and hour_start_val > hour_end_val:
        return jsonify({'success': False, 'error': 'hour_end must be after hour_start'}), 400

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
    if edt <= sdt:
        return jsonify({'success': False, 'error': 'End must be after start'}), 400
    if reference_parity:
        validated_total_steps, bounds_error = _validate_stream_scan_bounds(
            sdt,
            edt,
            step,
            max_steps=_ELECTION_REFERENCE_MAX_STEPS,
        )
    else:
        validated_total_steps, bounds_error = _validate_stream_scan_bounds(sdt, edt, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400

    # Gender parameter validation (informational only)
    if matter in {'conception', 'fertility'}:
        g_raw = (request.args.get('gender') or '').strip().lower()
        if g_raw and g_raw not in {'male', 'boy', 'masculine', 'female', 'girl', 'feminine'}:
            return jsonify({'success': False, 'error': 'gender must be male or female when provided'}), 400

    if matter == 'lunar_fertility':
        try:
            normalize_lunar_fertility_consider_mode(lunar_fertility_consider_mode_raw)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
        natal_snap = (request.args.get('natal_snap_id') or '').strip()
        natal_datetime = (request.args.get('natal_datetime') or '').strip()
        natal_location = (request.args.get('natal_location') or '').strip()
        if not natal_snap and not (natal_datetime and natal_location):
            return jsonify({'success': False, 'error': 'Lunar Fertility Windows requires a natal saved chart'}), 400
        house = request.args.get('house_system_code') or None
        if natal_snap:
            try:
                _bundle_from_snap_id(
                    natal_snap,
                    house_system_code=house,
                    missing_error='Natal snap not found',
                )
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400

    if matter == 'marriage':
        if marriage_algorithm not in {'alpha', 'beta'}:
            return jsonify({'success': False, 'error': 'marriage_algorithm must be alpha or beta'}), 400
        if marriage_algorithm == 'beta':
            marriage_beta_display_mode = (
                request.args.get('marriage_beta_display_mode') or 'total'
            ).strip().lower()
            marriage_beta_scope = (
                request.args.get('marriage_beta_scope') or 'all'
            ).strip().lower()
            if marriage_beta_display_mode not in _MARRIAGE_BETA_EXTRACTION_MODES:
                return jsonify({
                    'success': False,
                    'error': 'marriage_beta_display_mode must be total or detail',
                }), 400
            if marriage_beta_scope not in _MARRIAGE_BETA_EXTRACTION_SCOPES:
                return jsonify({
                    'success': False,
                    'error': 'marriage_beta_scope must be all, current, or selected',
                }), 400
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
            business_beta_display_mode = (
                request.args.get('business_beta_display_mode') or 'total'
            ).strip().lower()
            business_beta_scope = (
                request.args.get('business_beta_scope') or 'all'
            ).strip().lower()
            if business_beta_display_mode not in _BUSINESS_BETA_EXTRACTION_MODES:
                return jsonify({
                    'success': False,
                    'error': 'business_beta_display_mode must be total or detail',
                }), 400
            if business_beta_scope not in _BUSINESS_BETA_EXTRACTION_SCOPES:
                return jsonify({
                    'success': False,
                    'error': 'business_beta_scope must be all, current, or selected',
                }), 400
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
    if matter == 'estate':
        if estate_direction not in {'buy', 'sell'}:
            return jsonify({'success': False, 'error': 'estate_direction must be buy or sell'}), 400
        estate_display_mode = (
            request.args.get('estate_display_mode') or 'total'
        ).strip().lower()
        estate_scope = (
            request.args.get('estate_scope') or 'all'
        ).strip().lower()
        if estate_display_mode not in _ESTATE_EXTRACTION_MODES:
            return jsonify({
                'success': False,
                'error': 'estate_display_mode must be total or detail',
            }), 400
        if estate_scope not in _ESTATE_EXTRACTION_SCOPES:
            return jsonify({
                'success': False,
                'error': 'estate_scope must be all, current, or selected',
            }), 400
        if not estate_participant_snap_id:
            return jsonify({'success': False, 'error': 'Estate election requires estate_participant_snap_id'}), 400
        house = request.args.get('house_system_code') or None
        try:
            _bundle_from_snap_id(
                estate_participant_snap_id,
                house_system_code=house,
                missing_error='Estate participant snap not found',
            )
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

    return jsonify({
        'success': True,
        'matter': matter,
        'step_minutes': step,
        'reference_parity': reference_parity,
        'total_steps': validated_total_steps,
    })


@astro_clock_bp.route('/election/suggest/stream', methods=['GET'])
def election_suggest_stream():
    """Stream election suggestions over a time window via SSE.

    Computes a score at each step and emits a final result with top items.
    """
    matter, matter_error = _parse_election_matter(request.args.get('matter'))
    if matter_error:
        return jsonify({'success': False, 'error': matter_error}), 400
    assert matter is not None
    marriage_algorithm = (request.args.get('marriage_algorithm') or 'alpha').strip().lower()
    business_algorithm = (request.args.get('business_algorithm') or 'alpha').strip().lower()
    reference_parity = request.args.get('reference_parity', '0').lower() in {'1', 'true', 'yes'}
    estate_direction = (request.args.get('estate_direction') or request.args.get('direction') or 'buy').strip().lower()
    lunar_fertility_consider_mode_raw = request.args.get('consider_mode') or 'phase_and_antiphase'
    start = request.args.get('start')
    end = request.args.get('end')
    location = request.args.get('location')
    timezone_name = request.args.get('timezone')
    house_system_code = request.args.get('house_system_code') or None
    try:
        step = int(request.args.get('step_minutes', '60') or 60)
    except Exception:
        return jsonify({'success': False, 'error': 'step_minutes must be an integer >= 1'}), 400
    limit, limit_error = _parse_transit_limit(
        request.args.get('limit', '15'),
        default=15,
        max_value=200,
    )
    if limit_error:
        return jsonify({'success': False, 'error': limit_error}), 400
    assert limit is not None
    if reference_parity:
        if not _election_reference_model(matter, marriage_algorithm, business_algorithm):
            return jsonify({
                'success': False,
                'error': 'reference_parity is available only for Marriage Beta, Business Beta, and Estate',
            }), 400
        step = 1
    include_series = (request.args.get('include_series', '1').lower() in {'1', 'true', 'yes'})
    natal_snap = request.args.get('natal_snap_id')
    natal_datetime = request.args.get('natal_datetime')
    natal_location = request.args.get('natal_location')
    participant_a_snap_id = (request.args.get('participant_a_snap_id') or '').strip()
    participant_b_snap_id = (request.args.get('participant_b_snap_id') or '').strip()
    participant_snap_ids = [str(item).strip() for item in request.args.getlist('participant_snap_id') if str(item).strip()]
    unique_participant_snap_ids = list(dict.fromkeys(participant_snap_ids))
    estate_participant_snap_ids = [
        str(item).strip()
        for item in request.args.getlist('estate_participant_snap_id')
        if str(item).strip()
    ]
    estate_participant_snap_id = (
        estate_participant_snap_ids[0]
        if estate_participant_snap_ids
        else (unique_participant_snap_ids[0] if unique_participant_snap_ids else '')
    )
    marriage_beta_display_mode = (request.args.get('marriage_beta_display_mode') or 'total').strip().lower()
    marriage_beta_scope = (request.args.get('marriage_beta_scope') or 'all').strip().lower()
    marriage_beta_current_line_id = (request.args.get('marriage_beta_current_line_id') or '').strip()
    marriage_beta_selected_line_ids = [
        str(item).strip()
        for item in request.args.getlist('marriage_beta_selected_line_id')
        if str(item).strip()
    ]
    marriage_beta_level_percent = _parse_marriage_beta_level_percent(
        request.args.get(
            'marriage_beta_level_percent',
            str(_MARRIAGE_BETA_EXTRACTION_LEVEL_DEFAULT),
        )
    )
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
    estate_display_mode = (request.args.get('estate_display_mode') or 'total').strip().lower()
    estate_scope = (request.args.get('estate_scope') or 'all').strip().lower()
    estate_current_line_id = (request.args.get('estate_current_line_id') or '').strip()
    estate_selected_line_ids = [
        str(item).strip()
        for item in request.args.getlist('estate_selected_line_id')
        if str(item).strip()
    ]
    estate_level_percent = _parse_estate_level_percent(
        request.args.get('estate_level_percent', str(_ESTATE_EXTRACTION_LEVEL_DEFAULT))
    )
    lunar_fertility_level_percent = _parse_lunar_fertility_level_percent(
        request.args.get('level_percent', str(_LUNAR_FERTILITY_LEVEL_DEFAULT))
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
    if matter == 'lunar_fertility':
        try:
            lunar_fertility_consider_mode = normalize_lunar_fertility_consider_mode(lunar_fertility_consider_mode_raw)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
    else:
        lunar_fertility_consider_mode = 'phase_and_antiphase'
    if matter == 'marriage' and marriage_algorithm not in {'alpha', 'beta'}:
        return jsonify({'success': False, 'error': 'marriage_algorithm must be alpha or beta'}), 400
    if matter == 'marriage' and marriage_algorithm == 'beta':
        if marriage_beta_display_mode not in _MARRIAGE_BETA_EXTRACTION_MODES:
            return jsonify({'success': False, 'error': 'marriage_beta_display_mode must be total or detail'}), 400
        if marriage_beta_scope not in _MARRIAGE_BETA_EXTRACTION_SCOPES:
            return jsonify({'success': False, 'error': 'marriage_beta_scope must be all, current, or selected'}), 400
    if matter == 'business' and business_algorithm not in {'alpha', 'beta'}:
        return jsonify({'success': False, 'error': 'business_algorithm must be alpha or beta'}), 400
    if matter == 'business' and business_algorithm == 'beta':
        if business_beta_display_mode not in _BUSINESS_BETA_EXTRACTION_MODES:
            return jsonify({'success': False, 'error': 'business_beta_display_mode must be total or detail'}), 400
        if business_beta_scope not in _BUSINESS_BETA_EXTRACTION_SCOPES:
            return jsonify({'success': False, 'error': 'business_beta_scope must be all, current, or selected'}), 400
    if matter == 'estate':
        if estate_direction not in {'buy', 'sell'}:
            return jsonify({'success': False, 'error': 'estate_direction must be buy or sell'}), 400
        if not estate_participant_snap_id:
            return jsonify({'success': False, 'error': 'Estate election requires estate_participant_snap_id'}), 400
        if estate_display_mode not in _ESTATE_EXTRACTION_MODES:
            return jsonify({'success': False, 'error': 'estate_display_mode must be total or detail'}), 400
        if estate_scope not in _ESTATE_EXTRACTION_SCOPES:
            return jsonify({'success': False, 'error': 'estate_scope must be all, current, or selected'}), 400
    if weekday_mode and weekday_mode not in {'all', 'custom', 'none'}:
        return jsonify({'success': False, 'error': 'weekday_mode must be all, custom, or none'}), 400
    if hour_start_error:
        return jsonify({'success': False, 'error': hour_start_error}), 400
    if hour_end_error:
        return jsonify({'success': False, 'error': hour_end_error}), 400
    if hour_start is not None and hour_end is not None and hour_start > hour_end:
        return jsonify({'success': False, 'error': 'hour_end must be after hour_start'}), 400
    if matter == 'lunar_fertility' and not (natal_snap or (natal_datetime and natal_location)):
        return jsonify({'success': False, 'error': 'Lunar Fertility Windows requires a natal saved chart'}), 400

    # Choose model scorer
    from election import (
        score_marriage_election, score_marriage_beta_election, score_surgery_election, score_contract_election,
        score_business_election, score_business_beta_election, score_estate_election, score_journey_election, score_haircut_election,
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
        if matter == 'estate':
            return score_estate_election(cd, natal_hits=natal_hits, options=opts)
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

    # Natal context (optional) for enhancements. Presence of any natal-scoped
    # field is an explicit request, including incomplete direct input.
    natal_cd = None
    natal_context_requested = any(
        request.args.get(field_name) is not None
        for field_name in (
            'natal_snap_id',
            'natal_datetime',
            'natal_location',
            'natal_timezone',
        )
    )
    participant_mode_active = (
        (matter == 'marriage' and marriage_algorithm == 'beta')
        or (matter == 'business' and business_algorithm == 'beta')
        or matter == 'estate'
    )
    if not participant_mode_active and natal_context_requested:
        try:
            natal_cd, _nm = _natal_from_query(request.args)
        except Exception as exc:
            return jsonify({
                'success': False,
                'error': str(exc) or 'Natal context could not be loaded safely',
            }), 400
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
    marriage_participants: List[Dict[str, Any]] = []
    business_participants: List[Dict[str, Any]] = []
    estate_participant: Optional[Dict[str, Any]] = None
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
            saved_snaps = _snaps()
            for idx, (snap_id, bundle, fallback_label) in enumerate(
                (
                    (participant_a_snap_id, participant_a_bundle, 'Participant A'),
                    (participant_b_snap_id, participant_b_bundle, 'Participant B'),
                ),
                start=1,
            ):
                snap = saved_snaps.get(snap_id) or {}
                label = (
                    str(snap.get('label') or '').strip()
                    or str(snap.get('location') or '').strip()
                    or fallback_label
                )
                marriage_participants.append({
                    'snap_id': snap_id,
                    'label': label,
                    'chart_data': bundle.get('chart_data') or {},
                    'meta': bundle.get('meta') or {},
                    **_election_precision_from_saved_bundle(bundle),
                })
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
                precision = _election_precision_from_saved_bundle(bundle)
                business_participants.append(
                    {
                        'snap_id': snap_id,
                        'label': label,
                        'chart_data': bundle.get('chart_data') or {},
                        'meta': bundle.get('meta') or {},
                        **precision,
                    }
                )
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
    if matter == 'estate':
        if not estate_participant_snap_id:
            return jsonify({'success': False, 'error': 'Estate election requires estate_participant_snap_id'}), 400
        try:
            snap = _snaps().get(estate_participant_snap_id) or {}
            bundle = _bundle_from_snap_id(
                estate_participant_snap_id,
                house_system_code=house_system_code,
                missing_error='Estate participant snap not found',
            )
            bundle['chart_data'] = _extend_chart_data_for_marriage_beta(
                bundle.get('chart_data') or {},
                bundle.get('meta') or {},
                include_moon_day=False,
            )
            label = (
                str(snap.get('label') or '').strip()
                or str(snap.get('location') or '').strip()
                or 'Estate participant'
            )
            precision = _election_precision_from_saved_bundle(bundle)
            estate_participant = {
                'snap_id': estate_participant_snap_id,
                'label': label,
                'chart_data': bundle.get('chart_data') or {},
                'meta': bundle.get('meta') or {},
                **precision,
            }
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
    if reference_parity:
        validated_total_steps, bounds_error = _validate_stream_scan_bounds(
            sdt,
            edt,
            step,
            max_steps=_ELECTION_REFERENCE_MAX_STEPS,
        )
    else:
        validated_total_steps, bounds_error = _validate_stream_scan_bounds(sdt, edt, step)
    if bounds_error:
        return jsonify({'success': False, 'error': bounds_error}), 400
    default_series_limit = _STREAM_MAX_STEPS if matter == 'lunar_fertility' else _STREAM_BUFFER_ROWS
    try:
        series_limit = int(request.args.get('series_limit', str(default_series_limit)) or default_series_limit)
    except Exception:
        series_limit = default_series_limit
    series_limit = max(25, min(series_limit, _STREAM_MAX_STEPS))
    top_buffer_limit = max(50, limit * 8)

    # Weekday map (Python Mon=0..Sun=6); input uses sun..sat.
    weekday_filter_active = False
    weekday_idx: Set[int] = set()
    if weekday_mode == 'none':
        weekday_filter_active = True
    elif weekday_mode == 'custom' or weekdays_raw:
        m = {'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
        weekday_idx = set(m.get(w, None) for w in weekdays_raw)
        weekday_idx.discard(None)
        weekday_filter_active = True

    def _timestamp_passes_day_hour_filters(timestamp_value: Any) -> bool:
        try:
            raw_ts = str(timestamp_value or '').strip()
            if not raw_ts:
                return True
            ts = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            t_local = ts.astimezone(scan_zone)
            minute_of_day = (t_local.hour * 60) + t_local.minute
            if weekday_filter_active and (not weekday_idx or t_local.weekday() not in weekday_idx):
                return False
            if (hour_start is not None) and (minute_of_day < hour_start):
                return False
            if (hour_end is not None) and (minute_of_day > hour_end):
                return False
        except Exception:
            return True
        return True

    def _row_passes_day_hour_filters(row: Dict[str, Any]) -> bool:
        if not isinstance(row, dict):
            return False
        return _timestamp_passes_day_hour_filters(row.get('timestamp') or row.get('timestamp_local'))

    if matter == 'lunar_fertility':
        if natal_cd is None:
            return jsonify({'success': False, 'error': 'Lunar Fertility Windows requires a natal saved chart'}), 400
        try:
            lunar_result = scan_lunar_fertility_windows(
                natal_cd,
                sdt,
                edt,
                timezone_name=tz,
                consider_mode=lunar_fertility_consider_mode,
                level_percent=lunar_fertility_level_percent,
                ephemeris=_lunar_fertility_ephemeris_adapter(),
            )
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
        except Exception:
            logger.exception('Failed to compute Lunar Fertility Windows')
            return jsonify({'success': False, 'error': 'Lunar Fertility Windows calculation is unavailable'}), 503

        all_series_source_rows = [
            row for row in list(lunar_result.get('series') or [])
            if isinstance(row, dict)
        ]
        series_source_rows = [
            dict(row) for row in all_series_source_rows
            if _row_passes_day_hour_filters(row)
        ]
        passing_rows = [
            row for row in series_source_rows
            if bool(row.get('passes_level')) or float(row.get('score') or 0.0) >= lunar_fertility_level_percent
        ]
        # Level is a graph/inspection guide. Exported periods include every
        # nonzero favorable hour, as in the recovered SkyLiner workflow.
        grouped = group_lunar_fertility_periods(series_source_rows, timezone_name=tz)
        period_rows = grouped.get('rows') or []
        period_by_key = {
            (row.get('timestamp'), row.get('phase_kind'), row.get('sex_label')): row.get('period_id')
            for row in period_rows
            if isinstance(row, dict)
        }
        rebuilt_series_source_rows: List[Dict[str, Any]] = []
        for row in series_source_rows:
            row_copy = dict(row)
            row_copy.pop('period_id', None)
            period_id = period_by_key.get((row_copy.get('timestamp'), row_copy.get('phase_kind'), row_copy.get('sex_label')))
            if period_id:
                row_copy['period_id'] = period_id
            rebuilt_series_source_rows.append(row_copy)
        series_source_rows = rebuilt_series_source_rows
        top = sorted(
            series_source_rows,
            key=lambda row: float(row.get('score') or 0.0),
            reverse=True,
        )[:limit]
        series_rows: List[Dict[str, Any]] = []
        series_dropped = 0
        if include_series:
            series_rows = _reduce_series_rows(
                series_source_rows,
                series_limit,
                pinned_timestamps=[str(row.get('timestamp') or '') for row in top],
            )
            series_dropped = max(0, len(series_source_rows) - len(series_rows))
        model_stats = dict(lunar_result.get('stats') or {})
        payload = {
            'top': top,
            'matter': 'lunar_fertility',
            'location': location,
            'timezone': tz,
            'consider_mode': lunar_result.get('consider_mode') or lunar_fertility_consider_mode,
            'level_percent': lunar_result.get('level_percent', lunar_fertility_level_percent),
            'level_behavior': 'visual_inspection_guide',
            'periods': grouped.get('periods') or [],
            'anchors': lunar_result.get('anchors') or [],
            'signature': lunar_result.get('signature') or {},
            'stats': {
                **model_stats,
                'attempted': int(model_stats.get('attempted') or 0),
                'favorable_total': len(series_source_rows),
                'unfiltered_favorable_total': len(all_series_source_rows),
                'passing_total': len(passing_rows),
                'period_count': len(grouped.get('periods') or []),
                'kept_total': len(series_source_rows),
                'failed': 0,
                'series_total': len(series_source_rows) if include_series else 0,
                'series_retained': len(series_rows) if include_series else 0,
                'series_dropped': series_dropped if include_series else 0,
            },
            'model_metadata': _election_model_metadata(
                'lunar_fertility',
                natal_context_applied=True,
                reference_parity=False,
                step_minutes=60,
            ),
            'medical_disclaimer': (
                'Traditional Moon-sign polarity and fertility timing only; '
                'not medical advice, an ovulation estimate, or fetal-sex prediction.'
            ),
        }
        if include_series:
            payload['series'] = series_rows

        def _generate_lunar():
            yield f"data: {json.dumps({'type':'progress','progress':1.0})}\n\n"
            yield f"data: {json.dumps({'type':'done','data':payload})}\n\n"

        headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
        return Response(stream_with_context(_generate_lunar()), headers=headers)

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

    try:
        min_mercury_direct_days_requested = max(
            0,
            int(request.args.get('min_mercury_direct_days', '0') or 0),
        )
    except Exception:
        min_mercury_direct_days_requested = 0
    mercury_direct_stations: List[datetime] = []
    if matter == 'contract' and min_mercury_direct_days_requested:
        mercury_direct_stations = _mercury_direct_station_times(sdt, edt)

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
            ht = request.args.get('haircut_type')
            if ht: opts['haircut_type'] = ht
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
        if matter == 'estate':
            opts['estate_direction'] = estate_direction
            opts['include_traditional_timing'] = True
            opts.pop('include_fixed_stars', None)
            opts.pop('include_lunation_screen', None)
        if participant_a_cd is not None:
            opts['participant_a_cd'] = participant_a_cd
            opts['participant_a_meta'] = (participant_a_bundle or {}).get('meta') or {}
            opts['participant_a_snap_id'] = participant_a_snap_id
            if marriage_participants:
                opts['participant_a_label'] = marriage_participants[0].get('label')
                opts['participant_a_precision'] = {
                    key: marriage_participants[0].get(key)
                    for key in ('precision_class', 'precision_safe', 'precision_source')
                }
        if participant_b_cd is not None:
            opts['participant_b_cd'] = participant_b_cd
            opts['participant_b_meta'] = (participant_b_bundle or {}).get('meta') or {}
            opts['participant_b_snap_id'] = participant_b_snap_id
            if len(marriage_participants) >= 2:
                opts['participant_b_label'] = marriage_participants[1].get('label')
                opts['participant_b_precision'] = {
                    key: marriage_participants[1].get(key)
                    for key in ('precision_class', 'precision_safe', 'precision_source')
                }
        if business_participants:
            opts['business_participants'] = business_participants
            opts['participant_snap_ids'] = [item.get('snap_id') for item in business_participants if item.get('snap_id')]
        if estate_participant:
            opts['estate_participant'] = estate_participant
            opts['estate_participant_snap_id'] = estate_participant.get('snap_id')
        # SR/LR context if requested
        if include_sr_lr and natal_cd is not None:
            if sr_windows:
                opts['sr_windows'] = sr_windows
            if lr_list:
                opts['lr_list'] = lr_list
        if tz:
            opts['timezone'] = tz
        return opts

    def _generate():
        attempted = 0
        kept_total = 0
        failure_reasons: Counter = Counter()
        failure_samples: List[Dict[str, str]] = []
        all_series_rows: List[Dict[str, Any]] = []
        top_candidates: List[Dict[str, Any]] = []
        series_dropped = 0
        t = sdt
        total_steps = validated_total_steps or 1
        progress_stride = max(1, math.ceil(total_steps / 500))
        scan_step_index = 0

        def _progress_event(current_t: datetime, current_index: int) -> Optional[str]:
            if current_index % progress_stride and current_t < edt:
                return None
            try:
                progress_value = min(
                    1.0,
                    max(
                        0.0,
                        (
                            (current_t - sdt).total_seconds()
                            / ((edt - sdt).total_seconds() or 1)
                        ),
                    ),
                )
            except Exception:
                progress_value = 0.0
            return (
                f"data: {json.dumps({'type': 'progress', 'progress': progress_value})}\n\n"
            )

        # Prepare planetary hours calculator if traditional timing requested
        ph_calc = None
        coords = None
        try:
            if (
                include_sr_lr
                or request.args.get('include_traditional_timing','').lower() in {'1','true','yes'}
                or (matter == 'business' and business_algorithm == 'beta')
                or matter == 'estate'
            ):
                coords = _ensure_coords_for_location(location)
                if coords:
                    lat, lon = coords
                    ph_calc = _ph_instance(lat, lon)
        except Exception:
            ph_calc = None
        while t <= edt:
            # Filter by weekday/hour if provided (use local time at tz)
            skip_for_filter = False
            try:
                t_local = t.astimezone(scan_zone)
                minute_of_day = (t_local.hour * 60) + t_local.minute
                if weekday_filter_active and (not weekday_idx or t_local.weekday() not in weekday_idx):
                    skip_for_filter = True
                elif (hour_start is not None) and (minute_of_day < hour_start):
                    skip_for_filter = True
                elif (hour_end is not None) and (minute_of_day > hour_end):
                    skip_for_filter = True
            except Exception:
                pass
            if skip_for_filter:
                progress_event = _progress_event(t, scan_step_index)
                if progress_event:
                    yield progress_event
                t = t + step_td
                scan_step_index += 1
                continue
            attempted += 1
            # Compute chart at t for location
            try:
                cd, meta = _compute_chart_for(t.isoformat(), location, tz, house_system_code)
                if (
                    (matter == 'marriage' and marriage_algorithm == 'beta')
                    or (matter == 'business' and business_algorithm == 'beta')
                    or matter == 'estate'
                ):
                    cd = _extend_chart_data_for_marriage_beta(
                        cd,
                        meta,
                        include_moon_day=True,
                    )
                opts = _model_options()
                opts['current_timestamp'] = t
                opts['event_meta'] = meta
                if matter == 'contract' and min_mercury_direct_days_requested:
                    prior_stations = [
                        station for station in mercury_direct_stations
                        if station <= t.astimezone(timezone.utc)
                    ]
                    if prior_stations:
                        latest_station = max(prior_stations)
                        opts['mercury_direct_station_age_days'] = (
                            t.astimezone(timezone.utc) - latest_station
                        ).total_seconds() / 86400.0
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
                if (
                    include_series
                    or (matter == 'marriage' and marriage_algorithm == 'beta')
                    or (matter == 'business' and business_algorithm == 'beta')
                    or matter == 'estate'
                ):
                    all_series_rows.append(row)
            except Exception as exc:
                reason = type(exc).__name__
                failure_reasons[reason] += 1
                if len(failure_samples) < 3:
                    failure_samples.append({
                        'timestamp': t.isoformat(),
                        'type': reason,
                        'message': str(exc)[:240] or reason,
                    })
                    logger.warning(
                        'Election step failed for %s at %s: %s',
                        matter,
                        t.isoformat(),
                        exc,
                        exc_info=True,
                    )
            progress_event = _progress_event(t, scan_step_index)
            if progress_event:
                yield progress_event
            t = t + step_td
            scan_step_index += 1
        extraction_payload: Optional[Dict[str, Any]] = None
        series_source_rows = list(all_series_rows)
        if matter == 'marriage' and marriage_algorithm == 'beta':
            extraction_payload = _extract_marriage_beta_periods(
                series_source_rows,
                step_td=step_td,
                display_mode=marriage_beta_display_mode,
                scope=marriage_beta_scope,
                level_percent=marriage_beta_level_percent,
                current_line_id=marriage_beta_current_line_id or None,
                selected_line_ids=marriage_beta_selected_line_ids,
            )
            series_source_rows = list(extraction_payload.get('rows') or [])
            top = list(extraction_payload.get('top_rows') or [])[:limit]
        elif matter == 'business' and business_algorithm == 'beta':
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
        elif matter == 'estate':
            extraction_payload = _extract_estate_periods(
                series_source_rows,
                step_td=step_td,
                display_mode=estate_display_mode,
                scope=estate_scope,
                level_percent=estate_level_percent,
                current_line_id=estate_current_line_id or None,
                selected_line_ids=estate_selected_line_ids,
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
                'failure_reasons': dict(sorted(failure_reasons.items())),
                'failure_samples': failure_samples,
                'series_total': len(series_source_rows) if include_series else 0,
                'series_retained': len(series_rows) if include_series else 0,
                'series_dropped': series_dropped if include_series else 0,
            },
        }
        payload['model_metadata'] = _election_model_metadata(
            matter,
            marriage_algorithm=marriage_algorithm,
            business_algorithm=business_algorithm,
            natal_context_applied=bool(
                natal_cd is not None
                or marriage_participants
                or business_participants
                or estate_participant
            ),
            reference_parity=reference_parity,
            step_minutes=step,
        )
        if include_series:
            payload['series'] = series_rows
        if matter == 'marriage':
            payload['marriage_algorithm'] = marriage_algorithm
            if marriage_algorithm == 'beta':
                payload['participants'] = {
                    'participant_a_snap_id': participant_a_snap_id,
                    'participant_b_snap_id': participant_b_snap_id,
                    'items': [
                        {
                            'snap_id': item.get('snap_id'),
                            'label': item.get('label'),
                            'precision_class': item.get('precision_class'),
                            'precision_safe': item.get('precision_safe'),
                            'precision_source': item.get('precision_source'),
                        }
                        for item in marriage_participants
                    ],
                    'precision_note': (
                        'House and cusp rules are active only for participants with safe birth-time precision.'
                    ),
                }
                if extraction_payload is not None:
                    payload['marriage_beta_extraction'] = {
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
                    }
                    payload['marriage_beta_periods'] = extraction_payload.get('periods') or []
        if matter == 'business':
            payload['business_algorithm'] = business_algorithm
            if business_algorithm == 'beta':
                certified_assumption = bool(business_participants) and all(
                    item.get('precision_class') == 'certified'
                    and item.get('precision_safe') is True
                    for item in business_participants
                )
                payload['participants'] = {
                    'participant_snap_ids': [item.get('snap_id') for item in business_participants if item.get('snap_id')],
                    'items': [
                        {
                            'snap_id': item.get('snap_id'),
                            'label': item.get('label'),
                            'precision_class': item.get('precision_class'),
                            'precision_safe': item.get('precision_safe'),
                            'precision_source': item.get('precision_source'),
                        }
                        for item in business_participants
                    ],
                    'certified_assumption': certified_assumption,
                    'precision_note': (
                        'All selected founder-owner charts have certified birth-time quality.'
                        if certified_assumption
                        else 'Uncertified or unresolved participant charts are precision-gated; unsafe Ascendant-based fit is withheld.'
                    ),
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
                        'certified_assumption': certified_assumption,
                    }
                    payload['business_beta_periods'] = extraction_payload.get('periods') or []
        if matter == 'estate':
            payload['estate_direction'] = estate_direction
            certified_assumption = bool(
                estate_participant
                and estate_participant.get('precision_class') == 'certified'
                and estate_participant.get('precision_safe') is True
            )
            payload['participants'] = {
                'estate_participant_snap_id': estate_participant_snap_id,
                'items': [
                    {
                        'snap_id': estate_participant.get('snap_id'),
                        'label': estate_participant.get('label'),
                        'precision_class': estate_participant.get('precision_class'),
                        'precision_safe': estate_participant.get('precision_safe'),
                        'precision_source': estate_participant.get('precision_source'),
                    }
                ] if estate_participant else [],
                'certified_assumption': certified_assumption,
                'precision_note': (
                    'The selected estate participant has certified birth-time quality.'
                    if certified_assumption
                    else 'Uncertified or unresolved participant charts are precision-gated; unsafe Ascendant-based fit is withheld.'
                ),
            }
            if extraction_payload is not None:
                payload['estate_extraction'] = {
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
                    'certified_assumption': certified_assumption,
                }
                payload['estate_periods'] = extraction_payload.get('periods') or []
        yield f"data: {json.dumps({'type':'done','data':payload})}\n\n"

    headers = {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    return Response(stream_with_context(_generate()), headers=headers)


# ---------- Research Mode (Dev-only Lotto analysis) ----------

def _research_session_is_terminal(session: Optional[Dict[str, Any]]) -> bool:
    if not session:
        return False
    return bool(
        session.get('ready')
        or session.get('failed')
        or (session.get('aborted') and not session.get('running'))
    )


def _prune_research_sessions_locked(now: Optional[float] = None) -> None:
    _prune_terminal_sessions_locked(
        _research_sessions,
        is_terminal=_research_session_is_terminal,
        max_sessions=_RESEARCH_SESSION_MAX,
        ttl_seconds=_RESEARCH_SESSION_TTL_SECONDS,
        now=now,
    )


def _update_research_session(session_id: str, **updates: Any) -> None:
    with _research_lock:
        now = perf_counter()
        _prune_research_sessions_locked(now)
        session = _research_sessions.get(session_id)
        if session is None:
            session = {'session_id': session_id, 'created_at': now}
            _research_sessions[session_id] = session
        session.update(updates)
        session['updated_at'] = now


def _research_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _research_lock:
        _prune_research_sessions_locked()
        session = _research_sessions.get(session_id) or {}
        serializable = {
            key: value
            for key, value in session.items()
            if key != 'thread'
        }
    return copy.deepcopy(serializable)


def _research_progress_payload(session_id: str) -> Dict[str, Any]:
    sess = _research_session_snapshot(session_id)
    done = int(sess.get('done') or 0)
    total = int(sess.get('total') or 0)
    ready = bool(sess.get('ready'))
    failed = bool(sess.get('failed'))
    terminal = ready or failed or bool(sess.get('aborted') and not sess.get('running'))
    percent = 1.0 if terminal else (float(done) / float(total) if total else 0.0)
    payload = {
        'session_id': session_id,
        'ready': ready,
        'failed': failed,
        'running': bool(sess.get('running')),
        'done': done,
        'total': total,
        'percent': max(0.0, min(1.0, percent)),
        'stage': str(sess.get('stage') or ('ready' if ready else 'pending')),
        'runtime': _background_runtime_payload(
            'research_compile',
            session_max=_RESEARCH_SESSION_MAX,
            session_ttl_seconds=_RESEARCH_SESSION_TTL_SECONDS,
        ),
    }
    if sess.get('workers') is not None:
        payload['workers'] = sess.get('workers')
    if sess.get('source'):
        payload['source'] = sess.get('source')
    if sess.get('error'):
        payload['error'] = sess.get('error')
    if sess.get('aborted'):
        payload['aborted'] = True
    if sess.get('abort_requested'):
        payload['abort_requested'] = True
    return payload


def get_background_runtime_metrics() -> Dict[str, Any]:
    """Return bounded-worker and process-local session metrics for app health."""
    return {
        'session_persistence': 'process_memory',
        'restart_volatile': True,
        'executor': _background_executor.snapshot(),
        'limits': {
            'astrocartography_atlas_search': {
                'session_max': _ATLAS_SEARCH_SESSION_MAX,
                'terminal_session_ttl_seconds': _ATLAS_SEARCH_SESSION_TTL_SECONDS,
            },
            'weather_scan': {
                'session_max': _WEATHER_SCAN_SESSION_MAX,
                'terminal_session_ttl_seconds': _WEATHER_SCAN_SESSION_TTL_SECONDS,
            },
            'mundane_scan': {
                'session_max': _MUNDANE_SCAN_SESSION_MAX,
                'terminal_session_ttl_seconds': _MUNDANE_SCAN_SESSION_TTL_SECONDS,
            },
            'research_compile': {
                'session_max': _RESEARCH_SESSION_MAX,
                'terminal_session_ttl_seconds': _RESEARCH_SESSION_TTL_SECONDS,
            },
        },
        'sessions': {
            'astrocartography_atlas_search': _session_store_metrics(
                _atlas_search_sessions,
                _atlas_search_lock,
                prune_locked=_prune_atlas_search_sessions_locked,
                is_terminal=_atlas_search_session_is_terminal,
            ),
            'weather_scan': _session_store_metrics(
                _weather_scan_sessions,
                _weather_scan_lock,
                prune_locked=_prune_weather_scan_sessions_locked,
                is_terminal=_weather_scan_session_is_terminal,
            ),
            'mundane_scan': _session_store_metrics(
                _mundane_scan_sessions,
                _mundane_scan_lock,
                prune_locked=_prune_mundane_scan_sessions_locked,
                is_terminal=_mundane_scan_session_is_terminal,
            ),
            'research_compile': _session_store_metrics(
                _research_sessions,
                _research_lock,
                prune_locked=_prune_research_sessions_locked,
                is_terminal=_research_session_is_terminal,
            ),
        },
    }


@astro_clock_bp.route('/runtime/background', methods=['GET'])
@_error_handler
def background_runtime_status():
    return _json_ok(get_background_runtime_metrics())


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


def _research_lab_chart_snapshot(
    row: Dict[str, Any],
    *,
    evaluator_families: Optional[List[str]],
    house_system_code: Optional[str],
    sex_code: Optional[str],
) -> Dict[str, Any]:
    lat = row.get('latitude')
    lon = row.get('longitude')
    bundle = _compute_chart_bundle_for(
        row.get('datetime'),
        row.get('location'),
        row.get('timezone'),
        house_system_code=house_system_code,
        latitude=lat,
        longitude=lon,
    )
    chart_data = bundle.get('chart_data') or {}
    meta = bundle.get('meta') or {}
    timestamp_iso = meta.get('timestamp') or row.get('datetime')
    if isinstance(chart_data, dict):
        chart_data = _extend_chart_data_for_points(chart_data, timestamp_iso)
        chart_data = _with_points_exact_geometry(chart_data, bundle.get('raw_chart'))
    else:
        chart_data = {}

    enrichments: Dict[str, Any] = {}
    try:
        arabic_parts = compute_arabic_parts(chart_data)
        if isinstance(arabic_parts, dict):
            chart_data['arabic_parts'] = arabic_parts
            enrichments['arabic_parts'] = arabic_parts
    except Exception:
        enrichments['arabic_parts'] = {}

    try:
        metrics = compute_metrics(chart_data, timestamp_iso, special_degrees=None)
        if isinstance(metrics, dict):
            try:
                finals = _compute_final_dispositors(metrics.get('planet_signs') or {})
                if finals:
                    metrics['final_dispositor'] = finals
            except Exception:
                pass
            enrichments['metrics'] = metrics
    except Exception:
        enrichments['metrics'] = {}

    try:
        fixed_star_hits = compute_fixed_star_hits(chart_data, orb_deg=1.0, check_planets=['Sun', 'Moon'], include_cusps=True)
        enrichments['fixed_star_hits'] = fixed_star_hits if isinstance(fixed_star_hits, list) else []
    except Exception:
        enrichments['fixed_star_hits'] = []

    try:
        asteroids_payload = compute_asteroid_positions(chart_data, timestamp_iso)
        enrichments['asteroids'] = asteroids_payload if isinstance(asteroids_payload, dict) else {}
    except Exception:
        enrichments['asteroids'] = {}

    try:
        points_payload = compute_symbolic_points_payload(
            chart_data,
            timestamp_iso=timestamp_iso,
            sex_code=sex_code,
            latitude=lat if lat is not None else meta.get('latitude'),
            longitude=lon if lon is not None else meta.get('longitude'),
            house_system=house_system_code,
        )
        enrichments['points_payload'] = points_payload if isinstance(points_payload, dict) else {}
    except Exception:
        enrichments['points_payload'] = {}

    try:
        almutens = compute_chart_almutens(chart_data)
        enrichments['almutens'] = almutens if isinstance(almutens, dict) else {}
    except Exception:
        enrichments['almutens'] = {}

    return {
        'row': row,
        'chart_data': chart_data,
        'meta': meta,
        'enrichments': enrichments,
        'evaluator_families': evaluator_families or [],
    }


@astro_clock_bp.route('/research/evaluators', methods=['GET'])
@_error_handler
def research_evaluators():
    return _json_ok({'families': list_evaluator_catalog()})


def _bounded_research_int(value, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = int(default)
    return max(minimum, min(number, maximum))


@astro_clock_bp.route('/research/analyze', methods=['POST'])
@_error_handler
def research_analyze_chart_set():
    body = request.get_json(force=True, silent=True) or {}
    raw_rows = body.get('charts') or body.get('rows') or []
    if not isinstance(raw_rows, list) or not raw_rows:
        return jsonify({'success': False, 'error': 'At least one chart row is required.'}), 400

    target_rows = normalize_chart_rows(raw_rows)
    invalid_rows = [row for row in target_rows if not row.get('valid')]
    valid_rows = [row for row in target_rows if row.get('valid')]
    if not valid_rows:
        return jsonify({'success': False, 'error': 'No valid chart rows were provided.', 'invalid_rows': invalid_rows}), 400

    families = body.get('evaluator_families') or body.get('families') or None
    if families is not None and not isinstance(families, list):
        families = None
    feature_scopes = body.get('feature_scopes')
    if feature_scopes is not None and not isinstance(feature_scopes, list):
        feature_scopes = None
    control_opts = body.get('control') if isinstance(body.get('control'), dict) else {}
    per_chart = _bounded_research_int(
        control_opts.get('per_chart') or body.get('controls_per_chart') or 20,
        20,
        minimum=1,
        maximum=100,
    )
    seed = control_opts.get('seed') or body.get('seed') or 'vox-stella-research'
    year_window = _bounded_research_int(
        control_opts.get('year_window') or body.get('year_window') or 3,
        3,
        minimum=0,
        maximum=50,
    )
    house_system_code = body.get('house_system_code') or body.get('houseSystem') or body.get('house_system') or 'P'
    sex_code = body.get('sex_code')
    min_occurrence = _bounded_research_int(body.get('min_occurrence') or 1, 1, minimum=1, maximum=1000)

    control_rows = generate_matched_control_rows(valid_rows, per_chart=per_chart, seed=seed, year_window=year_window)
    target_snapshots = [
        _research_lab_chart_snapshot(
            row,
            evaluator_families=families,
            house_system_code=house_system_code,
            sex_code=sex_code,
        )
        for row in valid_rows
    ]
    control_snapshots = [
        _research_lab_chart_snapshot(
            row,
            evaluator_families=families,
            house_system_code=house_system_code,
            sex_code=sex_code,
        )
        for row in control_rows
    ]

    stats = analyze_research_snapshots(
        target_snapshots,
        control_snapshots,
        evaluator_families=families,
        feature_scopes=feature_scopes,
        min_occurrence=min_occurrence,
    )
    run_manifest = {
        'run_id': build_run_id({
            'charts': [row.get('name') for row in valid_rows],
            'families': families,
            'feature_scopes': feature_scopes,
            'control_seed': seed,
            'per_chart': per_chart,
            'year_window': year_window,
            'house_system_code': house_system_code,
        }),
        'target_count': len(valid_rows),
        'generated_control_count': len(control_rows),
        'control_strategy': 'matched_generated',
        'control_seed': str(seed),
        'controls_per_chart': per_chart,
        'control_year_window': year_window,
        'house_system_code': house_system_code,
        'feature_scope_count': stats.get('feature_scope_count', 0),
        'invalid_rows': invalid_rows,
    }
    return _json_ok({
        'manifest': run_manifest,
        'charts': valid_rows,
        'comparison_charts': control_rows[:50],
        'statistics': stats,
        'signals': stats.get('signals') or [],
    })


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
    """Compute genuine classical final dispositors for research filters."""
    return compute_classical_final_dispositors(planet_signs or {})


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

    # The deterministic session id also de-duplicates concurrent requests,
    # including forced refreshes while an older on-disk cache still exists.
    existing = _research_session_snapshot(session_id)
    if existing and not _research_session_is_terminal(existing):
        return session_id, _research_progress_payload(session_id)

    csv_path = _safe_research_path(path)
    cache_dir = _ensure_research_cache_dir()
    cache_path = cache_dir / f"{session_id}.json"

    if cache_path.exists() and not force:
        rows = _load_cached_rows(cache_path)
        initialized = _initialize_background_session(
            _research_sessions,
            _research_lock,
            session_id,
            {
                'ready': True,
                'failed': False,
                'running': False,
                'done': len(rows),
                'total': len(rows),
                'percent': 1.0,
                'workers': 0,
                'stage': 'ready',
                'source': 'cache',
                'cache_path': str(cache_path),
            },
            is_terminal=_research_session_is_terminal,
            max_sessions=_RESEARCH_SESSION_MAX,
            ttl_seconds=_RESEARCH_SESSION_TTL_SECONDS,
        )
        if not initialized:
            raise _BackgroundCapacityError('Research session capacity is full')
        return session_id, _research_progress_payload(session_id)

    total_rows = _count_csv_rows(csv_path)
    initialized = _initialize_background_session(
        _research_sessions,
        _research_lock,
        session_id,
        {
            'ready': False,
            'failed': False,
            'running': False,
            'done': 0,
            'total': total_rows,
            'aborted': False,
            'abort_requested': False,
            'workers': 1,
            'stage': 'queued',
            'source': 'compiled',
            'cache_path': str(cache_path),
        },
        is_terminal=_research_session_is_terminal,
        max_sessions=_RESEARCH_SESSION_MAX,
        ttl_seconds=_RESEARCH_SESSION_TTL_SECONDS,
    )
    if not initialized:
        raise _BackgroundCapacityError('Research session capacity is full')

    def _compile_worker():
        eng = AstroClockEngine()
        t_obj = _parse_time_str(time_str)
        tz_name = tz_hint or _research_default_tz
        coords = _ensure_coords_for_location(location)
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
                        if sess.get('abort_requested'):
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
                    _update_research_session(
                        session_id,
                        done=len(results),
                        total=total_rows,
                    )
        except Exception as e:
            _update_research_session(
                session_id,
                failed=True,
                error=str(e),
                stage='failed',
            )
        finally:
            session = _research_session_snapshot(session_id)
            aborted = bool(session.get('abort_requested'))
            cache_error = None
            if not aborted and not session.get('failed'):
                try:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(
                        json.dumps({'rows': results}, ensure_ascii=False),
                        encoding='utf-8',
                    )
                except Exception as exc:
                    cache_error = str(exc)

            if aborted:
                _update_research_session(
                    session_id,
                    ready=False,
                    failed=False,
                    running=False,
                    aborted=True,
                    abort_requested=False,
                    workers=0,
                    stage='aborted',
                    done=len(results),
                )
            elif cache_error or session.get('failed'):
                _update_research_session(
                    session_id,
                    ready=False,
                    failed=True,
                    running=False,
                    workers=0,
                    stage='failed',
                    error=cache_error or session.get('error') or 'Research compile failed',
                    done=len(results),
                )
            else:
                _update_research_session(
                    session_id,
                    ready=True,
                    failed=False,
                    running=False,
                    workers=0,
                    stage='ready',
                    source=session.get('source') or 'compiled',
                    done=len(results),
                    total=len(results) or session.get('total') or total_rows,
                )

    def _worker():
        _update_research_session(
            session_id,
            running=True,
            workers=1,
            stage='running',
        )
        try:
            _compile_worker()
        except Exception as exc:
            logger.exception("Research compile session failed before processing: %s", session_id)
            _update_research_session(
                session_id,
                ready=False,
                failed=True,
                running=False,
                workers=0,
                stage='failed',
                error=str(exc),
            )

    if not _submit_background_job(f"research-compile-{session_id[:8]}", _worker):
        _update_research_session(
            session_id,
            ready=False,
            failed=True,
            running=False,
            workers=0,
            stage='failed',
            error='Background capacity is full; retry later',
        )
        raise _BackgroundCapacityError('Research background capacity is full')
    return session_id, _research_progress_payload(session_id)


@astro_clock_bp.route('/research/lotto/compile/start', methods=['POST'])
@_error_handler
def research_compile_start():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    force = bool(body.get('force'))
    try:
        session_id, progress = _start_research_compile(body, force=force)
    except _BackgroundCapacityError:
        return _background_busy_response('Research compile')
    return _json_ok({'session_id': session_id, 'progress': progress, 'cached': progress.get('ready') and progress.get('source') == 'cache'})


@astro_clock_bp.route('/research/lotto/compile', methods=['POST'])
@_error_handler
def research_compile():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    body = request.get_json(force=True, silent=True) or {}
    try:
        session_id, progress = _start_research_compile(body, force=bool(body.get('force')))
    except _BackgroundCapacityError:
        return _background_busy_response('Research compile')
    return _json_ok({'session_id': session_id, 'progress': progress})


@astro_clock_bp.route('/research/lotto/progress', methods=['GET'])
@_error_handler
def research_progress():
    if not _research_mode_enabled():
        return jsonify({'success': False, 'error': 'Research mode is disabled'}), 403
    sid = request.args.get('session_id') or request.args.get('sid')
    if not sid:
        return jsonify({'success': False, 'error': 'session_id required'}), 400
    if not _research_session_snapshot(str(sid)):
        return _missing_volatile_session_response('Research compile')
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
        sess = _research_sessions.get(sid)
        if sess is None:
            return _missing_volatile_session_response('Research compile')
        if not _research_session_is_terminal(sess):
            sess['abort_requested'] = True
            sess['stage'] = 'cancelling'
            sess['updated_at'] = perf_counter()
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
