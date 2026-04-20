# -*- coding: utf-8 -*-
"""
Caching helpers for Solar and Lunar Revolution charts.

The Morin workflow evaluates revolutions repeatedly while scanning transit
windows.  Building each chart through the engine (~300ms) quickly adds up, so
we maintain a small LRU cache keyed by (kind, timestamp, location, natal
signature, house system).  Each cache entry stores:

    - The computed revolution ``chart_data`` (as produced by HoraryEngine)
    - House influence aggregates so we can expose dominant domains
    - Determinations for the revolution chart
    - Similarity / concordance metrics against the natal chart

This module is intentionally dependency-light; callers pass in the natal chart
snapshot plus the desired return timestamp and we do the rest.
"""

from __future__ import annotations

import copy
import json
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

try:  # Optional at import time inside packaged CLI builds
    from horary_engine.engine import HoraryEngine  # type: ignore
except Exception:  # pragma: no cover
    HoraryEngine = None  # type: ignore

try:
    from house_influence import compute_house_influences  # type: ignore
except Exception:  # pragma: no cover
    compute_house_influences = None  # type: ignore

try:
    from context_layers import (  # type: ignore
        compute_sr_similarity,
        compute_sr_enhanced_markers,
        compute_sr_ruler_condition,
        score_lr_concordance,
    )
except Exception:  # pragma: no cover
    compute_sr_similarity = None  # type: ignore
    compute_sr_enhanced_markers = None  # type: ignore
    compute_sr_ruler_condition = None  # type: ignore
    score_lr_concordance = None  # type: ignore

from determinations import compute_determinations

_MAX_CACHE_ENTRIES = 24
_CACHE: "OrderedDict[Tuple[str, ...], Dict[str, Any]]" = OrderedDict()

_HOUSE_DOMAIN_MAP = {
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
    12: 'hidden',
}


