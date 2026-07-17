from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .tables import (
    BRANCHES,
    BRANCH_INDEX,
    ELEMENTS,
    FIRST_HOUR_STEM_BY_DAY_STEM,
    FIRST_MONTH_STEM_BY_YEAR_STEM,
    MONTH_BRANCH_INDICES,
    STEM_INDEX,
    STEMS,
    ten_god,
)
from .auxiliary_stars import build_auxiliary_stars
from .curation import confidence_tags, curation_summary, rule_notes_for_areas
from .life_areas import build_life_areas
from .palaces import build_palace_context
from .relationships import analyze_relationships
from .interpretation import build_interpretation, build_ten_god_profile, build_useful_element_recommendations
from .strength import evaluate_day_master_strength
from .timing_rhythm import build_timing_rhythm

from swisseph_state import swisseph as swe, swisseph_lock


@dataclass(frozen=True)
class BirthContext:
    dt_utc: datetime
    timezone: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    time_precision: str = "exact"
    source: str = "direct_input"
    source_snap_id: Optional[str] = None
    snap_label: Optional[str] = None
    calculation_sex: Optional[str] = None
    include_luck_pillars: bool = False
    use_true_solar_time: bool = False
    day_boundary_rule: str = "civil_midnight"
    hour_pillar_variant: str = "standard_zi_hour"
    luck_direction_rule: str = "year_stem_polarity"
    hour_known: bool = True
    missing_inputs: Tuple[Dict[str, str], ...] = ()


SOLAR_TERMS = (
    {"key": "xiao_han", "name": "Xiao Han", "longitude": 285.0, "month": 1, "day": 5, "month_index": 11},
    {"key": "li_chun", "name": "Li Chun", "longitude": 315.0, "month": 2, "day": 4, "month_index": 0},
    {"key": "jing_zhe", "name": "Jing Zhe", "longitude": 345.0, "month": 3, "day": 5, "month_index": 1},
    {"key": "qing_ming", "name": "Qing Ming", "longitude": 15.0, "month": 4, "day": 4, "month_index": 2},
    {"key": "li_xia", "name": "Li Xia", "longitude": 45.0, "month": 5, "day": 5, "month_index": 3},
    {"key": "mang_zhong", "name": "Mang Zhong", "longitude": 75.0, "month": 6, "day": 5, "month_index": 4},
    {"key": "xiao_shu", "name": "Xiao Shu", "longitude": 105.0, "month": 7, "day": 7, "month_index": 5},
    {"key": "li_qiu", "name": "Li Qiu", "longitude": 135.0, "month": 8, "day": 7, "month_index": 6},
    {"key": "bai_lu", "name": "Bai Lu", "longitude": 165.0, "month": 9, "day": 7, "month_index": 7},
    {"key": "han_lu", "name": "Han Lu", "longitude": 195.0, "month": 10, "day": 8, "month_index": 8},
    {"key": "li_dong", "name": "Li Dong", "longitude": 225.0, "month": 11, "day": 7, "month_index": 9},
    {"key": "da_xue", "name": "Da Xue", "longitude": 255.0, "month": 12, "day": 7, "month_index": 10},
)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _localize(value: datetime, timezone_name: str) -> datetime:
    try:
        return _ensure_utc(value).astimezone(ZoneInfo(timezone_name))
    except Exception:
        return _ensure_utc(value).astimezone(timezone.utc)


def _julian_day_number(day: date) -> int:
    a = (14 - day.month) // 12
    y = day.year + 4800 - a
    m = day.month + 12 * a - 3
    return day.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def sexagenary_day_index(day: date) -> int:
    return (_julian_day_number(day) + 49) % 60


def _angle_delta(longitude: float, target: float) -> float:
    return ((float(longitude) - float(target) + 180.0) % 360.0) - 180.0


def _solar_longitude(dt_utc: datetime) -> float:
    if swe is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")
    dt = _ensure_utc(dt_utc)
    hour = dt.hour + (dt.minute / 60.0) + (dt.second / 3600.0) + (dt.microsecond / 3600000000.0)
    jd_ut = swe.julday(dt.year, dt.month, dt.day, hour, getattr(swe, "GREG_CAL", 1))
    flags = getattr(swe, "FLG_SWIEPH", 2)
    try:
        lock = swisseph_lock
    except Exception:
        lock = None
    if callable(lock):
        with lock():
            pos, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    elif lock is None:
        pos, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    else:
        with lock:
            pos, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    return float(pos[0]) % 360.0


@lru_cache(maxsize=256)
def _term_crossing_utc(year: int, term_key: str) -> Tuple[datetime, str]:
    term = next(item for item in SOLAR_TERMS if item["key"] == term_key)
    approx = datetime(int(year), int(term["month"]), int(term["day"]), 0, 0, tzinfo=timezone.utc)
    if swe is None:
        return approx, "fixed_approximation"

    target = float(term["longitude"])
    lo = approx - timedelta(days=6)
    hi = approx + timedelta(days=6)
    try:
        for _ in range(4):
            if _angle_delta(_solar_longitude(lo), target) <= 0 <= _angle_delta(_solar_longitude(hi), target):
                break
            lo -= timedelta(days=3)
            hi += timedelta(days=3)
        for _ in range(48):
            mid = lo + ((hi - lo) / 2)
            if _angle_delta(_solar_longitude(mid), target) < 0:
                lo = mid
            else:
                hi = mid
        return hi, "swiss_ephemeris"
    except Exception:
        return approx, "fixed_approximation"


def _term_payload(year: int, term: Dict[str, Any]) -> Dict[str, Any]:
    crossing, source = _term_crossing_utc(int(year), str(term["key"]))
    return {
        "key": term["key"],
        "name": term["name"],
        "longitude": term["longitude"],
        "month_index": term["month_index"],
        "datetime_utc": crossing,
        "source": source,
    }


def _terms_around(dt_utc: datetime) -> List[Dict[str, Any]]:
    year = _ensure_utc(dt_utc).year
    terms: List[Dict[str, Any]] = []
    for term_year in (year - 1, year, year + 1):
        for term in SOLAR_TERMS:
            terms.append(_term_payload(term_year, term))
    terms.sort(key=lambda item: item["datetime_utc"])
    return terms


