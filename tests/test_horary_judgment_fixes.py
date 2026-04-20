from pathlib import Path
import sys
import datetime

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.models import (
    Aspect,
    AspectInfo,
    HoraryChart,
    Planet,
    PlanetPosition,
    Sign,
    SolarCondition,
)
from backend.horary_engine.engine import (
    EnhancedTraditionalAstrologicalCalculator,
    EnhancedTraditionalHoraryJudgmentEngine,
    _evaluate_enhanced,
    _structure_reasoning,
    get_category_rules,
    resolve_category,
)
from backend.horary_engine.perfection_core import EventDetector, EventType
from backend.horary_engine.serialization import deserialize_chart_for_evaluation
from backend.taxonomy import Category
import backend.horary_engine.engine as engine_module


def _pos(planet, longitude, house, speed):
    sign = list(Sign)[int((longitude % 360) // 30)]
    return PlanetPosition(
        planet=planet,
        longitude=longitude,
        latitude=0.0,
        house=house,
        sign=sign,
        dignity_score=0,
        essential_dignity=0,
        accidental_dignity=0,
        retrograde=False,
        speed=speed,
    )


def _minimal_chart(aspects=None):
    aspects = aspects or []
    planets = {
        Planet.SUN: _pos(Planet.SUN, 100.0, 10, 1.0),
        Planet.MOON: _pos(Planet.MOON, 120.0, 11, 13.0),
        Planet.MERCURY: _pos(Planet.MERCURY, 80.0, 9, 1.2),
        Planet.VENUS: _pos(Planet.VENUS, 60.0, 8, 1.1),
        Planet.MARS: _pos(Planet.MARS, 130.0, 7, 0.6),
        Planet.JUPITER: _pos(Planet.JUPITER, 200.0, 3, 0.2),
        Planet.SATURN: _pos(Planet.SATURN, 220.0, 4, 0.08),
    }
    return HoraryChart(
        date_time=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        date_time_utc=datetime.datetime(2024, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
        timezone_info="UTC",
        location=(0.0, 0.0),
        location_name="Test",
        planets=planets,
        aspects=aspects,
        houses=[i * 30.0 for i in range(12)],
        house_rulers={i: Planet.SUN for i in range(1, 13)},
        ascendant=0.0,
        midheaven=90.0,
        julian_day=2451545.0,
    )


def _property_quality_chart_data():
    return {
        "timezone_info": {
            "local_time": "2025-09-27T17:25:00+01:00",
            "utc_time": "2025-09-27T16:25:00+00:00",
            "timezone": "Europe/London",
            "location_name": "City of London, Greater London",
            "coordinates": {
                "latitude": 51.5156177,
                "longitude": -0.0919983,
            },
        },
        "planets": {
            "Jupiter": {
                "longitude": 112.04581402480581,
                "latitude": 0.014332258023116025,
                "house": 6,
                "sign": "Cancer",
                "dignity_score": 7,
                "essential_dignity": 6,
                "accidental_dignity": 1,
                "retrograde": False,
                "speed": 0.12972573328040318,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 72.7767},
            },
            "Mars": {
                "longitude": 213.61247892607057,
                "latitude": -0.04340810202592214,
                "house": 8,
                "sign": "Scorpio",
                "dignity_score": 8,
                "essential_dignity": 8,
                "accidental_dignity": 0,
                "retrograde": False,
                "speed": 0.6774743514912662,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 28.79},
            },
            "Mercury": {
                "longitude": 195.84284182338888,
                "latitude": 0.28422149729677176,
                "house": 7,
                "sign": "Libra",
                "dignity_score": -3,
                "essential_dignity": 0,
                "accidental_dignity": -3,
                "retrograde": False,
                "speed": 1.6361982090736227,
                "solar_condition": {"condition": "Under the Beams", "distance_from_sun": 11.0203},
            },
            "Moon": {
                "longitude": 249.28853931512148,
                "latitude": -5.191901351827381,
                "house": 9,
                "sign": "Sagittarius",
                "dignity_score": 0,
                "essential_dignity": 0,
                "accidental_dignity": 0,
                "retrograde": False,
                "speed": 11.879939583636082,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 64.466},
            },
            "Saturn": {
                "longitude": 358.0108186439088,
                "latitude": -2.511773200622734,
                "house": 1,
                "sign": "Pisces",
                "dignity_score": 2,
                "essential_dignity": 2,
                "accidental_dignity": 0,
                "retrograde": True,
                "speed": -0.076771018942041,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 173.1883},
            },
            "Sun": {
                "longitude": 184.8224975592281,
                "latitude": -0.00015991393126060427,
                "house": 7,
                "sign": "Libra",
                "dignity_score": -1,
                "essential_dignity": -4,
                "accidental_dignity": 3,
                "retrograde": False,
                "speed": 0.9813154904102406,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 0.0},
            },
            "Venus": {
                "longitude": 159.99190415914245,
                "latitude": 1.1999725245023143,
                "house": 7,
                "sign": "Virgo",
                "dignity_score": 2,
                "essential_dignity": 1,
                "accidental_dignity": 1,
                "retrograde": False,
                "speed": 1.2285161473862043,
                "solar_condition": {"condition": "Free of Sun", "distance_from_sun": 24.8306},
            },
        },
        "aspects": [
            {
                "planet1": "Sun",
                "planet2": "Moon",
                "aspect": "Sextile",
                "orb": 4.47,
                "applying": False,
                "time_to_perfection": -0.41,
                "perfection_within_sign": False,
                "degrees_to_exact": 4.47,
            },
            {
                "planet1": "Sun",
                "planet2": "Saturn",
                "aspect": "Opposition",
                "orb": 6.81,
                "applying": False,
                "time_to_perfection": -6.44,
                "perfection_within_sign": False,
                "degrees_to_exact": 6.81,
            },
            {
                "planet1": "Moon",
                "planet2": "Mercury",
                "aspect": "Sextile",
                "orb": 6.55,
                "applying": True,
                "time_to_perfection": 0.64,
                "perfection_within_sign": True,
                "exact_time": "2025-09-28T07:46:21+00:00",
                "degrees_to_exact": 6.55,
            },
            {
                "planet1": "Moon",
                "planet2": "Venus",
                "aspect": "Square",
                "orb": 0.7,
                "applying": True,
                "time_to_perfection": 0.07,
                "perfection_within_sign": True,
                "exact_time": "2025-09-27T18:00:05+00:00",
                "degrees_to_exact": 0.7,
            },
            {
                "planet1": "Mercury",
                "planet2": "Jupiter",
                "aspect": "Square",
                "orb": 6.2,
                "applying": True,
                "time_to_perfection": 4.12,
                "perfection_within_sign": True,
                "exact_time": "2025-10-01T19:14:15+00:00",
                "degrees_to_exact": 6.2,
            },
            {
                "planet1": "Jupiter",
                "planet2": "Saturn",
                "aspect": "Trine",
                "orb": 5.97,
                "applying": True,
                "time_to_perfection": 28.89,
                "perfection_within_sign": True,
                "exact_time": "2025-10-26T13:41:48+00:00",
                "degrees_to_exact": 5.97,
            },
        ],
        "house_rulers": {
            "1": "Saturn",
            "2": "Mars",
            "3": "Venus",
            "4": "Mercury",
            "5": "Mercury",
            "6": "Moon",
            "7": "Sun",
            "8": "Venus",
            "9": "Mars",
            "10": "Jupiter",
            "11": "Jupiter",
            "12": "Saturn",
        },
        "houses": [321.96, 25.79, 58.18, 74.21, 87.31, 104.6, 141.96, 205.79, 238.18, 254.21, 267.31, 284.6],
        "ascendant": 321.9629,
        "midheaven": 254.2116,
        "moon_last_aspect": {
            "planet": "Sun",
            "aspect": "Sextile",
            "orb": 4.47,
            "degrees_difference": 4.47,
            "perfection_eta_days": 0.41,
            "perfection_eta_description": "0.4 days ago",
            "applying": False,
        },
        "moon_next_aspect": {
            "planet": "Venus",
            "aspect": "Square",
            "orb": 0.7,
            "degrees_difference": 0.7,
            "perfection_eta_days": 0.07,
            "perfection_eta_description": "Within hours",
            "applying": True,
        },
    }


