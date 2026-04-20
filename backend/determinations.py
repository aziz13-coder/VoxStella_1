# -*- coding: utf-8 -*-
"""
Determinations (Spec Step 1)

Build explicit Determination objects from natal chart_data, aligning with the
spec's structure: natural signification, house position, rulerships,
aspect-based determinations, life-area scores, and nature/condition.

Inputs: serialized natal chart_data; optionally metrics (from astro_clock_metrics).
Outputs: {'determinations': [Determination...], 'by_planet': {name: Determination}}

Notes:
- Uses existing house_influence and astro_clock_metrics to stay consistent with
  current engine scoring and domains.
- Life-area scores include a full 12-house map plus convenience keys for
  spec examples (life/health/wealth/relationships/honors/death).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _planet_list(chart_data: Dict[str, Any], include_modern: bool = False) -> List[str]:
    base = ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn']
    if include_modern:
        base += ['Uranus','Neptune','Pluto']
    # filter by availability
    raw = chart_data.get('planets') or {}
    names = set()
    if isinstance(raw, dict):
        names.update([str(nm) for nm in raw.keys()])
    elif isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict) and row.get('planet'):
                names.add(str(row['planet']))
    return [nm for nm in base if nm in names]


def _house_of(planet: str, chart_data: Dict[str, Any]) -> Optional[int]:
    try:
        raw = chart_data.get('planets') or {}
        if isinstance(raw, dict):
            row = raw.get(planet)
            if isinstance(row, dict) and row.get('house') is not None:
                return int(row.get('house'))
        elif isinstance(raw, list):
            for row in raw:
                if isinstance(row, dict) and row.get('planet') == planet and row.get('house') is not None:
                    return int(row.get('house'))
    except Exception:
        return None
    return None


def _house_domain_map() -> Dict[int, str]:
    # Mapping aligned to house_influence basic rules
    return {
        1: 'life',
        2: 'wealth',
        3: 'short_travel',
        4: 'home',
        5: 'children',
        6: 'health',
        7: 'relationships',
        8: 'death',  # crisis/mortality bucket
        9: 'belief',
        10: 'honors',
        11: 'friends',
        12: 'death',  # hidden enemies/illness bucket
    }


def _nature_primary(planet: str) -> str:
    if planet in ('Jupiter','Venus'):
        return 'benefic'
    if planet in ('Saturn','Mars'):
        return 'malefic'
    return 'neutral'


def compute_determinations(
    chart_data: Dict[str, Any],
    *,
    metrics: Optional[Dict[str, Any]] = None,
    include_modern: bool = False,
) -> Dict[str, Any]:
    # Lazy imports to avoid heavy startup
    try:
        from astro_clock_metrics import compute_metrics  # type: ignore
    except Exception:
        compute_metrics = None  # type: ignore
    try:
        from house_influence import compute_house_influences  # type: ignore
        from house_influence import _load_basic_rules as _load_rules  # type: ignore
    except Exception:
        compute_house_influences = None  # type: ignore
        _load_rules = lambda: {}

    # Metrics
    if metrics is None:
        ts_iso = None
        try:
            tzinfo = chart_data.get('timezone_info') or {}
            ts_iso = tzinfo.get('utc_time') or tzinfo.get('local_time')
        except Exception:
            ts_iso = None
        try:
            if compute_metrics:
                metrics = compute_metrics(chart_data or {}, ts_iso, special_degrees=[])
            else:
                metrics = {}
        except Exception:
            metrics = {}

    # House influences
    hi = {'houses': [], 'planet_strengths': {}}
    try:
        if compute_house_influences:
            hi = compute_house_influences(chart_data or {}, metrics or {})
    except Exception:
        hi = {'houses': [], 'planet_strengths': {}}

    # Build lookup maps from house_influence output
    influences_by_house: Dict[int, List[Dict[str, Any]]] = {}
    for row in (hi.get('houses') or []):
        try:
            h = int(row.get('house'))
            influences_by_house[h] = list(row.get('influences') or [])
        except Exception:
            continue

    # Build Determination per planet
    rules = _load_rules() or {}
    house_domains = _house_domain_map()
    dets: List[Dict[str, Any]] = []
    by_planet: Dict[str, Dict[str, Any]] = {}
    planets = _planet_list(chart_data or {}, include_modern=include_modern)
    pstatus = (metrics or {}).get('planet_status') or {}

    for p in planets:
        # Natural signification (short string from basic rules)
        nat = ''
        try:
            nat = str((rules.get('planets') or {}).get(p, {}).get('nature') or '')
        except Exception:
            nat = ''

        # House position
        ph = _house_of(p, chart_data) or None
        house_sig = []
        try:
            if isinstance(ph, int):
                domtxt = str((rules.get('houses') or {}).get(str(ph), {}).get('domain') or '')
                if domtxt:
                    house_sig = [s.strip() for s in domtxt.split(',') if s.strip()]
        except Exception:
            house_sig = []
        house_position = {'house': ph, 'significations': house_sig}

        # Rulerships (domicile + co-rulership simplified)
        rulerships: List[Dict[str, Any]] = []
        try:
            hr = chart_data.get('house_rulers') or {}
            if isinstance(hr, dict):
                for k, v in hr.items():
                    try:
                        if str(v) == p:
                            rulerships.append({'house': int(k), 'strength': 'domicile', 'significations': [str((rules.get('houses') or {}).get(str(k), {}).get('domain') or '')]})
                    except Exception:
                        continue
        except Exception:
            pass

        # Aspect-based determinations (natal aspects → aspected planet's house/domain)
        aspect_dets: List[Dict[str, Any]] = []
        try:
            aspects = chart_data.get('aspects') or []
            if isinstance(aspects, list):
                # Build planet house map
                phouses: Dict[str, Optional[int]] = {}
                rawp = chart_data.get('planets') or {}
                if isinstance(rawp, dict):
                    for nm, row in rawp.items():
                        if isinstance(row, dict):
                            try:
                                phouses[str(nm)] = int(row.get('house')) if row.get('house') is not None else None
                            except Exception:
                                phouses[str(nm)] = None
                elif isinstance(rawp, list):
                    for row in rawp:
                        try:
                            nm = str(row.get('planet'))
                            phouses[nm] = int(row.get('house')) if row.get('house') is not None else None
                        except Exception:
                            continue
                for a in aspects:
                    if not isinstance(a, dict):
                        continue
                    p1 = str(a.get('planet1') or a.get('p1') or '')
                    p2 = str(a.get('planet2') or a.get('p2') or '')
                    if p1 == p or p2 == p:
                        other = p2 if p1 == p else p1
                        asp = str(a.get('aspect') or a.get('name') or '')
                        h_other = phouses.get(other)
                        sigs = []
                        try:
                            if isinstance(h_other, int):
                                domtxt = str((rules.get('houses') or {}).get(str(h_other), {}).get('domain') or '')
                                if domtxt:
                                    sigs = [s.strip() for s in domtxt.split(',') if s.strip()]
                        except Exception:
                            sigs = []
                        aspect_dets.append({'aspectedPlanet': other, 'aspect': asp, 'aspectedHouse': h_other, 'significations': sigs})
        except Exception:
            aspect_dets = []

        # Life-area scores
        # Aggregate influence values for this planet across houses
        per_house: Dict[int, float] = {i: 0.0 for i in range(1, 13)}
        try:
            for h, infl in influences_by_house.items():
                for inf in infl:
                    try:
                        if str(inf.get('planet')) != p:
                            continue
                        per_house[h] += _safe_float(inf.get('value'), 0.0)
                    except Exception:
                        continue
        except Exception:
            pass
        # Map into named life areas
        life_scores: Dict[str, float] = {}
        for h, v in per_house.items():
            key = house_domains.get(h)
            if key:
                life_scores[key] = life_scores.get(key, 0.0) + float(v)

        # Extend life-area map with spec aliases (violence, 8th house, family loss, etc.)
        by_area: Dict[str, float] = dict(life_scores)
        abs_per_house = {h: abs(float(v)) for h, v in per_house.items()}
        death_core = abs_per_house.get(8, 0.0)
        death_hidden = abs_per_house.get(12, 0.0)
        violence_score = death_core + death_hidden + abs_per_house.get(1, 0.0)
        loss_score = death_core + death_hidden
        grief_score = loss_score + abs_per_house.get(4, 0.0) + abs_per_house.get(10, 0.0)
        family_score = sum(abs_per_house.get(h, 0.0) for h in (3, 4, 5, 7, 10))
        alias_pairs = {
            '8th_house': death_core,
            '8th_house_matters': death_core,
            'death_house': death_core + death_hidden,
            'violence': violence_score,
            'loss': loss_score,
            'grief': grief_score,
            'relevant_family_house': family_score,
            'family': family_score,
            '6th_house': abs_per_house.get(6, 0.0),
            '6th_house_matters': abs_per_house.get(6, 0.0),
            '12th_house': abs_per_house.get(12, 0.0),
            '12th_house_matters': abs_per_house.get(12, 0.0),
            'illness': abs_per_house.get(6, 0.0) + abs_per_house.get(12, 0.0),
            'chronic_conditions': abs_per_house.get(6, 0.0) + abs_per_house.get(12, 0.0),
        }
        for alias, val in alias_pairs.items():
            by_area.setdefault(alias, float(val))

        # Convenience top keys in spec examples (keep legacy keys available)
        convenience = {
            'life': by_area.get('life', 0.0),
            'health': by_area.get('health', 0.0),
            'wealth': by_area.get('wealth', 0.0),
            'relationships': by_area.get('relationships', 0.0),
            'honors': by_area.get('honors', 0.0),
            'death': by_area.get('death', 0.0),
        }

        # Nature / condition
        status = (pstatus.get(p) or {}) if isinstance(pstatus, dict) else {}
        dignified = bool(status.get('dignified'))
        afflicted = bool(status.get('afflicted'))
        strong = bool(status.get('strong'))
        cond_score = 0.0
        try:
            if dignified:
                cond_score += 4.0
            if strong:
                cond_score += 2.0
            if afflicted:
                cond_score -= 4.0
        except Exception:
            cond_score = 0.0
        nature = {'primary': _nature_primary(p), 'conditionScore': cond_score}

        det = {
            'planet': p,
            'naturalSignifications': [s.strip() for s in str(nat).split(',') if s.strip()],
            'housePosition': house_position,
            'rulerships': rulerships,
            'aspectDeterminations': aspect_dets,
            'determinationScores': {
                'by_house': per_house,
                'by_area': by_area,
                **convenience,
            },
            'nature': nature,
        }
        dets.append(det)
        by_planet[p] = det

    return {'determinations': dets, 'by_planet': by_planet}


__all__ = ['compute_determinations']
