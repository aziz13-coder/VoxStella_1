from pathlib import Path
import sys
import datetime
from types import SimpleNamespace

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.models import HoraryChart, Planet, PlanetPosition, Sign, Aspect
from backend.horary_engine.engine import EnhancedTraditionalHoraryJudgmentEngine
from backend.horary_engine.perfection_core import EventDetector, EventType
import backend.horary_engine.aspects as aspects_module


def _pos(planet, longitude, house, speed, dignity_score=0, retrograde=False):
    sign = list(Sign)[int((longitude % 360) // 30)]
    return PlanetPosition(
        planet=planet,
        longitude=longitude,
        latitude=0.0,
        house=house,
        sign=sign,
        dignity_score=dignity_score,
        essential_dignity=0,
        accidental_dignity=0,
        retrograde=retrograde,
        speed=speed,
    )


def _chart(planets=None):
    base = {
        Planet.SUN: _pos(Planet.SUN, 100.0, 10, 1.0),
        Planet.MOON: _pos(Planet.MOON, 120.0, 11, 13.0),
        Planet.MERCURY: _pos(Planet.MERCURY, 80.0, 9, 1.2),
        Planet.VENUS: _pos(Planet.VENUS, 60.0, 8, 1.1),
        Planet.MARS: _pos(Planet.MARS, 130.0, 7, 0.6),
        Planet.JUPITER: _pos(Planet.JUPITER, 200.0, 3, 0.2),
        Planet.SATURN: _pos(Planet.SATURN, 220.0, 4, 0.08),
    }
    if planets:
        base.update(planets)
    return HoraryChart(
        date_time=datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc),
        date_time_utc=datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc),
        timezone_info="UTC",
        location=(0.0, 0.0),
        location_name="Test",
        planets=base,
        aspects=[],
        houses=[i * 30.0 for i in range(12)],
        house_rulers={i: Planet.SUN for i in range(1, 13)},
        ascendant=0.0,
        midheaven=90.0,
        julian_day=2451545.0,
    )


def test_translation_requires_recent_separating_leg(monkeypatch):
    detector = EventDetector()
    chart = _chart()

    def fake_sep(chart_obj, translator, target, window_days, max_degree=None):
        if translator == Planet.MOON and target == Planet.SUN:
            return {"aspect": Aspect.SEXTILE, "timing": -8.0, "target": Planet.SUN}
        return None

    def fake_app(chart_obj, planet1, planet2, window_days, max_degree=None):
        if planet1 == Planet.MOON and planet2 == Planet.SATURN:
            return {"aspect": Aspect.TRINE, "timing": 2.0, "target": Planet.SATURN}
        return None

    def fake_earliest(chart_obj, planet, window_days, exclude=None, max_degree=None):
        if planet == Planet.MOON:
            return {"target": Planet.SATURN, "aspect": Aspect.TRINE, "timing": 2.0}
        return None

    monkeypatch.setattr(detector, "_find_separating_aspect", fake_sep)
    monkeypatch.setattr(detector, "_find_applying_aspect", fake_app)
    monkeypatch.setattr(detector, "_find_earliest_application", fake_earliest)
    monkeypatch.setattr(
        detector,
        "_get_cached_reception",
        lambda *_args, **_kwargs: {"type": "none", "mutual": "none", "one_way": []},
    )

    events = detector._detect_translation_events(chart, Planet.SUN, Planet.SATURN, window_days=30)
    assert not any(e.event_type == EventType.TRANSLATION for e in events)


def test_collection_requires_slower_dignified_collector(monkeypatch):
    detector = EventDetector()
    chart = _chart(
        planets={
            Planet.MERCURY: _pos(Planet.MERCURY, 80.0, 9, 1.2, dignity_score=-1),
            Planet.SUN: _pos(Planet.SUN, 100.0, 10, 1.0),
            Planet.VENUS: _pos(Planet.VENUS, 140.0, 8, 1.1),
        }
    )

    def fake_app(chart_obj, planet1, planet2, window_days, max_degree=None):
        if (planet1, planet2) == (Planet.SUN, Planet.MERCURY):
            return {"aspect": Aspect.CONJUNCTION, "timing": 2.0, "target": Planet.MERCURY}
        if (planet1, planet2) == (Planet.VENUS, Planet.MERCURY):
            return {"aspect": Aspect.SEXTILE, "timing": 3.0, "target": Planet.MERCURY}
        return None

    monkeypatch.setattr(detector, "_find_applying_aspect", fake_app)
    monkeypatch.setattr(
        detector,
        "_find_earliest_application",
        lambda _chart, planet, _window, exclude=None, max_degree=None: (
            {"target": Planet.MERCURY, "aspect": Aspect.CONJUNCTION, "timing": 2.0}
            if planet == Planet.SUN
            else {"target": Planet.MERCURY, "aspect": Aspect.SEXTILE, "timing": 3.0}
            if planet == Planet.VENUS
            else None
        ),
    )
    monkeypatch.setattr(
        detector,
        "_get_cached_reception",
        lambda _chart, p1, p2: {"type": "none", "mutual": "none", "one_way": ["sign"]}
        if p1 == Planet.MERCURY and p2 in {Planet.SUN, Planet.VENUS}
        else {"type": "none", "mutual": "none", "one_way": []},
    )

    events = detector._detect_collection_events(chart, Planet.SUN, Planet.VENUS, window_days=30)
    assert not any(e.event_type == EventType.COLLECTION for e in events)


