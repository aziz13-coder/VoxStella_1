from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


_CORE_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
_ANGLE_NAMES = {"Ascendant", "Descendant", "IC", "Midheaven"}
_SPECIAL_DEGREE_ORB = 0.75
_ASTEROID_CONTACT_ORB = 1.0
_MCINTOSH_QUINDECILE_ORB = 2.0
_MCINTOSH_DESCENDANT_CLUSTER_ORB = 12.0
_MCINTOSH_DESCENDANT_CUSP_ORB = 2.5
_MCINTOSH_HARD_ASPECT_ORB = 6.0
_MCINTOSH_CONJUNCTION_ORB = 7.0
_EXACT_DIGNITY_DEGREE_ORB = 0.75

_MCINTOSH_CLUSTER_BODIES = {
    "Sun",
    "Moon",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
    "Node",
}
_MCINTOSH_MOON_CONJUNCTION_TARGETS = {"Saturn", "Uranus", "Neptune", "Pluto"}

_EXALTATION_DEGREES = {
    "Sun": ("Aries", 19.0),
    "Moon": ("Taurus", 3.0),
    "Mercury": ("Virgo", 15.0),
    "Venus": ("Pisces", 27.0),
    "Mars": ("Capricorn", 28.0),
    "Jupiter": ("Cancer", 15.0),
    "Saturn": ("Libra", 21.0),
}
_FALL_DEGREES = {
    "Sun": ("Libra", 19.0),
    "Moon": ("Scorpio", 3.0),
    "Mercury": ("Pisces", 15.0),
    "Venus": ("Virgo", 27.0),
    "Mars": ("Cancer", 28.0),
    "Jupiter": ("Capricorn", 15.0),
    "Saturn": ("Aries", 21.0),
}

_TRADITIONAL_PLANET_DIRECTIONS = {
    "Sun": "east",
    "Moon": "northwest",
    "Mars": "south",
    "Mercury": "north",
    "Jupiter": "northeast",
    "Venus": "southeast",
    "Saturn": "west",
}
_TRADITIONAL_HOUSE_DIRECTIONS = {
    "1": "east",
    "2": "north-northeast",
    "3": "northeast",
    "4": "north",
    "5": "north-northwest",
    "6": "northwest",
    "7": "west",
    "8": "south-southwest",
    "9": "southwest",
    "10": "south",
    "11": "south-southeast",
    "12": "southeast",
}

_AXIS_KEYWORDS = {
    "violence_homicide": {
        "aggressive",
        "argument",
        "assassination",
        "attack",
        "death",
        "evil",
        "fear",
        "grave",
        "graves",
        "kill",
        "police",
        "rape",
        "weapons",
    },
    "abduction_missing_person": {
        "abduction",
        "disguised",
        "hidden enemy",
        "hotels",
        "missing",
        "prisons",
        "secret opposition",
        "seizure",
        "underworld",
    },
    "deception_coverup": {
        "disguised",
        "evidence",
        "hidden",
        "investigators",
        "secret",
        "theft",
    },
    "domestic_partner_involvement": {
        "couple",
        "domestic",
        "marriage",
        "partner",
        "relationship",
    },
    "family_involvement": {
        "family",
        "home",
        "household",
        "mother",
        "parent",
    },
    "child_victim": {
        "child",
        "children",
    },
    "water_disappearance_or_drowning": {
        "swimming",
        "water",
    },
    "authority_or_public_case": {
        "authority",
        "courtroom",
        "government",
        "justice",
        "police",
        "public",
        "public office",
    },
    "route_vehicle_transport": {
        "airport",
        "cars",
        "local",
        "phone",
        "technology",
        "vehicles",
    },
}

_AXIS_CATEGORIES = {
    "violence_homicide": "Violence",
    "abduction_missing_person": "Abduction",
    "deception_coverup": "Deception",
    "domestic_partner_involvement": "Domestic",
    "family_involvement": "Family",
    "child_victim": "Children",
    "water_disappearance_or_drowning": "Water",
    "authority_or_public_case": "Authority",
    "route_vehicle_transport": "Disaster",
}

