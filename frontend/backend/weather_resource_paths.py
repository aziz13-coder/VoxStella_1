from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_backend_roots() -> list[Path]:
    roots: list[Path] = []

    env_backend_dir = str(os.environ.get("HORARY_BACKEND_DIR") or "").strip()
    if env_backend_dir:
        roots.append(Path(env_backend_dir).resolve())

    here = Path(__file__).resolve().parent
    roots.append(here)
    roots.append(here.parent)
    roots.append(here.parent / "backend")
    roots.append(here.parent / "frontend" / "backend")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_root = Path(meipass).resolve()
        roots.append(meipass_root)
        roots.append(meipass_root / "backend")
        roots.append(meipass_root / "frontend" / "backend")

    cwd = str(os.getcwd() or "").strip()
    if cwd:
        cwd_root = Path(cwd).resolve()
        roots.append(cwd_root)
        roots.append(cwd_root / "backend")
        roots.append(cwd_root / "frontend" / "backend")

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        normalized = str(root)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(root)
    return deduped


def resolve_weather_resource_path(filename: str) -> Path:
    normalized_name = str(filename or "").strip()
    if not normalized_name:
        raise ValueError("Weather resource filename is required")

    candidates: list[Path] = []
    for root in _candidate_backend_roots():
        candidates.append(root / "knowledge" / "weather" / normalized_name)
        candidates.append(root / "backend" / "knowledge" / "weather" / normalized_name)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]