def _normalize_key(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _natal_signature(natal_cd: Dict[str, Any]) -> str:
    if not isinstance(natal_cd, dict):
        return 'natal:unknown'
    for key in ('cache_signature', 'snap_id', 'id', 'uuid'):
        token = natal_cd.get(key)
        if token:
            return f"natal:{token}"
    ts = natal_cd.get('timestamp') or natal_cd.get('datetime') or ''
    loc = ''
    try:
        tz_meta = natal_cd.get('timezone_info') or {}
        loc = tz_meta.get('location_name') or natal_cd.get('location_name') or ''
    except Exception:
        loc = ''
    basis = {'timestamp': ts, 'location': loc}
    return f"natal:{_normalize_key(basis)}"


def _cache_get(key: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    try:
        value = _CACHE[key]
    except KeyError:
        return None
    _CACHE.move_to_end(key)
    return copy.deepcopy(value)


def _cache_set(key: Tuple[str, ...], value: Dict[str, Any]) -> None:
    _CACHE[key] = copy.deepcopy(value)
    _CACHE.move_to_end(key)
    while len(_CACHE) > _MAX_CACHE_ENTRIES:
        _CACHE.popitem(last=False)


def _dominant_domains(house_influence: Optional[Dict[str, Any]], limit: int = 3) -> Tuple[str, ...]:
    if not isinstance(house_influence, dict):
        return ()
    domains: Dict[str, float] = {}
    for row in (house_influence.get('houses') or []):
        try:
            house_num = int(row.get('house'))
            domain = _HOUSE_DOMAIN_MAP.get(house_num)
            if not domain:
                continue
            val = 0.0
            for inf in (row.get('influences') or []):
                val += abs(float(inf.get('value') or 0.0))
            domains[domain] = domains.get(domain, 0.0) + val
        except Exception:
            continue
    sorted_items = sorted(domains.items(), key=lambda item: -item[1])
    return tuple(item[0] for item in sorted_items[:limit])


def _summarize_determinations(det_payload: Dict[str, Any], limit: int = 6) -> Tuple[Dict[str, Any], ...]:
    dets = []
    try:
        for det in (det_payload.get('determinations') or [])[:limit]:
            planet = det.get('planet')
            nature = (det.get('nature') or {}).get('primary')
            areas = []
            for area in det.get('areas') or []:
                label = area.get('area')
                if label:
                    areas.append(label)
                if len(areas) >= 3:
                    break
            dets.append({
                'planet': planet,
                'nature': nature,
                'areas': areas,
            })
    except Exception:
        return ()
    return tuple(dets)


def _push_signal(bucket: list[str], seen: set[str], label: Optional[str], limit: int = 4) -> None:
    text = str(label or '').strip()
    if not text:
        return
    key = text.lower()
    if key in seen:
        return
    if len(bucket) >= limit:
        return
    seen.add(key)
    bucket.append(text)


def _humanize_similarity_tag(kind: str, tag: str) -> Optional[str]:
    text = str(tag or '').strip()
    if not text:
        return None
    lower = text.lower()
    if kind == 'solar':
        if lower == 'asc same sign':
            return 'Ascendant returns to natal sign'
        if lower == 'mc same sign':
            return 'MC returns to natal sign'
        if lower == 'ruler angular':
            return 'Year ruler angular'
        if lower == 'ruler succedent':
            return 'Year ruler succedent'
        if lower == 'ruler cadent':
            return 'Year ruler cadent'
        if lower == 'ruler dignified':
            return 'Year ruler dignified'
        if lower == 'ruler combust':
            return 'Year ruler combust'
        if lower == 'ruler under beams':
            return 'Year ruler under beams'
        if lower == 'ruler cazimi':
            return 'Year ruler cazimi'
        if lower == 'ruler benefic':
            return 'Year ruler benefic'
        if lower == 'ruler malefic':
            return 'Year ruler malefic'
        if text.endswith(' same sign'):
            return f"{text[:-10]} returns to natal sign"
        if text.endswith(' same house'):
            return f"{text[:-11]} repeats natal house"
        if text.endswith(' returns to place'):
            return f"{text[:-17]} on natal degree"
        if text.endswith(' returns by Tri'):
            return f"{text[:-15]} trines natal degree"
        if text.endswith(' returns by Sex'):
            return f"{text[:-15]} sextiles natal degree"
        if text.endswith(' returns by Sq'):
            return f"{text[:-14]} squares natal degree"
        if text.endswith(' returns by Opp'):
            return f"{text[:-15]} opposes natal degree"
    if kind == 'lunar':
        if lower == 'lr asc~natal asc':
            return 'Lunar Asc aligns with natal Asc'
        if lower == 'lr asc same sr sign':
            return 'Lunar Asc matches solar-return sign'
        if lower == 'lr in pd window':
            return 'Lunar return falls in active direction window'
        if text.endswith(' LR~Natal place'):
            return f"{text[:-14]} on natal degree in lunar return"
        if text.endswith(' LR~Natal aspect'):
            return f"{text[:-15]} aspects natal degree in lunar return"
    return text


def _summarize_sr_markers(natal_cd: Dict[str, Any], sr_cd: Dict[str, Any]) -> Tuple[str, ...]:
    if not compute_sr_enhanced_markers:
        return ()
    try:
        markers = compute_sr_enhanced_markers(natal_cd or {}, sr_cd or {}, orb_deg=3.0) or {}
    except Exception:
        return ()
    bucket: list[str] = []
    seen: set[str] = set()
    for raw in (markers.get('angle_tags') or [])[:2]:
        label = str(raw or '').strip()
        if label.startswith('SR '):
            label = label[3:]
        label = label.replace(' near Natal ', ' on natal ')
        label = label.replace(' square Natal ', ' squares natal ')
        label = label.replace(' trine Natal ', ' trines natal ')
        _push_signal(bucket, seen, label)
    aspects = list(markers.get('aspects') or [])
    aspects.sort(key=lambda item: float(item.get('orb') or 99.0))
    for item in aspects:
        if len(bucket) >= 4:
            break
        p1 = str(item.get('p1') or '')
        p2 = str(item.get('p2') or '')
        if not p1.startswith('SR '):
            continue
        if not (p2 in {'Natal Asc', 'Natal MC'} or p1 in {'SR Sun', 'SR Moon'}):
            continue
        left = p1[3:]
        right = p2.replace('Natal ', 'natal ')
        aspect = str(item.get('aspect') or '').strip().lower()
        if not (left and right and aspect):
            continue
        _push_signal(bucket, seen, f'{left} {aspect}s {right}')
    return tuple(bucket)


def _support_signals(
    kind: str,
    natal_cd: Dict[str, Any],
    chart_data: Dict[str, Any],
    similarity: Dict[str, Any],
) -> Tuple[str, ...]:
    bucket: list[str] = []
    seen: set[str] = set()
    if kind == 'solar' and compute_sr_ruler_condition:
        try:
            ruler_info = compute_sr_ruler_condition(chart_data or {}) or {}
        except Exception:
            ruler_info = {}
        for raw in (ruler_info.get('tags') or []):
            _push_signal(bucket, seen, _humanize_similarity_tag(kind, str(raw)))
        for label in _summarize_sr_markers(natal_cd or {}, chart_data or {}):
            _push_signal(bucket, seen, label)
    for raw in (similarity.get('tags') or []):
        _push_signal(bucket, seen, _humanize_similarity_tag(kind, str(raw)))
    return tuple(bucket)


def get_revolution_context(
    kind: str,
    dt: Optional[datetime],
    *,
    natal_chart: Dict[str, Any],
    location: Optional[str],
    timezone_label: Optional[str],
    house_system_code: Optional[str] = None,
    sr_chart: Optional[Dict[str, Any]] = None,
    pd_windows: Optional[Iterable[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Return cached revolution context for ``kind`` ('solar' | 'lunar')."""
    if kind not in {'solar', 'lunar'}:
        raise ValueError(f"Unsupported revolution kind: {kind!r}")
    if dt is None or HoraryEngine is None:
        return None
    loc = location or 'Greenwich, UK'
    tz = timezone_label or 'UTC'
    dt_iso = dt.replace(tzinfo=dt.tzinfo or datetime.utcfromtimestamp(0).tzinfo).isoformat()
    key = (
        kind,
        dt_iso,
        loc,
        tz,
        house_system_code or '',
        _natal_signature(natal_chart),
    )
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        eng = HoraryEngine()
    except Exception:
        return None

    try:
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        settings = {
            'location': loc,
            'use_current_time': False,
            'date': date_str,
            'time': time_str,
            'timezone': tz,
            'manual_houses': None,
            'house_system_code': house_system_code,
            'ignore_radicality': True,
            'ignore_void_moon': True,
            # Revolutions are diagnostic; suppress horary-only warnings.
            'ignore_combustion': True,
            'ignore_saturn_7th': True,
            'exaltation_confidence_boost': 0.0,
        }
        judged = eng.judge('Revolution Chart', settings)
    except Exception:
        return None

    chart_data = judged.get('chart_data') if isinstance(judged, dict) else {}
    if isinstance(chart_data, str):
        try:
            chart_data = json.loads(chart_data)
        except Exception:
            chart_data = {}
    house_influence = {}
    if compute_house_influences:
        try:
            house_influence = compute_house_influences(chart_data or {}, {})
        except Exception:
            house_influence = {}
    determinations = {}
    try:
        determinations = compute_determinations(chart_data or {}, include_modern=False)
    except Exception:
        determinations = {}

    similarity: Dict[str, Any] = {}
    if kind == 'solar' and compute_sr_similarity:
        try:
            sim = compute_sr_similarity(natal_chart or {}, chart_data or {}) or {}
            raw_score = float(sim.get('score') or 0.0)
            norm = max(0.0, min(1.0, raw_score / 10.0))
            similarity = {
                'score': raw_score,
                'normalized': norm,
                'level': sim.get('level'),
                'tags': sim.get('tags') or [],
            }
        except Exception:
            similarity = {}
    elif kind == 'lunar' and score_lr_concordance:
        try:
            pd_list = list(pd_windows or [])
        except Exception:
            pd_list = []
        try:
            score, tags = score_lr_concordance(
                natal_chart or {},
                sr_chart or {},
                chart_data or {},
                pd_list,
            ) if sr_chart is not None else (0, [])
            raw_score = float(score)
            norm = max(0.0, min(1.0, raw_score / 10.0))
            similarity = {
                'score': raw_score,
                'normalized': norm,
                'tags': tags,
            }
        except Exception:
            similarity = {}

    context = {
        'kind': kind,
        'timestamp': dt_iso,
        'location': loc,
        'timezone': tz,
        'chart_data': chart_data or {},
        'house_influence': house_influence or {},
        'determinations': determinations or {},
        'domains': _dominant_domains(house_influence),
        'determination_summary': _summarize_determinations(determinations or {}),
        'similarity': similarity,
        'support_signals': _support_signals(kind, natal_chart or {}, chart_data or {}, similarity or {}),
    }
    _cache_set(key, context)
    return copy.deepcopy(context)


__all__ = ['get_revolution_context']
