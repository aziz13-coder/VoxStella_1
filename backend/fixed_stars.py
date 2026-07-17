# -*- coding: utf-8 -*-
"""
Fixed star proximity checks (lightweight, no external ephemeris).

Provides a small catalog of notable fixed stars with approximate tropical
longitudes and utilities to detect conjunctions with Sun/Moon and house cusps.

Note: Longitudes are approximate modern tropical values; accuracy is sufficient
for infotainment/heads-up tiles and can be refined later if needed.
"""

from typing import List, Dict, Any, Optional


def _deg_norm(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0


def _ang_dist(a: float, b: float) -> float:
    a = _deg_norm(a)
    b = _deg_norm(b)
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


# Minimal catalog of bright/traditional fixed stars with approximate tropical longitudes
FIXED_STAR_CATALOG: List[Dict[str, Any]] = [
    {"name": "Regulus",    "constellation": "Leo",  "longitude": 149.833},
    {"name": "Spica",      "constellation": "Vir",  "longitude": 173.833},
    {"name": "Aldebaran",  "constellation": "Gem",  "longitude": 69.783},
    {"name": "Antares",    "constellation": "Sgr",  "longitude": 249.767},
    {"name": "Fomalhaut",  "constellation": "Psc",  "longitude": 333.867},
    {"name": "Algol",      "constellation": "Tau",  "longitude": 56.167},
    {"name": "Sirius",     "constellation": "CMa",  "longitude": 104.083},
    {"name": "Arcturus",   "constellation": "Lib",  "longitude": 204.167},
    {"name": "Vega",       "constellation": "Cap",  "longitude": 285.317},
    {"name": "Betelgeuse", "constellation": "Gem",  "longitude": 88.750},
    {"name": "Pollux",     "constellation": "Cnc",  "longitude": 113.217},
    {"name": "Procyon",    "constellation": "Cnc",  "longitude": 115.967},
    {"name": "Denebola",   "constellation": "Leo",  "longitude": 141.767},
    {"name": "Capella",    "constellation": "Gem",  "longitude": 81.867},
    # Added popular stars per request (approximate tropical longitudes)
    {"name": "Acrux",      "constellation": "Crux",        "longitude": 222.000},
    {"name": "Achernar",   "constellation": "Eridanus",    "longitude": 345.000},
    {"name": "Alcyone",    "constellation": "Taurus",      "longitude": 59.000},
    {"name": "Hyades",     "constellation": "Taurus",      "longitude": 65.750},
    {"name": "Algenib",    "constellation": "Pegasus",     "longitude": 9.000},
    {"name": "Markab",     "constellation": "Pegasus",     "longitude": 353.000},
    {"name": "Alhena",     "constellation": "Gemini",      "longitude": 99.000},
    {"name": "Algorab",    "constellation": "Corvus",      "longitude": 193.000},
    {"name": "Alpheratz",  "constellation": "Andromeda",   "longitude": 14.000},
    {"name": "Altair",     "constellation": "Aquila",      "longitude": 302.000},
    {"name": "Bellatrix",  "constellation": "Orion",       "longitude": 80.000},
    {"name": "Castor",     "constellation": "Gemini",      "longitude": 110.000},
    {"name": "Canopus",    "constellation": "Carina",      "longitude": 95.000},
    {"name": "Deneb",      "constellation": "Cygnus",      "longitude": 313.000},
    {"name": "Zosma",      "constellation": "Leo",         "longitude": 171.000},
    # Extended catalog (approximate tropical longitudes)
    {"name": "Rigel",       "constellation": "Orion",       "longitude": 78.000},
    {"name": "Praesaepe",   "constellation": "Cancer",      "longitude": 127.200},
    {"name": "North Asellus","constellation": "Cancer",     "longitude": 127.400},
    {"name": "South Asellus","constellation": "Cancer",     "longitude": 128.583},
    {"name": "Phecda",      "constellation": "Ursa Major",  "longitude": 150.483},
    {"name": "Rasalhague",  "constellation": "Ophiuchus",   "longitude": 259.000},
    {"name": "Rasalgethi",  "constellation": "Hercules",    "longitude": 242.000},
    {"name": "Unukalhai",   "constellation": "Serpens",     "longitude": 232.067},
    {"name": "Alphard",     "constellation": "Hydra",       "longitude": 150.000},
    {"name": "Vindemiatrix","constellation": "Virgo",       "longitude": 187.000},
    {"name": "Zuben Elgenubi","constellation": "Libra",    "longitude": 199.000},
    {"name": "Zuben Elschemali","constellation": "Libra",  "longitude": 206.000},
    {"name": "Deneb Kaitos","constellation": "Cetus",      "longitude": 15.000},
    {"name": "Alkaid",      "constellation": "Ursa Major",  "longitude": 152.000},
    {"name": "Alnilam",     "constellation": "Orion",       "longitude": 84.000},
    {"name": "Alrescha",    "constellation": "Pisces",      "longitude": 359.000},
    {"name": "Deneb Algedi","constellation": "Capricorn",   "longitude": 300.000},
    {"name": "Scheat",      "constellation": "Pegasus",     "longitude": 359.367},
    {"name": "Hamal",       "constellation": "Ari",         "longitude": 37.000},
]


def _normalize_planets(planets) -> Dict[str, float]:
    """Return mapping planet name -> longitude from chart_data['planets'] (list or dict)."""
    result: Dict[str, float] = {}
    if isinstance(planets, list):
        for p in planets:
            try:
                name = p.get("planet") or p.get("name")
                lon = float(p.get("longitude"))
                if name is not None:
                    result[name] = lon
            except Exception:
                continue
    elif isinstance(planets, dict):
        for name, info in planets.items():
            try:
                lon = float(info.get("longitude"))
                result[name] = lon
            except Exception:
                continue
    return result


def compute_fixed_star_hits(chart_data: Dict[str, Any], orb_deg: float = 1.0,
                            check_planets: Optional[List[str]] = None,
                            include_cusps: bool = True) -> List[Dict[str, Any]]:
    """
    Compute fixed star conjunctions to selected planets (default: Sun, Moon)
    and optionally to house cusps, within orb_deg.

    Returns a list of hits with fields:
      - name, constellation, star_longitude
      - target_type: 'planet' or 'cusp'
      - target: planet name or cusp label 'C1'..'C12'
      - target_longitude
      - orb_deg (absolute separation)
    """
    if check_planets is None:
        check_planets = ["Sun", "Moon"]

    hits: List[Dict[str, Any]] = []
    planets_map = _normalize_planets(chart_data.get("planets", {}))

    # Planetary hits
    for star in FIXED_STAR_CATALOG:
        s_lon = float(star["longitude"]) % 360
        for pname in check_planets:
            if pname in planets_map:
                p_lon = float(planets_map[pname]) % 360
                d = _ang_dist(s_lon, p_lon)
                if d <= orb_deg:
                    hits.append({
                        "name": star["name"],
                        "constellation": star.get("constellation"),
                        "star_longitude": s_lon,
                        "target_type": "planet",
                        "target": pname,
                        "target_longitude": p_lon,
                        "orb_deg": round(d, 3),
                    })

    # Cusp hits
    if include_cusps:
        cusps = chart_data.get("houses") or chart_data.get("house_cusps") or []
        if isinstance(cusps, list) and len(cusps) >= 1:
            for i, cusp_lon in enumerate(cusps[:12]):
                try:
                    c_lon = float(cusp_lon) % 360
                except Exception:
                    continue
                label = f"C{i+1}"
                for star in FIXED_STAR_CATALOG:
                    s_lon = float(star["longitude"]) % 360
                    d = _ang_dist(s_lon, c_lon)
                    if d <= orb_deg:
                        hits.append({
                            "name": star["name"],
                            "constellation": star.get("constellation"),
                            "star_longitude": s_lon,
                            "target_type": "cusp",
                            "target": label,
                            "target_longitude": c_lon,
                            "orb_deg": round(d, 3),
                        })

    # Sort by smallest orb
    hits.sort(key=lambda h: h.get("orb_deg", 999))
    return hits
