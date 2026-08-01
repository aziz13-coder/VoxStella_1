from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

import forensic_statistical_benchmark_runner as runner


def test_axis_metrics_treat_case_axis_detection_as_primary_target():
    rows = [
        {
            "case_id": "case_one",
            "expected_axes": ["violence_homicide", "deception_coverup"],
            "matched_axes": ["violence_homicide"],
            "contradicted_axes": [],
        },
        {
            "case_id": "case_two",
            "expected_axes": ["abduction_missing_person"],
            "matched_axes": ["abduction_missing_person"],
            "contradictory_axes": ["child_victim"],
            "contradicted_axes": ["child_victim"],
        },
    ]

    metrics = runner.compute_axis_metrics(rows)

    assert metrics["runnable_case_count"] == 2
    assert metrics["aligned_case_count"] == 0
    assert metrics["partial_case_count"] == 1
    assert metrics["misaligned_case_count"] == 1
    assert metrics["expected_axis_count"] == 3
    assert metrics["matched_axis_count"] == 2
    assert metrics["micro_recall"] == 0.6667
    assert metrics["macro_recall"] == 0.6667
    assert metrics["negative_axis_count"] == 1
    assert metrics["true_negative_axis_count"] == 0
    assert metrics["specificity"] == 0.0
    assert metrics["balanced_accuracy"] == 0.3333
    assert metrics["false_positive_contradiction_count"] == 1
    assert metrics["per_axis"]["violence_homicide"]["recall"] == 1.0
    assert metrics["per_axis"]["deception_coverup"]["recall"] == 0.0
    assert metrics["per_axis"]["abduction_missing_person"]["recall"] == 1.0


def test_null_significance_reports_empirical_p_value_against_controls():
    observed = 0.75
    controls = [0.10, 0.25, 0.50, 0.74, 0.75, 0.80]

    result = runner.compute_null_significance(observed, controls)

    assert result["observed"] == 0.75
    assert result["control_count"] == 6
    assert result["empirical_p_value"] == 0.4286
    assert result["control_mean"] == 0.5233
    assert result["control_max"] == 0.8


def test_predicted_axes_include_trafficking_or_possession_context():
    payload = {
        "findings": [
            {
                "id": "victim_possession_context",
                "title": "Possession Or Value Motive",
                "category": "Victim Context",
                "axis_hints": ["trafficking_or_possession_context"],
                "rationale": "Victim ruler in the 2nd house: consider trafficking because the person is treated as a possession.",
            }
        ]
    }

    axes = runner.derive_predicted_axes(payload)

    assert "trafficking_or_possession_context" in axes


def test_predicted_axes_do_not_mine_alternative_outcomes_from_rationales():
    payload = {
        "findings": [
            {
                "title": "House context doctrine check",
                "category": "General",
                "rationale": (
                    "Victim near the immediate scene or residence; taken for trafficking as a possession; "
                    "communication issue with vehicle and short distance; family home and end of the matter; "
                    "party drinking dancing entertainment; routine disrupted by a stalker; suspect territory; "
                    "deceased person with financial disagreement; far away; public authorities and witness; "
                    "friends may know; enclosed area hidden and kidnapped."
                ),
            }
        ]
    }

    assert runner.derive_predicted_axes(payload) == []


def test_seeded_permutation_controls_honor_requested_count_and_are_reproducible():
    rows = [
        {
            "expected_axes": ["violence_homicide"] if index % 2 else ["accident_or_disaster"],
            "predicted_axes": ["violence_homicide"] if index < 3 else ["accident_or_disaster"],
            "contradictory_axes": [],
        }
        for index in range(6)
    ]

    first = runner._permutation_control_metric(
        rows,
        metric_key="micro_recall",
        max_controls=40,
        seed=123,
    )
    second = runner._permutation_control_metric(
        rows,
        metric_key="micro_recall",
        max_controls=40,
        seed=123,
    )

    assert len(first) == 40
    assert first == second