def test_collection_emits_when_collector_is_slower_and_received(monkeypatch):
    detector = EventDetector()
    chart = _chart(
        planets={
            Planet.MERCURY: _pos(Planet.MERCURY, 80.0, 9, 0.05, dignity_score=2),
            Planet.SUN: _pos(Planet.SUN, 100.0, 10, 1.0),
            Planet.VENUS: _pos(Planet.VENUS, 140.0, 8, 1.1),
        }
    )

    def fake_app(chart_obj, planet1, planet2, window_days, max_degree=None):
        if (planet1, planet2) == (Planet.SUN, Planet.MERCURY):
            return {"aspect": Aspect.CONJUNCTION, "timing": 2.0, "target": Planet.MERCURY}
        if (planet1, planet2) == (Planet.VENUS, Planet.MERCURY):
            return {"aspect": Aspect.SEXTILE, "timing": 3.0, "target": Planet.MERCURY}
        return None

    monkeypatch.setattr(detector, "_find_applying_aspect", fake_app)
    monkeypatch.setattr(
        detector,
        "_find_earliest_application",
        lambda _chart, planet, _window, exclude=None, max_degree=None: (
            {"target": Planet.MERCURY, "aspect": Aspect.CONJUNCTION, "timing": 2.0}
            if planet == Planet.SUN
            else {"target": Planet.MERCURY, "aspect": Aspect.SEXTILE, "timing": 3.0}
            if planet == Planet.VENUS
            else None
        ),
    )
    monkeypatch.setattr(
        detector,
        "_get_cached_reception",
        lambda _chart, p1, p2: {"type": "none", "mutual": "none", "one_way": ["sign"]}
        if p1 == Planet.MERCURY and p2 in {Planet.SUN, Planet.VENUS}
        else {"type": "none", "mutual": "none", "one_way": []},
    )

    events = detector._detect_collection_events(chart, Planet.SUN, Planet.VENUS, window_days=30)
    collection = next(e for e in events if e.event_type == EventType.COLLECTION)
    assert collection.favorable is True
    assert collection.mediator == Planet.MERCURY


def test_prohibition_must_preempt_receiver_before_direct_perfection(monkeypatch):
    detector = EventDetector()
    chart = _chart()

    def fake_app(chart_obj, planet1, planet2, window_days, max_degree=None):
        mapping = {
            (Planet.SUN, Planet.SATURN): {"aspect": Aspect.TRINE, "timing": 5.0, "target": Planet.SATURN},
            (Planet.MARS, Planet.SATURN): {"aspect": Aspect.SQUARE, "timing": 2.0, "target": Planet.SATURN},
        }
        return mapping.get((planet1, planet2))

    monkeypatch.setattr(detector, "_find_applying_aspect", fake_app)
    monkeypatch.setattr(detector, "_find_earliest_application", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        detector,
        "_get_cached_reception",
        lambda *_args, **_kwargs: {"type": "none", "mutual": "none", "one_way": []},
    )

    events = detector._detect_prohibition_events(chart, Planet.SUN, Planet.SATURN, window_days=30)
    prohibition = next(e for e in events if e.event_type == EventType.PROHIBITION)
    assert prohibition.mediator == Planet.MARS
    assert prohibition.exact_in_days == 2.0


def test_void_of_course_uses_sign_bound_last_aspect_only(monkeypatch):
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = _chart(
        planets={
            Planet.MOON: _pos(Planet.MOON, 35.0, 2, 13.0),
        }
    )

    monkeypatch.setattr(engine, "_debug_compare_moon_aspect_systems", lambda _chart: None)
    monkeypatch.setattr(engine, "_days_to_sign_exit", lambda _moon: 1.9)
    monkeypatch.setattr(aspects_module, "calculate_moon_next_aspect", lambda *_args, **_kwargs: None)

    result = engine._is_moon_void_of_course_enhanced(chart)
    assert result["void"] is True
    assert "Moon makes no applying aspects before leaving Taurus" in result["reason"]
    assert result["exception"] is True


def test_radicality_override_preserves_raw_invalid_state():
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = _chart()
    chart.ascendant = 1.5

    result = engine._calculate_considerations(
        chart,
        {},
        ignore_radicality=True,
        ignore_void_moon=False,
        ignore_saturn_7th=True,
    )

    assert result["radical"] is True
    assert result["radical_raw"] is False
    assert result["radicality_ignored"] is True
