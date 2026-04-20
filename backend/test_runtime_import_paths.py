from __future__ import annotations

import importlib
from pathlib import Path


def test_extend_backend_runtime_import_paths_prefers_env_backend_dir(monkeypatch, tmp_path):
    backend_root = tmp_path / "resources" / "backend"
    sibling_backend = backend_root / "backend"
    sibling_backend.mkdir(parents=True)

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(backend_root))
    module = importlib.import_module("runtime_import_paths")
    module = importlib.reload(module)

    inserted = module.extend_backend_runtime_import_paths()

    assert str(backend_root.resolve()) in inserted
    assert str(sibling_backend.resolve()) in inserted
