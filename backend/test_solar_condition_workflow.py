from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import os
import sys

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from horary_engine.engine import EnhancedTraditionalHoraryJudgmentEngine, extract_testimonies
from horary_engine.serialization import (
    deserialize_chart_for_evaluation,
    serialize_chart_for_frontend,
)
from models import HoraryChart, Planet, PlanetPosition, Sign, SolarAnalysis, SolarCondition


def _position(planet, longitude, sign, house=1):
    return PlanetPosition(
        planet=planet,
        longitude=longitude,
        latitude=0.0,
        house=house,
        sign=sign,
        dignity_score=0,
        speed=1.0,
    )


def _chart(planets, solar_analyses):
    return HoraryChart(
        date_time=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
        date_time_utc=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
        timezone_info="UTC",
        location=(0.0, 0.0),
        location_name="Test",
        planets=planets,
        aspects=[],
        houses=[i * 30.0 for i in range(12)],
        house_rulers={1: Planet.MERCURY, 2: Planet.VENUS},
        ascendant=0.0,
        midheaven=90.0,
        solar_analyses=solar_analyses,
    )


def test_precompute_attaches_solar_analysis_to_planet_positions():
    mercury = _position(Planet.MERCURY, 80.0, Sign.GEMINI)
    analysis = SolarAnalysis(
        planet=Planet.MERCURY,
        distance_from_sun=3.0,
        condition=SolarCondition.COMBUSTION,
    )
    chart = SimpleNamespace(
        planets={Planet.MERCURY: mercury},
        solar_analyses={Planet.MERCURY: analysis},
    )

    engine = object.__new__(EnhancedTraditionalHoraryJudgmentEngine)
    engine._precompute_planet_state(chart)

    assert mercury.solar_condition is analysis
    assert mercury.visibility is SolarCondition.COMBUSTION


def test_combustion_testimony_accepts_attached_solar_analysis_enum():
    mercury = _position(Planet.MERCURY, 80.0, Sign.GEMINI)
    mercury.solar_condition = SolarAnalysis(
        planet=Planet.MERCURY,
        distance_from_sun=3.0,
        condition=SolarCondition.COMBUSTION,
    )
    chart = SimpleNamespace(
        planets={Planet.MERCURY: mercury},
        house_rulers={1: Planet.MERCURY},
        aspects=[],
    )

    primitives = extract_testimonies(chart, {"querent": Planet.MERCURY})

    assert any(isinstance(item, dict) and item.get("key") == "l1_combust" for item in primitives)


def test_under_beams_exception_survives_summary_and_deserialization():
    venus = _position(Planet.VENUS, 40.0, Sign.TAURUS, house=2)
    analysis = SolarAnalysis(
        planet=Planet.VENUS,
        distance_from_sun=12.0,
        condition=SolarCondition.UNDER_BEAMS,
        traditional_exception=True,
    )
    serialized = serialize_chart_for_frontend(
        _chart({Planet.VENUS: venus}, {Planet.VENUS: analysis}),
        {Planet.VENUS: analysis},
    )

    under_beams = serialized["solar_conditions_summary"]["under_beams_planets"]
    assert under_beams[0]["traditional_exception"] is True

    round_tripped = deserialize_chart_for_evaluation(serialized)
    round_trip_analysis = round_tripped.planets[Planet.VENUS].solar_condition
    assert round_trip_analysis.condition is SolarCondition.UNDER_BEAMS
    assert round_trip_analysis.traditional_exception is True


def test_ignored_combustion_still_reports_suppressed_solar_factor():
    chart = SimpleNamespace(
        solar_analyses={
            Planet.MERCURY: SolarAnalysis(
                planet=Planet.MERCURY,
                distance_from_sun=3.0,
                condition=SolarCondition.COMBUSTION,
            )
        }
    )

    engine = object.__new__(EnhancedTraditionalHoraryJudgmentEngine)
    result = engine._analyze_enhanced_solar_factors(
        chart,
        Planet.MOON,
        Planet.MERCURY,
        ignore_combustion=True,
    )

    assert result["combustion_count"] == 0
    assert result["detailed_analyses"]["Mercury"]["effect_ignored"] is True
    assert "ignored" in result["summary"].lower()
    assert result["significant"] is True