_AXIS_TITLES = {
    "violence_homicide": "Special degree activates violent-event testimony",
    "abduction_missing_person": "Special degree activates abduction or missing-person testimony",
    "deception_coverup": "Special degree activates deception or evidence testimony",
    "domestic_partner_involvement": "Partner asteroid or degree activates relationship testimony",
    "family_involvement": "Family or household asteroid-degree testimony is active",
    "child_victim": "Child-house asteroid-degree testimony is active",
    "water_disappearance_or_drowning": "Water or disappearance degree testimony is active",
    "authority_or_public_case": "Public or authority degree testimony is active",
    "route_vehicle_transport": "Route or vehicle degree testimony is active",
}


def _norm360(value: float) -> float:
    out = float(value) % 360.0
    return out if out >= 0 else out + 360.0


def _angular_distance(a: Any, b: Any) -> Optional[float]:
    try:
        delta = abs((_norm360(float(a)) - _norm360(float(b))) % 360.0)
        return delta if delta <= 180.0 else 360.0 - delta
    except Exception:
        return None


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _keyword_blob(*parts: Any) -> str:
    values: List[str] = []
    for part in parts:
        if isinstance(part, Mapping):
            values.extend(_keyword_blob(key, value) for key, value in part.items())
        elif isinstance(part, (list, tuple, set)):
            values.extend(_keyword_blob(item) for item in part)
        else:
            text = _normalize_text(part)
            if text:
                values.append(text)
    return " ".join(values)


def _degree_matches(actual: Any, target: Any, *, orb: float = _SPECIAL_DEGREE_ORB) -> bool:
    actual_float = _to_float(actual)
    target_float = _to_float(target)
    if actual_float is None or target_float is None:
        return False
    if target_float >= 30.0:
        return actual_float >= 29.0
    return abs(actual_float - target_float) <= orb


def _aspect_record(features: Mapping[str, Any], p1: str, p2: str) -> Mapping[str, Any]:
    aspects = features.get("aspects") if isinstance(features, Mapping) else {}
    if not isinstance(aspects, Mapping) or not p1 or not p2:
        return {}
    return aspects.get(f"{p1}_to_{p2}") or aspects.get(f"{p2}_to_{p1}") or {}


