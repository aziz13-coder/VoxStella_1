from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from weather_resource_paths import resolve_weather_resource_path


_FAMILY_MODELS_PATH = resolve_weather_resource_path("weather_family_models.runtime.json")
_REFERENCE_RUNTIME_PATH = resolve_weather_resource_path("weather_reference_runtime.json")


def _load_json_object(path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Weather runtime asset must be a JSON object: {path}")
    return payload


@lru_cache(maxsize=1)
def load_weather_family_models() -> Dict[str, Any]:
    payload = _load_json_object(_FAMILY_MODELS_PATH)
    if not isinstance(payload.get("families"), list):
        raise ValueError("Weather family asset missing families")
    return payload


@lru_cache(maxsize=1)
def load_weather_reference_runtime() -> Dict[str, Any]:
    payload = _load_json_object(_REFERENCE_RUNTIME_PATH)
    if not isinstance(payload.get("layer_definitions"), list):
        raise ValueError("Weather reference runtime missing layer_definitions")
    return payload


def get_weather_family_definitions() -> List[Dict[str, Any]]:
    return list(load_weather_family_models().get("families") or [])


def get_weather_layer_definitions() -> List[Dict[str, Any]]:
    return list(load_weather_reference_runtime().get("layer_definitions") or [])


def get_weather_source_index() -> Dict[str, Dict[str, Any]]:
    source_index = load_weather_reference_runtime().get("source_index") or {}
    if not isinstance(source_index, dict):
        raise ValueError("Weather reference runtime missing source_index")
    return source_index


def get_weather_reference_notes() -> Dict[str, Any]:
    notes = load_weather_reference_runtime().get("doctrine_notes") or {}
    if not isinstance(notes, dict):
        raise ValueError("Weather reference runtime missing doctrine_notes")
    return notes