def test_statistical_runner_prioritizes_axis_detection_and_tracks_survivability(monkeypatch):
    def fake_route(_query):
        return {
            "status_code": 200,
            "payload": {
                "success": True,
                "findings": [
                    {
                        "title": "Homicide and hidden cover-up",
                        "category": "Violence",
                        "rationale": "Murder and concealment testimony.",
                    }
                ],
                "categories": {"Violence": 1},
                "survivability": {
                    "level": "Lower",
                    "outcome_band": "fatal_pressure_dominant",
                    "score": -5.0,
                    "light_mediation_impact": {
                        "effect": "recovery_support",
                        "score_delta": 0.25,
                        "level_changed": False,
                        "band_changed": False,
                        "visibility": "raw_only",
                    },
                },
                "relationship_status": {
                    "primary_label": "intimate_partner",
                    "labels": ["intimate_partner"],
                    "confidence": "Moderate",
                },
            },
        }

    monkeypatch.setattr(runner, "_call_forensic_route", fake_route)

    report = runner.run_statistical_benchmark_suite(
        include_control_cases=False,
        case_limit=1,
    )

    assert report["primary_target"] == "case_axis_detection"
    assert report["secondary_target"] == "survivability_outcome_direction"
    assert report["evaluation_design"]["axis_prediction_basis"] == "explicit_rule_id_category_mapping_v1"
    assert report["evaluation_design"]["uses_free_text_for_axis_prediction"] is False
    assert report["primary_axis_metrics"]["runnable_case_count"] == 1
    assert report["primary_axis_metrics"]["expected_axis_count"] >= 1
    assert report["primary_axis_metrics"]["matched_axis_count"] >= 1
    assert "secondary_survivability_metrics" in report
    assert report["secondary_survivability_metrics"]["scored_case_count"] == 1
    assert report["relationship_status_metrics"]["case_count"] == 1
    assert "macro_f1" in report["relationship_status_metrics"]
    assert report["light_mediation_calibration_metrics"]["case_count_with_signal"] == 1
    assert report["light_mediation_calibration_metrics"]["raw_delta_case_count"] == 1
    assert report["light_mediation_calibration_metrics"]["level_flip_count"] == 0
    assert report["light_mediation_calibration_metrics"]["visibility_counts"] == {"raw_only": 1}
    assert report["route_error_count"] == 0


def test_statistical_runner_can_override_house_system_for_sensitivity_scans(monkeypatch):
    captured_queries = []

    def fake_route(query):
        captured_queries.append(dict(query))
        return {
            "status_code": 200,
            "payload": {
                "success": True,
                "findings": [{"title": "Homicide", "category": "Violence"}],
                "categories": {"Violence": 1},
                "survivability": {
                    "level": "Lower",
                    "outcome_band": "fatal_pressure_dominant",
                },
                "relationship_status": {
                    "primary_label": "stranger_public",
                    "labels": ["stranger_public"],
                },
            },
        }

    monkeypatch.setattr(runner, "_call_forensic_route", fake_route)

    report = runner.run_statistical_benchmark_suite(
        include_control_cases=False,
        case_limit=1,
        house_system_code="P",
    )

    assert report["house_system_code"] == "P"
    assert captured_queries
    assert captured_queries[0]["house_system_code"] == "P"


def test_statistical_runner_excludes_september_11_event_but_not_ordinary_911_calls(tmp_path):
    dataset_path = tmp_path / "cases.json"
    runnable_query = {
        "mode": "manual",
        "datetime": "2020-01-01T12:00:00",
        "location": "Test",
        "timezone": "UTC",
        "latitude": "0",
        "longitude": "0",
    }
    dataset_path.write_text(
        """
        {
          "cases": [
            {
              "id": "september_11_attacks",
              "title": "September 11 attacks at the World Trade Center",
              "benchmark": {
                "replay_status": "runnable",
                "expected_primary_axes": ["violence_homicide"],
                "query": {
                  "mode": "manual",
                  "datetime": "2001-09-11T08:46:00",
                  "location": "New York",
                  "timezone": "America/New_York",
                  "latitude": "40.7128",
                  "longitude": "-74.0060"
                }
              }
            },
            {
              "id": "ordinary_911_call_case",
              "title": "Missing-person case anchored to a 911 call",
              "benchmark": {
                "replay_status": "runnable",
                "expected_primary_axes": ["abduction_missing_person"],
                "query": REPLACE_QUERY
              }
            }
          ]
        }
        """.replace("REPLACE_QUERY", __import__("json").dumps(runnable_query)),
        encoding="utf-8",
    )

    cases = runner.load_statistical_cases([dataset_path])

    assert [case["case_id"] for case in cases] == ["ordinary_911_call_case"]
    with pytest.raises(ValueError, match="Excluded forensic statistical benchmark case id"):
        runner.load_statistical_cases([dataset_path], case_id="september_11_attacks")


