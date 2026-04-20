from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import horary_engine.services.geolocation as geolocation


def test_safe_geocode_rejects_serialized_object_payload(monkeypatch):
    called = {"value": False}

    class _FakeGeolocator:
        def geocode(self, *_args, **_kwargs):
            called["value"] = True
            raise AssertionError("Geocoder should not be called for invalid object payloads")

    monkeypatch.setattr(geolocation, "Nominatim", lambda **_kwargs: _FakeGeolocator())

    with pytest.raises(geolocation.LocationError, match="Invalid location payload"):
        geolocation.safe_geocode("[object Object]")

    assert called["value"] is False


def test_search_live_location_candidates_ignores_serialized_object_payload():
    assert geolocation.search_live_location_candidates("[object Object]") == []
