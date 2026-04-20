from __future__ import annotations

from pathlib import Path
import sys

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

try:
    import backend.event_keywords_helper as ekh
except Exception:
    import event_keywords_helper as ekh


def _write_catalog(path: Path) -> None:
    path.write_text(
        """```yaml
attack_violence:
  keywords:
    primary: [attack_violence, conflict]
    secondary: [relationship_conflict]
  synonyms: [assault]
```
""",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch):
    monkeypatch.setattr(ekh, "_CACHE", None)


def test_merge_event_synonyms_reads_catalog_next_to_frozen_executable(monkeypatch, tmp_path: Path):
    exec_dir = tmp_path / "runtime"
    exec_dir.mkdir()
    _write_catalog(exec_dir / "event_keywords_catalog.md")

    monkeypatch.setattr(ekh, "__file__", str(tmp_path / "missing" / "event_keywords_helper.py"))
    monkeypatch.setattr(ekh.os, "getcwd", lambda: str(tmp_path / "cwd"))
    monkeypatch.setattr(sys, "executable", str(exec_dir / "horary_backend.exe"))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert Path(ekh._dict_path()) == exec_dir / "event_keywords_catalog.md"
    tokens = ekh.merge_event_synonyms(["relationship_conflict"], promote_canonical=True)

    assert "attack_violence" in tokens


def test_dict_path_prefers_meipass_bundle_when_available(monkeypatch, tmp_path: Path):
    meipass_dir = tmp_path / "bundle"
    meipass_dir.mkdir()
    catalog = meipass_dir / "event_keywords_catalog.md"
    _write_catalog(catalog)

    monkeypatch.setattr(ekh, "__file__", str(tmp_path / "missing" / "event_keywords_helper.py"))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "runtime" / "horary_backend.exe"))
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass_dir), raising=False)

    assert Path(ekh._dict_path()) == catalog