def _point_map(points: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    out: Dict[str, Mapping[str, Any]] = {}
    for point in points:
        name = str(point.get("name") or "")
        if name:
            out[name] = point
    return out


def _aspect_orb(
    features: Mapping[str, Any],
    points_by_name: Mapping[str, Mapping[str, Any]],
    p1: str,
    p2: str,
    *,
    aspect_type: str,
    exact_angle: float,
) -> Optional[float]:
    record = _aspect_record(features, p1, p2)
    if isinstance(record, Mapping) and record:
        typ = str(record.get("type") or record.get("aspect") or "").strip().lower().replace(" ", "_")
        if typ == aspect_type:
            orb = _to_float(record.get("orb"))
            if orb is not None:
                return abs(orb)
    a = points_by_name.get(p1)
    b = points_by_name.get(p2)
    if not a or not b:
        return None
    distance = _angular_distance(a.get("longitude"), b.get("longitude"))
    if distance is None:
        return None
    return abs(distance - exact_angle)


def _dedupe_append(values: MutableMapping[str, List[str]], key: str, item: str) -> None:
    if not item:
        return
    bucket = values.setdefault(key, [])
    if item not in bucket:
        bucket.append(item)


def _point_house(info: Mapping[str, Any]) -> Optional[int]:
    try:
        return int(info.get("house"))
    except Exception:
        return None


def _build_role_points(features: Mapping[str, Any]) -> List[Dict[str, Any]]:
    planets = features.get("planets") if isinstance(features, Mapping) else {}
    planets = planets if isinstance(planets, Mapping) else {}
    houses = features.get("houses") if isinstance(features, Mapping) else {}
    houses = houses if isinstance(houses, Mapping) else {}
    angles = features.get("angles") if isinstance(features, Mapping) else {}
    angles = angles if isinstance(angles, Mapping) else {}
    role_map: Dict[str, List[str]] = {}

    for name in _CORE_PLANETS:
        if name in planets:
            role_map.setdefault(name, [])
    _dedupe_append(role_map, "Moon", "moon")
    ruler_roles = {
        "first_ruler": "victim",
        "seventh_ruler": "perpetrator",
        "eighth_ruler": "death",
        "twelfth_ruler": "hidden",
        "fourth_ruler": "family",
        "fifth_ruler": "child",
        "third_ruler": "route",
        "ninth_ruler": "route",
        "tenth_ruler": "authority",
        "eleventh_ruler": "associate",
    }
    for field, role in ruler_roles.items():
        ruler = houses.get(field)
        if ruler:
            _dedupe_append(role_map, str(ruler), role)
    angle_roles = {
        "Ascendant": ("victim", "angle"),
        "Descendant": ("perpetrator", "relationship", "angle"),
        "IC": ("family", "home", "angle"),
        "Midheaven": ("authority", "public", "angle"),
    }
    points: List[Dict[str, Any]] = []
    for name, info in planets.items():
        if not isinstance(info, Mapping):
            continue
        lon = _to_float(info.get("longitude"))
        if lon is None:
            continue
        roles = list(dict.fromkeys(role_map.get(str(name), [])))
        points.append({"name": str(name), "kind": "planet", "info": info, "roles": roles, "longitude": lon})
    for name, roles in angle_roles.items():
        info = angles.get(name)
        if not isinstance(info, Mapping):
            continue
        lon = _to_float(info.get("longitude"))
        if lon is None:
            continue
        points.append({"name": name, "kind": "angle", "info": info, "roles": list(roles), "longitude": lon})
    return points


def _roles_support_axis(roles: Sequence[str], axis: str, case_context: Mapping[str, Any]) -> bool:
    role_set = set(roles)
    if "angle" in role_set:
        return axis not in {"child_victim", "family_involvement"} or bool(role_set & {"home", "family"})
    if axis in {"violence_homicide", "deception_coverup"}:
        return bool(role_set & {"victim", "perpetrator", "moon", "death", "hidden"})
    if axis in {"abduction_missing_person", "water_disappearance_or_drowning"}:
        return bool(role_set & {"victim", "perpetrator", "moon", "death", "hidden", "route"})
    if axis == "domestic_partner_involvement":
        return bool(role_set & {"victim", "perpetrator", "relationship"})
    if axis == "family_involvement":
        return bool(role_set & {"family", "home", "moon"}) or bool(case_context.get("child_case"))
    if axis == "child_victim":
        return bool(role_set & {"child"}) or bool(case_context.get("child_case"))
    if axis == "authority_or_public_case":
        return bool(role_set & {"authority", "public", "perpetrator"})
    if axis == "route_vehicle_transport":
        return bool(role_set & {"route", "victim", "perpetrator", "moon"})
    return False


def _axes_from_keywords(blob: str, roles: Sequence[str], case_context: Mapping[str, Any]) -> List[str]:
    axes: List[str] = []
    for axis, keywords in _AXIS_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords) and _roles_support_axis(roles, axis, case_context):
            axes.append(axis)
    return axes


def _iter_degree_rows(degree_special: Mapping[str, Any]) -> Iterable[Tuple[str, float, Dict[str, Any]]]:
    special = degree_special.get("special") if isinstance(degree_special, Mapping) else {}
    if isinstance(special, Mapping):
        for key, payload in special.items():
            match = re.match(r"^([A-Za-z]+)_([0-9]+(?:\.[0-9]+)?)$", str(key))
            if not match:
                continue
            sign, degree = match.group(1), float(match.group(2))
            row = dict(payload or {}) if isinstance(payload, Mapping) else {}
            row["source_key"] = str(key)
            yield sign, degree, row
    sign_degrees = degree_special.get("sign_degrees") if isinstance(degree_special, Mapping) else {}
    if isinstance(sign_degrees, Mapping):
        for sign, rows in sign_degrees.items():
            for row in rows or []:
                if not isinstance(row, Mapping):
                    continue
                degrees = row.get("degree")
                degree_values = degrees if isinstance(degrees, list) else [degrees]
                for degree in degree_values:
                    degree_float = _to_float(degree)
                    if degree_float is None:
                        continue
                    row_copy = dict(row)
                    row_copy["source_key"] = f"{sign}_{degree}"
                    yield str(sign), degree_float, row_copy


