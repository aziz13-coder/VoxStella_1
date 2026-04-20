from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.horary_engine.engine import (  # noqa: E402
    EnhancedTraditionalHoraryJudgmentEngine,
    HoraryEngine,
    _evaluate_enhanced,
    _structure_reasoning,
    get_category_rules,
    resolve_category,
)
from backend.horary_engine.serialization import deserialize_chart_for_evaluation  # noqa: E402
import backend.horary_engine.engine as engine_module  # noqa: E402


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
QUESTION_FIXTURE_DIR = FIXTURE_ROOT / "horary_questions"
MANUAL_REVIEW_DIR = FIXTURE_ROOT / "horary_manual_review"
CORPUS_PATH = FIXTURE_ROOT / "horary_hard_test_corpus.json"


def load_hard_test_corpus() -> List[Dict[str, Any]]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _normalize_category(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _reasoning_rules(final_or_result: Dict[str, Any]) -> List[str]:
    return [
        entry.get("rule", "")
        for entry in final_or_result.get("reasoning", [])
        if isinstance(entry, dict)
    ]


def replay_serialized_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    engine = EnhancedTraditionalHoraryJudgmentEngine()
    chart = deserialize_chart_for_evaluation(payload["chart_data"])
    question_analysis = engine.question_analyzer.analyze_question(payload["question"])
    if payload.get("category"):
        analyzed_category = _normalize_category(question_analysis.get("question_type"))
        if payload["category"] != "general" or analyzed_category == "general":
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

    return {
        "question": payload["question"],
        "category": _normalize_category(question_analysis.get("question_type")),
        "verdict": final.get("result"),
        "confidence": final.get("confidence"),
        "perfection_type": (final.get("traditional_factors") or {}).get("perfection_type"),
        "reasoning": _reasoning_rules(final),
        "raw": final,
    }


def replay_hard_test_case(case: Dict[str, Any], monkeypatch=None) -> Dict[str, Any]:
    source_kind = case["source_kind"]

    if source_kind == "question_fixture":
        payload = json.loads((QUESTION_FIXTURE_DIR / case["source_file"]).read_text(encoding="utf-8"))
        return replay_serialized_payload(payload)

    if source_kind == "manual_review":
        payload = json.loads((MANUAL_REVIEW_DIR / case["source_file"]).read_text(encoding="utf-8"))
        return replay_serialized_payload(payload)

    if source_kind == "live_engine":
        if monkeypatch is None:
            raise RuntimeError("live_engine cases require pytest monkeypatch")

        monkeypatch.setattr(
            engine_module,
            "safe_geocode",
            lambda _location: (
                case["coordinates"]["lat"],
                case["coordinates"]["lon"],
                case["location"],
            ),
        )

        engine = HoraryEngine()
        settings = {
            "location": case["location"],
            "date": case["date"],
            "time": case["time"],
            "timezone": case["timezone"],
            "house_system_code": "R",
            "use_current_time": False,
        }

        with contextlib.redirect_stdout(io.StringIO()):
            result = engine.judge(case["question"], settings)

        return {
            "question": case["question"],
            "category": _normalize_category((result.get("question_analysis") or {}).get("question_type")),
            "verdict": result.get("judgment"),
            "confidence": result.get("confidence"),
            "perfection_type": (result.get("traditional_factors") or {}).get("perfection_type"),
            "reasoning": _reasoning_rules(result),
            "raw": result,
        }

    raise ValueError(f"Unsupported source_kind: {source_kind}")


# Backwards-compatible alias for older imports
_replay_serialized_payload = replay_serialized_payload
