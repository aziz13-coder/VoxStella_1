#!/usr/bin/env python3
"""Prove which backend tree is used by development and release workflows.

``backend/**`` is the only authoritative Python source tree.  The historical
``frontend/backend/**`` tree is retained temporarily for reference and legacy
tests, but Electron packaging may consume only its generated ``runtime/**``
staging directory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List


CANONICAL_BACKEND = Path("backend")
LEGACY_BACKEND_MIRROR = Path("frontend") / "backend"
GENERATED_RUNTIME_STAGE = LEGACY_BACKEND_MIRROR / "runtime" / "horary_backend"
PACKAGED_RUNTIME = Path("resources") / "backend" / "runtime" / "horary_backend"
OWNERSHIP_MARKER = LEGACY_BACKEND_MIRROR / "README.md"

_MIRROR_SKIP_DIRS = {
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "runtime",
    "venv",
    ".venv",
}
_MIRROR_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".py", ".yaml", ".yml"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_astrocartography_mirror(relative_path: Path) -> bool:
    normalized = relative_path.as_posix().lower()
    return (
        "astrocartography" in normalized
        or normalized in {"astro_clock_api.py", "test_astro_clock_api_astrocartography.py"}
    )


def compare_legacy_astrocartography_mirrors(repo_root: Path) -> List[Dict[str, Any]]:
    """Describe mirror drift without treating the legacy copy as a release input."""

    root = Path(repo_root).resolve()
    canonical_root = root / CANONICAL_BACKEND
    legacy_root = root / LEGACY_BACKEND_MIRROR
    if not legacy_root.is_dir():
        return []

    rows: List[Dict[str, Any]] = []
    for legacy_path in sorted(path for path in legacy_root.rglob("*") if path.is_file()):
        relative_path = legacy_path.relative_to(legacy_root)
        if any(part in _MIRROR_SKIP_DIRS for part in relative_path.parts):
            continue
        if legacy_path.suffix.lower() not in _MIRROR_SUFFIXES:
            continue
        if not _is_astrocartography_mirror(relative_path):
            continue

        canonical_path = canonical_root / relative_path
        legacy_hash = _sha256(legacy_path)
        if not canonical_path.is_file():
            rows.append(
                {
                    "path": relative_path.as_posix(),
                    "status": "legacy_only",
                    "canonical_sha256": None,
                    "legacy_sha256": legacy_hash,
                }
            )
            continue

        canonical_hash = _sha256(canonical_path)
        rows.append(
            {
                "path": relative_path.as_posix(),
                "status": "synchronized" if canonical_hash == legacy_hash else "diverged",
                "canonical_sha256": canonical_hash,
                "legacy_sha256": legacy_hash,
            }
        )
    return rows


def validate_frontend_package_config(package_payload: Dict[str, Any]) -> List[str]:
    """Reject any Electron configuration that packages the legacy source tree."""

    errors: List[str] = []
    scripts = package_payload.get("scripts") or {}
    normalized_build_command = " ".join(
        str(scripts.get("build-backend-exe") or "").replace("\\", "/").lower().split()
    )
    if "cd ../backend" not in normalized_build_command or "python build_backend.py" not in normalized_build_command:
        errors.append(
            "frontend/package.json must build the backend from ../backend/build_backend.py."
        )

    build_config = package_payload.get("build") or {}
    extra_resources = build_config.get("extraResources") or []
    resource_sources = [
        str(entry.get("from") or "").replace("\\", "/").rstrip("/")
        for entry in extra_resources
        if isinstance(entry, dict)
    ]
    expected_source = "backend/runtime/horary_backend"
    if resource_sources != [expected_source]:
        errors.append(
            "Electron extraResources must contain only the generated compiled runtime "
            f"{expected_source!r}; found {resource_sources!r}."
        )

    packaged_files = [
        str(item).replace("\\", "/").lstrip("./")
        for item in (build_config.get("files") or [])
    ]
    source_entries = [
        item
        for item in packaged_files
        if item == "backend" or item.startswith("backend/")
    ]
    if source_entries:
        errors.append(
            "Electron build.files must not include frontend/backend Python sources: "
            + ", ".join(source_entries)
        )
    return errors


def _require_pattern(
    errors: List[str],
    text: str,
    pattern: str,
    message: str,
) -> None:
    if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) is None:
        errors.append(message)


def probe_canonical_import_origins(
    repo_root: Path,
    modules: Iterable[str] = ("app", "astrocartography_service"),
) -> Dict[str, str]:
    """Resolve module origins from the canonical backend working directory.

    ``find_spec`` avoids importing the Flask application while still exercising
    the same top-level module lookup used by PyInstaller from ``backend/**``.
    """

    root = Path(repo_root).resolve()
    canonical_root = (root / CANONICAL_BACKEND).resolve()
    module_names = tuple(str(module) for module in modules)
    probe = (
        "import importlib.util, json\n"
        f"names = {module_names!r}\n"
        "out = {}\n"
        "for name in names:\n"
        "    spec = importlib.util.find_spec(name)\n"
        "    out[name] = None if spec is None else spec.origin\n"
        "print(json.dumps(out, sort_keys=True))\n"
    )
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env["PYTHONPATH"] = ""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=canonical_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    origins = json.loads(completed.stdout.strip())
    resolved: Dict[str, str] = {}
    for module_name in module_names:
        raw_origin = origins.get(module_name)
        if not raw_origin:
            raise RuntimeError(f"Could not resolve canonical backend module {module_name!r}.")
        origin = Path(raw_origin).resolve()
        try:
            origin.relative_to(canonical_root)
        except ValueError as exc:
            raise RuntimeError(
                f"Module {module_name!r} resolved outside canonical backend: {origin}"
            ) from exc
        resolved[module_name] = origin.relative_to(root).as_posix()
    return resolved


def audit_repository(repo_root: Path, *, run_import_probe: bool = True) -> Dict[str, Any]:
    root = Path(repo_root).resolve()
    errors: List[str] = []

    package_path = root / "frontend" / "package.json"
    if package_path.is_file():
        package_payload = json.loads(package_path.read_text(encoding="utf-8"))
        errors.extend(validate_frontend_package_config(package_payload))
    else:
        errors.append("Missing frontend/package.json.")

    prepare_path = root / "frontend" / "scripts" / "prepare-backend.js"
    prepare_text = prepare_path.read_text(encoding="utf-8") if prepare_path.is_file() else ""
    if not prepare_text:
        errors.append("Missing frontend/scripts/prepare-backend.js.")
    else:
        _require_pattern(
            errors,
            prepare_text,
            r"backendSrc\s*=\s*path\.join\(\s*__dirname\s*,\s*['\"]\.\.['\"]\s*,"
            r"\s*['\"]\.\.['\"]\s*,\s*['\"]backend['\"]\s*\)",
            "prepare-backend.js must source the compiled runtime from repository backend/**.",
        )
        _require_pattern(
            errors,
            prepare_text,
            r"runtimeBundleSrc\s*=\s*path\.join\(\s*backendSrc\s*,\s*['\"]dist['\"]\s*,"
            r"\s*['\"]horary_backend['\"]\s*\)",
            "prepare-backend.js must copy backend/dist/horary_backend.",
        )
        _require_pattern(
            errors,
            prepare_text,
            r"backendRuntimeRoot\s*=\s*path\.join\(\s*__dirname\s*,\s*['\"]\.\.['\"]\s*,"
            r"\s*['\"]backend['\"]\s*,\s*['\"]runtime['\"]\s*\)",
            "prepare-backend.js must stage only frontend/backend/runtime/**.",
        )
        if re.search(r"copyDirectory\s*\(\s*backendSrc\b", prepare_text):
            errors.append(
                "prepare-backend.js must not copy canonical Python sources into frontend/backend."
            )

    build_path = root / CANONICAL_BACKEND / "build_backend.py"
    build_text = build_path.read_text(encoding="utf-8") if build_path.is_file() else ""
    compact_build = re.sub(r"\s+", "", build_text)
    if "backend_dir=Path(__file__).parent" not in compact_build:
        errors.append("backend/build_backend.py must anchor its build root to its own directory.")
    if 'app_py=backend_dir/"app.py"' not in compact_build:
        errors.append("backend/build_backend.py must use backend/app.py as the PyInstaller entrypoint.")
    if "cwd=backend_dir" not in compact_build:
        errors.append("backend/build_backend.py must run PyInstaller with backend/** as cwd.")

    batch_path = root / "package-app-new.bat"
    batch_text = batch_path.read_text(encoding="utf-8") if batch_path.is_file() else ""
    normalized_batch = batch_text.replace("\\", "/").lower()
    _require_pattern(
        errors,
        normalized_batch,
        r"pushd\s+backend\b.*?build_backend\.py",
        "package-app-new.bat must enter backend/** before invoking build_backend.py.",
    )
    if re.search(r"(?:pushd|cd)\s+frontend/backend\b", normalized_batch):
        errors.append("package-app-new.bat must never build from frontend/backend.")

    main_path = root / "frontend" / "main.js"
    main_text = main_path.read_text(encoding="utf-8") if main_path.is_file() else ""
    _require_pattern(
        errors,
        main_text,
        r"resources\s*,\s*['\"]backend['\"]\s*,\s*['\"]runtime['\"]\s*,"
        r"\s*['\"]horary_backend['\"]",
        "Electron must launch resources/backend/runtime/horary_backend.",
    )
    _require_pattern(
        errors,
        main_text,
        r"__dirname\s*,\s*['\"]\.\.['\"]\s*,\s*['\"]backend['\"]\s*,\s*['\"]app\.py['\"]",
        "Electron development fallback must resolve repository backend/app.py.",
    )

    for relative_helper in (
        Path("frontend/scripts/package-working-exe.js"),
        Path("frontend/scripts/fix-and-package.js"),
    ):
        helper_path = root / relative_helper
        helper_text = helper_path.read_text(encoding="utf-8") if helper_path.is_file() else ""
        _require_pattern(
            errors,
            helper_text,
            r"backendRuntimeSrc\s*=\s*path\.join\(\s*__dirname\s*,\s*['\"]\.\.['\"]\s*,"
            r"\s*['\"]\.\.['\"]\s*,\s*['\"]backend['\"]\s*,\s*['\"]dist['\"]\s*,"
            r"\s*['\"]horary_backend['\"]\s*\)",
            f"{relative_helper.as_posix()} must source repository backend/dist/horary_backend.",
        )

    marker_path = root / OWNERSHIP_MARKER
    marker_text = marker_path.read_text(encoding="utf-8") if marker_path.is_file() else ""
    marker_lower = marker_text.lower()
    if "non-authoritative" not in marker_lower or "backend/**" not in marker_text:
        errors.append(
            "frontend/backend/README.md must mark the tree non-authoritative and name backend/** "
            "as the canonical source."
        )

    import_origins: Dict[str, str] = {}
    if run_import_probe:
        try:
            import_origins = probe_canonical_import_origins(root)
        except Exception as exc:
            errors.append(f"Canonical import-origin probe failed: {exc}")

    mirror_rows = compare_legacy_astrocartography_mirrors(root)
    status_counts: Dict[str, int] = {}
    for row in mirror_rows:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "ok": not errors,
        "errors": errors,
        "ownership": {
            "canonical_source": CANONICAL_BACKEND.as_posix(),
            "pyinstaller_entrypoint": (CANONICAL_BACKEND / "app.py").as_posix(),
            "compiled_runtime_source": (
                CANONICAL_BACKEND / "dist" / "horary_backend"
            ).as_posix(),
            "generated_runtime_stage": GENERATED_RUNTIME_STAGE.as_posix(),
            "packaged_runtime": PACKAGED_RUNTIME.as_posix(),
            "legacy_mirror": LEGACY_BACKEND_MIRROR.as_posix(),
        },
        "import_origins": import_origins,
        "mirror_summary": {
            "pair_count": len(mirror_rows),
            "status_counts": status_counts,
            "rows": mirror_rows,
        },
    }


def _print_human_report(report: Dict[str, Any]) -> None:
    ownership = report["ownership"]
    print(f"canonical source: {ownership['canonical_source']}")
    print(f"PyInstaller entrypoint: {ownership['pyinstaller_entrypoint']}")
    print(f"compiled runtime source: {ownership['compiled_runtime_source']}")
    print(f"generated staging path: {ownership['generated_runtime_stage']}")
    print(f"packaged runtime path: {ownership['packaged_runtime']}")
    print(f"legacy mirror: {ownership['legacy_mirror']} (non-authoritative)")
    for module_name, origin in sorted((report.get("import_origins") or {}).items()):
        print(f"import {module_name}: {origin}")
    summary = report["mirror_summary"]
    print(
        "astrocartography mirror status: "
        f"{summary['pair_count']} inspected; {summary['status_counts']}"
    )
    if report["ok"]:
        print("[OK] Backend source ownership is unambiguous.")
        return
    for error in report["errors"]:
        print(f"[ERROR] {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to this script's parent repository).",
    )
    parser.add_argument("--json", action="store_true", help="Emit the complete audit as JSON.")
    parser.add_argument(
        "--skip-import-probe",
        action="store_true",
        help="Skip the isolated Python module-origin probe.",
    )
    args = parser.parse_args()

    report = audit_repository(args.repo_root, run_import_probe=not args.skip_import_probe)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
