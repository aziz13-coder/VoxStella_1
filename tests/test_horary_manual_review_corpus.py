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
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "horary_manual_review"


def _replay_manual_case(name: str):
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


def _rules(final):
    return [entry.get("rule", "") for entry in final.get("reasoning", [])]


def test_conception_manual_review_case_surfaces_pregnancy_support_signals():
    payload, final = _replay_manual_case("conceive_review.json")
    rules = _rules(final)

    assert payload["question"] == "Will I conceive?"
    assert final["traditional_factors"]["perfection_type"] == "pregnancy_sufficiency"
    assert final["traditional_factors"]["reception"] == "unilateral"
    assert any("L1" in rule and "L5" in rule for rule in rules)
    assert any("Moon not void of course" in rule for rule in rules)


def test_marriage_manual_review_case_preserves_mixed_secondary_balance():
    payload, final = _replay_manual_case("marry_review.json")
    rules = _rules(final)

    assert payload["question"] == "Will he marry me?"
    assert (
        final["traditional_factors"]["perfection_type"]
        == "mixed_or_inconclusive_secondary_balance"
    )
    assert final["traditional_factors"]["reception"]["mutual"] == "mixed_reception"
    assert any("No perfection found - strict evaluation for event likelihood" in rule for rule in rules)
    assert any("mixed_reception" in rule for rule in rules)
    assert any("Moon Trine Venus" in rule for rule in rules)
    assert any("deg/day" in rule for rule in rules)
    assert not any("FLAG: MOON_NEXT_DECISIVE" in rule for rule in rules)


def test_divorce_manual_review_case_replays_secondary_balance_denial():
    payload, final = _replay_manual_case("divorce_review.json")
    rules = _rules(final)

    assert payload["question"] == "Will there be a divorce?"
    assert final["traditional_factors"]["perfection_type"] == "denial_secondary_balance"
    assert any("No perfection found - strict evaluation for event likelihood" in rule for rule in rules)
    assert any("No direct perfection found between Jupiter and Mercury" in rule for rule in rules)


def test_property_investment_manual_review_case_surfaces_profit_vs_property_doctrine():
    payload, final = _replay_manual_case("property_invest_review.json")
    rules = _rules(final)

    assert payload["question"] == "should I invest in this house?"
    assert final["traditional_factors"]["property_family"] == "advisability_profit"
    assert any("Property family: advisability/profit" in rule for rule in rules)
    assert any("10th-house profit testimony" in rule for rule in rules)
    assert any("4th-house property condition" in rule for rule in rules)


def test_divorce_question_routes_to_relationship_category():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will there be a divorce?")

    assert analysis["question_type"] == Category.RELATIONSHIP


def test_reconciliation_manual_review_case_surfaces_explicit_prohibition():
    payload, final = _replay_manual_case("reconcile_review.json")
    rules = _rules(final)

    assert payload["question"] == "Will my partner and I reconcile this month?"
    assert final["traditional_factors"]["perfection_type"] == "prohibition"
    assert any("Prohibition:" in rule for rule in rules)
    assert any("pre-empting the significators' perfection" in rule for rule in rules)
