from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrocartography_goal_models import list_goal_models
from astrocartography_model_stress import (
    evaluate_public_semantic_expectations,
    run_stress_suite,
)

STRESS_CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "stress_test_astrocartography_models.py"
)
stress_cli_main = runpy.run_path(str(STRESS_CLI_PATH))["main"]


def test_default_public_gate_contains_only_active_standalone_peers():
    report = run_stress_suite()
    inventory = {
        item["goal_id"]: item for item in report["model_inventory"]
    }
    public_ids = set(report["public_gate"]["model_ids"])

    assert public_ids
    assert public_ids == {
        goal_id
        for goal_id, item in inventory.items()
        if item["status"] == "active"
        and item["composition_mode"] == "standalone"
    }
    assert all(
        inventory[goal_id]["gate_bucket"] == "public_peer"
        for goal_id in public_ids
    )
    assert report["validation_scope"]["default_public_gate"] == (
        "active_standalone_peers_only"
    )


def test_every_catalog_model_has_an_explicit_gate_bucket_and_reason():
    report = run_stress_suite()
    catalog_ids = {
        str(model.get("id") or "")
        for model in list_goal_models(include_deprecated=True)
    }
    inventory = report["model_inventory"]
    inventory_ids = {item["goal_id"] for item in inventory}
    public_ids = set(report["public_gate"]["model_ids"])
    excluded_ids = {
        item["goal_id"] for item in report["model_exclusions"]
    }

    assert inventory_ids == catalog_ids
    assert public_ids.isdisjoint(excluded_ids)
    assert public_ids | excluded_ids == catalog_ids
    assert all(item["status"] for item in inventory)
    assert all(item["composition_mode"] for item in inventory)
    assert all(item["gate_bucket"] for item in inventory)
    assert all(item["gate_reason"] for item in inventory)


def test_public_peer_gate_uses_real_semantic_and_overlap_failures_only():
    report = run_stress_suite()
    public_ids = set(report["public_gate"]["model_ids"])

    assert all(
        pair["left"] in public_ids and pair["right"] in public_ids
        for pair in report["high_overlap_pairs"]
    )
    assert all(
        pair["similarity"] >= report["overlap_threshold"]
        for pair in report["high_overlap_pairs"]
    )
    assert report["gate_passed"] is (
        not report["expectation_failures"]
        and not report["high_overlap_pairs"]
    )
    assert report["public_gate"]["passed"] is report["gate_passed"]


def test_public_semantic_error_is_not_silently_ignored():
    scenario_results = [
        {
            "id": "forced_public_error",
            "label": "Forced Public Error",
            "expected_lead": "education",
            "expected": ["education"],
            "ranking": [
                {"goal_id": "communication", "raw_score": 2.0, "score": 60},
                {"goal_id": "education", "raw_score": 1.0, "score": 55},
            ],
        }
    ]
    inventory = {
        "education": {
            "status": "active",
            "composition_mode": "standalone",
            "gate_bucket": "public_peer",
            "gate_reason": "included",
        },
        "communication": {
            "status": "active",
            "composition_mode": "standalone",
            "gate_bucket": "public_peer",
            "gate_reason": "included",
        },
    }

    _, failures, exclusions = evaluate_public_semantic_expectations(
        scenario_results,
        public_peer_model_ids=["education", "communication"],
        inventory_by_id=inventory,
    )

    assert exclusions == []
    assert failures == [
        {
            "scenario": "forced_public_error",
            "expectation": "expected_lead",
            "expected_lead": "education",
            "top_id": "communication",
            "top_ids": ["communication", "education"],
        }
    ]


def test_intentional_parent_specialist_pairs_use_residual_checks_not_cosine():
    report = run_stress_suite()
    excluded_pairs = {
        (item["parent_id"], item["specialist_id"])
        for item in report["intentional_parent_specialist_pair_exclusions"]
    }
    active_checks = report["active_specialist_residuals"]["checks"]
    research_checks = report["non_public_research"]["residual_checks"]
    checks = [*active_checks, *research_checks]

    assert excluded_pairs
    assert {
        (check["parent_id"], check["specialist_id"]) for check in checks
    } == excluded_pairs
    assert all(
        check["method"] == "specialist_residual_vector"
        and check["raw_full_model_cosine_excluded"] is True
        and check["scenario_count"] == report["scenario_count"]
        and check["observed_max_abs_residual"]
        <= check["configured_max_abs_residual"] + 1e-6
        for check in checks
    )
    assert all(
        {pair["left"], pair["right"]} != {parent_id, specialist_id}
        for parent_id, specialist_id in excluded_pairs
        for pair in report["high_overlap_pairs"]
    )


def test_experimental_models_are_separate_non_public_research():
    report = run_stress_suite()
    research = report["non_public_research"]
    inventory = {
        item["goal_id"]: item for item in report["model_inventory"]
    }

    assert research["non_public"] is True
    assert research["affects_default_public_gate"] is False
    assert research["model_ids"]
    assert all(
        inventory[goal_id]["status"] == "experimental"
        and inventory[goal_id]["gate_bucket"] == "non_public_research"
        for goal_id in research["model_ids"]
    )
    assert all(
        scenario["semantic_assertions_applied"] is False
        for scenario in research["scenarios"]
    )


def test_requested_peer_overlap_threshold_is_enforced():
    strict = run_stress_suite(overlap_threshold=0.92)
    permissive = run_stress_suite(overlap_threshold=0.99)
    strict_pairs = {
        (pair["left"], pair["right"])
        for pair in strict["high_overlap_pairs"]
    }
    permissive_pairs = {
        (pair["left"], pair["right"])
        for pair in permissive["high_overlap_pairs"]
    }

    assert permissive_pairs <= strict_pairs
    assert all(
        pair["similarity"] >= permissive["overlap_threshold"]
        for pair in permissive["high_overlap_pairs"]
    )
    assert strict["public_gate"]["overlap_threshold"] == 0.92
    assert permissive["public_gate"]["overlap_threshold"] == 0.99


def test_stress_cli_is_loaded_from_the_explicit_repository_path():
    loaded_path = Path(stress_cli_main.__globals__["__file__"]).resolve()

    assert STRESS_CLI_PATH.is_file()
    assert loaded_path == STRESS_CLI_PATH.resolve()


def test_stress_cli_reports_sections_and_returns_public_gate_status(capsys):
    report = run_stress_suite(overlap_threshold=0.92)

    assert stress_cli_main(["--overlap-threshold", "0.92"]) == (
        0 if report["gate_passed"] else 1
    )
    output = capsys.readouterr().out
    assert "Default public gate: active standalone peers only" in output
    assert "Active specialist residual diagnostics" in output
    assert "Non-public experimental research" in output
    assert "Explicit default-gate exclusions" in output
    assert "Intentional parent/specialist cosine exclusions" in output
    assert "Scope: synthetic semantic fixtures only" in output