def test_relationship_status_metrics_prioritize_precision_and_exact_labels():
    rows = [
        {
            "case_id": "partner_case",
            "expected_relationship_labels": ["intimate_partner"],
            "predicted_relationship_labels": ["intimate_partner", "family"],
            "expected_primary_relationship": "intimate_partner",
            "predicted_primary_relationship": "intimate_partner",
        },
        {
            "case_id": "stranger_case",
            "expected_relationship_labels": ["stranger_public"],
            "predicted_relationship_labels": ["family"],
            "expected_primary_relationship": "stranger_public",
            "predicted_primary_relationship": "family",
        },
    ]

    metrics = runner.compute_relationship_status_metrics(rows)

    assert metrics["case_count"] == 2
    assert metrics["exact_match_rate"] == 0.0
    assert metrics["primary_accuracy"] == 0.5
    assert metrics["micro_precision"] == 0.3333
    assert metrics["micro_recall"] == 0.5
    assert metrics["micro_f1"] == 0.4
    assert metrics["per_label"]["family"]["false_positive"] == 2
    assert metrics["per_label"]["stranger_public"]["false_negative"] == 1


def test_relationship_metrics_ignore_cases_without_relationship_ground_truth():
    metrics = runner.compute_relationship_status_metrics(
        [
            {
                "case_id": "outcome_only",
                "expected_relationship_labels": [],
                "predicted_relationship_labels": ["stranger_public"],
            }
        ]
    )

    assert metrics["case_count"] == 0
    assert metrics["primary_accuracy"] is None
    assert metrics["macro_f1"] is None


def test_markdown_report_names_targets_and_significance():
    report = {
        "benchmark_id": "unit",
        "primary_target": "case_axis_detection",
        "secondary_target": "survivability_outcome_direction",
        "case_count": 2,
        "route_error_count": 0,
        "primary_axis_metrics": {
            "runnable_case_count": 2,
            "micro_recall": 0.75,
            "macro_recall": 0.625,
            "expected_axis_count": 4,
            "matched_axis_count": 3,
            "false_positive_contradiction_count": 1,
            "per_axis": {},
        },
        "secondary_survivability_metrics": {
            "scored_case_count": 2,
            "aligned_count": 1,
            "partial_count": 1,
            "misaligned_count": 0,
            "accuracy": 0.5,
        },
        "relationship_status_metrics": {
            "case_count": 2,
            "primary_accuracy": 0.5,
            "exact_match_rate": 0.0,
            "micro_precision": 0.3333,
            "micro_recall": 0.5,
            "micro_f1": 0.4,
            "macro_f1": 0.25,
            "per_label": {},
        },
        "light_mediation_calibration_metrics": {
            "case_count_with_signal": 2,
            "raw_delta_case_count": 2,
            "level_flip_count": 0,
            "band_flip_count": 0,
            "mean_abs_score_delta": 0.2,
            "max_abs_score_delta": 0.35,
            "visibility_counts": {"raw_only": 2},
        },
        "significance": {
            "axis_micro_recall": {
                "observed": 0.75,
                "control_count": 4,
                "control_mean": 0.25,
                "empirical_p_value": 0.2,
            }
        },
        "case_results": [],
    }

    markdown = runner.render_markdown_report(report)

    assert "# Forensic Statistical Benchmark Report" in markdown
    assert "Primary target: case-axis detection" in markdown
    assert "Secondary target: survivability/outcome direction" in markdown
    assert "Relationship Status" in markdown
    assert "Light Mediation Calibration" in markdown
    assert "Fixture-level empirical p-value" in markdown
    assert "not evidence of real-world forensic validity" in markdown