def _special_degree_findings(
    *,
    features: Mapping[str, Any],
    degree_special: Mapping[str, Any],
    relationship_delta: MutableMapping[str, float],
    survivability_delta: MutableMapping[str, float],
    evidence: List[str],
) -> List[Dict[str, Any]]:
    case_context = features.get("case_context") if isinstance(features, Mapping) else {}
    case_context = case_context if isinstance(case_context, Mapping) else {}
    findings: List[Dict[str, Any]] = []
    seen = set()

    for point in _build_role_points(features):
        info = point.get("info") if isinstance(point.get("info"), Mapping) else {}
        sign = str(info.get("sign") or "")
        degree = info.get("degree_in_sign")
        roles = list(point.get("roles") or [])
        if not sign or degree is None:
            continue
        for row_sign, row_degree, row in _iter_degree_rows(degree_special):
            if row_sign != sign or not _degree_matches(degree, row_degree):
                continue
            blob = _keyword_blob(row.get("label"), row.get("notes"), row.get("keywords"))
            axes = _axes_from_keywords(blob, roles, case_context)
            if not axes:
                continue
            source_key = str(row.get("source_key") or f"{row_sign}_{row_degree:g}")
            evidence_text = (
                f"{point['name']} at {float(degree):.2f} {sign} matches {source_key} "
                f"on roles {','.join(roles) or 'sensitive point'}"
            )
            if evidence_text not in evidence:
                evidence.append(evidence_text)
            for axis in axes:
                key = ("degree", source_key, point["name"], axis)
                if key in seen:
                    continue
                seen.add(key)
                category = _AXIS_CATEGORIES.get(axis, "Degree Signatures")
                findings.append(
                    {
                        "id": f"secondary_degree_{source_key.lower()}_{axis}",
                        "title": _AXIS_TITLES.get(axis, "Special degree testimony is active"),
                        "category": category,
                        "weight": 1.2 if point.get("kind") == "angle" else 1.0,
                        "rationale": (
                            "Source-backed special-degree testimony is counted only when it lands on "
                            f"a relevant significator, ruler, or angle: {evidence_text}."
                        ),
                        "evidence": {"point": point["name"], "degree": round(float(degree), 3), "source_key": source_key},
                    }
                )
                if axis == "domestic_partner_involvement":
                    relationship_delta["intimate_partner"] = relationship_delta.get("intimate_partner", 0.0) + 0.35
                elif axis == "family_involvement":
                    relationship_delta["family"] = relationship_delta.get("family", 0.0) + 0.3
                elif axis == "violence_homicide":
                    survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.3
                elif axis in {"abduction_missing_person", "deception_coverup"} and {"victim", "moon", "death"} & set(roles):
                    survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.15
    return findings


def _contact_targets(features: Mapping[str, Any]) -> List[Dict[str, Any]]:
    points = _build_role_points(features)
    targets: List[Dict[str, Any]] = []
    for point in points:
        roles = set(point.get("roles") or [])
        if roles or point.get("name") in {"Moon", "Venus"} or point.get("kind") == "angle":
            targets.append(point)
    return targets