def _li_chun_for_year(year: int) -> Dict[str, Any]:
    return _term_payload(year, next(term for term in SOLAR_TERMS if term["key"] == "li_chun"))


def _year_pillar_index(dt_utc: datetime) -> Tuple[int, int, Dict[str, Any]]:
    dt = _ensure_utc(dt_utc)
    li_chun = _li_chun_for_year(dt.year)
    bazi_year = dt.year if dt >= li_chun["datetime_utc"] else dt.year - 1
    return (bazi_year - 1984) % 60, bazi_year, li_chun


def _month_pillar_indices(dt_utc: datetime, year_stem_index: int) -> Tuple[int, int, Dict[str, Any]]:
    dt = _ensure_utc(dt_utc)
    latest = None
    for term in _terms_around(dt):
        if term["datetime_utc"] <= dt:
            latest = term
        else:
            break
    if latest is None:
        latest = _terms_around(dt)[0]
    month_index = int(latest["month_index"])
    first_stem = FIRST_MONTH_STEM_BY_YEAR_STEM[int(year_stem_index) % 10]
    stem_index = (first_stem + month_index) % 10
    branch_index = MONTH_BRANCH_INDICES[month_index]
    return stem_index, branch_index, latest


def _adjacent_solar_term(dt_utc: datetime, direction: str) -> Optional[Dict[str, Any]]:
    dt = _ensure_utc(dt_utc)
    terms = _terms_around(dt)
    if direction == "forward":
        return next((term for term in terms if term["datetime_utc"] > dt), None)
    return next((term for term in reversed(terms) if term["datetime_utc"] < dt), None)


