# -*- coding: utf-8 -*-
"""
Simple knowledge-driven evaluator for forensic analysis.

Loads YAML rule files from knowledge/ and evaluates them against features.
Supports a small DSL:
  - Logical: all, any, not
  - Equality/inclusion: field: value | field: [v1, v2]
  - Numeric: field<=, field>=, field<, field>
  - Presence booleans: field: true/false
"""

from typing import Any, Dict, List, Tuple
import os
import glob
import math
import yaml

"""
Lightweight caching for knowledge and dictionary YAML loads.

We avoid re-reading files on every request by keeping a snapshot of
filenames + mtimes. If the snapshot is unchanged, we return the cached
result. This keeps behavior identical while improving latency.
"""

# Cache: dir_path -> (rules, snapshot map)
_KNOWLEDGE_CACHE: Dict[str, Tuple[List[Dict[str, Any]], Dict[str, float]]] = {}
# Cache: (dir_path, filename) -> (data, mtime)
_DICT_CACHE: Dict[Tuple[str, str], Tuple[Dict[str, Any], float]] = {}


def _snapshot_dir(dir_path: str) -> Dict[str, float]:
    snap: Dict[str, float] = {}
    try:
        for fp in glob.glob(os.path.join(dir_path, '*.yaml')):
            try:
                snap[os.path.abspath(fp)] = os.path.getmtime(fp)
            except Exception:
                # If mtime fails, omit file from snapshot
                continue
    except Exception:
        return {}
    return snap


def _same_snapshot(a: Dict[str, float], b: Dict[str, float]) -> bool:
    if len(a) != len(b):
        return False
    for k, v in a.items():
        if b.get(k) != v:
            return False
    return True


def _resolve(d: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    cur: Any = d
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def _get(d: Dict[str, Any], path: str) -> Any:
    return _resolve(d, path)[1]


def _cmp(field_val: Any, op: str, expected: Any) -> bool:
    try:
        if op == 'eq':
            if isinstance(expected, list):
                # If field is a list/set, match on any overlap; else membership
                if isinstance(field_val, (list, set, tuple)):
                    return any(v in set(field_val) for v in expected)
                return field_val in expected
            return field_val == expected
        if op == 'true':
            return bool(field_val) is True
        if op == 'false':
            return bool(field_val) is False
        # numeric comparisons
        v = float(field_val)
        e = float(expected)
        if op == 'lt':
            return v < e
        if op == 'lte':
            return v <= e
        if op == 'gt':
            return v > e
        if op == 'gte':
            return v >= e
    except Exception:
        return False
    return False


def _all_condition_states(states: List[bool | None]) -> bool | None:
    if not states:
        return False
    if any(state is False for state in states):
        return False
    if any(state is None for state in states):
        return None
    return True


def _any_condition_states(states: List[bool | None]) -> bool | None:
    if not states:
        return False
    if any(state is True for state in states):
        return True
    if any(state is None for state in states):
        return None
    return False


def _eval_condition_state(cond: Any, features: Dict[str, Any]) -> bool | None:
    if cond is None:
        return False
    if isinstance(cond, dict):
        # logical ops first
        if 'all' in cond:
            children = cond['all'] or []
            return _all_condition_states([_eval_condition_state(c, features) for c in children])
        if 'any' in cond:
            children = cond['any'] or []
            return _any_condition_states([_eval_condition_state(c, features) for c in children])
        if 'not' in cond:
            state = _eval_condition_state(cond['not'], features)
            return None if state is None else not state
        # field tests
        saw_missing = False
        for key, expected in cond.items():
            # support suffix operators: field<=, field>=, field<, field>, otherwise eq/true/false
            op = 'eq'
            field = key
            if key.endswith('<='):
                op = 'lte'; field = key[:-2]
            elif key.endswith('>='):
                op = 'gte'; field = key[:-2]
            elif key.endswith('<'):
                op = 'lt'; field = key[:-1]
            elif key.endswith('>'):
                op = 'gt'; field = key[:-1]
            elif isinstance(expected, bool):
                op = 'true' if expected else 'false'
            present, field_val = _resolve(features, field)
            # Missing is unknown, not false. Previously, ``field: false``
            # matched an absent path because bool(None) is False, allowing
            # incomplete feature payloads to satisfy rules accidentally.
            if not present:
                saw_missing = True
                continue
            if not _cmp(field_val, op, expected):
                return False
        return None if saw_missing else True
    if isinstance(cond, list):
        return _all_condition_states([_eval_condition_state(c, features) for c in cond])
    # unexpected literal -> truthy/falsey
    return bool(cond)


def _eval_condition(cond: Any, features: Dict[str, Any]) -> bool:
    # Unknown never satisfies a rule, including when nested under ``not``.
    return _eval_condition_state(cond, features) is True


def _validate_condition(cond: Any, *, location: str) -> None:
    """Reject ambiguous or vacuous rule conditions at knowledge-load time."""
    if isinstance(cond, list):
        if not cond:
            raise ValueError(f"{location} must not be an empty condition list")
        for index, child in enumerate(cond):
            _validate_condition(child, location=f"{location}[{index}]")
        return

    if not isinstance(cond, dict) or not cond:
        raise ValueError(f"{location} must be a non-empty mapping or list")

    logical_keys = {key for key in cond if key in {'all', 'any', 'not'}}
    if logical_keys:
        if len(cond) != 1 or len(logical_keys) != 1:
            raise ValueError(f"{location} mixes a logical operator with other conditions")
        operator = next(iter(logical_keys))
        child = cond[operator]
        if operator in {'all', 'any'}:
            if not isinstance(child, list) or not child:
                raise ValueError(f"{location}.{operator} must be a non-empty list")
            for index, nested in enumerate(child):
                _validate_condition(nested, location=f"{location}.{operator}[{index}]")
        else:
            _validate_condition(child, location=f"{location}.not")
        return

    for key, expected in cond.items():
        if not isinstance(key, str) or not key.strip().rstrip('<>'):
            raise ValueError(f"{location} contains an invalid feature path")
        if isinstance(expected, dict):
            raise ValueError(f"{location}.{key} has an unsupported mapping value")


def _validate_rule(rule: Any, *, source: str, index: int, seen_ids: set[str]) -> Dict[str, Any]:
    location = f"{source}: rule[{index}]"
    if not isinstance(rule, dict):
        raise ValueError(f"{location} must be a mapping")
    rule_id = rule.get('id')
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError(f"{location} requires a non-empty id")
    if rule_id in seen_ids:
        raise ValueError(f"{location} duplicates rule id {rule_id!r}")
    seen_ids.add(rule_id)
    _validate_condition(rule.get('condition'), location=f"{location}.condition")
    weight = rule.get('weight', 1)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)):
        raise ValueError(f"{location}.weight must be a finite number")
    evidence = rule.get('evidence') or []
    if not isinstance(evidence, list) or any(not isinstance(path, str) or not path for path in evidence):
        raise ValueError(f"{location}.evidence must be a list of feature paths")
    axis_hints = rule.get('axis_hints') or []
    if not isinstance(axis_hints, list) or any(not isinstance(axis, str) or not axis for axis in axis_hints):
        raise ValueError(f"{location}.axis_hints must be a list of axis identifiers")
    source_refs = rule.get('source_refs') or []
    if not isinstance(source_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in source_refs):
        raise ValueError(f"{location}.source_refs must be a list of non-empty source references")
    validated = dict(rule)
    validated['_source_file'] = source
    return validated