def _asteroid_findings(
    *,
    features: Mapping[str, Any],
    relationship_delta: MutableMapping[str, float],
    survivability_delta: MutableMapping[str, float],
    evidence: List[str],
) -> List[Dict[str, Any]]:
    asteroids = features.get("asteroids") if isinstance(features, Mapping) else {}
    asteroids = asteroids if isinstance(asteroids, Mapping) else {}
    targets = _contact_targets(features)
    findings: List[Dict[str, Any]] = []
    seen = set()

    def add_finding(axis: str, asteroid_name: str, target_name: str, orb: float, rationale: str, weight: float = 1.0) -> None:
        key = ("asteroid", asteroid_name, target_name, axis)
        if key in seen:
            return
        seen.add(key)
        findings.append(
            {
                "id": f"secondary_asteroid_{asteroid_name.lower()}_{axis}",
                "title": _AXIS_TITLES.get(axis, "Asteroid testimony is active"),
                "category": _AXIS_CATEGORIES.get(axis, "Asteroids"),
                "weight": weight,
                "rationale": rationale,
                "evidence": {"asteroid": asteroid_name, "target": target_name, "orb_deg": round(orb, 3)},
            }
        )

    for asteroid_name, asteroid_info in asteroids.items():
        if not isinstance(asteroid_info, Mapping):
            continue
        asteroid_lon = _to_float(asteroid_info.get("longitude"))
        if asteroid_lon is None:
            continue
        for target in targets:
            orb = _angular_distance(asteroid_lon, target.get("longitude"))
            if orb is None or orb > _ASTEROID_CONTACT_ORB:
                continue
            roles = set(target.get("roles") or [])
            target_name = str(target.get("name") or "sensitive point")
            contact = f"{asteroid_name} conjunct {target_name} within {orb:.2f} degrees"
            if contact not in evidence:
                evidence.append(contact)
            rationale = (
                "Asteroid testimony is low-weight and source-backed only by broad asteroid doctrine; "
                f"it is counted here because {contact} touches {','.join(sorted(roles)) or 'a sensitive point'}."
            )
            if asteroid_name == "Juno" and (roles & {"victim", "perpetrator", "relationship"} or target_name in {"Ascendant", "Descendant", "Venus"}):
                relationship_delta["intimate_partner"] = relationship_delta.get("intimate_partner", 0.0) + 0.85
                add_finding("domestic_partner_involvement", asteroid_name, target_name, orb, rationale, weight=1.1)
            elif asteroid_name == "Ceres" and (roles & {"family", "child", "home", "moon", "victim"} or target_name in {"Moon", "IC"}):
                relationship_delta["family"] = relationship_delta.get("family", 0.0) + 0.65
                survivability_delta["recovery_support"] = survivability_delta.get("recovery_support", 0.0) + 0.15
                add_finding("family_involvement", asteroid_name, target_name, orb, rationale, weight=1.0)
                if roles & {"child"}:
                    add_finding("child_victim", asteroid_name, target_name, orb, rationale, weight=0.8)
            elif asteroid_name == "Vesta" and (roles & {"family", "home", "victim", "moon"} or target_name in {"Moon", "IC", "Ascendant"}):
                relationship_delta["family"] = relationship_delta.get("family", 0.0) + 0.35
                survivability_delta["recovery_support"] = survivability_delta.get("recovery_support", 0.0) + 0.15
                add_finding("family_involvement", asteroid_name, target_name, orb, rationale, weight=0.8)
            elif asteroid_name == "Proserpina" and (roles & {"victim", "perpetrator", "moon", "death", "hidden"} or target_name in {"Ascendant", "Descendant"}):
                survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.2
                add_finding("abduction_missing_person", asteroid_name, target_name, orb, rationale, weight=1.0)
            elif asteroid_name == "Pallas" and roles & {"authority", "public", "associate"}:
                relationship_delta["friend_acquaintance"] = relationship_delta.get("friend_acquaintance", 0.0) + 0.25
                add_finding("authority_or_public_case", asteroid_name, target_name, orb, rationale, weight=0.7)

    return findings


def _add_secondary_finding(
    findings: List[Dict[str, Any]],
    seen: set,
    *,
    finding_id: str,
    title: str,
    category: str,
    weight: float,
    rationale: str,
    evidence_payload: Mapping[str, Any],
) -> bool:
    if finding_id in seen:
        return False
    seen.add(finding_id)
    findings.append(
        {
            "id": finding_id,
            "title": title,
            "category": category,
            "weight": weight,
            "rationale": rationale,
            "evidence": dict(evidence_payload),
        }
    )
    return True


