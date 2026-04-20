# -*- coding: utf-8 -*-
"""
Feature extraction for forensic analysis from compact AstroClock dashboard.

Inputs: compact dashboard payload (from compact_dashboard_projection)
Outputs: normalized feature dict used by knowledge rules.
"""

from typing import Any, Dict, List


SIGNS = [
    (0, "Aries"), (30, "Taurus"), (60, "Gemini"), (90, "Cancer"), (120, "Leo"), (150, "Virgo"),
    (180, "Libra"), (210, "Scorpio"), (240, "Sagittarius"), (270, "Capricorn"), (300, "Aquarius"), (330, "Pisces"),
]
MUTE_SIGNS = {"Cancer", "Scorpio", "Pisces"}
WATER_SIGNS = {"Cancer", "Scorpio", "Pisces"}
HARD_ASPECT_TYPES = {"conjunction", "square", "opposition"}
HARD_MALEFIC_PLANETS = ("Mars", "Saturn", "Uranus", "Pluto")
HARD_AFFLICTION_MAX_ORB = 5.0


def _norm360(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0


def _deg_in_sign(lon: float) -> float:
    return float(_norm360(float(lon)) % 30.0)


def _in_via_combusta(lon: float) -> bool:
    """Via combusta: 15° Libra (180+15=195) to 15° Scorpio (210+15=225)."""
    L = _norm360(float(lon))
    return 195.0 <= L < 225.0


def _house_number(value: Any) -> Any:
    try:
        return int(value)
    except Exception:
        return None


def _planet_sign_name(entry: Dict[str, Any]) -> str:
    try:
        return str(entry.get("sign") or "").strip()
    except Exception:
        return ""


def _aspect_entry(aspects: Dict[str, Dict[str, Any]], p1: str, p2: str) -> Dict[str, Any]:
    if not p1 or not p2:
        return {}
    return aspects.get(f"{p1}_to_{p2}") or aspects.get(f"{p2}_to_{p1}") or {}


def _has_aspect(aspects: Dict[str, Dict[str, Any]], p1: str, p2: str, types=None) -> bool:
    entry = _aspect_entry(aspects, p1, p2)
    if not entry:
        return False
    if not types:
        return True
    return str(entry.get("type") or "").lower() in set(types)


def _has_hard_aspect(aspects: Dict[str, Dict[str, Any]], p1: str, p2: str) -> bool:
    return _has_aspect(aspects, p1, p2, HARD_ASPECT_TYPES)


def _planet_hard_afflicted(name: str, aspects: Dict[str, Dict[str, Any]]) -> bool:
    if not name:
        return False
    for target in HARD_MALEFIC_PLANETS:
        if target == name:
            continue
        entry = _aspect_entry(aspects, name, target)
        if not entry:
            continue
        typ = str(entry.get("type") or "").lower()
        if typ not in HARD_ASPECT_TYPES:
            continue
        try:
            orb = float(entry.get("orb", 999.0))
        except Exception:
            orb = 999.0
        # Broad symbolic stress is useful context, but downstream binary rules
        # should only flip on tighter hard contacts.
        if orb <= HARD_AFFLICTION_MAX_ORB:
            return True
    return False


def extract_features(dashboard: Dict[str, Any]) -> Dict[str, Any]:
    planets_in = dashboard.get("planets") or []
    planets: Dict[str, Dict[str, Any]] = {}
    degree_sig = {
        "anaretic": [],
        "ingress": [],
        "middegree": [],
        "via_combusta": [],
    }

    for p in planets_in:
        try:
            name = p.get("planet") or p.get("name")
            if not name:
                continue
            lon = float(p.get("longitude", 0.0))
            deg = _deg_in_sign(lon)
            # sign name from longitude if not provided
            def _sign_name(L: float) -> str:
                d = _norm360(L)
                idx = int(d // 30) % 12
                return SIGNS[idx][1]
            entry = {
                "sign": p.get("sign") or _sign_name(lon),
                "house": p.get("house"),
                "longitude": lon,
                "degree_in_sign": deg,
                "dignity_score": p.get("dignity_score"),
                "dignities": p.get("dignities") or [],
                "essential_dignity_raw": p.get("essential_dignity"),
                "retrograde": bool(p.get("retrograde", False)),
                "angular": bool(p.get("house") in [1,4,7,10]),
                "anaretic": deg >= 29.0,
                "ingress": deg < 1.0,
                "middegree": 14.5 <= deg <= 15.5,
                "via_combusta": _in_via_combusta(lon),
                "mute_sign": (_sign_name(lon) in MUTE_SIGNS),
            }
            planets[name] = entry
            # degree signatures lists
            if entry["anaretic"]:
                degree_sig["anaretic"].append(name)
            if entry["ingress"]:
                degree_sig["ingress"].append(name)
            if entry["middegree"]:
                degree_sig["middegree"].append(name)
            if entry["via_combusta"]:
                degree_sig["via_combusta"].append(name)
        except Exception:
            continue

    # Moon special
    moon = planets.get("Moon") or {}

    # Build aspects map for easy matching
    # Prefer full aspects when available; otherwise use top_aspects + tightest
    aspects_list = []
    if isinstance(dashboard.get("all_aspects"), list):
        aspects_list = dashboard.get("all_aspects") or []
    else:
        aspects_list = (dashboard.get("top_aspects") or []) + ([dashboard.get("tightest_aspect")] if dashboard.get("tightest_aspect") else [])
    aspects: Dict[str, Dict[str, Any]] = {}
    for a in aspects_list:
        try:
            p1 = a.get("planet1")
            p2 = a.get("planet2")
            if not p1 or not p2:
                continue
            entry = {
                "type": (a.get("aspect") or "").strip().lower(),
                "applying": bool(a.get("applying", False)),
                "orb": float(a.get("orb", 999.0)),
                # Propagate horary engine perfection metrics when present
                "time_to_perfection": (float(a.get("time_to_perfection")) if a.get("time_to_perfection") is not None else None),
                "perfection_within_sign": (True if a.get("perfection_within_sign") in (True, 'true', 'True', 1, '1') else (False if a.get("perfection_within_sign") in (False, 'false', 'False', 0, '0') else None)),
                "degrees_to_exact": (float(a.get("degrees_to_exact")) if a.get("degrees_to_exact") is not None else None),
                "exact_time": a.get("exact_time") or None,
            }
            key = f"{p1}_to_{p2}"
            rev_key = f"{p2}_to_{p1}"
            aspects[key] = entry
            if rev_key not in aspects:
                # Keep a reverse alias so rules are not sensitive to serialization order.
                aspects[rev_key] = dict(entry)
        except Exception:
            continue

    # Fixed stars: preserve full hit list and a convenience map (last-hit wins by name)
    fs_hits: List[Dict[str, Any]] = []
    fs_map: Dict[str, Dict[str, Any]] = {}
    for hit in dashboard.get("fixed_star_hits") or []:
        try:
            fs_hits.append(hit)
            nm = hit.get("name")
            if nm:
                fs_map[nm] = hit
        except Exception:
            continue

    # Solar conditions summary (combustion, under beams, cazimi) → sets by planet name
    solar = {"combustion": set(), "under_beams": set(), "cazimi": set()}
    sc = dashboard.get("solar_conditions") or {}
    for k in ("combustion", "under_beams", "cazimi"):
        try:
            for item in sc.get(k) or []:
                pname = item.get("planet") or item.get("name")
                if pname:
                    solar[k].add(pname)
        except Exception:
            continue

    # Optional solar phase breakdown (non-breaking): applying/separating/stationary
    solar_phase = {
        "combustion_applying": [],
        "combustion_separating": [],
        "combustion_stationary": [],
        "under_beams_applying": [],
        "under_beams_separating": [],
        "under_beams_stationary": [],
        "cazimi_applying": [],
        "cazimi_separating": [],
        "cazimi_stationary": [],
    }
    try:
        for key in ("combustion", "under_beams", "cazimi"):
            items = (sc.get(key) or []) if isinstance(sc, dict) else []
            for it in items:
                try:
                    pname = it.get("planet") or it.get("name")
                    ph = (it.get("phase") or "").strip().lower()
                    if not pname or not ph:
                        continue
                    if ph not in ("applying", "separating", "stationary"):
                        continue
                    solar_phase[f"{key}_{ph}"].append(pname)
                except Exception:
                    continue
        # Deduplicate and sort for stability
        for k, v in list(solar_phase.items()):
            try:
                solar_phase[k] = sorted(set(v))
            except Exception:
                pass
    except Exception:
        # If anything goes wrong, preserve compatibility by just keeping empty lists
        pass

    # House-level synthesized metrics
    rulers = dashboard.get("house_rulers") or {}
    first_ruler = rulers.get("1") or rulers.get(1)
    eighth_ruler = rulers.get("8") or rulers.get(8)
    first_ruler_house = _house_number(planets.get(first_ruler, {}).get("house")) if first_ruler else None
    first_rules_eighth = bool(first_ruler and eighth_ruler and (str(first_ruler) == str(eighth_ruler)))

    malefics = {"Mars", "Saturn"}
    emphasis12_count = 0
    malefic_6th = 0
    malefic_8th = 0
    malefics_angular_count = 0
    house_counts = {str(i): 0 for i in range(1, 13)}
    water_planet_count = 0
    water_planets_in_4_8_12 = 0
    for pname, pinfo in planets.items():
        h = _house_number(pinfo.get("house"))
        if h == 12:
            emphasis12_count += 1
        if h == 6 and pname in malefics:
            malefic_6th += 1
        if h == 8 and pname in malefics:
            malefic_8th += 1
        if h in (1, 4, 7, 10) and pname in HARD_MALEFIC_PLANETS:
            malefics_angular_count += 1
        if h is not None and str(h) in house_counts:
            house_counts[str(h)] += 1
        if _planet_sign_name(pinfo) in WATER_SIGNS:
            water_planet_count += 1
            if h in (4, 8, 12):
                water_planets_in_4_8_12 += 1

    cusps = dashboard.get("house_cusps") or []

    def _sign_from_cusp(cidx: int) -> str:
        try:
            L = float(cusps[cidx - 1])
            idx = int(_norm360(L) // 30) % 12
            return SIGNS[idx][1]
        except Exception:
            return ""

    cusp_signs = {str(i): _sign_from_cusp(i) for i in range(1, 13)}
    water_cusp_count = sum(1 for sign in cusp_signs.values() if sign in WATER_SIGNS)
    water_cusp_4_8_12 = sum(1 for key in ("4", "8", "12") if cusp_signs.get(key) in WATER_SIGNS)

    houses_synth = {
        "first_ruler": first_ruler,
        "first_ruler_house": first_ruler_house,
        "eighth_ruler": eighth_ruler,
        "first_ruler_rules_8th": first_rules_eighth,
        "emphasis12_count": emphasis12_count,
        "emphasis12_strong": bool(emphasis12_count >= 2),
        "malefics_in_6th": malefic_6th,
        "malefics_in_8th": malefic_8th,
        "malefics_angular_count": malefics_angular_count,
        "counts": house_counts,
        "signs": cusp_signs,
        "water_cusp_count": water_cusp_count,
        "water_cusp_4_8_12": water_cusp_4_8_12,
        "water_planet_count": water_planet_count,
        "water_planets_in_4_8_12": water_planets_in_4_8_12,
        "first_ruler_in_4_8_12": bool(first_ruler_house in (4, 8, 12)),
        "first_ruler_in_8_or_12": bool(first_ruler_house in (8, 12)),
        "first_ruler_in_5th": bool(first_ruler_house == 5),
        "first_ruler_hard_afflicted": _planet_hard_afflicted(str(first_ruler or ""), aspects),
    }

    sixth_ruler = rulers.get("6") or rulers.get(6)
    sixth_ruler_house = _house_number(planets.get(sixth_ruler, {}).get("house")) if sixth_ruler else None
    houses_synth["sixth_ruler"] = sixth_ruler
    houses_synth["sixth_ruler_house"] = sixth_ruler_house
    houses_synth["sixth_ruler_in_7th"] = bool(sixth_ruler_house == 7)
    houses_synth["sixth_ruler_hard_afflicted"] = _planet_hard_afflicted(str(sixth_ruler or ""), aspects)

    seventh_ruler = rulers.get("7") or rulers.get(7)
    seventh_ruler_house = _house_number(planets.get(seventh_ruler, {}).get("house")) if seventh_ruler else None
    houses_synth["seventh_ruler"] = seventh_ruler
    houses_synth["seventh_ruler_house"] = seventh_ruler_house
    houses_synth["seventh_ruler_in_12th"] = bool(seventh_ruler_house == 12)
    houses_synth["seventh_ruler_in_8_or_12"] = bool(seventh_ruler_house in (8, 12))
    houses_synth["seventh_ruler_angular"] = bool(seventh_ruler_house in (1, 4, 7, 10))
    houses_synth["seventh_ruler_in_3_4_12"] = bool(seventh_ruler_house in (3, 4, 12))
    houses_synth["seventh_ruler_in_3_or_9"] = bool(seventh_ruler_house in (3, 9))
    houses_synth["seventh_ruler_in_3_9_10"] = bool(seventh_ruler_house in (3, 9, 10))
    houses_synth["seventh_ruler_in_10th"] = bool(seventh_ruler_house == 10)
    houses_synth["seventh_ruler_hard_afflicted"] = _planet_hard_afflicted(str(seventh_ruler or ""), aspects)

    def _inject_ruler_context(label: str, house_num: int) -> None:
        ruler = rulers.get(str(house_num)) or rulers.get(house_num)
        info = planets.get(ruler) or {}
        ruler_house = _house_number(info.get("house"))
        ruler_sign = _planet_sign_name(info)
        houses_synth[f"{label}_ruler"] = ruler
        houses_synth[f"{label}_ruler_house"] = ruler_house
        houses_synth[f"{label}_ruler_angular"] = bool(ruler_house in (1, 4, 7, 10))
        houses_synth[f"{label}_ruler_in_4_8_12"] = bool(ruler_house in (4, 8, 12))
        houses_synth[f"{label}_ruler_in_8_or_12"] = bool(ruler_house in (8, 12))
        houses_synth[f"{label}_ruler_water_sign"] = bool(ruler_sign in WATER_SIGNS)
        houses_synth[f"{label}_ruler_mute_sign"] = bool(ruler_sign in MUTE_SIGNS)
        houses_synth[f"{label}_ruler_hard_afflicted"] = _planet_hard_afflicted(str(ruler or ""), aspects)

    _inject_ruler_context("fourth", 4)
    _inject_ruler_context("fifth", 5)
    _inject_ruler_context("sixth", 6)
    _inject_ruler_context("eighth", 8)
    _inject_ruler_context("ninth", 9)
    _inject_ruler_context("tenth", 10)
    _inject_ruler_context("third", 3)
    _inject_ruler_context("eleventh", 11)

    houses_synth["first_and_seventh_rulers_same_house"] = bool(
        first_ruler_house is not None and first_ruler_house == seventh_ruler_house
    )
    houses_synth["first_and_seventh_rulers_aspected"] = _has_aspect(
        aspects, str(first_ruler or ""), str(seventh_ruler or "")
    )
    houses_synth["first_and_seventh_rulers_hard_aspect"] = _has_hard_aspect(
        aspects, str(first_ruler or ""), str(seventh_ruler or "")
    )
    fifth_ruler_house = houses_synth.get("fifth_ruler_house")
    houses_synth["first_and_fifth_rulers_same_house"] = bool(
        first_ruler_house is not None and first_ruler_house == fifth_ruler_house
    )
    houses_synth["fifth_and_seventh_rulers_same_house"] = bool(
        fifth_ruler_house is not None and fifth_ruler_house == seventh_ruler_house
    )
    houses_synth["seventh_and_tenth_same_ruler"] = bool(
        seventh_ruler and houses_synth.get("tenth_ruler") and str(seventh_ruler) == str(houses_synth.get("tenth_ruler"))
    )
    houses_synth["seventh_and_eleventh_same_ruler"] = bool(
        seventh_ruler and houses_synth.get("eleventh_ruler") and str(seventh_ruler) == str(houses_synth.get("eleventh_ruler"))
    )
    houses_synth["first_fifth_seventh_clustered"] = bool(
        first_ruler_house is not None
        and first_ruler_house == fifth_ruler_house
        and first_ruler_house == seventh_ruler_house
    )

    angle_signs = {
        "C1": _sign_from_cusp(1),
        "C4": _sign_from_cusp(4),
        "C7": _sign_from_cusp(7),
        "C10": _sign_from_cusp(10),
    }
    houses_synth["angles_signs"] = angle_signs
    houses_synth["mute_signs_on_angles"] = any(s in MUTE_SIGNS for s in angle_signs.values())
    houses_synth["mute_sign_on_3rd_or_9th"] = ((_sign_from_cusp(3) in MUTE_SIGNS) or (_sign_from_cusp(9) in MUTE_SIGNS))

    north_node_house = _house_number(planets.get("North Node", {}).get("house") or planets.get("Node", {}).get("house"))
    houses_synth["north_node_house"] = north_node_house
    houses_synth["north_node_in_8th"] = bool(north_node_house == 8)

    neptune = planets.get("Neptune") or {}
    neptune_house = _house_number(neptune.get("house"))
    houses_synth["neptune_present"] = bool(neptune)
    houses_synth["neptune_angular"] = bool(neptune_house in (1, 4, 7, 10))
    houses_synth["neptune_in_4_8_12"] = bool(neptune_house in (4, 8, 12))
    houses_synth["neptune_water_sign"] = bool(_planet_sign_name(neptune) in WATER_SIGNS)

    moon_house = _house_number(moon.get("house"))
    moon_flags = {
        "void_of_course": bool((dashboard.get("moon") or {}).get("void_of_course", False)),
        "via_combusta": bool(moon.get("via_combusta", False)),
        "house": moon_house,
        "sign": _planet_sign_name(moon),
        "water_sign": bool(_planet_sign_name(moon) in WATER_SIGNS),
        "in_4_8_12": bool(moon_house in (4, 8, 12)),
        "in_3_or_9": bool(moon_house in (3, 9)),
        "hard_malefic_contact": _planet_hard_afflicted("Moon", aspects),
    }

    out = {
        "sect": dashboard.get("sect") or {},
        "planets": planets,
        "degree_signatures": degree_sig,
        "moon": moon_flags,
        "aspects": aspects,
        "lots": dashboard.get("arabic_parts") or {},
        "fixed_stars": fs_map,
        "fixed_stars_list": fs_hits,
        "house_cusps": dashboard.get("house_cusps") or [],
        "house_rulers": rulers,
        "houses": houses_synth,
        "solar": {k: sorted(v) for k, v in solar.items()},
        "solar_phase": solar_phase,
    }
    return out


def compute_dominance(features: Dict[str, Any]) -> Dict[str, Any]:
    """Compute Planetary Dominance scores with a traditional-inspired rubric.

    Scoring (approximate where data is limited):
      - Angular Placement (0–30): angular=True → +30
      - House Strength (0–20): angular house → +20; succedent → +10; cadent → +0
      - Essential Dignity (-20 to +25): domicile +25; exaltation +20; detriment -15; fall -20; else 0
      - Aspects (0+): per aspect: conj +5, opposition +4, square +3, trine +3, sextile +2; +1 if applying
      - Motion (-5 to 0): retrograde → -5; else 0 (stationary unknown)
    Levels:
      80+ Extremely Dominant; 60–79 Highly; 40–59 Moderate; 20–39 Slight; 0–19 Weak
    """
    planets = features.get('planets') or {}
    aspects = features.get('aspects') or {}

    def house_group(h):
        try:
            h = int(h)
        except Exception:
            return 'cadent'
        if h in (1,4,7,10):
            return 'angular'
        if h in (2,5,8,11):
            return 'succedent'
        return 'cadent'

    def essential_points(info: Dict[str, Any]) -> int:
        # Use dignities array or essential_dignity_raw if available
        tags = info.get('dignities') or []
        tagset = set()
        for t in tags if isinstance(tags, list) else []:
            try:
                tagset.add(str(t).strip().lower())
            except Exception:
                continue
        raw = str(info.get('essential_dignity_raw') or '').strip().lower()
        if 'domicile' in tagset or 'rulership' in tagset or 'own' in raw or 'domicile' in raw or 'ruler' in raw:
            return 25
        if 'exalt' in raw or any('exalt' in t for t in tagset):
            return 20
        if 'detriment' in raw or 'detriment' in tagset:
            return -15
        if 'fall' in raw or 'fall' in tagset:
            return -20
        # fallback: modest mapping from dignity_score if present
        try:
            ds = float(info.get('dignity_score'))
            if ds >= 4:
                return 15
            if ds <= -4:
                return -10
        except Exception:
            pass
        return 0

    def level(score: int) -> str:
        if score >= 80:
            return 'Extremely Dominant'
        if score >= 60:
            return 'Highly Dominant'
        if score >= 40:
            return 'Moderately Dominant'
        if score >= 20:
            return 'Slightly Dominant'
        return 'Weak'

    # Pre-index aspects for both directions
    aspects_for = {name: [] for name in planets.keys()}
    for key, a in aspects.items():
        try:
            p1, p2 = key.split('_to_')
        except Exception:
            continue
        if p1 in aspects_for:
            aspects_for[p1].append(a)
        if p2 in aspects_for:
            aspects_for[p2].append(a)

    results = {}
    for name, info in planets.items():
        if not isinstance(info, dict):
            continue
        # Angular placement
        angular_pts = 30 if info.get('angular') else 0
        # House strength
        hg = house_group(info.get('house'))
        house_pts = 20 if hg == 'angular' else (10 if hg == 'succedent' else 0)
        # Essential dignity
        ess_pts = essential_points(info)
        # Motion
        motion_pts = -5 if info.get('retrograde') else 0
        # Aspects
        asp_pts = 0
        for a in aspects_for.get(name, []):
            typ = str(a.get('type') or '').lower()
            base = 0
            if typ == 'conjunction': base = 5
            elif typ == 'opposition': base = 4
            elif typ == 'square': base = 3
            elif typ == 'trine': base = 3
            elif typ == 'sextile': base = 2
            base += 1 if a.get('applying') else 0
            asp_pts += base
        total = angular_pts + house_pts + ess_pts + motion_pts + asp_pts
        results[name] = {
            'score': int(total),
            'level': level(total),
            'breakdown': {
                'angular': angular_pts,
                'house': house_pts,
                'essential': ess_pts,
                'motion': motion_pts,
                'aspects': asp_pts,
            }
        }
    return {'planets': results}
