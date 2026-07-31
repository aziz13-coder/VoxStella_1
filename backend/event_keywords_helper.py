# -*- coding: utf-8 -*-
"""
Event-keyword catalog helper

Reads the bundled event-keyword catalog and augments existing tokens with
known related terms. When canonical promotion is enabled, it may also classify
an unambiguous direct term as one canonical event.

Canonical promotion is conservative: only an unambiguous, directly supplied
catalog term may promote a canonical event. Expanded terms do not cascade.

Safe behavior: if the file is missing or parsing fails, the input is returned
unchanged.
"""

from __future__ import annotations

from typing import Dict, Set, List, Optional
import os
import re
import sys

_CACHE: Optional[Dict[str, Set[str]]] = None


def _dict_path() -> Optional[str]:
    # Prefer local bundled/runtime catalog files; fall back to repo-root variants.
    #
    # In PyInstaller onefile runs, __file__ points inside the extraction dir and
    # adjacent resource files may instead live next to the executable. Check both
    # locations so packaged and source runtimes resolve the same catalog.
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.path.join(here, os.pardir))
    exec_dir = os.path.dirname(getattr(sys, "executable", "") or "")
    meipass_dir = getattr(sys, "_MEIPASS", None)
    cands = [
        os.path.join(here, "event_keywords_catalog.md"),
        os.path.join(here, "event_keywords_dictionary.md"),
        os.path.join(here, "event_keywords_dictionary(1).md"),
        os.path.join(exec_dir, "event_keywords_catalog.md"),
        os.path.join(exec_dir, "event_keywords_dictionary.md"),
        os.path.join(exec_dir, "event_keywords_dictionary(1).md"),
        os.path.join(root, "event_keywords_dictionary(1).md"),
        os.path.join(root, "event_keywords_dictionary.md"),
        os.path.join(root, "event_keywords_catalog.md"),
        os.path.join(os.getcwd(), "event_keywords_dictionary(1).md"),
        os.path.join(os.getcwd(), "event_keywords_dictionary.md"),
        os.path.join(os.getcwd(), "event_keywords_catalog.md"),
    ]
    if meipass_dir:
        cands = [
            os.path.join(meipass_dir, "event_keywords_catalog.md"),
            os.path.join(meipass_dir, "event_keywords_dictionary.md"),
            os.path.join(meipass_dir, "event_keywords_dictionary(1).md"),
            *cands,
        ]
    for p in cands:
        if os.path.isfile(p):
            return p
    return None


def _parse_yaml_blocks(lines: List[str]) -> Dict[str, Set[str]]:
    evmap: Dict[str, Set[str]] = {}
    in_yaml = False
    buf: List[str] = []
    for line in lines:
        if line.strip().startswith('```yaml'):
            in_yaml = True
            buf = []
            continue
        if in_yaml and line.strip().startswith('```'):
            # parse buf
            _merge_map(evmap, _parse_block(buf))
            in_yaml = False
            buf = []
            continue
        if in_yaml:
            buf.append(line)
    return evmap


def _merge_map(base: Dict[str, Set[str]], add: Dict[str, Set[str]]) -> None:
    for k, vals in add.items():
        base.setdefault(k, set()).update(vals)


def _parse_block(block: List[str]) -> Dict[str, Set[str]]:
    result: Dict[str, Set[str]] = {}
    current: Optional[str] = None
    kw_indent: Optional[int] = None
    in_keywords = False
    # regex
    top_key = re.compile(r'^(\w[\w\d_]*):\s*$')  # e.g., promotion:
    def _capture_list(line: str) -> List[str]:
        try:
            lb = line.find('['); rb = line.rfind(']')
            if lb == -1 or rb == -1 or rb <= lb:
                return []
            inner = line[lb+1:rb]
            parts = [p.strip().strip('"\'') for p in inner.split(',') if p.strip()]
            # Keep underscores; normalize to lowercase
            return [p.lower() for p in parts if p]
        except Exception:
            return []
    list_keys = ("primary:", "secondary:", "context:", "types:", "symptoms:")
    for raw in block:
        s = raw.rstrip('\n')
        # new top-level event name
        m = top_key.match(s.strip())
        if m and not s.startswith(' '):
            current = m.group(1).lower()
            result.setdefault(current, set())
            in_keywords = False
            kw_indent = None
            continue
        if current is None:
            continue
        # keywords: start
        if s.strip().startswith('keywords:'):
            in_keywords = True
            kw_indent = len(s) - len(s.lstrip(' '))
            continue
        if in_keywords:
            # end section if indentation decreases to kw_indent or less and line has content
            if s.strip() and (len(s) - len(s.lstrip(' '))) <= (kw_indent or 0) and not s.strip().startswith('-'):
                in_keywords = False
            for key in list_keys:
                if key in s:
                    for tok in _capture_list(s):
                        result[current].add(tok)
        # synonyms:
        if 'synonyms:' in s:
            for tok in _capture_list(s):
                result[current].add(tok)
    return result


def _load_map() -> Dict[str, Set[str]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = _dict_path()
    if not path:
        _CACHE = {}
        return _CACHE
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        evmap = _parse_yaml_blocks(lines)
    except Exception:
        evmap = {}
    _CACHE = evmap
    return evmap


def merge_event_synonyms(tokens: List[str], *, promote_canonical: Optional[bool] = None) -> List[str]:
    """Return tokens plus catalog terms for recognized events.

    - Input tokens are preserved as-is, order maintained.
    - Added terms are appended in deterministic order and deduplicated
      case-insensitively.
    - Only canonical event tokens expand into their catalog terms.
    - If canonical promotion is enabled, an original non-canonical token
      promotes an event only when it belongs to exactly one catalog entry.
      Generated terms never cascade into additional events.
    """
    evmap = _load_map()
    if not evmap or not tokens:
        return tokens
    # Opt-in canonical promotion via param or env
    if promote_canonical is None:
        try:
            promote_canonical = str(os.environ.get('EVENT_KEYWORDS_PROMOTE', '0')).lower() in {'1','true','yes','on'}
        except Exception:
            promote_canonical = False
    out: List[str] = []
    seen: Set[str] = set()
    original_keys: List[str] = []
    # preserve originals
    for t in tokens:
        if not isinstance(t, str) or not t:
            continue
        key = t.lower()
        original_keys.append(key)
        if key not in seen:
            out.append(t)
            seen.add(key)
    # expand for known events
    for key in original_keys:
        if key in evmap:
            for syn in sorted(evmap.get(key, set())):
                if syn and syn not in seen:
                    out.append(syn)
                    seen.add(syn)
    # A generic term such as "fight", "loss", or "fall" may occur under
    # several events. Choosing one here would manufacture specificity that the
    # input did not contain, so only unique direct matches can be promoted.
    if promote_canonical:
        token_events: Dict[str, Set[str]] = {}
        for event, event_tokens in evmap.items():
            for token in event_tokens:
                token_events.setdefault(token.lower(), set()).add(event.lower())
        for key in original_keys:
            # A canonical input already identifies its event. Do not reinterpret
            # it through a different event's related terms.
            if key in evmap:
                continue
            matching_events = token_events.get(key, set())
            if len(matching_events) != 1:
                continue
            event = next(iter(matching_events))
            if event not in seen:
                out.append(event)
                seen.add(event)
    return out


__all__ = ['merge_event_synonyms']