def test_translation_event_emits_for_favorable_paths(monkeypatch):
    detector = EventDetector()
    chart = _minimal_chart()

    def fake_sep(chart_obj, translator, target, window_days, max_degree=None):
        if translator == Planet.MOON and target == Planet.SUN:
            return {"aspect": Aspect.SEXTILE, "timing": -1.0, "target": Planet.SUN}
        return None

    def fake_app(chart_obj, planet1, planet2, window_days, max_degree=None):
        if planet1 == Planet.MOON and planet2 == Planet.SATURN:
            return {"aspect": Aspect.TRINE, "timing": 2.0, "target": Planet.SATURN}
        return None

    def fake_earliest(chart_obj, planet, window_days, exclude=None, max_degree=None):
        if planet == Planet.MOON:
            return {"target": Planet.SATURN, "aspect": Aspect.TRINE, "timing": 2.0}
        return None

    def fake_reception(chart_obj, p1, p2):
        return {"type": "none", "mutual": "none", "one_way": []}

    monkeypatch.setattr(detector, "_find_separating_aspect", fake_sep)
    monkeypatch.setattr(detector, "_find_applying_aspect", fake_app)
    monkeypatch.setattr(detector, "_find_earliest_application", fake_earliest)
    monkeypatch.setattr(detector, "_get_cached_reception", fake_reception)

    events = detector._detect_translation_events(chart, Planet.SUN, Planet.SATURN, window_days=30)
    assert any(e.event_type == EventType.TRANSLATION and e.favorable for e in events)


