# -*- coding: utf-8 -*-
"""
Morin-style Transits to Natal

Computes Morin latitude-corrected aspects from transiting planets
to a fixed natal chart (Sun–Saturn scope). Reuses geometry from
backend/morin_aspects.py. This module is engine-agnostic: it consumes
serialized natal chart_data (with planet longitudes and latitudes)
and a transit timestamp (ISO), returning rows suitable for frontend display.

Reference helper: Implementing the astrological logic.txt
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional, Set, Deque
from datetime import datetime, timezone, timedelta
import math
import collections
import logging

from swisseph_state import swisseph as swe

logger = logging.getLogger(__name__)

_PARTILE_ORB_DEG = 1.0

# Reuse Morin helpers (underscore utilities are module-private but importable)
from morin_aspects import (
    CLASSICAL,
    ORB_OF_VIRTUE,
    ASPECT_SET,
    _jd_from_iso,
    _lon_lat_at,
    _semi_diameter_deg,
    _sph_to_vec,
    _unit,
    _rotate,
    _angular_sep_deg,
    _build_plane_normal,
    _apparent_inclination,
    _dexter_sinister,
)
from astro_clock_metrics import compute_metrics
from house_influence import compute_house_influences
from determinations import compute_determinations
try:
    from horary_engine.engine import HoraryEngine  # type: ignore
except Exception:  # pragma: no cover
    HoraryEngine = None  # type: ignore
try:
    from primary_directions import compute_primary_direction_windows  # type: ignore
except Exception:  # pragma: no cover
    compute_primary_direction_windows = None  # type: ignore

try:
    # Context helpers for SR/LR
    from context_layers import compute_solar_return_timestamp, compute_nearest_lunar_return  # type: ignore
except Exception:  # pragma: no cover
    compute_solar_return_timestamp = None  # type: ignore
    compute_nearest_lunar_return = None  # type: ignore

try:
    from revolution_cache import get_revolution_context  # type: ignore
except Exception:  # pragma: no cover
    get_revolution_context = None  # type: ignore


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _parse_iso_datetime_utc(value: Any) -> datetime:
    """Parse an ISO instant, applying the API convention that naive means UTC."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("ISO datetime must be a non-empty string")
    parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_partile_orb(orb: Any) -> bool:
    """Return whether an aspect is within the product's one-degree partile band."""
    try:
        value = abs(float(orb))
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and value <= _PARTILE_ORB_DEG


def _norm360(x: float) -> float:
    return x % 360.0


def _antiscia_lon(lon: float) -> float:
    """Return the antiscia longitude around the Cancer/Capricorn axis.

    Formula: antiscion(λ) = (180° - λ) mod 360°
    """
    return (180.0 - float(lon)) % 360.0

def _contra_antiscia_lon(lon: float) -> float:
    """Return the contra-antiscia longitude around the Aries/Libra axis.

    Formula: contra(λ) = (360° - λ) mod 360°
    """
    return (360.0 - float(lon)) % 360.0


_SIGN_NAMES = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces',
]

_SIGN_RULERS: Dict[str, List[str]] = {
    'Aries': ['Mars'],
    'Taurus': ['Venus'],
    'Gemini': ['Mercury'],
    'Cancer': ['Moon'],
    'Leo': ['Sun'],
    'Virgo': ['Mercury'],
    'Libra': ['Venus'],
    'Scorpio': ['Mars'],
    'Sagittarius': ['Jupiter'],
    'Capricorn': ['Saturn'],
    'Aquarius': ['Saturn'],
    'Pisces': ['Jupiter'],
}

_SIGN_EXALTATIONS: Dict[str, List[str]] = {
    'Aries': ['Sun'],
    'Taurus': ['Moon'],
    'Gemini': [],
    'Cancer': ['Jupiter'],
    'Leo': [],
    'Virgo': ['Mercury'],
    'Libra': ['Saturn'],
    'Scorpio': [],
    'Sagittarius': [],
    'Capricorn': ['Mars'],
    'Aquarius': [],
    'Pisces': ['Venus'],
}


