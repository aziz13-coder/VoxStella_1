import json
import sys
from pathlib import Path

import synastry_engine


def test_catalog_path_falls_back_to_frozen_executable_dir(tmp_path, monkeypatch):
    catalog_path = tmp_path / "synastry_rule_catalog.json"
    catalog_path.write_text(json.dumps({"sources": [], "categories": {}, "rule_families": []}), encoding="utf-8")

    fake_module_path = tmp_path / "subdir" / "synastry_engine.py"
    fake_module_path.parent.mkdir(parents=True, exist_ok=True)
    fake_module_path.write_text("# placeholder", encoding="utf-8")

    monkeypatch.setattr(synastry_engine, "__file__", str(fake_module_path))
    monkeypatch.setenv("VOX_STELLA_SYNASTRY_RULE_CATALOG", "")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "horary_backend.exe"), raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", None, raising=False)

    synastry_engine._load_catalog.cache_clear()
    try:
        resolved = synastry_engine._catalog_path()
        assert resolved == catalog_path
        assert synastry_engine._load_catalog() == {"sources": [], "categories": {}, "rule_families": []}
    finally:
        synastry_engine._load_catalog.cache_clear()
