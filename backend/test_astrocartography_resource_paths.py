from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from astrocartography_resource_paths import resolve_astrocartography_resource_path


def test_resolve_astrocartography_resource_path_prefers_packaged_backend_dir(tmp_path, monkeypatch):
    backend_dir = tmp_path / "runtime-backend"
    asset_dir = backend_dir / "knowledge" / "astrocartography"
    asset_dir.mkdir(parents=True)
    asset_path = asset_dir / "interpretation_runtime.json"
    asset_path.write_text('{"ok": true}', encoding="utf-8")

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(backend_dir))

    resolved = resolve_astrocartography_resource_path("interpretation_runtime.json")

    assert resolved == asset_path
