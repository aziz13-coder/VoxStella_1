from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

METADATA_FILENAME = "build_metadata.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def detect_backend_root(explicit_root: Optional[Path | str] = None) -> Path:
    if explicit_root:
        return Path(explicit_root).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def metadata_path(root: Optional[Path | str] = None) -> Path:
    return detect_backend_root(root) / METADATA_FILENAME


def metadata_candidates(root: Optional[Path | str] = None) -> list[Path]:
    backend_root = detect_backend_root(root)
    candidates = [backend_root / METADATA_FILENAME]
    internal_candidate = backend_root / "_internal" / METADATA_FILENAME
    if internal_candidate not in candidates:
        candidates.append(internal_candidate)
    return candidates


def _run_git(args: list[str], *, cwd: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except Exception:
        return None
    output = (result.stdout or "").strip()
    return output or None


def detect_git_metadata(repo_root: Optional[Path | str] = None) -> Dict[str, Any]:
    cwd = Path(repo_root).resolve() if repo_root else _repo_root()
    commit = _run_git(["rev-parse", "HEAD"], cwd=cwd)
    short_commit = _run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    status = _run_git(["status", "--short"], cwd=cwd)
    payload: Dict[str, Any] = {
        "available": bool(commit or short_commit or branch),
    }
    if commit:
        payload["commit"] = commit
    if short_commit:
        payload["short_commit"] = short_commit
    if branch:
        payload["branch"] = branch
    if status is not None:
        payload["dirty"] = bool(status.strip())
    return payload


def build_metadata_payload(*, runtime_kind: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "metadata_version": 1,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_kind": runtime_kind,
        "builder_python": sys.version.split()[0],
        "builder_platform": platform.platform(),
        "git": detect_git_metadata(),
    }
    if extra:
        payload.update(extra)
    return payload


def write_build_metadata(root: Optional[Path | str] = None, *, extra: Optional[Dict[str, Any]] = None) -> Path:
    target = metadata_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_metadata_payload(runtime_kind="pyinstaller_bundle", extra=extra)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_build_metadata(root: Optional[Path | str] = None) -> Dict[str, Any]:
    for target in metadata_candidates(root):
        if not target.exists():
            continue
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {
                    **payload,
                    "metadata_source": "file",
                }
        except Exception as exc:
            return {
                "metadata_source": "unreadable",
                "metadata_error": str(exc),
                "runtime_kind": "pyinstaller_bundle" if getattr(sys, "frozen", False) else "source_runtime",
            }
    if getattr(sys, "frozen", False):
        return {
            "metadata_source": "unavailable",
            "runtime_kind": "pyinstaller_bundle",
            "git": {"available": False},
        }
    payload = build_metadata_payload(runtime_kind="source_runtime")
    payload["metadata_source"] = "runtime_probe"
    return payload