def test_prohibition_requires_chronology_and_preemption():
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    aspect = AspectInfo(
        planet1=Planet.SUN,
        planet2=Planet.MARS,
        aspect=Aspect.SQUARE,
        orb=1.0,
        applying=True,
        time_to_perfection=1.0,
    )
    chart = _minimal_chart(aspects=[aspect])

    no_chrono = engine._check_malefic_prohibition(chart, Planet.SUN, earliest_perfection_days=None)
    assert no_chrono["has_prohibition"] is False

    preempt = engine._check_malefic_prohibition(chart, Planet.SUN, earliest_perfection_days=3.0)
    assert preempt["has_prohibition"] is True
    assert preempt["prohibitions"][0]["kind"] == "true_prohibition"

    post = engine._check_malefic_prohibition(chart, Planet.SUN, earliest_perfection_days=0.5)
    assert post["has_prohibition"] is True
    assert post["prohibitions"][0]["kind"] == "post_perfection"


def test_solar_condition_uses_configured_under_beams_limit():
    calc = EnhancedTraditionalAstrologicalCalculator()
    sun_pos = _pos(Planet.SUN, 0.0, 10, 1.0)
    mars_pos = _pos(Planet.MARS, 16.0, 1, 0.6)

    analysis = calc._analyze_enhanced_solar_condition(
        Planet.MARS,
        mars_pos,
        sun_pos,
        lat=0.0,
        lon=0.0,
        jd_ut=2451545.0,
    )
    assert analysis.condition == SolarCondition.FREE


def test_lost_object_voc_denial_uses_enhanced_voc_check(monkeypatch):
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = _minimal_chart()

    monkeypatch.setattr(
        engine,
        "_is_moon_void_of_course_enhanced",
        lambda _: {"void": True, "reason": "Moon makes no applying aspects"},
    )

    denials = engine._check_theft_loss_specific_denials(
        chart,
        Category.LOST_OBJECT,
        Planet.SUN,
        Planet.MERCURY,
    )
    assert any("Moon void-of-course" in reason for reason in denials)


def test_considerations_include_override_context(monkeypatch):
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = _minimal_chart()

    monkeypatch.setattr(
        engine_module,
        "check_enhanced_radicality",
        lambda _chart, _ignore=False: {"valid": False, "reason": "Ascendant too early"},
    )
    monkeypatch.setattr(
        engine,
        "_is_moon_void_of_course_enhanced",
        lambda _chart: {"void": True, "reason": "Moon makes no applying aspects"},
    )

    result = engine._calculate_considerations(
        chart,
        {},
        ignore_radicality=True,
        ignore_void_moon=True,
        ignore_saturn_7th=True,
    )
    assert result["radical"] is True
    assert result["radical_raw"] is False
    assert result["radicality_ignored"] is True
    assert result["moon_void"] is True
    assert result["moon_void_ignored"] is True
    assert "ignored" in result["moon_void_reason"]


def test_property_quality_question_no_perfection_uses_condition_reasoning_without_synthetic_denial():
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = deserialize_chart_for_evaluation(_property_quality_chart_data())
    question = "should I invest in this house?"
    question_analysis = engine.question_analyzer.analyze_question(question)
    question_analysis["question_type"] = Category.PROPERTY

    judgment = engine._apply_enhanced_judgment(
        chart,
        question_analysis,
        False,
        False,
        False,
        False,
        None,
        90,
        question_text=question,
    )
    structured = _structure_reasoning(judgment.get("reasoning", []))
    category_rules = get_category_rules(resolve_category(question_analysis.get("question_type")))
    evaluation = _evaluate_enhanced(structured, category_rules)
    final = engine._finalize_judgment(
        judgment,
        evaluation,
        structured,
        chart,
        question_analysis,
        resolve_category(question_analysis.get("question_type")),
        category_rules,
    )

    quality_no_perfection = next(
        entry for entry in final["reasoning"]
        if entry.get("stage") == "Quality Assessment" and "No direct perfection found between Saturn and Mercury" in entry.get("rule", "")
    )

    assert question_analysis["question_intent"] == "QUALITY"
    assert final["result"] == "NO"
    assert quality_no_perfection["weight"] == 0
    assert not any("Supportive signals noted -" in entry.get("rule", "") for entry in final["reasoning"])
    assert any(
        entry.get("rule") == "One-way reception between Saturn and Mercury" and entry.get("weight") == 3
        for entry in final["reasoning"]
    )
    breakdown = final.get("confidence_breakdown") or {}
    adjustments = breakdown.get("confidence_adjustments") or []
    assert not any("No viable perfection found between significators" in str(item.get("factor")) for item in adjustments)
