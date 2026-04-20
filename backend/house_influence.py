# -*- coding: utf-8 -*-
"""
House Influence Calculator (Morin-inspired)

Computes per-house planetary influence scores using a simplified version of the
logic described:
  - Occupation (planet in house)
  - Rulership (domicile ruler of cusp sign)
  - Aspect to cusp (major aspects, with orb scaling)
  - Co-rulership (exaltation 0.4x; triplicity 0.3x based on sect)

Total planet strength is estimated from chart_data + metrics as:
  Intrinsic + Essential dignity + House position + Motion + Solar (combustion) + Aspects Received

This module is engine-agnostic and consumes serialized chart_data and the
metrics dict produced by astro_clock_metrics.compute_metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import json
import os
import math

try:
    from sect import compute_sect_info  # day/night for triplicity selection
except Exception:  # pragma: no cover
    compute_sect_info = None  # type: ignore


# ------------------------
# Constants and tables
# ------------------------

PLANET_INTRINSIC = {
    'Sun': 18.0,
    'Moon': 15.0,
    'Saturn': 12.0,
    'Jupiter': 8.0,
    'Mars': 12.0,
    'Venus': 8.0,
    'Mercury': 8.0,
}

# House values (Ch. XIV)
HOUSE_VALUES = {
    1: 6.0, 2: 3.0, 3: 0.5, 4: 4.5, 5: 2.5, 6: 1.0,
    7: 5.0, 8: 3.5, 9: 2.0, 10: 5.5, 11: 4.0, 12: 1.5,
}

# Classical sign rulers (domicile)
SIGN_RULER = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon',
    'Leo': 'Sun', 'Virgo': 'Mercury', 'Libra': 'Venus', 'Scorpio': 'Mars',
    'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter',
}

# Exaltations (principal)
EXALTATION = {
    'Aries': 'Sun',
    'Taurus': 'Moon',
    'Cancer': 'Jupiter',
    'Virgo': 'Mercury',
    'Libra': 'Saturn',
    'Capricorn': 'Mars',
    'Pisces': 'Venus',
}

# Triplicity rulers (Dorothean). Format: { element: (day, night, participating) }
TRIPLICITY = {
    'Fire': ('Sun', 'Jupiter', 'Saturn'),
    'Earth': ('Venus', 'Moon', 'Mars'),
    'Air': ('Saturn', 'Mercury', 'Jupiter'),
    'Water': ('Venus', 'Mars', 'Moon'),
}

BENEFICS = {'Jupiter', 'Venus'}
MALEFICS = {'Saturn', 'Mars'}

ASPECTS = [
    # angle, name, proportion, default_allowed_orb
    (0.0, 'Conjunction', 1.00, 8.0),
    (60.0, 'Sextile', 0.33, 6.0),
    (90.0, 'Square', 0.50, 8.0),
    (120.0, 'Trine', 0.67, 8.0),
    (180.0, 'Opposition', 0.50, 10.0),
]

# ------------------------
# Basic Analysis rules (loaded from JSON)
# ------------------------

_BASIC_RULES: Optional[Dict[str, Any]] = None


def _load_basic_rules() -> Dict[str, Any]:
    global _BASIC_RULES
    if _BASIC_RULES is not None:
        return _BASIC_RULES
    # Search for a rules file in common backend locations
    candidates = [
        os.path.join(os.path.dirname(__file__), 'knowledge', 'basic_analysis_rules.json'),
        os.path.join(os.path.dirname(__file__), 'basic_analysis_rules.json'),
    ]
    data: Dict[str, Any] = {
        'version': 'fallback-1.0',
        'hierarchy': ['location', 'rulership', 'aspectual'],
        'planets': {
            'Sun': {'nature': 'authority, vitality, prestige', 'benefic': True},
            'Moon': {'nature': 'emotion, habit, body', 'benefic': True},
            'Mercury': {'nature': 'communication, trade, intellect', 'benefic': None},
            'Venus': {'nature': 'harmony, love, beauty', 'benefic': True},
            'Mars': {'nature': 'conflict, aggression, heat', 'benefic': False},
            'Jupiter': {'nature': 'expansion, abundance, growth', 'benefic': True},
            'Saturn': {'nature': 'restriction, cold, fear', 'benefic': False},
        },
        'houses': {
            '1': {'domain': 'self, body, character'},
            '2': {'domain': 'money, possessions, income'},
            '3': {'domain': 'siblings, messages, short travel'},
            '4': {'domain': 'home, roots, land, parents'},
            '5': {'domain': 'children, pleasure, creativity'},
            '6': {'domain': 'work, illness, service'},
            '7': {'domain': 'marriage, partnerships, open enemies'},
            '8': {'domain': 'crisis, debts, mortality'},
            '9': {'domain': 'belief, higher learning, journeys'},
            '10': {'domain': 'career, honors, reputation'},
            '11': {'domain': 'friends, hopes, benefactors'},
            '12': {'domain': 'illness, confinement, hidden enemies'},
        },
        'rulership_patterns': {
            '7-2': 'Money through marriage, contracts, or litigation',
            '10-12': 'Profession brings misfortune, illness, prison, or exile',
            '1-8': 'Self/health bound up with crisis or mortality',
        },
        'aspect_notes': {
            'afflicting': ['Square', 'Opposition', 'Quincunx'],
            'favorable': ['Trine', 'Sextile'],
        },
        'location_examples': [
            {'planet': 'Mars', 'house': 7,
             'positive': 'Competitive partnerships; success against rivals when strong and supported',
             'negative': 'Quarrels, lawsuits, aggressive enemies; severed partnerships when afflicted'},
            {'planet': 'Jupiter', 'house': 2,
             'positive': 'Wealth and financial growth; multiple income sources',
             'negative': 'Overextension and losses; optimism without delivery when afflicted'},
            {'planet': 'Saturn', 'house': 12,
             'positive': 'Discipline in seclusion; dangers mitigated when benefics co-present',
             'negative': 'Chronic illness, confinement, hidden enemies; repeated obstacles'},
        ],
        'modifiers': {
            'dignified_keywords': ['domicile', 'exaltation', 'triplicity'],
            'debilitated_keywords': ['detriment', 'fall'],
        },
    }
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
        except Exception:
            continue
    _BASIC_RULES = data
    return data


# ------------------------
# Morin Dictionary Keywords (externalized source of truth)
# ------------------------
_MORIN_KWS: Optional[Dict[str, Any]] = None


def _load_morin_keywords() -> Dict[str, Any]:
    """Load curated Morin keywords map from knowledge JSON.

    Fallbacks to an empty dict when not present to avoid breaking existing logic.
    """
    global _MORIN_KWS
    if _MORIN_KWS is not None:
        return _MORIN_KWS
    candidates = [
        os.path.join(os.path.dirname(__file__), 'knowledge', 'morin_keywords.json'),
        os.path.join(os.path.dirname(__file__), 'morin_keywords.json'),
    ]
    data: Dict[str, Any] = {}
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
        except Exception:
            continue
    _MORIN_KWS = data if isinstance(data, dict) else {}
    return _MORIN_KWS


def _kw_planet_from_dict(planet: str) -> List[str]:
    try:
        dic = _load_morin_keywords().get('planets', {})
        return list(dic.get(str(planet), {}).get('keywords_primary') or [])
    except Exception:
        return []


def _kw_house_from_dict(house: int) -> List[str]:
    try:
        dic = _load_morin_keywords().get('houses', {})
        row = dic.get(str(int(house))) or {}
        out: List[str] = []
        out.extend(row.get('keywords_primary') or [])
        cusp = row.get('cusp')
        if cusp:
            out.append(str(cusp))
        # fortunate/unfortunate tag
        if row.get('fortunate') is True:
            out.append('fortunate')
        elif row.get('fortunate') is False:
            out.append('unfortunate')
        return out
    except Exception:
        return []


def _kw_aspect_from_dict(aspect: Optional[str]) -> List[str]:
    try:
        if not aspect:
            return []
        dic = _load_morin_keywords().get('aspects', {})
        return list(dic.get(str(aspect), []) or [])
    except Exception:
        return []


def _p_nature(p: str) -> str:
    try:
        return str(_load_basic_rules().get('planets', {}).get(p, {}).get('nature') or '')
    except Exception:
        return ''


def _h_domain(h: int) -> str:
    try:
        return str(_load_basic_rules().get('houses', {}).get(str(h), {}).get('domain') or '')
    except Exception:
        return ''


# ------------------------
# Utilities
# ------------------------

def _norm360(x: float) -> float:
    return x % 360.0


def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _absdiff_deg(a: float, b: float) -> float:
    return abs(_norm180(a - b))


def _sign_from_lon(lon: Optional[float]) -> Optional[str]:
    if lon is None:
        return None
    d = _norm360(float(lon))
    names = [
        'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces',
    ]
    return names[int(d // 30) % 12]


def _element_of_sign(sign: str) -> str:
    s = (sign or '').strip().lower()
    if s in ('aries', 'leo', 'sagittarius'): return 'Fire'
    if s in ('taurus', 'virgo', 'capricorn'): return 'Earth'
    if s in ('gemini', 'libra', 'aquarius'): return 'Air'
    return 'Water'

def _modality_of_sign(sign: str) -> str:
    s = (sign or '').strip().lower()
    if s in ('aries','cancer','libra','capricorn'):
        return 'Cardinal'
    if s in ('taurus','leo','scorpio','aquarius'):
        return 'Fixed'
    return 'Mutable'


def _allowed_orb(name: str, default: float) -> float:
    """Allowed orb per aspect. Consult rules.aspect_orbs if provided."""
    try:
        rules = _load_basic_rules()
        m = (rules.get('aspect_orbs') or {})
        if name in m:
            return float(m.get(name))
    except Exception:
        pass
    return default


def _aspect_to(lon1: float, lon2: float) -> Optional[Tuple[str, float, float]]:
    """Return (name, orb, allowed) if within orb, else None."""
    for angle, aname, _prop, aorb in ASPECTS:
        sep = _absdiff_deg(lon1, lon2)
        orb = abs(sep - angle)
        if orb > 180.0:
            orb = 360.0 - orb
        allowed = _allowed_orb(aname, aorb)
        if orb <= allowed:
            return aname, orb, allowed
    return None


# ------------------------
# Data extraction from chart_data / metrics
# ------------------------

def _planet_rows(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    pls = chart_data.get('planets') or []
    out: List[Dict[str, Any]] = []
    if isinstance(pls, dict):
        for nm, info in pls.items():
            if isinstance(info, dict):
                r = dict(info)
                r.setdefault('planet', nm)
                out.append(r)
    elif isinstance(pls, list):
        for p in pls:
            if isinstance(p, dict):
                out.append(p)
    return out


def _planet_index(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for r in _planet_rows(chart_data):
        nm = r.get('planet') or r.get('name')
        if nm:
            idx[str(nm)] = r
    return idx


def _house_cusps(chart_data: Dict[str, Any]) -> List[float]:
    cusps = chart_data.get('houses') or chart_data.get('house_cusps') or []
    if not isinstance(cusps, list):
        return []
    return [float(x) for x in cusps[:12]]


def _house_of_planet(name: str, chart_data: Dict[str, Any]) -> Optional[int]:
    p = _planet_index(chart_data).get(name)
    if isinstance(p, dict):
        try:
            h = int(p.get('house'))
            if 1 <= h <= 12:
                return h
        except Exception:
            pass
        try:
            lon = float(p.get('longitude'))
        except Exception:
            lon = None
        cusps = _house_cusps(chart_data)
        if lon is not None and len(cusps) >= 12:
            # determine in which arc between cusps the lon falls
            def in_arc(start: float, end: float, point: float) -> bool:
                start = _norm360(start); end = _norm360(end); point = _norm360(point)
                if start <= end:
                    return start <= point < end
                else:
                    return point >= start or point < end
            for i in range(12):
                if in_arc(cusps[i], cusps[(i + 1) % 12], lon):
                    return i + 1
    return None


# ------------------------
# Strength computation
# ------------------------

def _intrinsic(name: str) -> float:
    return PLANET_INTRINSIC.get(name, 0.0)


def _dignity_component(planet: str, pdata: Dict[str, Any]) -> float:
    # Prefer categorical dignities if present
    vals = 0.0
    try:
        digs = pdata.get('dignities')
        if isinstance(digs, list):
            names = {str(x).strip().lower() for x in digs}
            if 'domicile' in names: vals += 5.0
            if 'exaltation' in names: vals += 4.0
            if 'triplicity' in names: vals += 3.0
            if 'detriment' in names: vals += -5.0
            if 'fall' in names: vals += -4.0
            return vals
    except Exception:
        pass
    # Fallback to essential_dignity numeric if available
    try:
        ess = float(pdata.get('essential_dignity', 0.0) or 0.0)
        vals += ess
    except Exception:
        pass
    return vals


def _house_position_component(house: Optional[int]) -> float:
    try:
        return float(HOUSE_VALUES.get(int(house or 0), 0.0))
    except Exception:
        return 0.0


def _motion_component(planet: str, pdata: Dict[str, Any]) -> float:
    # Simplified: benefics (Jupiter, Venus) +2 direct, -3 retro;
    # malefics (Saturn, Mars) +2 direct, -2 retro; others 0.
    retro = bool(pdata.get('retrograde'))
    if planet in BENEFICS:
        return -3.0 if retro else 2.0
    if planet in MALEFICS:
        return -2.0 if retro else 2.0
    return 0.0


def _solar_component(planet: str, metrics: Dict[str, Any]) -> float:
    try:
        cond = (metrics.get('solar') or {}).get('conditions') or {}
        label = cond.get(planet)
        if isinstance(label, str):
            lab = label.strip().lower()
            if lab.startswith('cazimi'):
                return 4.0
            if lab.startswith('combust'):
                return -5.0
            if 'under' in lab and 'beam' in lab:
                # Under the beams — moderate penalty
                return -2.0
    except Exception:
        pass
    return 0.0

def _sun_longitude(metrics: Dict[str, Any], chart_data: Dict[str, Any]) -> Optional[float]:
    try:
        plons = metrics.get('planet_longitudes') or {}
        if isinstance(plons, dict) and 'Sun' in plons:
            return float(plons.get('Sun'))
    except Exception:
        pass
    try:
        sun = _planet_index(chart_data).get('Sun')
        if isinstance(sun, dict):
            return float(sun.get('longitude'))
    except Exception:
        pass
    return None


def _orientation_component(planet: str, lon: Optional[float], sun_lon: Optional[float]) -> Tuple[float, Optional[str]]:
    """Return (+2/-2 adjustment, 'oriental'/'occidental'/None). Sun gets 0/None."""
    if planet == 'Sun' or lon is None or sun_lon is None:
        return 0.0, None
    try:
        delta = _norm180(float(lon) - float(sun_lon))
        if delta < 0:
            return 2.0, 'oriental'  # west of Sun, rises before
        else:
            return -2.0, 'occidental'
    except Exception:
        return 0.0, None


def _elevation_component(planet: str, pdata: Dict[str, Any]) -> Tuple[float, Optional[str]]:
    """Heuristic elevation: apply for Moon only using speed.
    Moon fast (>=13.9°/day) → perigee (−1), slow (<=12.1) → apogee (+1).
    Others: 0.
    """
    try:
        if planet != 'Moon':
            return 0.0, None
        spd = float(pdata.get('speed', 0.0) or 0.0)
        if spd >= 13.9:
            return -1.0, 'perigee'
        if spd <= 12.1:
            return 1.0, 'apogee'
    except Exception:
        pass
    return 0.0, None


def _aspects_received_breakdown(planet: str, metrics: Dict[str, Any], base_strengths: Dict[str, float], dignity_map: Dict[str, float]) -> Tuple[float, List[Dict[str, Any]]]:
    total = 0.0
    items: List[Dict[str, Any]] = []
    pairs = metrics.get('planetary_aspects') or []
    for a in pairs:
        p1 = a.get('planet1'); p2 = a.get('planet2'); aname = a.get('aspect')
        if not isinstance(aname, str):
            continue
        # Determine if planet receives aspect from the other
        if planet == p1 and p2 in base_strengths:
            other = p2
        elif planet == p2 and p1 in base_strengths:
            other = p1
        else:
            continue

        # Proportion
        prop = next((pr for ang, nm, pr, _ao in ASPECTS if nm == aname), None)
        if prop is None:
            continue
        try:
            orb = float(a.get('orb') or 999.0)
        except Exception:
            orb = 999.0
        try:
            allowed = float(a.get('allowed_orb') or 6.0)
        except Exception:
            allowed = 6.0
        if allowed <= 0:
            allowed = 6.0
        # Orb factor: (allowed - orb)/allowed, floored at 0
        orb_factor = max(0.0, (allowed - orb) / allowed)

        # Polarity: Trine/Sextile positive; Square/Opp negative; Conjunction depends on other planet nature
        sign_val = 1.0
        if aname in ('Square', 'Opposition'):
            sign_val = -1.0
        elif aname == 'Conjunction':
            if other in MALEFICS:
                sign_val = -1.0
            elif other in BENEFICS:
                sign_val = 1.0
            else:
                sign_val = 0.5  # neutral-ish

        contrib = base_strengths[other] * prop * orb_factor * sign_val
        # Dignity refinement
        try:
            ess = float(dignity_map.get(other, 0.0) or 0.0)
            dignity_factor = max(0.75, min(1.25, 1.0 + ess / 10.0))
            if contrib >= 0:
                contrib *= dignity_factor
            else:
                contrib *= (1.0 / dignity_factor)
        except Exception:
            pass
        total += contrib
        try:
            items.append({
                'from': other,
                'aspect': aname,
                'orb': round(orb, 2),
                'prop': prop,
                'contrib': round(contrib, 2),
            })
        except Exception:
            pass

    items.sort(key=lambda x: -abs(float(x.get('contrib') or 0.0)))
    return total, items[:5]


def compute_total_strengths(chart_data: Dict[str, Any], metrics: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
    """Return per-planet total strengths following the described formula.

    Strategy: compute base totals first (without aspects received), then add
    aspects contributions using the base totals of aspecting planets.
    """
    planets = _planet_index(chart_data)
    sun_lon = _sun_longitude(metrics, chart_data)
    # Base strengths
    base: Dict[str, float] = {}
    dignity_map: Dict[str, float] = {}
    breakdowns: Dict[str, Dict[str, Any]] = {}
    for name, pdata in planets.items():
        intr = _intrinsic(name)
        dign = _dignity_component(name, pdata)
        dignity_map[name] = dign
        house = None
        try:
            house = int(pdata.get('house'))
        except Exception:
            house = _house_of_planet(name, chart_data)
        house_pos = _house_position_component(house)
        motion = _motion_component(name, pdata)
        solar = _solar_component(name, metrics)
        try:
            plon = float(pdata.get('longitude', None)) if pdata is not None else None
        except Exception:
            plon = None
        orient_adj, _orient_lbl = _orientation_component(name, plon, sun_lon)
        elev_adj, _elev_lbl = _elevation_component(name, pdata)
        core_total = intr + dign + house_pos + motion + solar + orient_adj + elev_adj
        base[name] = max(0.0, core_total)
        breakdowns[name] = {
            'intrinsic': round(intr, 2),
            'dignity': round(dign, 2),
            'house_position': round(house_pos, 2),
            'motion': round(motion, 2),
            'solar': round(solar, 2),
            'orientation': {'value': round(orient_adj, 2), 'label': _orient_lbl},
            'elevation': {'value': round(elev_adj, 2), 'label': _elev_lbl},
            'aspects': {'total': 0.0, 'top': []},
            'core': round(core_total, 2),
        }

    # Add aspects received
    totals: Dict[str, float] = {k: v for k, v in base.items()}
    for name in planets.keys():
        s, top = _aspects_received_breakdown(name, metrics, base, dignity_map)
        totals[name] = max(0.0, totals.get(name, 0.0) + s)
        try:
            breakdowns[name]['aspects'] = {'total': round(s, 2), 'top': top}
            breakdowns[name]['total'] = round(totals[name], 2)
        except Exception:
            pass
    return totals, breakdowns


# ------------------------
# Influence per connection type
# ------------------------

def _proximity_factor(planet_lon: float, cusp_lon: float) -> Tuple[float, float]:
    """Return (factor, distance_deg). 1.0–1.2 within 10°.
    Closer to cusp increases factor linearly to +0.2 at exact.
    """
    d = _absdiff_deg(planet_lon, cusp_lon)
    k = max(0.0, 1.0 - min(d, 10.0) / 10.0)
    return (1.0 + 0.2 * k), d


def _dexter_to_cusp(planet_lon: float, cusp_lon: float) -> bool:
    """Return True if planet casts a dexter aspect to the cusp (earlier in zodiac)."""
    forward = (_norm360(cusp_lon) - _norm360(planet_lon)) % 360.0
    return forward <= 180.0


def _phase_to_cusp(planet_lon: float, cusp_lon: float, angle: float, planet_speed: float) -> str:
    diff = _norm180((planet_lon - cusp_lon) - angle)
    if abs(planet_speed) <= 1e-6:
        return 'stationary'
    return 'applying' if (diff * planet_speed) < 0 else 'separating'


def _house_group(h: int) -> str:
    if h in (1, 4, 7, 10):
        return 'angular'
    if h in (2, 5, 8, 11):
        return 'succedent'
    return 'cadent'


def _location_factor(h: Optional[int]) -> float:
    if h in (1, 4, 7, 10):
        return 1.2
    if h in (3, 6, 9, 12):
        return 0.8
    return 1.0


def _house_rulers_from_chart(chart_data: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        hr = chart_data.get('house_rulers') or {}
        if isinstance(hr, dict):
            for k, v in hr.items():
                out[str(k)] = v if isinstance(v, str) else getattr(v, 'value', None) or str(v)
    except Exception:
        pass
    return out


def _sign_rulers_for_cusp(sign: str, day_chart: Optional[bool]) -> Dict[str, Tuple[str, Optional[str]]]:
    """Return mapping of role -> (planet, kind) with keys: 'ruler', 'exalt', 'triplicity'.
    Triplicity picks day or night ruler according to chart sect when provided.
    """
    ruler = SIGN_RULER.get(sign)
    exalt = EXALTATION.get(sign)
    elem = _element_of_sign(sign)
    tri = TRIPLICITY.get(elem)
    trip = None
    if tri:
        if day_chart is None:
            # default to day ruler if unknown
            trip = tri[0]
        else:
            trip = tri[0] if day_chart else tri[1]
    return {
        'ruler': (ruler, 'domicile'),
        'exalt': (exalt, 'exaltation'),
        'triplicity': (trip, 'triplicity'),
    }


def compute_house_influences(chart_data: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compute influence breakdown for each of the 12 houses.

    Returns a dict with key 'houses': list of { house, sign, cusp_longitude, influences: [...] }.
    Influence entries have fields: planet, type, value, and type-specific context.
    """
    cusps = _house_cusps(chart_data)
    # Build a 12-house scaffold even if cusps are missing; skip cusp-based aspects in that case.
    have_cusps = len(cusps) >= 12
    if not have_cusps:
        cusps = [None] * 12

    # Determine cusp signs (may be realigned below if an off-by-one ordering is detected)
    cusp_signs = [_sign_from_lon(c) for c in cusps]

    # Attempt alignment with provided house_rulers if available. In some environments,
    # upstream cusp arrays may be shifted by one position; when a house_rulers map is
    # present, choose the rotation (0..11) that maximizes ruler/sign agreement.
    try:
        hr_map = chart_data.get('house_rulers') or {}
        if isinstance(hr_map, dict) and any(str(k) in hr_map for k in ("1","2","3","4","5","6","7","8","9","10","11","12")):
            # Normalize to string->str planet name
            norm_hr = {str(k): (v if isinstance(v, str) else getattr(v, 'value', None) or str(v)) for k, v in hr_map.items()}
            def score_rotation(offset: int) -> int:
                score = 0
                for i in range(12):
                    s = cusp_signs[(i + offset) % 12]
                    if not isinstance(s, str):
                        continue
                    expected = SIGN_RULER.get(s)
                    actual = norm_hr.get(str(i+1))
                    if expected and actual and expected == actual:
                        score += 1
                return score
            best_off = 0
            base_score = score_rotation(0)
            best_score = base_score
            for off in range(1, 12):
                sc = score_rotation(off)
                if sc > best_score:
                    best_score = sc
                    best_off = off
            # Apply rotation only if it improves alignment meaningfully
            if best_off != 0 and best_score > base_score and best_score >= 3:
                # Realign cusps and signs by the detected rotation
                cusps = [cusps[(i + best_off) % 12] for i in range(12)]
                cusp_signs = [cusp_signs[(i + best_off) % 12] for i in range(12)]
                have_cusps = len([c for c in cusps if c is not None]) >= 12
    except Exception:
        # Non-fatal; continue with original ordering
        pass

    # Sect (for triplicity day/night)
    day_chart: Optional[bool] = None
    try:
        if compute_sect_info:
            sec = compute_sect_info(chart_data)
            cs = str(sec.get('chart_sect') or '')
            day_chart = True if cs == 'diurnal' else (False if cs == 'nocturnal' else None)
    except Exception:
        day_chart = None

    # Planet longitudes and houses
    pindex = _planet_index(chart_data)
    plon: Dict[str, float] = {}
    phouse: Dict[str, int] = {}
    for nm, pdata in pindex.items():
        try:
            plon[nm] = float(pdata.get('longitude'))
        except Exception:
            continue
        # Prefer computing house from cusps when available for consistency
        h_calc = _house_of_planet(nm, chart_data)
        if h_calc is not None:
            phouse[nm] = int(h_calc)
        else:
            try:
                phouse[nm] = int(pdata.get('house'))
            except Exception:
                phouse[nm] = 0

    totals, breakdowns = compute_total_strengths(chart_data, metrics)

    rows: List[Dict[str, Any]] = []
    # Precompute house ruler overrides if present in chart_data
    house_rulers = _house_rulers_from_chart(chart_data)

    for i in range(12):
        hnum = i + 1
        cusp = cusps[i]
        sign = cusp_signs[i] if have_cusps else None
        influences: List[Dict[str, Any]] = []

        # Occupation
        for nm, h in phouse.items():
            if h == hnum and nm in totals and nm in plon:
                base = float(totals[nm])
                factor, dist = _proximity_factor(plon[nm], cusp)
                val = (base + HOUSE_VALUES.get(hnum, 0.0)) * factor
                influences.append({
                    'planet': nm,
                    'type': 'occupation',
                    'value': round(val, 2),
                    'proximity_deg': round(dist, 2),
                    'proximity_factor': round(factor, 2),
                    'details': {
                        'total': round(base, 2),
                        'house_value': HOUSE_VALUES.get(hnum, 0.0),
                        'breakdown': breakdowns.get(nm),
                    }
                })

        # Rulership (domicile)
        ruler_nm = None
        if house_rulers.get(str(hnum)):
            ruler_nm = house_rulers.get(str(hnum))
        elif isinstance(sign, str):
            ruler_nm = SIGN_RULER.get(sign)
        if ruler_nm and ruler_nm in totals:
            try:
                w = float((_load_basic_rules().get('governance_weights') or {}).get('rulership') or 0.7)
            except Exception:
                w = 0.7
            base_val = float(totals[ruler_nm]) * w
            loc_fac = _location_factor(phouse.get(ruler_nm))
            influences.append({
                'planet': ruler_nm,
                'type': 'rulership',
                'value': round(base_val * loc_fac, 2),
                'location_factor': loc_fac,
                'details': {
                    'total': round(float(totals[ruler_nm]), 2),
                    'factor': w,
                    'breakdown': breakdowns.get(ruler_nm),
                }
            })

        # Aspect to cusp (all planets) — only when cusps are present
        if have_cusps and cusp is not None:
            for nm, lon in plon.items():
                if nm not in totals:
                    continue
                asp = _aspect_to(lon, cusp)
                if not asp:
                    continue
                aname, orb, allowed = asp
                # Aspect proportion from table
                prop = next((pr for ang, nn, pr, ao in ASPECTS if nn == aname), 0.0)
                orb_fac = max(0.0, (allowed - float(orb)) / allowed)
                # Dexter/sinister bias and application/separation
                dexter = _dexter_to_cusp(lon, cusp)
                try:
                    rules = _load_basic_rules()
                    dexter_factor = float((rules.get('dexter') or {}).get('factor') or 1.1) if dexter else float((rules.get('sinister') or {}).get('factor') or 0.9)
                except Exception:
                    dexter_factor = 1.1 if dexter else 0.9
                try:
                    spd = float(pindex.get(nm, {}).get('speed', 0.0) or 0.0)
                except Exception:
                    spd = 0.0
                angle = next((ang for ang, nn, _pr, _ao in ASPECTS if nn == aname), 0.0)
                phase = _phase_to_cusp(lon, cusp, angle, spd)
                try:
                    pf = (_load_basic_rules().get('phase_factors') or {})
                    phase_factor = float(pf.get('applying') or 1.15) if phase == 'applying' else (float(pf.get('separating') or 0.85) if phase == 'separating' else 1.0)
                except Exception:
                    phase_factor = 1.15 if phase == 'applying' else (0.85 if phase == 'separating' else 1.0)
                raw_total = float(totals[nm])
                val = raw_total * prop * orb_fac * dexter_factor * phase_factor
                influences.append({
                    'planet': nm,
                    'type': 'aspect',
                    'aspect': aname,
                    'orb': round(float(orb), 2),
                    'value': round(val, 2),
                    'dexter': bool(dexter),
                    'phase': phase,
                    'origin_house': int(phouse.get(nm)) if nm in phouse and phouse.get(nm) is not None else None,
                    'origin_domain': _h_domain(int(phouse.get(nm))) if nm in phouse and phouse.get(nm) is not None else None,
                    'details': {
                        'total': round(raw_total, 2),
                        'proportion': prop,
                        'orb_factor': round(orb_fac, 2),
                        'dexter_factor': dexter_factor,
                        'phase_factor': phase_factor,
                        'breakdown': breakdowns.get(nm),
                    }
                })

        # Co-rulership (exaltation/triplicity)
        sr = _sign_rulers_for_cusp(sign or '', day_chart)
        ex_nm, _ = sr.get('exalt', (None, None))
        if ex_nm and ex_nm in totals:
            try:
                w_ex = float((_load_basic_rules().get('governance_weights') or {}).get('exaltation') or 0.4)
            except Exception:
                w_ex = 0.4
            influences.append({
                'planet': ex_nm,
                'type': 'co_rulership',
                'co_kind': 'exaltation',
                'value': round(float(totals[ex_nm]) * w_ex, 2),
                'details': { 'total': round(float(totals[ex_nm]), 2), 'factor': w_ex, 'breakdown': breakdowns.get(ex_nm) },
            })
        trip_nm, _ = sr.get('triplicity', (None, None))
        if trip_nm and trip_nm in totals:
            try:
                w_tri = float((_load_basic_rules().get('governance_weights') or {}).get('triplicity') or 0.3)
            except Exception:
                w_tri = 0.3
            influences.append({
                'planet': trip_nm,
                'type': 'co_rulership',
                'co_kind': 'triplicity',
                'value': round(float(totals[trip_nm]) * w_tri, 2),
                'details': { 'total': round(float(totals[trip_nm]), 2), 'factor': w_tri, 'breakdown': breakdowns.get(trip_nm) },
            })
        # Participating triplicity ruler (weaker)
        try:
            elem = _element_of_sign(sign or '')
            trow = TRIPLICITY.get(elem)
            part_nm = None
            if trow and len(trow) >= 3:
                part_nm = trow[2]
            if part_nm and part_nm in totals and part_nm not in {ex_nm, trip_nm}:
                try:
                    w_tri_p = float((_load_basic_rules().get('governance_weights') or {}).get('triplicity_participating') or 0.15)
                except Exception:
                    w_tri_p = 0.15
                influences.append({
                    'planet': part_nm,
                    'type': 'co_rulership',
                    'co_kind': 'triplicity_participating',
                    'value': round(float(totals[part_nm]) * w_tri_p, 2),
                    'details': { 'total': round(float(totals[part_nm]), 2), 'factor': w_tri_p, 'breakdown': breakdowns.get(part_nm) },
                })
        except Exception:
            pass

        # Rank influences
        influences.sort(key=lambda x: (-float(x.get('value', 0.0)), x.get('type', '')))
        # Dominant / secondary markers relative to top
        if influences:
            top = float(influences[0].get('value') or 0.0)
            for inf in influences:
                v = float(inf.get('value') or 0.0)
                if v >= top * 1.0:
                    inf['rank'] = 'dominant'
                elif v >= top * 0.5:
                    inf['rank'] = 'secondary'
                else:
                    inf['rank'] = 'tertiary'
            # Calibration: promote presence/governance when values are close to top
            try:
                rules = _load_basic_rules()
                cfg = (rules.get('rank_tie_promote') or {})
                close_thresh = float(cfg.get('threshold') or 0.92)
            except Exception:
                close_thresh = 0.92
            for inf in influences:
                try:
                    if inf.get('type') in ('occupation','rulership','co_rulership'):
                        if float(inf.get('value') or 0.0) >= top * close_thresh:
                            inf['rank'] = 'dominant'
                except Exception:
                    continue

        # Build quick tooltips and add keywords for analysis
        for inf in influences:
            try:
                if inf.get('type') == 'occupation':
                    d = inf.get('details') or {}
                    inf['tooltip'] = f"Occupation: ({d.get('total',0)} + {HOUSE_VALUES.get(hnum,0.0)}) × {inf.get('proximity_factor')}"
                elif inf.get('type') == 'rulership':
                    d = inf.get('details') or {}
                    inf['tooltip'] = f"Rulership: {d.get('total',0)} × {d.get('factor',0)} × {inf.get('location_factor')}"
                elif inf.get('type') == 'aspect':
                    d = inf.get('details') or {}
                    inf['tooltip'] = (
                        f"Aspect: {d.get('total',0)} × {d.get('proportion',0)} × {d.get('orb_factor',0)} × "
                        f"{d.get('dexter_factor',1)} × {d.get('phase_factor',1)}"
                    )
                elif inf.get('type') == 'co_rulership':
                    d = inf.get('details') or {}
                    label = inf.get('co_kind','')
                    inf['tooltip'] = f"Co-rule ({label}): {d.get('total',0)} × {d.get('factor',0)}"
            except Exception:
                pass
            # Keywords for synthesis (loaded from Morin dictionary where available)
            try:
                aspect_name = inf.get('aspect') if inf.get('type') == 'aspect' else None
            except Exception:
                aspect_name = None
            try:
                tags: List[str] = []
                # Planet keywords from dictionary
                pnm = str(inf.get('planet'))
                tags += _kw_planet_from_dict(pnm)
                # House keywords from dictionary
                tags += _kw_house_from_dict(hnum)
                # Governance/support tags
                if inf.get('type') == 'rulership':
                    tags += ['governance','dispositorship']
                if inf.get('type') == 'co_rulership':
                    tags += ['support']
                # Aspect keywords
                if aspect_name:
                    tags += _kw_aspect_from_dict(str(aspect_name)) + ['to-cusp']
                # Natural agreement (planet analogue with house)
                try:
                    hkws = _load_morin_keywords().get('houses', {}).get(str(hnum), {})
                    if pnm and pnm in (hkws.get('analog_planets') or []):
                        tags.append('natural_agreement')
                except Exception:
                    pass
                # Dignity tags from pindex dignities list
                try:
                    dlist = [str(x).lower() for x in (pindex.get(pnm, {}).get('dignities') or [])]
                except Exception:
                    dlist = []
                dign_map = {'domicile':'domicile','exaltation':'exaltation','detriment':'detriment','fall':'fall'}
                for key in ('domicile','exaltation','detriment','fall'):
                    if any(key in d for d in dlist):
                        tags.append(key)
                        # Expand with dictionary dignity keywords
                        try:
                            tags += list((_load_morin_keywords().get('dignities', {}) or {}).get(key, []) or [])
                        except Exception:
                            pass
                # Sect tags using computed sect info
                try:
                    sec = compute_sect_info(chart_data) if compute_sect_info else None
                except Exception:
                    sec = None
                try:
                    if isinstance(sec, dict):
                        if pnm == sec.get('benefic_of_sect'):
                            tags.append('sect_benefic')
                            tags += list((_load_morin_keywords().get('sect', {}) or {}).get('benefic_of_sect', []) or [])
                        if pnm == sec.get('malefic_of_sect'):
                            tags.append('malefic_of_sect')
                            tags += list((_load_morin_keywords().get('sect', {}) or {}).get('malefic_out_of_sect', []) or [])
                        # per-planet flags
                        try:
                            row = next((r for r in (sec.get('planets') or []) if str(r.get('planet')) == pnm), None)
                        except Exception:
                            row = None
                        if row:
                            if row.get('in_sect') is True:
                                tags.append('in_sect')
                            elif row.get('in_sect') is False:
                                tags.append('out_of_sect')
                            if row.get('hayz'):
                                tags.append('hayz')
                except Exception:
                    pass
                if inf.get('rank') == 'dominant':
                    tags += ['dominant']
                # unique preserve order
                seen = set(); kw = []
                for t in tags:
                    if t and t not in seen:
                        seen.add(t); kw.append(t)
                inf['keywords'] = kw
            except Exception:
                inf['keywords'] = []

        rows.append({
            'house': hnum,
            'sign': sign,
            'cusp_longitude': round(float(cusp), 2) if (have_cusps and cusp is not None) else None,
            'influences': influences,
            # Optional non-breaking enrichment for UI: per-house Basic Analysis (Morin-style determinations)
            'basic_analysis': _build_basic_analysis(
                hnum=hnum,
                sign=sign,
                cusp=cusp,
                chart_data=chart_data,
                metrics=metrics,
                phouse=phouse,
                pindex=pindex,
                plon=plon,
                totals=totals,
                breakdowns=breakdowns,
                house_rulers=house_rulers,
                house_influences=influences,
            ),
        })

    # Planet strengths summary (top/weak) for prompt enrichment
    strengths_summary: Dict[str, Any] = {}
    try:
        items = []
        for nm, bd in breakdowns.items():
            try:
                items.append({
                    'planet': nm,
                    'total': round(float(totals.get(nm, 0.0)), 2),
                    'dignity': round(float(bd.get('dignity', 0.0) or 0.0), 2),
                    'house_position': round(float(bd.get('house_position', 0.0) or 0.0), 2),
                })
            except Exception:
                continue
        items.sort(key=lambda x: float(x.get('total') or 0.0), reverse=True)
        strengths_summary['top'] = items[:3]
        items_asc = sorted(items, key=lambda x: float(x.get('total') or 0.0))
        strengths_summary['weak'] = items_asc[:3]
    except Exception:
        strengths_summary = {}

    return { 'houses': rows, 'planet_strengths': strengths_summary }


