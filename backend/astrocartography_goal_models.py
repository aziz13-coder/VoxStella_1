from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Sequence

from astrocartography_resource_paths import resolve_astrocartography_resource_path


GOAL_MODEL_PATH = resolve_astrocartography_resource_path("place_goal_models.runtime.json")
DEFAULT_GOAL_MODEL_SCHEMA_PATH = resolve_astrocartography_resource_path("place_goal_model.schema.json")
SUPPORTED_SCHEMA_VERSION = 2


class GoalModelValidationError(ValueError):
    pass


def _schema_path_for(payload_path: Path) -> Path:
    adjacent = payload_path.with_name("place_goal_model.schema.json")
    return adjacent if adjacent.exists() else DEFAULT_GOAL_MODEL_SCHEMA_PATH


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _resolve_schema_ref(root_schema: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not str(ref).startswith("#/"):
        raise GoalModelValidationError(f"Unsupported external schema reference: {ref}")
    node: Any = root_schema
    for token in str(ref)[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise GoalModelValidationError(f"Unresolvable schema reference: {ref}")
        node = node[token]
    if not isinstance(node, dict):
        raise GoalModelValidationError(f"Schema reference does not resolve to an object: {ref}")
    return node


def _validate_schema_value(
    value: Any,
    schema: Dict[str, Any],
    root_schema: Dict[str, Any],
    path: str,
) -> None:
    if "$ref" in schema:
        _validate_schema_value(value, _resolve_schema_ref(root_schema, str(schema["$ref"])), root_schema, path)
        return

    if "oneOf" in schema:
        successes = 0
        errors: List[str] = []
        for candidate in schema.get("oneOf") or []:
            try:
                _validate_schema_value(value, candidate, root_schema, path)
                successes += 1
            except GoalModelValidationError as exc:
                errors.append(str(exc))
        if successes != 1:
            detail = "; ".join(errors[:2])
            raise GoalModelValidationError(f"{path}: expected exactly one schema branch; {detail}")
        return

    if "const" in schema and value != schema.get("const"):
        raise GoalModelValidationError(f"{path}: expected constant {schema.get('const')!r}, found {value!r}")
    if "enum" in schema and value not in (schema.get("enum") or []):
        raise GoalModelValidationError(f"{path}: {value!r} is not one of {schema.get('enum')!r}")

    expected_types = schema.get("type")
    if expected_types is not None:
        type_names = [expected_types] if isinstance(expected_types, str) else list(expected_types)
        if not any(_type_matches(value, str(type_name)) for type_name in type_names):
            raise GoalModelValidationError(f"{path}: expected type {type_names!r}, found {type(value).__name__}")

    if isinstance(value, dict):
        required = [str(item) for item in (schema.get("required") or [])]
        missing = [item for item in required if item not in value]
        if missing:
            raise GoalModelValidationError(f"{path}: missing required fields {missing!r}")
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            unknown = sorted(str(key) for key in value if key not in properties)
            if unknown:
                raise GoalModelValidationError(f"{path}: unknown fields {unknown!r}")
        for key, child in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                _validate_schema_value(child, child_schema, root_schema, f"{path}.{key}")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(value) < int(min_items):
            raise GoalModelValidationError(f"{path}: expected at least {min_items} items")
        if max_items is not None and len(value) > int(max_items):
            raise GoalModelValidationError(f"{path}: expected at most {max_items} items")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(serialized) != len(set(serialized)):
                raise GoalModelValidationError(f"{path}: duplicate array items are not allowed")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema_value(item, item_schema, root_schema, f"{path}[{index}]")

    if isinstance(value, str):
        if schema.get("minLength") is not None and len(value) < int(schema["minLength"]):
            raise GoalModelValidationError(f"{path}: value is shorter than {schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(str(pattern), value) is None:
            raise GoalModelValidationError(f"{path}: {value!r} does not match {pattern!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if schema.get("minimum") is not None and float(value) < float(schema["minimum"]):
            raise GoalModelValidationError(f"{path}: value is below minimum {schema['minimum']}")
        if schema.get("maximum") is not None and float(value) > float(schema["maximum"]):
            raise GoalModelValidationError(f"{path}: value is above maximum {schema['maximum']}")
        if schema.get("exclusiveMinimum") is not None and float(value) <= float(schema["exclusiveMinimum"]):
            raise GoalModelValidationError(f"{path}: value must exceed {schema['exclusiveMinimum']}")
        if schema.get("exclusiveMaximum") is not None and float(value) >= float(schema["exclusiveMaximum"]):
            raise GoalModelValidationError(f"{path}: value must be below {schema['exclusiveMaximum']}")


def _validate_payload_semantics(payload: Dict[str, Any]) -> None:
    models = payload.get("models")
    if not isinstance(models, list) or not models:
        raise GoalModelValidationError("models: expected a non-empty list")
    if any(not isinstance(model, dict) for model in models):
        raise GoalModelValidationError("models: every entry must be an object")

    ids: Dict[str, Dict[str, Any]] = {}
    for index, model in enumerate(models):
        model_id = str(model.get("id") or "").strip().lower()
        if model_id in ids:
            raise GoalModelValidationError(f"models[{index}].id: duplicate model id {model_id!r}")
        ids[model_id] = model

        component_ids: set[str] = set()
        for component_index, component in enumerate(model.get("score_components") or []):
            component_id = str(component.get("component_id") or "").strip().lower()
            if component_id in component_ids:
                raise GoalModelValidationError(
                    f"models[{index}]({model_id}).score_components[{component_index}].component_id: "
                    f"duplicate id {component_id!r}"
                )
            component_ids.add(component_id)

        normalization = model.get("normalization") or {}
        min_score = normalization.get("min_score")
        max_score = normalization.get("max_score")
        if min_score is not None and max_score is not None and float(min_score) >= float(max_score):
            raise GoalModelValidationError(
                f"models[{index}]({model_id}).normalization: min_score must be below max_score"
            )

        for component_index, component in enumerate(model.get("score_components") or []):
            if component.get("kind") != "constraint":
                continue
            adjustments = [
                key
                for key in ("multiplier", "add", "cap_score")
                if component.get(key) is not None
            ]
            if len(adjustments) != 1:
                raise GoalModelValidationError(
                    f"models[{index}]({model_id}).score_components[{component_index}]: "
                    "constraint requires exactly one of multiplier, add, or cap_score"
                )

    for index, model in enumerate(models):
        model_id = str(model.get("id") or "").strip().lower()
        composition = model.get("composition") or {}
        if str(composition.get("mode") or "") != "specialist_residual":
            continue
        parent_id = str(composition.get("parent_id") or "").strip().lower()
        if parent_id == model_id:
            raise GoalModelValidationError(f"models[{index}]({model_id}).composition: self-parenting is invalid")
        parent = ids.get(parent_id)
        if parent is None:
            raise GoalModelValidationError(
                f"models[{index}]({model_id}).composition.parent_id: unknown parent {parent_id!r}"
            )
        if str((parent.get("composition") or {}).get("mode") or "") != "standalone":
            raise GoalModelValidationError(
                f"models[{index}]({model_id}).composition.parent_id: specialist chains are not supported"
            )
        if str(parent.get("score_polarity") or "") != str(model.get("score_polarity") or ""):
            raise GoalModelValidationError(
                f"models[{index}]({model_id}).composition: parent and specialist score polarity must match"
            )
        if str(model.get("status") or "") == "active" and str(parent.get("status") or "") != "active":
            raise GoalModelValidationError(
                f"models[{index}]({model_id}).composition: an active specialist requires an active parent"
            )


def validate_goal_model_payload(
    payload: Dict[str, Any],
    *,
    schema: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise GoalModelValidationError("Astrocartography goal model payload must be a JSON object")
    schema_version = payload.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise GoalModelValidationError(
            f"Unsupported astrocartography goal model schema_version {schema_version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    root_schema = schema or json.loads(DEFAULT_GOAL_MODEL_SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(root_schema, dict):
        raise GoalModelValidationError("Astrocartography goal model schema must be a JSON object")
    models = payload.get("models")
    if not isinstance(models, list):
        raise GoalModelValidationError("Astrocartography goal model payload missing models list")
    for index, model in enumerate(models):
        _validate_schema_value(model, root_schema, root_schema, f"models[{index}]")
    _validate_payload_semantics(payload)
    return payload


@lru_cache(maxsize=8)
def _load_goal_model_payload_cached(
    path_str: str,
    mtime_ns: int,
    file_size: int,
    schema_path_str: str,
    schema_mtime_ns: int,
    schema_file_size: int,
) -> Dict[str, Any]:
    del mtime_ns, file_size, schema_mtime_ns, schema_file_size
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path_str).read_text(encoding="utf-8"))
    return validate_goal_model_payload(payload, schema=schema)


def _stat_signature(path: Path) -> Sequence[int]:
    try:
        stat = path.stat()
        return int(getattr(stat, "st_mtime_ns", 0)), int(getattr(stat, "st_size", 0))
    except Exception:
        return 0, 0


def load_goal_model_payload() -> Dict[str, Any]:
    path = GOAL_MODEL_PATH
    schema_path = _schema_path_for(path)
    mtime_ns, file_size = _stat_signature(path)
    schema_mtime_ns, schema_file_size = _stat_signature(schema_path)
    return _load_goal_model_payload_cached(
        str(path),
        mtime_ns,
        file_size,
        str(schema_path),
        schema_mtime_ns,
        schema_file_size,
    )


def list_goal_models(*, include_deprecated: bool = False) -> List[Dict[str, Any]]:
    payload = load_goal_model_payload()
    models = payload.get("models") or []
    if include_deprecated:
        return list(models)
    return [
        model
        for model in models
        if str(model.get("status") or "").strip().lower() != "deprecated"
    ]


def get_goal_model(goal_id: str) -> Dict[str, Any]:
    goal_id = str(goal_id or "").strip().lower()
    for model in list_goal_models(include_deprecated=True):
        if str(model.get("id") or "").strip().lower() == goal_id:
            return model
    raise KeyError(f"Unknown astrocartography goal model: {goal_id}")


def get_active_goal_model(goal_id: str) -> Dict[str, Any]:
    model = get_goal_model(goal_id)
    if str(model.get("status") or "").strip().lower() != "active":
        raise KeyError(f"Astrocartography goal model is not active: {goal_id}")
    return model
