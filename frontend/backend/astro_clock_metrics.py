# -*- coding: utf-8 -*-
"""
Astro Clock Metrics — engine-agnostic enrichments used by the dashboard.

Adds:
- Angle aspects (ASC/DSC/MC/IC), with orbs and bonuses per user policy
- Minor aspects (quincunx 150°, semisquare 45°, sesquiquadrate 135°)
- Affliction classification with severity tiers and escalators
- Element/modality/sign emphasis and angularity awareness
- House emphasis and coarse house-affliction flags
- Modern planets are always included for metrics (Uranus/Neptune/Pluto)
- Degree hits against supplied special degrees, midpoint activation, stacking

This module consumes serialized chart_data from the horary engine and does not
import the engine itself. It reuses modern helpers to compute modern planets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional, Iterable
import math
import re

from modern_planets import compute_modern_planets


# ------------------------
# Utilities
# ------------------------

def _norm180(x: float) -> float:
    return ((x + 180.0) % 360.0) - 180.0


def _norm360(x: float) -> float:
    return x % 360.0


def _absdiff_deg(a: float, b: float) -> float:
    return abs(_norm180(a - b))


def _sign_name_from_lon(lon: float) -> str:
    d = _norm360(lon)
    names = [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    return names[int(d // 30) % 12]


def _element_of_sign(sign: str) -> str:
    s = sign.strip().lower()
    if s in ("aries", "leo", "sagittarius"): return "Fire"
    if s in ("taurus", "virgo", "capricorn"): return "Earth"
    if s in ("gemini", "libra", "aquarius"): return "Air"
    return "Water"  # cancer, scorpio, pisces


def _modality_of_sign(sign: str) -> str:
    s = sign.strip().lower()
    if s in ("aries", "cancer", "libra", "capricorn"): return "Cardinal"
    if s in ("taurus", "leo", "scorpio", "aquarius"): return "Fixed"
    return "Mutable"


def _planet_list(chart_data: Dict[str, Any], timestamp_iso: Optional[str]) -> List[Dict[str, Any]]:
    """Return a normalized list of planet dicts, always including modern planets for metrics."""
    planets = chart_data.get("planets") or []
    out: List[Dict[str, Any]] = []
    if isinstance(planets, dict):
        for name, info in planets.items():
            if isinstance(info, dict):
                p = dict(info)
                p.setdefault("planet", name)
                out.append(p)
    elif isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict):
                out.append(p)

    # Always append modern planets (Uranus/Neptune/Pluto) for metrics
    try:
        modern = compute_modern_planets(chart_data, timestamp_iso or "")
    except Exception:
        modern = []
    # Avoid duplicate entries
    present = {str(p.get("planet")) for p in out}
    for mp in modern:
        if str(mp.get("planet")) not in present:
            out.append(mp)
    return out


def _angles_from_chart(chart_data: Dict[str, Any]) -> Dict[str, float]:
    asc = None
    mc = None
    try:
        asc = float(chart_data.get("ascendant")) if chart_data.get("ascendant") is not None else None
    except Exception:
        asc = None
    try:
        mc = float(chart_data.get("midheaven")) if chart_data.get("midheaven") is not None else None
    except Exception:
        mc = None

    if asc is None:
        # fall back to house cusp 1 if available
        cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
        if isinstance(cusps, list) and len(cusps) >= 1:
            try:
                asc = float(cusps[0])
            except Exception:
                asc = 0.0
    if mc is None:
        cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
        if isinstance(cusps, list) and len(cusps) >= 10:
            try:
                mc = float(cusps[9])
            except Exception:
                mc = 90.0

    asc = float(asc or 0.0)
    mc = float(mc or 90.0)
    dsc = _norm360(asc + 180.0)
    ic = _norm360(mc + 180.0)
    return {"ASC": asc, "DSC": dsc, "MC": mc, "IC": ic}


def _is_within_deg_of_any_angle(lon: float, angles: Dict[str, float], max_deg: float = 5.0) -> bool:
    for a in angles.values():
        if _absdiff_deg(lon, a) <= max_deg:
            return True
    return False


# ------------------------
# Aspect policy (user-specified)
# ------------------------

class _AspectDef:
    __slots__ = ("angle", "name", "base_orb", "cap")
    def __init__(self, angle: float, name: str, base_orb: float, cap: float):
        self.angle = angle
        self.name = name
        self.base_orb = base_orb
        self.cap = cap


MAJOR_MINOR_ASPECTS: List[_AspectDef] = [
    _AspectDef(0.0,   "Conjunction",      8.0, 10.0),
    _AspectDef(180.0, "Opposition",       7.0, 10.0),
    _AspectDef(90.0,  "Square",           6.0,  8.0),
    _AspectDef(120.0, "Trine",            6.0,  8.0),
    _AspectDef(60.0,  "Sextile",          4.0,  5.0),
    _AspectDef(150.0, "Quincunx",         3.0,  4.0),
    _AspectDef(45.0,  "Semisquare",       2.0,  2.0),
    _AspectDef(135.0, "Sesquiquadrate",   2.0,  2.0),
]

HARD_FOR_AFFLICTION = {
    "Conjunction": 6.0,
    "Opposition": 6.0,
    "Square": 5.0,
    "Quincunx": 3.0,
    "Semisquare": 2.0,
    "Sesquiquadrate": 2.0,
}


def _orb_to_aspect(lon1: float, lon2: float, A: float) -> float:
    sep = abs(_norm180(lon1 - lon2))
    orb = abs(sep - A)
    if orb > 180.0:
        orb = 360.0 - orb
    return orb


def _allowed_orb(ad: _AspectDef, body1: Dict[str, Any], body2: Dict[str, Any], angles: Dict[str, float]) -> float:
    """Compute allowed orb with bonuses and caps.

    Angle bonus: +2° if either body is an angle or within 5° of one.
    Luminary bonus: +1° if Sun or Moon is involved (then cap by ad.cap).
    """
    base = ad.base_orb
    # detect angular proximity
    b1ang = _is_within_deg_of_any_angle(float(body1.get("longitude", 0.0)), angles, 5.0) if body1.get("planet") else False
    b2ang = _is_within_deg_of_any_angle(float(body2.get("longitude", 0.0)), angles, 5.0) if body2.get("planet") else False
    # Angle points are always angular
    if body1.get("kind") == "angle" or body2.get("kind") == "angle" or b1ang or b2ang:
        base += 2.0
    p1 = (body1.get("planet") or "").strip()
    p2 = (body2.get("planet") or "").strip()
    if p1 in ("Sun", "Moon") or p2 in ("Sun", "Moon"):
        base += 1.0
    # cap
    return min(base, ad.cap)


def _is_afflicting(ad: _AspectDef, orb: float) -> bool:
    limit = HARD_FOR_AFFLICTION.get(ad.name)
    if limit is None:
        return False  # trine/sextile not considered afflicting
    return orb <= limit


def _severity_tier(orb: float, angular_involved: bool) -> str:
    if orb <= 2.0 or angular_involved:
        return "severe"
    if orb <= 4.0:
        return "moderate"
    return "mild"


def _escalate_tier(tier: str) -> str:
    if tier == "mild":
        return "moderate"
    if tier == "moderate":
        return "severe"
    return tier


def _compute_mercury_shock(planets: List[Dict[str, Any]]) -> bool:
    """Return True if Mercury has a very tight minor/quincunx aspect from Mars or Uranus.

    Rules:
      - Consider only Quincunx (150°), Semisquare (45°), Sesquiquadrate (135°)
      - Orb < 1.0°
      - Suppress if Mercury is cazimi the Sun (|Mercury–Sun| ≤ 0.283°)
    """
    lookup = {p.get("planet"): p for p in planets}
    merc = lookup.get("Mercury")
    if not merc:
        return False
    lonM = float(merc.get("longitude", 0.0))

    # Cazimi suppression
    sun = lookup.get("Sun")
    if sun is not None:
        try:
            lonS = float(sun.get("longitude", 0.0))
            from math import fabs
            if _absdiff_deg(lonM, lonS) <= 0.283:
                return False
        except Exception:
            pass

    targets = [lookup.get("Mars"), lookup.get("Uranus")]
    for t in targets:
        if not t:
            continue
        lonT = float(t.get("longitude", 0.0))
        for ad in MAJOR_MINOR_ASPECTS:
            name = ad.name
            if name not in ("Quincunx", "Semisquare", "Sesquiquadrate"):
                continue
            orb = _orb_to_aspect(lonM, lonT, ad.angle)
            if orb < 1.0:
                return True
    return False


def _neptune_angular_or_station(planets: List[Dict[str, Any]], angles: Dict[str, float]) -> bool:
    nep = next((p for p in planets if p.get("planet") == "Neptune"), None)
    if not nep:
        return False
    try:
        lon = float(nep.get("longitude", 0.0))
        speed = abs(float(nep.get("speed", 0.0)))
    except Exception:
        lon, speed = 0.0, 0.0
    if _is_within_deg_of_any_angle(lon, angles, 5.0):
        return True
    # Stationary heuristic: very low apparent speed
    if speed <= 0.02:  # deg/day
        return True
    return False


# ------------------------
# Degree hits and midpoint activation
# ------------------------

def _parse_degree_token(token: str) -> Optional[float]:
    """Parse strings like '25 Leo' → ecliptic longitude (float degrees)."""
    try:
        parts = token.strip().replace("\u00B0", " ").split()
        if not parts:
            return None
        deg = float(parts[0])
        sign = parts[1].strip().lower() if len(parts) > 1 else None
        signs = {
            "aries": 0, "taurus": 30, "gemini": 60, "cancer": 90,
            "leo": 120, "virgo": 150, "libra": 180, "scorpio": 210,
            "sagittarius": 240, "capricorn": 270, "aquarius": 300, "pisces": 330,
        }
        if sign is None or sign not in signs:
            return None
        return signs[sign] + deg
    except Exception:
        return None


_SIGN_BASES = {
    "aries": 0.0,
    "taurus": 30.0,
    "gemini": 60.0,
    "cancer": 90.0,
    "leo": 120.0,
    "virgo": 150.0,
    "libra": 180.0,
    "scorpio": 210.0,
    "sagittarius": 240.0,
    "capricorn": 270.0,
    "aquarius": 300.0,
    "pisces": 330.0,
}

_SIGN_ALIASES = {
    "ari": "aries",
    "aries": "aries",
    "tau": "taurus",
    "taur": "taurus",
    "taurus": "taurus",
    "gem": "gemini",
    "gemini": "gemini",
    "can": "cancer",
    "cancer": "cancer",
    "leo": "leo",
    "vir": "virgo",
    "virgo": "virgo",
    "lib": "libra",
    "libra": "libra",
    "sco": "scorpio",
    "scorp": "scorpio",
    "scorpio": "scorpio",
    "sag": "sagittarius",
    "sagi": "sagittarius",
    "sagittarius": "sagittarius",
    "cap": "capricorn",
    "capr": "capricorn",
    "capricorn": "capricorn",
    "aqu": "aquarius",
    "aqua": "aquarius",
    "aquarius": "aquarius",
    "pis": "pisces",
    "pisces": "pisces",
}

_SIGN_PATTERN = re.compile(
    r"(?i)\b("
    r"aries|ari|taurus|taur|tau|gemini|gem|cancer|can|leo|virgo|vir|"
    r"libra|lib|scorpio|scorp|sco|sagittarius|sagi|sag|capricorn|capr|cap|"
    r"aquarius|aqua|aqu|pisces|pis"
    r")\b"
)


def _parse_degree_token(token: str) -> Optional[float]:
    """Parse sign-based degree tokens into ecliptic longitude."""
    try:
        text = str(token or "").strip()
        if not text:
            return None

        sign_match = _SIGN_PATTERN.search(text)
        if not sign_match:
            return None
        sign_token = sign_match.group(0).strip().lower()
        sign_name = _SIGN_ALIASES.get(sign_token)
        if sign_name is None:
            return None

        degree_text = f"{text[:sign_match.start()]} {text[sign_match.end():]}".strip()
        if not degree_text:
            return None

        normalized = degree_text
        for src, target in (
            ("\u00B0", " "),
            ("\u00BA", " "),
            ("\u2032", " "),
            ("\u2033", " "),
            ("\u2019", " "),
            ("\u201D", " "),
            ("'", " "),
            ('"', " "),
        ):
            normalized = normalized.replace(src, target)
        normalized = normalized.replace("deg", " ")
        normalized = normalized.replace("min", " ")
        normalized = normalized.replace("sec", " ")
        normalized = normalized.replace(":", " ")

        residual = re.sub(r"[\d\.\s+-]", "", normalized.lower())
        if residual:
            return None

        numbers = re.findall(r"\d+(?:\.\d+)?", normalized)
        if not numbers or len(numbers) > 3:
            return None
        if len(numbers) > 1 and "." in numbers[0]:
            return None

        degrees = float(numbers[0])
        minutes = float(numbers[1]) if len(numbers) >= 2 else 0.0
        seconds = float(numbers[2]) if len(numbers) >= 3 else 0.0
        if not (0.0 <= degrees < 30.0):
            return None
        if not (0.0 <= minutes < 60.0):
            return None
        if not (0.0 <= seconds < 60.0):
            return None

        return _SIGN_BASES[sign_name] + degrees + (minutes / 60.0) + (seconds / 3600.0)
    except Exception:
        return None


def _midpoint(a: float, b: float) -> float:
    # shortest-arc midpoint on circle
    da = _norm180(b - a)
    return _norm360(a + da / 2.0)


def _degree_hits(chart_data: Dict[str, Any], planets: List[Dict[str, Any]], special_degrees: Iterable[str]) -> Dict[str, Any]:
    """Compute hits to special degrees with multiple windows and stacking.

    Windows:
      - planets/angles: ±1.0°
      - cusps & parts: ±0.5°
    Plus midpoint activation within ±1.0°.
    """
    angles = _angles_from_chart(chart_data)
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list):
        cusps = []
    # parts from API payload if present
    parts = (chart_data.get("arabic_parts") or {})
    parts_list = list(parts.values()) if isinstance(parts, dict) else (parts if isinstance(parts, list) else [])

    deg_list: List[Tuple[str, float]] = []
    for tok in special_degrees or []:
        v = _parse_degree_token(str(tok))
        if v is not None:
            deg_list.append((str(tok), v))

    results: List[Dict[str, Any]] = []
    for label, dlon in deg_list:
        hits: List[Dict[str, Any]] = []
        # planets & angles window ±1.0
        for p in planets:
            lon = float(p.get("longitude", 0.0))
            if _absdiff_deg(lon, dlon) <= 1.0:
                hits.append({"type": "planet", "target": p.get("planet"), "orb": _absdiff_deg(lon, dlon)})
        for aname, alon in angles.items():
            if _absdiff_deg(alon, dlon) <= 1.0:
                hits.append({"type": "angle", "target": aname, "orb": _absdiff_deg(alon, dlon)})
        # house cusps & parts window ±0.5
        for idx, cusp in enumerate(cusps[:12]):
            try:
                c = float(cusp)
            except Exception:
                continue
            if _absdiff_deg(c, dlon) <= 0.5:
                hits.append({"type": "cusp", "target": f"H{idx+1}", "orb": _absdiff_deg(c, dlon)})
        for part in parts_list:
            try:
                plon = float(part.get("lon"))
            except Exception:
                continue
            if _absdiff_deg(plon, dlon) <= 0.5:
                hits.append({"type": "part", "target": str(part.get("name")), "orb": _absdiff_deg(plon, dlon)})

        # midpoint activation: any pair with midpoint near degree within ±1°
        midpoint_active = False
        n = len(planets)
        for i in range(n):
            lon1 = float(planets[i].get("longitude", 0.0))
            for j in range(i + 1, n):
                lon2 = float(planets[j].get("longitude", 0.0))
                mp = _midpoint(lon1, lon2)
                if _absdiff_deg(mp, dlon) <= 1.0:
                    midpoint_active = True
                    break
            if midpoint_active:
                break

        # stacking factor: +0.25 per extra hit beyond 1
        stack_factor = 1.0 + max(0, len(hits) - 1) * 0.25

        results.append({
            "degree": label,
            "longitude": dlon,
            "hits": hits,
            "count": len(hits),
            "stack_factor": round(stack_factor, 2),
            "midpoint_active": midpoint_active,
        })

    return {"items": results}


# ------------------------
# Main computation entry
# ------------------------

def compute_metrics(chart_data: Dict[str, Any], timestamp_iso: Optional[str], special_degrees: Optional[List[str]] = None) -> Dict[str, Any]:
    planets = _planet_list(chart_data, timestamp_iso)
    angles = _angles_from_chart(chart_data)

    # Angular flags and simple statuses
    for p in planets:
        try:
            lon = float(p.get("longitude", 0.0))
            p["near_angle"] = _is_within_deg_of_any_angle(lon, angles, 5.0)
        except Exception:
            p["near_angle"] = False

    # Build emphasis
    sign_emphasis: Dict[str, float] = {}
    element_balance: Dict[str, float] = {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0}
    modality_balance: Dict[str, float] = {"Cardinal": 0.0, "Fixed": 0.0, "Mutable": 0.0}
    planet_signs: Dict[str, str] = {}
    for p in planets:
        sign = p.get("sign") or _sign_name_from_lon(float(p.get("longitude", 0.0)))
        w = 1.5 if p.get("near_angle") else 1.0
        sign_emphasis[sign] = sign_emphasis.get(sign, 0.0) + w
        element_balance[_element_of_sign(sign)] += w
        modality_balance[_modality_of_sign(sign)] += w
        name = p.get("planet")
        if name:
            planet_signs[str(name)] = sign

    # Planet strength/affliction (coarse)
    planet_status: Dict[str, Dict[str, Any]] = {}
    for p in planets:
        name = str(p.get("planet"))
        ess = float(p.get("essential_dignity", 0) or 0)
        acc = float(p.get("accidental_dignity", 0) or 0)
        dig = float(p.get("dignity_score", ess + acc) or 0)
        strong = (ess >= 4) or (acc >= 3 and p.get("near_angle")) or (dig >= 5)
        dignified = ess >= 4
        # mark afflicted later from aspects
        planet_status[name] = {"strong": bool(strong), "dignified": bool(dignified), "afflicted": False, "index": dig}

    # Afflictions and aspects (planet-planet and planet-angle)
    mercury_shock = _compute_mercury_shock(planets)
    neptune_amp = _neptune_angular_or_station(planets, angles)

    aspects: List[Dict[str, Any]] = []
    # planet-planet
    for i in range(len(planets)):
        a = planets[i]
        lonA = float(a.get("longitude", 0.0))
        for j in range(i + 1, len(planets)):
            b = planets[j]
            lonB = float(b.get("longitude", 0.0))
            for ad in MAJOR_MINOR_ASPECTS:
                orb = _orb_to_aspect(lonA, lonB, ad.angle)
                allowed = _allowed_orb(ad, a, b, angles)
                if orb <= allowed:
                    ang_involved = bool(a.get("near_angle") or b.get("near_angle"))
                    afflicting = _is_afflicting(ad, orb)
                    tier = _severity_tier(orb, ang_involved) if afflicting else None
                    # escalators
                    if tier:
                        if mercury_shock and (a.get("planet") == "Mercury" or b.get("planet") == "Mercury") and orb <= 4.0:
                            tier = _escalate_tier(tier)
                        if neptune_amp and (a.get("planet") == "Neptune" or b.get("planet") == "Neptune"):
                            tier = _escalate_tier(tier)
                    aspects.append({
                        "kind": "planet",
                        "planet1": a.get("planet"),
                        "planet2": b.get("planet"),
                        "aspect": ad.name,
                        "orb": round(orb, 2),
                        "allowed_orb": allowed,
                        "afflicting": bool(afflicting),
                        "severity": tier,
                    })
                    # mark afflicted status only for moderate/severe tiers
                    if afflicting and (tier in ("moderate", "severe")):
                        planet_status[a.get("planet")]["afflicted"] = True
                        planet_status[b.get("planet")]["afflicted"] = True

    # planet-angle
    for p in planets:
        for aname, alon in angles.items():
            body_angle = {"kind": "angle", "planet": aname, "longitude": alon}
            for ad in MAJOR_MINOR_ASPECTS:
                orb = _orb_to_aspect(float(p.get("longitude", 0.0)), alon, ad.angle)
                allowed = _allowed_orb(ad, p, body_angle, angles)
                if orb <= allowed:
                    ang_involved = True  # by definition
                    afflicting = _is_afflicting(ad, orb)
                    tier = _severity_tier(orb, ang_involved) if afflicting else None
                    if tier:
                        if mercury_shock and p.get("planet") == "Mercury" and orb <= 4.0:
                            tier = _escalate_tier(tier)
                        if neptune_amp and p.get("planet") == "Neptune":
                            tier = _escalate_tier(tier)
                    aspects.append({
                        "kind": "angle",
                        "planet": p.get("planet"),
                        "angle": aname,
                        "aspect": ad.name,
                        "orb": round(orb, 2),
                        "allowed_orb": allowed,
                        "afflicting": bool(afflicting),
                        "severity": tier,
                    })
                    if afflicting and (tier in ("moderate", "severe")):
                        planet_status[p.get("planet")]["afflicted"] = True

    # House emphasis and coarse afflictions
    cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
    if not isinstance(cusps, list):
        cusps = []
    house_emphasis: Dict[str, int] = {str(i): 0 for i in range(1, 13)}
    for p in planets:
        try:
            h = int(p.get("house", 0))
        except Exception:
            h = 0
        if 1 <= h <= 12:
            house_emphasis[str(h)] += 1
    malefics = {"Mars", "Saturn"}
    # include modern heavies in affliction context
    malefics_modern = {"Neptune", "Pluto"}
    house_afflicted: Dict[str, bool] = {str(i): False for i in range(1, 13)}
    # Strategy: a house is afflicted if (a) malefic in house and afflicted, or (b) its ruler (if available in chart_data) is afflicted
    rulers = chart_data.get("house_rulers") or {}
    # rulers keys might be strings or ints mapped to names
    for hstr in house_afflicted.keys():
        hnum = int(hstr)
        # (a)
        for p in planets:
            if int(p.get("house", 0)) == hnum and (p.get("planet") in malefics or p.get("planet") in malefics_modern):
                if planet_status.get(p.get("planet"), {}).get("afflicted"):
                    house_afflicted[hstr] = True
                    break
        # (b)
        if not house_afflicted[hstr]:
            rname = rulers.get(str(hnum)) or rulers.get(hnum)
            if rname and planet_status.get(rname, {}).get("afflicted"):
                house_afflicted[hstr] = True

    # Degree hits (optional)
    degree_hits = _degree_hits(chart_data, planets, special_degrees or []) if special_degrees else {"items": []}

    # Planet lookups for filters
    planet_longitudes: Dict[str, float] = {}
    planet_houses: Dict[str, int] = {}
    planet_deg_in_sign: Dict[str, float] = {}
    planet_speeds: Dict[str, float] = {}
    for p in planets:
        try:
            name = str(p.get("planet"))
            lon = float(p.get("longitude", 0.0))
            planet_longitudes[name] = lon
            try:
                planet_houses[name] = int(p.get("house", 0))
            except Exception:
                planet_houses[name] = 0
            planet_deg_in_sign[name] = _norm360(lon) % 30.0
            try:
                planet_speeds[name] = float(p.get("speed", 0.0) or 0.0)
            except Exception:
                planet_speeds[name] = 0.0
        except Exception:
            continue

    # House rulers mapping passthrough (string keys)
    house_rulers = {}
    try:
        hr = chart_data.get("house_rulers") or {}
        if isinstance(hr, dict):
            # Normalize keys to strings
            house_rulers = {str(k): v for k, v in hr.items()}
    except Exception:
        house_rulers = {}

    # Solar overlay (engine-agnostic): reuse engine summary when present; add phase context
    solar_conditions: Dict[str, str] = {}
    solar_distance: Dict[str, float] = {}
    solar_phase_by_planet: Dict[str, str] = {}
    solar_phase_sets: Dict[str, List[str]] = {
        'combustion_applying': [], 'combustion_separating': [], 'combustion_stationary': [],
        'under_beams_applying': [], 'under_beams_separating': [], 'under_beams_stationary': [],
        'cazimi_applying': [], 'cazimi_separating': [], 'cazimi_stationary': [],
    }
    try:
        scs = chart_data.get('solar_conditions_summary') if isinstance(chart_data, dict) else None
        if isinstance(scs, dict):
            def _ingest(items, label):
                for it in items or []:
                    try:
                        nm = str(it.get('planet') or it.get('name') or '')
                        if not nm:
                            continue
                        solar_conditions[nm] = label
                        if it.get('distance_from_sun') is not None:
                            solar_distance[nm] = float(it.get('distance_from_sun'))
                    except Exception:
                        continue
            _ingest(scs.get('cazimi_planets'), 'Cazimi')
            _ingest(scs.get('combusted_planets'), 'Combustion')
            _ingest(scs.get('under_beams_planets'), 'Under the Beams')

        # Compute phase for planets with solar condition
        sun_lon = float(planet_longitudes.get('Sun', 0.0))
        sun_spd = float(planet_speeds.get('Sun', 0.0))
        for nm, cond in list(solar_conditions.items()):
            try:
                pl_lon = float(planet_longitudes.get(nm))
                pl_spd = float(planet_speeds.get(nm, 0.0))
                diff = ((pl_lon - sun_lon + 180.0) % 360.0) - 180.0
                rel_speed = pl_spd - sun_spd
                if abs(rel_speed) <= 1e-4:
                    ph = 'stationary'
                else:
                    ph = 'applying' if (diff * rel_speed) < 0 else 'separating'
                solar_phase_by_planet[nm] = ph
                key = None
                if cond == 'Combustion': key = f'combustion_{ph}'
                elif cond == 'Under the Beams': key = f'under_beams_{ph}'
                elif cond == 'Cazimi': key = f'cazimi_{ph}'
                if key and key in solar_phase_sets:
                    solar_phase_sets[key].append(nm)
            except Exception:
                continue
        # Deduplicate and sort
        for k, v in list(solar_phase_sets.items()):
            try:
                solar_phase_sets[k] = sorted(set(v))
            except Exception:
                pass
    except Exception:
        pass

    return {
        "sign_emphasis": sign_emphasis,
        "element_balance": element_balance,
        "modality_balance": modality_balance,
        "planet_signs": planet_signs,
        "planet_longitudes": planet_longitudes,
        "planet_houses": planet_houses,
        "planet_deg_in_sign": planet_deg_in_sign,
        "house_rulers": house_rulers,
        "planet_status": planet_status,
        "angle_aspects": [a for a in aspects if a.get("kind") == "angle"],
        "planetary_aspects": [a for a in aspects if a.get("kind") == "planet"],
        "house": {
            "emphasis": house_emphasis,
            "afflicted": house_afflicted,
        },
        "degree_hits": degree_hits,
        # Optional flags
        "flags": {
            "mercury_shock": mercury_shock,
            "neptune_station_or_angular": neptune_amp,
        },
        # Solar overlay for trait rules
        "solar": {
            "conditions": solar_conditions,
            "distance_deg": solar_distance,
            "phase": solar_phase_by_planet,
        },
        "solar_phase": solar_phase_sets,
    }