def _build_basic_analysis(
    *,
    hnum: int,
    sign: Optional[str],
    cusp: Optional[float],
    chart_data: Dict[str, Any],
    metrics: Dict[str, Any],
    phouse: Dict[str, int],
    pindex: Dict[str, Dict[str, Any]],
    plon: Dict[str, float],
    totals: Dict[str, float],
    breakdowns: Dict[str, Dict[str, Any]],
    house_rulers: Dict[str, str],
    house_influences: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compose a Basic Analysis layer per house without altering core outputs.

    The analysis follows Morin's hierarchy: Location > Rulership > Aspectual,
    and colors outcomes by simple state modifiers.
    """
    rules = _load_basic_rules()
    # Overview
    ruler_nm = house_rulers.get(str(hnum)) or (SIGN_RULER.get(sign) if isinstance(sign, str) else None)
    ex_nm = EXALTATION.get(sign) if isinstance(sign, str) else None
    # Triplicity depends on sect; approximate with day/night flag when available
    day_chart = None
    try:
        sec = compute_sect_info(chart_data) if compute_sect_info else None
        cs = str(sec.get('chart_sect') or '') if isinstance(sec, dict) else ''
        day_chart = True if cs == 'diurnal' else (False if cs == 'nocturnal' else None)
    except Exception:
        day_chart = None
    tri_nm = None
    try:
        elem = _element_of_sign(sign or '')
        trow = TRIPLICITY.get(elem)
        if trow:
            tri_nm = trow[0] if (day_chart is None or day_chart is True) else trow[1]
    except Exception:
        tri_nm = None
    overview = {
        'priority': rules.get('hierarchy', ['location', 'rulership', 'aspectual']),
        'cusp_sign': sign,
        'ruler': ruler_nm,
        'exaltation': ex_nm,
        'triplicity_ruler': tri_nm,
        'house_system_code': str(chart_data.get('house_system_code') or ''),
    }

    # Location block: planets occupying this house
    location_items: List[Dict[str, Any]] = []
    # Precompute planet status map
    pstatus = metrics.get('planet_status') or {}
    psolar = (metrics.get('solar') or {}).get('conditions') or {}
    for nm, h in phouse.items():
        if int(h) != int(hnum):
            continue
        try:
            bd = breakdowns.get(nm) or {}
            st = pstatus.get(nm, {})
            dignified = bool(st.get('dignified')) or (bd.get('dignity', 0) or 0) >= 4
            afflicted = bool(st.get('afflicted'))
            strong = bool(st.get('strong'))
            cond = psolar.get(nm)
            dignities_list = []
            try:
                digs = pindex.get(nm, {}).get('dignities') or []
                if isinstance(digs, list):
                    dignities_list = [str(x) for x in digs]
            except Exception:
                dignities_list = []
            # Pull up to two strongest aspects to this cusp for this planet (from house_influences)
            cusp_aspects = []
            for inf in house_influences:
                if inf.get('type') == 'aspect' and inf.get('planet') == nm:
                    cusp_aspects.append(inf)
            cusp_aspects.sort(key=lambda x: -abs(float(x.get('value') or 0.0)))
            cusp_aspects = cusp_aspects[:2]
            # Compose summary with Morin-style location emphasis
            domain = _h_domain(hnum)
            nature = _p_nature(nm)
            # Prefer curated examples when available
            def _loc_phrase(planet: str, house: int, favorable: bool) -> str:
                try:
                    for ex in (rules.get('location_examples') or []):
                        if ex.get('planet') == planet and int(ex.get('house')) == int(house):
                            return ex.get('positive') if favorable else ex.get('negative')
                except Exception:
                    pass
                # Fallback phrasing when no curated example; avoid dangling 'via' when nature is empty
                nat = (nature or '').strip()
                if favorable:
                    return f"Enhances {domain}{(' with ' + nat) if nat else ''}."
                return f"Strains {domain}{(' via ' + nat) if nat else ''}."
            favorable = bool(strong and dignified and not afflicted)
            phrase = _loc_phrase(nm, hnum, favorable)
            # Minimal state tags
            tags = []
            if dignified:
                tags.append('dignified')
            if cond:
                tags.append(str(cond))
            if afflicted:
                tags.append('afflicted')
            tag_str = f" {'[' + ', '.join(tags) + ']'}" if tags else ''
            summary = f"{nm} in House {hnum}: {phrase}{tag_str}"
            location_items.append({
                'planet': nm,
                'summary': summary,
                'state': {
                    'strong': strong,
                    'dignified': dignified,
                    'afflicted': afflicted,
                    'solar_condition': cond,
                    'dignities': dignities_list,
                    'total_strength': bd.get('total'),
                },
                'main_aspects_to_cusp': [
                    {
                        'aspect': a.get('aspect'),
                        'orb': a.get('orb'),
                        'phase': a.get('phase'),
                        'dexter': a.get('dexter'),
                        'afflicting': (a.get('aspect') in (rules.get('aspect_notes', {}).get('afflicting') or [])) or (nm in MALEFICS and a.get('aspect') in ('Square','Opposition')),
                    }
                    for a in cusp_aspects
                ],
            })
        except Exception:
            continue

    # Rulership details (for synthesis only; no dedicated section in basic analysis)
    ruler_house = None
    pattern_label = None
    try:
        if ruler_nm:
            ruler_house = phouse.get(ruler_nm)
            key = f"{hnum}-{ruler_house}"
            pattern_label = rules.get('rulership_patterns', {}).get(key)
    except Exception:
        ruler_house = None
        pattern_label = None

    # Aspectual details (for synthesis only; no dedicated section in basic analysis)
    top_aspect = None
    aspect_top_list: List[Dict[str, Any]] = []
    try:
        aitems = [inf for inf in house_influences if inf.get('type') == 'aspect']
        aitems.sort(key=lambda x: -abs(float(x.get('value') or 0.0)))
        if aitems:
            top_aspect = aitems[0]
        # Build top 2 aspect summaries for prompt usage
        for a in aitems[:2]:
            try:
                aname = a.get('aspect')
                nm = a.get('planet')
                try:
                    rules = _load_basic_rules()
                    aff_list = (rules.get('aspect_notes') or {}).get('afflicting') or []
                except Exception:
                    aff_list = ['Square','Opposition']
                is_aff = False
                try:
                    if aname in aff_list:
                        is_aff = True
                    elif nm in MALEFICS and aname in ('Square','Opposition'):
                        is_aff = True
                except Exception:
                    is_aff = False
                aspect_top_list.append({
                    'planet': nm,
                    'aspect': aname,
                    'orb': a.get('orb'),
                    'phase': a.get('phase'),
                    'dexter': a.get('dexter'),
                    'phrase': _aspect_phrase(a),
                    'afflicting': bool(is_aff),
                    'origin_house': a.get('origin_house'),
                    'origin_domain': a.get('origin_domain'),
                })
            except Exception:
                continue
    except Exception:
        top_aspect = None
        aspect_top_list = []

    # Build Determinators panel (UI/text-only)
    def _top_items(kind: str, limit: int = 2):
        items = [inf for inf in house_influences if inf.get('type') == kind]
        items.sort(key=lambda x: -abs(float(x.get('value') or 0.0)))
        return items[:limit]

    presence_top = _top_items('occupation')
    governance_top = (_top_items('rulership') + _top_items('co_rulership'))[:2]
    aspect_top = _top_items('aspect')

    cues: Dict[str, Any] = {}
    try:
        group = _house_group(hnum)
        ang_notes = (rules.get('angularity_notes') or {})
        cues['house_group'] = group
        cues['house_group_note'] = ang_notes.get(group)
    except Exception:
        pass
    try:
        if isinstance(sign, str):
            mod = _modality_of_sign(sign)
            cues['cusp_modality'] = mod
            cues['modality_note'] = (rules.get('modality_notes') or {}).get(mod)
    except Exception:
        pass

    def _aspect_phrase(a: Dict[str, Any]) -> str:
        """Rich aspect phrase including origin, style, condition, and mitigation.

        Uses rules JSON for verbs/adverbs and gracefully falls back to shorter text.
        """
        rules = _load_basic_rules()
        try:
            nm = str(a.get('planet') or '')
            aname = str(a.get('aspect') or '')
            orb = float(a.get('orb') or 999.0)
            phs = (a.get('phase') or '').strip().lower()

            # Phase / dexter / orb band
            aph = (rules.get('aspect_phase_phrases') or {})
            phase_word = aph.get('applying') if phs == 'applying' else (aph.get('separating') if phs == 'separating' else None)
            dex_phrase = (rules.get('dexter') or {}).get('phrase') if bool(a.get('dexter')) else (rules.get('sinister') or {}).get('phrase')
            ob = (rules.get('orb_bands') or {})
            partile_deg = float(ob.get('partile_deg') or 0.5)
            tight_deg = float(ob.get('tight_deg') or 1.5)
            wide_deg = float(ob.get('wide_deg') or 5.0)
            if orb <= partile_deg:
                orb_word = aph.get('partile') or 'precise'
            elif orb <= tight_deg:
                orb_word = 'tight'
            elif orb <= wide_deg:
                orb_word = 'wide'
            else:
                orb_word = None

            # Origin context: house, domain, angularity adverb
            oh = None
            try:
                oh = int(phouse.get(nm)) if nm in phouse else None
            except Exception:
                oh = None
            origin_dom = _h_domain(oh) if oh else None
            og = _house_group(oh) if oh else None
            ang_adv = (rules.get('angularity_adverbs') or {}).get(og) if og else None

            # Planet sign style
            psign = _sign_from_lon(plon.get(nm)) if nm in plon else None
            elem = _element_of_sign(psign) if psign else None
            elem_adj = (rules.get('element_adjectives') or {}).get(elem) if elem else None
            mod = _modality_of_sign(psign) if psign else None
            mod_adj = (rules.get('modality_adjectives') or {}).get(mod) if mod else None

            # Condition: dignity/affliction/sect/solar
            pstat = (metrics.get('planet_status') or {}).get(nm, {})
            dignified = bool(pstat.get('dignified')) or (breakdowns.get(nm, {}).get('dignity', 0) or 0) >= 4
            afflicted = bool(pstat.get('afflicted'))
            malef = nm in MALEFICS
            sect_phrase = None
            try:
                if malef and day_chart is not None:
                    sectp = rules.get('sect_modifiers') or {}
                    sect_phrase = sectp.get('malefic_in_sect') if day_chart else sectp.get('malefic_out_of_sect')
            except Exception:
                sect_phrase = None
            solar_c = None
            try:
                sc = ((metrics.get('solar') or {}).get('conditions') or {}).get(nm)
                if sc:
                    lc = str(sc).lower()
                    sm = rules.get('solar_modifiers') or {}
                    if 'cazimi' in lc:
                        solar_c = sm.get('cazimi')
                    elif 'combust' in lc:
                        solar_c = sm.get('combust')
                    elif 'beam' in lc:
                        solar_c = sm.get('under_beams')
            except Exception:
                solar_c = None

            # Reception by house ruler
            received = None
            try:
                if psign and ruler_nm:
                    if SIGN_RULER.get(psign) == ruler_nm:
                        received = (rules.get('reception_phrases') or {}).get('received_by_house_ruler')
            except Exception:
                received = None

            # Governance ties
            gov_note = None
            try:
                if ruler_nm:
                    if nm == ruler_nm:
                        gov_note = (rules.get('governance_phrases') or {}).get('by_ruler')
                    elif ruler_nm in plon:
                        r_sign = _sign_from_lon(plon.get(ruler_nm))
                        disp = SIGN_RULER.get(r_sign) if r_sign else None
                        if disp and nm == disp:
                            gov_note = (rules.get('governance_phrases') or {}).get('by_dispositor')
            except Exception:
                gov_note = None

            # Planet effect lexicon by aspect polarity
            eff = (rules.get('planet_effects') or {}).get(nm, {})
            harsh = aname in ((rules.get('aspect_notes') or {}).get('afflicting') or []) or (malef and aname in ('Square','Opposition'))
            eff_list = eff.get('harsh' if harsh else 'harmonious') or eff.get('neutral') or []
            effect_word = eff_list[0] if eff_list else ( 'presses on' if harsh else 'supports' )

            # Target domain
            tdom = _h_domain(hnum)

            # Compose
            head_parts = []
            # Origin: planet [in House N (domain)], [cadent/angular...] and [dignified/afflicted]
            origin_bits = []
            origin_bits.append(nm)
            if oh:
                origin_bits.append(f"in House {oh}{(' (' + origin_dom + ')') if origin_dom else ''}")
            cond_bits = []
            if og and ang_adv:
                cond_bits.append(ang_adv)
            if dignified:
                cond_bits.append('dignified')
            elif afflicted:
                cond_bits.append('afflicted')
            if cond_bits:
                origin_bits.append(', ' + ' and '.join(cond_bits))
            head_parts.append(' '.join([b for b in origin_bits if b]))

            # Core aspect clause
            aspect_bits = []
            if phase_word := (aph.get('applying') if phs=='applying' else (aph.get('separating') if phs=='separating' else None)):
                aspect_bits.append(phase_word)
            if bool(a.get('dexter')) and (rules.get('dexter') or {}).get('phrase'):
                aspect_bits.append('dexter')
            aspect_bits.append(aname.lower())
            to_cusp = f"to Cusp {hnum}"
            if orb_word:
                to_cusp += f" ({orb_word} {orb:.1f}°)"

            # Style modifier from sign element/modality
            style_bits = []
            if elem_adj:
                style_bits.append(elem_adj)
            if mod_adj:
                style_bits.append(mod_adj)
            style_phrase = ' '.join(style_bits) if style_bits else None

            # Effect sentence
            effect_clause = f"{effect_word} matters of {tdom}"
            # Secondary clauses
            sec_clauses = []
            if phs == 'applying':
                sec_clauses.append('pressure builds toward perfection')
            elif phs == 'separating':
                sec_clauses.append('effects ease as it recedes')
            if sect_phrase:
                sec_clauses.append(sect_phrase)
            if solar_c:
                sec_clauses.append(solar_c)
            if received:
                sec_clauses.append(received)
            if gov_note:
                sec_clauses.append(gov_note)

            # Join everything
            head = ' '.join([p for p in head_parts if p]).strip()
            core = ' '.join([p for p in aspect_bits if p]) + f" {to_cusp}"
            tail = ': ' + effect_clause
            if style_phrase:
                tail += f" in a {style_phrase} manner"
            if sec_clauses:
                tail += '; ' + '; '.join(sec_clauses)
            return (head + ' ' + core + tail).strip()
        except Exception:
            # Fallback to previous minimal phrasing
            ph = (a.get('phase') or '').strip().lower()
            orb = float(a.get('orb') or 999)
            aname = str(a.get('aspect') or '')
            nm = str(a.get('planet') or '')
            aph = (rules.get('aspect_phase_phrases') or {})
            partile_word = str(aph.get('partile') or 'very strong') if orb <= 1.0 else None
            phase_word = aph.get('applying') if ph == 'applying' else (aph.get('separating') if ph == 'separating' else None)
            dex_phrase = (rules.get('dexter') or {}).get('phrase') if bool(a.get('dexter')) else (rules.get('sinister') or {}).get('phrase')
            str_note = (rules.get('aspect_strength_notes') or {}).get(aname)
            try:
                sign_name = _sign_from_lon(plon.get(nm)) if nm in plon else None
                elem = _element_of_sign(sign_name) if sign_name else None
                mod = ((rules.get('aspect_sign_modifiers') or {}).get(aname) or {}).get(elem) if elem else None
            except Exception:
                mod = None
            parts = [phase_word, ('partile (' + str(partile_word) + ')' if partile_word else None), str_note, mod, dex_phrase]
            bits = [b for b in parts if b]
            return '; '.join(bits) if bits else ''

    def _analogy_label(planet: str) -> Optional[str]:
        try:
            hints = (rules.get('analogy_hints') or {}).get(str(hnum)) or {}
            if planet in (hints.get('support') or []):
                return 'analogical support'
            if planet in (hints.get('contrary') or []):
                return 'contrary to domain'
        except Exception:
            pass
        return None

    def _natural_sig_note(planet: str, via: str) -> Optional[str]:
        try:
            ns = (rules.get('natural_significators') or {}).get(str(hnum)) or []
            if planet in ns:
                return f"relevant here because tied to H{hnum} ({via})"
        except Exception:
            pass
        return None

    rank_adv = rules.get('rank_adverbs') or {}

    determinators_panel = {
        'title': 'Determinators (Morin): Presence → Governance → Aspect',
        'presence': [],
        'governance': [],
        'aspect': [],
    }

    for inf in presence_top:
        nm = str(inf.get('planet'))
        det = {
            'planet': nm,
            'rank': inf.get('rank'),
            'adverb': rank_adv.get(str(inf.get('rank') or ''), ''),
            'value': inf.get('value'),
            'tooltip': inf.get('tooltip'),
            'keywords': inf.get('keywords') or [],
        }
        an = _analogy_label(nm)
        if an:
            det['analogy'] = an
        nsn = _natural_sig_note(nm, 'presence')
        if nsn:
            det['note'] = nsn
        determinators_panel['presence'].append(det)

    for inf in governance_top:
        nm = str(inf.get('planet'))
        det = {
            'planet': nm,
            'type': inf.get('type'),
            'rank': inf.get('rank'),
            'adverb': rank_adv.get(str(inf.get('rank') or ''), ''),
            'value': inf.get('value'),
            'tooltip': inf.get('tooltip'),
            'keywords': inf.get('keywords') or [],
        }
        an = _analogy_label(nm)
        if an:
            det['analogy'] = an
        nsn = _natural_sig_note(nm, 'rulership' if inf.get('type') == 'rulership' else 'co-rulership')
        if nsn:
            det['note'] = nsn
        determinators_panel['governance'].append(det)

    for inf in aspect_top[:2]:
        nm = str(inf.get('planet'))
        det = {
            'planet': nm,
            'aspect': inf.get('aspect'),
            'orb': inf.get('orb'),
            'phase': inf.get('phase'),
            'rank': inf.get('rank'),
            'adverb': rank_adv.get(str(inf.get('rank') or ''), ''),
            'value': inf.get('value'),
            'tooltip': inf.get('tooltip'),
            'keywords': inf.get('keywords') or [],
            'phrase': _aspect_phrase(inf),
        }
        nsn = _natural_sig_note(nm, 'aspect')
        if nsn:
            det['note'] = nsn
        determinators_panel['aspect'].append(det)

    route_bits = []
    dom = _h_domain(hnum)
    if presence_top:
        p0 = presence_top[0]
        route_bits.append(f"by presence {p0.get('planet')} ({p0.get('rank')})")
    if ruler_nm:
        if ruler_house:
            route_bits.append(f"by governance {ruler_nm} (ruler in H{ruler_house})")
        else:
            route_bits.append(f"by governance {ruler_nm}")
    if aspect_top:
        a0 = aspect_top[0]
        a_phrase = _aspect_phrase(a0)
        route_bits.append(f"by aspect {a0.get('planet')} {str(a0.get('aspect')).lower()} {('to cusp; ' + a_phrase) if a_phrase else 'to cusp'}")
    route_line = f"H{hnum} ({dom}): " + "; ".join(route_bits)

    conflicts: List[str] = []
    try:
        favorable_loc = False
        if presence_top:
            nm0 = str(presence_top[0].get('planet'))
            st0 = metrics.get('planet_status', {}).get(nm0, {})
            favorable_loc = bool(st0.get('strong')) and (bool(st0.get('dignified')) or (breakdowns.get(nm0, {}).get('dignity', 0) or 0) >= 4) and not bool(st0.get('afflicted'))
        if aspect_top:
            a0 = aspect_top[0]
            aname = a0.get('aspect')
            aff = (aname in (rules.get('aspect_notes', {}).get('afflicting') or [])) or (str(a0.get('planet')) in MALEFICS and aname in ('Square','Opposition'))
            if favorable_loc and aff:
                phrase = (rules.get('contradiction_phrases') or {}).get('good_loc_bad_aspect') or 'Favorable occupation but applying affliction to cusp → mixed.'
                conflicts.append(phrase)
            elif (not aff) and str(a0.get('planet')) in BENEFICS:
                phrase = (rules.get('contradiction_phrases') or {}).get('benefic_supports') or 'Benefic trine/sextile to cusp mitigates difficulties.'
                conflicts.append(phrase)
            # Additional nuanced patterns
            try:
                occ_planet = str(presence_top[0].get('planet')) if presence_top else None
                occ_status = metrics.get('planet_status', {}).get(occ_planet or '', {}) if occ_planet else {}
                occ_dignified = bool(occ_status.get('dignified')) or (breakdowns.get(occ_planet or '', {}).get('dignity', 0) or 0) >= 4
                occ_malef = occ_planet in MALEFICS
                occ_benef = occ_planet in BENEFICS
                asp_pl = str(a0.get('planet'))
                is_benefic_aspect = (aname in (rules.get('aspect_notes', {}).get('favorable') or [])) or (asp_pl in BENEFICS and aname in ('Trine','Sextile'))
                is_malefic_affliction = (aname in (rules.get('aspect_notes', {}).get('afflicting') or [])) and (asp_pl in MALEFICS)
                # Dignified malefic in house but benefic aspect to cusp
                if occ_planet and occ_malef and occ_dignified and is_benefic_aspect:
                    phrase = (rules.get('contradiction_phrases') or {}).get('dignified_malefic_benefic_aspect') or 'Powerful malefic present; benefic aspect to cusp tempers severity.'
                    conflicts.append(phrase)
                # Benefic occupant but malefic affliction to cusp
                if occ_planet and occ_benef and is_malefic_affliction:
                    phrase = (rules.get('contradiction_phrases') or {}).get('benefic_occupant_malefic_affliction') or 'Benefic occupant, yet malefic affliction to cusp introduces strain.'
                    conflicts.append(phrase)
            except Exception:
                pass
    except Exception:
        pass

    primary = None
    prim_meta = None
    try:
        if house_influences:
            primary = max(house_influences, key=lambda x: abs(float(x.get('value') or 0.0)))
        if primary:
            pnm = str(primary.get('planet'))
            stp = metrics.get('planet_status', {}).get(pnm, {})
            benefic = (rules.get('planets', {}).get(pnm, {}).get('benefic'))
            prim_meta = {
                'planet': pnm,
                'type': primary.get('type'),
                'value': primary.get('value'),
                'benefic': benefic,
                'dignified': bool(stp.get('dignified')) or (breakdowns.get(pnm, {}).get('dignity', 0) or 0) >= 4,
                'afflicted': bool(stp.get('afflicted')),
            }
    except Exception:
        prim_meta = None

    # Synthesis bullets
    synthesis: List[str] = []
    # 1) Location-driven points
    for li in location_items[:2]:
        nm = li.get('planet')
        state = li.get('state') or {}
        good = bool(state.get('strong')) and bool(state.get('dignified')) and not bool(state.get('afflicted'))
        dom = _h_domain(hnum)
        if good:
            synthesis.append(f"{nm} directly determines House {hnum} ({dom}) toward favorable outcomes when well disposed.")
        else:
            synthesis.append(f"{nm} presses on House {hnum} ({dom}); debility or affliction warns of difficulties.")
    # 2) Rulership binding
    if ruler_nm and ruler_house:
        if pattern_label:
            synthesis.append(f"Ruler of {hnum} in {ruler_house} — {pattern_label}.")
        else:
            synthesis.append(f"Ruler of {hnum} in {ruler_house} routes { _h_domain(hnum) } via { _h_domain(int(ruler_house)) } (secondary).")
    # 3) Aspectual emphasis
    if top_aspect:
        try:
            # Use enriched Morin-style phrasing for aspect to cusp
            enrich = _aspect_phrase(top_aspect)
            if enrich:
                synthesis.append(enrich)
            else:
                # Fallback to legacy brief phrasing
                afflicting = (top_aspect.get('aspect') in (rules.get('aspect_notes', {}).get('afflicting') or [])) or (str(top_aspect.get('planet')) in MALEFICS and top_aspect.get('aspect') in ('Square','Opposition'))
                synthesis.append(f"Applying {str(top_aspect.get('aspect')).lower()} from {top_aspect.get('planet')} to Cusp {hnum} {'intensifies challenges' if afflicting else 'supports outcomes'}.")
            # Mitigation injection: malefic afflicting but dignified
            try:
                pnm = str(top_aspect.get('planet'))
                afflicting2 = (top_aspect.get('aspect') in (rules.get('aspect_notes', {}).get('afflicting') or [])) or (pnm in MALEFICS and top_aspect.get('aspect') in ('Square','Opposition'))
                if pnm in MALEFICS and afflicting2:
                    stp = metrics.get('planet_status', {}).get(pnm, {})
                    dignified = bool(stp.get('dignified')) or (breakdowns.get(pnm, {}).get('dignity', 0) or 0) >= 4
                    if dignified:
                        mphrase = (rules.get('mitigation_rules') or {}).get('malefic_good_state')
                        if mphrase:
                            synthesis.append(mphrase)
            except Exception:
                pass
        except Exception:
            pass

    # Ruler Dependency Map (sign tone + routing + up to two conditions + optional dispositor line)
    ruler_map = None
    try:
        if ruler_nm and isinstance(sign, str):
            rguide = rules.get('ruler_dependency_guide') or {}
            traits = ((rguide.get('sign_traits') or {}).get(sign)) or {}
            tones = traits.get('tone') or []
            tone_str = ', '.join([t for t in (tones if isinstance(tones, list) else [])[:2]])
            tmpl = (rguide.get('templates') or {})
            # Baseline
            base_line = None
            if tmpl.get('baseline'):
                try:
                    base_line = str(tmpl.get('baseline')).format(sign=sign, house=hnum, tone=tone_str or 'characteristic')
                except Exception:
                    base_line = None
            # Route via ruler house with rulership pattern
            route_line_map = None
            if tmpl.get('route') and ruler_house:
                try:
                    route_label = pattern_label or _h_domain(int(ruler_house))
                    route_line_map = str(tmpl.get('route')).format(ruler=ruler_nm, ruler_house=ruler_house, routing_label=route_label)
                except Exception:
                    route_line_map = None
            # Condition candidates — show at most two
            cond_lines: List[str] = []
            try:
                st = metrics.get('planet_status', {}).get(ruler_nm, {})
                bd = breakdowns.get(ruler_nm, {})
                dign_list = []
                try:
                    dign_list = [str(x).lower() for x in (pindex.get(ruler_nm, {}).get('dignities') or [])]
                except Exception:
                    dign_list = []
                dignified = bool(st.get('dignified')) or (bd.get('dignity', 0) or 0) >= 4 or ('domicile' in dign_list or 'exaltation' in dign_list or 'triplicity' in dign_list)
                debilitated = ('detriment' in dign_list or 'fall' in dign_list) or (bd.get('dignity', 0) or 0) <= -4
                # Angularity of ruler
                hgrp = None
                try:
                    if ruler_house:
                        hgrp = _house_group(int(ruler_house))
                except Exception:
                    hgrp = None
                # Motion/solar
                retro = False
                try:
                    retro = bool(pindex.get(ruler_nm, {}).get('retrograde'))
                except Exception:
                    retro = False
                solar_cond = None
                try:
                    solar_cond = (metrics.get('solar') or {}).get('conditions', {}).get(ruler_nm)
                except Exception:
                    solar_cond = None
                # Assemble in priority order; stop at 2
                if dignified and len(cond_lines) < 2 and tmpl.get('dignified'):
                    cond_lines.append(str(tmpl.get('dignified')))
                if debilitated and len(cond_lines) < 2 and tmpl.get('debilitated'):
                    cond_lines.append(str(tmpl.get('debilitated')))
                if retro and len(cond_lines) < 2 and tmpl.get('retrograde'):
                    cond_lines.append(str(tmpl.get('retrograde')))
                if solar_cond and len(cond_lines) < 2:
                    lc = str(solar_cond).strip().lower()
                    if lc.startswith('combust') and tmpl.get('combust'):
                        cond_lines.append(str(tmpl.get('combust')))
                    elif lc.startswith('under') and 'beam' in lc and tmpl.get('under_beams'):
                        cond_lines.append(str(tmpl.get('under_beams')))
                    elif lc.startswith('cazimi') and tmpl.get('cazimi'):
                        cond_lines.append(str(tmpl.get('cazimi')))
                if hgrp and len(cond_lines) < 2:
                    if hgrp == 'angular' and tmpl.get('angular'):
                        cond_lines.append(str(tmpl.get('angular')))
                    elif hgrp == 'cadent' and tmpl.get('cadent'):
                        cond_lines.append(str(tmpl.get('cadent')))
                    elif hgrp == 'succedent' and tmpl.get('succedent'):
                        cond_lines.append(str(tmpl.get('succedent')))
            except Exception:
                cond_lines = []
            # Dispositor (only when differs from ruler)
            chain_line = None
            try:
                if ruler_nm in plon:
                    r_sign = _sign_from_lon(plon.get(ruler_nm))
                    disp = SIGN_RULER.get(r_sign) if r_sign else None
                    if disp and disp != ruler_nm:
                        ctmpl = (rguide.get('chain_template'))
                        if ctmpl:
                            chain_line = str(ctmpl).format(ruler=ruler_nm, dispositor=disp)
            except Exception:
                chain_line = None
            # Append assembled lines
            for line in [base_line, route_line_map]:
                if line:
                    synthesis.append(line)
            for line in cond_lines[:2]:
                synthesis.append(line)
            if chain_line:
                synthesis.append(chain_line)
            ruler_map = {
                'baseline': base_line,
                'route': route_line_map,
                'conditions': cond_lines[:2],
                'dispositor': chain_line,
            }
    except Exception:
        ruler_map = None

    return {
        'label': 'Basic Analysis',
        'overview': overview,
        'location': location_items,
        'synthesis': synthesis,
        'ruler_map': ruler_map,
        'aspect_top': aspect_top_list,
        'determinators_panel': determinators_panel,
        'route_line': route_line,
        'cues': cues,
        'conflicts': conflicts,
        'primary_determinator': prim_meta,
    }
