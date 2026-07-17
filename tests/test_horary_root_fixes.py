from __future__ import annotations

from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.relationship_doctrine import (  # noqa: E402
    analyze_relationship_question_text,
    evaluate_relationship_affection_snapshot,
)
from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer  # noqa: E402
from backend.taxonomy import Category  # noqa: E402
from tests.horary_external_cunning_man_utils import (  # noqa: E402
    build_external_case_payload,
    load_external_replay_corpus,
    replay_external_case,
)
from backend.horary_engine.serialization import deserialize_chart_for_evaluation  # noqa: E402
from backend.horary_engine.engine import EnhancedTraditionalHoraryJudgmentEngine  # noqa: E402


CORPUS = {case["id"]: case for case in load_external_replay_corpus()}


def test_relationship_affection_questions_are_split_from_event_questions():
    analysis = analyze_relationship_question_text("will x and i like one another romantically?")
    assert analysis["family"] == "affection"
    assert analysis["requires_mutuality"] is True

    outcome = analyze_relationship_question_text("will we reconcile and get back together?")
    assert outcome["family"] == "outcome"


def test_affection_snapshot_denies_one_way_reception_for_mutual_liking():
    evaluation = evaluate_relationship_affection_snapshot(
        {
            "family": "affection",
            "mutual": "none",
            "one_way": ["Saturn↦Sun(sign)"],
            "display_text": "Saturn receives Sun by domicile",
            "perfects": True,
            "aspect_name": "Conjunction",
            "querent_name": "Sun",
            "quesited_name": "Saturn",
            "querent_dignity": -7,
            "quesited_dignity": 2,
            "quesited_solar_condition": "Under the Beams",
            "quesited_retrograde": False,
        }
    )

    assert evaluation["applies"] is True
    assert evaluation["result"] == "NO"
    assert any("One-way reception only" in entry["rule"] for entry in evaluation["reasoning"])


def test_pope_death_question_routes_to_turned_ninth_and_its_eighth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the Pope die in the next few days?")

    assert analysis["question_type"] == Category.DEATH
    assert analysis["third_person_analysis"]["subject_house"] == 9
    assert analysis["relevant_houses"] == [9, 4]


def test_career_review_routes_to_tenth_not_sixth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get a good yearly review of my work?")

    assert analysis["question_type"] == Category.CAREER
    assert analysis["relevant_houses"] == [1, 10]
    assert analysis["significators"]["quesited_house"] == 10
    assert analysis["economic_analysis"]["family"] == "career_review"


def test_tenant_payment_turns_to_tenant_and_tenant_money():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will my tenant send full payment?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["tenant_house"] == 7
    assert analysis["significators"]["tenant_money_house"] == 8


def test_bet_profit_routes_to_winnings_not_querents_money():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I profit from this bet?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 2, 8]
    assert analysis["significators"]["quesited_house"] == 8
    assert analysis["significators"]["bookmaker_house"] == 7


def test_business_profit_routes_to_tenth_and_eleventh():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will investing in this business prove profitable for me?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 10, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["business_house"] == 10
    assert analysis["significators"]["profit_house"] == 11


def test_bank_foreclosure_routes_to_contracting_party():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will the bank foreclose?")

    assert analysis["question_type"] == Category.MONEY
    assert analysis["relevant_houses"] == [1, 7]
    assert analysis["significators"]["quesited_house"] == 7
    assert analysis["significators"]["counterparty_house"] == 7


def test_friend_house_question_turns_to_eleventh():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should I move to my friend's house?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 11]
    assert analysis["significators"]["quesited_house"] == 11
    assert analysis["significators"]["property_family"] == "friend_house_move"


def test_property_purchase_advisability_uses_fourth_and_tenth():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Should I buy this flat?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 4, 10]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["counterparty_house"] == 7
    assert analysis["significators"]["profit_house"] == 10


def test_rental_question_keeps_owner_and_property_in_frame():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will we rent the house?")

    assert analysis["question_type"] == Category.PROPERTY
    assert analysis["relevant_houses"] == [1, 7, 4]
    assert analysis["significators"]["quesited_house"] == 4
    assert analysis["significators"]["seller_house"] == 7


def test_external_romance_replay_now_aligns_with_source_verdict():
    replayed = replay_external_case(CORPUS["x_romantically_article_spec"])

    assert replayed["verdict"] == "NO"
    assert replayed["perfection_type"] == "relationship_affection_balance"
    assert any("Relationship family: affection/reciprocity" in rule for rule in replayed["reasoning"])


def test_external_pope_replay_uses_turned_houses_and_denies_without_death_perfection():
    payload = build_external_case_payload(CORPUS["pope_die_article_spec"])
    chart = deserialize_chart_for_evaluation(payload["chart_data"])
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    question_analysis = engine.question_analyzer.analyze_question(payload["question"])

    assert question_analysis["question_type"] == Category.DEATH
    assert question_analysis["relevant_houses"] == [9, 4]

    significators = engine._identify_significators(chart, question_analysis)
    assert significators["querent_house"] == 9
    assert significators["quesited_house"] == 4

    replayed = replay_external_case(CORPUS["pope_die_article_spec"])
    assert replayed["verdict"] == "NO"
    assert replayed["perfection_type"] == "none"
    assert any("Querent: Moon (ruler of 9), Quesited: Jupiter (ruler of 4)" in rule for rule in replayed["reasoning"])


def test_higher_education_admission_routes_to_ninth_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("Will I get into a university in the USA?")

    assert analysis["question_type"] == Category.EDUCATION
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9


def test_first_person_higher_level_exams_route_to_ninth_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("How will I do in my exams?")

    assert analysis["question_type"] == Category.EDUCATION
    assert analysis["relevant_houses"] == [1, 9]
    assert analysis["significators"]["quesited_house"] == 9


def test_train_arrival_routes_to_short_travel_third_house():
    analyzer = TraditionalHoraryQuestionAnalyzer()
    analysis = analyzer.analyze_question("What time will the train arrive?")

    assert analysis["question_type"] == Category.TRAVEL
    assert analysis["relevant_houses"] == [1, 3]
    assert analysis["significators"]["quesited_house"] == 3
