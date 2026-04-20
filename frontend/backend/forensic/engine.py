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


def _get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


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


def _eval_condition(cond: Any, features: Dict[str, Any]) -> bool:
    if cond is None:
        return False
    if isinstance(cond, dict):
        # logical ops first
        if 'all' in cond:
            return all(_eval_condition(c, features) for c in cond['all'] or [])
        if 'any' in cond:
            return any(_eval_condition(c, features) for c in cond['any'] or [])
        if 'not' in cond:
            return not _eval_condition(cond['not'], features)
        # field tests
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
            field_val = _get(features, field)
            if not _cmp(field_val, op, expected):
                return False
        return True
    if isinstance(cond, list):
        return all(_eval_condition(c, features) for c in cond)
    # unexpected literal -> truthy/falsey
    return bool(cond)


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
    for fp in sorted(glob.glob(os.path.join(dir_path, '*.yaml'))):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or []
                if isinstance(data, list):
                    rules.extend(data)
        except Exception:
            continue

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
                    'evidence': {},
                }
                for path in rule.get('evidence') or []:
                    finding['evidence'][path] = _get(features, path)
                findings.append(finding)
        except Exception:
            continue
    # sort by weight desc
    findings.sort(key=lambda x: x.get('weight', 0), reverse=True)
    return findings
