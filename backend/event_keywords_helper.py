# -*- coding: utf-8 -*-
"""
Event Keywords Helper (non-intrusive)

Reads event keywords from 'event_keywords_dictionary(1).md' and exposes a
single function to augment an existing list of event tokens with known
synonyms/related keywords. This does NOT change event detection logic — it
only adds extra tokens to lists you already build.

Safe behavior: if the file is missing or parsing fails, it returns the input
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
    """Return tokens + synonyms for any recognized event tokens.

    - Input tokens are preserved as-is, order maintained.
    - Added synonyms are appended, deduplicated (case-insensitive).
    - Only expands tokens that match event keys in the dictionary.
    - If promote_canonical is True (or ENV EVENT_KEYWORDS_PROMOTE on),
      then if any token matches a synonym or keyword list for an event,
      the canonical event token is appended as well.
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
    # preserve originals
    for t in tokens:
        if t and t.lower() not in seen:
            out.append(t)
            seen.add(t.lower())
    # expand for known events
    for t in tokens:
        key = t.lower()
        if key in evmap:
            for syn in evmap.get(key, set()):
                if syn and syn not in seen:
                    out.append(syn)
                    seen.add(syn)
    # optional canonical promotion: if any token matches a synonym set, add the canonical event token
    if promote_canonical:
        for ev, toks in evmap.items():
            try:
                # if any token already present (original or synonym) appears in this event's token set
                if any(tok in seen for tok in (tok.lower() for tok in toks)):
                    if ev.lower() not in seen:
                        out.append(ev)
                        seen.add(ev.lower())
            except Exception:
                continue
    return out


__all__ = ['merge_event_synonyms']
