from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import weather_prospective_benchmark_runner as runner


def test_run_prospective_suite_reports_scaffold_when_empty(monkeypatch):
    monkeypatch.setattr(runner, "load_prospective_cases", lambda **_: [])

    report = runner.run_prospective_suite()

    assert report["case_count"] == 0
    assert report["status"] == "scaffold_only"
    assert "not yet scored" in report["critical_answer"]
