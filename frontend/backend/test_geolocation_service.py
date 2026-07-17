from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import horary_engine.services.geolocation as geolocation


def test_safe_geocode_rejects_serialized_object_payload(monkeypatch):
    called = {"value": False}

    def _fail_catalog_lookup(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("Catalog lookup should not be called for invalid object payloads")

    monkeypatch.setattr(geolocation, "_search_offline_city_catalog", _fail_catalog_lookup)

    with pytest.raises(geolocation.LocationError, match="Invalid location payload"):
        geolocation.safe_geocode("[object Object]")

    assert called["value"] is False


def test_safe_geocode_uses_bundled_city_catalog_without_network():
    latitude, longitude, label = geolocation.safe_geocode("New York")

    assert latitude == pytest.approx(40.71427, abs=0.05)
    assert longitude == pytest.approx(-74.00597, abs=0.05)
    assert "New York" in label


def test_search_location_candidates_uses_offline_city_catalog():
    candidates = geolocation.search_live_location_candidates("Jerusalem, Israel", limit=3)

    assert candidates
    assert candidates[0]["live_source"] == "offline_city_catalog"
    assert candidates[0]["timezone"] == "Asia/Jerusalem"


def test_timezone_fallback_uses_bundled_catalog():
    manager = geolocation.TimezoneManager()

    assert manager._get_fallback_timezone(40.7128, -74.0060) == "America/New_York"


def test_search_live_location_candidates_ignores_serialized_object_payload():
    assert geolocation.search_live_location_candidates("[object Object]") == []


def test_no_online_geocoding_imports_or_calls_in_editable_source():
    repo_root = next(parent for parent in Path(__file__).resolve().parents if (parent / "AGENTS.md").exists())
    roots = [
        repo_root / "backend",
        repo_root / "frontend" / "backend",
        repo_root / "frontend" / "src",
    ]
    blocked_parts = {
        "build",
        "dist",
        "dist-electron",
        "node_modules",
        "resources",
        "venv",
        "website",
        "win-unpacked",
        "__pycache__",
    }
    patterns = (
        "from " + "geo" + "py",
        "import " + "geo" + "py",
        "geo" + "py",
        "Nomi" + "natim",
        "." + "geo" + "code(",
        "geolocator." + "reverse(",
    )
    violations = []

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part in blocked_parts for part in path.parts):
                continue
            if not path.is_file() or path.suffix not in {".py", ".js", ".jsx", ".mjs", ".ts", ".tsx"}:
                continue
            if path.name.startswith("test_") or path.parent.name == "tests":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern in text:
                    violations.append(f"{path.relative_to(repo_root)} uses {pattern}")

    assert violations == []
