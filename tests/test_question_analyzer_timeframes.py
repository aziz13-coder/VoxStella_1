from datetime import datetime

from backend.question_analyzer import TraditionalHoraryQuestionAnalyzer


def test_this_month_uses_chart_local_datetime():
    analyzer = TraditionalHoraryQuestionAnalyzer()

    analysis = analyzer.analyze_question(
        "Will my partner and I reconcile this month?",
        reference_datetime=datetime.fromisoformat("2009-04-15T18:17:00-04:00"),
    )

    timeframe = analysis["timeframe_analysis"]
    assert timeframe["type"] == "this_month"
    assert timeframe["end_date"] == datetime(2009, 4, 30, 23, 59, 59, 999999)
    assert timeframe["window_days"] == 16


def test_this_month_never_returns_a_nonpositive_window_on_last_day():
    analyzer = TraditionalHoraryQuestionAnalyzer()

    analysis = analyzer.analyze_question(
        "Will this happen this month?",
        reference_datetime=datetime(2026, 7, 31, 23, 30),
    )

    assert analysis["timeframe_analysis"]["window_days"] == 1