def _sign_from_lon(lon: float) -> str:
    d = _norm360(float(lon))
    idx = int(d // 30) % 12
    return _SIGN_NAMES[idx]


def _sign_rulers_for(sign: str) -> Set[str]:
    sign_norm = str(sign).title()
    rulers = _SIGN_RULERS.get(sign_norm, [])
    exalts = _SIGN_EXALTATIONS.get(sign_norm, [])
    return {r for r in rulers + exalts if r}




def _aspect_short(name: str) -> str:
    try:
        k = (name or '').strip().lower()
    except Exception:
        k = ''
    if 'conj' in k: return 'Conj'
    if 'opp' in k: return 'Opp'
    if 'square' in k: return 'Sq'
    if 'trine' in k: return 'Tri'
    if 'sex' in k: return 'Sex'
    if 'semi' in k: return 'Semi'
    if 'quin' in k: return 'Qnx'
    return name or ''


def _classify_quality(transiting: str, aspect: str) -> str:
    """Simplified quality classifier from planetary nature + aspect family.

    Returns one of: 'benefic' | 'malefic' | 'mixed'.
    """
    try:
        fam = _aspect_hard_soft(aspect)
    except Exception:
        fam = 'other'
    if transiting in ('Jupiter', 'Venus'):
        return 'benefic' if fam in ('soft', 'conj') else 'mixed'
    if transiting in ('Saturn', 'Mars'):
        return 'malefic' if fam in ('hard', 'conj') else 'mixed'
    return 'mixed'


def _estimate_effective_window(
    ts_iso: str,
    sep_now: float,
    sep_future: float,
    dt_days: float,
    max_orb: float,
    transiting: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Estimate Morin's partile activation window around an exact transit.

    Book 24, chapter 13 gives the Moon six hours before and after the
    partile transit and the other planets one day before and after.  The
    exact instant is estimated from the local separation slope.  A nearly
    stationary separation has no defensible linear exact-time estimate, so
    it returns ``None`` instead of inventing an arbitrary window.

    ``max_orb`` remains in the signature because it is part of the caller's
    hit geometry, but it is deliberately not used as the activation
    half-width.  The wider platic orb and Morin's short partile activation
    period are different concepts.
    """
    try:
        t0 = _parse_iso_datetime_utc(str(ts_iso))
        step_days = float(dt_days)
        current_sep = abs(float(sep_now))
        future_sep = abs(float(sep_future))
        if (
            not math.isfinite(step_days)
            or not math.isfinite(current_sep)
            or not math.isfinite(future_sep)
            or step_days <= 0.0
            or float(max_orb) <= 0.0
        ):
            return None
        rate = (future_sep - current_sep) / step_days
        rate_abs = abs(rate)
        if not math.isfinite(rate_abs) or rate_abs < 1e-6:
            return None
        center_offset_days = -current_sep / rate
        if not math.isfinite(center_offset_days):
            return None
        center = t0 + timedelta(days=center_offset_days)
        half_width = timedelta(hours=6 if str(transiting or '') == 'Moon' else 24)
        return {
            'start': (center - half_width).isoformat(),
            'end': (center + half_width).isoformat(),
            'exact_estimate': center.isoformat(),
            'basis': 'morin_partile_activation',
        }
    except Exception:
        return None


def _normalize_planets(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw = chart_data.get('planets') or {}
    idx: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        for nm, row in raw.items():
            if isinstance(row, dict):
                r = dict(row)
                r.setdefault('planet', nm)
                idx[str(nm)] = r
    elif isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict) and row.get('planet'):
                idx[str(row['planet'])] = row
    return idx


def _natal_house_map(chart_data: Dict[str, Any]) -> Dict[str, Optional[int]]:
    idx = _normalize_planets(chart_data)
    out: Dict[str, Optional[int]] = {}
    for nm, row in idx.items():
        try:
            h = row.get('house')
            out[nm] = int(h) if h is not None else None
        except Exception:
            out[nm] = None
    return out


def _house_rulers_map(chart_data: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        hr = chart_data.get('house_rulers') or {}
        if isinstance(hr, dict):
            for k, v in hr.items():
                key = str(k)
                try:
                    val = v if isinstance(v, str) else getattr(v, 'value', None) or str(v)
                except Exception:
                    val = str(v)
                out[key] = val
    except Exception:
        pass
    return out


def _extract_birth_datetime(chart_data: Dict[str, Any]) -> Optional[datetime]:
    """Return natal datetime (UTC) if present."""
    if not isinstance(chart_data, dict):
        return None
    direct_keys = ['datetime', 'timestamp', 'birth_datetime', 'natal_datetime', 'original_datetime']
    for key in direct_keys:
        val = chart_data.get(key)
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    metadata = chart_data.get('metadata')
    if isinstance(metadata, dict):
        for key in ('birth_iso', 'original_birth_iso', 'datetime'):
            val = metadata.get(key)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
    date_val = chart_data.get('date')
    time_val = chart_data.get('time')
    if isinstance(date_val, str):
        iso = f"{date_val}T{time_val or '00:00:00'}"
        try:
            dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _extract_cusps(chart_data: Dict[str, Any]) -> List[float]:
    try:
        hc = chart_data.get('houses') or chart_data.get('house_cusps') or []
        if isinstance(hc, list):
            vals = [float(x) for x in hc[:12]]
            if len(vals) < 12:
                vals = vals + [0.0] * (12 - len(vals))
            return vals
    except Exception:
        pass
    return [0.0] * 12


def _house_from_cusps(lon: float, cusps: List[float]) -> int:
    """Return 1..12 house index for a longitude using cusp arcs (CCW, wrap)."""
    if not cusps or len(cusps) < 12:
        return 1
    lon = _norm360(lon)
    for i in range(12):
        a = _norm360(cusps[i])
        b = _norm360(cusps[(i + 1) % 12])
        if a <= b:
            if a <= lon < b:
                return i + 1
        else:
            if lon >= a or lon < b:
                return i + 1
    return 1


def _extract_pof(chart_data: Dict[str, Any]) -> Optional[float]:
    """Best-effort extraction of Part of Fortune longitude from natal chart_data.

    Tries common locations: chart_data['arabic_parts'] or chart_data['parts'] dicts.
    Returns None if not found or invalid.
    """
    try:
        for key in ('arabic_parts', 'parts', 'lots'):
            val = chart_data.get(key)
            if isinstance(val, dict):
                # try several common names
                for k, v in val.items():
                    name = str(k).lower()
                    if 'fortune' in name:
                        try:
                            lon = float(v.get('longitude')) if isinstance(v, dict) else float(v)
                            return _norm360(lon)
                        except Exception:
                            continue
    except Exception:
        return None
    return None


def _angularity_bonus(h: Optional[int]) -> float:
    if h in (1, 4, 7, 10):
        return 1.5
    if h in (2, 5, 8, 11):
        return 0.5
    return 0.0


_SLOW_WEIGHT: Dict[str, float] = {
    'Saturn': 3.0,
    'Jupiter': 2.5,
    'Mars': 2.0,
    'Sun': 1.0,
    'Venus': 1.0,
    'Mercury': 1.0,
    'Moon': 0.8,
}

_SIMULTANEOUS_HORIZON_DAYS = 2.5  # days; per-planet windows applied when evaluating
_SUCCESSIVE_HORIZON_DAYS = 35.0   # days; covers Morin's "short interval" requirement
_SR_LR_MEMO: Dict[tuple, Dict[str, Any]] = {}
_SR_LR_MEMO_MAX = 64
_CLUSTER_MIN_COUNT = 3


def _new_transit_registry_context() -> Dict[str, Dict[str, Deque[Dict[str, Any]]]]:
    """Create isolated history for one exact calculation or window scan.

    Transit history is natal- and request-specific.  Keeping these registries
    at module scope allowed unrelated charts and concurrent users to affect one
    another's multiple/successive-transit multipliers.
    """
    return {
        'simultaneous': collections.defaultdict(collections.deque),
        'malefic': collections.defaultdict(collections.deque),
    }

_POSITIVE_DOMAINS = {
    'life', 'character', 'intellect', 'wealth', 'money', 'relationships', 'marriage',
    'children', 'pleasure', 'honors', 'friends', 'belief', 'long_travel', 'home',
    'siblings', 'relatives'
}
_NEGATIVE_DOMAINS = {
    'danger', 'death', 'illness', 'health', 'prison', 'servitude', 'shared_resources',
    'conflict', 'violence', 'enemy', 'hidden_enemies'
}

_DOMAIN_POLARITY: Dict[str, int] = {}
for _dom in _POSITIVE_DOMAINS:
    _DOMAIN_POLARITY[_dom] = 1
for _dom in _NEGATIVE_DOMAINS:
    _DOMAIN_POLARITY[_dom] = -1
_DOMAIN_POLARITY.update({
    'health': -1,
    'illness': -1,
    'illness_chronic': -1,
    'illness_acute': -1,
    'secrets': -1,
    'hidden': -1,
    'hidden_enemies': -1,
    'servitude': -1,
    'shared': -1,
    'accident': -1,
    'loss': -1,
    'enemy': -1,
    'conflict': -1,
    'violence': -1,
    'body': 1,
    'career': 1,
    'money': 1,
    'belief': 1,
    'friends': 1,
    'children': 1,
    'home': 1,
    'siblings': 1,
    'relatives': 1,
    'service': -1,
    'prison': -1,
    'long_travel': 1,
})

_DOMAIN_PRIMARY_HOUSE: Dict[str, int] = {
    'life': 1,
    'character': 1,
    'intellect': 1,
    'wealth': 2,
    'money': 2,
    'siblings': 3,
    'relatives': 3,
    'contracts': 7,
    'short_travel': 3,
    'home': 4,
    'parents': 4,
    'inheritance': 4,
    'children': 5,
    'pleasure': 5,
    'service': 6,
    'health': 6,
    'relationships': 7,
    'marriage': 7,
    'conflict': 7,
    'danger': 8,
    'death': 8,
    'shared_resources': 8,
    'belief': 9,
    'long_travel': 9,
    'honors': 10,
    'friends': 11,
    'hopes': 11,
    'prison': 12,
    'hidden_enemies': 12,
}

_PLANET_NATURE_DOMAINS: Dict[str, Set[str]] = {
    'Sun': {'honors', 'life', 'authority'},
    'Moon': {'life', 'home', 'children', 'marriage'},
    'Mercury': {'intellect', 'short_travel', 'contracts'},
    'Venus': {'relationships', 'marriage', 'pleasure', 'wealth'},
    'Mars': {'conflict', 'danger', 'death', 'violence', 'shared_resources'},
    'Jupiter': {'wealth', 'honors', 'belief', 'freedom'},
    'Saturn': {'illness', 'prison', 'servitude', 'danger', 'death', 'disgrace'},
}

_EVENT_TAG_MAP: Dict[str, str] = {
    'life': 'life',
    'health': 'illness',
    'danger': 'danger',
    'death': 'death',
    'shared_resources': 'shared_resources',
    'honors': 'honor',
    'wealth': 'wealth',
    'relationships': 'relationships',
    'marriage': 'partnership',
    'conflict': 'conflict',
    'pleasure': 'pleasure',
    'friends': 'friends',
    'home': 'home',
    'children': 'children',
    'short_travel': 'journeys',
    'belief': 'belief',
    'secrets': 'secrets',
    'hidden_enemies': 'hidden enemies',
    'prison': 'imprisonment',
}

_DOMAIN_SYNONYMS: Dict[str, str] = {
    'illness': 'health',
    'illness_chronic': 'health',
    'illness_acute': 'health',
    'disease': 'health',
    'sickness': 'health',
    'fever': 'health',
    'injury': 'danger',
    'accident': 'danger',
    'peril': 'danger',
    'violence': 'danger',
    'wounds': 'danger',
    'career': 'honors',
    'profession': 'honors',
    'actions': 'honors',
    'undertakings': 'honors',
    'dignities': 'honors',
    'dignity': 'honors',
    'position': 'honors',
    'prestige': 'honors',
    'fame': 'honors',
    'glory': 'honors',
    'renown': 'honors',
    'repute': 'honors',
    'illustrious': 'honors',
    'authority': 'honors',
    'king': 'honors',
    'kings': 'honors',
    'queen': 'honors',
    'queens': 'honors',
    'sovereign': 'honors',
    'sovereigns': 'honors',
    'finances': 'wealth',
    'fortune': 'wealth',
    'riches': 'wealth',
    'inheritance': 'shared_resources',
    'paternal inheritance': 'shared_resources',
    'travel': 'long_travel',
    'journey': 'long_travel',
    'journeys': 'long_travel',
    'travels': 'long_travel',
    'abroad': 'long_travel',
    'long_journey': 'long_travel',
    'long_journeys': 'long_travel',
    'religion': 'belief',
    'sacred': 'belief',
    'spirituality': 'belief',
    'faith': 'belief',
    'freedom': 'belief',
    'lawsuit': 'conflict',
    'lawsuits': 'conflict',
    'litigation': 'conflict',
    'quarrel': 'conflict',
    'quarrels': 'conflict',
    'conflicts': 'conflict',
    'war': 'conflict',
    'open enemies': 'conflict',
    'enemies': 'conflict',
    'hidden enemies': 'hidden_enemies',
    'secret enemies': 'hidden_enemies',
    'servants': 'service',
    'household': 'service',
    'domestics': 'service',
    'animals': 'service',
    'servitude': 'prison',
    'captivity': 'prison',
    'incarceration': 'prison',
    'prison': 'prison',
    'exile': 'prison',
    'disgrace': 'prison',
    'dishonor': 'prison',
    'catastrophe': 'prison',
    'siblings': 'siblings',
    'brothers': 'siblings',
    'sisters': 'siblings',
    'relatives': 'relatives',
    'kin': 'relatives',
    'parents': 'home',
    'father': 'home',
    'mother': 'home',
    'motherhood': 'home',
    'temperament': 'life',
    'character': 'life',
    'habits': 'life',
    'ability': 'life',
    'mind': 'intellect',
    'mental qualities': 'intellect',
    'intelligence': 'intellect',
    'disposition': 'life',
    'constitution': 'life',
    'wife': 'marriage',
    'husband': 'marriage',
    'spouse': 'marriage',
    'partner': 'marriage',
    'contracts': 'relationships',
    'agreements': 'relationships',
    'pacts': 'relationships',
    'pleasures': 'pleasure',
    'games': 'pleasure',
    'entertainments': 'pleasure',
    'friends': 'friends',
    'allies': 'friends',
    'hopes': 'hopes',
    'expectations': 'hopes',
    'squandering': 'shared_resources',
    'daring': 'danger',
    'animals': 'service',
    'household affairs': 'service',
    'service': 'service',
    'domestic': 'service',
    'contracts and agreements': 'relationships',
    'conflict': 'conflict',
}

_HOUSE_DEFAULT_DOMAIN: Dict[int, str] = {
    1: 'life',
    2: 'wealth',
    3: 'siblings',
    4: 'home',
    5: 'children',
    6: 'service',
    7: 'relationships',
    8: 'death',
    9: 'belief',
    10: 'honors',
    11: 'friends',
    12: 'hidden_enemies',
}

_HOUSE_CONTEXT_DOMAINS: Dict[int, Tuple[str, ...]] = {
    1: ('life', 'character'),
    2: ('wealth', 'money'),
    3: ('siblings', 'relatives', 'short_travel'),
    4: ('home', 'parents'),
    5: ('children', 'pleasure'),
    6: ('service', 'health'),
    # Morin treats the 7th as a mixed house: marriage/contracts/lawsuits/open enemies.
    7: ('relationships', 'marriage', 'conflict'),
    8: ('death', 'danger', 'shared_resources'),
    9: ('belief', 'long_travel'),
    10: ('honors',),
    11: ('friends', 'hopes'),
    12: ('hidden_enemies', 'prison', 'health', 'secrets'),
}

_DOMAIN_PRIMARY_HOUSE['secrets'] = 12

_RAW_KEYWORD_DOMAIN_MAP: Dict[str, str] = {
    'Body': 'life',
    'Career': 'honors',
    'Money': 'wealth',
    'Health': 'health',
    'Home': 'home',
    'Children': 'children',
    'Travel': 'short_travel',
    'Belief': 'belief',
    'Relationship': 'relationships',
    'Friends': 'friends',
    'Hidden': 'secrets',
    'Shared': 'shared_resources',
    'Asc': 'life',
    'MC': 'honors',
}

_CONSERVATIVE_DOMAIN_TOKENS: Set[str] = (
    set(_DOMAIN_PRIMARY_HOUSE.keys())
    | set(_DOMAIN_POLARITY.keys())
    | {'career', 'money', 'belief', 'friends', 'children', 'home', 'relationships', 'secrets'}
)

_CONFLICT_DOMAIN_HINTS: Set[str] = {
    'attack_violence',
    'conflict',
    'enemy',
    'enemy_attack',
    'internal_conflict_war',
    'lawsuit',
    'legal_defeat',
    'legal_resolution',
    'legal_victory',
    'major_lawsuit_initiated',
    'quarrel',
    'relationship_conflict',
    'settlement',
    'violent_confrontation',
    'war',
    'war_declaration_offensive',
    'war_response_defensive',
    'warfare_involvement',
}
_DANGER_DOMAIN_HINTS: Set[str] = {
    'accident_major',
    'danger',
    'death_natural',
    'death_violent',
    'death_threat_high',
    'death_threat_moderate',
    'drowning_submersion',
    'fall_from_height',
    'fire_burn',
    'injury_accident',
    'injury_risk',
    'life_threatening_accident',
    'near_death_experience',
    'travel_accident',
}
_MARRIAGE_DOMAIN_HINTS: Set[str] = {
    'bride',
    'engagement',
    'groom',
    'husband',
    'marriage',
    'marriage_likely',
    'matrimony',
    'spouse',
    'wedding',
    'wedlock',
    'wife',
}
_RELATIONSHIP_DOMAIN_HINTS: Set[str] = {
    'agreement',
    'agreements',
    'contracts',
    'partnership',
    'partnership_strengthened',
    'partnership_strained',
    'relationship',
    'relationships',
    'significant_partnership',
}
_HIDDEN_DOMAIN_HINTS: Set[str] = {
    'hidden_enemies',
    'secret_enemies',
    'secrets',
}
_PRISON_DOMAIN_HINTS: Set[str] = {
    'arrest_imprisonment',
    'captivity',
    'disgrace',
    'exile_or_forced_travel',
    'imprisonment_risk',
    'prison',
}
_DOMESTIC_ADVERSE_EVENT_HINTS: Set[str] = {
    'argument',
    'disagreement',
    'domestic_discord',
    'domestic_disruption',
    'estrangement',
    'family_conflict',
    'family_dispute',
    'family_fight',
    'family_problems',
    'family_strife',
    'family_tension',
    'feud',
    'household_conflict',
    'household_strife',
    'rift',
}
_RELATIONSHIP_ADVERSE_EVENT_HINTS: Set[str] = {
    'betrayal',
    'divorce',
    'divorce_or_separation',
    'friendship_loss',
    'partnership_strained',
    'relationship_crisis',
    'separation',
}
_ADVERSE_STEP_HINTS: Set[str] = (
    _CONFLICT_DOMAIN_HINTS
    | _DANGER_DOMAIN_HINTS
    | _DOMESTIC_ADVERSE_EVENT_HINTS
    | _PRISON_DOMAIN_HINTS
    | _RELATIONSHIP_ADVERSE_EVENT_HINTS
    | {
        'bankruptcy',
        'danger',
        'death',
        'delay_obstruction',
        'illness',
        'loss_deprivation',
        'loss_of_authority',
        'major_financial_loss',
        'miscommunication',
        'reputation_damage',
        'shared_resource_loss',
    }
)
_STRONG_ADVERSE_STEP_HINTS: Set[str] = (
    _CONFLICT_DOMAIN_HINTS
    | _DANGER_DOMAIN_HINTS
    | _PRISON_DOMAIN_HINTS
    | {
        'bankruptcy_risk',
        'danger',
        'death',
        'illness',
        'loss_of_authority',
        'major_financial_loss',
        'reputation_damage',
        'shared_resource_loss',
    }
)
_ORIENTATION_TAGS: Set[str] = {'positive', 'negative', 'mixed'}


def _house_candidate_domains(house_num: Optional[int]) -> List[str]:
    out: List[str] = []
    if house_num is None:
        return out
    primary = _HOUSE_DEFAULT_DOMAIN.get(int(house_num))
    if primary:
        out.append(primary)
    for candidate in _HOUSE_CONTEXT_DOMAINS.get(int(house_num), ()):
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def _row_context_tokens(row: Optional[Dict[str, Any]]) -> Set[str]:
    tokens: Set[str] = set()
    if not isinstance(row, dict):
        return tokens

    def _push(raw: Any) -> None:
        if not isinstance(raw, str):
            return
        low = raw.strip().lower()
        if not low:
            return
        tokens.add(_DOMAIN_SYNONYMS.get(low, low))

    for raw in (row.get('keywords') or []):
        _push(raw)
    for raw in (row.get('enriched_keywords') or []):
        _push(raw)
    for raw in (row.get('prediction_tags') or []):
        _push(raw)
    pred = row.get('prediction') or {}
    if isinstance(pred, dict):
        _push(pred.get('eventType'))
        _push(pred.get('lifeArea'))
    _push(row.get('event_domain'))
    return tokens


def _sync_prediction_orientation_tags(row: Optional[Dict[str, Any]]) -> None:
    if not isinstance(row, dict):
        return
    tone = str(row.get('tone') or '').strip().lower()
    if tone not in _ORIENTATION_TAGS:
        return

    tags: List[str] = []
    for raw in (row.get('prediction_tags') or []):
        tag = str(raw).strip()
        if not tag or tag.lower() in _ORIENTATION_TAGS:
            continue
        tags.append(tag)
    tags.append(tone)
    row['prediction_tags'] = list(dict.fromkeys(tags))

    pred = row.get('prediction')
    if isinstance(pred, dict):
        pred['tags'] = row['prediction_tags']


def _step_tone_from_hits(hits_list: List[Dict[str, Any]]) -> str:
    if not hits_list:
        return 'mixed'

    total_weight = 0.0
    weighted_balance = 0.0
    pos_weight = 0.0
    neg_weight = 0.0
    mixed_weight = 0.0
    adverse_weight = 0.0
    strong_adverse_weight = 0.0

    for hit in hits_list:
        if not isinstance(hit, dict):
            continue
        weight = max(
            1.0,
            abs(_safe_float(hit.get('significance')))
            or abs(_safe_float(hit.get('prediction_score')))
            or abs(_safe_float(hit.get('score')))
            or 1.0,
        )
        total_weight += weight
        tone_score = _safe_float(hit.get('tone_score'))
        weighted_balance += tone_score * weight

        tags = {str(tag).strip().lower() for tag in (hit.get('prediction_tags') or []) if str(tag).strip()}
        tone = str(hit.get('tone') or '').strip().lower()
        if 'positive' in tags:
            tone = 'positive'
        elif 'negative' in tags:
            tone = 'negative'
        elif 'mixed' in tags or 'mixed_outcome' in tags:
            tone = 'mixed'

        if tone == 'positive':
            pos_weight += weight
        elif tone == 'negative':
            neg_weight += weight
        else:
            mixed_weight += weight

        ctx_tokens = _row_context_tokens(hit)
        adverse_hits = ctx_tokens & _ADVERSE_STEP_HINTS
        if adverse_hits:
            adverse_weight += weight
            if adverse_hits & _STRONG_ADVERSE_STEP_HINTS:
                strong_adverse_weight += weight

    if total_weight <= 0.0:
        return 'mixed'

    avg = weighted_balance / total_weight

    # Morin's determination-first model should not headline a row as positive
    # when adverse/conflict testimony is materially present in the same row.
    if strong_adverse_weight > 0.0:
        if neg_weight >= (pos_weight * 0.6) or avg <= 0.15:
            return 'negative'
        return 'mixed'
    if adverse_weight > 0.0:
        if neg_weight > pos_weight and avg <= 0.35:
            return 'negative'
        if pos_weight > 0.0:
            return 'mixed'

    if avg >= 0.8 and neg_weight == 0.0 and mixed_weight == 0.0 and adverse_weight == 0.0:
        return 'positive'
    if avg <= -0.45 or neg_weight > (pos_weight * 1.15):
        return 'negative'
    if (pos_weight > 0.0 and (neg_weight > 0.0 or mixed_weight > 0.0)) or mixed_weight > 0.0:
        return 'mixed'
    if pos_weight > 0.0:
        return 'positive'
    if neg_weight > 0.0:
        return 'negative'
    return 'mixed'


def _pick_contextual_domain(
    dom_list: Iterable[str],
    *,
    row: Optional[Dict[str, Any]] = None,
    event_type: Optional[str] = None,
) -> Optional[str]:
    normalized: List[str] = []
    seen: Set[str] = set()
    for dom in dom_list:
        if not dom:
            continue
        norm = _DOMAIN_SYNONYMS.get(str(dom).lower(), str(dom).lower())
        if not norm or norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)
    if not normalized:
        return None

    tokens = _row_context_tokens(row)
    if event_type:
        tokens.add(_DOMAIN_SYNONYMS.get(str(event_type).lower(), str(event_type).lower()))

    if 'conflict' in normalized and tokens & _CONFLICT_DOMAIN_HINTS:
        return 'conflict'
    if 'danger' in normalized and tokens & _DANGER_DOMAIN_HINTS:
        return 'danger'
    if 'prison' in normalized and tokens & _PRISON_DOMAIN_HINTS:
        return 'prison'
    if 'hidden_enemies' in normalized and tokens & (_HIDDEN_DOMAIN_HINTS | _PRISON_DOMAIN_HINTS):
        return 'hidden_enemies'
    if 'marriage' in normalized and tokens & _MARRIAGE_DOMAIN_HINTS:
        return 'marriage'
    if 'relationships' in normalized and tokens & _RELATIONSHIP_DOMAIN_HINTS:
        return 'relationships'

    for dom in normalized:
        if dom in _DOMAIN_PRIMARY_HOUSE:
            return dom
    return normalized[0]


_ROW_CRISIS_EVENT_TYPES: Set[str] = {
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
    'imprisonment_risk',
}


def _event_candidate_areas(event_type: Optional[str]) -> Set[str]:
    event = str(event_type or '').strip().lower()
    if not event:
        return set()
    if event in _ROW_CRISIS_EVENT_TYPES:
        return {'conflict', 'danger', 'death', 'prison', 'hidden_enemies', 'secrets'}
    if event in {
        'promotion', 'recognition', 'public_recognition', 'honor_award', 'new_job',
        'career_elevation', 'professional_recognition', 'authority_earned',
        'structure_established', 'power_increase', 'loss_of_authority',
        'public_humiliation', 'demotion', 'retirement', 'fall_from_power',
        'authority_problems', 'exceptional_honor_received', 'career_setback_major',
        'church_honors', 'business_success', 'business_failure',
    }:
        return {'honors'}
    if event in {
        'financial_gain', 'financial_loss', 'salary_increase', 'speculation_gain',
        'speculation_loss', 'inheritance', 'inheritance_windfall',
        'inheritance_received', 'shared_resource_loss', 'investment_success',
        'investment_loss', 'bankruptcy', 'bankruptcy_risk', 'debt_crisis',
        'major_wealth_acquisition', 'unexpected_financial_gain',
        'major_financial_loss', 'loss_of_possessions', 'property_value_increase',
        'property_value_decrease', 'theft_fraud',
    }:
        return {'wealth', 'money', 'shared_resources'}
    if event in {
        'marriage', 'marriage_likely', 'significant_partnership',
        'romantic_connection', 'romance', 'reconciliation', 'engagement',
        'partnership_strengthened', 'harmonious_relationship_period',
    }:
        return {'relationships', 'marriage'}
    if event in {
        'relationship_conflict', 'partnership_strained', 'lawsuit',
        'legal_victory', 'legal_defeat', 'legal_resolution', 'settlement',
        'major_lawsuit_initiated', 'divorce', 'separation',
        'divorce_or_separation', 'betrayal',
    }:
        return {'relationships', 'conflict'}
    if event in {
        'moving_home', 'purchase_property', 'relocation_permanent',
        'family_celebration', 'family_conflict', 'family_joy',
        'family_problems', 'domestic_happiness', 'domestic_disruption',
    }:
        return {'home'}
    if event in {
        'short_journey', 'long_journey', 'major_journey_fortunate',
        'travel_misfortune', 'foreign_residence', 'exile_or_forced_travel',
        'communication_breakthrough', 'miscommunication',
    }:
        return {'short_journeys', 'long_travel'}
    if event in {
        'degree_completion', 'exam_success', 'exam_failure',
        'enrollment_admission', 'publication', 'artistic_success',
        'discovery_breakthrough', 'intellectual_breakthrough',
        'educational_achievement', 'mental_confusion_period',
        'spiritual_awakening', 'religious_conversion', 'pilgrimage',
        'mystical_experience',
    }:
        return {'belief'}
    if event in {
        'illness_acute', 'illness_chronic', 'recovery_health', 'surgery',
        'hospitalization', 'fever', 'severe_illness_onset',
        'chronic_illness_development', 'sudden_health_crisis',
        'recovery_period', 'vitality_strengthening', 'injury_risk',
        'accident_risk', 'protection_granted',
    }:
        return {'health', 'life', 'service'}
    if event in {'birth_of_child', 'pregnancy', 'childbirth', 'loss_of_child'}:
        return {'children', 'home'}
    if event in {'birth_self', 'opportunity_received'}:
        return {'life', 'honors', 'wealth'}
    return set()


def _event_candidate_domain_alignment(event_type: Optional[str], life_area: Optional[str]) -> float:
    area = _DOMAIN_SYNONYMS.get(str(life_area or '').strip().lower(), str(life_area or '').strip().lower())
    if not area:
        return 0.0
    allowed = _event_candidate_areas(event_type)
    if not allowed:
        return 0.0
    if area in allowed:
        return 1.0
    if area in {'wealth', 'money'} and allowed & {'wealth', 'money'}:
        return 0.9
    if area in {'relationships', 'marriage'} and allowed & {'relationships', 'marriage'}:
        return 0.9
    if area in {'short_journeys', 'long_travel'} and allowed & {'short_journeys', 'long_travel'}:
        return 0.9
    if event_type in _ROW_CRISIS_EVENT_TYPES and area in {'conflict', 'danger', 'death', 'prison', 'hidden_enemies', 'secrets'}:
        return 0.8
    return 0.0


def _explicit_row_event_tokens(row: Optional[Dict[str, Any]]) -> Set[str]:
    tokens: Set[str] = set()
    if not isinstance(row, dict):
        return tokens
    for raw in (row.get('enriched_keywords') or []):
        if isinstance(raw, str) and raw.strip():
            tokens.add(raw.strip().lower())
    for raw in (row.get('prediction_tags') or []):
        if isinstance(raw, str) and raw.strip():
            tokens.add(raw.strip().lower())
    return tokens


def _select_row_event_type(
    row: Optional[Dict[str, Any]],
    life_area: Optional[str],
    kw_all: Set[str],
    event_search_order: List[str],
) -> Optional[str]:
    explicit_tokens = _explicit_row_event_tokens(row)
    best_event: Optional[str] = None
    best_key: Optional[Tuple[float, float, float, int]] = None
    for idx, event in enumerate(event_search_order):
        if event not in kw_all:
            continue
        alignment = _event_candidate_domain_alignment(event, life_area)
        explicit_bonus = 1.0 if event in explicit_tokens else 0.0
        crisis_bonus = 0.25 if event in _ROW_CRISIS_EVENT_TYPES and alignment > 0.0 else 0.0
        key = (alignment, explicit_bonus, crisis_bonus, -idx)
        if best_key is None or key > best_key:
            best_key = key
            best_event = event
    return best_event


def _conservative_domain_tokens(row: Dict[str, Any]) -> List[str]:
    doms: List[str] = []
    seen: Set[str] = set()

    def _push(name: Optional[str]) -> None:
        if not name:
            return
        norm = _DOMAIN_SYNONYMS.get(str(name).lower(), str(name).lower())
        if not norm or norm not in _CONSERVATIVE_DOMAIN_TOKENS or norm in seen:
            return
        seen.add(norm)
        doms.append(norm)

    for raw in (row.get('keywords') or []):
        token = str(raw or '').strip()
        if not token:
            continue
        mapped = _RAW_KEYWORD_DOMAIN_MAP.get(token)
        if mapped:
            _push(mapped)
        if token.startswith('C') and token[1:].isdigit():
            try:
                for dom in _house_candidate_domains(int(token[1:])):
                    _push(dom)
            except Exception:
                pass
    for raw in (row.get('enriched_keywords') or []):
        _push(str(raw or ''))
    return doms


def _domain_polarity(name: Optional[str]) -> int:
    if not name:
        return 0
    key = str(name).lower()
    return _DOMAIN_POLARITY.get(key, 0)


def _prune_registry(registry: Dict[str, Deque[Dict[str, Any]]], cutoff: datetime) -> None:
    for key, dq in list(registry.items()):
        while dq and dq[0]['timestamp'] < cutoff:
            dq.popleft()
        if not dq:
            registry.pop(key, None)


def _register_registry_event(
    registry: Dict[str, Deque[Dict[str, Any]]],
    key: str,
    entry: Dict[str, Any],
    horizon_days: float,
) -> None:
    dq = registry.setdefault(key, collections.deque())
    dq.append(entry)
    cutoff = entry['timestamp'] - timedelta(days=horizon_days)
    while dq and dq[0]['timestamp'] < cutoff:
        dq.popleft()
def _score_hit(
    hit: Dict[str, Any],
    natal_house_of: Dict[str, Optional[int]],
    house_rulers: Dict[str, str],
    focus_houses: Optional[List[int]] = None,
    focus_planets: Optional[List[str]] = None,
    planet_conditions: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    A = str(hit.get('transiting') or '')
    B = str(hit.get('natal') or hit.get('target_label') or '')
    orb = float(hit.get('orb') or 0.0)
    max_orb = float(hit.get('max_orb') or 0.0)
    partile = bool(hit.get('partile'))
    bodily_contact = (
        bool(hit.get('bodily_contact'))
        if 'bodily_contact' in hit
        else partile
    )
    platic = bool(hit.get('complete_platic'))
    target_type = str(hit.get('target_type') or 'planet')
    natal_house = hit.get('natal_house') if hit.get('natal_house') is not None else natal_house_of.get(B)

    bd: Dict[str, float] = {}
    # Base from transiting planet
    base = _SLOW_WEIGHT.get(A, 1.0)
    bd['slow'] = base
    score = base
    # Orb closeness
    if max_orb > 0:
        clos = max(0.0, (max_orb - orb) / max_orb)
        bd['orb_proximity'] = 2.0 * clos
        score += bd['orb_proximity']
    else:
        clos = 0.0
        bd['orb_proximity'] = 0.0
    # Exactness is already represented continuously by orb proximity.  Retain
    # the engine's historical physical-contact bonus without conflating that
    # much tighter condition with the public one-degree ``partile`` flag.
    bd['partile'] = 0.0
    if bodily_contact:
        bd['bodily_contact'] = 2.0
        score += 2.0
    else:
        bd['bodily_contact'] = 0.0
    if platic:
        bd['platic'] = 1.0
        score += 1.0
    else:
        bd['platic'] = 0.0
    # Angularity bonus removed per spec (no target-house scaling)
    bd['angularity'] = 0.0
    # Aspect-type influence with planetary nature (malefic/benefic)
    try:
        fam = _aspect_hard_soft(str(hit.get('aspect') or ''))  # 'hard'|'soft'|'conj'|'other'
        is_mal = A in ('Mars', 'Saturn')
        is_ben = A in ('Jupiter', 'Venus')
        is_dep = A in ('Sun','Moon','Mercury')
        delta = 0.0
        if is_ben:
            if fam == 'soft':
                delta = 0.6
            elif fam == 'conj':
                delta = 0.4
            elif fam == 'hard':
                delta = -0.4
        elif is_mal:
            if fam == 'hard':
                delta = -0.8
            elif fam == 'conj':
                delta = -0.4
            elif fam == 'soft':
                delta = -0.2
        else:
            # Dependent planets (Sun/Moon/Mercury): scale by natal condition
            if fam in ('soft','hard'):
                base = 0.1 if fam == 'soft' else -0.1
                cond = 0.0
                try:
                    if planet_conditions and isinstance(planet_conditions, dict):
                        cond = float(planet_conditions.get(A, 0.0))
                except Exception:
                    cond = 0.0
                # amplify by (1 + cond); cond in [-1,1]
                delta = base * (1.0 + cond)
            else:
                delta = 0.0
        # Scale by closeness so tighter aspects weigh more (retain 50% at wide)
        # Extra weight: malefic quincunx is penalized stronger than other hard aspects
        try:
            aname = str(hit.get('aspect') or '').lower()
            if is_mal and 'quin' in aname:
                delta -= 0.2  # deepen penalty before scaling
        except Exception:
            pass
        # Scale by closeness only
        delta *= (0.5 + 0.5 * clos)
        score += delta
        bd['aspect'] = delta
    except Exception:
        bd['aspect'] = 0.0

    # Special-rule scoring adjustments (Rule 3 & Rule 4 nuances)
    try:
        special = 0.0
        fam = _aspect_hard_soft(str(hit.get('aspect') or ''))
        # Extra harm: malefic hard into H8/H12
        if A in ('Mars','Saturn') and fam == 'hard' and (isinstance(natal_house, int) and natal_house in (8,12)):
            special -= 0.6 * (0.5 + 0.5 * clos)
        # Malefic (contra-)antiscia to MC
        try:
            if A in ('Mars','Saturn') and str(hit.get('target_type') or '') in ('antiscia','contra_antiscia'):
                lbl = str(hit.get('target_label') or '')
                if lbl.startswith('MC'):
                    special -= 0.4 * (0.5 + 0.5 * clos)
        except Exception:
            pass
        # Lethal conjunction flags
        flags = hit.get('special_flags') or {}
        if flags.get('lethal_new_moon') and A in ('Sun','Moon'):
            special -= 1.2
        if flags.get('asc8_conj'):
            try:
                asc_r = str(house_rulers.get('1') or house_rulers.get(1) or '')
                h8_r = str(house_rulers.get('8') or house_rulers.get(8) or '')
                if A == asc_r or A == h8_r:
                    special -= 1.0
            except Exception:
                pass
        if special != 0.0:
            score += special
            bd['special_rules'] = special
    except Exception:
        pass

    # Ascendant target boost (Asc / Asc (antiscia) / Asc (contra-antiscia))
    try:
        label = str(hit.get('target_label') or hit.get('natal') or '')
        base_label = label
        if base_label.endswith(' (antiscia)'):
            base_label = base_label[:-11]
        elif base_label.endswith(' (contra-antiscia)'):
            base_label = base_label[:-18]
        if base_label == 'Asc':
            try:
                orb = float(hit.get('orb') or 0.0)
                mx = float(hit.get('max_orb') or 1.0) or 1.0
                clos2 = max(0.0, min(1.0, 1.0 - (orb / mx)))
            except Exception:
                clos2 = 0.0
            asc_bonus = 0.8 * (0.5 + 0.5 * clos2)
            score += asc_bonus
            bd['asc_target'] = round(asc_bonus, 3)
    except Exception:
        pass
    # Ruler relevance (only when target is a planet)
    bd['ruler'] = 0.0
    try:
        if target_type == 'planet':
            ruled_houses = [int(k) for k, v in house_rulers.items() if str(v) == B]
            for h in ruled_houses[:2]:
                score += (1.0 if h in (1, 10) else 0.5)
                bd['ruler'] += (1.0 if h in (1, 10) else 0.5)
    except Exception:
        pass
    # Context (focus) boosts
    bd['focus'] = 0.0
    try:
        fh = set(int(x) for x in (focus_houses or []) if isinstance(x, (int, str)))
    except Exception:
        fh = set()
    try:
        fp = set(str(x) for x in (focus_planets or []) if isinstance(x, (int, str)))
    except Exception:
        fp = set()
    if natal_house is not None and int(natal_house) in fh:
        score += 0.75
        bd['focus'] += 0.75
    if B in fp or A in fp:
        score += 0.5
        bd['focus'] += 0.5

    if target_type in {'empty', 'empty_space', 'zodiac_space'}:
        score *= 0.25
        bd['empty_space'] = -0.75

    # (Removed) Natal significance additive contributions to score
    return float(round(score, 3)), bd


# (helper removed per request — keeping original per-path keyword logic)


def _house_band(h: Optional[int]) -> Optional[str]:
    try:
        if h in (1, 4, 7, 10):
            return 'Angular'
        if h in (2, 5, 8, 11):
            return 'Succedent'
        if h in (3, 6, 9, 12):
            return 'Cadent'
    except Exception:
        pass
    return None


def _house_domain(h: Optional[int]) -> Optional[str]:
    """Return a concise domain label for a natal house number.
    Used for more specific keyword tagging in Morin-style synthesis.
    """
    try:
        if h == 1: return 'Body'
        if h == 2: return 'Money'
        if h == 3: return 'Travel'
        if h == 4: return 'Home'
        if h == 5: return 'Children'
        if h == 6: return 'Health'
        if h == 7: return 'Relationship'
        if h == 8: return 'Shared'
        if h == 9: return 'Belief'
        if h == 10: return 'Career'
        if h == 11: return 'Friends'
        if h == 12: return 'Hidden'
    except Exception:
        pass
    return None


def _aspect_hard_soft(name: str) -> str:
    k = (name or '').lower()
    if 'opp' in k or 'square' in k or 'quin' in k:
        return 'hard'
    if 'conj' in k:
        return 'conj'
    if 'trine' in k or 'sext' in k:
        return 'soft'
    return 'other'


def _natal_aspect_map(chart_data: Dict[str, Any]) -> Dict[frozenset, str]:
    """Build a map of natal aspects between classical planets for quick lookups.
    Returns mapping: frozenset({p1, p2}) -> canonical aspect name.
    """
    out: Dict[frozenset, str] = {}
    try:
        arr = chart_data.get('aspects') or []
        if isinstance(arr, list):
            for a in arr:
                if not isinstance(a, dict):
                    continue
                p1 = a.get('planet1') or a.get('p1')
                p2 = a.get('planet2') or a.get('p2')
                asp = a.get('aspect') or a.get('name')
                if p1 and p2 and asp:
                    key = frozenset({str(p1), str(p2)})
                    out[key] = str(asp)
    except Exception:
        return out
    return out


def _transit_hit_key(hit: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(hit.get('transiting') or ''),
        str(hit.get('aspect') or ''),
        str(hit.get('target_label') or hit.get('natal') or ''),
    )


def _select_morin_transit_step_candidates(
    hits: List[Dict[str, Any]],
    *,
    top_n_per_type: int = 3,
    prediction_n_per_type: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Select identical display/predictor candidates for every scan transport."""
    top_n = max(1, int(top_n_per_type or 1))
    prediction_n = max(top_n, int(prediction_n_per_type or top_n))
    planet_hits = [h for h in hits if str(h.get('target_type')) == 'planet']
    point_hits = [h for h in hits if str(h.get('target_type')) != 'planet']
    top_planets = planet_hits[:top_n]
    top_points = point_hits[:top_n]
    prediction_planets = planet_hits[:prediction_n]
    prediction_points = point_hits[:prediction_n]

    def _base_label(hit: Dict[str, Any]) -> str:
        label = str(hit.get('target_label') or hit.get('natal') or '')
        return label.replace(' (contra-antiscia)', '').replace(' (antiscia)', '')

    asc_hits = [hit for hit in hits if _base_label(hit) == 'Asc']

    def _append_unique(
        base: List[Dict[str, Any]],
        extra: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        seen = {_transit_hit_key(hit) for hit in base}
        for hit in extra:
            key = _transit_hit_key(hit)
            if key not in seen:
                base.append(hit)
                seen.add(key)
        return base

    # Ascendant variants are retained for prediction extraction even when they
    # rank below the normal per-type limit.  They must not inflate the display
    # ``top`` set or its aggregate step score beyond the documented limit.
    prediction_points = _append_unique(prediction_points, asc_hits)
    return (
        [dict(hit) for hit in (top_planets + top_points)],
        [dict(hit) for hit in (prediction_planets + prediction_points)],
    )


def scan_morin_transits_window(
    natal_chart_data: Dict[str, Any],
    start_iso: str,
    end_iso: str,
    step_minutes: int = 60,
    planet_names: Optional[List[str]] = None,
    top_n_per_step: int = 3,
    prediction_n_per_step: Optional[int] = None,
    include_modern: bool = False,
    natal_include_modern: bool = False,
    include_cusps: bool = False,
    include_antiscia: bool = False,
    include_lots: bool = False,
    focus_houses: Optional[List[int]] = None,
    focus_planets: Optional[List[str]] = None,
    sensitive_houses: Optional[List[int]] = None,
    sensitive_planets: Optional[List[str]] = None,
    flt_transiting: Optional[List[str]] = None,
    flt_natal: Optional[List[str]] = None,
    flt_aspects: Optional[List[str]] = None,
    pd_windows: Optional[List[Dict[str, Any]]] = None,
    use_new_significance: Optional[bool] = None,
    observer_location: Optional[str] = None,
    observer_timezone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Scan a time window and return per-step top Morin transit hits.

    Output items: { timestamp, count, top: [hit, ...] }
    """
    if swe is None:
        return []
    try:
        from datetime import datetime, timezone
        # parse start/end
        sdt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        edt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        # Naive API inputs are defined as UTC, while explicitly offset inputs
        # retain their display offset.  Both become aware and therefore compare
        # safely, without rewriting timestamps expected by replay/export clients.
        if sdt.tzinfo is None:
            sdt = sdt.replace(tzinfo=timezone.utc)
        if edt.tzinfo is None:
            edt = edt.replace(tzinfo=timezone.utc)
        if edt <= sdt:
            return []
    except Exception:
        return []

    step_minutes = max(1, int(step_minutes or 60))
    out: List[Dict[str, Any]] = []
    cur = sdt
    delta = None
    try:
        from datetime import timedelta
        delta = timedelta(minutes=step_minutes)
    except Exception:
        delta = None
    # Safety bound: avoid excessive steps
    max_steps = 5000
    steps = 0
    # Precompute natal context once for the entire scan window (avoids repeated work per step)
    _ctx = _prepare_natal_context(
        natal_chart_data,
        include_cusps=include_cusps,
        include_antiscia=include_antiscia,
        include_lots=include_lots,
        sensitive_houses=sensitive_houses,
        sensitive_planets=sensitive_planets,
        natal_include_modern=natal_include_modern,
    )
    retro_pass_tracker: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    registry_context = _new_transit_registry_context()
    while cur <= edt and steps < max_steps:
        ts_iso = cur.replace(tzinfo=cur.tzinfo or timezone.utc).isoformat()
        hits = compute_morin_transits_to_natal(
            natal_chart_data,
            ts_iso,
            dt_hours=0.5,
            planet_names=planet_names,
            include_modern=include_modern,
            natal_include_modern=natal_include_modern,
            include_cusps=include_cusps,
            include_antiscia=include_antiscia,
            include_lots=include_lots,
            focus_houses=focus_houses,
            focus_planets=focus_planets,
            sensitive_houses=sensitive_houses,
            sensitive_planets=sensitive_planets,
            observer_location=observer_location,
            observer_timezone=observer_timezone,
            _prepared_ctx=_ctx,
        )
        # Apply filters BEFORE selecting top N so top reflects filters
        if flt_transiting:
            hits = [h for h in hits if str(h.get('transiting')) in flt_transiting]
        if flt_natal:
            hits = [
                h for h in hits
                if str(h.get('natal')) in flt_natal
                or str(h.get('target_label')) in flt_natal
            ]
        if flt_aspects:
            hits = [h for h in hits if str(h.get('aspect')) in flt_aspects]
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
        # Enrich the complete active set once so Morin's simultaneous-transit
        # analysis sees the whole sky.  Display/predictor limits are presentation
        # concerns and must not change the astrological result.
        enriched_hits: List[Dict[str, Any]] = [dict(hit) for hit in hits]
        if enriched_hits:
            try:
                enriched_hits = enrich_hits_with_concordance(
                    natal_chart_data, enriched_hits, ts_iso, pd_windows=pd_windows,
                    use_new_significance=use_new_significance,
                    observer_location=observer_location,
                    observer_timezone=observer_timezone,
                    registry_context=registry_context,
                )
            except Exception:
                pass
        if not isinstance(enriched_hits, list):
            try:
                enriched_hits = list(enriched_hits) if enriched_hits is not None else []
            except Exception:
                enriched_hits = [dict(hit) for hit in hits]
        # Split by target type only after enrichment.  Keep the displayed step
        # narrow while retaining a deeper predictor candidate set.
        top_sel, prediction_sel = _select_morin_transit_step_candidates(
            enriched_hits,
            top_n_per_type=top_n_per_step,
            prediction_n_per_type=prediction_n_per_step,
        )
        top_planets = [h for h in top_sel if str(h.get('target_type')) == 'planet']
        top_points = [h for h in top_sel if str(h.get('target_type')) != 'planet']
        # Step aggregates based on significance
        try:
            step_signif = sum(float(h.get('significance') or 0.0) for h in top_sel)
        except Exception:
            try:
                step_signif = sum(float(h.get('score') or 0.0) for h in top_sel)
            except Exception:
                step_signif = 0.0
        row = {
            'timestamp': ts_iso,
            'count': len(hits),  # filtered count
            'top': top_sel,
            '_prediction_hits': prediction_sel,
            'top_planets': top_planets,
            'top_cusps': top_points,
            'step_score': round(float(step_signif), 3),
            'tone': _step_tone_from_hits(top_sel),
        }
        out.append(row)
        steps += 1
        if not delta:
            break
        cur = cur + delta
    return out

def compute_morin_transits_to_natal(
    natal_chart_data: Dict[str, Any],
    transit_timestamp_iso: str,
    dt_hours: float = 0.5,
    planet_names: Optional[List[str]] = None,
    include_modern: bool = False,
    natal_include_modern: bool = False,
    include_cusps: bool = False,
    include_antiscia: bool = False,
    include_lots: bool = False,
    focus_houses: Optional[List[int]] = None,
    focus_planets: Optional[List[str]] = None,
    sensitive_houses: Optional[List[int]] = None,
    sensitive_planets: Optional[List[str]] = None,
    observer_location: Optional[str] = None,
    observer_timezone: Optional[str] = None,
    _prepared_ctx: Optional[Tuple[Any, ...]] = None,
) -> List[Dict[str, Any]]:
    """Return Morin-style transit hits from transiting A to natal B.

    Each row:
      { transiting, natal, aspect, orb, max_orb, partile, complete_platic,
        direction, phase }

    Notes:
      - Uses CLASSICAL (Sun..Saturn) by default. Natal bodies must include
        latitude to honor Morin's geometry.
      - Orbs gate by sum of orbs-of-virtue for A and B.
      - Partile: separation ≤ sum of semi-diameters (deg).
      - Phase: applying/separating via forward step (+dt).
    """
    if swe is None:
        return []

    # Observer snapshot for concordance (fallback to chart metadata if API did not provide)
    tz_meta = {}
    if isinstance(natal_chart_data, dict):
        tz_meta = natal_chart_data.get('timezone_info') or {}
    _snapshot_location = observer_location or tz_meta.get('location_name')
    if not _snapshot_location:
        coords = tz_meta.get('coordinates') if isinstance(tz_meta, dict) else None
        try:
            lat = coords.get('latitude') if isinstance(coords, dict) else None
            lon = coords.get('longitude') if isinstance(coords, dict) else None
            if lat is not None and lon is not None:
                _snapshot_location = f"{float(lat):.4f}, {float(lon):.4f}"
        except Exception:
            _snapshot_location = None
    _snapshot_timezone = observer_timezone or tz_meta.get('timezone') or 'UTC'

    # Reuse the optimized path used by window scan by preparing natal context once
    _ctx = _prepared_ctx or _prepare_natal_context(
        natal_chart_data,
        include_cusps=include_cusps,
        include_antiscia=include_antiscia,
        include_lots=include_lots,
        sensitive_houses=sensitive_houses,
        sensitive_planets=sensitive_planets,
        natal_include_modern=natal_include_modern,
    )
    try:
        jd0 = _jd_from_iso(transit_timestamp_iso)
    except Exception:
        return []
    dt_days = float(dt_hours) / 24.0

    # Transiting set
    names = planet_names or (list(CLASSICAL) + (["Uranus", "Neptune", "Pluto"] if include_modern else []))
    if not include_modern:
        names = [n for n in names if n in CLASSICAL]

    # Transit positions now and +dt for latitude trend
    now_ll: Dict[str, Tuple[float, float]] = {}
    fut_ll: Dict[str, Tuple[float, float]] = {}
    fut2_ll: Dict[str, Tuple[float, float]] = {}
    for nm in names:
        now_ll[nm] = _lon_lat_at(jd0, nm)
        fut_ll[nm] = _lon_lat_at(jd0 + dt_days, nm)
        # second forward step to determine trend at t+dt when rebuilding plane
        fut2_ll[nm] = _lon_lat_at(jd0 + 2*dt_days, nm)

    (natal_ll, target_meta, natal_house_of, house_rulers, natal_aspects, planet_domain_infl) = _ctx
    asc_ruler_name = ''
    try:
        asc_ruler_name = str(house_rulers.get('1') or house_rulers.get(1) or '')
    except Exception:
        asc_ruler_name = ''
    # Step-level special flags per rules (3) and (4)
    def _absdiff_deg(a: float, b: float) -> float:
        return abs((((a - b) + 180.0) % 360.0) - 180.0)
    lethal_new_moon = False
    lethal_full_moon = False
    asc8_conj = False
    try:
        if 'Sun' in now_ll and 'Moon' in now_ll:
            lonS = now_ll['Sun'][0]; lonM = now_ll['Moon'][0]
            nm_sep = _absdiff_deg(lonS, lonM)
            if nm_sep <= 1.0:
                # near New Moon; check proximity/opposition to natal malefics
                for mal in ('Mars','Saturn'):
                    if mal in natal_ll:
                        mlon = natal_ll[mal][0]
                        if min(_absdiff_deg(lonS, mlon), _absdiff_deg((lonS+180.0)%360.0, mlon)) <= 1.0:
                            lethal_new_moon = True
                            break
            # near Full Moon
            fm_sep = abs(nm_sep - 180.0)
            if fm_sep <= 1.0:
                for mal in ('Mars','Saturn'):
                    if mal in natal_ll:
                        mlon = natal_ll[mal][0]
                        if min(_absdiff_deg(lonS, mlon), _absdiff_deg(lonM, mlon)) <= 1.0:
                            lethal_full_moon = True
                            break
        # Conjunction of rulers of 1 and 8 by natal sign rulers
        asc_r = asc_ruler_name
        h8_r = str(house_rulers.get('8') or house_rulers.get(8) or '')
        if asc_r and h8_r and asc_r in now_ll and h8_r in now_ll:
            if _absdiff_deg(now_ll[asc_r][0], now_ll[h8_r][0]) <= 1.0:
                asc8_conj = True
    except Exception:
        lethal_new_moon = False; lethal_full_moon = False; asc8_conj = False
    out: List[Dict[str, Any]] = []
    # Build transit condition map for dependent planets from transit positions
    def _cond_dep(now_ll, fut_ll) -> Dict[str, float]:
        cond: Dict[str, float] = {}
        try:
            lonS = now_ll.get('Sun', (None,None))[0]
        except Exception:
            lonS = None
        for nm in ('Sun','Moon','Mercury'):
            try:
                lon = now_ll[nm][0]
            except Exception:
                continue
            val = 0.0
            # Sign-based dignity (simple)
            sign = _sign_from_lon(lon)
            if nm == 'Sun':
                if sign == 'Aries': val += 0.3
                if sign == 'Leo': val += 0.2
                if sign == 'Libra': val -= 0.3
                if sign == 'Aquarius': val -= 0.2
            elif nm == 'Moon':
                if sign == 'Taurus': val += 0.3
                if sign == 'Cancer': val += 0.2
                if sign == 'Scorpio': val -= 0.3
                if sign == 'Capricorn': val -= 0.2
            elif nm == 'Mercury':
                if sign in ('Gemini','Virgo'): val += 0.2
                if sign in ('Sagittarius','Pisces'): val -= 0.2
                if sign == 'Virgo': val += 0.3  # exalt domicile
                if sign == 'Pisces': val -= 0.3  # fall/detriment
            # Solar proximity for Moon/Mercury
            if lonS is not None and nm in ('Moon','Mercury'):
                sep = abs((((lon - lonS) + 180.0) % 360.0) - 180.0)
                if sep <= 0.25:
                    val += 0.5  # cazimi-ish
                elif sep <= 8.0:
                    val -= 0.5  # combust
                elif sep <= 17.0:
                    val -= 0.2  # under beams
            # Retrograde for Mercury
            if nm == 'Mercury':
                try:
                    lonAf = fut_ll[nm][0]
                    dlon = ((lonAf - lon + 540.0) % 360.0) - 180.0
                    if dlon < 0: val -= 0.5
                except Exception:
                    pass
            cond[nm] = max(-1.0, min(1.0, val))
        return cond

    dep_conditions = _cond_dep(now_ll, fut_ll)

    for A in names:
        if A not in now_ll:
            continue
        lonA, latA = now_ll[A]
        lonAf, latAf = fut_ll[A]
        rA = _unit(_sph_to_vec(lonA, latA))
        inclA = _apparent_inclination(A, latA)
        nA = _build_plane_normal(rA, latA, latAf, inclA)

        for B, (lonB, latB) in natal_ll.items():
            rB = _unit(_sph_to_vec(lonB, latB))
            for ang, label in ASPECT_SET:
                r_pos = _unit(_rotate(rA, nA, +ang))
                r_neg = _unit(_rotate(rA, nA, -ang))
                sep_pos = _angular_sep_deg(r_pos, rB)
                sep_neg = _angular_sep_deg(r_neg, rB)
                if sep_pos <= sep_neg:
                    sep = sep_pos
                    branch = +1
                else:
                    sep = sep_neg
                    branch = -1

                # Orbs-of-virtue gate (A + B)
                # For cusp/lot/antiscia targets, only use orbA (transiting planet orb)
                tmeta = target_meta.get(B, {})
                ttype = tmeta.get('target_type', 'planet')
                def _orb_for(name: str, allow_modern: bool) -> float:
                    return float(ORB_OF_VIRTUE.get(name, 2.0 if allow_modern else 0.0))
                orbA = _orb_for(A, include_modern)
                if ttype == 'planet':
                    orbB = _orb_for(B, natal_include_modern)
                    moietyA = orbA / 2.0
                    moietyB = orbB / 2.0
                    combined = moietyA + moietyB
                else:
                    orbB = 0.0
                    moietyA = orbA / 2.0
                    moietyB = 0.0
                    combined = moietyA
                if sep > combined:
                    continue
                # Tight cap for (contra-)antiscia targets
                try:
                    if ttype in ('antiscia','contra_antiscia') and sep > 3.0:
                        continue
                except Exception:
                    pass
                # Aspect-specific cap: Semi-sextile / Quincunx scored only when orb ≤ 3°
                try:
                    lbl_low = (label or '').strip().lower()
                    if ('semi' in lbl_low or 'quin' in lbl_low) and (sep > 3.0):
                        continue
                except Exception:
                    pass

                # Partile is the documented one-degree exactness band.  Keep
                # physical disc contact as separate evidence rather than using
                # it to redefine the traditional/product-facing term.
                sd_sum = _semi_diameter_deg(A, jd0)
                if ttype == 'planet':
                    sd_sum += _semi_diameter_deg(B, jd0)
                partile = _is_partile_orb(sep)
                bodily_contact = sep <= sd_sum
                complete_platic = (sep <= (min(moietyA, moietyB) if ttype == 'planet' else moietyA))

                # Phase via forward step for A (B fixed)
                lonA2, latA2 = fut_ll[A]
                # Use an additional forward step's latitude to preserve trend at t+dt
                _lonA3, latA3 = fut2_ll.get(A, (lonA2, latA2))
                rA2 = _unit(_sph_to_vec(lonA2, latA2))
                nA2 = _build_plane_normal(rA2, latA2, latA3, inclA)
                r_branch_future = _unit(_rotate(rA2, nA2, +ang if branch > 0 else -ang))
                sep_future = _angular_sep_deg(r_branch_future, rB)
                if sep_future < sep - 1e-6:
                    phase = 'applying'
                elif sep_future > sep + 1e-6:
                    phase = 'separating'
                else:
                    phase = 'stationary'

                # Meta
                natal_house = tmeta.get('natal_house')

                row = {
                    'transiting': A,
                    'natal': B,
                    'aspect': label,
                    'orb': round(float(sep), 4),
                    'max_orb': round(float(combined), 4),
                    'partile': bool(partile),
                    'bodily_contact': bool(bodily_contact),
                    'complete_platic': bool(complete_platic),
                    'direction': _dexter_sinister(lonA, lonB),
                    'phase': phase,
                    'is_malefic': True if A in ('Mars','Saturn') else False,
                    'is_benefic': True if A in ('Jupiter','Venus') else False,
                    'is_luminary': True if A in ('Sun','Moon') else False,
                    'target_type': ttype,
                    'target_label': B,
                    'natal_house': natal_house,
                    'transit_longitude': _norm360(float(lonA)),
                    'transit_latitude': float(latA),
                    'transit_sign': _sign_from_lon(lonA),
                    'target_longitude': _norm360(float(lonB)),
                    'target_latitude': float(latB),
                    'target_sign': _sign_from_lon(lonB),
                }
                # Quality & effective window
                try:
                    row['quality'] = _classify_quality(A, label)
                except Exception:
                    row['quality'] = 'mixed'
                try:
                    row['effectiveWindow'] = _estimate_effective_window(
                        transit_timestamp_iso,
                        float(sep),
                        float(sep_future),
                        float(dt_days),
                        float(combined),
                        A,
                    ) or None
                except Exception:
                    row['effectiveWindow'] = None
                # Attach special rule flags for scoring adjustments
                try:
                    if lethal_new_moon or lethal_full_moon or asc8_conj:
                        row['special_flags'] = {
                            'lethal_new_moon': bool(lethal_new_moon),
                            'lethal_full_moon': bool(lethal_full_moon),
                            'asc8_conj': bool(asc8_conj),
                        }
                except Exception:
                    pass
                try:
                    score, breakdown = _score_hit(row, natal_house_of, house_rulers, focus_houses, focus_planets, dep_conditions)
                    row['score'] = score
                    row['score_breakdown'] = breakdown
                except Exception:
                    pass
                # Dynamic keywords
                try:
                    kw: List[str] = []

                    # 1) Primary risk/context cues first (to surface in tags)
                    try:
                        hs_kind = hs  # 'hard'|'soft'|'conj'|'other'
                        near_exact = (float(sep) <= 1.0) or bool(partile)
                        if A in ('Mars', 'Saturn'):
                            # Injury risk: only for hard or near‑exact conjunctions to Body houses/Asc
                            if (hs_kind == 'hard' or (hs_kind == 'conj' and near_exact)) and (
                                B in ('Asc',) or (isinstance(natal_house, int) and natal_house in (1, 6))
                            ):
                                kw.append('Injury risk')
                            # Career strain: only for hard or near‑exact conjunctions to MC/H10
                            if (hs_kind == 'hard' or (hs_kind == 'conj' and near_exact)) and (
                                B in ('MC','C10') or (isinstance(natal_house, int) and natal_house == 10)
                            ):
                                kw.append('Career strain')
                        # Rule 3: New Moon near malefics
                        if lethal_new_moon and A in ('Sun','Moon'):
                            kw.append('Injury risk')
                        # Rule 3: Conjunction of rulers ASC and 8th
                        if asc8_conj:
                            try:
                                asc_r = str(house_rulers.get('1') or house_rulers.get(1) or '')
                                h8_r = str(house_rulers.get('8') or house_rulers.get(8) or '')
                                if A in (asc_r, h8_r):
                                    kw.append('Injury risk')
                            except Exception:
                                pass
                        # Rule 4: malefic hard to H8/H12 amplifies harm
                        if A in ('Mars','Saturn') and hs_kind == 'hard' and (isinstance(natal_house, int) and natal_house in (8,12)):
                            kw.append('Injury risk')
                    except Exception:
                        pass

                    # 2) Planetary nature and aspect hardness/softness
                    if A in ('Saturn','Mars'): kw.append('Malefic')
                    if A in ('Jupiter','Venus'): kw.append('Benefic')
                    hs = _aspect_hard_soft(label)
                    if hs == 'hard': kw.append('Hard')
                    elif hs == 'soft': kw.append('Soft')

                    # 3) Exactness + phase
                    if float(sep) <= 0.25:
                        kw.append('Exact')
                    elif partile:
                        kw.append('Partile')
                    elif complete_platic:
                        kw.append('Platic')
                    if phase == 'applying': kw.append('Applying')
                    elif phase == 'separating': kw.append('Separating')

                    # 4) Domain via trait-like influence (fallback to natal location)
                    h = int(natal_house) if isinstance(natal_house, int) else None
                    dom_added = False
                    if ttype == 'planet':
                        try:
                            cont = planet_domain_infl.get(B, {}) if isinstance(planet_domain_infl, dict) else {}
                            scores = cont.get('scores') if isinstance(cont, dict) else cont
                            if scores and isinstance(scores, dict):
                                top_dom = max(scores.items(), key=lambda x: x[1])[0]
                                if top_dom:
                                    kw.append(top_dom)
                                    dom_added = True
                                    # Add influence evidence for the chosen domain (up to 2)
                                    try:
                                        ev_map = cont.get('evidence') if isinstance(cont, dict) else {}
                                        evs = list(ev_map.get(top_dom, [])) if isinstance(ev_map, dict) else []
                                        # sort by value_norm then value
                                        evs.sort(key=lambda e: (-float(e.get('value_norm') or e.get('value') or 0.0), str(e.get('type'))))
                                        added = 0
                                        for e in evs:
                                            if added >= 2:
                                                break
                                            et = str(e.get('type'))
                                            if et == 'occupation':
                                                htag = f"Loc(H{int(e.get('house'))})" if e.get('house') else None
                                                if htag and htag not in kw:
                                                    kw.append(htag); added += 1
                                            elif et == 'rulership':
                                                htag = f"Ruler(H{int(e.get('house'))})" if e.get('house') else None
                                                if htag and htag not in kw:
                                                    kw.append(htag); added += 1
                                            elif et == 'aspect':
                                                try:
                                                    hnum = int(e.get('house')) if e.get('house') is not None else None
                                                    an = _aspect_short(str(e.get('aspect') or ''))
                                                    ob = float(e.get('orb') or 0.0)
                                                    ph = str(e.get('phase') or '')
                                                    phs = 'app' if ph == 'applying' else ('sep' if ph == 'separating' else '')
                                                    if hnum and an:
                                                        lab = f"C{hnum} {an} {round(ob,1)}° {phs}".strip()
                                                        if lab and lab not in kw:
                                                            kw.append(lab); added += 1
                                                except Exception:
                                                    pass
                                            elif et == 'co_rulership':
                                                ck = str(e.get('co_kind') or '')
                                                tag = 'Exalt' if ck.startswith('exalt') else ('Triplicity' if ck.startswith('triplicity') else None)
                                                if tag and tag not in kw:
                                                    kw.append(tag); added += 1
                                        # Domain synonyms (one)
                                        try:
                                            syn = {
                                                'Belief': ['Study','Journey'],
                                                'Shared': ['Debts','Taxes'],
                                                'Body': ['Self','Vitality'],
                                                'Money': ['Resources','Income'],
                                            }.get(top_dom, [])
                                            if syn:
                                                s = syn[0]
                                                if s not in kw:
                                                    kw.append(s)
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                        except Exception:
                            dom_added = False
                    if not dom_added:
                        dom = _house_domain(h)
                        if dom: kw.append(dom)
                    # (Removed) added positive cues tied to domain and soft aspects

                    # 5) Rulership tags (up to two) + significance cues
                    if ttype == 'planet':
                        try:
                            added = 0
                            for hk in range(1, 13):
                                rv = (house_rulers or {}).get(str(hk))
                                if str(rv) == str(B):
                                    dlab = _house_domain(hk)
                                    if hk in (1, 10):
                                        kw.append(f'Ruler(H{hk})')
                                    elif dlab:
                                        kw.append(f'Ruler({dlab})')
                                    else:
                                        kw.append(f'Ruler(H{hk})')
                                    added += 1
                                    if added >= 2:
                                        break
                        except Exception:
                            pass
                        # (Removed) Core planet cue tied to natal significance

                    # 6) Target nature (recognize base label for (contra-)antiscia)
                    base_label = B
                    try:
                        if ttype in ('antiscia','contra_antiscia') and isinstance(B, str):
                            if B.endswith(' (antiscia)'):
                                base_label = B.replace(' (antiscia)', '')
                            elif B.endswith(' (contra-antiscia)'):
                                base_label = B.replace(' (contra-antiscia)', '')
                    except Exception:
                        base_label = B
                    if base_label in ('Asc','MC'):
                        kw.append(base_label)
                    elif (isinstance(base_label, str) and base_label.startswith('C') and base_label[1:].isdigit()):
                        kw.append(base_label)
                    elif ttype == 'cusp' and isinstance(natal_house, int):
                        kw.append(f'C{natal_house}')
                    elif ttype == 'lot' and base_label == 'POF':
                        kw.append('POF')
                    if ttype == 'antiscia':
                        kw.append('Antiscia')
                    elif ttype == 'contra_antiscia':
                        kw.append('Contra-antiscia')

                    # 7) Natal house marker
                    if h is not None:
                        kw.append(f'Natal(H{h})')
                        # (Removed) Dominant(Hx) significance cue

                    # 8) Aspect short label
                    asp_s = _aspect_short(label)
                    if asp_s: kw.append(asp_s)

                    # 9) Dexter/Sinister + motion
                    try:
                        if str(row.get('direction')) == 'dexter':
                            kw.append('Dexter')
                        elif str(row.get('direction')) == 'sinister':
                            kw.append('Sinister')
                    except Exception:
                        pass
                    try:
                        dlon = ((lonAf - lonA + 540.0) % 360.0) - 180.0
                        if dlon < 0:
                            kw.append('Rx')
                    except Exception:
                        pass

                    # Natal aspect echo or change (returns to radical aspects)
                    try:
                        if ttype == 'planet':
                            nat_asp = natal_aspects.get(frozenset({A, B}))
                            if nat_asp:
                                nat_kind = _aspect_hard_soft(nat_asp)
                                tr_kind = _aspect_hard_soft(label)
                                if (nat_asp or '').lower().startswith((label or '').lower()[:3]):
                                    kw.append('Natal echo')
                                elif nat_kind == 'hard' and tr_kind == 'soft':
                                    kw.append('Hard→Soft')
                                elif nat_kind == 'soft' and tr_kind == 'hard':
                                    kw.append('Soft→Hard')
                    except Exception:
                        pass

                    # Focus cues
                    in_focus = False
                    try:
                        if focus_houses and isinstance(natal_house, int) and int(natal_house) in set(int(x) for x in focus_houses):
                            in_focus = True
                    except Exception:
                        pass
                    try:
                        if focus_planets and (B in focus_planets or A in focus_planets):
                            in_focus = True
                    except Exception:
                        pass
                    if in_focus:
                        kw.append('Focus')

                    # 10) Semantic cues (marriage/public/celebration) + catalog canonical events (phase 1)
                    try:
                        has_rel = 'Relationship' in kw
                        softish = (hs == 'soft') or (label == 'Conjunction') or ('Exact' in kw) or ('Partile' in kw)
                        if has_rel and softish and (A in ('Venus','Jupiter') or B in ('Venus','Jupiter')):
                            kw.append('marriage')
                        if (('MC' in kw) or ('C10' in kw) or ('Career' in kw)) and softish and (A in ('Venus','Jupiter','Sun') or B in ('Venus','Jupiter','Sun')):
                            kw.append('Public')
                        if ('Benefic' in kw and 'Soft' in kw) and (has_rel or ('Friends' in kw) or ('Home' in kw)):
                            kw.append('Celebration')
                        # Phase 1: map canonical catalog events using existing cues
                        has_career = ('Career' in kw) or ('C10' in kw) or ('MC' in kw)
                        has_home = ('Home' in kw) or ('C4' in kw)
                        has_money = ('Money' in kw)
                        has_health = ('Health' in kw) or ('C6' in kw)
                        has_shared = ('Shared' in kw) or ('shared_resources' in (row.get('enriched_keywords') or []))
                        has_hidden = ('Hidden' in kw) or ('secrets' in (row.get('enriched_keywords') or [])) or any(str(t).startswith('C12') for t in kw)
                        has_children = ('Children' in kw) or ('children' in (row.get('enriched_keywords') or []))
                        asc_ruler_hit = bool(asc_ruler_name and A == asc_ruler_name)
                        if has_career and softish and (A in ('Jupiter','Sun','Venus')):
                            if 'honor_award' not in kw: kw.append('honor_award')
                            if 'new_job' not in kw: kw.append('new_job')
                            if has_money and (A in ('Jupiter','Venus','Mercury')) and 'business_success' not in kw:
                                kw.append('business_success')
                        if has_career and (hs == 'hard') and (A in ('Saturn','Mars','Mercury')):
                            if 'job_loss' not in kw: kw.append('job_loss')
                            if has_money and 'business_failure' not in kw:
                                kw.append('business_failure')
                            if 'demotion' not in kw: kw.append('demotion')
                        if has_money and softish and (A in ('Jupiter','Venus')):
                            if 'salary_increase' not in kw: kw.append('salary_increase')
                            if has_shared and 'inheritance' not in kw: kw.append('inheritance')
                        if has_career and has_home and softish and (A == 'Saturn' or B == 'Saturn'):
                            if 'retirement' not in kw: kw.append('retirement')
                        if has_health and softish and (A in ('Jupiter','Venus','Sun')):
                            if 'recovery_health' not in kw: kw.append('recovery_health')
                        if has_health and (hs == 'hard') and (A in ('Saturn','Mars','Sun')):
                            if 'illness_acute' not in kw: kw.append('illness_acute')
                            if has_hidden and 'hospitalization' not in kw: kw.append('hospitalization')
                            if A in ('Mars','Sun') and 'fever' not in kw:
                                kw.append('fever')
                        can_birth_planet = (A in ('Jupiter','Venus','Moon','Sun')) or asc_ruler_hit
                        if has_children and softish and can_birth_planet:
                            if 'birth_of_child' not in kw: kw.append('birth_of_child')
                        # Candidate for native birth (life event)
                        try:
                            orb_tight = abs(float(row.get('orb') or 0.0)) <= 1.0
                        except Exception:
                            orb_tight = False
                        has_life = ('Body' in kw) or ('Asc' in kw) or ('C1' in kw) or (isinstance(natal_house, int) and natal_house == 1)
                        has_home_kw = ('Home' in kw) or ('C4' in kw) or (isinstance(natal_house, int) and natal_house == 4)
                        has_children_kw = has_children or (isinstance(natal_house, int) and natal_house == 5)
                        birth_self_planet = (A in ('Sun','Moon','Jupiter','Venus')) or asc_ruler_hit
                        if softish and orb_tight and birth_self_planet and has_children_kw and (has_life or has_home_kw):
                            if 'birth_self' not in kw: kw.append('birth_self')
                    except Exception:
                        pass

                    # Augment with external dictionary synonyms (non-intrusive)
                        try:
                            from event_keywords_helper import merge_event_synonyms  # type: ignore
                            kw = merge_event_synonyms(kw, promote_canonical=True)
                        except Exception:
                            pass
                    # de-dup preserve order
                    seen: Set[str] = set()
                    kw_list = [t for t in kw if t and not (t in seen or seen.add(t))]
                    row['keywords'] = kw_list

                    # Enriched keywords (normalized) for UI domain chips and helpers
                    try:
                        lower_set = {str(t).lower() for t in kw_list}
                        enriched: List[str] = []
                        # Domain normalization (House → domain tokens expected by UI)
                        dom_map = {
                            'body': 'life',
                            'money': 'money',
                            'travel': 'short_journeys',
                            'home': 'home',
                            'children': 'children',
                            'health': 'health',
                            'relationship': 'relationships',
                            'shared': 'shared_resources',
                            'belief': 'belief',
                            'career': 'career',
                            'friends': 'friends',
                            'hidden': 'secrets',
                        }
                        for cap in ('Body','Money','Travel','Home','Children','Health','Relationship','Shared','Belief','Career','Friends','Hidden'):
                            if cap in kw_list:
                                tok = dom_map.get(cap.lower())
                                if tok and tok not in enriched:
                                    enriched.append(tok)
                        # Semantic cues → normalized
                        if 'marriage' in lower_set or 'marriage' in kw_list:
                            if 'marriage' not in enriched: enriched.append('marriage')
                        if 'public' in lower_set:
                            if 'public_recognition' not in enriched: enriched.append('public_recognition')
                        if 'celebration' in lower_set:
                            if 'parties_celebrations' not in enriched: enriched.append('parties_celebrations')

                        # Event types per planet/situation (lifted from knowledge map, simplified rules)
                        def _has_cap(token: str) -> bool:
                            return token in kw_list
                        def _in_enriched(tok: str) -> bool:
                            return tok in enriched
                        def _add(tok: str):
                            if tok and tok not in enriched:
                                enriched.append(tok)
                        hs_kind = _aspect_hard_soft(label)
                        softish = (hs_kind == 'soft') or (label == 'Conjunction') or ('Exact' in kw_list) or ('Partile' in kw_list)
                        hardish = (hs_kind == 'hard')
                        # Domain presence via caps
                        has_career = _has_cap('Career') or 'C10' in kw_list or 'MC' in kw_list
                        has_home = _has_cap('Home') or 'C4' in kw_list or 'Asc' in kw_list and _has_cap('Body')
                        has_money = _has_cap('Money')
                        has_rel = _has_cap('Relationship') or 'marriage' in enriched
                        has_health = _has_cap('Health') or 'C6' in kw_list
                        has_travel = _has_cap('Travel') or 'short_journeys' in enriched

                        if A == 'Sun':
                            if has_career and softish:
                                _add('promotion'); _add('recognition')
                                _add('honor_award'); _add('new_job')
                            if has_career and hardish:
                                _add('fall_from_power'); _add('authority_problems')
                            if has_health and hardish:
                                _add('vitality_loss')
                        elif A == 'Moon':
                            if has_home and softish:
                                _add('domestic_happiness'); _add('family_joy'); _add('comfort_security'); _add('family_celebration')
                            if has_home and hardish:
                                _add('domestic_disruption'); _add('family_problems'); _add('family_conflict')
                            if 'public_recognition' in enriched and softish:
                                _add('public_approval')
                        elif A == 'Mercury':
                            if softish and (has_career or has_rel):
                                _add('business_deal'); _add('contract_signing'); _add('communication_breakthrough')
                                if has_career: _add('new_job')
                            if hardish and (has_career or has_rel or has_travel):
                                _add('miscommunication'); _add('contract_problems')
                        elif A == 'Venus':
                            if softish and has_rel:
                                _add('romantic_connection'); _add('reconciliation')
                            if softish and has_money:
                                _add('financial_gain')
                                _add('salary_increase')
                                if 'shared_resources' in enriched: _add('inheritance')
                            if hardish and has_rel:
                                _add('relationship_conflict')
                            if hardish and has_money:
                                _add('financial_loss')
                        elif A == 'Mars':
                            if hardish and (has_health or _has_cap('Body')):
                                _add('injury_risk'); _add('accident_risk')
                                _add('injury_accident')
                                _add('surgery')
                            if hardish and has_rel:
                                _add('conflict'); _add('relationship_conflict')
                            if hardish and has_home:
                                _add('family_conflict')
                            if hardish and has_travel and danger_det_score >= 0.5:
                                _add('travel_accident')
                            if softish and has_career:
                                _add('initiative')
                        elif A == 'Jupiter':
                            if softish:
                                _add('opportunity_received'); _add('protection_granted')
                                if has_money: _add('financial_windfall')
                                if has_career: _add('honor_award'); _add('new_job')
                                if has_money: _add('salary_increase')
                                if 'shared_resources' in enriched: _add('inheritance')
                                if has_career and has_money:
                                    _add('business_success')
                        if hardish:
                            _add('excess_problems')
                            if has_career and has_money:
                                _add('business_failure')
                        elif A == 'Saturn':
                            if softish and has_career:
                                _add('structure_established'); _add('discipline_rewarded'); _add('authority_earned')
                                if has_home:
                                    _add('retirement')
                            if softish and has_home and has_rel:
                                _add('family_conflict')
                            if hardish and has_travel and danger_det_score >= 0.5:
                                _add('travel_accident')
                        if hardish:
                            _add('delay_obstruction')
                            if has_health: _add('illness_chronic')
                            if has_money: _add('loss_deprivation')
                            if has_rel:
                                _add('relationship_conflict')
                            if has_career:
                                _add('job_loss')
                                _add('demotion')
                                if has_money:
                                    _add('business_failure')
                        # Cross-domain health-related canonical events
                        has_shared = _has_cap('Shared') or ('shared_resources' in enriched)
                        has_hidden = _has_cap('Hidden') or ('secrets' in enriched) or ('C12' in kw_list)
                        if has_health and softish and A in ('Jupiter','Venus','Sun'):
                            _add('recovery_health')
                        if has_health and hardish and A in ('Saturn','Mars','Sun'):
                            _add('illness_acute')
                            if has_hidden:
                                _add('hospitalization')
                            if A in ('Mars','Sun'):
                                _add('fever')
                        if has_home and hardish and A in ('Saturn','Mars'):
                            _add('family_conflict')
                        # Children / birth events
                        has_children = _has_cap('Children') or ('children' in enriched)
                        asc_ruler_hit = bool(asc_ruler_name and A == asc_ruler_name)
                        birth_child_planets = {'Jupiter','Venus','Moon','Sun'}
                        if has_children and softish and ((A in birth_child_planets) or asc_ruler_hit):
                            _add('pregnancy'); _add('birth_of_child')
                        try:
                            orb_val = abs(float(row.get('orb') or 0.0))
                        except Exception:
                            orb_val = 9.99
                        has_life_focus = _has_cap('Body') or _has_cap('Asc') or _in_enriched('life') or ((row.get('natal_house') == 1))
                        has_home_focus = _has_cap('Home') or _in_enriched('home') or ((row.get('natal_house') == 4))
                        birth_self_planet = (A in {'Sun','Moon','Jupiter','Venus'}) or asc_ruler_hit
                        if birth_self_planet and softish and (has_children or _in_enriched('children')) and (has_life_focus or has_home_focus) and orb_val <= 1.0:
                            _add('birth_self')
                        # Family celebration when celebration semantics + home/children domains
                        if 'parties_celebrations' in enriched and (has_home or has_children):
                            _add('family_celebration')
                        # --------------------------------------------
                        # Phase 2 canonical mappings — Travel + Death
                        # Rationale:
                        # - Travel: H3/H9 cues with Mercury/Jupiter and soft signatures.
                        # - Death: only under stricter malefic + hard conditions and relevant houses.
                        #   Violent: Mars-heavy or malefic to H1/H8; Natural: Saturn/soft malefic signatures.
                        # --------------------------------------------
                        try:
                            # Travel heuristics
                            has_h3 = _has_cap('C3') or _has_cap('Travel') or _in_enriched('short_journeys')
                            has_h9 = _has_cap('C9') or _has_cap('Belief')
                            if softish and (A in ('Mercury','Moon')) and has_h3:
                                _add('short_journey')
                            if softish and (A in ('Jupiter','Sun')) and has_h9:
                                _add('long_journey')
                        except Exception:
                            pass
                        try:
                            # Home move & property (Phase 2)
                            # moving_home: Home + (Travel(H3)/H9) with soft Moon/Mercury/Jupiter/Sun signatures
                            # purchase_property: Home + Money with soft Jupiter/Venus/Moon
                            has_h4 = _has_cap('C4') or _has_cap('Home')
                            if has_h4 and softish and (A in ('Moon','Mercury','Jupiter','Sun')) and (has_travel or _has_cap('C3') or _has_cap('Travel') or _has_cap('C9')):
                                _add('moving_home')
                            if has_h4 and has_money and softish and (A in ('Jupiter','Venus','Moon')):
                                _add('purchase_property')
                        except Exception:
                            pass
                        # --------------------------------------------
                        # Phase 2 canonical mappings — Legal/Contracts + Partnership nuance
                        # Rationale:
                        # - Lawsuit: Mercury/Saturn hard in relationship/career/money contexts.
                        # - Legal resolution: Jupiter/Sun soft in same domains.
                        # - Settlement: Venus/Jupiter soft with money + relation/career.
                        # - Partnership nuance: benefics vs malefics to 7th cues.
                        # --------------------------------------------
                        try:
                            # Partnership nuance (7th domain)
                            if has_rel:
                                if softish and (A in ('Venus','Jupiter')):
                                    _add('partnership_strengthened'); _add('romance')
                                if hardish and (A in ('Mars','Saturn')):
                                    _add('partnership_strained')
                        except Exception:
                            pass
                        # --------------------------------------------
                        # Phase 2 canonical mappings — Finance & Relationship depth
                        # Rationale:
                        # - Finance: investment_success/loss with 2nd+5th cues; bankruptcy when malefic + loss themes.
                        # - Relationship: engagement/divorce/separation/betrayal with 7th + aspect tone.
                        # --------------------------------------------
                        try:
                            # Financial speculation success/loss
                            has_spec = _has_cap('Children') or ('children' in enriched)  # proxy for 5th (speculation)
                            if softish and (A in ('Jupiter','Venus','Mercury')) and has_money and has_spec:
                                _add('investment_success')
                            if hardish and (A in ('Saturn','Mars','Mercury')) and has_money and has_spec:
                                _add('investment_loss')
                            # Theft/Fraud (strict): Mercury hard + hidden + money/shared
                            has_shared2 = _has_cap('Shared') or ('shared_resources' in enriched)
                            has_hidden2 = _has_cap('Hidden') or ('secrets' in enriched) or ('C12' in kw_list)
                            if hardish and (A in ('Mercury','Mars')) and has_hidden2 and (has_money or has_shared2):
                                _add('theft_fraud')
                            # Bankruptcy (strict): malefic hard + money + shared/hidden
                            if hardish and (A in ('Saturn','Mars')) and has_money and (has_shared2 or has_hidden2):
                                _add('bankruptcy')
                        except Exception:
                            pass
                        try:
                            # Relationship nuance: engagement/divorce/separation/betrayal
                            if has_rel and softish and (A in ('Venus','Jupiter')):
                                _add('engagement')
                            if has_rel and hardish and (A in ('Saturn','Mars')):
                                _add('separation')
                                # Divorce when legal conflict signatures also present
                                if 'lawsuit' in enriched or (A == 'Saturn' and (has_career or has_money)):
                                    _add('divorce')
                            # Betrayal: malefic (esp. Mars) hard + hidden cues in relationships
                            if has_rel and hardish and (A in ('Mars','Saturn')) and (('secrets' in enriched) or ('C12' in kw_list)):
                                _add('betrayal')
                        except Exception:
                            pass
                        # Augment with external dictionary synonyms (non-intrusive)
                        try:
                            from event_keywords_helper import merge_event_synonyms  # type: ignore
                            enriched = merge_event_synonyms(enriched, promote_canonical=True)
                        except Exception:
                            pass
                        row['enriched_keywords'] = enriched
                    except Exception:
                        row['enriched_keywords'] = []

                    # Technical tags (for optional display): copy select structured tokens from keywords
                    try:
                        import re as _re
                        tech: List[str] = []
                        for t in kw_list:
                            s = str(t)
                            if _re.match(r'^Loc\(H\d+\)$', s) or _re.match(r'^Ruler\(H\d+\)$', s) or _re.match(r'^Natal\(H\d+\)$', s) or _re.match(r'^C\d+\s+', s):
                                tech.append(s)
                        row['tech_tags'] = tech
                    except Exception:
                        row['tech_tags'] = []
                except Exception:
                    row['keywords'] = []
                out.append(row)

    out.sort(key=lambda r: (-float(r.get('score') or 0.0), abs(float(r.get('orb', 999.0)))))
    return out


def enrich_hits_with_concordance(
    natal_chart_data: Dict[str, Any],
    hits: List[Dict[str, Any]],
    transit_timestamp_iso: str,
    pd_windows: Optional[List[Dict[str, Any]]] = None,
    *,
    use_new_significance: Optional[bool] = None,
    observer_location: Optional[str] = None,
    observer_timezone: Optional[str] = None,
    context_out: Optional[Dict[str, Any]] = None,
    registry_context: Optional[Dict[str, Dict[str, Deque[Dict[str, Any]]]]] = None,
) -> List[Dict[str, Any]]:
    """Attach Determination matches and Concordance-lite to each hit, with a significance composite.

    - Matches hit domains (from enriched keywords and target) to PD window types in range ±window.
    - Adds quick SR/LR theme matches based on aspects of SR Sun/Moon or LR Moon to natal angles.
    - Computes overall_concordance in [0,1] and a 0–100 'significance' composite.
    """
    if not isinstance(hits, list) or not hits:
        return hits
    active_registry_context = (
        registry_context
        if isinstance(registry_context, dict)
        else _new_transit_registry_context()
    )
    simultaneous_registry = active_registry_context.setdefault(
        'simultaneous', collections.defaultdict(collections.deque)
    )
    malefic_registry = active_registry_context.setdefault(
        'malefic', collections.defaultdict(collections.deque)
    )
    # Determine significance formula toggle (env override unless explicit)
    try:
        if use_new_significance is None:
            import os as _os
            envv = str(_os.environ.get('TRANSITS_SIG_BETA', '1')).lower()
            use_new = envv in {'1','true','yes','new','beta'}
        else:
            use_new = bool(use_new_significance)
    except Exception:
        use_new = True
    # Determinations context
    det_ctx = compute_determinations(natal_chart_data or {})
    by_planet = det_ctx.get('by_planet', {}) if isinstance(det_ctx, dict) else {}
    # Natal angles
    cusps = _extract_cusps(natal_chart_data or {})
    natal_asc = float(cusps[0]) if len(cusps) >= 1 else None
    natal_mc = float(cusps[9]) if len(cusps) >= 10 else None
    house_rulers = _house_rulers_map(natal_chart_data or {})

    tz_meta = {}
    if isinstance(natal_chart_data, dict):
        tz_meta = natal_chart_data.get('timezone_info') or {}
    _snapshot_location = observer_location or tz_meta.get('location_name')
    if not _snapshot_location:
        coords = tz_meta.get('coordinates') if isinstance(tz_meta, dict) else None
        try:
            lat = coords.get('latitude') if isinstance(coords, dict) else None
            lon = coords.get('longitude') if isinstance(coords, dict) else None
            if lat is not None and lon is not None:
                _snapshot_location = f"{float(lat):.4f}, {float(lon):.4f}"
        except Exception:
            _snapshot_location = None
    _snapshot_timezone = observer_timezone or tz_meta.get('timezone') or 'UTC'

    # Transit timestamp dt
    try:
        t_dt = _parse_iso_datetime_utc(str(transit_timestamp_iso))
        t_year = t_dt.year
    except Exception:
        t_dt = None
        t_year = None

    birth_dt = _extract_birth_datetime(natal_chart_data or {})
    native_age_years: Optional[float] = None
    if birth_dt and t_dt:
        try:
            delta = t_dt.astimezone(timezone.utc) - birth_dt
            native_age_years = max(0.0, delta.total_seconds() / (365.2425 * 86400.0))
        except Exception:
            native_age_years = None
    transit_month = t_dt.month if t_dt else None
    is_summer_season = bool(transit_month in {6, 7, 8})

    if t_dt is not None:
        _prune_registry(simultaneous_registry, t_dt - timedelta(days=_SIMULTANEOUS_HORIZON_DAYS * 2.0))
        _prune_registry(malefic_registry, t_dt - timedelta(days=_SUCCESSIVE_HORIZON_DAYS * 1.2))

    # SR/LR graded similarity (0..1) using revolution charts when possible
    def _sr_lr_scores() -> Dict[str, Any]:
        out = {
            'sr_score': 0.0,
            'lr_score': 0.0,
            'sr_domains': set(),
            'lr_domains': set(),
            'sr_chart': {},
            'lr_chart': {},
        }
        if t_dt is None or swe is None:
            return out
        natal_dict = natal_chart_data or {}
        house_code = None
        if isinstance(natal_dict, dict):
            house_code = natal_dict.get('house_system_code')
        sr_ctx: Optional[Dict[str, Any]] = None
        sr_dt: Optional[datetime] = None
        try:
            natal_pl = _normalize_planets(natal_dict)
            ns = natal_pl.get('Sun', {})
            ns_lon = float(ns.get('longitude')) if isinstance(ns, dict) and ns.get('longitude') is not None else None
            if compute_solar_return_timestamp and ns_lon is not None and t_year is not None:
                sr_dt = compute_solar_return_timestamp(ns_lon, int(t_year))
        except Exception:
            sr_dt = None
        if get_revolution_context and sr_dt:
            sr_ctx = get_revolution_context(
                'solar',
                sr_dt,
                natal_chart=natal_dict,
                location=_snapshot_location,
                timezone_label=_snapshot_timezone,
                house_system_code=house_code,
                pd_windows=pd_windows,
            )
        sr_dirs: List[Dict[str, Any]] = []
        if sr_ctx:
            if compute_primary_direction_windows and sr_dt is not None:
                try:
                    sr_chart = sr_ctx.get('chart_data') or {}
                    sr_dirs = compute_primary_direction_windows(
                        sr_dt,
                        sr_dt.year,
                        sr_chart,
                        include_modern=include_modern,
                    )
                except Exception:
                    sr_dirs = []
            out['sr_domains'] = set(sr_ctx.get('domains') or [])
            out['sr_score'] = float((sr_ctx.get('similarity') or {}).get('normalized') or 0.0)
            out['sr_chart'] = sr_ctx.get('chart_data') or {}
            out['sr_context'] = sr_ctx
            out['sr_summary'] = {
                'timestamp': sr_ctx.get('timestamp'),
                'score': (sr_ctx.get('similarity') or {}).get('score'),
                'normalized_score': (sr_ctx.get('similarity') or {}).get('normalized'),
                'domains': list(sr_ctx.get('domains') or []),
                'determinations': list(sr_ctx.get('determination_summary') or []),
                'signals': list(sr_ctx.get('support_signals') or []),
                'tags': list((sr_ctx.get('similarity') or {}).get('tags') or []),
            }
        else:
            sr_dirs = []
            out['sr_context'] = None
            out['sr_summary'] = None

        lr_ctx: Optional[Dict[str, Any]] = None
        lr_dt: Optional[datetime] = None
        try:
            if compute_nearest_lunar_return and t_dt is not None:
                natal_pl = _normalize_planets(natal_dict)
                nm = natal_pl.get('Moon', {})
                nm_lon = float(nm.get('longitude')) if isinstance(nm, dict) and nm.get('longitude') is not None else None
                nm_lat = float(nm.get('latitude')) if isinstance(nm, dict) and nm.get('latitude') is not None else None
                if nm_lon is not None:
                    lr_dt = compute_nearest_lunar_return(nm_lon, t_dt, nm_lat)
        except Exception:
            lr_dt = None
        if get_revolution_context and lr_dt:
            lr_ctx = get_revolution_context(
                'lunar',
                lr_dt,
                natal_chart=natal_dict,
                location=_snapshot_location,
                timezone_label=_snapshot_timezone,
                house_system_code=house_code,
                sr_chart=out.get('sr_chart'),
                pd_windows=pd_windows,
            )
        lr_dirs: List[Dict[str, Any]] = []
        if lr_ctx:
            if compute_primary_direction_windows:
                try:
                    lr_chart = lr_ctx.get('chart_data') or {}
                    lr_dirs = compute_primary_direction_windows(
                        lr_dt,
                        lr_dt.year,
                        lr_chart,
                        include_modern=False,
                        window_days=30,
                    )
                except Exception:
                    lr_dirs = []
            out['lr_domains'] = set(lr_ctx.get('domains') or [])
            out['lr_score'] = float((lr_ctx.get('similarity') or {}).get('normalized') or 0.0)
            out['lr_chart'] = lr_ctx.get('chart_data') or {}
            out['lr_context'] = lr_ctx
            out['lr_summary'] = {
                'timestamp': lr_ctx.get('timestamp'),
                'score': (lr_ctx.get('similarity') or {}).get('score'),
                'normalized_score': (lr_ctx.get('similarity') or {}).get('normalized'),
                'domains': list(lr_ctx.get('domains') or []),
                'determinations': list(lr_ctx.get('determination_summary') or []),
                'signals': list(lr_ctx.get('support_signals') or []),
                'tags': list((lr_ctx.get('similarity') or {}).get('tags') or []),
            }
        else:
            lr_dirs = []
            out['lr_context'] = None
            out['lr_summary'] = None
        out['sr_directions'] = sr_dirs
        out['lr_directions'] = lr_dirs
        return out

    # SR/LR similarity — memoized per coarse scan context to avoid recomputation across steps
    try:
        natal_dict_for_key = natal_chart_data or {}
        house_code_key = natal_dict_for_key.get('house_system_code') if isinstance(natal_dict_for_key, dict) else None
        pl_idx = _normalize_planets(natal_dict_for_key)
        sun_lon_key = None
        moon_lon_key = None
        try:
            sun_lon_key = float((pl_idx.get('Sun') or {}).get('longitude')) if isinstance(pl_idx.get('Sun'), dict) else None
        except Exception:
            sun_lon_key = None
        try:
            moon_lon_key = float((pl_idx.get('Moon') or {}).get('longitude')) if isinstance(pl_idx.get('Moon'), dict) else None
        except Exception:
            moon_lon_key = None
        pd_len = len(pd_windows or [])
        memo_key = (
            int(t_year) if t_year is not None else None,
            str(house_code_key or ''),
            str(_snapshot_location or ''),
            str(_snapshot_timezone or ''),
            round(float(sun_lon_key or 0.0), 1),
            round(float(moon_lon_key or 0.0), 1),
            int(pd_len),
        )
    except Exception:
        memo_key = None
    sr_lr_once = None
    if memo_key is not None:
        try:
            sr_lr_once = _SR_LR_MEMO.get(memo_key)
        except Exception:
            sr_lr_once = None
    if not isinstance(sr_lr_once, dict):
        sr_lr_once = _sr_lr_scores()
        try:
            if memo_key is not None:
                if len(_SR_LR_MEMO) >= _SR_LR_MEMO_MAX:
                    try:
                        _SR_LR_MEMO.pop(next(iter(_SR_LR_MEMO)))
                    except Exception:
                        _SR_LR_MEMO.clear()
                _SR_LR_MEMO[memo_key] = sr_lr_once
        except Exception:
            pass

    child_det_keys = {'children', 'children_house', 'children_matters', 'fertility', '5th_house', '5th_house_matters'}
    death_det_keys = {'death', 'death_house', '8th_house', '8th_house_matters'}
    violence_det_keys = {'violence', 'danger', 'accident', 'death', '8th_house', '8th_house_matters'}
    family_det_keys = {'relevant_family_house', 'family', 'home', 'children', 'relationships', 'marriage'}
    loss_det_keys = {'loss', 'grief', 'death'}
    travel_det_keys = {'travel', 'short_travel', 'short_journeys', 'long_travel', 'journeys', 'movement', '3rd_house', '3rd_house_matters', '9th_house', '9th_house_matters'}
    relocation_det_keys = {'relocation', 'change', 'move', 'moving_home', '4th_house', '4th_house_matters', '9th_house', '9th_house_matters', 'home'}
    danger_det_keys = {'danger', 'life_threat', 'life_threats', 'violence', 'crisis', 'emergency', 'death', '8th_house', '8th_house_matters', '12th_house', '12th_house_matters', '1st_house', '1st_house_matters'}
    accident_det_keys = danger_det_keys | {'accident', 'accidents', 'sudden_events', 'collision', 'crash', 'catastrophe', 'disaster', 'major_accident', '3rd_house', '3rd_house_matters', '6th_house', '6th_house_matters'}
    near_death_det_keys = danger_det_keys | {'near_death', 'life_threat', 'life_threatening', 'critical', 'brush_with_death'}
    fire_det_keys = danger_det_keys | {'fire', 'burn', 'burns', 'combustion', 'scorching', 'destruction', 'flames', 'heat', '4th_house', '4th_house_matters'}
    water_det_keys = danger_det_keys | {'water', 'drowning', 'flood', 'submersion', 'river', 'ocean', 'pool', 'inundation', '4th_house', '4th_house_matters'}
    fall_det_keys = danger_det_keys | {'fall', 'falls', 'height', 'plunge', 'descent', 'sudden_drop'}
    spiritual_det_keys = {'spirituality', 'consciousness', 'awareness', 'illumination', 'understanding', 'belief', 'faith', '9th_house', '9th_house_matters', '12th_house', '12th_house_matters'}
    religion_det_keys = spiritual_det_keys | {'religion', 'religious', 'conversion', 'creed', 'doctrine', 'baptism'}
    pilgrimage_det_keys = religion_det_keys | travel_det_keys | {'pilgrimage', 'sacred_journey', 'holy_place', 'holy_travel'}
    mystical_det_keys = spiritual_det_keys | {'mysticism', 'mystical', 'vision', 'transcendence', 'occult', 'esoteric', 'metaphysical'}
    publishing_det_keys = {'writing', 'communication', 'publishing', 'publication', 'author', 'manuscript', 'book', 'article', 'paper', 'journal', '3rd_house', '3rd_house_matters', '9th_house', '9th_house_matters', '10th_house', '10th_house_matters'}
    creativity_det_keys = {'creativity', 'creative', 'art', 'arts', 'performance', 'exhibition', 'show', 'self_expression', 'talent', '5th_house', '5th_house_matters', '11th_house', '11th_house_matters'}
    innovation_det_keys = {'innovation', 'innovative', 'discovery', 'invention', 'breakthrough', 'research', 'science', 'insight', 'eureka', 'technology', '9th_house', '9th_house_matters', '11th_house', '11th_house_matters', '3rd_house', '3rd_house_matters'}
    possession_loss_det_keys = {'possessions', 'property', 'money', 'wealth', 'resources', 'goods', 'assets', '2nd_house', '2nd_house_matters', 'loss', 'theft', 'robbery', 'burglary'}
    health_det_keys = {'health', 'illness', 'disease', 'sickness', 'vitality', '6th_house', '6th_house_matters', '1st_house', '1st_house_matters'}
    acute_health_det_keys = health_det_keys | {'acute', 'sudden', 'inflammation', 'infection'}
    chronic_health_det_keys = health_det_keys | {'chronic', 'persistent', 'long_term', 'degenerative', '12th_house', '12th_house_matters'}
    fever_det_keys = health_det_keys | {'fever', 'heat', 'temperature', 'pyrexia', 'burning'}
    injury_det_keys = {'injury', 'trauma', 'wound', 'accident', 'violence', 'sudden_events', '1st_house', '6th_house', '8th_house'}
    surgery_det_keys = health_det_keys | {'surgery', 'operation', 'cutting', 'procedure', 'medical', 'intervention', '8th_house', '12th_house'}
    hospital_det_keys = {'hospital', 'confinement', 'institution', 'admission', '12th_house', '12th_house_matters', 'ward', 'clinic'}
    recovery_det_keys = {'recovery', 'healing', 'restoration', 'recuperation', 'rehabilitation', 'health', '1st_house', '6th_house'}
    property_det_keys = {'property', 'real_estate', 'land', 'home', 'estate', 'ic', '4th_house', '4th_house_matters'}
    wealth_det_keys = {'wealth', 'money', 'income', 'profits', 'gain', '2nd_house', '2nd_house_matters', '11th_house', '11th_house_matters'}
    speculation_det_keys = {'speculation', 'trading', 'investment', 'gambling', 'stocks', 'risk', '5th_house', '5th_house_matters'}
    shared_gain_det_keys = {'shared_resources', 'inheritance', 'legacy', 'partner_finances', 'insurance', 'windfall', '8th_house', '8th_house_matters'}
    shared_loss_det_keys = shared_gain_det_keys | {'debt', 'obligations', 'credit', 'taxes', 'loss'}
    marriage_det_keys = {'marriage', 'union', 'partners', 'partnership', 'wedding', '7th_house', '7th_house_matters'}
    relationship_det_keys = marriage_det_keys | {'relationships', 'romance', 'companionship'}
    legal_det_keys = {'legal', 'law', 'lawsuit', 'court', 'justice', 'judgment', 'trial', 'verdict', 'litigation', '7th_house', '7th_house_matters', '9th_house', '9th_house_matters', '10th_house', '10th_house_matters'}
    imprisonment_det_keys = {'imprisonment', 'confinement', 'prison', 'detention', 'arrest', 'incarceration', '12th_house', '12th_house_matters'}
    twelfth_det_keys = {'12th_house', '12th_house_matters', 'hidden_enemies', 'self_undoing', 'institution', 'hospital', 'prison', 'confinement'}
    confusion_det_keys = {'confusion', 'fog', 'delusion', 'uncertainty', 'bewilderment', 'neptune', '3rd_house', '3rd_house_matters', '12th_house', '12th_house_matters'}
    reputation_det_keys = {'reputation', 'honors', 'career', 'status', 'public', 'standing', 'recognition', '10th_house', '10th_house_matters', 'loss', 'disgrace', 'scandal', 'dishonor'}
    authority_det_keys = {'authority', 'executive', 'leadership', 'command', 'government', 'ruler', 'mc', '10th_house', '10th_house_matters', 'power', 'sun', 'sovereign'}
    conflict_det_keys = {'conflict', 'war', 'battle', 'violence', 'military', 'martial', 'aggression', '7th_house', '7th_house_matters', '1st_house', '1st_house_matters'}
    enemy_det_keys = {'enemy', 'enemies', 'adversary', 'opponent', 'opposition', '7th_house', '7th_house_matters', '12th_house', '12th_house_matters'}
    foreign_det_keys = {'foreign', 'abroad', 'international', 'diplomacy', 'expedition', '9th_house', '9th_house_matters'}
    homeland_det_keys = {'homeland', 'home', 'foundation', 'defense', 'protection', '4th_house', '4th_house_matters', '1st_house', '1st_house_matters'}
    education_det_keys = {
        'education', 'learning', 'studies', 'study', 'testing', 'exam', 'exams', 'mental_ability',
        'academic', 'achievement', 'academic_success', '9th_house', '9th_house_matters',
        '3rd_house', '3rd_house_matters'
    }
    education_enrollment_det_keys = education_det_keys | {'new_beginnings', 'enrollment', 'matriculation', 'acceptance', 'opportunity'}
    education_setback_det_keys = education_det_keys | {'difficulties', 'obstacles', 'setback', 'failure'}

    pd_windows_cache: Dict[int, List[Dict[str, Any]]] = {}
    pd_windows_source = list(pd_windows or [])

    def _pd_windows_for_year(year: Optional[int]) -> List[Dict[str, Any]]:
        if year is None:
            return []
        if year in pd_windows_cache:
            return pd_windows_cache[year]
        subset: List[Dict[str, Any]] = []
        for entry in pd_windows_source:
            if not isinstance(entry, dict):
                continue
            ts_raw = entry.get('timestamp')
            ts_year: Optional[int] = None
            if ts_raw:
                try:
                    ts = _parse_iso_datetime_utc(str(ts_raw))
                    ts_year = ts.year
                except Exception:
                    ts_year = None
            if ts_year is None:
                try:
                    ts_year = int(entry.get('year'))  # optional metadata
                except Exception:
                    ts_year = None
            if ts_year is None or int(ts_year) == int(year):
                subset.append(entry)
        if not subset and pd_windows_source:
            subset = list(pd_windows_source)
        pd_windows_cache[year] = subset
        return subset

    def _has_child_det(det: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(det, dict):
            return False
        try:
            scores = det.get('determinationScores') or {}
            by_area = scores.get('by_area') if isinstance(scores, dict) else scores
        except Exception:
            by_area = None
        if not isinstance(by_area, dict):
            return False
        for key, val in by_area.items():
            try:
                name = str(key).lower()
                if name in child_det_keys and abs(float(val)) >= 0.6:
                    return True
            except Exception:
                continue
        return False

    def _top_has_child(items: Optional[List[Dict[str, Any]]]) -> bool:
        if not isinstance(items, list):
            return False
        for item in items:
            try:
                name = str(item.get('area') or '').lower()
                score = abs(float(item.get('score') or item.get('value') or 0.0))
                if name in child_det_keys and score >= 0.6:
                    return True
            except Exception:
                continue
        return False
    try:
        jd_now = _jd_from_iso(transit_timestamp_iso)
    except Exception:
        jd_now = None

    def _normalize_domain(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        key = str(name).lower()
        key = _DOMAIN_SYNONYMS.get(key, key)
        return key

    def _primary_domain(dom_list: List[str], row: Optional[Dict[str, Any]] = None) -> Optional[str]:
        chosen = _pick_contextual_domain(dom_list, row=row)
        if chosen:
            return _normalize_domain(chosen)
        for dom in dom_list:
            norm = _normalize_domain(dom)
            if norm in _DOMAIN_PRIMARY_HOUSE:
                return norm
        return _normalize_domain(dom_list[0]) if dom_list else None

    def _planet_lon_at(name: str) -> Optional[float]:
        if jd_now is None:
            return None
        try:
            return _lon_lat_at(jd_now, name)[0]
        except Exception:
            return None

    def _planet_house_in_chart(chart: Dict[str, Any], planet_name: str) -> Optional[int]:
        planets = chart.get('planets') if isinstance(chart, dict) else None
        if isinstance(planets, dict):
            info = planets.get(planet_name)
            if isinstance(info, dict) and info.get('house') is not None:
                try:
                    return int(info.get('house'))
                except Exception:
                    return None
        if isinstance(planets, list):
            for row in planets:
                if not isinstance(row, dict):
                    continue
                if str(row.get('planet')) == planet_name and row.get('house') is not None:
                    try:
                        return int(row.get('house'))
                    except Exception:
                        return None
        return None

    def _natal_cluster_map(cd: Dict[str, Any]) -> Tuple[Dict[int, List[str]], Dict[str, List[str]]]:
        clusters: Dict[int, List[str]] = {}
        planet_to_cluster: Dict[str, List[str]] = {}
        planets = (cd or {}).get('planets')
        if isinstance(planets, dict):
            iterable = planets.items()
        elif isinstance(planets, list):
            iterable = [(str(row.get('planet')), row) for row in planets if isinstance(row, dict) and row.get('planet')]
        else:
            iterable = []
        for name, row in iterable:
            if not isinstance(row, dict):
                continue
            house = row.get('house')
            try:
                house = int(house) if house is not None else None
            except Exception:
                house = None
            if house is None:
                continue
            clusters.setdefault(house, []).append(str(name))
        for house, members in list(clusters.items()):
            if len(members) < 3:
                clusters.pop(house)
                continue
            members_sorted = sorted(members)
            clusters[house] = members_sorted
            for m in members_sorted:
                planet_to_cluster[m] = members_sorted
        return clusters, planet_to_cluster

    cluster_by_house, planet_cluster_map = _natal_cluster_map(natal_chart_data or {})

    def _strong_domains_for_planet(planet: str, threshold: float = 0.5) -> Set[str]:
        det = by_planet.get(planet) or {}
        scores = (det.get('determinationScores') or {}).get('by_area')
        if not isinstance(scores, dict):
            scores = det.get('determinationScores') if isinstance(det.get('determinationScores'), dict) else {}
        out: Set[str] = set()
        if isinstance(scores, dict):
            for name, val in scores.items():
                try:
                    if abs(float(val)) >= threshold:
                        out.add(str(name))
                except Exception:
                    continue
        return out

    def _planets_related(p1: str, p2: str) -> bool:
        return bool(_strong_domains_for_planet(p1) & _strong_domains_for_planet(p2))

    def _partile_weight(orb: float, planet: str) -> float:
        if orb <= 0.5:
            return 1.0
        if orb <= 1.0:
            return 0.85
        if orb <= 3.0:
            return 0.6
        wide_limit = 6.0 if planet == 'Moon' else 8.0
        if orb <= wide_limit:
            return 0.3
        return 0.0

    def _aspect_name_from_angle(angle: float, tolerance: float = 3.0) -> Optional[str]:
        allowed = {0.0, 60.0, 90.0, 120.0, 180.0}
        for asp in ASPECT_SET:
            base = None
            label = None
            if isinstance(asp, (list, tuple)) and len(asp) >= 2:
                try:
                    base = float(asp[0])
                except Exception:
                    base = None
                label = str(asp[1])
            elif isinstance(asp, dict):
                try:
                    base = float(asp.get('angle') or 0.0)
                except Exception:
                    base = None
                label = str(asp.get('label') or '')
            if base is None or base not in allowed or label is None:
                continue
            diff = abs(((angle - base + 180.0) % 360.0) - 180.0)
            if diff <= tolerance:
                return label or None
        return None

    def _light_coupling_multiplier(row: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        A = str(row.get('transiting') or '')
        if jd_now is None or A in ('Sun', 'Moon'):
            return 1.0, []
        lonA = _planet_lon_at(A)
        if lonA is None:
            return 1.0, []
        entries: List[Dict[str, Any]] = []
        multiplier = 1.0
        for light in ('Sun', 'Moon'):
            lonL = _planet_lon_at(light)
            if lonL is None:
                continue
            angle = abs(((lonA - lonL + 180.0) % 360.0) - 180.0)
            aspect_label = _aspect_name_from_angle(angle)
            if not aspect_label:
                continue
            base_boost = 1.2
            if 'conj' in aspect_label.lower():
                base_boost = 1.5
            elif any(k in aspect_label.lower() for k in ('trine', 'sext')):
                base_boost = 1.3
            related_mult = 1.0
            if _planets_related(A, light):
                related_mult = 1.3
            multiplier *= base_boost * related_mult
            entries.append({'light': light, 'aspect': aspect_label, 'boost': round(base_boost * related_mult, 3)})
        return multiplier, entries


    def _multiple_transit_multiplier(idx: int, t_dt: Optional[datetime]) -> Tuple[float, Optional[Dict[str, Any]]]:
        if t_dt is None:
            return 1.0, None

        base_row = hits[idx]
        base_planet = str(base_row.get('transiting') or '')
        base_label = str(base_row.get('target_label') or base_row.get('natal') or '')

        def _window_hours_for(planet: str) -> float:
            return 12.0 if planet == 'Moon' else 48.0  # ±6h for Moon, ±24h for others

        def _is_conjunction(label: Optional[str]) -> bool:
            return bool(label) and 'conj' in label.lower()

        candidates: List[Dict[str, Any]] = []

        seen_planets: Set[str] = set()

        for j, other in enumerate(hits):
            if j == idx:
                continue
            other_planet = str(other.get('transiting') or '')
            if not other_planet or other_planet == base_planet or other_planet in seen_planets:
                continue
            window = _window_hours_for(base_planet) + _window_hours_for(other_planet)
            if window <= 0:
                continue
            candidates.append({
                'planet': other_planet,
                'timestamp': t_dt,
                'aspect': str(other.get('aspect') or ''),
                'domains': set(domains_cache.get(j) or []),
                'hourDelta': 0.0,
            })
            seen_planets.add(other_planet)

        for entry in simultaneous_registry.get(base_label, []):
            other_planet = entry.get('planet')
            if not other_planet or other_planet == base_planet or other_planet in seen_planets:
                continue
            window = _window_hours_for(base_planet) + _window_hours_for(other_planet)
            if window <= 0:
                continue
            diff_hours = abs((t_dt - entry['timestamp']).total_seconds()) / 3600.0
            if diff_hours <= window:
                copy_entry = dict(entry)
                copy_entry['hourDelta'] = diff_hours
                candidates.append(copy_entry)
                seen_planets.add(other_planet)

        if not candidates:
            return 1.0, None

        related: List[Dict[str, Any]] = []
        has_sun = base_planet == 'Sun'
        has_moon = base_planet == 'Moon'
        conj_count = 1 if _is_conjunction(str(base_row.get('aspect') or '')) else 0

        for cand in candidates:
            other_planet = cand['planet']
            if not _planets_related(base_planet, other_planet):
                continue
            related.append(cand)
            if other_planet == 'Sun':
                has_sun = True
            if other_planet == 'Moon':
                has_moon = True
            if _is_conjunction(str(cand.get('aspect') or '')):
                conj_count += 1

        total_related = 1 + len(related)
        if total_related < _CLUSTER_MIN_COUNT:
            return 1.0, None

        if not related:
            return 1.0, None

        multiplier = 2.0
        if conj_count >= 2:
            multiplier *= 1.1
        if has_sun and has_moon:
            multiplier *= 1.1
        multiplier = min(multiplier, 3.0)

        meta = {
            'count': total_related,
            'planets': [base_planet] + [c['planet'] for c in related],
            'hours': [round(c.get('hourDelta', 0.0), 2) for c in related],
            'hasLights': has_sun and has_moon,
            'conjunctions': conj_count,
            'multiplier': round(multiplier, 3),
        }
        return multiplier, meta

    def _mutual_strengthening_multiplier(idx: int) -> Tuple[float, Optional[List[Dict[str, Any]]]]:
        base_domains = set(domains_cache.get(idx) or [])
        if not base_domains:
            return 1.0, None
        A = str(hits[idx].get('transiting') or '')
        pairs: List[Dict[str, Any]] = []
        for j, other in enumerate(hits):
            if j == idx:
                continue
            if str(other.get('target_label') or other.get('natal') or '') == str(hits[idx].get('target_label') or hits[idx].get('natal') or ''):
                continue
            other_domains = set(domains_cache.get(j) or [])
            if not (base_domains & other_domains):
                continue
            B = str(other.get('transiting') or '')
            if not _planets_related(A, B):
                continue
            pairs.append({'with': B, 'domains': list(base_domains & other_domains)})
        if not pairs:
            return 1.0, None
        return 1.0 + 0.3 * len(pairs), pairs

    def _revolution_danger_multiplier(row: Dict[str, Any]) -> Tuple[float, Optional[Dict[str, Any]]]:
        planet = str(row.get('transiting') or '')
        target_label = str(row.get('target_label') or row.get('natal') or '')
        rev_chart = sr_lr_once.get('sr_chart') or {}
        house = _planet_house_in_chart(rev_chart, planet)
        if house is None or house not in (8, 12):
            return 1.0, None
        quality_score = float(row.get('quality_score') or 0.0)
        is_malefic = planet in ('Mars', 'Saturn')
        base = 1.2
        if is_malefic and quality_score <= 0.0:
            base = 2.0 if target_label.startswith('Asc') else 1.7
        elif is_malefic or quality_score <= 0.0:
            base = 1.5
        elif target_label.startswith('Asc'):
            base = 1.3
        return base, {'revolutionHouse': house, 'multiplier': round(base, 3)}

    def _cluster_bonus(row: Dict[str, Any]) -> Tuple[float, Optional[Dict[str, Any]]]:
        target_label = str(row.get('target_label') or row.get('natal') or '')
        base = target_label.replace(' (antiscia)', '').replace(' (contra-antiscia)', '')
        if base not in planet_cluster_map:
            return 0.0, None
        members = planet_cluster_map[base]
        return len(members) * 10.0, {'clusterMembers': members}

    def _successive_malefic_multiplier(idx: int, pd_info: Dict[str, Any], doms: List[str], t_dt: Optional[datetime], sr_lr: Dict[str, Any]) -> Tuple[float, Optional[Dict[str, Any]]]:
        if t_dt is None:
            return 1.0, None
        malefics = {'Saturn', 'Mars'}
        row = hits[idx]
        planet = str(row.get('transiting') or '')
        if planet not in malefics:
            return 1.0, None
        target = str(row.get('target_label') or row.get('natal') or '')
        domains_set = set(doms)

        death_domains = {'death', 'danger', 'shared_resources', 'illness', 'life'}
        pd_matches = pd_info.get('matches') or []
        pd_support = False
        for match in pd_matches:
            dtype = str((match or {}).get('type') or '').lower()
            if any(key in dtype for key in ('death', 'danger', '8th', '12th', 'illness', 'shared')):
                pd_support = True
                break
        sr_domains = set(sr_lr.get('sr_domains') or [])
        sr_support = bool(sr_domains & death_domains)
        if not (pd_support and sr_support):
            return 1.0, None

        registry = malefic_registry.get(target, [])
        if not registry:
            return 1.0, None
        window_days = 30.0
        relevant = []
        for entry in registry:
            if entry.get('planet') not in malefics:
                continue
            diff = (t_dt - entry['timestamp']).total_seconds() / 86400.0
            if 0.0 < diff <= window_days:
                relevant.append({'planet': entry['planet'], 'days': diff, 'timestamp': entry['timestamp']})
        if not relevant:
            return 1.0, None
        closest = min(relevant, key=lambda r: r['days'])
        delta = closest['days']
        if delta <= 7.0:
            multiplier = 1.6
        elif delta <= 30.0:
            multiplier = 1.35
        elif delta <= 90.0:
            multiplier = 1.2
        else:
            multiplier = 1.1
        meta = {
            'priorPlanet': closest['planet'],
            'daysApart': round(delta, 2),
            'target': target,
            'pdSupport': pd_support,
            'srSupport': sr_support,
        }
        return multiplier, meta


    def _max_det_area(det: Optional[Dict[str, Any]], keys: Set[str]) -> float:
        if not isinstance(det, dict) or not keys:
            return 0.0
        try:
            scores = det.get('determinationScores') or {}
            by_area = scores.get('by_area') if isinstance(scores, dict) else scores
        except Exception:
            by_area = None
        if not isinstance(by_area, dict):
            return 0.0
        best = 0.0
        keyset = {str(k).lower() for k in keys}
        for name, val in by_area.items():
            try:
                if str(name).lower() in keyset:
                    best = max(best, abs(float(val)))
            except Exception:
                continue
        return best

    def _max_area_list(items: Optional[List[Dict[str, Any]]], keys: Set[str]) -> float:
        if not isinstance(items, list) or not keys:
            return 0.0
        best = 0.0
        keyset = {str(k).lower() for k in keys}
        for item in items:
            try:
                if str(item.get('area') or '').lower() in keyset:
                    best = max(best, abs(float(item.get('score') or item.get('value') or 0.0)))
            except Exception:
                continue
        return best

    def _drop_token(row: Dict[str, Any], token: str) -> None:
        if not token:
            return
        kw_list = row.get('keywords')
        if isinstance(kw_list, list):
            row['keywords'] = [t for t in kw_list if t != token]
        ek_list = row.get('enriched_keywords')
        if isinstance(ek_list, list):
            row['enriched_keywords'] = [t for t in ek_list if t != token]

    # Helper: domains for a hit
    def _hit_domains(row: Dict[str, Any]) -> List[str]:
        doms: List[str] = []
        try:
            doms.extend([str(x) for x in (row.get('enriched_keywords') or [])])
        except Exception:
            pass
        # Map base labels
        lbl = str(row.get('target_label') or row.get('natal') or '')
        base = lbl.replace(' (antiscia)','').replace(' (contra-antiscia)','')
        if base == 'Asc':
            doms.append('life')
        if base == 'MC':
            doms.append('honors')
        # C# → house domain
        if base.startswith('C') and base[1:].isdigit():
            try:
                h = int(base[1:])
                doms.append({'1':'life','2':'money','3':'short_journeys','4':'home','5':'children','6':'health','7':'marriage','8':'shared_resources','9':'belief','10':'career','11':'friends','12':'secrets'}.get(str(h),'') or '')
            except Exception:
                pass
        # Clean
        return [d for d in doms if d]

    # PD match within provided windows
    def _direction_match(ts_iso: str, doms: List[str], windows: List[Dict[str, Any]]) -> Dict[str, Any]:
        res = {'matches': [], 'signification_score': 0.0, 'timing_score': 0.0}
        if not windows:
            return res
        try:
            transit_dt = _parse_iso_datetime_utc(str(ts_iso))
        except Exception:
            return res
        for w in windows:
            try:
                start_dt = _parse_iso_datetime_utc(str(w.get('start')))
                end_dt = _parse_iso_datetime_utc(str(w.get('end')))
                if not (start_dt <= transit_dt <= end_dt):
                    continue
                item = w.get('item') or {}
                dtype = str(item.get('type') or '')
                strength = float(item.get('strength') or 0.0)
                match_ts = str(w.get('timestamp') or '')
                res['matches'].append({
                    'label': w.get('label'),
                    'type': dtype,
                    'quality': item.get('quality'),
                    'strength': strength,
                    'motion': item.get('motion'),
                    'timestamp': match_ts,
                })
                if dtype and dtype in doms:
                    res['signification_score'] = max(res['signification_score'], strength)
                elif not dtype:
                    res['signification_score'] = max(res['signification_score'], strength * 0.7)
                else:
                    res['signification_score'] = max(res['signification_score'], strength * 0.6)
                try:
                    center_dt = _parse_iso_datetime_utc(match_ts)
                    delta_days = abs((transit_dt - center_dt).total_seconds()) / 86400.0
                except Exception:
                    delta_days = None
                if delta_days is not None:
                    if delta_days <= 1.0:
                        timing = 20.0
                    elif delta_days <= 3.0:
                        timing = 15.0
                    elif delta_days <= 7.0:
                        timing = 10.0
                    elif delta_days <= 14.0:
                        timing = 5.0
                    else:
                        timing = 0.0
                    res['timing_score'] = max(res['timing_score'], timing)
            except Exception:
                continue
        return res

    # Cache domains for each hit (used for syzygies and determination matching)
    domains_cache: Dict[int, List[str]] = {}
    for idx, row in enumerate(hits):
        try:
            doms = _hit_domains(row)
            domains_cache[idx] = doms
            # Attach simple determination match structure
            A = str(row.get('transiting') or '')
            base_lbl = str(row.get('target_label') or row.get('natal') or '')
            base_lbl = base_lbl.replace(' (antiscia)','').replace(' (contra-antiscia)','')
            det_trans = by_planet.get(A) or {}
            det_tgt = by_planet.get(base_lbl) or {}
            # Summarize target top life-areas
            top_areas: List[Dict[str, Any]] = []
            try:
                areas = (det_tgt.get('determinationScores') or {}).get('by_area') or {}
                items = sorted(((k, float(v)) for k,v in areas.items()), key=lambda x: -abs(x[1]))
                for k,v in items[:3]:
                    top_areas.append({'area': k, 'score': round(v,2)})
            except Exception:
                top_areas = []
            row['determination'] = {
                'matched_domains': doms,
                'transitingPlanetDetermination': {
                    'planet': A,
                    'naturalSignifications': det_trans.get('naturalSignifications') or [],
                    'nature': (det_trans.get('nature') or {}).get('primary') if isinstance(det_trans.get('nature'), dict) else None,
                },
                'targetDetermination': {
                    'planet': base_lbl if base_lbl in by_planet else None,
                    'house': (det_tgt.get('housePosition') or {}).get('house') if isinstance(det_tgt.get('housePosition'), dict) else None,
                    'topAreas': top_areas,
                },
            }
            # Determination strength (-1..1): signed domain match, with house emphasis and light nature modulation.
            try:
                doms_norm = {
                    _normalize_domain(d)
                    for d in doms
                    if _normalize_domain(d)
                }
                trans_scores_raw = ((det_trans.get('determinationScores') or {}).get('by_area') or {})
                tgt_scores_raw = ((det_tgt.get('determinationScores') or {}).get('by_area') or {})
                trans_scores: Dict[str, float] = {}
                tgt_scores: Dict[str, float] = {}
                if isinstance(trans_scores_raw, dict):
                    for area_name, area_score in trans_scores_raw.items():
                        norm_area = _normalize_domain(area_name)
                        if not norm_area:
                            continue
                        trans_scores[norm_area] = float(area_score)
                if isinstance(tgt_scores_raw, dict):
                    for area_name, area_score in tgt_scores_raw.items():
                        norm_area = _normalize_domain(area_name)
                        if not norm_area:
                            continue
                        tgt_scores[norm_area] = float(area_score)

                matched_scores: List[float] = []
                for norm_dom in doms_norm:
                    if norm_dom in trans_scores:
                        matched_scores.append(float(trans_scores[norm_dom]))
                    if norm_dom in tgt_scores:
                        matched_scores.append(float(tgt_scores[norm_dom]))
                domain_score = max(matched_scores, key=lambda x: abs(x)) if matched_scores else 0.0

                # If no direct match exists, only allow a strong life-threat fallback for Asc/life hits.
                if not matched_scores:
                    base_lbl_l = base_lbl.lower()
                    life_hit = ('life' in doms_norm) or (base_lbl_l in {'asc', 'c1'})
                    if life_hit and trans_scores:
                        threat_keys = {
                            'death',
                            'danger',
                            'violence',
                            'health',
                            'illness',
                            'prison',
                            'hidden_enemies',
                            'shared_resources',
                        }
                        threat_scores = [
                            float(v) for k, v in trans_scores.items()
                            if (k in threat_keys and float(v) <= -0.6)
                        ]
                        if threat_scores:
                            domain_score = min(threat_scores)

                nat_data = det_trans.get('nature') or {}
                nat_score = 0.0
                if isinstance(nat_data, dict) and nat_data.get('conditionScore') is not None:
                    nat_score = max(-1.0, min(1.0, float(nat_data.get('conditionScore')) * 2.0))
                else:
                    nat = str((nat_data or {}).get('primary') or '').lower()
                    if nat == 'benefic':
                        nat_score = 0.5
                    elif nat == 'malefic':
                        nat_score = -0.5

                hpos = (det_tgt.get('housePosition') or {}).get('house') if isinstance(det_tgt.get('housePosition'), dict) else None
                if isinstance(hpos, int) and hpos in (1,4,7,10):
                    house_w = 1.0
                elif isinstance(hpos, int) and hpos in (2,5,8,11):
                    house_w = 0.6
                elif isinstance(hpos, int):
                    house_w = 0.3
                else:
                    house_w = 0.0

                if abs(domain_score) < 1e-9:
                    det_strength = 0.0
                else:
                    # Angular targets carry more determination force.
                    amp = 0.6 + 0.4 * house_w
                    det_strength = (domain_score * amp) + (0.2 * nat_score)
                det_strength = max(-1.0, min(1.0, float(det_strength)))
                row['determination_strength'] = round(det_strength, 3)
                row['determination']['strength'] = row['determination_strength']
            except Exception:
                row['determination_strength'] = 0.0
            domset = set(doms)
            try:
                det_strength_val = float(row.get('determination_strength') or 0.0)
            except Exception:
                det_strength_val = 0.0
            trans_child_det = _has_child_det(det_trans)
            tgt_child_det = _has_child_det(det_tgt)
            child_det_ok = trans_child_det or tgt_child_det or _top_has_child(top_areas)
            if 'birth_of_child' in (row.get('keywords') or []):
                if det_strength_val < 0.6 or not child_det_ok:
                    _drop_token(row, 'birth_of_child')
            if 'birth_self' in (row.get('keywords') or []):
                life_home_ok = bool(domset & {'life', 'home', 'children'})
                if det_strength_val < 0.6 or not child_det_ok or not life_home_ok:
                    _drop_token(row, 'birth_self')
            death_tokens = set(row.get('keywords') or []) & {'death_natural', 'death_violent', 'death_of_family'}
            if death_tokens:
                death_trans_score = _max_det_area(det_trans, death_det_keys)
                death_tgt_score = max(_max_det_area(det_tgt, death_det_keys), _max_area_list(top_areas, death_det_keys))
                violence_trans_score = max(_max_det_area(det_trans, violence_det_keys), death_trans_score)
                violence_tgt_score = max(_max_det_area(det_tgt, violence_det_keys), _max_area_list(top_areas, violence_det_keys), death_tgt_score)
                family_trans_score = _max_det_area(det_trans, family_det_keys)
                family_tgt_score = max(_max_det_area(det_tgt, family_det_keys), _max_area_list(top_areas, family_det_keys))
                loss_trans_score = max(_max_det_area(det_trans, loss_det_keys), death_trans_score)
                if 'death_natural' in death_tokens:
                    if det_strength_val < 0.7 or death_trans_score < 0.7 or death_tgt_score < 0.7:
                        _drop_token(row, 'death_natural')
                if 'death_violent' in death_tokens:
                    if det_strength_val < 0.8 or violence_trans_score < 0.8 or violence_tgt_score < 0.8:
                        _drop_token(row, 'death_violent')
            if 'death_of_family' in death_tokens:
                if det_strength_val < 0.5 or family_trans_score < 0.5 or loss_trans_score < 0.5 or family_tgt_score < 0.5:
                    _drop_token(row, 'death_of_family')
            orb_val = abs(_safe_float(row.get('orb'), 9.99))
            max_orb_val = _safe_float(row.get('max_orb'), 1.0) or 1.0
            clos = max(0.0, min(1.0, 1.0 - (orb_val / max_orb_val)))
            pd = _direction_match(transit_timestamp_iso, doms, _pd_windows_for_year(t_year))
            sr_dir = _direction_match(
                transit_timestamp_iso,
                doms,
                sr_lr_once.get('sr_directions') or [],
            )
            lr_dir = _direction_match(
                transit_timestamp_iso,
                doms,
                sr_lr_once.get('lr_directions') or [],
            )
            sr_score = float(sr_lr_once.get('sr_score') or 0.0)
            lr_score = float(sr_lr_once.get('lr_score') or 0.0)

            score_raw = float(row.get('score') or 0.0)
            score_norm = max(0.0, min(1.0, score_raw / 10.0))
            baseline_score = score_norm * 50.0
            pd_signif = float(pd.get('signification_score') or 0.0)
            sr_signif = float(sr_dir.get('signification_score') or 0.0)
            lr_signif = float(lr_dir.get('signification_score') or 0.0)
            signif_pts = min(100.0, pd_signif + 0.7 * sr_signif + 0.5 * lr_signif)
            concordance_pts = 0.0
            quality_score = float(row.get('quality_score') or 0.0)
            planetary_state_pts = max(0.0, min(50.0, (quality_score + 10.0) * 2.5))
            determination_pts = max(0.0, min(50.0, det_strength_val * 50.0))
            timing_from_transit = clos * 10.0
            pd_tim = float(pd.get('timing_score') or 0.0)
            sr_tim = float(sr_dir.get('timing_score') or 0.0)
            lr_tim = float(lr_dir.get('timing_score') or 0.0)
            timing_from_directions = min(20.0, pd_tim + 0.7 * sr_tim + 0.5 * lr_tim)
            timing_from_revolutions = min(10.0, (sr_score + lr_score) * 10.0)
            timing_pts = min(30.0, timing_from_transit + timing_from_directions + timing_from_revolutions)
            components = {
                'signification': round(signif_pts, 1),
                'planetary_state': round(planetary_state_pts, 1),
                'determination': round(determination_pts, 1),
                'timing': round(timing_pts, 1),
            }

            base_total = baseline_score + concordance_pts + signif_pts + planetary_state_pts + determination_pts + timing_pts
            base_total = max(0.0, min(230.0, base_total))

            partile_mult = _partile_weight(orb_val, A)
            if partile_mult == 0.0:
                base_total = 0.0
            multi_mult, multi_meta = _multiple_transit_multiplier(idx, t_dt)
            mutual_mult, mutual_meta = _mutual_strengthening_multiplier(idx)
            light_mult, light_meta = _light_coupling_multiplier(row)
            rev_mult, rev_meta = _revolution_danger_multiplier(row)
            cluster_bonus, cluster_meta = _cluster_bonus(row)
            successive_mult, successive_meta = _successive_malefic_multiplier(idx, pd, doms, t_dt, sr_lr_once)

            total_multiplier = partile_mult if partile_mult else 1.0
            total_multiplier *= multi_mult
            total_multiplier *= mutual_mult
            total_multiplier *= light_mult
            total_multiplier *= rev_mult
            total_multiplier *= successive_mult

            final_score = base_total * total_multiplier + cluster_bonus
            final_score = max(0.0, min(230.0, final_score))
            overall_norm = 0.0 if final_score <= 0.0 else min(1.0, final_score / 230.0)

            combined_matches = (pd.get('matches') or []) + (sr_dir.get('matches') or []) + (lr_dir.get('matches') or [])

            row['concordance'] = {
                'direction_matches': combined_matches,
                'pd_matches': pd.get('matches') or [],
                'solar_direction_matches': sr_dir.get('matches') or [],
                'lunar_direction_matches': lr_dir.get('matches') or [],
                'components': components,
                'direction_score': round(signif_pts, 1),
                'direction_primary_score': round(pd_signif, 1),
                'direction_solar_score': round(sr_signif, 1),
                'direction_lunar_score': round(lr_signif, 1),
                'direction_concordance': round(signif_pts / 100.0, 3) if signif_pts else 0.0,
                'planetary_state_score': round(planetary_state_pts, 1),
                'determination_score': round(determination_pts, 1),
                'timing_score': round(timing_pts, 1),
                'timing_breakdown': {
                    'transit': round(timing_from_transit, 1),
                    'directions': round(timing_from_directions, 1),
                    'revolutions': round(timing_from_revolutions, 1),
                },
                'overall_score': round(final_score, 1),
                'overall_concordance': round(overall_norm, 3),
                'threshold_met': final_score >= 150.0,
                'solar_score': round(sr_score, 3),
                'lunar_score': round(lr_score, 3),
                'solar_match': round(sr_score, 3),
                'lunar_match': round(lr_score, 3),
                'confidence': round(max(0.0, min(1.0, overall_norm)), 2),
                'multipliers': {
                    'partile': round(partile_mult, 3),
                    'multiple_transits': round(multi_mult, 3),
                    'mutual_strengthening': round(mutual_mult, 3),
                    'light_coupling': round(light_mult, 3),
                    'revolution_state': round(rev_mult, 3),
                    'successive_malefics': round(successive_mult, 3),
                    'cluster_bonus': round(cluster_bonus, 1),
                },
            }
            if sr_lr_once.get('sr_summary'):
                row['concordance']['solar_revolution'] = sr_lr_once.get('sr_summary')
            if sr_lr_once.get('lr_summary'):
                row['concordance']['lunar_revolution'] = sr_lr_once.get('lr_summary')
            # Syzygies: other hits at t that reinforce same domains within tight orb
            try:
                domset = set(doms)
                syz: List[Dict[str, Any]] = []
                for j, other in enumerate(hits):
                    if other is row:
                        continue
                    try:
                        if abs(float(other.get('orb') or 99.0)) > 1.5:
                            continue
                        odoms = domains_cache.get(j) or []
                        if not domset.intersection(set(odoms)):
                            continue
                        syz.append({
                            'planet': str(other.get('transiting') or ''),
                            'aspect': str(other.get('aspect') or ''),
                            'target': str(other.get('target_label') or other.get('natal') or ''),
                            'orb': float(other.get('orb') or 0.0),
                        })
                        if len(syz) >= 4:
                            break
                    except Exception:
                        continue
                if syz:
                    row['syzygies'] = syz
            except Exception:
                pass

            row['significance_variant'] = 'morin_v2'
            target_area_for_tone: Optional[str] = None
            target_area_source: Optional[str] = None

            def _derive_target_area() -> Tuple[Optional[str], Optional[str]]:
                base_label = str(row.get('target_label') or row.get('natal') or '')
                base_clean = base_label.replace(' (antiscia)', '').replace(' (contra-antiscia)', '')
                # Direct angles/cusps
                if base_clean == 'Asc':
                    return 'life', 'ascendant'
                if base_clean == 'MC':
                    return 'honors', 'mc'
                if base_clean.startswith('C') and base_clean[1:].isdigit():
                    try:
                        area = _HOUSE_DEFAULT_DOMAIN.get(int(base_clean[1:]))
                    except Exception:
                        area = None
                    if area:
                        return area, 'cusp'
                # Planetary targets: evaluate determinations of natal planet
                if str(row.get('target_type') or '') == 'planet':
                    candidates: List[Tuple[str, float, str]] = []

                    def _push(area: Optional[str], weight: float, source: str) -> None:
                        if not area:
                            return
                        norm = _normalize_domain(area)
                        if not norm:
                            return
                        candidates.append((norm, float(weight), source))

                    loc_house: Optional[int] = None
                    try:
                        loc_house = (det_tgt.get('housePosition') or {}).get('house') if isinstance(det_tgt.get('housePosition'), dict) else None
                    except Exception:
                        loc_house = None
                    if isinstance(loc_house, int):
                        _push(_HOUSE_DEFAULT_DOMAIN.get(loc_house), 1.0, 'location')
                    for rul in (det_tgt.get('rulerships') or []):
                        try:
                            rh = int(rul.get('house'))
                        except Exception:
                            rh = None
                        if rh is None:
                            continue
                        _push(_HOUSE_DEFAULT_DOMAIN.get(rh), 0.75, 'rulership')
                    for asp in (det_tgt.get('aspectDeterminations') or []):
                        try:
                            ah = int(asp.get('aspectedHouse'))
                        except Exception:
                            ah = None
                        if ah is None:
                            continue
                        aspect_label = str(asp.get('aspect') or '')
                        weight = 0.82
                        if 'conj' in aspect_label.lower():
                            weight = 0.9
                        _push(_HOUSE_DEFAULT_DOMAIN.get(ah), weight, 'aspect')
                    target_det = (row.get('determination') or {}).get('targetDetermination') or {}
                    score_list: List[Dict[str, Any]] = []
                    if isinstance(target_det.get('topAreas'), list):
                        score_list.extend(target_det.get('topAreas'))  # type: ignore[arg-type]
                    if isinstance(top_areas, list) and not score_list:
                        score_list.extend(top_areas)
                    for item in score_list:
                        if not isinstance(item, dict):
                            continue
                        area_item = item.get('area')
                        try:
                            val = abs(float(item.get('score') or 0.0))
                        except Exception:
                            val = 0.0
                        if area_item and val > 0.0:
                            weight = min(1.2, 0.6 + 0.4 * min(1.0, val))
                            _push(area_item, weight, 'score')
                    if not candidates and isinstance(loc_house, int):
                        _push(_HOUSE_DEFAULT_DOMAIN.get(loc_house), 0.45, 'location_default')
                    if candidates:
                        candidates.sort(key=lambda x: (x[1], 1 if _domain_polarity(x[0]) < 0 else 0), reverse=True)
                        best = candidates[0]
                        return best[0], best[2]
                return None, None

            target_primary_area, target_source = _derive_target_area()
            if target_primary_area:
                target_area_for_tone = _normalize_domain(target_primary_area)
                row['target_primary_area'] = target_area_for_tone
            if target_source:
                target_area_source = target_source
                row['target_area_source'] = target_source
            if not target_area_for_tone:
                for candidate in doms:
                    norm_cand = _normalize_domain(candidate)
                    if norm_cand:
                        target_area_for_tone = norm_cand
                        row['target_primary_area'] = norm_cand
                        row.setdefault('target_area_source', 'matched_domain')
                        break
            if not target_area_for_tone and row.get('event_domain'):
                cand = _normalize_domain(row.get('event_domain'))
                if cand:
                    target_area_for_tone = cand
                    row['target_primary_area'] = cand
                    row.setdefault('target_area_source', 'event_domain')

            laws_applied: List[Dict[str, Any]] = []
            final_score_adj = float(final_score)
            overall_norm_adj = float(overall_norm)
            tone_adj = row.get('tone')
            tone_score_adj = row.get('tone_score')

            base_label_full = str(row.get('target_label') or row.get('natal') or '')
            base_clean = base_label_full.replace(' (antiscia)', '').replace(' (contra-antiscia)', '')
            doms_norm = [d for d in (_normalize_domain(x) for x in doms) if d]
            doms_set_norm = set(doms_norm)
            event_domain_law = _primary_domain(list(doms_norm), row=row)
            if not event_domain_law:
                base_low = base_clean.lower()
                if base_low in {'asc', 'ascendant'}:
                    event_domain_law = 'life'
                elif base_low == 'mc':
                    event_domain_law = 'honors'
            if not event_domain_law and target_area_for_tone:
                event_domain_law = target_area_for_tone
            elif target_area_for_tone is None and event_domain_law:
                target_area_for_tone = event_domain_law
                row['target_primary_area'] = target_area_for_tone
                row.setdefault('target_area_source', 'event_domain')
            sr_domains_norm = {d for d in (_normalize_domain(x) for x in sr_lr_once.get('sr_domains') or []) if d}
            lr_domains_norm = {d for d in (_normalize_domain(x) for x in sr_lr_once.get('lr_domains') or []) if d}
            pd_matches = list(pd.get('matches') or [])
            benefics = {'Jupiter', 'Venus'}
            malefics = {'Saturn', 'Mars'}

            def _add_law(num: int, name: str, applies: bool, **info: Any) -> Dict[str, Any]:
                entry: Dict[str, Any] = {
                    'lawNumber': num,
                    'lawName': name,
                    'applies': bool(applies),
                }
                for key, value in info.items():
                    if value is not None:
                        entry[key] = value
                laws_applied.append(entry)
                return entry

            def _match_domain_house(house: Optional[int], domain: Optional[str]) -> bool:
                if not isinstance(house, int) or not domain:
                    return False
                d = str(domain)
                if d in {'death', 'danger'}:
                    return house in (8, 12)
                primary = _DOMAIN_PRIMARY_HOUSE.get(d)
                if primary is not None:
                    return house == primary
                return False

            det_threshold = 0.35
            det_present = abs(det_strength_val) >= det_threshold
            law1 = _add_law(
                1,
                'Radical Determination Governs All',
                det_present,
                strength=round(det_strength_val, 3),
                matchedDomains=sorted(doms_set_norm),
                targetArea=target_area_for_tone,
                targetSource=row.get('target_area_source'),
            )
            if not det_present:
                final_score_adj = 0.0
                overall_norm_adj = 0.0
                tone_adj = 'mixed'
                tone_score_adj = 0.0
                law1['blocked'] = True

            determination_sources: Set[str] = set()
            det_trans_house = None
            try:
                det_trans_house = (det_trans.get('housePosition') or {}).get('house') if isinstance(det_trans.get('housePosition'), dict) else None
            except Exception:
                det_trans_house = None
            if _match_domain_house(det_trans_house, event_domain_law):
                determination_sources.add('location')
            for rul in (det_trans.get('rulerships') or []):
                try:
                    rh = int(rul.get('house'))
                except Exception:
                    rh = None
                if _match_domain_house(rh, event_domain_law):
                    determination_sources.add('rulership')
                    break
            for asp_det in (det_trans.get('aspectDeterminations') or []):
                try:
                    ah = int(asp_det.get('aspectedHouse'))
                except Exception:
                    ah = None
                if _match_domain_house(ah, event_domain_law):
                    determination_sources.add('aspect')
                    break
            try:
                scores = (det_trans.get('determinationScores') or {}).get('by_area') or {}
                if event_domain_law and abs(float(scores.get(event_domain_law, 0.0))) >= 0.3:
                    determination_sources.add('score')
            except Exception:
                pass
            if event_domain_law and event_domain_law in (_PLANET_NATURE_DOMAINS.get(A, set())):
                determination_sources.add('nature')
            target_support_sources: List[str] = []
            for area in top_areas or []:
                name = str((area or {}).get('area') or '').lower()
                if event_domain_law and name == event_domain_law:
                    determination_sources.add('target_support')
                    target_support_sources.append(name)
            law2 = _add_law(
                2,
                'Multiple Determinations Compound',
                len(determination_sources) >= 2,
                sources=sorted(determination_sources),
                targetSupport=sorted(set(target_support_sources)),
                targetArea=target_area_for_tone,
            )
            if multi_meta:
                law2['transitAllies'] = multi_meta
            if multi_mult and abs(multi_mult - 1.0) > 1e-3:
                law2['strengthModifier'] = round(multi_mult, 3)

            direction_support = False
            if event_domain_law:
                for match in pd_matches:
                    dtype = str((match or {}).get('type') or '').lower()
                    if event_domain_law in dtype or _normalize_domain(dtype) == event_domain_law:
                        direction_support = True
                        break
                    if event_domain_law in {'death', 'danger'} and any(key in dtype for key in ('death', 'danger', '8th', '12th', 'illness', 'shared')):
                        direction_support = True
                        break
            law3 = _add_law(
                3,
                'Directions Are Primary, Transits Are Triggers',
                direction_support,
                matchCount=len(pd_matches),
                significationScore=round(signif_pts, 1),
                timingScore=round(float(pd.get('timing_score') or 0.0), 1),
            )
            if not direction_support:
                cap = 60.0 if event_domain_law and (event_domain_law in sr_domains_norm or event_domain_law in lr_domains_norm) else 40.0
                final_score_adj = min(final_score_adj, cap)
                law3['cappedScore'] = cap

            transit_support_flag = bool(event_domain_law and event_domain_law in doms_set_norm)
            law4 = _add_law(
                4,
                'Planets Act on Connected Matters',
                transit_support_flag,
                eventDomain=event_domain_law,
                domains=sorted(doms_set_norm),
            )
            if not transit_support_flag:
                law4['notes'] = 'No matched domain keywords or targets'

            returns_radical = base_clean == A and str(row.get('aspect') or '').lower().startswith('conj')
            _add_law(
                5,
                'Return to Radical Place',
                returns_radical,
                aspect=str(row.get('aspect') or ''),
                partile=bool(row.get('partile')),
                target=base_label_full,
            )

            revolution_support = bool(event_domain_law and (event_domain_law in sr_domains_norm or event_domain_law in lr_domains_norm))
            timing_support = {'direction': direction_support, 'revolution': revolution_support, 'transit': transit_support_flag, 'partile': round(partile_mult, 3)}
            if cluster_meta:
                timing_support['cluster'] = cluster_meta
            law6_applies = direction_support and revolution_support and transit_support_flag and partile_mult > 0.0
            _add_law(
                6,
                'Nativity Shows General Times, Transits Show Specific Days',
                law6_applies,
                support=timing_support,
            )

            is_benefic = A in benefics
            is_malefic = A in malefics
            key_points = {'Asc', 'MC', 'Sun', 'Moon'}
            law7_applies = is_benefic and (base_clean in key_points or event_domain_law in {'life', 'honors', 'wealth', 'relationships'})
            _add_law(
                7,
                'Benefics Strengthen Significators',
                law7_applies,
                planet=A,
                target=base_clean,
                eventDomain=event_domain_law,
                targetArea=target_area_for_tone,
            )

            law8_effect = None
            if is_benefic and event_domain_law in {'life', 'health', 'honors', 'wealth'}:
                law8_effect = 'reinforces'
            elif is_malefic and event_domain_law in {'life', 'health', 'danger', 'death'}:
                law8_effect = 'threatens'
            _add_law(
                8,
                'Benefics Strengthen Life, Malefics Weaken It',
                law8_effect is not None,
                effect=law8_effect,
                eventDomain=event_domain_law,
                targetArea=target_area_for_tone,
            )

            hard_family = _aspect_hard_soft(str(row.get('aspect') or ''))
            law9_applies = is_malefic and hard_family == 'hard'
            _add_law(
                9,
                'Malefic Squares and Oppositions Intensify Harm',
                law9_applies,
                aspect=str(row.get('aspect') or ''),
            )

            law10_applies = is_malefic and base_clean == 'Asc' and direction_support
            law10_info: Dict[str, Any] = {}
            if successive_meta and successive_mult > 1.0:
                law10_info['successive'] = successive_meta
                law10_info['successiveMultiplier'] = round(successive_mult, 3)
            _add_law(
                10,
                'Malefics to ASC Signal Illness or Danger',
                law10_applies,
                **law10_info,
            )

            law11_applies = is_benefic and base_clean == 'MC' and direction_support
            _add_law(
                11,
                'Benefics to MC Promise Honors',
                law11_applies,
                planet=A,
                target=base_clean,
            )

            tone_lower = str(tone_adj or row.get('tone') or '').lower()
            law12_ok = True
            if is_benefic and tone_lower == 'negative':
                law12_ok = False
            if is_malefic and tone_lower == 'positive':
                law12_ok = False
            law12_entry = _add_law(
                12,
                "Benefics Don't Harm, Malefics Don't Help",
                law12_ok,
                tone=tone_lower or None,
            )
            if not law12_ok:
                final_score_adj *= 0.6
                overall_norm_adj = min(1.0, final_score_adj / 230.0 if final_score_adj > 0 else 0.0)
                tone_adj = 'mixed'
                tone_score_adj = 0.0
                law12_entry['adjusted'] = True

            special_flags = row.get('special_flags') or {}
            syzygy_danger = bool(special_flags.get('lethal_new_moon') or special_flags.get('lethal_full_moon'))
            law13_details: Dict[str, Any] = {}
            if syzygy_danger:
                law13_details['flags'] = {k: v for k, v in special_flags.items() if v}
            if light_meta:
                law13_details['lightCouplings'] = light_meta
                law13_details['lightMultiplier'] = round(light_mult, 3)
            _add_law(
                13,
                'Syzygies at Malefic Degrees Warn of Danger',
                syzygy_danger or bool(light_meta),
                **law13_details,
            )

            law14_entry = _add_law(
                14,
                'Revolution State Check',
                bool(rev_meta) or revolution_support,
                multiplier=round(rev_mult, 3),
                details=rev_meta,
                revolutionDomains=sorted(sr_domains_norm | lr_domains_norm),
            )
            if not revolution_support and not rev_meta:
                law14_entry['notes'] = 'No supporting solar or lunar revolution evidence'

            angular_target = base_clean in {'Asc', 'MC'} or (isinstance(row.get('natal_house'), int) and row.get('natal_house') in (1, 4, 7, 10))
            _add_law(
                15,
                'Angular Positions Amplify Effects',
                angular_target,
                natalHouse=row.get('natal_house'),
                target=base_clean,
            )

            transit_sign = str(row.get('transit_sign') or '')
            target_sign = str(row.get('target_sign') or '')
            mutual_reception = False
            if base_clean in CLASSICAL and A in CLASSICAL and transit_sign and target_sign:
                if base_clean in _sign_rulers_for(transit_sign) and A in _sign_rulers_for(target_sign):
                    mutual_reception = True
            law16_entry = _add_law(
                16,
                'Mutual Reception Helps',
                mutual_reception,
                transitSign=transit_sign or None,
                targetSign=target_sign or None,
            )
            if mutual_reception:
                final_score_adj *= 1.1
                final_score_adj = min(final_score_adj, 230.0)
                overall_norm_adj = min(1.0, final_score_adj / 230.0)
                law16_entry['strengthModifier'] = 1.1
            if mutual_meta:
                law16_entry['domainAllies'] = mutual_meta
                law16_entry['domainMultiplier'] = round(mutual_mult, 3)

            final_score = max(0.0, min(230.0, final_score_adj))
            overall_norm = max(0.0, min(1.0, overall_norm_adj))
            row['tone'] = tone_adj
            if tone_score_adj is not None:
                try:
                    row['tone_score'] = float(tone_score_adj)
                except Exception:
                    pass
            row['concordance']['overall_score'] = round(final_score, 1)
            row['concordance']['overall_concordance'] = round(overall_norm, 3)
            row['concordance']['confidence'] = round(max(0.0, min(1.0, overall_norm)), 2)
            row['concordance']['threshold_met'] = final_score >= 150.0
            row['laws_applied'] = laws_applied
            if final_score <= 0.0:
                row['prediction_score'] = 0.0
            try:
                _sync_prediction_orientation_tags(row)
            except Exception:
                pass
                row['significance'] = 0.0

            if t_dt is not None:
                registry_entry = {
                    'planet': A,
                    'timestamp': t_dt,
                    'aspect': str(row.get('aspect') or ''),
                    'domains': set(doms),
                }
                _register_registry_event(simultaneous_registry, base_lbl, registry_entry, _SIMULTANEOUS_HORIZON_DAYS)
                if A in ('Saturn', 'Mars'):
                    _register_registry_event(malefic_registry, base_lbl, registry_entry, _SUCCESSIVE_HORIZON_DAYS)
            event_domain = _primary_domain(doms, row=row)
            if not event_domain:
                base_clean = base_lbl.lower()
                if base_clean in {'asc', 'ascendant'}:
                    event_domain = 'life'
                elif base_clean in {'mc'}:
                    event_domain = 'honors'
            doms_set = set(_normalize_domain(d) for d in doms if d)
            nature_support = bool(event_domain and event_domain in _PLANET_NATURE_DOMAINS.get(A, set()))
            ruler_support = False
            house_num = _DOMAIN_PRIMARY_HOUSE.get(event_domain) if event_domain else None
            if house_num is not None and house_rulers:
                for key in (str(house_num), house_num):
                    try:
                        if str(house_rulers.get(key) or '').lower() == A.lower():
                            ruler_support = True
                            break
                    except Exception:
                        continue
            direction_support = False
            if event_domain:
                for match in pd.get('matches') or []:
                    dtype = str((match or {}).get('type') or '').lower()
                    if event_domain in dtype or _normalize_domain(dtype) == event_domain:
                        direction_support = True
                        break
                    if event_domain in {'death', 'danger'} and any(key in dtype for key in ('death', 'danger', '8th', '12th', 'illness', 'shared')):
                        direction_support = True
                        break
            transit_support = bool(event_domain and event_domain in doms_set)
            quality_val = float(row.get('quality_score') or 0.0)
            state_support = abs(quality_val) >= 5.0

            conc = row.get('concordance') or {}
            sr_domains_set = set(sr_lr_once.get('sr_domains') or [])
            lr_domains_set = set(sr_lr_once.get('lr_domains') or [])
            ways = sum(1 for flag in (nature_support, ruler_support, direction_support, transit_support, state_support) if flag)
            revolution_support = bool(event_domain and (event_domain in sr_domains_set or event_domain in lr_domains_set))
            base_score = float(ways * 15.0)
            if direction_support:
                base_score += 5.0
            if event_domain and event_domain in sr_domains_set:
                base_score += 10.0
            if event_domain and event_domain in lr_domains_set:
                base_score += 8.0

            mixed_outcome = False
            if partile_mult == 0.0:
                prediction_score = 0.0
            else:
                score_working = base_score
                score_working *= partile_mult
                score_working *= max(1.0, min(2.0, multi_mult))
                score_working *= max(1.0, min(1.8, successive_mult))
                score_working *= max(1.0, min(1.5, light_mult))
                score_working *= max(1.0, min(1.4, rev_mult))
                score_working += min(cluster_bonus, 10.0)

                if not direction_support:
                    score_working = min(score_working, 40.0)
                elif not revolution_support:
                    score_working = min(score_working, 60.0)
                else:
                    score_working = min(score_working, 100.0)

                pos_hit = bool(doms_set & _POSITIVE_DOMAINS)
                neg_hit = bool(doms_set & _NEGATIVE_DOMAINS)
                if pos_hit and neg_hit:
                    mixed_outcome = True
                    score_working *= 0.75
                prediction_score = max(0.0, min(100.0, score_working))

            row['event_domain'] = event_domain

            # Orientation tag should reflect finalized tone when available.
            # Avoid prematurely forcing 'positive' from a zero/unset quality_score.
            tone_lower_early = str(row.get('tone') or '').lower()
            if tone_lower_early in {'positive','negative','mixed'}:
                orientation_tag = tone_lower_early
            else:
                # Defer orientation to later tone computation; don't emit a polarity tag now.
                orientation_tag = None
            tags: List[str] = []
            if event_domain:
                primary_tag = _EVENT_TAG_MAP.get(event_domain, event_domain)
                if primary_tag:
                    tags.append(primary_tag)
            if orientation_tag:
                tags.append(orientation_tag)
            if event_domain in {'death', 'danger'} or (orientation_tag == 'negative' and A in ('Saturn', 'Mars')):
                tags.append('risk')
            if multi_mult > 1.0:
                tags.append('multiple_transit')
            if successive_mult > 1.0:
                tags.append('successive')
            if mixed_outcome and 'mixed_outcome' not in tags:
                tags.append('mixed_outcome')
            row['prediction_score'] = round(prediction_score, 1)
            row['prediction_tags'] = list(dict.fromkeys([t for t in tags if t]))
            row['significance'] = row['prediction_score']

            # Prediction object per spec: lifeArea, eventType, description, confidence
            kw_all = set([str(x).lower() for x in (row.get('enriched_keywords') or [])])
            # Life area priority mapping
            life_priority = ['honors','career','marriage','relationships','conflict','danger','prison','money','wealth','home','health','friends','children','belief','life','shared_resources','secrets','short_journeys']
            def _pick_life_area():
                # map synonyms in doms
                domset = set(doms)
                syn = {
                    'career':'honors',
                    'money':'wealth',
                    'relationship':'relationships',
                    'short_travel':'short_journeys',
                    'shared':'shared_resources',
                    'hidden':'secrets',
                }
                mapped: List[str] = []
                seen_mapped: Set[str] = set()
                for d in domset:
                    norm = syn.get(d, d)
                    if norm not in seen_mapped:
                        seen_mapped.add(norm)
                        mapped.append(norm)
                contextual = _pick_contextual_domain(mapped, row=row)
                if contextual:
                    return contextual
                for key in life_priority:
                    if key in mapped:
                        return key
                # fallback by target
                base = str(row.get('target_label') or row.get('natal') or '')
                if base == 'MC': return 'honors'
                if base == 'Asc': return 'life'
                return mapped[0] if mapped else None
            life_area = None
            try:
                life_area = _pick_life_area()
            except Exception:
                life_area = None
            # Phase 2 canonical mappings (post-SR/LR/PD): travel + death (conservative)
            try:
                A = str(row.get('transiting') or '')
                label = str(row.get('aspect') or '')
                hs_kind = _aspect_hard_soft(label)
                softish = (hs_kind == 'soft') or ('conjunction' in label.lower())
                hardish = (hs_kind == 'hard')
                kws = set([str(x) for x in (row.get('keywords') or [])])
                enriched_now = list(row.get('enriched_keywords') or [])
                def _has_cap(s: str) -> bool:
                    return s in kws
                def _add(tok: str):
                    if tok and (tok not in enriched_now):
                        enriched_now.append(tok)
                base_lbl = str(row.get('target_label') or row.get('natal') or '')
                base_lbl = base_lbl.replace(' (antiscia)', '').replace(' (contra-antiscia)', '')
                det_trans = by_planet.get(A) or {}
                det_tgt = by_planet.get(base_lbl) or {}
                top_areas = (row.get('determination') or {}).get('targetDetermination', {}).get('topAreas', [])
                try:
                    det_strength_val = float(row.get('determination_strength') or 0.0)
                except Exception:
                    det_strength_val = 0.0
                conc = row.get('concordance') or {}
                overall_val = _safe_float(conc.get('overall_concordance'))
                dir_val = _safe_float(conc.get('direction_concordance'))
                solar_norm = _safe_float(conc.get('solar_score'))
                lunar_norm = _safe_float(conc.get('lunar_score'))
                multipliers = conc.get('multipliers') or {}
                multi_factor = _safe_float(multipliers.get('multiple_transits'), 1.0)
                partile_factor = _safe_float(multipliers.get('partile'), 1.0)
                quality_score = _safe_float(row.get('quality_score'))
                good_state = quality_score >= 1.0
                excellent_state = quality_score >= 1.8
                poor_state = quality_score <= -1.0
                very_poor_state = quality_score <= -1.5
                station_like = (row.get('phase') == 'stationary') or ('stationary' in kw_all) or ('station' in kw_all)
                retrograde_flag = ('retrograde' in kw_all) or ('retrograde' in kws)
                target_planet = base_lbl if str(row.get('target_type') or '') == 'planet' else None
                is_malefic = A in ('Saturn','Mars')
                is_benefic = A in ('Jupiter','Venus','Sun')
                travel_trans_score = _max_det_area(det_trans, travel_det_keys)
                travel_tgt_score = max(
                    _max_det_area(det_tgt, travel_det_keys),
                    _max_area_list(top_areas, travel_det_keys),
                )
                relocation_trans_score = _max_det_area(det_trans, relocation_det_keys)
                relocation_tgt_score = max(
                    _max_det_area(det_tgt, relocation_det_keys),
                    _max_area_list(top_areas, relocation_det_keys),
                )
                travel_det_ok = max(travel_trans_score, travel_tgt_score) >= 0.3
                long_travel_det_ok = max(travel_trans_score, travel_tgt_score) >= 0.4
                relocation_det_ok = max(relocation_trans_score, relocation_tgt_score) >= 0.5
                danger_det_score = max(
                    _max_det_area(det_trans, violence_det_keys),
                    _max_area_list(top_areas, violence_det_keys),
                )
                # House presence flags reused across danger/education logic
                has_h1 = _has_cap('C1') or _has_cap('Asc') or ('Body' in kws) or ('life' in kw_all) or ((row.get('natal_house') == 1))
                has_h2 = _has_cap('C2') or ('Money' in kws) or ('money' in kw_all) or ((row.get('natal_house') == 2))
                has_h3 = _has_cap('C3') or ('Travel' in kws) or ('short_journeys' in kw_all) or ('movement' in kw_all)
                has_h4 = _has_cap('C4') or ('Home' in kws) or ((row.get('natal_house') == 4))
                has_h5 = _has_cap('C5') or ('Children' in kws) or ('children' in kw_all) or ('creativity' in kw_all) or ((row.get('natal_house') == 5))
                has_h6 = _has_cap('C6') or ('Health' in kws) or ('illness' in kw_all) or ((row.get('natal_house') == 6))
                has_h7 = _has_cap('C7') or ('Relationship' in kws) or ((row.get('natal_house') == 7))
                has_h8 = _has_cap('C8') or ('shared_resources' in kw_all) or ('death' in kw_all) or ((row.get('natal_house') == 8))
                has_h9 = _has_cap('C9') or ('Belief' in kws) or ('belief' in kw_all)
                has_h10 = _has_cap('C10') or ('Career' in kws) or ('career' in kw_all)
                has_h11 = _has_cap('C11') or ('Friends' in kws) or ('friends' in kw_all) or ('patrons' in kw_all)
                has_h12 = _has_cap('C12') or ('Hidden' in kws) or ('secrets' in kw_all) or ('institutions' in kw_all) or ((row.get('natal_house') == 12))
                # Travel with SR/LR awareness (light gate: allow even without SR/LR)
                if softish and (A in ('Mercury','Moon')) and has_h3 and travel_det_ok:
                    _add('short_journey')
                if softish and (A in ('Jupiter','Sun')) and has_h9 and long_travel_det_ok:
                    _add('long_journey')
                # Relocation (permanent) — require strong concordance + Home + (H9 or Travel signals)
                ov_ok = overall_val >= 0.6
                if (
                    ov_ok
                    and det_strength_val >= 0.5
                    and relocation_det_ok
                    and travel_det_ok
                    and has_h4
                    and (has_h9 or ('long_journey' in kw_all) or ('short_journeys' in kw_all))
                    and softish
                    and (A in ('Moon','Mercury','Jupiter','Sun'))
                ):
                    _add('relocation_permanent')
                # Education milestones (degree completion, exams, enrollment)
                education_trans_score = _max_det_area(det_trans, education_det_keys)
                education_tgt_score = max(
                    _max_det_area(det_tgt, education_det_keys),
                    _max_area_list(top_areas, education_det_keys),
                )
                education_strength = max(education_trans_score, education_tgt_score)
                enrollment_trans_score = _max_det_area(det_trans, education_enrollment_det_keys)
                enrollment_tgt_score = max(
                    _max_det_area(det_tgt, education_enrollment_det_keys),
                    _max_area_list(top_areas, education_enrollment_det_keys),
                )
                enrollment_strength = max(education_strength, enrollment_trans_score, enrollment_tgt_score)
                setback_trans_score = _max_det_area(det_trans, education_setback_det_keys)
                setback_tgt_score = max(
                    _max_det_area(det_tgt, education_setback_det_keys),
                    _max_area_list(top_areas, education_setback_det_keys),
                )
                education_setback_strength = max(education_strength, setback_trans_score, setback_tgt_score)
                ruler_h9_present = _has_cap('Ruler(H9)') or ('ruler(h9)' in kw_all) or ('ruler(belief)' in kw_all)
                ruler_h3_present = _has_cap('Ruler(H3)') or ('ruler(h3)' in kw_all) or ('ruler(travel)' in kw_all)
                planet_supports_education = (
                    A in ('Mercury', 'Jupiter', 'Sun') or ruler_h9_present or ruler_h3_present
                )
                target_supports_education = base_lbl in ('Mercury', 'Jupiter', 'Ruler(H9)', 'Ruler(H3)')
                education_axis_ok = has_h9 and (has_h3 or has_h10)
                enrollment_axis_ok = has_h9 and (has_h3 or has_h11)
                exam_axis_ok = has_h9 and has_h3
                if (
                    softish
                    and planet_supports_education
                    and (target_supports_education or planet_supports_education)
                    and education_strength >= 0.6
                    and det_strength_val >= 0.6
                    and overall_val >= 0.6
                    and dir_val >= 0.3
                    and education_axis_ok
                ):
                    _add('degree_completion')
                if (
                    softish
                    and (planet_supports_education or target_supports_education)
                    and enrollment_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.5
                    and enrollment_axis_ok
                ):
                    _add('enrollment_admission')
                if (
                    softish
                    and (planet_supports_education or target_supports_education)
                    and education_strength >= 0.4
                    and det_strength_val >= 0.4
                    and overall_val >= 0.4
                    and exam_axis_ok
                ):
                    _add('exam_success')
                failure_planet = (A in ('Saturn', 'Mars')) or (A == 'Mercury' and hardish)
                if (
                    hardish
                    and failure_planet
                    and education_setback_strength >= 0.4
                    and det_strength_val >= 0.4
                    and exam_axis_ok
                    and overall_val <= 0.55
                ):
                    _add('exam_failure')
                # Spiritual experiences (awakening, conversion, pilgrimage, mystical)
                spiritual_trans_score = _max_det_area(det_trans, spiritual_det_keys)
                spiritual_tgt_score = max(
                    _max_det_area(det_tgt, spiritual_det_keys),
                    _max_area_list(top_areas, spiritual_det_keys),
                )
                spiritual_strength = max(spiritual_trans_score, spiritual_tgt_score)
                religion_trans_score = _max_det_area(det_trans, religion_det_keys)
                religion_tgt_score = max(
                    _max_det_area(det_tgt, religion_det_keys),
                    _max_area_list(top_areas, religion_det_keys),
                )
                religion_strength = max(religion_trans_score, religion_tgt_score)
                pilgrimage_trans_score = _max_det_area(det_trans, pilgrimage_det_keys)
                pilgrimage_tgt_score = max(
                    _max_det_area(det_tgt, pilgrimage_det_keys),
                    _max_area_list(top_areas, pilgrimage_det_keys),
                )
                pilgrimage_strength = max(pilgrimage_trans_score, pilgrimage_tgt_score, travel_det_ok and travel_trans_score or 0.0)
                mystical_trans_score = _max_det_area(det_trans, mystical_det_keys)
                mystical_tgt_score = max(
                    _max_det_area(det_tgt, mystical_det_keys),
                    _max_area_list(top_areas, mystical_det_keys),
                )
                mystical_strength = max(mystical_trans_score, mystical_tgt_score)
                ruler_h12_present = _has_cap('Ruler(H12)') or ('ruler(h12)' in kw_all) or ('ruler(secrets)' in kw_all)
                spiritual_planet_ok = A in ('Jupiter', 'Moon', 'Neptune', 'Sun') or ruler_h9_present or ruler_h12_present
                target_spiritual_ok = base_lbl in ('Jupiter', 'Neptune', 'Moon', 'Ruler(H9)', 'Ruler(H12)')
                belief_semantics = has_h9 or ('belief' in kw_all) or ('faith' in kw_all) or ('religion' in kw_all)
                hidden_semantics = has_h12 or ('secrets' in kw_all) or ('spirituality' in kw_all) or ('mysticism' in kw_all)
                consciousness_semantics = ('consciousness' in kw_all) or ('awareness' in kw_all) or ('insight' in kw_all) or ('illumination' in kw_all)
                spiritual_axis_ok = belief_semantics or hidden_semantics
                pilgrimage_axis_ok = has_h9 and (has_h3 or ('short_journeys' in kw_all) or ('long_journey' in kw_all))
                mystical_axis_ok = hidden_semantics or ('vision' in kw_all) or ('transcendence' in kw_all)
                if (
                    softish
                    and (spiritual_planet_ok or target_spiritual_ok)
                    and spiritual_axis_ok
                    and det_strength_val >= 0.5
                    and spiritual_strength >= 0.5
                    and overall_val >= 0.5
                ):
                    _add('spiritual_awakening')
                if (
                    softish
                    and (spiritual_planet_ok or target_spiritual_ok)
                    and belief_semantics
                    and det_strength_val >= 0.5
                    and religion_strength >= 0.5
                    and overall_val >= 0.5
                    and dir_val >= 0.2
                ):
                    _add('religious_conversion')
                if (
                    softish
                    and (A in ('Jupiter', 'Moon', 'Mercury') or target_spiritual_ok)
                    and pilgrimage_axis_ok
                    and det_strength_val >= 0.4
                    and pilgrimage_strength >= 0.4
                    and travel_det_ok
                    and overall_val >= 0.45
                ):
                    _add('pilgrimage')
                mystical_planet_ok = A in ('Neptune', 'Moon', 'Jupiter') or target_spiritual_ok or ruler_h12_present
                if (
                    (softish or 'conjunction' in label.lower())
                    and mystical_planet_ok
                    and mystical_axis_ok
                    and det_strength_val >= 0.6
                    and mystical_strength >= 0.6
                    and overall_val >= 0.55
                    and orb_val <= 1.5
                ):
                    _add('mystical_experience')
                if (
                    softish
                    and (A == 'Jupiter' or is_benefic)
                    and belief_semantics
                    and has_h10
                    and religion_strength >= 0.6
                    and good_state
                ):
                    _add('church_honors')
                # Creative / intellectual achievements
                authority_trans_score = _max_det_area(det_trans, authority_det_keys)
                authority_tgt_score = max(
                    _max_det_area(det_tgt, authority_det_keys),
                    _max_area_list(top_areas, authority_det_keys),
                )
                authority_strength = max(authority_trans_score, authority_tgt_score)
                conflict_trans_score = _max_det_area(det_trans, conflict_det_keys)
                conflict_tgt_score = max(
                    _max_det_area(det_tgt, conflict_det_keys),
                    _max_area_list(top_areas, conflict_det_keys),
                )
                conflict_strength = max(conflict_trans_score, conflict_tgt_score)
                enemy_trans_score = _max_det_area(det_trans, enemy_det_keys)
                enemy_tgt_score = max(
                    _max_det_area(det_tgt, enemy_det_keys),
                    _max_area_list(top_areas, enemy_det_keys),
                )
                enemy_strength = max(enemy_trans_score, enemy_tgt_score)
                foreign_trans_score = _max_det_area(det_trans, foreign_det_keys)
                foreign_tgt_score = max(
                    _max_det_area(det_tgt, foreign_det_keys),
                    _max_area_list(top_areas, foreign_det_keys),
                )
                foreign_strength = max(foreign_trans_score, foreign_tgt_score)
                homeland_trans_score = _max_det_area(det_trans, homeland_det_keys)
                homeland_tgt_score = max(
                    _max_det_area(det_tgt, homeland_det_keys),
                    _max_area_list(top_areas, homeland_det_keys),
                )
                homeland_strength = max(homeland_trans_score, homeland_tgt_score)
                if (
                    has_career
                    and softish
                    and reputation_strength >= 0.7
                    and (A in ('Jupiter','Sun') or is_benefic)
                    and excellent_state
                ):
                    _add('exceptional_honor_received')
                if (
                    has_career
                    and softish
                    and reputation_strength >= 0.5
                    and (is_benefic or A in ('Venus','Jupiter','Sun'))
                    and good_state
                ):
                    _add('career_elevation')
                if (
                    has_career
                    and hardish
                    and reputation_strength >= 0.5
                    and malefic_planet
                    and (very_poor_state or overall_val <= 0.45)
                ):
                    _add('disgrace_or_scandal')
                if (
                    has_career
                    and hardish
                    and reputation_strength >= 0.4
                    and malefic_planet
                    and (poor_state or overall_val <= 0.5)
                ):
                    _add('career_setback_major')
                if (
                    has_career
                    and softish
                    and reputation_strength >= 0.5
                    and A == 'Sun'
                    and good_state
                ):
                    _add('professional_recognition')
                if (
                    has_career
                    and authority_strength >= 0.6
                    and softish
                    and (A == 'Jupiter' or is_benefic)
                    and excellent_state
                ):
                    _add('power_increase')
                if (
                    has_career
                    and authority_strength >= 0.5
                    and hardish
                    and (A == 'Saturn' or malefic_planet)
                    and (poor_state or overall_val <= 0.45)
                ):
                    _add('loss_of_authority')
                if (
                    has_career
                    and hardish
                    and malefic_planet
                    and very_poor_state
                    and has_h1
                ):
                    _add('public_humiliation')
                if (
                    hardish
                    and malefic_planet
                    and (has_h7 or has_h1)
                    and conflict_strength >= 0.5
                    and danger_strength_full >= 0.4
                ):
                    _add('violent_confrontation')
                if (
                    A == 'Mars'
                    and hardish
                    and (has_h10 or has_h6)
                    and conflict_strength >= 0.6
                    and enemy_strength >= 0.4
                    and (poor_state or overall_val <= 0.5)
                ):
                    _add('warfare_involvement')
                if (
                    malefic_planet
                    and hardish
                    and (has_h7 or has_h12)
                    and enemy_strength >= 0.5
                ):
                    _add('enemy_attack')
                if (
                    softish
                    and (A == 'Jupiter')
                    and has_h9
                    and travel_det_ok
                    and overall_val >= 0.5
                ):
                    _add('major_journey_fortunate')
                if (
                    hardish
                    and (A == 'Saturn' or malefic_planet)
                    and has_h9
                    and travel_det_ok
                    and danger_strength_full >= 0.5
                    and (poor_state or overall_val <= 0.45)
                ):
                    _add('travel_misfortune')
                if (
                    softish
                    and (A in ('Jupiter','Sun'))
                    and foreign_strength >= 0.6
                    and relocation_det_ok
                    and has_h10
                ):
                    _add('foreign_residence')
                if (
                    hardish
                    and (A == 'Saturn' or malefic_planet)
                    and foreign_strength >= 0.6
                    and (has_h9 or has_h12)
                    and (poor_state or overall_val <= 0.45)
                ):
                    _add('exile_or_forced_travel')
                if (
                    softish
                    and innovation_strength >= 0.5
                    and (A in ('Mercury','Jupiter','Uranus') or target_planet in ('Mercury','Jupiter','Uranus'))
                    and (has_h9 or has_h3 or 'innovation' in kw_all)
                    and det_strength_val >= 0.5
                    and overall_val >= 0.5
                ):
                    _add('intellectual_breakthrough')
                if (
                    softish
                    and education_strength >= 0.6
                    and (A == 'Jupiter' or is_benefic)
                    and good_state
                ):
                    _add('educational_achievement')
                if (
                    (hardish or 'square' in label.lower() or 'opposition' in label.lower())
                    and (A in ('Neptune','Saturn') or target_planet in ('Neptune','Saturn'))
                    and confusion_strength >= 0.4
                    and (has_h3 or has_h9 or 'mind' in kw_all)
                    and (poor_state or overall_val <= 0.5)
                ):
                    _add('mental_confusion_period')
                publishing_trans_score = _max_det_area(det_trans, publishing_det_keys)
                publishing_tgt_score = max(
                    _max_det_area(det_tgt, publishing_det_keys),
                    _max_area_list(top_areas, publishing_det_keys),
                )
                publishing_strength = max(publishing_trans_score, publishing_tgt_score)
                creativity_trans_score = _max_det_area(det_trans, creativity_det_keys)
                creativity_tgt_score = max(
                    _max_det_area(det_tgt, creativity_det_keys),
                    _max_area_list(top_areas, creativity_det_keys),
                )
                creativity_strength = max(creativity_trans_score, creativity_tgt_score)
                innovation_trans_score = _max_det_area(det_trans, innovation_det_keys)
                innovation_tgt_score = max(
                    _max_det_area(det_tgt, innovation_det_keys),
                    _max_area_list(top_areas, innovation_det_keys),
                )
                innovation_strength = max(innovation_trans_score, innovation_tgt_score)
                publication_planet_ok = A in ('Mercury', 'Jupiter') or target_planet in ('Mercury', 'Jupiter') or ruler_h3_present or ruler_h9_present
                publication_axis_ok = has_h9 or has_h3 or has_h10 or ('publication' in kw_all) or ('manuscript' in kw_all)
                if (
                    softish
                    and publication_planet_ok
                    and publication_axis_ok
                    and det_strength_val >= 0.5
                    and publishing_strength >= 0.5
                    and overall_val >= 0.5
                    and dir_val >= 0.2
                ):
                    _add('publication')
                creative_planet_ok = A in ('Venus', 'Moon', 'Sun', 'Neptune') or target_planet in ('Venus', 'Moon', 'Sun', 'Neptune')
                creative_axis_ok = has_h5 or has_h10 or has_h11 or ('art' in kw_all) or ('creativity' in kw_all)
                if (
                    softish
                    and creative_planet_ok
                    and creative_axis_ok
                    and det_strength_val >= 0.5
                    and creativity_strength >= 0.5
                    and overall_val >= 0.45
                ):
                    _add('artistic_success')
                innovation_planet_ok = A in ('Uranus', 'Mercury', 'Jupiter') or target_planet in ('Uranus', 'Mercury', 'Jupiter')
                innovation_axis_ok = has_h9 or has_h11 or has_h3 or ('innovation' in kw_all) or ('discovery' in kw_all)
                if (
                    (softish or 'conjunction' in label.lower())
                    and innovation_planet_ok
                    and innovation_axis_ok
                    and det_strength_val >= 0.6
                    and innovation_strength >= 0.6
                    and overall_val >= 0.6
                    and dir_val >= 0.3
                ):
                    _add('discovery_breakthrough')
                # Material and social losses
                health_trans_score = _max_det_area(det_trans, health_det_keys)
                health_tgt_score = max(
                    _max_det_area(det_tgt, health_det_keys),
                    _max_area_list(top_areas, health_det_keys),
                )
                health_strength = max(health_trans_score, health_tgt_score)
                acute_trans_score = _max_det_area(det_trans, acute_health_det_keys)
                acute_tgt_score = max(
                    _max_det_area(det_tgt, acute_health_det_keys),
                    _max_area_list(top_areas, acute_health_det_keys),
                )
                acute_strength = max(acute_trans_score, acute_tgt_score)
                chronic_trans_score = _max_det_area(det_trans, chronic_health_det_keys)
                chronic_tgt_score = max(
                    _max_det_area(det_tgt, chronic_health_det_keys),
                    _max_area_list(top_areas, chronic_health_det_keys),
                )
                chronic_strength = max(chronic_trans_score, chronic_tgt_score)
                fever_trans_score = _max_det_area(det_trans, fever_det_keys)
                fever_tgt_score = max(
                    _max_det_area(det_tgt, fever_det_keys),
                    _max_area_list(top_areas, fever_det_keys),
                )
                fever_strength = max(fever_trans_score, fever_tgt_score)
                injury_trans_score = _max_det_area(det_trans, injury_det_keys)
                injury_tgt_score = max(
                    _max_det_area(det_tgt, injury_det_keys),
                    _max_area_list(top_areas, injury_det_keys),
                )
                injury_strength = max(injury_trans_score, injury_tgt_score, danger_strength)
                surgery_trans_score = _max_det_area(det_trans, surgery_det_keys)
                surgery_tgt_score = max(
                    _max_det_area(det_tgt, surgery_det_keys),
                    _max_area_list(top_areas, surgery_det_keys),
                )
                surgery_strength = max(surgery_trans_score, surgery_tgt_score)
                hospital_trans_score = _max_det_area(det_trans, hospital_det_keys)
                hospital_tgt_score = max(
                    _max_det_area(det_tgt, hospital_det_keys),
                    _max_area_list(top_areas, hospital_det_keys),
                )
                hospital_strength = max(hospital_trans_score, hospital_tgt_score)
                recovery_trans_score = _max_det_area(det_trans, recovery_det_keys)
                recovery_tgt_score = max(
                    _max_det_area(det_tgt, recovery_det_keys),
                    _max_area_list(top_areas, recovery_det_keys),
                )
                recovery_strength = max(recovery_trans_score, recovery_tgt_score)
                possession_trans_score = _max_det_area(det_trans, possession_loss_det_keys)
                possession_tgt_score = max(
                    _max_det_area(det_tgt, possession_loss_det_keys),
                    _max_area_list(top_areas, possession_loss_det_keys),
                )
                possession_strength = max(possession_trans_score, possession_tgt_score, _max_det_area(det_trans, loss_det_keys))
                property_trans_score = _max_det_area(det_trans, property_det_keys)
                property_tgt_score = max(
                    _max_det_area(det_tgt, property_det_keys),
                    _max_area_list(top_areas, property_det_keys),
                )
                property_strength = max(property_trans_score, property_tgt_score)
                wealth_trans_score = _max_det_area(det_trans, wealth_det_keys)
                wealth_tgt_score = max(
                    _max_det_area(det_tgt, wealth_det_keys),
                    _max_area_list(top_areas, wealth_det_keys),
                )
                wealth_strength = max(wealth_trans_score, wealth_tgt_score)
                speculation_trans_score = _max_det_area(det_trans, speculation_det_keys)
                speculation_tgt_score = max(
                    _max_det_area(det_tgt, speculation_det_keys),
                    _max_area_list(top_areas, speculation_det_keys),
                )
                speculation_strength = max(speculation_trans_score, speculation_tgt_score)
                shared_gain_trans_score = _max_det_area(det_trans, shared_gain_det_keys)
                shared_gain_tgt_score = max(
                    _max_det_area(det_tgt, shared_gain_det_keys),
                    _max_area_list(top_areas, shared_gain_det_keys),
                )
                shared_gain_strength = max(shared_gain_trans_score, shared_gain_tgt_score)
                shared_loss_trans_score = _max_det_area(det_trans, shared_loss_det_keys)
                shared_loss_tgt_score = max(
                    _max_det_area(det_tgt, shared_loss_det_keys),
                    _max_area_list(top_areas, shared_loss_det_keys),
                )
                shared_loss_strength = max(shared_loss_trans_score, shared_loss_tgt_score)
                reputation_trans_score = _max_det_area(det_trans, reputation_det_keys)
                reputation_tgt_score = max(
                    _max_det_area(det_tgt, reputation_det_keys),
                    _max_area_list(top_areas, reputation_det_keys),
                )
                reputation_strength = max(reputation_trans_score, reputation_tgt_score)
                relationship_strength = max(
                    _max_det_area(det_trans, relationship_det_keys),
                    _max_det_area(det_tgt, relationship_det_keys),
                    _max_area_list(top_areas, relationship_det_keys),
                )
                marriage_strength = max(
                    _max_det_area(det_trans, marriage_det_keys),
                    _max_det_area(det_tgt, marriage_det_keys),
                    _max_area_list(top_areas, marriage_det_keys),
                )
                child_strength = max(
                    _max_det_area(det_trans, child_det_keys),
                    _max_det_area(det_tgt, child_det_keys),
                    _max_area_list(top_areas, child_det_keys),
                )
                family_strength = max(
                    _max_det_area(det_trans, family_det_keys),
                    _max_det_area(det_tgt, family_det_keys),
                    _max_area_list(top_areas, family_det_keys),
                )
                legal_strength = max(
                    _max_det_area(det_trans, legal_det_keys),
                    _max_det_area(det_tgt, legal_det_keys),
                    _max_area_list(top_areas, legal_det_keys),
                )
                imprisonment_strength = max(
                    _max_det_area(det_trans, imprisonment_det_keys),
                    _max_det_area(det_tgt, imprisonment_det_keys),
                    _max_area_list(top_areas, imprisonment_det_keys),
                )
                confusion_strength = max(
                    _max_det_area(det_trans, confusion_det_keys),
                    _max_det_area(det_tgt, confusion_det_keys),
                    _max_area_list(top_areas, confusion_det_keys),
                )
                def _remove(tok: str) -> None:
                    try:
                        while tok in enriched_now:
                            enriched_now.remove(tok)
                    except Exception:
                        pass
                benefic_planet = A in ('Jupiter', 'Venus', 'Sun') or target_planet in ('Jupiter', 'Venus', 'Sun')
                malefic_planet = A in ('Saturn', 'Mars') or target_planet in ('Saturn', 'Mars')
                fever_planet = A in ('Mars', 'Sun') or target_planet in ('Mars', 'Sun')
                health_axis_ok = has_h6 or has_h1 or has_h12
                illness_acute_ok = (
                    hardish
                    and malefic_planet
                    and health_axis_ok
                    and health_strength >= 0.5
                    and acute_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.5
                )
                if illness_acute_ok:
                    _add('illness_acute')
                else:
                    _remove('illness_acute')
                chronic_ok = (
                    hardish
                    and (A == 'Saturn' or target_planet == 'Saturn')
                    and (has_h6 or has_h12)
                    and chronic_strength >= 0.6
                    and health_strength >= 0.5
                    and det_strength_val >= 0.6
                    and overall_val >= 0.55
                )
                if chronic_ok:
                    _add('illness_chronic')
                else:
                    _remove('illness_chronic')
                fever_ok = (
                    (hardish or 'conjunction' in label.lower())
                    and fever_planet
                    and health_axis_ok
                    and fever_strength >= 0.45
                    and health_strength >= 0.4
                    and det_strength_val >= 0.45
                    and overall_val >= 0.45
                    and orb_val <= 1.2
                )
                if fever_ok:
                    _add('fever')
                else:
                    _remove('fever')
                injury_ok = (
                    hardish
                    and malefic_planet
                    and (has_h1 or has_h6 or has_h8)
                    and injury_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.55
                    and orb_val <= 1.2
                )
                if injury_ok:
                    _add('injury_accident')
                else:
                    _remove('injury_accident')
                surgery_ok = (
                    (A == 'Mars' or target_planet == 'Mars')
                    and (hardish or 'conjunction' in label.lower())
                    and (has_h6 or has_h8 or has_h12)
                    and surgery_strength >= 0.45
                    and det_strength_val >= 0.45
                    and overall_val >= 0.5
                    and orb_val <= 1.5
                )
                if surgery_ok:
                    _add('surgery')
                else:
                    _remove('surgery')
                hospital_ok = (
                    (malefic_planet or tone == 'negative')
                    and (has_h12 or has_h6 or has_h8)
                    and hospital_strength >= 0.45
                    and det_strength_val >= 0.45
                    and overall_val >= 0.5
                )
                if hospital_ok:
                    _add('hospitalization')
                else:
                    _remove('hospitalization')
                recovery_ok = (
                    softish
                    and benefic_planet
                    and (has_h1 or has_h6)
                    and recovery_strength >= 0.5
                    and health_strength >= 0.45
                    and det_strength_val >= 0.5
                    and overall_val >= 0.45
                )
                if recovery_ok:
                    _add('recovery_health')
                else:
                    _remove('recovery_health')
                danger_strength_full = max(
                    _max_det_area(det_trans, danger_det_keys),
                    _max_det_area(det_tgt, danger_det_keys),
                    _max_area_list(top_areas, danger_det_keys),
                )
                death_strength = max(
                    _max_det_area(det_trans, death_det_keys),
                    _max_det_area(det_tgt, death_det_keys),
                    _max_area_list(top_areas, death_det_keys),
                )
                twelfth_strength = max(
                    _max_det_area(det_trans, twelfth_det_keys),
                    _max_det_area(det_tgt, twelfth_det_keys),
                    _max_area_list(top_areas, twelfth_det_keys),
                )
                if (
                    malefic_planet
                    and has_h1
                    and hardish
                    and max(danger_strength_full, death_strength) >= 0.7
                    and twelfth_strength >= 0.6
                    and (poor_state or overall_val >= 0.65)
                ):
                    _add('death_threat_high')
                elif (
                    malefic_planet
                    and has_h1
                    and hardish
                    and max(danger_strength_full, death_strength) >= 0.5
                    and (multi_factor > 1.05 or twelfth_strength >= 0.5)
                ):
                    _add('death_threat_moderate')
                if (
                    (A in ('Saturn','Mars'))
                    and (has_h6 or has_h1)
                    and hardish
                    and chronic_strength >= 0.6
                    and (station_like or retrograde_flag)
                ):
                    _add('severe_illness_onset')
                if (
                    (A == 'Saturn')
                    and has_h6
                    and hardish
                    and chronic_strength >= 0.5
                ):
                    _add('chronic_illness_development')
                if (
                    (A in ('Mars','Uranus'))
                    and (has_h6 or has_h12)
                    and hardish
                    and acute_strength >= 0.4
                    and danger_strength_full >= 0.4
                ):
                    _add('sudden_health_crisis')
                if (
                    is_benefic
                    and (A in ('Jupiter','Venus'))
                    and (has_h1 or has_h6)
                    and softish
                    and recovery_strength >= 0.4
                    and (good_state or overall_val >= 0.45)
                ):
                    _add('recovery_period')
                if (
                    (A in ('Sun','Jupiter'))
                    and has_h1
                    and (softish or 'conjunction' in label.lower())
                    and health_strength >= 0.5
                    and (good_state or overall_val >= 0.5)
                ):
                    _add('vitality_strengthening')
                if (
                    has_rel
                    and softish
                    and marriage_strength >= 0.6
                    and (A in ('Venus','Jupiter') or is_benefic)
                    and good_state
                ):
                    _add('marriage_likely')
                if (
                    has_rel
                    and softish
                    and relationship_strength >= 0.5
                    and (is_benefic or A in ('Venus','Jupiter'))
                    and overall_val >= 0.45
                ):
                    _add('significant_partnership')
                if (
                    has_rel
                    and hardish
                    and relationship_strength >= 0.6
                    and malefic_planet
                    and (poor_state or overall_val <= 0.45)
                ):
                    _add('divorce_or_separation')
                if (
                    has_rel
                    and hardish
                    and relationship_strength >= 0.4
                    and A == 'Mars'
                ):
                    _add('relationship_crisis')
                if (
                    has_rel
                    and softish
                    and relationship_strength >= 0.4
                    and A == 'Venus'
                    and good_state
                ):
                    _add('harmonious_relationship_period')
                if (
                    has_h5
                    and softish
                    and child_strength >= 0.6
                    and (A in ('Jupiter','Venus','Moon','Sun') or is_benefic)
                ):
                    _add('childbirth')
                if (
                    has_h5
                    and hardish
                    and child_strength >= 0.5
                    and malefic_planet
                    and (poor_state or danger_strength_full >= 0.5)
                ):
                    _add('loss_of_child')
                if (
                    has_h4
                    and hardish
                    and family_strength >= 0.4
                    and (A == 'Mars' or malefic_planet)
                ):
                    _add('family_conflict')
                if (
                    has_money
                    and softish
                    and wealth_strength >= 0.7
                    and (A == 'Jupiter' or is_benefic)
                    and (('pof' in kw_all) or base_lbl == 'POF' or target_planet == 'POF')
                    and good_state
                ):
                    _add('major_wealth_acquisition')
                if (
                    (has_money or has_h11)
                    and softish
                    and wealth_strength >= 0.5
                    and (A in ('Jupiter','Uranus'))
                    and good_state
                ):
                    _add('unexpected_financial_gain')
                if (
                    has_h8
                    and softish
                    and shared_gain_strength >= 0.5
                    and (A == 'Jupiter' or is_benefic)
                ):
                    _add('inheritance_received')
                if (
                    has_money
                    and hardish
                    and shared_loss_strength >= 0.6
                    and malefic_planet
                    and (poor_state or overall_val <= 0.45)
                ):
                    _add('major_financial_loss')
                if (
                    has_money
                    and hardish
                    and shared_loss_strength >= 0.7
                    and malefic_planet
                    and (poor_state or very_poor_state)
                    and multi_factor > 1.05
                ):
                    _add('bankruptcy_risk')
                if (
                    (has_money or has_h8)
                    and hardish
                    and shared_loss_strength >= 0.5
                    and A == 'Saturn'
                ):
                    _add('debt_crisis')
                lawsuit_ok = (
                    hardish
                    and legal_strength >= 0.5
                    and det_strength_val >= 0.45
                    and (has_rel or has_career or has_money or has_shared)
                    and (A in ('Mercury', 'Saturn', 'Mars') or target_planet in ('Mercury', 'Saturn', 'Mars'))
                )
                if lawsuit_ok:
                    _add('lawsuit')
                else:
                    _remove('lawsuit')
                if (
                    has_rel
                    and hardish
                    and legal_strength >= 0.5
                    and A == 'Mars'
                    and has_h1
                ):
                    _add('major_lawsuit_initiated')
                else:
                    _remove('major_lawsuit_initiated')
                legal_victory_ok = (
                    legal_strength >= 0.5
                    and softish
                    and (A == 'Jupiter' or is_benefic)
                    and good_state
                )
                if legal_victory_ok:
                    _add('legal_victory')
                else:
                    _remove('legal_victory')
                legal_resolution_ok = (
                    legal_strength >= 0.45
                    and softish
                    and det_strength_val >= 0.45
                    and overall_val >= 0.45
                    and (A in ('Jupiter', 'Sun', 'Mercury') or is_benefic)
                )
                if legal_resolution_ok:
                    _add('legal_resolution')
                else:
                    _remove('legal_resolution')
                settlement_ok = (
                    legal_strength >= 0.45
                    and softish
                    and det_strength_val >= 0.45
                    and overall_val >= 0.45
                    and has_money
                    and (has_rel or has_career or has_shared)
                    and (A in ('Venus', 'Jupiter', 'Mercury') or is_benefic)
                )
                if settlement_ok:
                    _add('settlement')
                else:
                    _remove('settlement')
                legal_defeat_ok = (
                    legal_strength >= 0.5
                    and hardish
                    and (A == 'Saturn' or malefic_planet)
                    and (poor_state or overall_val <= 0.45)
                )
                if legal_defeat_ok:
                    _add('legal_defeat')
                else:
                    _remove('legal_defeat')
                imprisonment_event_ok = (
                    has_h12
                    and hardish
                    and det_strength_val >= 0.55
                    and imprisonment_strength >= 0.7
                    and overall_val >= 0.55
                    and dir_val >= 0.25
                    and (A == 'Saturn' or malefic_planet)
                    and (poor_state or very_poor_state)
                )
                if imprisonment_event_ok:
                    _add('arrest_imprisonment')
                else:
                    _remove('arrest_imprisonment')
                imprisonment_risk_ok = (
                    has_h12
                    and hardish
                    and (A == 'Saturn' or malefic_planet)
                    and imprisonment_strength >= 0.6
                    and (poor_state or very_poor_state)
                )
                if imprisonment_risk_ok:
                    _add('imprisonment_risk')
                else:
                    _remove('imprisonment_risk')
                loss_planet_ok = A in ('Saturn', 'Mars', 'Mercury') or target_planet in ('Saturn', 'Mars')
                possession_axis_ok = has_h2 or has_h8 or has_h12 or ('money' in kw_all) or ('possessions' in kw_all) or ('theft' in kw_all)
                if (
                    hardish
                    and loss_planet_ok
                    and possession_axis_ok
                    and det_strength_val >= 0.4
                    and possession_strength >= 0.4
                    and overall_val >= 0.4
                    and tone == 'negative'
                ):
                    _add('loss_of_possessions')
                reputation_planet_ok = A in ('Saturn', 'Mars', 'Sun') or target_planet in ('Saturn', 'Mars', 'Sun') or has_h10
                reputation_axis_ok = has_h10 or has_h11 or ('reputation' in kw_all) or ('career' in kw_all) or ('public' in kw_all)
                if (
                    hardish
                    and reputation_planet_ok
                    and reputation_axis_ok
                    and det_strength_val >= 0.6
                    and reputation_strength >= 0.6
                    and overall_val >= 0.6
                    and dir_val >= 0.3
                    and tone == 'negative'
                ):
                    _add('reputation_damage')
                if (
                    softish
                    and benefic_planet
                    and has_h4
                    and property_strength >= 0.5
                    and wealth_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.5
                    and dir_val >= 0.2
                ):
                    _add('property_value_increase')
                if (
                    hardish
                    and malefic_planet
                    and has_h4
                    and property_strength >= 0.4
                    and possession_strength >= 0.4
                    and det_strength_val >= 0.45
                    and overall_val >= 0.55
                    and dir_val >= 0.3
                    and tone == 'negative'
                ):
                    _add('property_value_decrease')
                if (
                    softish
                    and benefic_planet
                    and has_h5
                    and speculation_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.55
                    and dir_val >= 0.25
                ):
                    _add('speculation_gain')
                if (
                    hardish
                    and malefic_planet
                    and has_h5
                    and speculation_strength >= 0.45
                    and det_strength_val >= 0.45
                    and overall_val >= 0.5
                    and tone == 'negative'
                ):
                    _add('speculation_loss')
                if (
                    softish
                    and benefic_planet
                    and has_h8
                    and shared_gain_strength >= 0.5
                    and det_strength_val >= 0.5
                    and overall_val >= 0.55
                ):
                    _add('inheritance_windfall')
                if (
                    hardish
                    and malefic_planet
                    and has_h8
                    and shared_loss_strength >= 0.45
                    and det_strength_val >= 0.45
                    and overall_val >= 0.5
                    and tone == 'negative'
                ):
                    _add('shared_resource_loss')
                # War / conflict authority configurations
                authority_axis_ok = has_h10 or _has_cap('MC') or ('authority' in kw_all) or ('command' in kw_all)
                enemy_axis_ok = has_h7 or _has_cap('C7') or ('enemy' in kw_all) or ('enemies' in kw_all)
                foreign_axis_ok = has_h9 or ('foreign' in kw_all) or ('abroad' in kw_all)
                homeland_axis_ok = has_h4 or has_h1 or ('homeland' in kw_all) or ('defense' in kw_all)
                target_authority = base_lbl in ('MC', 'Sun') or _has_cap('MC') or _has_cap('C10')
                mars_involved = (A == 'Mars') or (target_planet == 'Mars')
                sun_involved = (A == 'Sun') or (target_planet == 'Sun') or ('Sun' in (row.get('keywords') or []))
                if (
                    mars_involved
                    and hardish
                    and orb_val <= 1.0
                    and authority_axis_ok
                    and target_authority
                    and enemy_axis_ok
                    and authority_strength >= 0.7
                    and conflict_strength >= 0.6
                    and enemy_strength >= 0.5
                    and foreign_strength >= 0.4
                    and det_strength_val >= 0.65
                    and overall_val >= 0.7
                    and dir_val >= 0.5
                    and sun_involved
                ):
                    _add('war_declaration_offensive')
                defensive_mars = A in ('Mars', 'Saturn') or target_planet in ('Mars', 'Saturn')
                if (
                    defensive_mars
                    and hardish
                    and orb_val <= 1.2
                    and homeland_axis_ok
                    and enemy_axis_ok
                    and authority_strength >= 0.5
                    and conflict_strength >= 0.5
                    and homeland_strength >= 0.5
                    and overall_val >= 0.6
                    and dir_val >= 0.4
                ):
                    _add('war_response_defensive')
                internal_axis_ok = has_h4 and has_h10
                if (
                    defensive_mars
                    and hardish
                    and internal_axis_ok
                    and authority_strength >= 0.6
                    and conflict_strength >= 0.5
                    and homeland_strength >= 0.5
                    and foreign_strength < 0.4
                    and overall_val >= 0.55
                    and dir_val >= 0.35
                ):
                    _add('internal_conflict_war')
                # Severe danger events (accident, near death, violence, fire, drowning, fall)
                accident_strength = max(
                    _max_det_area(det_trans, accident_det_keys),
                    _max_area_list(top_areas, accident_det_keys),
                )
                near_death_strength = max(
                    _max_det_area(det_trans, near_death_det_keys),
                    _max_area_list(top_areas, near_death_det_keys),
                )
                fire_strength = max(
                    _max_det_area(det_trans, fire_det_keys),
                    _max_area_list(top_areas, fire_det_keys),
                )
                water_strength = max(
                    _max_det_area(det_trans, water_det_keys),
                    _max_area_list(top_areas, water_det_keys),
                )
                fall_strength = max(
                    _max_det_area(det_trans, fall_det_keys),
                    _max_area_list(top_areas, fall_det_keys),
                )
                danger_strength = max(
                    _max_det_area(det_trans, danger_det_keys),
                    _max_area_list(top_areas, danger_det_keys),
                )
                try:
                    orb_val = abs(float(row.get('orb') or 0.0))
                except Exception:
                    orb_val = 9.99
                tone = str(row.get('tone') or '').lower()
                target_planet = base_lbl
                accident_planet_ok = A in ('Mars', 'Saturn', 'Uranus') or target_planet in ('Mars', 'Saturn', 'Uranus')
                accident_axis_ok = (has_h1 or has_h8 or has_h12) and (has_h3 or has_h6 or has_h8)
                if (
                    hardish
                    and accident_planet_ok
                    and accident_axis_ok
                    and det_strength_val >= 0.6
                    and accident_strength >= 0.6
                    and danger_strength >= 0.55
                    and overall_val >= 0.7
                    and dir_val >= 0.4
                    and orb_val <= 1.0
                ):
                    _add('accident_major')
                near_death_planet_ok = (
                    A in ('Mars', 'Saturn') or target_planet in ('Mars', 'Saturn')
                )
                near_death_axis_ok = has_h8 and (has_h1 or has_h12)
                if (
                    (hardish or 'conjunction' in label.lower())
                    and near_death_planet_ok
                    and near_death_axis_ok
                    and det_strength_val >= 0.7
                    and near_death_strength >= 0.7
                    and danger_strength >= 0.65
                    and overall_val >= 0.75
                    and dir_val >= 0.5
                    and orb_val <= 0.6
                ):
                    _add('near_death_experience')
                violence_planet_ok = A in ('Mars', 'Saturn', 'Uranus') or target_planet in ('Mars', 'Saturn', 'Uranus')
                violence_axis_ok = has_h1 or has_h8 or has_h12 or has_h7
                if (
                    hardish
                    and violence_planet_ok
                    and violence_axis_ok
                    and det_strength_val >= 0.6
                    and danger_det_score >= 0.6
                    and overall_val >= 0.55
                    and dir_val >= 0.35
                    and orb_val <= 1.2
                ):
                    _add('attack_violence')
                fire_planet_ok = A in ('Mars', 'Sun') or target_planet in ('Mars', 'Sun')
                fire_axis_ok = has_h1 or has_h4 or has_h6 or has_h8
                if (
                    (hardish or (A == 'Sun' and tone == 'negative'))
                    and fire_planet_ok
                    and fire_axis_ok
                    and det_strength_val >= 0.5
                    and fire_strength >= 0.5
                    and danger_strength >= 0.45
                    and overall_val >= 0.45
                    and orb_val <= 1.0
                ):
                    _add('fire_burn')
                water_planet_ok = A in ('Moon', 'Mars', 'Neptune') or target_planet in ('Moon', 'Mars', 'Neptune')
                water_axis_ok = has_h4 or has_h8 or has_h12
                if (
                    hardish
                    and water_planet_ok
                    and water_axis_ok
                    and det_strength_val >= 0.6
                    and water_strength >= 0.6
                    and danger_strength >= 0.55
                    and overall_val >= 0.6
                    and dir_val >= 0.4
                    and orb_val <= 0.7
                ):
                    _add('drowning_submersion')
                fall_planet_ok = A in ('Saturn', 'Mars', 'Uranus') or target_planet in ('Saturn', 'Mars', 'Uranus')
                fall_axis_ok = has_h1 or has_h6 or has_h8 or has_h12
                if (
                    hardish
                    and fall_planet_ok
                    and fall_axis_ok
                    and det_strength_val >= 0.5
                    and fall_strength >= 0.5
                    and danger_strength >= 0.5
                    and overall_val >= 0.5
                    and dir_val >= 0.3
                    and orb_val <= 1.0
                ):
                    _add('fall_from_height')
                # Death events with concordance + determination gates
                conc = row.get('concordance') or {}
                try:
                    dir_ok = float(conc.get('direction_concordance') or 0.0) >= 0.5
                    ov_ok = float(conc.get('overall_concordance') or 0.0) >= 0.6
                except Exception:
                    dir_ok = False
                    ov_ok = False
                fam_houses = {4, 10, 7, 5}
                has_family_target = (
                    any(_has_cap(f'C{h}') for h in fam_houses) or
                    any(_has_cap(f'Ruler(H{h})') for h in fam_houses) or
                    (isinstance(row.get('natal_house'), int) and int(row['natal_house']) in fam_houses)
                )
                has_h1 = _has_cap('C1') or _has_cap('Asc') or ((row.get('natal_house') == 1))
                has_h8 = _has_cap('C8') or ('shared_resources' in kw_all) or ((row.get('natal_house') == 8))
                has_ruler_h8 = _has_cap('Ruler(H8)') or ('ruler(h8)' in kw_all) or ('ruler(shared_resources)' in kw_all)
                is_mal = A in ('Mars', 'Saturn')
                death_trans_score = _max_det_area(det_trans, death_det_keys)
                death_tgt_score = max(
                    _max_det_area(det_tgt, death_det_keys),
                    _max_area_list(top_areas, death_det_keys),
                )
                violence_trans_score = max(_max_det_area(det_trans, violence_det_keys), death_trans_score)
                violence_tgt_score = max(
                    _max_det_area(det_tgt, violence_det_keys),
                    _max_area_list(top_areas, violence_det_keys),
                    death_tgt_score,
                )
                family_trans_score = _max_det_area(det_trans, family_det_keys)
                family_tgt_score = max(
                    _max_det_area(det_tgt, family_det_keys),
                    _max_area_list(top_areas, family_det_keys),
                )
                loss_trans_score = max(_max_det_area(det_trans, loss_det_keys), death_trans_score)
                death_signal_ok = (dir_ok or ov_ok)
                if is_mal and hardish and death_signal_ok:
                    if has_family_target:
                        if (
                            det_strength_val >= 0.5
                            and family_trans_score >= 0.5
                            and loss_trans_score >= 0.5
                            and family_tgt_score >= 0.5
                        ):
                            _add('death_of_family')
                    death_target_hook = (
                        death_tgt_score >= 0.7 or has_h1 or has_h8 or has_ruler_h8
                    )
                    if det_strength_val >= 0.7 and death_trans_score >= 0.7 and death_target_hook:
                        violent_ready = (
                            det_strength_val >= 0.8
                            and violence_trans_score >= 0.8
                            and (violence_tgt_score >= 0.8 or has_h1 or has_h8 or has_ruler_h8)
                        )
                        if violent_ready and (A == 'Mars' or has_h1 or has_h8 or has_ruler_h8):
                            _add('death_violent')
                        else:
                            _add('death_natural')
                # Special concordance, timing, and context-sensitive tokens
                syzygies = list(row.get('syzygies') or [])
                def _clean_target_label(val: Any) -> str:
                    return str(val or '').replace(' (antiscia)', '').replace(' (contra-antiscia)', '').lower()
                base_norm = _clean_target_label(base_lbl)
                label_lower = label.lower()
                A_lower = A.lower()
                benefic_set_l = {'jupiter', 'venus', 'sun'}
                malefic_set_l = {'saturn', 'mars'}
                light_set_l = {'sun', 'moon'}
                same_target_syzygies = [
                    s for s in syzygies
                    if _clean_target_label(s.get('target') or s.get('natal') or '') == base_norm
                ]
                def _syzygy_aspect(entry: Dict[str, Any]) -> str:
                    return str(entry.get('aspect') or '').lower()
                def _syzygy_orb(entry: Dict[str, Any]) -> float:
                    try:
                        return abs(float(entry.get('orb') or 0.0))
                    except Exception:
                        return 99.0
                benefic_conj_count = sum(
                    1 for s in same_target_syzygies
                    if str(s.get('planet') or '').lower() in benefic_set_l
                    and 'conj' in _syzygy_aspect(s)
                    and _syzygy_orb(s) <= 2.0
                )
                primary_benefic = (A_lower in benefic_set_l) and ('conj' in label_lower)
                if (
                    primary_benefic
                    and det_strength_val >= 0.6
                    and (excellent_state or (good_state and overall_val >= 0.6))
                    and benefic_conj_count + 1 >= 2
                    and multi_factor > 1.05
                ):
                    _add('fateful_day_benefic')
                malefic_syzygy_same_point = any(
                    str(s.get('planet') or '').lower() in malefic_set_l
                    and 'conj' in _syzygy_aspect(s)
                    and _syzygy_orb(s) <= 2.0
                    for s in same_target_syzygies
                )
                malefic_syzygy_hard = any(
                    str(s.get('planet') or '').lower() in malefic_set_l
                    and any(key in _syzygy_aspect(s) for key in ('square', 'opposition', 'conj'))
                    and _syzygy_orb(s) <= 3.0
                    for s in syzygies
                    if _clean_target_label(s.get('target') or s.get('natal') or '') == base_norm
                )
                negative_house_focus = (
                    has_h6 or has_h8 or has_h12
                    or base_lbl in {'C6', 'C8', 'C12', 'Ruler(H6)', 'Ruler(H8)', 'Ruler(H12)'}
                    or (event_domain and event_domain in {'danger', 'death', 'illness', 'shared_resources'})
                )
                poor_condition = poor_state or very_poor_state or overall_val <= 0.45
                if (
                    A_lower in malefic_set_l
                    and hardish
                    and det_strength_val >= 0.6
                    and negative_house_focus
                    and (malefic_syzygy_same_point or ('opp' in label_lower and base_lbl in {'Saturn', 'Mars'}))
                    and poor_condition
                ):
                    _add('fateful_day_malefic')
                special_flags = row.get('special_flags') or {}
                other_light_conj = any(
                    str(s.get('planet') or '').lower() in light_set_l
                    and str(s.get('planet') or '').lower() != A_lower
                    and 'conj' in _syzygy_aspect(s)
                    and _syzygy_orb(s) <= 1.5
                    for s in same_target_syzygies
                )
                primary_light = A_lower in light_set_l
                if (
                    primary_light
                    and 'conj' in label_lower
                    and det_strength_val >= 0.5
                    and (other_light_conj or special_flags.get('lethal_new_moon'))
                    and orb_val <= 1.5
                ):
                    _add('eclipse_activation')
                lunation_flag = bool(
                    special_flags.get('lethal_new_moon')
                    or special_flags.get('lethal_full_moon')
                    or (primary_light and other_light_conj)
                )
                if (
                    lunation_flag
                    and malefic_syzygy_hard
                    and det_strength_val >= 0.6
                    and (angular_target or base_lbl in {'C1', 'C4', 'C7', 'C10'})
                ):
                    _add('syzygy_critical')
                danger_gate = max(danger_strength_full, death_trans_score, death_tgt_score)
                if (
                    lunation_flag
                    and (malefic_planet or malefic_syzygy_hard)
                    and has_h1
                    and danger_gate >= 0.6
                ):
                    _add('lights_conjunction_malefic')
                cardinal_labels = {'Asc', 'MC', 'IC', 'Desc', 'C1', 'C4', 'C7', 'C10'}
                cardinal_target = base_lbl in cardinal_labels or (
                    isinstance(row.get('natal_house'), int) and row.get('natal_house') in (1, 4, 7, 10)
                )
                if (
                    A_lower in {'saturn', 'jupiter', 'mars'}
                    and det_strength_val >= 0.4
                    and orb_val <= 1.5
                ):
                    _add('slow_planet_transit')
                if (
                    station_like
                    and det_strength_val >= 0.4
                    and cardinal_target
                    and orb_val <= 1.0
                ):
                    _add('stationary_planet_transit')
                if (
                    retrograde_flag
                    and A_lower in malefic_set_l
                    and hardish
                    and det_strength_val >= 0.5
                ):
                    _add('retrograde_malefic')
                if det_strength_val >= 0.45 and len(determination_sources) >= 3:
                    _add('multiple_determination')
                if det_strength_val >= 0.4 and cardinal_target:
                    _add('cardinal_cusp_involvement')
                luminary_support = (
                    primary_light
                    or any(str(s.get('planet') or '').lower() in light_set_l for s in same_target_syzygies)
                    or bool(locals().get('light_meta'))
                )
                if luminary_support and det_strength_val >= 0.4:
                    _add('luminary_participation')
                direction_matches = conc.get('direction_matches') or []
                dormant_matches = [
                    m for m in direction_matches
                    if 'dormant' in str((m or {}).get('type') or '').lower()
                ]
                if (
                    dormant_matches
                    and det_strength_val >= 0.5
                    and (dir_val >= 0.35 or multi_factor > 1.05)
                ):
                    _add('dormant_direction_activated')
                revolution_both = False
                if event_domain and isinstance(sr_domains_norm, set) and isinstance(lr_domains_norm, set):
                    revolution_both = (
                        (event_domain in sr_domains_norm) and (event_domain in lr_domains_norm)
                    )
                if not revolution_both and solar_norm >= 0.5 and lunar_norm >= 0.5:
                    revolution_both = True
                if revolution_both and det_strength_val >= 0.5:
                    _add('revolution_amplified')
                reckless_cues = any(
                    token in kw_all for token in {'reckless', 'violence', 'brawl', 'intemperate', 'aggression'}
                )
                if (
                    native_age_years is not None
                    and native_age_years < 30.0
                    and A == 'Mars'
                    and hardish
                    and det_strength_val >= 0.4
                    and (accident_strength >= 0.5 or danger_strength >= 0.5 or near_death_strength >= 0.5)
                    and (is_summer_season or 'summer' in kw_all)
                    and (reckless_cues or malefic_syzygy_hard)
                ):
                    _add('youth_recklessness_danger')
                if (
                    native_age_years is not None
                    and native_age_years >= 60.0
                    and A == 'Saturn'
                    and (has_h6 or has_h12)
                    and det_strength_val >= 0.4
                    and health_strength >= 0.5
                    and (hardish or tone == 'negative')
                    and (danger_strength >= 0.45 or chronic_strength >= 0.5)
                ):
                    _add('elder_health_crisis')
                # Persist augmented list
                row['enriched_keywords'] = enriched_now
                kw_all = set([str(x).lower() for x in (row.get('enriched_keywords') or [])])
            except Exception:
                pass

            # Event type from enriched keywords (keep current coded keywords)
            event_candidates = [
                'promotion','recognition','business_deal','contract_signing','communication_breakthrough','romantic_connection','romance','marriage','reconciliation','relationship_conflict',
                'financial_gain','financial_loss','injury_risk','accident_risk','public_recognition','parties_celebrations','opportunity_received',
                'protection_granted','delay_obstruction','illness_chronic','fall_from_power','authority_problems','domestic_happiness','family_joy',
                'domestic_disruption','family_problems','miscommunication','excess_problems','structure_established','discipline_rewarded','authority_earned',
                # Extended canonical events from catalog (non-breaking additions)
                'honor_award','new_job','job_loss','inheritance','salary_increase',
                'degree_completion','exam_success','exam_failure','enrollment_admission',
                'accident_major','near_death_experience',
                'war_declaration_offensive','war_response_defensive','internal_conflict_war','warfare_involvement','enemy_attack','violent_confrontation',
                'attack_violence','fire_burn','drowning_submersion','fall_from_height',
                'publication','artistic_success','discovery_breakthrough','loss_of_possessions','reputation_damage',
                'property_value_increase','property_value_decrease','speculation_gain','speculation_loss','inheritance_windfall','shared_resource_loss',
                'spiritual_awakening','religious_conversion','pilgrimage','mystical_experience',
                'lawsuit','legal_victory','legal_defeat','legal_resolution','settlement','arrest_imprisonment',
                'illness_acute','injury_accident','surgery','hospitalization','recovery_health','fever',
                'demotion','business_success','business_failure','retirement',
                'birth_of_child','birth_self','death_natural','death_violent','death_of_family','short_journey','long_journey',
                'partnership_strengthened','partnership_strained','pregnancy','engagement','divorce','separation','betrayal',
                'investment_success','investment_loss','bankruptcy','theft_fraud','family_celebration','family_conflict','moving_home','purchase_property','relocation_permanent','travel_accident'
                ,'death_threat_high','death_threat_moderate','severe_illness_onset','life_threatening_accident','chronic_illness_development','sudden_health_crisis','recovery_period','vitality_strengthening'
                ,'exceptional_honor_received','career_elevation','disgrace_or_scandal','career_setback_major','professional_recognition','power_increase','loss_of_authority','public_humiliation'
                ,'major_wealth_acquisition','unexpected_financial_gain','inheritance_received','major_financial_loss','bankruptcy_risk','debt_crisis'
                ,'marriage_likely','significant_partnership','divorce_or_separation','relationship_crisis','harmonious_relationship_period','childbirth','loss_of_child'
                ,'major_lawsuit_initiated','imprisonment_risk'
                ,'major_journey_fortunate','travel_misfortune','foreign_residence','exile_or_forced_travel'
                ,'intellectual_breakthrough','educational_achievement','mental_confusion_period','church_honors'
                ,'fateful_day_benefic','fateful_day_malefic','eclipse_activation','syzygy_critical','station_on_sensitive_point','lights_conjunction_malefic'
                ,'slow_planet_transit','stationary_planet_transit','retrograde_malefic','multiple_determination','cardinal_cusp_involvement','luminary_participation','dormant_direction_activated','revolution_amplified','youth_recklessness_danger','elder_health_crisis'
            ]
            crisis_event_candidates = [
                'war_declaration_offensive','war_response_defensive','internal_conflict_war','warfare_involvement','enemy_attack','violent_confrontation',
                'attack_violence','accident_major','near_death_experience','life_threatening_accident','death_violent',
                'death_natural','death_of_family','death_threat_high','death_threat_moderate',
                'fire_burn','drowning_submersion','fall_from_height','injury_accident','travel_accident','arrest_imprisonment',
            ]
            if any(ev in kw_all for ev in crisis_event_candidates):
                event_search_order = crisis_event_candidates + [ev for ev in event_candidates if ev not in crisis_event_candidates]
            else:
                event_search_order = event_candidates
            event_type = _select_row_event_type(row, life_area, kw_all, event_search_order)
            confidence = round(max(0.0, min(1.0, overall_norm)), 2)
            try:
                from nlg_templates import prediction_evidence_level
                evidence_level = prediction_evidence_level(row)
            except Exception:
                evidence_level = 'theme_only'
            prediction_label = None
            try:
                transiting_label = str(row.get('transiting') or '')
                aspect_label = str(row.get('aspect') or '')
                target_label = str(row.get('target_label') or row.get('natal') or '')
                if transiting_label and aspect_label and target_label:
                    prediction_label = f"{transiting_label} {aspect_label} {target_label}"
            except Exception:
                prediction_label = None
            row['prediction'] = {
                'lifeArea': life_area,
                'eventType': event_type,
                'label': prediction_label,
                'description': None,
                'confidence': confidence,
                'confidenceBasis': 'morin_rule_concordance',
                'evidenceLevel': evidence_level,
                'isEventPrediction': bool(event_type) and evidence_level in {'supported', 'corroborated'},
                'score': row.get('prediction_score'),
                'tags': row.get('prediction_tags', []),
            }
            # Boost quality for natal echo (gentle)
            try:
                if ('Natal echo' in (row.get('keywords') or [])) or ('natal echo' in set([str(x).lower() for x in (row.get('enriched_keywords') or [])])):
                    if isinstance(row.get('quality_score'), (int, float)):
                        row['quality_score'] = round(min(10.0, float(row['quality_score']) + 1.0), 1)
                        row['quality_label'] = row.get('quality_label') or row.get('quality')
            except Exception:
                pass
            # Description
            try:
                from nlg_templates import render_prediction
                # Pass through: enrich function will use hit.prediction + concordance + keywords
                desc = render_prediction(row)
            except Exception:
                try:
                    A = str(row.get('transiting') or '')
                    asp = str(row.get('aspect') or '')
                    tgt = str(row.get('target_label') or row.get('natal') or '')
                    desc = f"{A} {asp} {tgt}"
                except Exception:
                    desc = None
            row['prediction']['description'] = desc
            row['life_area'] = life_area
            # Quality score/label per Morin's hierarchy (determination-led)
            try:
                # Derive target life area from target label/cusp
                target_area_source: Optional[str] = None

                def _target_area_from_row(r: Dict[str, Any]) -> Optional[str]:
                    nonlocal target_area_source
                    base = str(r.get('target_label') or r.get('natal') or '')
                    b = base.replace(' (antiscia)', '').replace(' (contra-antiscia)', '')
                    if b == 'Asc':
                        target_area_source = 'ascendant'
                        return 'life'
                    if b == 'MC':
                        target_area_source = 'mc'
                        return 'honors'
                    if b.startswith('C') and b[1:].isdigit():
                        try:
                            area = _pick_contextual_domain(_house_candidate_domains(int(b[1:])), row=r)
                        except Exception:
                            area = None
                        if area:
                            target_area_source = 'cusp'
                            return area
                    if str(r.get('target_type') or '') == 'planet':
                        candidates: List[Tuple[str, float, str]] = []

                        def _add_candidate(area: Optional[str], weight: float, source: str) -> None:
                            if not area:
                                return
                            norm = _normalize_domain(area)
                            if not norm:
                                return
                            candidates.append((norm, float(weight), source))

                        tgt_det = det_tgt if isinstance(det_tgt, dict) else {}
                        # Location of natal planet
                        loc_house: Optional[int] = None
                        try:
                            loc_house = (tgt_det.get('housePosition') or {}).get('house') if isinstance(tgt_det.get('housePosition'), dict) else None
                        except Exception:
                            loc_house = None
                        if isinstance(loc_house, int):
                            for loc_area in _house_candidate_domains(loc_house):
                                _add_candidate(loc_area, 1.0, 'location')
                        # Rulerships
                        for rul in (tgt_det.get('rulerships') or []):
                            try:
                                rh = int(rul.get('house'))
                            except Exception:
                                rh = None
                            if rh is None:
                                continue
                            for area_rul in _house_candidate_domains(rh):
                                _add_candidate(area_rul, 0.75, 'rulership')
                        # Aspect-based determinations
                        for asp in (tgt_det.get('aspectDeterminations') or []):
                            try:
                                ah = int(asp.get('aspectedHouse'))
                            except Exception:
                                ah = None
                            if ah is None:
                                continue
                            aspect_label = str(asp.get('aspect') or '')
                            weight = 0.82
                            if 'conj' in aspect_label.lower():
                                weight = 0.9
                            for area_asp in _house_candidate_domains(ah):
                                _add_candidate(area_asp, weight, 'aspect')
                        # Scores list captured earlier
                        target_det = (r.get('determination') or {}).get('targetDetermination') or {}
                        top_list: List[Dict[str, Any]] = []
                        if isinstance(target_det.get('topAreas'), list):
                            top_list.extend(target_det.get('topAreas'))  # type: ignore[arg-type]
                        if isinstance(top_areas, list) and not top_list:
                            top_list.extend(top_areas)
                        for item in top_list:
                            if not isinstance(item, dict):
                                continue
                            area_item = item.get('area')
                            try:
                                score_item = abs(float(item.get('score') or 0.0))
                            except Exception:
                                score_item = 0.0
                            if area_item and score_item > 0.0:
                                weight = min(1.2, 0.6 + 0.4 * min(1.0, score_item))
                                _add_candidate(area_item, weight, 'score')
                        # Event domain fallback (already normalized later in pipeline)
                        ev_dom = r.get('event_domain')
                        if ev_dom:
                            _add_candidate(ev_dom, 0.65, 'event_domain')
                        if not candidates and isinstance(loc_house, int):
                            for loc_area in _house_candidate_domains(loc_house):
                                _add_candidate(loc_area, 0.5, 'location_default')
                        if candidates:
                            candidates.sort(key=lambda x: (x[1], 1 if _domain_polarity(x[0]) < 0 else 0), reverse=True)
                            preferred_area = _pick_contextual_domain(
                                [area for area, _weight, _source in candidates],
                                row=r,
                                event_type=((r.get('prediction') or {}).get('eventType')),
                            )
                            best_area, _weight, source = candidates[0]
                            if preferred_area:
                                for cand_area, cand_weight, cand_source in candidates:
                                    if cand_area == preferred_area:
                                        best_area, _weight, source = cand_area, cand_weight, cand_source
                                        break
                            target_area_source = source
                            return best_area
                    # Fallback to existing event domain if already tagged
                    ev_dom = r.get('event_domain')
                    if ev_dom:
                        target_area_source = 'event_domain'
                        return _normalize_domain(ev_dom)
                    return None

                def _contrary(area: Optional[str]) -> Optional[str]:
                    if not area:
                        return None
                    return {'life':'death','death':'life','wealth':'shared_resources','shared_resources':'wealth'}.get(area)

                def _planet_base_nature_signed(p: str) -> float:
                    m = {'Jupiter':2.0,'Venus':1.5,'Sun':0.5,'Moon':0.0,'Mercury':0.0,'Mars':-1.0,'Saturn':-2.0}
                    v = float(m.get(p, 0.0))
                    return max(-1.0, min(1.0, v / 2.0))  # normalize to [-1,1]

                def _aspect_factor(lbl: str) -> float:
                    k = (lbl or '').lower()
                    if 'conj' in k or 'opp' in k or 'square' in k:
                        return 1.0
                    if 'trine' in k or 'sext' in k:
                        return 0.8
                    if 'quin' in k or 'semi' in k:
                        return 0.6
                    return 0.7

                target_area = _target_area_from_row(row)
                target_area_for_tone = target_area
                if not target_area and row.get('event_domain'):
                    target_area_for_tone = _normalize_domain(row.get('event_domain'))  # type: ignore[arg-type]
                row['target_primary_area'] = target_area_for_tone
                if target_area_source:
                    row['target_area_source'] = target_area_source
                if row.get('target_primary_area'):
                    try:
                        target_area_for_tone = _normalize_domain(row.get('target_primary_area'))
                    except Exception:
                        target_area_for_tone = None
                # Expand matched domains with simple synonyms
                syn_map = {
                    'career': {'honors'},
                    'money': {'wealth'},
                    'relationship': {'relationships'},
                    'relationships': {'relationship'},
                    'short_travel': {'short_journeys'},
                    'short_journeys': {'short_travel'},
                    'shared': {'shared_resources'},
                    'shared_resources': {'shared'},
                    'hidden': {'secrets', 'hidden_enemies', 'prison'},
                    'secrets': {'hidden', 'hidden_enemies'},
                    'body': {'life'},
                }
                expanded = set(doms)
                for d0 in list(doms):
                    for syn in syn_map.get(d0, set()):
                        expanded.add(syn)
                det_strength = float(row.get('determination_strength') or 0.0)
                A = str(row.get('transiting') or '')
                aspect_label = str(row.get('aspect') or '')
                phase_label = str(row.get('phase') or '').lower()
                domain_norm = target_area_for_tone or row.get('target_primary_area')
                if domain_norm:
                    domain_norm = _normalize_domain(domain_norm)
                if not domain_norm:
                    for candidate in expanded:
                        cand_norm = _normalize_domain(candidate)
                        if cand_norm:
                            domain_norm = cand_norm
                            break
                domain_sign = _domain_polarity(domain_norm) if domain_norm else 0
                # Benefic mitigation (other transits, lights)
                benefic_support = False
                if multi_meta and isinstance(multi_meta, dict):
                    for p in multi_meta.get('planets', []):
                        if p != A and p in ('Jupiter', 'Venus'):
                            benefic_support = True
                            break
                if not benefic_support and mutual_meta:
                    for info in mutual_meta:
                        if str(info.get('with')) in ('Jupiter', 'Venus'):
                            benefic_support = True
                            break
                if not benefic_support and light_meta:
                    for lc in light_meta:
                        if lc.get('light') in {'Sun', 'Moon'}:
                            benefic_support = True
                            break
                malefic = A in ('Saturn', 'Mars')
                benefic = A in ('Jupiter', 'Venus')
                nature_val = _planet_base_nature_signed(A)
                det_strength_local = _safe_float(row.get('determination_strength'))
                orb_local = abs(_safe_float(row.get('orb'), 9.99))
                max_orb_local = max(0.1, _safe_float(row.get('max_orb'), 1.0))
                orb_factor = max(0.15, min(1.0, 1.0 - (orb_local / max_orb_local)))
                aspect_factor = _aspect_factor(str(row.get('aspect') or ''))

                if abs(det_strength_local) >= 0.05:
                    directional = det_strength_local
                else:
                    directional = nature_val * float(domain_sign) if domain_sign else 0.0

                domain_term = float(domain_sign) * (1.0 if benefic else (-1.0 if malefic else 0.0))
                raw_quality = (
                    (0.65 * directional)
                    + (0.25 * nature_val)
                    + (0.10 * domain_term)
                ) * 10.0 * aspect_factor * orb_factor
                quality_score_local = max(-10.0, min(10.0, raw_quality))
                pred_for_tone = row.get('prediction') or {}
                selected_event_token = ''
                if isinstance(pred_for_tone, dict):
                    selected_event_token = str(pred_for_tone.get('eventType') or '').strip().lower()
                    selected_event_token = _DOMAIN_SYNONYMS.get(selected_event_token, selected_event_token)
                adverse_tokens = _row_context_tokens(row) & _ADVERSE_STEP_HINTS
                strong_adverse_tokens = adverse_tokens & _STRONG_ADVERSE_STEP_HINTS
                hard_selected_adverse = (
                    _aspect_hard_soft(aspect_label) == 'hard'
                    and bool(selected_event_token)
                    and selected_event_token in _ADVERSE_STEP_HINTS
                )
                if hard_selected_adverse:
                    if strong_adverse_tokens or malefic or domain_sign < 0:
                        quality_score_local = min(quality_score_local, -1.0)
                    elif quality_score_local > 0.0:
                        quality_score_local = 0.0

                if quality_score_local >= 7.0:
                    quality_label_local = 'very_benefic'
                    quality_class_local = 'benefic'
                elif quality_score_local >= 2.0:
                    quality_label_local = 'moderately_benefic'
                    quality_class_local = 'benefic'
                elif quality_score_local > 0.0:
                    quality_label_local = 'benefic'
                    quality_class_local = 'benefic'
                elif quality_score_local <= -7.0:
                    quality_label_local = 'very_malefic'
                    quality_class_local = 'malefic'
                elif quality_score_local < 0.0:
                    quality_label_local = 'malefic'
                    quality_class_local = 'malefic'
                else:
                    quality_label_local = 'neutral'
                    quality_class_local = 'neutral'

                row['quality_score'] = round(float(quality_score_local), 1)
                row['quality_label'] = quality_label_local
                row['quality'] = quality_class_local
                if quality_score_local >= 1.0:
                    row['tone'] = 'positive'
                elif quality_score_local <= -1.0:
                    row['tone'] = 'negative'
                else:
                    row['tone'] = 'mixed'
                if hard_selected_adverse and row.get('tone') == 'mixed':
                    tags_local = list(row.get('prediction_tags') or [])
                    if 'mixed_outcome' not in {str(t).strip().lower() for t in tags_local}:
                        tags_local.append('mixed_outcome')
                    row['prediction_tags'] = tags_local
                row['tone_score'] = round(max(-1.0, min(1.0, quality_score_local / 10.0)), 3)
                _sync_prediction_orientation_tags(row)
            except Exception:
                row.setdefault('tone', 'mixed')
                row.setdefault('tone_score', 0.0)
                row.setdefault('quality_score', 0.0)
                row.setdefault('quality_label', 'neutral')
                row.setdefault('quality', 'neutral')
        except Exception as exc:
            logger.exception("Failed enriching Morin hit", exc_info=exc)
            continue
    if isinstance(context_out, dict):
        context_out.clear()
        context_out.update({
            'solar': sr_lr_once.get('sr_summary'),
            'lunar': sr_lr_once.get('lr_summary'),
            'solar_score': sr_lr_once.get('sr_score'),
            'lunar_score': sr_lr_once.get('lr_score'),
            'solar_domains': list(sr_lr_once.get('sr_domains') or []),
            'lunar_domains': list(sr_lr_once.get('lr_domains') or []),
            'solar_chart': sr_lr_once.get('sr_chart'),
            'lunar_chart': sr_lr_once.get('lr_chart'),
            'solar_directions': sr_lr_once.get('sr_directions') or [],
            'lunar_directions': sr_lr_once.get('lr_directions') or [],
        })
    return hits


def _prepare_natal_context(
    natal_chart_data: Dict[str, Any],
    *,
    include_cusps: bool = False,
    include_antiscia: bool = False,
    include_lots: bool = False,
    sensitive_houses: Optional[List[int]] = None,
    sensitive_planets: Optional[List[str]] = None,
    natal_include_modern: bool = False,
) -> Tuple[
    Dict[str, Tuple[float, float]],  # natal_ll
    Dict[str, Dict[str, Any]],       # target_meta
    Dict[str, Optional[int]],        # natal_house_of
    Dict[str, str],                  # house_rulers
    Dict[frozenset, str],            # natal_aspects
    Dict[str, Dict[str, float]],     # planet_domain_influence (domain->score)
]:
    """Build and return reusable natal context structures for repeated transit scans.

    This avoids recomputing target longitudes and metadata for each scan step.
    """
    natal_idx = _normalize_planets(natal_chart_data)
    cusps = _extract_cusps(natal_chart_data or {})
    natal_ll: Dict[str, Tuple[float, float]] = {}
    target_meta: Dict[str, Dict[str, Any]] = {}

    # Select natal planets
    natal_names_base = list(CLASSICAL) + (["Uranus", "Neptune", "Pluto"] if natal_include_modern else [])
    if sensitive_planets is not None:
        natal_names = [p for p in natal_names_base if p in (sensitive_planets or [])]
    else:
        natal_names = list(natal_names_base)

    for nm in natal_names:
        row = natal_idx.get(nm)
        if isinstance(row, dict):
            try:
                lon = float(row.get('longitude'))
                lat = float((row.get('latitude', 0.0) or 0.0))
                label = nm
                natal_ll[label] = (_norm360(lon), float(lat))
                target_meta[label] = {'target_type': 'planet', 'natal_house': int(row.get('house')) if row.get('house') is not None else None}
            except Exception:
                continue

    # Angles always included: C1 (Asc) and C10 (MC)
    try:
        angles = [('Asc', cusps[0]), ('MC', cusps[9])]
    except Exception:
        angles = [('Asc', 0.0), ('MC', 0.0)]
    for label, lon in angles:
        try:
            natal_ll[label] = (_norm360(float(lon)), 0.0)
            target_meta[label] = {'target_type': 'cusp', 'natal_house': 1 if label == 'Asc' else 10}
        except Exception:
            continue

    # Full cusps if requested (or when specific houses selected)
    houses_to_include: List[int] = []
    try:
        if sensitive_houses:
            houses_to_include = [int(h) for h in sensitive_houses if 1 <= int(h) <= 12]
        elif include_cusps:
            houses_to_include = list(range(1,13))
    except Exception:
        houses_to_include = list(range(1,13)) if include_cusps else []
    # When including cusps, avoid duplicating angles already present as Asc/MC.
    # Always skip C1 (Asc is canonical). For C10, keep only when it differs from MC by a meaningful margin.
    try:
        mc_lon = float(cusps[9]) if len(cusps) >= 10 else None
    except Exception:
        mc_lon = None
    for i, lon in enumerate(cusps):
        hnum = i + 1
        if hnum not in houses_to_include:
            continue
        # Skip C1 because Asc is already included at the same longitude
        if hnum == 1:
            continue
        # Skip C10 if it is essentially the same as MC (within 0.05°)
        if hnum == 10 and mc_lon is not None:
            try:
                cand = _norm360(float(lon))
                mc = _norm360(float(mc_lon))
                d = abs((cand - mc + 540.0) % 360.0 - 180.0)
                if d <= 0.05:
                    continue
            except Exception:
                pass
        lab = f'C{hnum}'
        try:
            natal_ll[lab] = (_norm360(float(lon)), 0.0)
            target_meta[lab] = {'target_type': 'cusp', 'natal_house': hnum}
        except Exception:
            continue

    # Part of Fortune if present and requested
    if include_lots:
        pof = _extract_pof(natal_chart_data or {})
        if pof is not None:
            natal_ll['POF'] = (_norm360(float(pof)), 0.0)
            try:
                target_meta['POF'] = {'target_type': 'lot', 'natal_house': _house_from_cusps(pof, cusps)}
            except Exception:
                target_meta['POF'] = {'target_type': 'lot', 'natal_house': None}

    # Antiscia and contra-antiscia for all natal targets if requested
    if include_antiscia:
        add: Dict[str, Tuple[float, float]] = {}
        add_meta: Dict[str, Dict[str, Any]] = {}
        for lab, (lon, _lat) in list(natal_ll.items()):
            anti_lon = _antiscia_lon(lon)
            alabel = f"{lab} (antiscia)"
            add[alabel] = (anti_lon, 0.0)
            m = dict(target_meta.get(lab, {}))
            m['target_type'] = 'antiscia'
            add_meta[alabel] = m
            # Contra-antiscia
            try:
                contra_lon = _contra_antiscia_lon(lon)
                clabel = f"{lab} (contra-antiscia)"
                add[clabel] = (contra_lon, 0.0)
                m2 = dict(target_meta.get(lab, {}))
                m2['target_type'] = 'contra_antiscia'
                add_meta[clabel] = m2
            except Exception:
                pass
        natal_ll.update(add)
        target_meta.update(add_meta)

    natal_house_of = _natal_house_map(natal_chart_data or {})
    house_rulers = _house_rulers_map(natal_chart_data or {})
    natal_aspects = _natal_aspect_map(natal_chart_data or {})

    # Build planet-domain influence map from trait-like house influence analysis
    # Shape: { planet: { 'scores': {domain:score}, 'evidence': {domain: [evidence...] } } }
    planet_domain_infl: Dict[str, Dict[str, Any]] = {}
    try:
        # Compute metrics (timestamp not critical for classical planets; use a fixed ISO)
        ts_iso = '2000-01-01T00:00:00+00:00'
        metrics = compute_metrics(natal_chart_data or {}, ts_iso, special_degrees=[])
        h_infl = compute_house_influences(natal_chart_data or {}, metrics)
        houses = (h_infl or {}).get('houses') or []
        # Aggregate per planet per domain scores using the provided values
        # Aggregate per-planet domain scores
        for hrow in houses:
            try:
                hnum = int(hrow.get('house'))
            except Exception:
                continue
            dom_label = _house_domain(hnum)
            if not dom_label:
                continue
            for inf in (hrow.get('influences') or []):
                try:
                    p = str(inf.get('planet'))
                    if not p:
                        continue
                    val = float(inf.get('value') or 0.0)
                    if val == 0.0:
                        continue
                    # init container
                    if p not in planet_domain_infl:
                        planet_domain_infl[p] = {'scores': {}, 'evidence': {}}
                    # scores
                    scores_map = planet_domain_infl[p]['scores']
                    scores_map[dom_label] = scores_map.get(dom_label, 0.0) + val
                    # evidence capture (keep raw value before normalization)
                    ev_map = planet_domain_infl[p]['evidence']
                    ev_list = ev_map.setdefault(dom_label, [])
                    etype = str(inf.get('type'))
                    ev: Dict[str, Any] = {'type': etype, 'house': hnum, 'value': float(val)}
                    if etype == 'aspect':
                        try:
                            ev['aspect'] = str(inf.get('aspect') or '')
                            ev['orb'] = float(inf.get('orb') or 0.0)
                            ev['phase'] = str(inf.get('phase') or '')
                            ev['dexter'] = bool(inf.get('dexter'))
                        except Exception:
                            pass
                    elif etype == 'co_rulership':
                        ev['co_kind'] = str(inf.get('co_kind') or '')
                    ev_list.append(ev)
                except Exception:
                    continue
        # Optional: normalize by max per planet for consistency (scores)
        for p, cont in list(planet_domain_infl.items()):
            try:
                m = cont.get('scores') or {}
                mx = max(abs(v) for v in m.values()) if m else 0.0
                if mx > 0:
                    for k in list(m.keys()):
                        m[k] = float(round(m[k] / mx, 4))
                # evidence normalization per planet
                ev_all = []
                for lst in (cont.get('evidence') or {}).values():
                    ev_all.extend(lst)
                ev_max = max((abs(float(e.get('value') or 0.0)) for e in ev_all), default=0.0)
                if ev_max > 0:
                    for lst in (cont.get('evidence') or {}).values():
                        for e in lst:
                            try:
                                e['value_norm'] = float(round(float(e.get('value') or 0.0)/ev_max, 4))
                            except Exception:
                                e['value_norm'] = 0.0
            except Exception:
                pass
    except Exception:
        planet_domain_infl = {}

    return natal_ll, target_meta, natal_house_of, house_rulers, natal_aspects, planet_domain_infl


def _compute_hits_with_ctx(
    ctx: Tuple[
        Dict[str, Tuple[float, float]],
        Dict[str, Dict[str, Any]],
        Dict[str, Optional[int]],
        Dict[str, str],
        Dict[frozenset, str],
        Dict[str, Dict[str, float]],
    ],
    transit_timestamp_iso: str,
    *,
    dt_hours: float = 0.5,
    planet_names: Optional[List[str]] = None,
    include_modern: bool = False,
    natal_include_modern: bool = False,
    focus_houses: Optional[List[int]] = None,
    focus_planets: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Compute Morin transits using a pre-built natal context tuple.

    The tuple can be obtained from _prepare_natal_context(). This function is
    intentionally internal to keep the public API stable while enabling window
    scans to avoid redundant natal preprocessing in tight loops.
    """
    try:
        jd0 = _jd_from_iso(transit_timestamp_iso)
    except Exception:
        return []
    dt_days = float(dt_hours) / 24.0

    # Transiting set
    names = planet_names or (list(CLASSICAL) + (["Uranus", "Neptune", "Pluto"] if include_modern else []))
    if not include_modern:
        names = [n for n in names if n in CLASSICAL]

    now_ll: Dict[str, Tuple[float, float]] = {}
    fut_ll: Dict[str, Tuple[float, float]] = {}
    fut2_ll: Dict[str, Tuple[float, float]] = {}
    for nm in names:
        now_ll[nm] = _lon_lat_at(jd0, nm)
        fut_ll[nm] = _lon_lat_at(jd0 + dt_days, nm)
        fut2_ll[nm] = _lon_lat_at(jd0 + 2*dt_days, nm)

    # Unpack natal context (6-tuple from _prepare_natal_context)
    (natal_ll, target_meta, natal_house_of, house_rulers, natal_aspects, planet_domain_infl) = ctx
    asc_ruler_name = ''
    try:
        asc_ruler_name = str(house_rulers.get('1') or house_rulers.get(1) or '')
    except Exception:
        asc_ruler_name = ''
    # Step-level special flags
    def _absdiff_deg(a: float, b: float) -> float:
        return abs((((a - b) + 180.0) % 360.0) - 180.0)
    lethal_new_moon = False
    lethal_full_moon = False
    asc8_conj = False
    try:
        if 'Sun' in now_ll and 'Moon' in now_ll:
            lonS = now_ll['Sun'][0]; lonM = now_ll['Moon'][0]
            nm_sep = _absdiff_deg(lonS, lonM)
            if nm_sep <= 1.0:
                for mal in ('Mars','Saturn'):
                    if mal in natal_ll:
                        mlon = natal_ll[mal][0]
                        if min(_absdiff_deg(lonS, mlon), _absdiff_deg((lonS+180.0)%360.0, mlon)) <= 1.0:
                            lethal_new_moon = True
                            break
            # near Full Moon
            fm_sep = abs(nm_sep - 180.0)
            if fm_sep <= 1.0:
                for mal in ('Mars','Saturn'):
                    if mal in natal_ll:
                        mlon = natal_ll[mal][0]
                        if min(_absdiff_deg(lonS, mlon), _absdiff_deg(lonM, mlon)) <= 1.0:
                            lethal_full_moon = True
                            break
        asc_r = str(house_rulers.get('1') or house_rulers.get(1) or '')
        h8_r = str(house_rulers.get('8') or house_rulers.get(8) or '')
        if asc_r and h8_r and asc_r in now_ll and h8_r in now_ll:
            if _absdiff_deg(now_ll[asc_r][0], now_ll[h8_r][0]) <= 1.0:
                asc8_conj = True
    except Exception:
        lethal_new_moon = False; lethal_full_moon = False; asc8_conj = False
    # Build dependent planet conditions (Sun/Moon/Mercury) from transit positions
    def _sign_from_lon(lon: float) -> str:
        names = [
            'Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
        d = lon % 360.0; return names[int(d // 30) % 12]

    def _cond_dep(now_ll, fut_ll) -> Dict[str, float]:
        cond: Dict[str, float] = {}
        try:
            lonS = now_ll.get('Sun', (None,None))[0]
        except Exception:
            lonS = None
        for nm in ('Sun','Moon','Mercury'):
            try:
                lon = now_ll[nm][0]
            except Exception:
                continue
            val = 0.0
            sign = _sign_from_lon(lon)
            if nm == 'Sun':
                if sign == 'Aries': val += 0.3
                if sign == 'Leo': val += 0.2
                if sign == 'Libra': val -= 0.3
                if sign == 'Aquarius': val -= 0.2
            elif nm == 'Moon':
                if sign == 'Taurus': val += 0.3
                if sign == 'Cancer': val += 0.2
                if sign == 'Scorpio': val -= 0.3
                if sign == 'Capricorn': val -= 0.2
            elif nm == 'Mercury':
                if sign in ('Gemini','Virgo'): val += 0.2
                if sign in ('Sagittarius','Pisces'): val -= 0.2
                if sign == 'Virgo': val += 0.3
                if sign == 'Pisces': val -= 0.3
            if lonS is not None and nm in ('Moon','Mercury'):
                sep = abs((((lon - lonS) + 180.0) % 360.0) - 180.0)
                if sep <= 0.25:
                    val += 0.5
                elif sep <= 8.0:
                    val -= 0.5
                elif sep <= 17.0:
                    val -= 0.2
            if nm == 'Mercury':
                try:
                    lonAf = fut_ll[nm][0]
                    dlon = ((lonAf - lon + 540.0) % 360.0) - 180.0
                    if dlon < 0: val -= 0.5
                except Exception:
                    pass
            cond[nm] = max(-1.0, min(1.0, val))
        return cond

    dep_conditions = _cond_dep(now_ll, fut_ll)

    out: List[Dict[str, Any]] = []
    for A in names:
        if A not in now_ll:
            continue
        lonA, latA = now_ll[A]
        lonAf, latAf = fut_ll[A]
        rA = _unit(_sph_to_vec(lonA, latA))
        inclA = _apparent_inclination(A, latA)
        nA = _build_plane_normal(rA, latA, latAf, inclA)
        for B, (lonB, _latB) in natal_ll.items():
            rB = _unit(_sph_to_vec(lonB, 0.0)) if target_meta.get(B, {}).get('target_type') != 'planet' else _unit(_sph_to_vec(lonB, natal_ll[B][1]))
            for ang, label in ASPECT_SET:
                r_pos = _unit(_rotate(rA, nA, +ang))
                r_neg = _unit(_rotate(rA, nA, -ang))
                sep_pos = _angular_sep_deg(r_pos, rB)
                sep_neg = _angular_sep_deg(r_neg, rB)
                if sep_pos <= sep_neg:
                    sep = sep_pos
                    branch = +1
                else:
                    sep = sep_neg
                    branch = -1

                # Orbs-of-virtue gate (A + B)
                tmeta = target_meta.get(B, {})
                ttype = tmeta.get('target_type', 'planet')
                def _orb_for(name: str, allow_modern: bool) -> float:
                    return float(ORB_OF_VIRTUE.get(name, 2.0 if allow_modern else 0.0))
                orbA = _orb_for(A, include_modern)
                if ttype == 'planet':
                    orbB = _orb_for(B, natal_include_modern)
                    moietyA = orbA / 2.0
                    moietyB = orbB / 2.0
                    combined = moietyA + moietyB
                else:
                    orbB = 0.0
                    moietyA = orbA / 2.0
                    moietyB = 0.0
                    combined = moietyA
                if sep > combined:
                    continue
                # Tight cap for (contra-)antiscia targets
                try:
                    if ttype in ('antiscia','contra_antiscia') and sep > 3.0:
                        continue
                except Exception:
                    pass
                # Aspect-specific cap: Semi-sextile / Quincunx scored only when orb ≤ 3°
                try:
                    lbl_low = (label or '').strip().lower()
                    if ('semi' in lbl_low or 'quin' in lbl_low) and (sep > 3.0):
                        continue
                except Exception:
                    pass

                # Match the public one-degree partile definition while retaining
                # physical disc contact as a distinct calculation detail.
                sd_sum = _semi_diameter_deg(A, jd0)
                if ttype == 'planet':
                    sd_sum += _semi_diameter_deg(B, jd0)
                partile = _is_partile_orb(sep)
                bodily_contact = sep <= sd_sum
                complete_platic = (sep <= (min(moietyA, moietyB) if ttype == 'planet' else moietyA))

                # Phase via forward step for A (B fixed)
                lonA2, latA2 = fut_ll[A]
                _lonA3, latA3 = fut2_ll.get(A, (lonA2, latA2))
                rA2 = _unit(_sph_to_vec(lonA2, latA2))
                nA2 = _build_plane_normal(rA2, latA2, latA3, inclA)
                r_branch_future = _unit(_rotate(rA2, nA2, +ang if branch > 0 else -ang))
                sep_future = _angular_sep_deg(r_branch_future, rB)
                if sep_future < sep - 1e-6:
                    phase = 'applying'
                elif sep_future > sep + 1e-6:
                    phase = 'separating'
                else:
                    phase = 'stationary'

                natal_house = tmeta.get('natal_house')
                row = {
                    'transiting': A,
                    'natal': B,
                    'aspect': label,
                    'orb': round(float(sep), 4),
                    'max_orb': round(float(combined), 4),
                    'partile': bool(partile),
                    'bodily_contact': bool(bodily_contact),
                    'complete_platic': bool(complete_platic),
                    'direction': _dexter_sinister(lonA, lonB),
                    'phase': phase,
                    'is_malefic': True if A in ('Mars','Saturn') else False,
                    'is_benefic': True if A in ('Jupiter','Venus') else False,
                    'is_luminary': True if A in ('Sun','Moon') else False,
                    'target_type': ttype,
                    'target_label': B,
                    'natal_house': natal_house,
                }
                # Quality & effective window
                try:
                    row['quality'] = _classify_quality(A, label)
                except Exception:
                    row['quality'] = 'mixed'
                try:
                    row['effectiveWindow'] = _estimate_effective_window(
                        transit_timestamp_iso,
                        float(sep),
                        float(sep_future),
                        float(dt_days),
                        float(combined),
                        A,
                    ) or None
                except Exception:
                    row['effectiveWindow'] = None
                # Attach special rule flags for scoring adjustments
                try:
                    if lethal_new_moon or lethal_full_moon or asc8_conj:
                        row['special_flags'] = {
                            'lethal_new_moon': bool(lethal_new_moon),
                            'lethal_full_moon': bool(lethal_full_moon),
                            'asc8_conj': bool(asc8_conj),
                        }
                except Exception:
                    pass
                try:
                    score, breakdown = _score_hit(row, natal_house_of, house_rulers, focus_houses, focus_planets, dep_conditions)
                    row['score'] = score
                    row['score_breakdown'] = breakdown
                except Exception:
                    pass

                # Keywords (same logic as compute_morin_transits_to_natal)
                try:
                    kw: List[str] = []
                    try:
                        hs_kind2 = _aspect_hard_soft(label)
                        near_exact2 = (float(sep) <= 1.0) or bool(partile)
                        if A in ('Mars', 'Saturn'):
                            if (hs_kind2 == 'hard' or (hs_kind2 == 'conj' and near_exact2)) and (
                                B in ('Asc',) or (isinstance(natal_house, int) and natal_house in (1, 6))
                            ):
                                kw.append('Injury risk')
                            if (hs_kind2 == 'hard' or (hs_kind2 == 'conj' and near_exact2)) and (
                                B in ('MC','C10') or (isinstance(natal_house, int) and natal_house == 10)
                            ):
                                kw.append('Career strain')
                        if lethal_new_moon and A in ('Sun','Moon'):
                            kw.append('Injury risk')
                        if asc8_conj:
                            try:
                                asc_r = str(house_rulers.get('1') or house_rulers.get(1) or '')
                                h8_r = str(house_rulers.get('8') or house_rulers.get(8) or '')
                                if A in (asc_r, h8_r):
                                    kw.append('Injury risk')
                            except Exception:
                                pass
                        if A in ('Mars','Saturn') and hs_kind2 == 'hard' and (isinstance(natal_house, int) and natal_house in (8,12)):
                            kw.append('Injury risk')
                    except Exception:
                        pass
                    if A in ('Saturn','Mars'): kw.append('Malefic')
                    if A in ('Jupiter','Venus'): kw.append('Benefic')
                    hs = _aspect_hard_soft(label)
                    if hs == 'hard': kw.append('Hard')
                    elif hs == 'soft': kw.append('Soft')
                    if float(sep) <= 0.25:
                        kw.append('Exact')
                    elif partile:
                        kw.append('Partile')
                    elif complete_platic:
                        kw.append('Platic')
                    if phase == 'applying': kw.append('Applying')
                    elif phase == 'separating': kw.append('Separating')
                    # Domain via trait-like influence (fallback to natal location)
                    h = int(natal_house) if isinstance(natal_house, int) else None
                    dom_added = False
                    if ttype == 'planet':
                        try:
                            cont = planet_domain_infl.get(B, {}) if isinstance(planet_domain_infl, dict) else {}
                            scores2 = cont.get('scores') if isinstance(cont, dict) else cont
                            if scores2 and isinstance(scores2, dict):
                                top_dom2 = max(scores2.items(), key=lambda x: x[1])[0]
                                if top_dom2:
                                    kw.append(top_dom2)
                                    dom_added = True
                                    # Evidence tags (up to 2)
                                    try:
                                        ev_map2 = cont.get('evidence') if isinstance(cont, dict) else {}
                                        evs2 = list(ev_map2.get(top_dom2, [])) if isinstance(ev_map2, dict) else []
                                        evs2.sort(key=lambda e: (-float(e.get('value_norm') or e.get('value') or 0.0), str(e.get('type'))))
                                        added2 = 0
                                        for e in evs2:
                                            if added2 >= 2:
                                                break
                                            et = str(e.get('type'))
                                            if et == 'occupation':
                                                htag = f"Loc(H{int(e.get('house'))})" if e.get('house') else None
                                                if htag and htag not in kw:
                                                    kw.append(htag); added2 += 1
                                            elif et == 'rulership':
                                                htag = f"Ruler(H{int(e.get('house'))})" if e.get('house') else None
                                                if htag and htag not in kw:
                                                    kw.append(htag); added2 += 1
                                            elif et == 'aspect':
                                                try:
                                                    hnum = int(e.get('house')) if e.get('house') is not None else None
                                                    an = _aspect_short(str(e.get('aspect') or ''))
                                                    ob = float(e.get('orb') or 0.0)
                                                    ph = str(e.get('phase') or '')
                                                    phs = 'app' if ph == 'applying' else ('sep' if ph == 'separating' else '')
                                                    if hnum and an:
                                                        lab = f"C{hnum} {an} {round(ob,1)}° {phs}".strip()
                                                        if lab and lab not in kw:
                                                            kw.append(lab); added2 += 1
                                                except Exception:
                                                    pass
                                            elif et == 'co_rulership':
                                                ck = str(e.get('co_kind') or '')
                                                tag = 'Exalt' if ck.startswith('exalt') else ('Triplicity' if ck.startswith('triplicity') else None)
                                                if tag and tag not in kw:
                                                    kw.append(tag); added2 += 1
                                        # Domain synonyms (one)
                                        try:
                                            syn = {
                                                'Belief': ['Study','Journey'],
                                                'Shared': ['Debts','Taxes'],
                                                'Body': ['Self','Vitality'],
                                                'Money': ['Resources','Income'],
                                            }.get(top_dom2, [])
                                            if syn:
                                                s = syn[0]
                                                if s not in kw:
                                                    kw.append(s)
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                        except Exception:
                            dom_added = False
                    if not dom_added:
                        dom = _house_domain(h)
                        if dom: kw.append(dom)
                    # (Removed) added positive cues tied to domain and soft aspects
                    if ttype == 'planet':
                        try:
                            added = 0
                            for hk in range(1, 13):
                                rv = (house_rulers or {}).get(str(hk))
                                if str(rv) == str(B):
                                    dlab = _house_domain(hk)
                                    if hk in (1, 10):
                                        kw.append(f'Ruler(H{hk})')
                                    elif dlab:
                                        kw.append(f'Ruler({dlab})')
                                    else:
                                        kw.append(f'Ruler(H{hk})')
                                    added += 1
                                    if added >= 2:
                                        break
                        except Exception:
                            pass
                        # (Removed) Core planet cue tied to natal significance
                    base_label2 = B
                    try:
                        if ttype in ('antiscia','contra_antiscia') and isinstance(B, str):
                            if B.endswith(' (antiscia)'):
                                base_label2 = B.replace(' (antiscia)', '')
                            elif B.endswith(' (contra-antiscia)'):
                                base_label2 = B.replace(' (contra-antiscia)', '')
                    except Exception:
                        base_label2 = B
                    if base_label2 in ('Asc','MC'):
                        kw.append(base_label2)
                    elif (isinstance(base_label2, str) and base_label2.startswith('C') and base_label2[1:].isdigit()):
                        kw.append(base_label2)
                    elif ttype == 'cusp' and isinstance(natal_house, int):
                        kw.append(f'C{natal_house}')
                    elif ttype == 'lot' and base_label2 == 'POF':
                        kw.append('POF')
                    if ttype == 'antiscia':
                        kw.append('Antiscia')
                    elif ttype == 'contra_antiscia':
                        kw.append('Contra-antiscia')
                    if h is not None:
                        kw.append(f'Natal(H{h})')
                    asp_s = _aspect_short(label)
                    if asp_s: kw.append(asp_s)
                    try:
                        if str(row.get('direction')) == 'dexter':
                            kw.append('Dexter')
                        elif str(row.get('direction')) == 'sinister':
                            kw.append('Sinister')
                    except Exception:
                        pass
                    try:
                        dlon = ((fut_ll[A][0] - lonA + 540.0) % 360.0) - 180.0
                        if dlon < 0:
                            kw.append('Rx')
                    except Exception:
                        pass
                    try:
                        if ttype == 'planet':
                            nat_asp = natal_aspects.get(frozenset({A, B}))
                            if nat_asp:
                                nat_kind = _aspect_hard_soft(nat_asp)
                                tr_kind = _aspect_hard_soft(label)
                                if (nat_asp or '').lower().startswith((label or '').lower()[:3]):
                                    kw.append('Natal echo')
                                elif nat_kind == 'hard' and tr_kind == 'soft':
                                    kw.append('Hard→Soft')
                                elif nat_kind == 'soft' and tr_kind == 'hard':
                                    kw.append('Soft→Hard')
                    except Exception:
                        pass
                    in_focus = False
                    try:
                        if focus_houses and isinstance(natal_house, int) and int(natal_house) in set(int(x) for x in focus_houses):
                            in_focus = True
                    except Exception:
                        pass
                    try:
                        if focus_planets and (B in focus_planets or A in focus_planets):
                            in_focus = True
                    except Exception:
                        pass
                    if in_focus:
                        kw.append('Focus')
                    # Semantic cues (marriage/public/celebration)
                    try:
                        has_rel = 'Relationship' in kw
                        hs_kind = _aspect_hard_soft(label)
                        softish = (hs_kind == 'soft') or (label == 'Conjunction') or ('Exact' in kw) or ('Partile' in kw)
                        if has_rel and softish and (A in ('Venus','Jupiter') or B in ('Venus','Jupiter')):
                            kw.append('marriage')
                        if (('MC' in kw) or ('C10' in kw) or ('Career' in kw)) and softish and (A in ('Venus','Jupiter','Sun') or B in ('Venus','Jupiter','Sun')):
                            kw.append('Public')
                        if ('Benefic' in kw and 'Soft' in kw) and (has_rel or ('Friends' in kw) or ('Home' in kw)):
                            kw.append('Celebration')
                        has_children = ('Children' in kw)
                        asc_ruler_hit = bool(asc_ruler_name and A == asc_ruler_name)
                        birth_child_planets = {'Jupiter','Venus','Moon','Sun'}
                        if has_children and softish and ((A in birth_child_planets) or asc_ruler_hit):
                            kw.append('pregnancy')
                            kw.append('birth_of_child')
                        try:
                            orb_tight = abs(float(sep)) <= 1.0
                        except Exception:
                            orb_tight = False
                        has_life_kw = ('Body' in kw) or ('Asc' in kw) or ('C1' in kw) or (isinstance(natal_house, int) and natal_house == 1)
                        has_home_kw = ('Home' in kw) or ('C4' in kw) or (isinstance(natal_house, int) and natal_house == 4)
                        if softish and orb_tight and ((A in birth_child_planets) or asc_ruler_hit) and has_children and (has_life_kw or has_home_kw):
                            kw.append('birth_self')
                    except Exception:
                        pass
                    seen: Set[str] = set()
                    row['keywords'] = [t for t in kw if t and not (t in seen or seen.add(t))]
                except Exception:
                    row['keywords'] = []
                out.append(row)

    out.sort(key=lambda r: (-float(r.get('score') or 0.0), abs(float(r.get('orb', 999.0)))))
    return out
