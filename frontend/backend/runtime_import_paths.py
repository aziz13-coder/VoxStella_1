from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_backend_import_roots() -> list[Path]:
    roots: list[Path] = []

    env_backend_dir = str(os.environ.get("HORARY_BACKEND_DIR") or "").strip()
    if env_backend_dir:
        backend_root = Path(env_backend_dir).resolve()
        roots.append(backend_root)
        roots.append(backend_root / "backend")

    here = Path(__file__).resolve().parent
    roots.append(here)
    roots.append(here.parent)
    roots.append(here.parent / "backend")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_root = Path(meipass).resolve()
        roots.append(meipass_root)
        roots.append(meipass_root / "backend")

    cwd = str(os.getcwd() or "").strip()
    if cwd:
        cwd_root = Path(cwd).resolve()
        roots.append(cwd_root)
        roots.append(cwd_root / "backend")

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        normalized = str(root)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(root)
    return deduped


def extend_backend_runtime_import_paths() -> list[str]:
    inserted: list[str] = []
    existing = {Path(item).resolve() for item in sys.path if item}

    for root in _candidate_backend_import_roots():
        if not root.exists() or not root.is_dir():
            continue
        resolved = root.resolve()
        if resolved in existing:
            continue
        sys.path.insert(0, str(resolved))
        existing.add(resolved)
        inserted.append(str(resolved))

    return inserted
