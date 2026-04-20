from pathlib import Path
import contextlib
import io
import json
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.engine import (  # noqa: E402
    EnhancedTraditionalHoraryJudgmentEngine,
    _evaluate_enhanced,
    _structure_reasoning,
    get_category_rules,
    resolve_category,
)
from backend.horary_engine.serialization import deserialize_chart_for_evaluation  # noqa: E402


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "horary_questions"


def _replay_fixture(name: str):
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = deserialize_chart_for_evaluation(payload["chart_data"])
    question_analysis = engine.question_analyzer.analyze_question(payload["question"])
    if payload.get("category"):
        question_analysis["question_type"] = payload["category"]
    window_days = question_analysis.get("timeframe_analysis", {}).get("window_days") or 90

    with contextlib.redirect_stdout(io.StringIO()):
        judgment = engine._apply_enhanced_judgment(
            chart,
            question_analysis,
            False,
            False,
            False,
            False,
            None,
            window_days,
            question_text=payload["question"],
        )
        structured = _structure_reasoning(judgment.get("reasoning", []))
        question_type = resolve_category(question_analysis.get("question_type"))
        category_rules = get_category_rules(question_type)
        evaluation = _evaluate_enhanced(structured, category_rules)
        final = engine._finalize_judgment(
            judgment,
            evaluation,
            structured,
            chart,
            question_analysis,
            question_type,
            category_rules,
        )

    return payload, final


def _reasoning_rules(final):
    return [entry.get("rule", "") for entry in final.get("reasoning", [])]


def test_lottery_question_replays_as_negative_prohibition_family_case():
    payload, final = _replay_fixture("lottery_prohibition.json")
    rules = _reasoning_rules(final)
    factors = final["traditional_factors"]

    assert payload["question"] == "will I win in the lottery?"
    assert final["result"] == "NO"
    assert factors["perfection_type"] == "frustration"
    assert factors["frustrating_planet"] == "Mercury"
    assert any("Mercury aspects Mars before significator perfection" in rule for rule in rules)
    assert any("Moon not void of course" in rule for rule in rules)


def test_funding_question_replays_as_affirmative_same_matter_unity_case():
    payload, final = _replay_fixture("funding_same_ruler.json")
    rules = _reasoning_rules(final)

    assert payload["question"] == "Will we secure a lead investor for our seed round before November?"
    assert final["result"] == "YES"
    assert final["traditional_factors"]["querent_strength"] == 3
    assert final["traditional_factors"]["quesited_strength"] == 3
    assert any("Shared Significator: Venus rules both houses 1 and 8" in rule for rule in rules)
    assert any("Same planet rules both significators" in rule for rule in rules)
    assert any("confidence only" in rule for rule in rules)


def test_education_exam_question_replays_as_affirmative_examiner_perfection_case():
    payload, final = _replay_fixture("physiotherapy_exam_yes.json")
    rules = _reasoning_rules(final)

    assert payload["question"] == "Will I pass my physiotherapy exam?"
    assert final["result"] == "YES"
    assert final["traditional_factors"]["perfection_type"] == "moon_sun_education"
    assert any("Moon (co-significator) applying Trine to Sun (examiner/authority)" in rule for rule in rules)
    assert any("Moon not void of course" in rule for rule in rules)


def test_education_admission_question_replays_as_negative_no_perfection_case():
    payload, final = _replay_fixture("masters_no_perfection.json")
    rules = _reasoning_rules(final)

    assert payload["question"] == "Will I be admitted to the master's program this cycle?"
    assert final["result"] == "NO"
    assert final["traditional_factors"]["perfection_type"] == "denial_secondary_balance"
    assert any("No perfection found - strict evaluation for event likelihood" in rule for rule in rules)
    assert any("No direct perfection found between Sun and Mars" in rule for rule in rules)


def test_quality_question_replays_as_negative_frustration_case():
    payload, final = _replay_fixture("pivot_frustration.json")
    rules = _reasoning_rules(final)

    assert payload["question"] == "Should we pivot to blog + RSS ?"
    assert final["result"] == "NO"
    assert final["traditional_factors"]["perfection_type"] == "frustration"
    assert final["traditional_factors"]["frustrating_planet"] == "Mars"
    assert any("Mars aspects Sun before significator perfection" in rule for rule in rules)
