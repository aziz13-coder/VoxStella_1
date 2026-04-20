from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import swisseph as swe


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.models import HoraryChart, Planet, PlanetPosition  # noqa: E402
from backend.horary_engine.aspects import (  # noqa: E402
    calculate_enhanced_aspects,
    calculate_moon_last_aspect,
    calculate_moon_next_aspect,
)
from backend.horary_engine.engine import EnhancedTraditionalAstrologicalCalculator  # noqa: E402
from backend.horary_engine.serialization import serialize_chart_for_frontend  # noqa: E402

from tests.horary_hard_test_utils import replay_serialized_payload  # noqa: E402


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
EXTERNAL_CORPUS_PATH = FIXTURE_ROOT / "horary_external_cunning_man_replay.json"


def load_external_replay_corpus() -> List[Dict[str, Any]]:
    return json.loads(EXTERNAL_CORPUS_PATH.read_text(encoding="utf-8"))


def _local_and_utc(case: Dict[str, Any]) -> tuple[dt.datetime, dt.datetime]:
    tz = ZoneInfo(case["timezone"])
    local_dt = dt.datetime.fromisoformat(case["local_dt"]).replace(tzinfo=tz)
    return local_dt, local_dt.astimezone(dt.timezone.utc)


def build_external_case_payload(case: Dict[str, Any]) -> Dict[str, Any]:
    calculator = EnhancedTraditionalAstrologicalCalculator()
    local_dt, utc_dt = _local_and_utc(case)
    jd_ut = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

    planets: Dict[Planet, PlanetPosition] = {}
    for planet_enum, planet_id in calculator.planets_swe.items():
        planet_data, _ = swe.calc_ut(jd_ut, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
        longitude = float(planet_data[0])
        latitude = float(planet_data[1])
        speed = float(planet_data[3])
        planets[planet_enum] = PlanetPosition(
            planet=planet_enum,
            longitude=longitude,
            latitude=latitude,
            house=0,
            sign=calculator._get_sign(longitude),
            dignity_score=0,
            retrograde=speed < 0,
            speed=speed,
        )

    houses = [float(cusp) for cusp in case["houses"]]
    house_rulers = {
        index + 1: calculator._get_sign(cusp).ruler for index, cusp in enumerate(houses)
    }
    for position in planets.values():
        position.house = calculator._calculate_house_position(position.longitude, houses)

    sun_pos = planets[Planet.SUN]
    solar_analyses = {}
    for planet_enum, position in planets.items():
        solar_analysis = calculator._analyze_enhanced_solar_condition(
            planet_enum,
            position,
            sun_pos,
            0.0,
            0.0,
            jd_ut,
        )
        solar_analyses[planet_enum] = solar_analysis
        dignity_info = calculator._calculate_comprehensive_traditional_dignity(
            position.planet,
            position,
            houses,
            sun_pos,
            solar_analysis,
        )
        position.dignity_score = dignity_info["score"]
        position.essential_dignity = dignity_info["essential_score"]
        position.accidental_dignity = dignity_info["accidental_score"]
        position.dignities = dignity_info["dignities"]

    chart = HoraryChart(
        date_time=local_dt,
        date_time_utc=utc_dt,
        timezone_info=case["timezone"],
        location=(0.0, 0.0),
        location_name=case["location_name"],
        planets=planets,
        aspects=calculate_enhanced_aspects(planets, jd_ut),
        houses=houses,
        house_rulers=house_rulers,
        ascendant=houses[0],
        midheaven=houses[9],
        solar_analyses=solar_analyses,
        julian_day=jd_ut,
        moon_last_aspect=calculate_moon_last_aspect(planets, jd_ut),
        moon_next_aspect=calculate_moon_next_aspect(planets, jd_ut, ignore_orb_for_voc=True),
    )
    setattr(chart, "house_system_code", "R")

    return {
        "question": case["question"],
        "category": case["category"],
        "chart_data": serialize_chart_for_frontend(chart, chart.solar_analyses),
    }


def replay_external_case(case: Dict[str, Any]) -> Dict[str, Any]:
    payload = build_external_case_payload(case)
    replayed = replay_serialized_payload(payload)
    replayed["payload"] = payload
    return replayed
