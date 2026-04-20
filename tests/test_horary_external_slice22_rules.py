from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402


def test_tenant_move_out_question_keeps_property_and_tenant_together():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("When will my tenant move out?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["property_family"] == "occupancy_change"
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7


def test_occupant_leave_property_question_stays_on_shared_occupancy_family():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will he leave the property?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["property_family"] == "occupancy_change"
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7


def test_eviction_question_keeps_home_and_landlord_visible():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get evicted/loose my Home?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 7]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["property_family"] == "eviction_risk"
    assert analysis["significators"]["property_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
