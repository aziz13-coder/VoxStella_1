from __future__ import annotations

from typing import Any, Dict, List, Optional


_MOON_DAY_MARKERS: List[int] = [
    0,
    30,
    36,
    40,
    45,
    51,
    60,
    72,
    80,
    90,
    103,
    108,
    120,
    135,
    144,
    150,
    154,
    160,
    180,
]


def _wrap360(value: float) -> float:
    return float(value) % 360.0


def _planet_longitude(chart_data: Dict[str, Any], name: str) -> Optional[float]:
    planets = chart_data.get("planets")
    if isinstance(planets, dict):
        row = planets.get(name)
        if isinstance(row, dict) and row.get("longitude") is not None:
            try:
                return _wrap360(float(row.get("longitude")))
            except Exception:
                return None
    elif isinstance(planets, list):
        for row in planets:
            if not isinstance(row, dict):
                continue
            row_name = str(row.get("planet") or row.get("name") or "").strip()
            if row_name != name or row.get("longitude") is None:
                continue
            try:
                return _wrap360(float(row.get("longitude")))
            except Exception:
                return None
    return None


def _phase_interval_for_nid(nid: int) -> tuple[float, float]:
    if nid <= 15:
        start = max(0.0, float(nid - 1) * 12.0)
        end = min(180.0, float(nid) * 12.0)
        return start, end
    start = max(0.0, 360.0 - (float(nid) * 12.0))
    end = min(180.0, 360.0 - (float(nid - 1) * 12.0))
    return min(start, end), max(start, end)


def _interval_tags(start: float, end: float) -> List[str]:
    tags: List[str] = []
    for marker in _MOON_DAY_MARKERS:
        if float(marker) < start:
            continue
        if float(marker) >= end and not (marker == 180 and end >= 180.0):
            continue
        tags.append(f"{int(marker):03d}")
    return tags


def compute_moon_day(chart_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Approximate Galaxy moon-day intervals from the current Sun/Moon elongation.

    The repo does not contain Galaxy's original `moondaywork.GetMoonDays(...)`
    utility. This helper uses a lunation-angle proxy:

    - lunar day number is derived from 30 equal 12-degree lunation slices
    - the interval tag list is built from the same marker set Galaxy uses
    - the mirrored 0..180 phase interval preserves the first-half/second-half
      polarity that the marriage branch consumes
    """

    sun_lon = _planet_longitude(chart_data, "Sun")
    moon_lon = _planet_longitude(chart_data, "Moon")
    if sun_lon is None or moon_lon is None:
        return None

    elongation = _wrap360(moon_lon - sun_lon)
    nid = max(1, min(30, int(elongation // 12.0) + 1))
    phase_start, phase_end = _phase_interval_for_nid(nid)
    tags = _interval_tags(phase_start, phase_end)

    return {
        "nid": nid,
        "elongation_deg": round(elongation, 3),
        "lunation_half": "first" if nid <= 16 else "second",
        "phase_interval_deg": [round(phase_start, 3), round(phase_end, 3)],
        "interval_tags": tags,
        "tag_string": "/".join(tags),
        "source": "lunation_angle_proxy",
        "galaxy_mode": "marriage_interval_tags",
        "is_proxy": True,
    }


__all__ = ["compute_moon_day"]
