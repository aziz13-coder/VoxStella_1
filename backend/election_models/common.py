from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Stable, model-agnostic constants
FIXED_SIGNS = {"Taurus", "Leo", "Scorpio", "Aquarius"}
CARDINAL_SIGNS = {"Aries", "Cancer", "Libra", "Capricorn"}
MUTABLE_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}

BENEFICS = {"Jupiter", "Venus"}
MALEFICS = {"Mars", "Saturn"}

ANGULAR_HOUSES = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}
CADENT_HOUSES = {3, 6, 9, 12}

TRAD_RULER = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Optional adapters used by some models
try:
    from house_influence import EXALTATION as HI_EXALTATION, TRIPLICITY as HI_TRIPLICITY
    from house_influence import _element_of_sign as _hi_element
except Exception:
    HI_EXALTATION = {}
    HI_TRIPLICITY = {}

    def _hi_element(sign: str) -> str:  # type: ignore
        s = (sign or '').strip().lower()
        if s in ('aries', 'leo', 'sagittarius'):
            return 'Fire'
        if s in ('taurus', 'virgo', 'capricorn'):
            return 'Earth'
        if s in ('gemini', 'libra', 'aquarius'):
            return 'Air'
        return 'Water'

try:
    from sect import compute_sect_info
except Exception:
    compute_sect_info = None  # type: ignore

try:
    from morin_aspects import compute_morin_combustion
except Exception:
    compute_morin_combustion = None  # type: ignore

_DEGREE_TOKEN_RE = re.compile(r'[+\-]?\d+(?:\.\d+)?')


def _safe_float(value: Any) -> Optional[float]:
    """Best-effort conversion of numeric and formatted longitude inputs."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace('−', '-').replace('–', '-').replace('—', '-')
        try:
            result = float(text)
            return result if math.isfinite(result) else None
        except ValueError:
            cleaned = text
            for ch in ('°', 'º', '˚', '’', '′', "'", '″', '‴', '“', '”', ':'):
                cleaned = cleaned.replace(ch, ' ')
            tokens = [tok for tok in _DEGREE_TOKEN_RE.findall(cleaned)]
            if not tokens:
                return None
            try:
                degrees = float(tokens[0])
            except Exception:
                return None
            minutes = float(tokens[1]) if len(tokens) > 1 else 0.0
            seconds = float(tokens[2]) if len(tokens) > 2 else 0.0
            sign = -1.0 if degrees < 0 else 1.0
            total = abs(degrees) + minutes / 60.0 + seconds / 3600.0
            total = sign * total
            return total if math.isfinite(total) else None
    return None


def _sign_from_lon(lon: float) -> str:
    names = [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    ]
    try:
        i = int((float(lon) % 360.0) // 30)
        return names[i]
    except Exception:
        return "Aries"


def _collect_planets(cd: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    pls = cd.get("planets")
    if isinstance(pls, list):
        for p in pls:
            if isinstance(p, dict) and p.get("planet"):
                out[str(p["planet"])] = p
    elif isinstance(pls, dict):
        for nm, info in pls.items():
            if isinstance(info, dict):
                row = dict(info)
                row.setdefault("planet", nm)
                out[str(nm)] = row
    return out


def _house_cusps(cd: Dict[str, Any]) -> List[float]:
    for key in ("house_cusps", "houses"):
        v = cd.get(key)
        if isinstance(v, list) and len(v) >= 12:
            return [float(x) for x in v[:12]]
    return []


def _get_aspects_list(cd: Dict[str, Any]):
    try:
        for key in ('planetary_aspects_precise', 'planetary_aspects', 'aspects'):
            v = cd.get(key)
            if isinstance(v, list):
                return v
    except Exception:
        return None
    return None


def _house_from_lon(lon: float, cusps: List[float]) -> Optional[int]:
    try:
        if not cusps or len(cusps) < 12:
            return None
        L = (float(lon) % 360.0)
        for i in range(12):
            a = float(cusps[i] % 360.0)
            b = float(cusps[(i + 1) % 12] % 360.0)
            if i == 11:
                if (L >= a) or (L < b):
                    return 12
            else:
                if a <= b:
                    if a <= L < b:
                        return i + 1
                else:
                    if L >= a or L < b:
                        return i + 1
        return None
    except Exception:
        return None


def _ang_sep(a: float, b: float) -> float:
    try:
        return abs((((float(a) - float(b)) + 180.0) % 360.0) - 180.0)
    except Exception:
        return 999.0

def _is_via_combusta(lon: Optional[float]) -> bool:
    """Return True if longitude lies within Via Combusta (15° Libra–15° Scorpio).

    Range in ecliptic degrees: [195°, 225°).
    """
    try:
        if lon is None:
            return False
        L = float(lon) % 360.0
        return 195.0 <= L < 225.0
    except Exception:
        return False


def _ordinal(n: Optional[int]) -> str:
    try:
        n = int(n) if n is not None else 0
    except Exception:
        n = 0
    if n % 100 in (11, 12, 13):
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def _is_waxing(moon_lon: float, sun_lon: float) -> Optional[bool]:
    """Return True when the Moon is ahead of the Sun (increasing in light)."""
    try:
        moon = float(moon_lon) % 360.0
        sun = float(sun_lon) % 360.0
    except Exception:
        return None
    if not math.isfinite(moon) or not math.isfinite(sun):
        return None
    delta = (moon - sun) % 360.0  # 0..360, waxing when Moon leads the Sun
    if math.isclose(delta, 180.0, abs_tol=1e-6):
        return False
    return delta < 180.0 or math.isclose(delta, 0.0, abs_tol=1e-6)


@dataclass
class Score:
    value: float
    tags: List[str]
    pros: Optional[List[str]] = None
    cautions: Optional[List[str]] = None
    lines: Optional[List[Dict[str, Any]]] = None

__all__ = [
    'FIXED_SIGNS', 'CARDINAL_SIGNS', 'MUTABLE_SIGNS',
    'BENEFICS', 'MALEFICS',
    'ANGULAR_HOUSES', 'SUCCEDENT_HOUSES', 'CADENT_HOUSES',
    'TRAD_RULER',
    'HI_EXALTATION', 'HI_TRIPLICITY', '_hi_element',
    'compute_sect_info', 'compute_morin_combustion',
    '_safe_float',
    '_sign_from_lon', '_collect_planets', '_house_cusps', '_get_aspects_list', '_house_from_lon', '_ang_sep', '_ordinal', '_is_waxing', '_is_via_combusta',
    'Score',
]
