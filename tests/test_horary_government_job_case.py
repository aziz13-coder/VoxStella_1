from pathlib import Path
import contextlib
import io
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.engine import HoraryEngine  # noqa: E402
import backend.horary_engine.engine as engine_module  # noqa: E402


def test_government_job_chart_replays_as_affirmative_occurrence_case(monkeypatch):
    monkeypatch.setattr(
        engine_module,
        "safe_geocode",
        lambda _location: (38.8950368, -77.0365427, "Washington, District of Columbia"),
    )

    engine = HoraryEngine()
    settings = {
        "location": "Washington, District of Columbia",
        "date": "2001-05-15",
        "time": "10:20",
        "timezone": "America/New_York",
        "house_system_code": "R",
        "use_current_time": False,
    }

    with contextlib.redirect_stdout(io.StringIO()):
        result = engine.judge("Will I get a job? (government position)", settings)

    rules = [entry.get("rule", "") for entry in result.get("reasoning", [])]

    assert result["judgment"] == "YES"
    assert result["confidence"] >= 60
    assert result["question_analysis"]["question_type"] == "career"
    assert result["question_analysis"]["relevant_houses"] == [1, 10]
    assert result["traditional_factors"]["perfection_type"] == "direct"
    assert result["chart_data"]["house_rulers"]["1"] == "Moon"
    assert result["chart_data"]["house_rulers"]["10"] == "Mars"
    assert any("Querent: Moon (ruler of 1), Quesited: Mars (ruler of 10)" in rule for rule in rules)
    assert any("Moon not void of course" in rule for rule in rules)
    assert any("Perfection: Applying major aspect present" in rule for rule in rules)