def _mcintosh_pattern_findings(
    *,
    features: Mapping[str, Any],
    relationship_delta: MutableMapping[str, float],
    survivability_delta: MutableMapping[str, float],
    evidence: List[str],
) -> List[Dict[str, Any]]:
    """McIntosh-derived confirmatory forensic patterns.

    These are intentionally secondary and role-gated. They should not create
    primary axis findings unless later benchmark work proves that is useful.
    """

    points = _build_role_points(features)
    points_by_name = _point_map(points)
    findings: List[Dict[str, Any]] = []
    seen = set()

    def roles_for(name: str) -> set:
        point = points_by_name.get(name) or {}
        return set(point.get("roles") or [])

    def relevant_pair(name_a: str, name_b: str) -> bool:
        roles = roles_for(name_a) | roles_for(name_b)
        return bool(roles & {"victim", "perpetrator", "moon", "death", "hidden", "relationship"})

    def append_evidence(text: str) -> None:
        if text and text not in evidence:
            evidence.append(text)

    # 1) Quindecile: obsession/separation testimony, only when one side is a
    # role-relevant point.
    names = sorted(points_by_name.keys())
    for idx, name_a in enumerate(names):
        for name_b in names[idx + 1 :]:
            if not relevant_pair(name_a, name_b):
                continue
            orb = _aspect_orb(
                features,
                points_by_name,
                name_a,
                name_b,
                aspect_type="quindecile",
                exact_angle=165.0,
            )
            if orb is None or orb > _MCINTOSH_QUINDECILE_ORB:
                continue
            roles = sorted(roles_for(name_a) | roles_for(name_b))
            text = f"{name_a}-{name_b} quindecile within {orb:.2f} degrees on roles {','.join(roles) or 'sensitive point'}"
            if _add_secondary_finding(
                findings,
                seen,
                finding_id=f"secondary_mcintosh_quindecile_{name_a.lower()}_{name_b.lower()}",
                title="Quindecile activates obsessive-separation testimony",
                category="Violence",
                weight=0.75,
                rationale=(
                    "McIntosh flags the 165 degree quindecile as obsessive, disruptive, "
                    f"and separating testimony; counted only because {text}."
                ),
                evidence_payload={"planet1": name_a, "planet2": name_b, "orb_deg": round(orb, 3), "roles": roles},
            ):
                append_evidence(text)
                survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.18

    # 2) Descendant / 7th-house cluster: repeated negative-outcome pattern in
    # McIntosh case examples.
    descendant = points_by_name.get("Descendant")
    descendant_lon = descendant.get("longitude") if isinstance(descendant, Mapping) else None
    cluster: List[str] = []
    for name, point in points_by_name.items():
        if name not in _MCINTOSH_CLUSTER_BODIES:
            continue
        info = point.get("info") if isinstance(point.get("info"), Mapping) else {}
        house = _point_house(info)
        near_descendant = False
        if descendant_lon is not None:
            orb = _angular_distance(point.get("longitude"), descendant_lon)
            near_descendant = bool(orb is not None and orb <= _MCINTOSH_DESCENDANT_CLUSTER_ORB)
        if house == 7 or near_descendant:
            cluster.append(name)
    cluster = list(dict.fromkeys(cluster))
    cluster_malefics = sorted(set(cluster) & {"Moon", "Mars", "Saturn", "Neptune", "Pluto", "Uranus"})
    if len(cluster) >= 3 and cluster_malefics:
        text = f"Descendant/7th-house cluster includes {', '.join(cluster)}"
        if _add_secondary_finding(
            findings,
            seen,
            finding_id="secondary_mcintosh_descendant_stellium",
            title="Descendant or 7th-house stellium intensifies perpetrator-axis testimony",
            category="Violence",
            weight=1.0,
            rationale=(
                "McIntosh describes negative-outcome crime charts with a stellium around "
                f"the Descendant/7th house; counted here because {text}."
            ),
            evidence_payload={"cluster": cluster, "malefic_or_lunar_members": cluster_malefics},
        ):
            append_evidence(text)
            survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.3

    # 3) Named hard patterns: Mars-Pluto square, Moon conjunct outer/malefic
    # planets, and Mars on the Descendant.
    mars_pluto_orb = _aspect_orb(
        features,
        points_by_name,
        "Mars",
        "Pluto",
        aspect_type="square",
        exact_angle=90.0,
    )
    if mars_pluto_orb is not None and mars_pluto_orb <= _MCINTOSH_HARD_ASPECT_ORB and relevant_pair("Mars", "Pluto"):
        text = f"Mars square Pluto within {mars_pluto_orb:.2f} degrees with role relevance"
        if _add_secondary_finding(
            findings,
            seen,
            finding_id="secondary_mcintosh_mars_square_pluto",
            title="Mars-Pluto square marks dangerous anger testimony",
            category="Violence",
            weight=0.9,
            rationale=(
                "McIntosh singles out Mars square Pluto when one planet rules the suspect "
                f"or person of interest; counted here because {text}."
            ),
            evidence_payload={"planet1": "Mars", "planet2": "Pluto", "orb_deg": round(mars_pluto_orb, 3)},
        ):
            append_evidence(text)
            survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.25

    for target in sorted(_MCINTOSH_MOON_CONJUNCTION_TARGETS):
        orb = _aspect_orb(
            features,
            points_by_name,
            "Moon",
            target,
            aspect_type="conjunction",
            exact_angle=0.0,
        )
        if orb is None or orb > _MCINTOSH_CONJUNCTION_ORB:
            continue
        text = f"Moon conjunct {target} within {orb:.2f} degrees"
        if _add_secondary_finding(
            findings,
            seen,
            finding_id=f"secondary_mcintosh_moon_conjunct_{target.lower()}",
            title=f"Moon-{target} conjunction adds negative-outcome testimony",
            category="Violence",
            weight=0.85,
            rationale=(
                "McIntosh notes Moon conjunctions to outer planets, especially Pluto "
                f"or Saturn, in negative-result charts; counted here because {text}."
            ),
            evidence_payload={"planet1": "Moon", "planet2": target, "orb_deg": round(orb, 3)},
        ):
            append_evidence(text)
            survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.22

    mars = points_by_name.get("Mars")
    if mars and descendant_lon is not None:
        orb = _angular_distance(mars.get("longitude"), descendant_lon)
        if orb is not None and orb <= _MCINTOSH_DESCENDANT_CUSP_ORB:
            text = f"Mars on Descendant within {orb:.2f} degrees"
            if _add_secondary_finding(
                findings,
                seen,
                finding_id="secondary_mcintosh_mars_on_descendant",
                title="Mars on the 7th cusp adds violent encounter testimony",
                category="Violence",
                weight=0.9,
                rationale=(
                    "McIntosh notes Mars on the 7th cusp recurring in negative-result "
                    f"charts; counted here because {text}."
                ),
                evidence_payload={"planet": "Mars", "angle": "Descendant", "orb_deg": round(orb, 3)},
            ):
                append_evidence(text)
                survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.25

    # 4) Exact exaltation/fall degree nuance. Victim/Moon strength helps
    # recovery; victim fall and perpetrator exact exaltation add pressure.
    for point in points:
        name = str(point.get("name") or "")
        if name not in _EXALTATION_DEGREES and name not in _FALL_DEGREES:
            continue
        info = point.get("info") if isinstance(point.get("info"), Mapping) else {}
        sign = str(info.get("sign") or "")
        degree = info.get("degree_in_sign")
        roles = set(point.get("roles") or [])
        if not sign or degree is None:
            continue
        point_kind: Optional[str] = None
        if name in _EXALTATION_DEGREES:
            ex_sign, ex_degree = _EXALTATION_DEGREES[name]
            if sign == ex_sign and _degree_matches(degree, ex_degree, orb=_EXACT_DIGNITY_DEGREE_ORB):
                point_kind = "exaltation"
        if point_kind is None and name in _FALL_DEGREES:
            fall_sign, fall_degree = _FALL_DEGREES[name]
            if sign == fall_sign and _degree_matches(degree, fall_degree, orb=_EXACT_DIGNITY_DEGREE_ORB):
                point_kind = "fall"
        if point_kind is None:
            continue
        if not (roles & {"victim", "perpetrator", "moon"} or name == "Moon"):
            continue
        role_label = ",".join(sorted(roles)) or ("moon" if name == "Moon" else "sensitive point")
        text = f"{name} at exact {point_kind} degree on roles {role_label}"
        if _add_secondary_finding(
            findings,
            seen,
            finding_id=f"secondary_mcintosh_exact_dignity_degree_{name.lower()}_{point_kind}",
            title=f"Exact {point_kind} degree modifies forensic strength",
            category="Dignity",
            weight=0.65,
            rationale=(
                "McIntosh distinguishes exact exaltation/fall degrees from broad dignity; "
                f"counted only on a role point because {text}."
            ),
            evidence_payload={"planet": name, "kind": point_kind, "degree": round(float(degree), 3), "roles": sorted(roles)},
        ):
            append_evidence(text)
            if point_kind == "exaltation":
                if roles & {"victim", "moon"} or name == "Moon":
                    survivability_delta["recovery_support"] = survivability_delta.get("recovery_support", 0.0) + 0.2
                if roles & {"perpetrator"}:
                    survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.12
            elif point_kind == "fall":
                if roles & {"victim", "moon"} or name == "Moon":
                    survivability_delta["fatal_pressure"] = survivability_delta.get("fatal_pressure", 0.0) + 0.2
                if roles & {"perpetrator"}:
                    survivability_delta["recovery_support"] = survivability_delta.get("recovery_support", 0.0) + 0.1

    return findings


