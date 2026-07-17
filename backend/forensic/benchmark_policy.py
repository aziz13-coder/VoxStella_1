from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional


NINE_ELEVEN_EXCLUSION_REASON = "9/11 is excluded from forensic benchmarks by benchmark policy."

_NINE_ELEVEN_EVENT_PATTERNS = (
    "9/11/2001",
    "9-11-2001",
    "09/11/2001",
    "09-11-2001",
    "september 11 attacks",
    "september 11, 2001",
    "september 11 2001",
    "world trade center",
    "twin towers",
)

_NINE_ELEVEN_DATE_FIELDS = (
    "date",
    "date_local",
    "event_date",
    "incident_date",
    "datetime",
    "datetime_local",
)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _iter_text_values(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        text = _normalize_text(value)
        if text:
            yield text
        return
    if isinstance(value, Path):
        text = _normalize_text(value.name)
        if text:
            yield text
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_text_values(item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_text_values(item)
        return
    text = _normalize_text(value)
    if text:
        yield text


def _event_text_blob(case: Dict[str, Any]) -> str:
    values = []
    for key in (
        "id",
        "case_id",
        "title",
        "case_title",
        "event",
        "episode",
        "summary",
        "notes",
        "benchmark",
        "query",
    ):
        values.extend(_iter_text_values(case.get(key)))
    return " ".join(values)


def _has_september_11_date(case: Dict[str, Any]) -> bool:
    benchmark = case.get("benchmark") if isinstance(case.get("benchmark"), dict) else {}
    query = case.get("query") if isinstance(case.get("query"), dict) else {}
    tested_anchors = case.get("tested_anchors") if isinstance(case.get("tested_anchors"), list) else []
    sources = [case, benchmark, query]
    for anchor in tested_anchors:
        if isinstance(anchor, dict):
            sources.append(anchor)
            if isinstance(anchor.get("query"), dict):
                sources.append(anchor.get("query") or {})
    for source in sources:
        for key in _NINE_ELEVEN_DATE_FIELDS:
            text = _normalize_text(source.get(key) if isinstance(source, dict) else None)
            if text.startswith("2001-09-11") or text.startswith("9/11/2001") or text.startswith("09/11/2001"):
                return True
    return False


def benchmark_exclusion_reason(case: Dict[str, Any]) -> Optional[str]:
    """Return an explicit benchmark exclusion reason, if this case is barred.

    This intentionally targets the September 11 event, not generic emergency
    "911 call" wording that appears in ordinary case narratives.
    """

    if not isinstance(case, dict):
        return None
    blob = _event_text_blob(case)
    if any(pattern in blob for pattern in _NINE_ELEVEN_EVENT_PATTERNS):
        return NINE_ELEVEN_EXCLUSION_REASON
    if _has_september_11_date(case) and any(
        marker in blob
        for marker in (
            "terror",
            "attack",
            "pentagon",
            "world trade",
            "twin towers",
            "flight 11",
            "flight 175",
            "flight 77",
            "flight 93",
        )
    ):
        return NINE_ELEVEN_EXCLUSION_REASON
    return None


def is_excluded_benchmark_case(case: Dict[str, Any]) -> bool:
    return benchmark_exclusion_reason(case) is not None
