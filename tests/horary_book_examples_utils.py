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

from backend.horary_engine.engine import HoraryEngine  # noqa: E402
import backend.horary_engine.engine as engine_module  # noqa: E402


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
BOOK_REPLAY_CORPUS_PATH = FIXTURE_ROOT / "horary_book_examples_replay.json"


def load_book_replay_corpus() -> List[Dict[str, Any]]:
    return json.loads(BOOK_REPLAY_CORPUS_PATH.read_text(encoding="utf-8"))


def _reasoning_rules(result: Dict[str, Any]) -> List[str]:
    return [
        entry.get("rule", "")
        for entry in result.get("reasoning", [])
        if isinstance(entry, dict)
    ]


def _normalize_category(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, str) and value.startswith("Category."):
        return value.split(".", 1)[1].lower()
    return value


def _ascendant_sign(longitude: float) -> str:
    signs = [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    ]
    return signs[int((longitude % 360) // 30)]


def replay_book_case(case: Dict[str, Any]) -> Dict[str, Any]:
    coords = case["coordinates"]
    location_name = case["location_name"]
    original_geocode = getattr(engine_module, "safe_geocode")
    engine_module.safe_geocode = lambda _location: (coords["lat"], coords["lon"], location_name)

    try:
        engine = HoraryEngine()
        local_dt = str(case["local_dt"])
        date_text, time_text = local_dt.split("T", 1)
        settings = {
            "location": location_name,
            "date": date_text,
            "time": time_text[:5],
            "timezone": case["timezone"],
            "house_system_code": "R",
            "use_current_time": False,
        }

        with contextlib.redirect_stdout(io.StringIO()):
            result = engine.judge(case["question"], settings)
    finally:
        engine_module.safe_geocode = original_geocode

    question_analysis = result.get("question_analysis") or {}
    significators = question_analysis.get("significators") or {}
    asc = float(result.get("chart_data", {}).get("ascendant") or 0.0)

    return {
        "question": case["question"],
        "verdict": result.get("judgment"),
        "confidence": result.get("confidence"),
        "category": _normalize_category(question_analysis.get("question_type")),
        "houses": question_analysis.get("relevant_houses"),
        "significator_houses": {
            key: value
            for key, value in significators.items()
            if key in {"querent_house", "quesited_house", "subject_house", "death_house"}
        },
        "perfection_type": (result.get("traditional_factors") or {}).get("perfection_type"),
        "reasoning": _reasoning_rules(result),
        "ascendant": asc,
        "ascendant_degree_in_sign": asc % 30,
        "ascendant_sign": _ascendant_sign(asc),
        "raw": result,
    }
