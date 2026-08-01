import json
from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

import forensic_house_system_selection_runner as selector


def _development_dataset(tmp_path: Path, role: str = "development") -> Path:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"evaluation_role": role, "cases": []}), encoding="utf-8")
    return path


def test_selection_uses_declared_weighted_metrics_and_stable_ranking(monkeypatch, tmp_path):
    dataset_path = _development_dataset(tmp_path)

    def _fake_suite(_paths, *, house_system_code, **_kwargs):
        metrics = {
            "R": (0.80, 0.60, 0.50),
            "P": (0.70, 0.90, 0.50),
        }[house_system_code]
        return {
            "case_count": 10,
            "route_error_count": 0,
            "primary_axis_metrics": {
                "labeled_balanced_accuracy": metrics[0],
                "micro_recall": 0.5,
                "explicit_contradiction_specificity": 0.9,
            },
            "secondary_survivability_metrics": {"partial_credit_accuracy": metrics[1]},
            "relationship_status_metrics": {"macro_f1": metrics[2]},
        }

    monkeypatch.setattr(selector, "run_statistical_benchmark_suite", _fake_suite)

    report = selector.run_house_system_selection([dataset_path], house_system_codes=["P", "R"])

    assert report["winner"]["house_system_code"] == "P"
    assert report["winner"]["selection_score"] == 0.74
    assert [row["house_system_code"] for row in report["rankings"]] == ["P", "R"]
    assert report["evaluation_design"]["uses_locked_holdout"] is False


def test_selection_rejects_holdout_and_retrospective_datasets(tmp_path):
    for role in ("locked_external_holdout_v1", "development_retrospective_only"):
        dataset_path = _development_dataset(tmp_path, role=role)
        with pytest.raises(ValueError, match="tuning is prohibited"):
            selector.run_house_system_selection([dataset_path], house_system_codes=["R"])


def test_route_errors_make_a_house_system_ineligible(monkeypatch, tmp_path):
    dataset_path = _development_dataset(tmp_path)

    def _fake_suite(_paths, *, house_system_code, **_kwargs):
        return {
            "case_count": 1,
            "route_error_count": 1 if house_system_code == "P" else 0,
            "primary_axis_metrics": {"labeled_balanced_accuracy": 1.0},
            "secondary_survivability_metrics": {"partial_credit_accuracy": 1.0},
            "relationship_status_metrics": {"macro_f1": 1.0},
        }

    monkeypatch.setattr(selector, "run_statistical_benchmark_suite", _fake_suite)

    report = selector.run_house_system_selection([dataset_path], house_system_codes=["P", "R"])

    assert report["winner"]["house_system_code"] == "R"
    failed = next(row for row in report["rankings"] if row["house_system_code"] == "P")
    assert failed["eligible"] is False
    assert failed["selection_score"] is None
