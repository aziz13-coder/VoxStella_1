from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.engine import (  # noqa: E402
    EnhancedTraditionalHoraryJudgmentEngine,
    HoraryEngine,
)


def _judge_weak_conception_chart():
    settings = {
        "location": "San Diego, CA",
        "date": "2014-01-15",
        "time": "16:43",
        "timezone": "America/Los_Angeles",
        "use_current_time": False,
        "latitude": 32.7157,
        "longitude": -117.1611,
        "location_name": "San Diego, CA",
        "house_system_code": "R",
    }

    with contextlib.redirect_stdout(io.StringIO()):
        return HoraryEngine().judge("Will I conceive?", settings)


def _reasoning_rules(result):
    return [
        entry.get("rule", "")
        for entry in result.get("reasoning", [])
        if isinstance(entry, dict)
    ]


def test_reception_alone_cannot_create_pregnancy_sufficiency(monkeypatch):
    monkeypatch.setattr(
        EnhancedTraditionalHoraryJudgmentEngine,
        "_detect_reception_between_planets",
        lambda _self, _chart, _querent, _quesited: "unilateral",
    )

    result = _judge_weak_conception_chart()
    traditional_factors = result["traditional_factors"]

    assert traditional_factors["reception"] == "unilateral"
    assert traditional_factors["perfection_type"] == "none"
    assert result["judgment"] == "NO"
    assert not any("Pregnancy: L1" in rule for rule in _reasoning_rules(result))


def test_generic_moon_to_benefic_alone_cannot_create_pregnancy_sufficiency(
    monkeypatch,
):
    monkeypatch.setattr(
        EnhancedTraditionalHoraryJudgmentEngine,
        "_detect_reception_between_planets",
        lambda _self, _chart, _querent, _quesited: "none",
    )
    monkeypatch.setattr(
        EnhancedTraditionalHoraryJudgmentEngine,
        "_check_enhanced_moon_testimony",
        lambda _self, _chart, _querent, _quesited, _ignore_void=False: {
            "aspects": [
                {
                    "testimony_type": "moon_to_benefic",
                    "applying": True,
                    "favorable": True,
                    "description": "Moon applies to a benefic",
                }
            ],
            "favorable": True,
            "neutral": False,
            "unfavorable": False,
            "reason": "Moon applies to a benefic",
            "void_of_course": False,
            "timing": "Moderate timeframe",
        },
    )

    result = _judge_weak_conception_chart()

    assert result["traditional_factors"]["perfection_type"] == "none"
    assert result["judgment"] == "NO"
    assert not any(
        "Pregnancy: Moon applying to benefic" in rule
        for rule in _reasoning_rules(result)
    )
