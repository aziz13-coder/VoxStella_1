from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from horary_engine import engine as engine_module
from models import Planet


def _calculator_with_two_planets():
    calculator = object.__new__(
        engine_module.EnhancedTraditionalAstrologicalCalculator
    )
    calculator.planets_swe = {
        Planet.SUN: engine_module.swe.SUN,
        Planet.MOON: engine_module.swe.MOON,
    }
    return calculator


def test_ephemeris_snapshot_is_atomic_under_shared_lock(monkeypatch):
    calculator = _calculator_with_two_planets()
    lock_state = {"active": False, "entries": 0}

    @contextmanager
    def tracking_lock():
        assert lock_state["active"] is False
        lock_state["active"] = True
        lock_state["entries"] += 1
        try:
            yield
        finally:
            lock_state["active"] = False

    def fake_calc_ut(_jd, planet_id, _flags):
        assert lock_state["active"] is True
        longitude = 10.0 if planet_id == engine_module.swe.SUN else 20.0
        return ([longitude, 0.0, 0.0, 1.0, 0.0, 0.0], 0)

    def fake_houses(_jd, _lat, _lon, _house_code):
        assert lock_state["active"] is True
        return ([float(index * 30) for index in range(12)], [5.0, 95.0])

    monkeypatch.setattr(engine_module, "swisseph_lock", tracking_lock)
    monkeypatch.setattr(engine_module.swe, "calc_ut", fake_calc_ut)
    monkeypatch.setattr(engine_module.swe, "houses", fake_houses)

    planets, houses, ascendant, midheaven = (
        calculator._calculate_ephemeris_snapshot(
            2_460_000.5,
            31.778,
            35.235,
            b"R",
        )
    )

    assert set(planets) == {Planet.SUN, Planet.MOON}
    assert len(houses) == 12
    assert ascendant == 5.0
    assert midheaven == 95.0
    assert lock_state == {"active": False, "entries": 1}


def test_planet_failure_raises_instead_of_fabricating_position(monkeypatch):
    calculator = _calculator_with_two_planets()

    def fail_calc_ut(*_args, **_kwargs):
        raise RuntimeError("ephemeris unavailable")

    monkeypatch.setattr(engine_module.swe, "calc_ut", fail_calc_ut)
    monkeypatch.setattr(
        engine_module.swe,
        "houses",
        lambda *_args: pytest.fail("houses must not be calculated after a planet failure"),
    )

    with pytest.raises(
        engine_module.EphemerisCalculationError,
        match="Sun position",
    ):
        calculator._calculate_ephemeris_snapshot(
            2_460_000.5,
            31.778,
            35.235,
            b"R",
        )


def test_house_failure_raises_instead_of_fabricating_equal_houses(monkeypatch):
    calculator = _calculator_with_two_planets()
    monkeypatch.setattr(
        engine_module.swe,
        "calc_ut",
        lambda *_args: ([10.0, 0.0, 0.0, 1.0, 0.0, 0.0], 0),
    )

    def fail_houses(*_args, **_kwargs):
        raise RuntimeError("house calculation unavailable")

    monkeypatch.setattr(engine_module.swe, "houses", fail_houses)

    with pytest.raises(
        engine_module.EphemerisCalculationError,
        match="astrological houses",
    ):
        calculator._calculate_ephemeris_snapshot(
            2_460_000.5,
            31.778,
            35.235,
            b"R",
        )


def test_enhanced_denial_check_has_one_effective_definition():
    source_path = Path(engine_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    judgment_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "EnhancedTraditionalHoraryJudgmentEngine"
    )
    definitions = [
        node
        for node in judgment_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_check_enhanced_denial_conditions"
    ]

    assert len(definitions) == 1
