from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from astrocartography_resource_paths import resolve_astrocartography_resource_path

GOAL_MODEL_PATH = resolve_astrocartography_resource_path("place_goal_models.runtime.json")


@lru_cache(maxsize=8)
def _load_goal_model_payload_cached(path_str: str, mtime_ns: int, file_size: int) -> Dict[str, Any]:
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Astrocartography goal model payload must be a JSON object")
    return payload


def load_goal_model_payload() -> Dict[str, Any]:
    path = GOAL_MODEL_PATH
    try:
        stat = path.stat()
        mtime_ns = int(getattr(stat, "st_mtime_ns", 0))
        file_size = int(getattr(stat, "st_size", 0))
    except Exception:
        mtime_ns = 0
        file_size = 0
    return _load_goal_model_payload_cached(str(path), mtime_ns, file_size)


def list_goal_models() -> List[Dict[str, Any]]:
    payload = load_goal_model_payload()
    models = payload.get("models") or []
    if not isinstance(models, list):
        raise ValueError("Astrocartography goal model payload missing models list")
    return [model for model in models if isinstance(model, dict)]


def get_goal_model(goal_id: str) -> Dict[str, Any]:
    goal_id = str(goal_id or "").strip().lower()
    for model in list_goal_models():
        if str(model.get("id") or "").strip().lower() == goal_id:
            return model
    raise KeyError(f"Unknown astrocartography goal model: {goal_id}")
