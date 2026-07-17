#!/usr/bin/env python3
"""
Build script to create a standalone backend runtime using PyInstaller.

The Electron app ships the backend inside the packaged resources folder, so
startup behavior matters more than having a single-file artifact. Use an
onedir bundle to avoid PyInstaller onefile extraction latency during packaged
launches.
"""

import importlib.metadata
import os
import sys
import subprocess
import shutil
from pathlib import Path

from build_metadata import write_build_metadata

CRITICAL_MODULES = (
    "flask",
    "flask_cors",
    "swisseph",
    "timezonefinder",
    "pytz",
    "nacl",
    "nacl.signing",
)

REQUIRED_PYTHON = (3, 12)
REQUIRED_PYINSTALLER = "6.21.0"

RUNTIME_HIDDEN_IMPORTS = (
    "astro_clock_api",
    "birth_certification",
    "runtime_import_paths",
    "licensing",
    "mundane_assets",
    "mundane_benchmark_profiles",
    "mundane_chart_rules",
    "mundane_domain_rules",
    "mundane_models",
    "mundane_resource_paths",
    "mundane_scan_grid",
    "mundane_scan_models",
    "mundane_scan_service",
    "mundane_service",
    "mundane_trigger_rules",
    "weather_assets",
    "weather_benchmark_profiles",
    "weather_chart_rules",
    "weather_domain_rules",
    "weather_models",
    "weather_resource_paths",
    "weather_scan_models",
    "weather_scan_service",
    "weather_service",
)

RUNTIME_DATA_ENTRIES = (
    ("horary_constants.yaml", "."),
    ("event_keywords_catalog.md", "."),
    ("synastry_rule_catalog.json", "."),
    ("horary_config.py", "."),
    ("production_server.py", "."),
    ("knowledge/astrocartography", "knowledge/astrocartography"),
    ("knowledge/mundane", "knowledge/mundane"),
    ("knowledge/weather", "knowledge/weather"),
    ("benchmarks", "benchmarks"),
    ("rules_lilly_general_v1.yaml", "."),
    ("forensic/knowledge", "forensic/knowledge"),
    ("traits/catalog", "traits/catalog"),
    ("traits/traits.json", "traits"),
    ("traits/knowledge", "traits/knowledge"),
    ("Phsychology traits", "Phsychology traits"),
    ("ephemeris/sweph", "ephemeris/sweph"),
)

OPTIONAL_RUNTIME_DATA_ENTRIES = (
    ("../extracted_text_docs/new_sources_inspection", "traits/corpus/new_sources_inspection"),
)


def _log_ok(message: str) -> None:
    print(f"[OK] {message}")


def _log_error(message: str) -> None:
    print(f"[ERROR] {message}")


def build_runtime_data_args(backend_dir: Path, build_metadata_path: Path) -> list[str]:
    """Return the PyInstaller --add-data arguments required by the runtime bundle."""
    data_args: list[str] = []
    for relative_source, destination in RUNTIME_DATA_ENTRIES:
        source = (backend_dir / relative_source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Required runtime data is missing: {source}")
        data_args.extend(["--add-data", f"{source};{destination}"])
    for relative_source, destination in OPTIONAL_RUNTIME_DATA_ENTRIES:
        source = (backend_dir / relative_source).resolve()
        if source.exists():
            data_args.extend(["--add-data", f"{source};{destination}"])
        else:
            print(f"[WARN] Optional runtime data is unavailable: {source}")
    data_args.extend(["--add-data", f"{build_metadata_path};."])
    return data_args


def check_build_dependencies() -> bool:
    """Fail fast if required runtime modules are not available."""
    if sys.version_info[:2] != REQUIRED_PYTHON:
        _log_error(
            "Release backend builds require Python "
            f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}; found "
            f"{sys.version_info.major}.{sys.version_info.minor}."
        )
        return False

    try:
        pyinstaller_version = importlib.metadata.version("pyinstaller")
    except importlib.metadata.PackageNotFoundError:
        pyinstaller_version = None
    if pyinstaller_version != REQUIRED_PYINSTALLER:
        _log_error(
            f"PyInstaller {REQUIRED_PYINSTALLER} is required; "
            f"found {pyinstaller_version or 'not installed'}."
        )
        return False

    missing = []
    for mod in CRITICAL_MODULES:
        try:
            __import__(mod)
        except Exception as exc:
            missing.append((mod, str(exc)))
    if not missing:
        return True

    _log_error("Missing required Python modules for backend build:")
    for mod, err in missing:
        print(f"  - {mod}: {err}")
    print("Install backend dependencies first, then rebuild.")
    print("Suggested command: python -m pip install -r backend/requirements.txt")
    return False


def build_backend():
    """Build the backend into a standalone runtime bundle."""
    if not check_build_dependencies():
        return None

    backend_dir = Path(__file__).parent

    app_py = backend_dir / "app.py"
    dist_dir = backend_dir / "dist"
    build_dir = backend_dir / "build"
    executable_name = "horary_backend.exe" if sys.platform == "win32" else "horary_backend"
    bundle_dir = dist_dir / "horary_backend"
    executable_path = bundle_dir / executable_name

    try:
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)
        build_metadata_path = write_build_metadata(
            build_dir,
            extra={
                "build_target": "pyinstaller_onedir",
                "bundle_name": "horary_backend",
                "app_version": os.environ.get("VOX_STELLA_BUILD_VERSION", "").strip() or None,
            },
        )
        spec_dir = build_dir / "spec"
        spec_dir.mkdir(parents=True, exist_ok=True)

        pyinstaller_cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onedir",
            "--name",
            "horary_backend",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(build_dir),
            "--specpath",
            str(spec_dir),
            "--console",
            "--clean",
            str(app_py),
        ]
        pyinstaller_cmd[12:12] = build_runtime_data_args(backend_dir, build_metadata_path)

        hidden_imports = [
            "swisseph",
            "timezonefinder",
            "pytz",
            "flask",
            "flask_cors",
            "nacl",
            "nacl.bindings",
            "nacl.signing",
            "nacl.exceptions",
            *RUNTIME_HIDDEN_IMPORTS,
        ]
        for module_name in hidden_imports:
            pyinstaller_cmd.extend(["--hidden-import", module_name])

        print("Building backend executable...")
        print(f"Command: {' '.join(pyinstaller_cmd)}")

        result = subprocess.run(pyinstaller_cmd, check=True, cwd=backend_dir)

        if result.returncode == 0:
            if executable_path.exists():
                bundle_size_mb = sum(
                    item.stat().st_size for item in bundle_dir.rglob("*") if item.is_file()
                ) / (1024 * 1024)
                _log_ok(f"Backend runtime created: {executable_path}")
                _log_ok(f"Bundle directory: {bundle_dir}")
                _log_ok(f"Bundle size: {bundle_size_mb:.1f} MB")
                return str(executable_path)

            _log_error("Backend runtime executable not found after build")
            return None

        _log_error("PyInstaller failed")
        return None
    except subprocess.CalledProcessError as exc:
        _log_error(f"Build failed: {exc}")
        return None
    except Exception as exc:
        _log_error(f"Unexpected error: {exc}")
        return None


if __name__ == "__main__":
    runtime_path = build_backend()
    if runtime_path:
        print("\nTo test the executable:")
        print(f"  {runtime_path}")
        print("\nThe runtime bundle should be copied to the Electron app's resources folder.")
    else:
        sys.exit(1)