def _traditional_directional_analysis(features: Mapping[str, Any]) -> Dict[str, Any]:
    points = _build_role_points(features)
    focus_points: List[Dict[str, Any]] = []
    for point in points:
        name = str(point.get("name") or "")
        info = point.get("info") if isinstance(point.get("info"), Mapping) else {}
        house = _point_house(info)
        direction = _TRADITIONAL_PLANET_DIRECTIONS.get(name)
        house_direction = _TRADITIONAL_HOUSE_DIRECTIONS.get(str(house)) if house is not None else None
        if not direction and not house_direction:
            continue
        focus_points.append(
            {
                "point": name,
                "roles": list(point.get("roles") or []),
                "planet_direction": direction,
                "house": house,
                "house_direction": house_direction,
                "degree_marker": round(_to_float(info.get("degree_in_sign")) or 0.0, 2),
            }
        )
    return {
        "planet_directions": dict(_TRADITIONAL_PLANET_DIRECTIONS),
        "house_directions": dict(_TRADITIONAL_HOUSE_DIRECTIONS),
        "focus_points": focus_points,
        "scoring_effect": "none",
        "source_basis": "mcintosh_planet_house_direction_mapping",
    }


def _round_score_map(scores: Mapping[str, float], *, cap: Optional[float] = None) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key, value in scores.items():
        try:
            amount = float(value)
        except Exception:
            continue
        if cap is not None:
            amount = max(-cap, min(cap, amount))
        if amount:
            out[str(key)] = round(amount, 2)
    return out


