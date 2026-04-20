from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from mundane_resource_paths import resolve_mundane_resource_path


_CHART_TYPES_PATH = resolve_mundane_resource_path("mundane_chart_types.runtime.json")
_DOMAIN_MODELS_PATH = resolve_mundane_resource_path("mundane_domain_models.runtime.json")
_COUNTRY_REGISTRY_PATH = resolve_mundane_resource_path("mundane_country_registry.runtime.json")
_REFERENCE_RUNTIME_PATH = resolve_mundane_resource_path("mundane_reference_runtime.json")


def _load_json_object(path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Mundane runtime asset must be a JSON object: {path}")
    return payload


@lru_cache(maxsize=1)
def load_mundane_chart_types() -> Dict[str, Any]:
    payload = _load_json_object(_CHART_TYPES_PATH)
    if not isinstance(payload.get("chart_types"), list):
        raise ValueError("Mundane chart type asset missing chart_types")
    return payload


@lru_cache(maxsize=1)
def load_mundane_domain_models() -> Dict[str, Any]:
    payload = _load_json_object(_DOMAIN_MODELS_PATH)
    if not isinstance(payload.get("domains"), list):
        raise ValueError("Mundane domain asset missing domains")
    return payload


@lru_cache(maxsize=1)
def load_mundane_country_registry() -> Dict[str, Any]:
    payload = _load_json_object(_COUNTRY_REGISTRY_PATH)
    if not isinstance(payload.get("polities"), list):
        raise ValueError("Mundane country registry missing polities")
    return payload


@lru_cache(maxsize=1)
def load_mundane_reference_runtime() -> Dict[str, Any]:
    payload = _load_json_object(_REFERENCE_RUNTIME_PATH)
    if not isinstance(payload.get("context_types"), list):
        raise ValueError("Mundane reference runtime missing context_types")
    return payload


def get_chart_type_definitions() -> List[Dict[str, Any]]:
    return list(load_mundane_chart_types().get("chart_types") or [])


def get_domain_definitions() -> List[Dict[str, Any]]:
    return list(load_mundane_domain_models().get("domains") or [])


def get_polity_definitions() -> List[Dict[str, Any]]:
    return list(load_mundane_country_registry().get("polities") or [])


def get_context_type_definitions() -> List[Dict[str, Any]]:
    return list(load_mundane_reference_runtime().get("context_types") or [])


def get_trigger_family_definitions() -> List[Dict[str, Any]]:
    return list(load_mundane_reference_runtime().get("trigger_families") or [])


def get_activation_watchpoints() -> List[Dict[str, Any]]:
    return list(load_mundane_reference_runtime().get("activation_watchpoints") or [])


def get_source_index() -> Dict[str, Dict[str, Any]]:
    source_index = load_mundane_reference_runtime().get("source_index") or {}
    if not isinstance(source_index, dict):
        raise ValueError("Mundane reference runtime missing source_index")
    return source_index


def get_reference_notes() -> Dict[str, Any]:
    notes = load_mundane_reference_runtime().get("doctrine_notes") or {}
    if not isinstance(notes, dict):
        raise ValueError("Mundane reference runtime missing doctrine_notes")
    return notes
