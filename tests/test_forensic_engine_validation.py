from __future__ import annotations

from pathlib import Path

import pytest

from backend.forensic.engine import _eval_condition, evaluate, load_knowledge


def _write_rules(directory: Path, body: str) -> None:
    (directory / "rules.yaml").write_text(body, encoding="utf-8")


def test_missing_boolean_path_does_not_match_explicit_false() -> None:
    assert _eval_condition({"flags.retrograde": False}, {}) is False
    assert _eval_condition({"flags.retrograde": False}, {"flags": {"retrograde": False}}) is True


def test_negating_a_missing_path_remains_unknown_and_fails_closed() -> None:
    assert _eval_condition({"not": {"flags.retrograde": True}}, {}) is False
    assert _eval_condition({"not": {"flags.retrograde": True}}, {"flags": {"retrograde": False}}) is True


@pytest.mark.parametrize("condition", [{"all": []}, {"any": []}, []])
def test_empty_condition_groups_fail_closed(condition) -> None:
    assert _eval_condition(condition, {"anything": True}) is False


@pytest.mark.parametrize(
    "condition_yaml",
    [
        "all: []",
        "any: []",
        "all:\n      - flags.ready: true\n    flags.other: true",
    ],
)
def test_knowledge_loader_rejects_vacuous_or_ambiguous_conditions(
    tmp_path: Path,
    condition_yaml: str,
) -> None:
    _write_rules(
        tmp_path,
        f"""
- id: invalid_rule
  title: Invalid
  category: Test
  condition:
    {condition_yaml}
""",
    )

    with pytest.raises(RuntimeError, match="Failed to load forensic knowledge file"):
        load_knowledge(str(tmp_path))


def test_knowledge_loader_rejects_duplicate_rule_ids(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        """
- id: duplicate
  condition: {flags.ready: true}
- id: duplicate
  condition: {flags.ready: false}
""",
    )

    with pytest.raises(RuntimeError, match="Failed to load forensic knowledge file"):
        load_knowledge(str(tmp_path))


def test_knowledge_loader_rejects_invalid_source_references(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        """
- id: invalid_sources
  condition: {flags.ready: true}
  source_refs: "not-a-list"
""",
    )

    with pytest.raises(RuntimeError, match="Failed to load forensic knowledge file"):
        load_knowledge(str(tmp_path))


def test_finding_exposes_scoring_and_validation_metadata() -> None:
    findings = evaluate(
        {"flags": {"ready": True}},
        [
            {
                "id": "exploratory_rule",
                "condition": {"flags.ready": True},
                "scoring": False,
                "validation_status": "case_derived_exploratory",
                "source_refs": ["local: test source, p. 1"],
                "_source_file": "rules.yaml",
            }
        ],
    )

    assert findings == [
        {
            "id": "exploratory_rule",
            "title": None,
            "category": None,
            "weight": 1,
            "rationale": None,
            "scoring_eligible": False,
            "validation_status": "case_derived_exploratory",
            "axis_hints": [],
            "source_refs": ["local: test source, p. 1"],
            "source_file": "rules.yaml",
            "evidence": {},
        }
    ]