def compute_secondary_factor_analysis(
    features: Mapping[str, Any],
    degree_special: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute bounded forensic testimony from special degrees and asteroids.

    The rules are intentionally confirmatory: they require a relevant role point
    or tight asteroid conjunction before they can move relationship or
    survivability scores.
    """

    if not isinstance(features, Mapping):
        return {
            "findings": [],
            "axis_hints": [],
            "relationship_score_delta": {},
            "survivability_delta": {"fatal_pressure": 0.0, "recovery_support": 0.0, "net_score": 0.0},
            "evidence": [],
        }

    degree_special = degree_special if isinstance(degree_special, Mapping) else {}
    relationship_delta: Dict[str, float] = {}
    survivability_delta: Dict[str, float] = {}
    evidence: List[str] = []
    findings: List[Dict[str, Any]] = []
    findings.extend(
        _special_degree_findings(
            features=features,
            degree_special=degree_special,
            relationship_delta=relationship_delta,
            survivability_delta=survivability_delta,
            evidence=evidence,
        )
    )
    findings.extend(
        _asteroid_findings(
            features=features,
            relationship_delta=relationship_delta,
            survivability_delta=survivability_delta,
            evidence=evidence,
        )
    )
    findings.extend(
        _mcintosh_pattern_findings(
            features=features,
            relationship_delta=relationship_delta,
            survivability_delta=survivability_delta,
            evidence=evidence,
        )
    )

    relationship_scores = _round_score_map(relationship_delta, cap=1.5)
    fatal_pressure = min(1.2, max(0.0, float(survivability_delta.get("fatal_pressure", 0.0) or 0.0)))
    recovery_support = min(0.5, max(0.0, float(survivability_delta.get("recovery_support", 0.0) or 0.0)))
    axis_hints = []
    for finding in findings:
        category = str(finding.get("category") or "")
        title = str(finding.get("title") or "")
        axis_hints.append({"id": finding.get("id"), "category": category, "title": title})

    findings.sort(key=lambda item: float(item.get("weight") or 0.0), reverse=True)
    return {
        "findings": findings,
        "axis_hints": axis_hints,
        "relationship_score_delta": relationship_scores,
        "survivability_delta": {
            "fatal_pressure": round(fatal_pressure, 2),
            "recovery_support": round(recovery_support, 2),
            "net_score": round(recovery_support - fatal_pressure, 2),
        },
        "evidence": evidence[:12],
        "traditional_directional_analysis": _traditional_directional_analysis(features),
        "source_basis": [
            "special_degrees_require_relevant_significator_or_angle",
            "asteroids_require_tight_conjunction_to_relevant_point",
            "mcintosh_role_gated_patterns",
            "mcintosh_traditional_direction_mapping",
        ],
    }
