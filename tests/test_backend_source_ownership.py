from __future__ import annotations

import json
from pathlib import Path

from scripts.check_backend_source_ownership import (
    audit_repository,
    compare_legacy_astrocartography_mirrors,
    probe_canonical_import_origins,
    validate_frontend_package_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflows_use_only_canonical_backend_source():
    report = audit_repository(REPO_ROOT, run_import_probe=False)

    assert report["errors"] == []
    assert report["ok"] is True
    assert report["ownership"] == {
        "canonical_source": "backend",
        "pyinstaller_entrypoint": "backend/app.py",
        "compiled_runtime_source": "backend/dist/horary_backend",
        "generated_runtime_stage": "frontend/backend/runtime/horary_backend",
        "packaged_runtime": "resources/backend/runtime/horary_backend",
        "legacy_mirror": "frontend/backend",
    }
    assert report["mirror_summary"]["pair_count"] > 0


def test_canonical_working_directory_resolves_canonical_modules():
    origins = probe_canonical_import_origins(REPO_ROOT)

    assert origins == {
        "app": "backend/app.py",
        "astrocartography_service": "backend/astrocartography_service.py",
    }


def test_electron_config_rejects_legacy_source_tree_as_release_input():
    package_payload = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    package_payload["build"]["extraResources"] = [
        {"from": "backend", "to": "backend"},
    ]

    errors = validate_frontend_package_config(package_payload)

    assert errors
    assert "generated compiled runtime" in errors[0]


def test_astrocartography_mirror_drift_is_reported_without_source_ambiguity(tmp_path):
    canonical = tmp_path / "backend"
    legacy = tmp_path / "frontend" / "backend"
    canonical.mkdir(parents=True)
    legacy.mkdir(parents=True)
    canonical_file = canonical / "astrocartography_service.py"
    legacy_file = legacy / "astrocartography_service.py"
    canonical_file.write_text("CANONICAL = True\n", encoding="utf-8")
    legacy_file.write_text("CANONICAL = True\n", encoding="utf-8")

    synchronized = compare_legacy_astrocartography_mirrors(tmp_path)
    assert synchronized[0]["status"] == "synchronized"

    legacy_file.write_text("CANONICAL = False\n", encoding="utf-8")
    diverged = compare_legacy_astrocartography_mirrors(tmp_path)

    assert diverged[0]["status"] == "diverged"
    assert diverged[0]["canonical_sha256"] != diverged[0]["legacy_sha256"]
