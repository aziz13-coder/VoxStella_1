from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from weather_resource_paths import resolve_weather_resource_path


def test_resolve_weather_resource_path_prefers_packaged_backend_dir(tmp_path, monkeypatch):
    backend_dir = tmp_path / "runtime-backend"
    asset_dir = backend_dir / "knowledge" / "weather"
    asset_dir.mkdir(parents=True)
    asset_path = asset_dir / "weather_family_models.runtime.json"
    asset_path.write_text('{"families": []}', encoding="utf-8")

    monkeypatch.setenv("HORARY_BACKEND_DIR", str(backend_dir))

    resolved = resolve_weather_resource_path("weather_family_models.runtime.json")

    assert resolved == asset_path