def _hour_pillar_indices(local_dt: datetime, day_stem_index: int) -> Tuple[int, int]:
    branch_index = ((int(local_dt.hour) + 1) // 2) % 12
    first_stem = FIRST_HOUR_STEM_BY_DAY_STEM[int(day_stem_index) % 10]
    stem_index = (first_stem + branch_index) % 10
    return stem_index, branch_index


def _equation_of_time_minutes(local_dt: datetime) -> float:
    day_of_year = int(local_dt.timetuple().tm_yday)
    days_in_year = 366 if calendar.isleap(int(local_dt.year)) else 365
    hour = (
        int(local_dt.hour)
        + (int(local_dt.minute) / 60.0)
        + (int(local_dt.second) / 3600.0)
        + (int(local_dt.microsecond) / 3600000000.0)
    )
    gamma = (2.0 * math.pi / float(days_in_year)) * (day_of_year - 1 + ((hour - 12.0) / 24.0))
    return 229.18 * (
        0.000075
        + (0.001868 * math.cos(gamma))
        - (0.032077 * math.sin(gamma))
        - (0.014615 * math.cos(2.0 * gamma))
        - (0.040849 * math.sin(2.0 * gamma))
    )


def _true_solar_conversion(local_dt: datetime, longitude: Optional[float]) -> Optional[Dict[str, Any]]:
    if longitude is None:
        return None
    offset = local_dt.utcoffset() or timedelta(0)
    timezone_offset_hours = offset.total_seconds() / 3600.0
    standard_meridian = timezone_offset_hours * 15.0
    equation = _equation_of_time_minutes(local_dt)
    longitude_correction = (4.0 * float(longitude)) - (60.0 * timezone_offset_hours)
    total_correction = equation + longitude_correction
    true_solar_dt = local_dt + timedelta(minutes=total_correction)
    return {
        "local_datetime": true_solar_dt,
        "equation_of_time_minutes": round(equation, 2),
        "longitude_correction_minutes": round(longitude_correction, 2),
        "total_correction_minutes": round(total_correction, 2),
        "timezone_offset_hours": round(timezone_offset_hours, 4),
        "standard_meridian": round(standard_meridian, 4),
        "longitude": round(float(longitude), 6),
        "method": "NOAA fractional-year equation of time plus longitude correction",
    }


def _minutes_to_hour_branch_boundary(local_dt: datetime) -> float:
    minute = (
        int(local_dt.hour) * 60.0
        + int(local_dt.minute)
        + (int(local_dt.second) / 60.0)
        + (int(local_dt.microsecond) / 60000000.0)
    )
    boundaries = [(23 * 60.0)] + [float(hour * 60) for hour in range(1, 24, 2)]
    return min(abs(((minute - boundary + 720.0) % 1440.0) - 720.0) for boundary in boundaries)


def _stem_payload(stem_index: int, day_stem_index: Optional[int] = None) -> Dict[str, Any]:
    idx = int(stem_index) % 10
    stem = STEMS[idx]
    payload = {
        "key": stem["key"],
        "index": idx,
        "element": stem["element"],
        "polarity": stem["polarity"],
    }
    if day_stem_index is not None:
        payload.update(ten_god(day_stem_index, idx))
    return payload


def _branch_payload(branch_index: int, day_stem_index: Optional[int] = None) -> Dict[str, Any]:
    idx = int(branch_index) % 12
    branch = BRANCHES[idx]
    hidden = []
    for rank, stem_key in enumerate(branch["hidden_stems"]):
        stem_idx = STEM_INDEX[stem_key]
        item = _stem_payload(stem_idx, day_stem_index)
        item["rank"] = rank + 1
        hidden.append(item)
    return {
        "key": branch["key"],
        "index": idx,
        "animal": branch["animal"],
        "element": branch["element"],
        "polarity": branch["polarity"],
        "hidden_stems": hidden,
    }


def _pillar_payload(name: str, stem_index: int, branch_index: int, day_stem_index: Optional[int]) -> Dict[str, Any]:
    stem = _stem_payload(stem_index, day_stem_index)
    branch = _branch_payload(branch_index, day_stem_index)
    stem_ten_god = "Day Master" if name == "day" else stem.get("god")
    stem_factor = "Self" if name == "day" else stem.get("factor")
    return {
        "name": name,
        "stem": stem["key"],
        "branch": branch["key"],
        "stem_index": stem["index"],
        "branch_index": branch["index"],
        "animal": branch["animal"],
        "stem_element": stem["element"],
        "branch_element": branch["element"],
        "stem_polarity": stem["polarity"],
        "branch_polarity": branch["polarity"],
        "ten_god": stem_ten_god,
        "five_factor": stem_factor,
        "hidden_stems": branch["hidden_stems"],
    }


def _element_balance(pillars: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    visible = {element: 0 for element in ELEMENTS}
    branches = {element: 0 for element in ELEMENTS}
    hidden = {element: 0 for element in ELEMENTS}
    for pillar in pillars.values():
        if not pillar:
            continue
        visible[pillar["stem_element"]] += 1
        branches[pillar["branch_element"]] += 1
        for hidden_stem in pillar.get("hidden_stems") or []:
            hidden[hidden_stem["element"]] += 1
    total = {
        element: visible[element] + branches[element] + hidden[element]
        for element in ELEMENTS
    }
    return {
        "visible_stems": visible,
        "branches": branches,
        "hidden_stems": hidden,
        "total": total,
    }


NA_YIN_BY_PAIR = {
    ("Jia", "Zi"): "Sea Gold", ("Yi", "Chou"): "Sea Gold",
    ("Bing", "Yin"): "Furnace Fire", ("Ding", "Mao"): "Furnace Fire",
    ("Wu", "Chen"): "Great Forest Wood", ("Ji", "Si"): "Great Forest Wood",
    ("Geng", "Wu"): "Roadside Earth", ("Xin", "Wei"): "Roadside Earth",
    ("Ren", "Shen"): "Sword-edge Metal", ("Gui", "You"): "Sword-edge Metal",
    ("Jia", "Xu"): "Mountain-top Fire", ("Yi", "Hai"): "Mountain-top Fire",
    ("Bing", "Zi"): "Stream Water", ("Ding", "Chou"): "Stream Water",
    ("Wu", "Yin"): "City Wall Earth", ("Ji", "Mao"): "City Wall Earth",
    ("Geng", "Chen"): "White Wax Metal", ("Xin", "Si"): "White Wax Metal",
    ("Ren", "Wu"): "Willow Wood", ("Gui", "Wei"): "Willow Wood",
    ("Jia", "Shen"): "Spring Water", ("Yi", "You"): "Spring Water",
    ("Bing", "Xu"): "House-top Earth", ("Ding", "Hai"): "House-top Earth",
    ("Wu", "Zi"): "Thunder Fire", ("Ji", "Chou"): "Thunder Fire",
    ("Geng", "Yin"): "Pine-Cypress Wood", ("Xin", "Mao"): "Pine-Cypress Wood",
    ("Ren", "Chen"): "Long-flowing Water", ("Gui", "Si"): "Long-flowing Water",
    ("Jia", "Wu"): "Sand Gold", ("Yi", "Wei"): "Sand Gold",
    ("Bing", "Shen"): "Mountain Fire", ("Ding", "You"): "Mountain Fire",
    ("Wu", "Xu"): "Plain Wood", ("Ji", "Hai"): "Plain Wood",
    ("Geng", "Zi"): "Wall Earth", ("Xin", "Chou"): "Wall Earth",
    ("Ren", "Yin"): "Gold Foil", ("Gui", "Mao"): "Gold Foil",
    ("Jia", "Chen"): "Lamp Fire", ("Yi", "Si"): "Lamp Fire",
    ("Bing", "Wu"): "Heavenly River Water", ("Ding", "Wei"): "Heavenly River Water",
    ("Wu", "Shen"): "Great Post Earth", ("Ji", "You"): "Great Post Earth",
    ("Geng", "Xu"): "Ornament Gold", ("Xin", "Hai"): "Ornament Gold",
    ("Ren", "Zi"): "Mulberry Wood", ("Gui", "Chou"): "Mulberry Wood",
    ("Jia", "Yin"): "Great Stream Water", ("Yi", "Mao"): "Great Stream Water",
    ("Bing", "Chen"): "Sand Earth", ("Ding", "Si"): "Sand Earth",
    ("Wu", "Wu"): "Heavenly Fire", ("Ji", "Wei"): "Heavenly Fire",
    ("Geng", "Shen"): "Pomegranate Wood", ("Xin", "You"): "Pomegranate Wood",
    ("Ren", "Xu"): "Great Sea Water", ("Gui", "Hai"): "Great Sea Water",
}


def _na_yin_payload(pillar_name: str, pillar: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(pillar, dict):
        return None
    stem = str(pillar.get("stem") or "")
    branch = str(pillar.get("branch") or "")
    return {
        "pillar": pillar_name,
        "stem": stem,
        "branch": branch,
        "na_yin": NA_YIN_BY_PAIR.get((stem, branch)),
        "status": "available" if (stem, branch) in NA_YIN_BY_PAIR else "unavailable",
    }


def _tai_yuan_payload(
    month_stem_index: int,
    month_branch_index: int,
    day_stem_index: int,
) -> Dict[str, Any]:
    stem_index = (int(month_stem_index) + 1) % 10
    branch_index = (int(month_branch_index) + 3) % 12
    pillar = _pillar_payload("tai_yuan", stem_index, branch_index, day_stem_index)
    return {
        "status": "source_based_preview",
        "method": "month_stem_plus_one_branch_plus_three_v1",
        "pillar": pillar,
        "summary": f"Tai Yuan is calculated from the month pillar as {pillar['stem']} {pillar['branch']}.",
        "source_page_refs": ["lu_zhiji_fate_search:p98", "sanming_tonghui_part3:pp263-266"],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _ming_gong_payload(
    month_branch_index: int,
    hour_branch_index: Optional[int],
    year_stem_index: int,
    day_stem_index: int,
) -> Dict[str, Any]:
    if hour_branch_index is None:
        return {
            "status": "withheld",
            "method": "month_hour_branch_variant_v1",
            "reason": "Ming Gong requires a known hour branch.",
            "source_page_refs": ["lu_zhiji_fate_search:p381"],
            "source_confidence": confidence_tags("local_source", "provisional_model", "school_variant"),
        }
    month_number = ((int(month_branch_index) - BRANCH_INDEX["Yin"]) % 12) + 1
    hour_number = (int(hour_branch_index) % 12) + 1
    branch_number = (14 - month_number - hour_number) % 12
    branch_index = (branch_number - 1) % 12
    first_stem = FIRST_MONTH_STEM_BY_YEAR_STEM[int(year_stem_index) % 10]
    stem_index = (first_stem + ((branch_index - BRANCH_INDEX["Yin"]) % 12)) % 10
    pillar = _pillar_payload("ming_gong", stem_index, branch_index, day_stem_index)
    return {
        "status": "school_variant_preview",
        "method": "month_hour_reverse_count_variant_v1",
        "pillar": pillar,
        "summary": f"Ming Gong is shown as a classical extra using a month-hour reverse-count variant: {pillar['stem']} {pillar['branch']}.",
        "source_page_refs": ["lu_zhiji_fate_search:p381"],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _classical_extras_payload(
    *,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    month_stem_index: int,
    month_branch_index: int,
    year_stem_index: int,
    day_stem_index: int,
    hour_pair: Optional[Tuple[int, int]],
) -> Dict[str, Any]:
    na_yin_rows = [
        row for row in (
            _na_yin_payload(name, pillars.get(name))
            for name in ("year", "month", "day", "hour")
        )
        if row
    ]
    return {
        "status": "source_based_preview",
        "method": "classical_extras_v1",
        "tai_yuan": _tai_yuan_payload(month_stem_index, month_branch_index, day_stem_index),
        "ming_gong": _ming_gong_payload(
            month_branch_index,
            hour_pair[1] if hour_pair else None,
            year_stem_index,
            day_stem_index,
        ),
        "na_yin": {
            "status": "source_based_preview",
            "method": "sixty_jiazi_na_yin_table_v1",
            "pillars": na_yin_rows,
            "summary": "Na Yin is exposed as a secondary classical layer and is not used to override main BaZi logic.",
        },
        "notes": [
            "Tai Yuan, Ming Gong, and Na Yin are classical extras for comparison only.",
            "Main strength, structure, useful-element, timing, and relationship logic remain primary.",
        ],
        "source_page_refs": [
            "lu_zhiji_fate_search:p98",
            "lu_zhiji_fate_search:p381",
            "sanming_tonghui_part3:pp263-266",
            "lu_zhiji_fate_search:pp122-124",
        ],
        "source_confidence": confidence_tags("local_source", "computed_rule", "school_variant"),
    }


def _ten_god_rows(pillars: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    visible: List[Dict[str, Any]] = []
    hidden: List[Dict[str, Any]] = []
    for pillar_name, pillar in pillars.items():
        if not pillar:
            continue
        if pillar.get("ten_god") and pillar.get("five_factor") != "Self":
            visible.append({
                "pillar": pillar_name,
                "stem": pillar["stem"],
                "factor": pillar.get("five_factor"),
                "factor_chinese": pillar.get("factor_chinese"),
                "factor_pinyin": pillar.get("factor_pinyin"),
                "relation_chinese": pillar.get("relation_chinese"),
                "relation_label": pillar.get("relation_label"),
                "god": pillar.get("ten_god"),
                "god_chinese": pillar.get("god_chinese"),
                "god_pinyin": pillar.get("god_pinyin"),
                "polarity_relation": pillar.get("polarity_relation"),
            })
        for hidden_stem in pillar.get("hidden_stems") or []:
            hidden.append({
                "pillar": pillar_name,
                "stem": hidden_stem["key"],
                "rank": hidden_stem.get("rank"),
                "factor": hidden_stem.get("factor"),
                "factor_chinese": hidden_stem.get("factor_chinese"),
                "factor_pinyin": hidden_stem.get("factor_pinyin"),
                "relation_chinese": hidden_stem.get("relation_chinese"),
                "relation_label": hidden_stem.get("relation_label"),
                "god": hidden_stem.get("god"),
                "god_chinese": hidden_stem.get("god_chinese"),
                "god_pinyin": hidden_stem.get("god_pinyin"),
                "polarity_relation": hidden_stem.get("polarity_relation"),
            })
    return {"visible": visible, "hidden": hidden}


def _strength_evidence(
    day_stem_index: int,
    pillars: Dict[str, Optional[Dict[str, Any]]],
    balance: Dict[str, Any],
) -> Dict[str, Any]:
    return evaluate_day_master_strength(day_stem_index, pillars, balance)


def _normalize_calculation_sex(value: Optional[str]) -> Optional[str]:
    raw = str(value or "").strip().lower()
    if raw in {"m", "male", "man", "masculine", "yang"}:
        return "male"
    if raw in {"f", "female", "woman", "feminine", "yin"}:
        return "female"
    return None


def _normalize_day_boundary_rule(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if raw in {"true_solar", "true_solar_midnight", "true_solar_date", "solar_midnight", "solar_day"}:
        return "true_solar_midnight"
    return "civil_midnight"


def _normalize_hour_pillar_variant(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if raw in {"late_zi", "late_zi_next_day", "zi_next_day", "next_day_zi", "23_next_day"}:
        return "late_zi_next_day"
    return "standard_zi_hour"


def _normalize_luck_direction_rule(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if raw in {"year_branch", "year_branch_polarity", "branch_polarity"}:
        return "year_branch_polarity"
    if raw in {"day_stem", "day_stem_polarity", "day_master", "day_master_polarity"}:
        return "day_stem_polarity"
    return "year_stem_polarity"


def _format_start_age(age_years: float) -> str:
    total_months = max(0, int(round(float(age_years) * 12)))
    years, months = divmod(total_months, 12)
    if years and months:
        return f"{years}y {months}m"
    if years:
        return f"{years}y"
    return f"{months}m"


def _sexagenary_index_for_pair(stem_index: int, branch_index: int) -> int:
    stem = int(stem_index) % 10
    branch = int(branch_index) % 12
    for idx in range(60):
        if idx % 10 == stem and idx % 12 == branch:
            return idx
    return stem


def _luck_direction(
    year_stem_index: int,
    year_branch_index: int,
    day_stem_index: int,
    calculation_sex: Optional[str],
    rule: Optional[str],
) -> Optional[Dict[str, Any]]:
    sex = _normalize_calculation_sex(calculation_sex)
    if not sex:
        return None
    year_stem = STEMS[int(year_stem_index) % 10]
    year_branch = BRANCHES[int(year_branch_index) % 12]
    day_stem = STEMS[int(day_stem_index) % 10]
    rule_key = _normalize_luck_direction_rule(rule)
    if rule_key == "year_branch_polarity":
        polarity_source = "year_branch"
        polarity_symbol = year_branch["key"]
        selected_polarity = year_branch["polarity"]
        rule_text = "yang year-branch male / yin year-branch female forward; opposite combinations reverse"
    elif rule_key == "day_stem_polarity":
        polarity_source = "day_stem"
        polarity_symbol = day_stem["key"]
        selected_polarity = day_stem["polarity"]
        rule_text = "yang Day Master male / yin Day Master female forward; opposite combinations reverse"
    else:
        polarity_source = "year_stem"
        polarity_symbol = year_stem["key"]
        selected_polarity = year_stem["polarity"]
        rule_text = "yang-year male / yin-year female forward; yin-year male / yang-year female reverse"

    forward = (sex == "male" and selected_polarity == "yang") or (sex == "female" and selected_polarity == "yin")
    return {
        "direction": "forward" if forward else "reverse",
        "step": 1 if forward else -1,
        "calculation_sex": sex,
        "rule_key": rule_key,
        "polarity_source": polarity_source,
        "polarity_symbol": polarity_symbol,
        "selected_polarity": selected_polarity,
        "year_stem": year_stem["key"],
        "year_stem_polarity": year_stem["polarity"],
        "year_branch": year_branch["key"],
        "year_branch_polarity": year_branch["polarity"],
        "day_stem": day_stem["key"],
        "day_stem_polarity": day_stem["polarity"],
        "rule": rule_text,
    }


def _annual_pillar_payload(reference_dt_utc: datetime, day_stem_index: int) -> Dict[str, Any]:
    annual_index, bazi_year, li_chun = _year_pillar_index(reference_dt_utc)
    pillar = _pillar_payload("annual", annual_index % 10, annual_index % 12, day_stem_index)
    return {
        **pillar,
        "sexagenary_index": annual_index,
        "bazi_year": bazi_year,
        "calendar_year": _ensure_utc(reference_dt_utc).year,
        "year_boundary": _serialize_term(li_chun),
    }


def _flowing_pillars_payload(reference_dt_utc: datetime, timezone_name: str, day_stem_index: int) -> Dict[str, Any]:
    reference_dt = _ensure_utc(reference_dt_utc)
    reference_local = _localize(reference_dt, timezone_name or "UTC")
    annual_index, _, _ = _year_pillar_index(reference_dt)
    month_stem_index, month_branch_index, month_term = _month_pillar_indices(reference_dt, annual_index % 10)
    day_index = sexagenary_day_index(reference_local.date())
    hour_stem_index, hour_branch_index = _hour_pillar_indices(reference_local, day_index % 10)
    month = _pillar_payload("flowing_month", month_stem_index, month_branch_index, day_stem_index)
    day = _pillar_payload("flowing_day", day_index % 10, day_index % 12, day_stem_index)
    hour = _pillar_payload("flowing_hour", hour_stem_index, hour_branch_index, day_stem_index)
    return {
        "reference_datetime_utc": reference_dt.isoformat(),
        "reference_local_datetime": reference_local.isoformat(),
        "flowing_month_pillar": {
            **month,
            "period": {
                "solar_term": _serialize_term(month_term),
                "calendar_year": reference_local.year,
                "calendar_month": reference_local.month,
            },
        },
        "flowing_day_pillar": {
            **day,
            "sexagenary_index": day_index,
            "period": {
                "local_date": reference_local.date().isoformat(),
            },
        },
        "flowing_hour_pillar": {
            **hour,
            "period": {
                "local_datetime": reference_local.isoformat(),
                "hour_branch": hour.get("branch"),
            },
        },
    }


def _luck_pillar_timing(
    context: BirthContext,
    *,
    dt_utc: datetime,
    local_dt: datetime,
    year_stem_index: int,
    year_branch_index: int,
    month_stem_index: int,
    month_branch_index: int,
    day_stem_index: int,
    reference_dt_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    reference_dt = _ensure_utc(reference_dt_utc or datetime.now(timezone.utc))
    annual = _annual_pillar_payload(reference_dt, day_stem_index)
    flowing = _flowing_pillars_payload(reference_dt, context.timezone or "UTC", day_stem_index)
    wants_luck = bool(context.include_luck_pillars or context.calculation_sex)
    luck_direction_rule = _normalize_luck_direction_rule(context.luck_direction_rule)
    direction = _luck_direction(
        year_stem_index,
        year_branch_index,
        day_stem_index,
        context.calculation_sex,
        luck_direction_rule,
    )

    if not wants_luck:
        return {
            "luck_pillars_enabled": False,
            "annual_pillar": annual,
            **flowing,
            "luck_pillars": [],
            "active_luck_pillar": None,
            "debug": {
                "method": "luck_pillars_not_requested",
            },
        }

    if direction is None:
        return {
            "luck_pillars_enabled": False,
            "annual_pillar": annual,
            **flowing,
            "luck_pillars": [],
            "active_luck_pillar": None,
            "debug": {
                "method": "luck_pillars_require_calculation_sex",
                "direction_rule": "year-stem polarity plus calculation sex",
                "direction_rule_key": luck_direction_rule,
            },
        }

    solar_term = _adjacent_solar_term(dt_utc, direction["direction"])
    if solar_term is None:
        return {
            "luck_pillars_enabled": False,
            "annual_pillar": annual,
            **flowing,
            "luck_pillars": [],
            "active_luck_pillar": None,
            "debug": {
                "method": "solar_term_lookup_failed",
                "direction": direction["direction"],
                "direction_rule": direction["rule"],
            },
        }

    distance = abs(solar_term["datetime_utc"] - dt_utc)
    distance_days = distance.total_seconds() / 86400.0
    start_age_years = distance_days / 3.0
    start_date = local_dt + timedelta(days=start_age_years * 365.2425)
    step = int(direction["step"])
    sequence: List[Dict[str, Any]] = []
    for idx in range(10):
        stem_index = (int(month_stem_index) + (step * (idx + 1))) % 10
        branch_index = (int(month_branch_index) + (step * (idx + 1))) % 12
        period_start = start_date + timedelta(days=idx * 3652.425)
        period_end = start_date + timedelta(days=(idx + 1) * 3652.425)
        age_start = start_age_years + (idx * 10)
        age_end = start_age_years + ((idx + 1) * 10)
        pillar = _pillar_payload("luck", stem_index, branch_index, day_stem_index)
        sequence.append({
            **pillar,
            "sequence": idx + 1,
            "sexagenary_index": _sexagenary_index_for_pair(stem_index, branch_index),
            "age_start": round(age_start, 2),
            "age_end": round(age_end, 2),
            "age_label": f"{_format_start_age(age_start)} - {_format_start_age(age_end)}",
            "calendar_start_year": period_start.year,
            "calendar_end_year": period_end.year,
            "starts_on": period_start.date().isoformat(),
            "ends_on": period_end.date().isoformat(),
        })

    active = None
    reference_local = _localize(reference_dt, context.timezone or "UTC")
    if reference_local >= start_date:
        active_index = int((reference_local - start_date).total_seconds() // (3652.425 * 86400))
        if 0 <= active_index < len(sequence):
            active = {**sequence[active_index], "active": True}
            sequence[active_index] = active

    return {
        "luck_pillars_enabled": True,
        "direction": direction["direction"],
        "direction_rule": direction["rule"],
        "direction_rule_key": direction["rule_key"],
        "polarity_source": direction["polarity_source"],
        "start_age": round(start_age_years, 2),
        "start_age_label": _format_start_age(start_age_years),
        "start_date": start_date.date().isoformat(),
        "annual_pillar": annual,
        **flowing,
        "luck_pillars": sequence,
        "active_luck_pillar": active,
        "debug": {
            "method": "three_days_per_year_from_adjacent_jie_solar_term",
            "calculation_sex": direction["calculation_sex"],
            "direction_rule_key": direction["rule_key"],
            "polarity_source": direction["polarity_source"],
            "polarity_symbol": direction["polarity_symbol"],
            "selected_polarity": direction["selected_polarity"],
            "year_stem": direction["year_stem"],
            "year_stem_polarity": direction["year_stem_polarity"],
            "year_branch": direction["year_branch"],
            "year_branch_polarity": direction["year_branch_polarity"],
            "day_stem": direction["day_stem"],
            "day_stem_polarity": direction["day_stem_polarity"],
            "direction": direction["direction"],
            "direction_rule": direction["rule"],
            "solar_term": _serialize_term(solar_term),
            "distance_days": round(distance_days, 4),
            "start_age_years": round(start_age_years, 4),
            "reference_datetime_utc": reference_dt.isoformat(),
        },
    }


def _serialize_term(term: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": term.get("key"),
        "name": term.get("name"),
        "longitude": term.get("longitude"),
        "datetime_utc": term.get("datetime_utc").isoformat() if isinstance(term.get("datetime_utc"), datetime) else term.get("datetime_utc"),
        "source": term.get("source"),
    }


def build_bazi_profile(context: BirthContext, reference_dt_utc: Optional[datetime] = None) -> Dict[str, Any]:
    dt_utc = _ensure_utc(context.dt_utc)
    local_dt = _localize(dt_utc, context.timezone or "UTC")
    day_boundary_rule = _normalize_day_boundary_rule(context.day_boundary_rule)
    hour_pillar_variant = _normalize_hour_pillar_variant(context.hour_pillar_variant)
    luck_direction_rule = _normalize_luck_direction_rule(context.luck_direction_rule)
    missing_inputs: List[Dict[str, str]] = list(context.missing_inputs)
    warnings: List[str] = []
    year_index, bazi_year, li_chun = _year_pillar_index(dt_utc)
    year_stem_index = year_index % 10
    year_branch_index = year_index % 12
    month_stem_index, month_branch_index, month_term = _month_pillar_indices(dt_utc, year_stem_index)
    true_solar = _true_solar_conversion(local_dt, context.longitude) if context.hour_known else None
    true_solar_requested = bool(context.use_true_solar_time)
    selected_hour_dt = (
        true_solar["local_datetime"]
        if true_solar_requested
        and true_solar
        and isinstance(true_solar.get("local_datetime"), datetime)
        else local_dt
    )
    selected_hour_clock_basis = (
        "true_solar_time"
        if selected_hour_dt is not local_dt
        else "civil_local_time"
    )
    civil_day_index = sexagenary_day_index(local_dt.date())
    true_solar_day_index = (
        sexagenary_day_index(true_solar["local_datetime"].date())
        if true_solar and isinstance(true_solar.get("local_datetime"), datetime)
        else None
    )
    day_basis_dt = local_dt
    day_basis = "civil_local_time"
    true_solar_day_applied = False

    if day_boundary_rule == "true_solar_midnight":
        if not context.hour_known:
            warnings.append("True solar day-boundary mode was requested, but the birth time is unknown; the civil-date day pillar was used.")
        elif context.longitude is None:
            if not any(item.get("field") == "longitude" for item in missing_inputs):
                missing_inputs.append({
                    "field": "longitude",
                    "message": "Longitude is required before true solar day-boundary mode can be applied.",
                })
            warnings.append("True solar day-boundary mode was requested without longitude; the civil-date day pillar was used.")
        elif true_solar and isinstance(true_solar.get("local_datetime"), datetime):
            day_basis_dt = true_solar["local_datetime"]
            day_basis = "true_solar_time"
            true_solar_day_applied = True

    late_zi_applied = False
    if hour_pillar_variant == "late_zi_next_day" and context.hour_known and int(selected_hour_dt.hour) == 23:
        day_basis_dt = selected_hour_dt + timedelta(days=1)
        day_basis = f"{selected_hour_clock_basis}_late_zi_next_day"
        late_zi_applied = True
        warnings.append(
            "Late Zi-hour next-day variant is applied from the selected "
            f"{selected_hour_clock_basis.replace('_', ' ')} clock; the day pillar is advanced."
        )

    day_index = sexagenary_day_index(day_basis_dt.date())
    day_stem_index = day_index % 10
    day_branch_index = day_index % 12
    civil_hour_pair = _hour_pillar_indices(local_dt, day_stem_index) if context.hour_known else None
    true_solar_pair = (
        _hour_pillar_indices(true_solar["local_datetime"], day_stem_index)
        if true_solar and isinstance(true_solar.get("local_datetime"), datetime)
        else None
    )
    true_solar_applied = bool(true_solar_requested and true_solar_pair)

    if true_solar_requested and not context.hour_known:
        warnings.append("True solar time was requested, but the birth time is unknown; hour-pillar conversion is unavailable.")
    if true_solar_requested and context.hour_known and context.longitude is None:
        if not any(item.get("field") == "longitude" for item in missing_inputs):
            missing_inputs.append({
                "field": "longitude",
                "message": "Longitude is required before true solar time can be applied to the hour pillar.",
            })
        warnings.append("True solar time was requested without longitude; civil local time was used for the hour pillar.")
    if true_solar_requested and true_solar and true_solar["local_datetime"].date() != local_dt.date() and day_boundary_rule == "civil_midnight":
        warnings.append("True solar time crosses the civil date; civil-midnight day-boundary mode keeps the civil-date day pillar.")
    if context.hour_known:
        boundary_distance = min(
            _minutes_to_hour_branch_boundary(local_dt),
            _minutes_to_hour_branch_boundary(true_solar["local_datetime"]) if true_solar else 999.0,
        )
        if boundary_distance <= 10.0:
            warnings.append("Birth time is within 10 minutes of a two-hour branch boundary; civil versus true-solar mode may matter.")

    raw_pillars: Dict[str, Optional[Tuple[int, int]]] = {
        "year": (year_stem_index, year_branch_index),
        "month": (month_stem_index, month_branch_index),
        "day": (day_stem_index, day_branch_index),
        "hour": (true_solar_pair if true_solar_applied else civil_hour_pair),
    }
    pillars = {
        name: (_pillar_payload(name, pair[0], pair[1], day_stem_index) if pair else None)
        for name, pair in raw_pillars.items()
    }
    balance = _element_balance(pillars)
    strength = _strength_evidence(day_stem_index, pillars, balance)
    analysis_payload = {
        "strength": strength["label"],
        "strength_evidence": strength["evidence"],
        "support_score": strength["support_score"],
        "pressure_score": strength["pressure_score"],
        "weighted_score": strength.get("weighted_score"),
        "strength_model": strength.get("model"),
        "method": strength["method"],
    }
    day_master_stem = STEMS[day_stem_index]
    timing = _luck_pillar_timing(
        context,
        dt_utc=dt_utc,
        local_dt=local_dt,
        year_stem_index=year_stem_index,
        year_branch_index=year_branch_index,
        month_stem_index=month_stem_index,
        month_branch_index=month_branch_index,
        day_stem_index=day_stem_index,
        reference_dt_utc=reference_dt_utc,
    )
    relationships = analyze_relationships(pillars, timing)
    useful_elements = build_useful_element_recommendations(
        day_stem_index=day_stem_index,
        analysis=analysis_payload,
        balance=balance,
        pillars=pillars,
        relationships=relationships,
        timing=timing,
    )
    if isinstance(useful_elements.get("timing_interaction"), dict):
        timing["useful_element_interaction"] = useful_elements["timing_interaction"]
    timing["rhythm"] = build_timing_rhythm(
        pillars=pillars,
        timing=timing,
        useful_elements=useful_elements,
    )

    if selected_hour_dt.hour == 23:
        if hour_pillar_variant != "late_zi_next_day":
            warnings.append("Birth time falls in late Zi hour; schools differ on whether the day pillar changes at 23:00.")
    if not context.hour_known:
        warnings.append("Birth time is unknown; hour pillar and hour-derived interpretation are unavailable.")

    civil_hour_payload = _pillar_payload("hour_civil", civil_hour_pair[0], civil_hour_pair[1], day_stem_index) if civil_hour_pair else None
    true_solar_hour_payload = (
        _pillar_payload("hour_true_solar", true_solar_pair[0], true_solar_pair[1], day_stem_index)
        if true_solar_pair
        else None
    )
    civil_day_payload = _pillar_payload("day", civil_day_index % 10, civil_day_index % 12, civil_day_index % 10)
    true_solar_day_payload = (
        _pillar_payload("day", true_solar_day_index % 10, true_solar_day_index % 12, true_solar_day_index % 10)
        if true_solar_day_index is not None
        else None
    )
    selected_day_payload = _pillar_payload("day", day_stem_index, day_branch_index, day_stem_index)
    day_comparison = {
        "rule": day_boundary_rule,
        "basis": day_basis,
        "hour_pillar_variant": hour_pillar_variant,
        "late_zi_next_day_applied": late_zi_applied,
        "late_zi_clock_basis": selected_hour_clock_basis,
        "late_zi_clock_datetime": selected_hour_dt.isoformat() if context.hour_known else None,
        "true_solar_day_boundary_applied": true_solar_day_applied,
        "civil": {**civil_day_payload, "date": local_dt.date().isoformat()},
        "true_solar": (
            {**true_solar_day_payload, "date": true_solar["local_datetime"].date().isoformat()}
            if true_solar_day_payload and true_solar
            else None
        ),
        "selected": {**selected_day_payload, "date": day_basis_dt.date().isoformat()},
        "changed": bool(
            civil_day_payload.get("stem") != selected_day_payload.get("stem")
            or civil_day_payload.get("branch") != selected_day_payload.get("branch")
            or local_dt.date() != day_basis_dt.date()
        ),
    }
    hour_comparison = {
        "mode": "true_solar_time" if true_solar_applied else "civil_local_time",
        "civil": civil_hour_payload,
        "true_solar": true_solar_hour_payload,
        "changed": bool(
            civil_hour_payload
            and true_solar_hour_payload
            and (
                civil_hour_payload.get("stem") != true_solar_hour_payload.get("stem")
                or civil_hour_payload.get("branch") != true_solar_hour_payload.get("branch")
            )
        ),
    }
    true_solar_payload = {
        "requested": true_solar_requested,
        "available": bool(true_solar),
        "applied": true_solar_applied,
        "selected_for_hour_pillar": true_solar_applied,
        "selected_for_day_pillar": true_solar_day_applied,
        "local_datetime": true_solar["local_datetime"].isoformat() if true_solar else None,
        "equation_of_time_minutes": true_solar.get("equation_of_time_minutes") if true_solar else None,
        "longitude_correction_minutes": true_solar.get("longitude_correction_minutes") if true_solar else None,
        "total_correction_minutes": true_solar.get("total_correction_minutes") if true_solar else None,
        "timezone_offset_hours": true_solar.get("timezone_offset_hours") if true_solar else None,
        "standard_meridian": true_solar.get("standard_meridian") if true_solar else None,
        "longitude": true_solar.get("longitude") if true_solar else context.longitude,
        "method": true_solar.get("method") if true_solar else None,
    }
    birth_payload = {
        "datetime_utc": dt_utc.isoformat(),
        "local_datetime": local_dt.isoformat(),
        "date": local_dt.date().isoformat(),
        "time": local_dt.strftime("%H:%M") if context.hour_known else None,
        "location": context.location,
        "timezone": context.timezone,
        "latitude": context.latitude,
        "longitude": context.longitude,
        "time_precision": context.time_precision,
        "calculation_sex": _normalize_calculation_sex(context.calculation_sex),
        "true_solar_time": true_solar_payload,
        "calculation_options": {
            "day_boundary_rule": day_boundary_rule,
            "hour_pillar_variant": hour_pillar_variant,
            "luck_direction_rule": luck_direction_rule,
        },
        "day_basis": {
            "basis": day_basis,
            "date": day_basis_dt.date().isoformat(),
            "local_datetime": day_basis_dt.isoformat(),
            "true_solar_day_boundary_applied": true_solar_day_applied,
            "late_zi_next_day_applied": late_zi_applied,
        },
    }
    classical_extras = _classical_extras_payload(
        pillars=pillars,
        month_stem_index=month_stem_index,
        month_branch_index=month_branch_index,
        year_stem_index=year_stem_index,
        day_stem_index=day_stem_index,
        hour_pair=true_solar_pair if true_solar_applied else civil_hour_pair,
    )
    day_master_payload = {
        "stem": day_master_stem["key"],
        "stem_index": day_stem_index,
        "element": day_master_stem["element"],
        "polarity": day_master_stem["polarity"],
        "pillar": pillars["day"],
    }
    ten_gods_payload = _ten_god_rows(pillars)
    ten_gods_payload = {
        **ten_gods_payload,
        "factor_profile": build_ten_god_profile(
            day_stem_index=day_stem_index,
            ten_gods=ten_gods_payload,
            analysis=analysis_payload,
            useful_elements=useful_elements,
        ),
    }
    auxiliary_stars = build_auxiliary_stars(
        pillars=pillars,
        timing=timing,
        relationships=relationships,
    )
    palace_context = build_palace_context(
        pillars=pillars,
        relationships=relationships,
        auxiliary_stars=auxiliary_stars,
    )
    life_areas = build_life_areas(
        ten_gods=ten_gods_payload,
        palace_context=palace_context,
        relationships=relationships,
        timing=timing,
        element_balance=balance,
        pillars=pillars,
        calculation_sex=_normalize_calculation_sex(context.calculation_sex),
    )
    interpretation = build_interpretation(
        birth=birth_payload,
        pillars=pillars,
        day_master=day_master_payload,
        balance=balance,
        ten_gods=ten_gods_payload,
        analysis=analysis_payload,
        relationships=relationships,
        timing=timing,
        useful_elements=useful_elements,
        auxiliary_stars=auxiliary_stars,
        palace_context=palace_context,
    )
    curation_payload = curation_summary()
    curation_payload["active_rule_notes"] = rule_notes_for_areas((
        "pillars",
        "solar_terms",
        "true_solar_time",
        "ten_gods",
        "strength",
        "useful_elements",
        "relationships",
        "timing",
        "auxiliary_stars",
        "life_areas",
    ))

    return {
        "source_snap_id": context.source_snap_id,
        "snap_label": context.snap_label,
        "birth": birth_payload,
        "missing_inputs": missing_inputs,
        "pillars": pillars,
        "day_master": day_master_payload,
        "element_balance": balance,
        "ten_gods": ten_gods_payload,
        "analysis": analysis_payload,
        "useful_elements": useful_elements,
        "auxiliary_stars": auxiliary_stars,
        "palace_context": palace_context,
        "life_areas": life_areas,
        "classical_extras": classical_extras,
        "interpretation": interpretation,
        "relationships": relationships,
        "source_confidence": confidence_tags(
            "local_source",
            "computed_rule",
            "school_variant",
            "provisional_model",
            "needs_validation",
        ),
        "curation": curation_payload,
        "luck_pillars": timing.get("luck_pillars") or [],
        "timing": timing,
        "debug": {
            "snap_source": context.source,
            "bazi_year": bazi_year,
            "solar_year_boundary": _serialize_term(li_chun),
            "month_solar_term": _serialize_term(month_term),
            "solar_term_source": month_term.get("source") or li_chun.get("source"),
            "hour_rule": "true solar time two-hour branch windows" if true_solar_applied else "civil local time two-hour branch windows",
            "hour_pillar_comparison": hour_comparison,
            "day_pillar_comparison": day_comparison,
            "true_solar_time": true_solar_payload,
            "day_cycle_rule": "Gregorian local civil date with Julian Day Number + 49 sexagenary offset",
            "day_boundary_rule": day_boundary_rule,
            "hour_pillar_variant": hour_pillar_variant,
            "luck_direction_rule": luck_direction_rule,
            "calculation_options": {
                "day_boundary_rule": day_boundary_rule,
                "hour_pillar_variant": hour_pillar_variant,
                "luck_direction_rule": luck_direction_rule,
            },
            "warnings": warnings,
        },
    }
