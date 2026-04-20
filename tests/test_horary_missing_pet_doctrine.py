from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.horary_engine.engine import HoraryEngine  # noqa: E402
from backend.horary_engine.pet_doctrine import evaluate_pet_missing_snapshot  # noqa: E402
import backend.horary_engine.engine as engine_module  # noqa: E402


def test_missing_pet_phrasings_route_to_pet_missing_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    prompts = [
        "Will my missing dog be found?",
        "Where is my missing dog?",
        "Will I recover my lost dog?",
        "Will my dog come home?",
    ]

    for prompt in prompts:
        analysis = analyzer.analyze_question(prompt)
        assert str(analysis["question_type"]) == "Category.PET"
        assert analysis["pet_analysis"]["family"] == "missing"
        assert analysis["relevant_houses"] == [1, 6]
        assert analysis["lost_object_analysis"] is None
        assert analysis["significators"]["pet_family"] == "missing"


def test_missing_pet_return_home_case_uses_pet_missing_balance(monkeypatch):
    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (42.6152778, -77.4027778, "Naples, New York"),
    )

    engine = HoraryEngine()
    settings = {
        "location": "Naples, New York",
        "date": "2025-01-06",
        "time": "23:19",
        "timezone": "America/New_York",
        "use_current_time": False,
    }

    with contextlib.redirect_stdout(io.StringIO()):
        result = engine.judge("Will my dog come home?", settings)

    location_projection = result.get("lost_object_location") or {}
    reasoning_rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]

    assert result["judgment"] == "YES"
    assert result["confidence"] >= 80
    assert result["question_analysis"]["question_type"] == "pet"
    assert result["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert result["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert location_projection.get("applies") is True
    assert any(
        "Reception between querent and pet significators supports the animal being found" in rule
        for rule in reasoning_rules
    )
    assert any("retrograde, favoring return or retracing" in rule for rule in reasoning_rules)


def test_missing_pet_snapshot_respects_earlier_blocking_secondary_perfection():
    snapshot = {
        "family": "missing",
        "pet_name": "Jupiter",
        "perfection_type": "direct_penalized",
        "secondary_perfection_type": "frustration",
        "secondary_perfection_reason": "Frustration: applier Moon perfects with Mercury before reaching Jupiter",
        "secondary_preempts_primary": True,
        "traditional_strength": 0,
        "one_way": ["Moon↦Jupiter(face)"],
        "pet_retrograde": True,
        "pet_angularity": "cadent",
        "pet_dignity": -5,
        "pet_solar_condition": "Free of Sun",
        "moon_score": 1,
        "pet_safety_score": 0,
    }

    evaluation = evaluate_pet_missing_snapshot(snapshot)
    rules = [entry.get("rule", "") for entry in evaluation.get("reasoning", [])]

    assert evaluation["applies"] is True
    assert evaluation["result"] == "NO"
    assert any("pre-empts the apparent recovery route" in rule for rule in rules)
