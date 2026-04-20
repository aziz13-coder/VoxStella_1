from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_resource_paths import resolve_mundane_resource_path


def test_resolve_mundane_resource_path_prefers_env_backend_dir(monkeypatch, tmp_path):
    backend_root = tmp_path / "resources" / "backend"
    knowledge_dir = backend_root / "knowledge" / "mundane"
    knowledge_dir.mkdir(parents=True)
    target = knowledge_dir / "mundane_chart_types.runtime.json"
    target.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(backend_root))

    resolved = resolve_mundane_resource_path("mundane_chart_types.runtime.json")

    assert resolved == target
