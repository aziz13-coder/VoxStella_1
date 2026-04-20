"""Reception dashboard computation for Astro Clock.

This module computes a compact, JSON‑friendly summary of receptions using
the existing horary engine helpers without modifying the engine itself.

It intentionally lives outside the engine package to respect the constraint
that new calculations for the Astro Clock should be in separate files.
"""

from typing import Any, Dict, List, Tuple

from horary_engine.serialization import deserialize_chart_for_evaluation
from horary_engine.reception import TraditionalReceptionCalculator
from models import Planet


CLASSICAL_PLANETS: Tuple[Planet, ...] = (
    Planet.SUN,
    Planet.MOON,
    Planet.MERCURY,
    Planet.VENUS,
    Planet.MARS,
    Planet.JUPITER,
    Planet.SATURN,
)


def _safe_chart_data(obj: Any) -> Dict[str, Any]:
    """Return a dict chart_data object; accept dict or JSON‑serializable dict‑like."""
    if isinstance(obj, dict):
        return obj
    try:
        import json

        return json.loads(obj) if isinstance(obj, str) else {}
    except Exception:
        return {}


def compute_reception_dashboard(chart_data: Any) -> Dict[str, Any]:
    """Compute mutual and unilateral receptions summary from serialized chart_data.

    Args:
        chart_data: The "chart_data" dict produced by the engine's
                    serialize_chart_for_frontend, or a JSON string.

    Returns:
        Dict with keys:
          - mutual: list of { p1, p2, type, strength, p1_dignities, p2_dignities, display }
          - top_unilateral: list of { receiving, received, dignities, strength, display }
    """
    cd = _safe_chart_data(chart_data)
    # Sanitize to classical planets only (Sun..Saturn) across all relevant fields
    try:
        allowed = {p.value for p in CLASSICAL_PLANETS}
        # planets dict
        pls = cd.get('planets')
        if isinstance(pls, dict):
            cd = dict(cd)  # shallow copy
            cd['planets'] = {k: v for k, v in pls.items() if isinstance(k, str) and k in allowed}
        elif isinstance(pls, list):
            cd = dict(cd)
            filtered = {}
            for p in pls:
                if not isinstance(p, dict):
                    continue
                nm = p.get('planet') or p.get('name')
                if nm in allowed:
                    # strip name key to match serializer dict shape
                    info = dict(p)
                    info.pop('planet', None)
                    info.pop('name', None)
                    filtered[nm] = info
            cd['planets'] = filtered
        # aspects list (optional); drop aspects that involve non-classical bodies
        if isinstance(cd.get('aspects'), list):
            cd['aspects'] = [
                a for a in cd['aspects']
                if isinstance(a, dict)
                and a.get('planet1') in allowed
                and a.get('planet2') in allowed
            ]
        # moon last/next aspects (optional)
        if isinstance(cd.get('moon_last_aspect'), dict):
            if cd['moon_last_aspect'].get('planet') not in allowed:
                cd.pop('moon_last_aspect', None)
        if isinstance(cd.get('moon_next_aspect'), dict):
            if cd['moon_next_aspect'].get('planet') not in allowed:
                cd.pop('moon_next_aspect', None)
        # house_rulers dictionary: keep entries whose ruler is classical
        if isinstance(cd.get('house_rulers'), dict):
            cd['house_rulers'] = {
                str(h): r for h, r in cd['house_rulers'].items()
                if isinstance(r, str) and r in allowed
            }
    except Exception:
        # Defensive: if sanitation fails, fall back to raw (engine may still parse)
        pass
    chart = deserialize_chart_for_evaluation(cd)
    calc = TraditionalReceptionCalculator()

    # Mutual receptions (unique unordered pairs)
    mutual: List[Dict[str, Any]] = []
    for i in range(len(CLASSICAL_PLANETS)):
        for j in range(i + 1, len(CLASSICAL_PLANETS)):
            a = CLASSICAL_PLANETS[i]
            b = CLASSICAL_PLANETS[j]
            try:
                m = calc.get_mutual_reception_only(chart, a, b)
                if m.get("has_mutual_reception"):
                    mutual.append(
                        {
                            "p1": a.value,
                            "p2": b.value,
                            "type": m.get("mutual_type"),
                            "strength": int(m.get("mutual_strength", 0)),
                            "p1_dignities": list(m.get("planet1_dignities", [])),
                            "p2_dignities": list(m.get("planet2_dignities", [])),
                            "display": m.get("display_text"),
                        }
                    )
            except Exception:
                # Defensive: skip any pair that fails
                continue

    # Sort mutual by strength desc, then by type name
    mutual.sort(key=lambda x: (x.get("strength", 0), str(x.get("type") or "")), reverse=True)

    # Unilateral receptions (ordered pairs). Exclude pairs that are mutual to avoid duplication.
    mutual_pairs = {(m["p1"], m["p2"]) for m in mutual} | {(m["p2"], m["p1"]) for m in mutual}
    unilateral: List[Dict[str, Any]] = []
    for a in CLASSICAL_PLANETS:
        for b in CLASSICAL_PLANETS:
            if a == b:
                continue
            if (a.value, b.value) in mutual_pairs:
                # Skip directions that belong to a mutual reception
                continue
            try:
                d = calc.does_planet_receive(chart, a, b)
                if d.get("has_reception"):
                    unilateral.append(
                        {
                            "receiving": a.value,
                            "received": b.value,
                            "dignities": list(d.get("dignities", [])),
                            "strength": int(d.get("reception_strength", 0)),
                            "display": d.get("display_text"),
                        }
                    )
            except Exception:
                continue

    unilateral.sort(key=lambda x: (x.get("strength", 0), len(x.get("dignities", []))), reverse=True)
    top_unilateral = unilateral[:10]

    return {"mutual": mutual, "top_unilateral": top_unilateral}