def load_knowledge(dir_path: str) -> List[Dict[str, Any]]:
    """Load all rule lists from knowledge/*.yaml with mtime snapshot caching."""
    try:
        cur_snap = _snapshot_dir(dir_path)
        cached = _KNOWLEDGE_CACHE.get(dir_path)
        if cached is not None:
            rules_cached, snap_cached = cached
            if _same_snapshot(cur_snap, snap_cached):
                return rules_cached
    except Exception:
        cur_snap = {}

    rules: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for fp in sorted(glob.glob(os.path.join(dir_path, '*.yaml'))):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or []
                if isinstance(data, list):
                    for index, rule in enumerate(data):
                        rules.append(
                            _validate_rule(
                                rule,
                                source=os.path.basename(fp),
                                index=index,
                                seen_ids=seen_ids,
                            )
                        )
        except Exception as exc:
            raise RuntimeError(f"Failed to load forensic knowledge file {fp}") from exc

    # Update cache on successful read
    try:
        _KNOWLEDGE_CACHE[dir_path] = (rules, cur_snap)
    except Exception:
        pass
    return rules


def load_planetary_meanings(dir_path: str) -> Dict[str, Any]:
    """Load planetary meanings with per-file mtime caching."""
    fp = os.path.join(dir_path, 'planetary_meanings.yaml')
    try:
        if not os.path.exists(fp):
            return {}
        m = os.path.getmtime(fp)
        key = (dir_path, 'planetary_meanings.yaml')
        cached = _DICT_CACHE.get(key)
        if cached is not None:
            data_cached, mtime_cached = cached
            if mtime_cached == m:
                return data_cached
        with open(fp, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            data = data if isinstance(data, dict) else {}
        _DICT_CACHE[key] = (data, m)
        return data
    except Exception:
        return {}


def load_dictionary(dir_path: str, filename: str) -> Dict[str, Any]:
    """Load an arbitrary YAML dictionary from knowledge/ with mtime caching."""
    fp = os.path.join(dir_path, filename)
    try:
        if not os.path.exists(fp):
            return {}
        m = os.path.getmtime(fp)
        key = (dir_path, filename)
        cached = _DICT_CACHE.get(key)
        if cached is not None:
            data_cached, mtime_cached = cached
            if mtime_cached == m:
                return data_cached
        with open(fp, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            data = data if isinstance(data, dict) else {}
        _DICT_CACHE[key] = (data, m)
        return data
    except Exception:
        return {}

def evaluate(features: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for rule in rules:
        try:
            cond = rule.get('condition')
            if _eval_condition(cond, features):
                finding = {
                    'id': rule.get('id'),
                    'title': rule.get('title'),
                    'category': rule.get('category'),
                    'weight': rule.get('weight', 1),
                    'rationale': rule.get('rationale'),
                    'scoring_eligible': rule.get('scoring', True) is not False,
                    'validation_status': rule.get('validation_status', 'unvalidated'),
                    'axis_hints': list(rule.get('axis_hints') or []),
                    'source_refs': list(rule.get('source_refs') or []),
                    'source_file': rule.get('_source_file'),
                    'evidence': {},
                }
                for path in rule.get('evidence') or []:
                    finding['evidence'][path] = _get(features, path)
                findings.append(finding)
        except Exception as exc:
            rule_id = rule.get('id') if isinstance(rule, dict) else None
            raise RuntimeError(f"Failed to evaluate forensic rule {rule_id!r}") from exc
    # sort by weight desc
    findings.sort(key=lambda x: x.get('weight', 0), reverse=True)
    return findings
