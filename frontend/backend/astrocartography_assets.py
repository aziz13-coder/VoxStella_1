from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict

from astrocartography_resource_paths import resolve_astrocartography_resource_path

ASSET_PATH = resolve_astrocartography_resource_path("interpretation_runtime.json")


@lru_cache(maxsize=1)
def load_astrocartography_assets() -> Dict[str, Any]:
    payload = json.loads(ASSET_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Astrocartography interpretation asset must be a JSON object")
    return payload


def get_range_policy() -> Dict[str, Any]:
    payload = load_astrocartography_assets()
    range_policy = payload.get("range_policy") or {}
    if not isinstance(range_policy, dict):
        raise ValueError("Astrocartography interpretation asset missing range_policy")
    return range_policy


def get_body_reference() -> Dict[str, Dict[str, Any]]:
    payload = load_astrocartography_assets()
    bodies = payload.get("bodies") or {}
    if not isinstance(bodies, dict):
        raise ValueError("Astrocartography interpretation asset missing bodies")
    return bodies


def get_angle_reference() -> Dict[str, Dict[str, Any]]:
    payload = load_astrocartography_assets()
    angles = payload.get("angles") or {}
    if not isinstance(angles, dict):
        raise ValueError("Astrocartography interpretation asset missing angles")
    return angles
