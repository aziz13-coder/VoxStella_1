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

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass).resolve())

    cwd = str(os.getcwd() or "").strip()
    if cwd:
        roots.append(Path(cwd).resolve())

    return roots


def resolve_astrocartography_resource_path(filename: str) -> Path:
    normalized_name = str(filename or "").strip()
    if not normalized_name:
        raise ValueError("Astrocartography resource filename is required")

    candidates: list[Path] = []
    for root in _candidate_backend_roots():
        candidates.append(root / "knowledge" / "astrocartography" / normalized_name)
        candidates.append(root / "backend" / "knowledge" / "astrocartography" / normalized_name)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]
