from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def patched_primary_directions(monkeypatch):
    import backend.primary_directions as pd

    class DummySwe:
        pass

    monkeypatch.setattr(pd, "swe", DummySwe())

    def fake_collect(natal_cd, natal_dt, include_modern=False):
        positions = {
            "Asc": {
                "lon": 0.0,
                "lat": 0.0,
                "oa": 10.0,
                "semi_arc": 1.0,
            },
            "Sun": {
                "lon": 120.0,
                "lat": 0.0,
                "oa": 40.0,
                "semi_arc": 1.0,
            },
        }
        return positions, 23.4, 45.0

    monkeypatch.setattr(pd, "_collect_natal_positions", fake_collect)

    def fake_sr(lon, target_year):
        return datetime(target_year, 4, 15, tzinfo=timezone.utc)

    monkeypatch.setattr(pd, "compute_solar_return_timestamp", fake_sr)
    return pd


def test_arc_to_days_and_signification(patched_primary_directions):
    pd = patched_primary_directions
    natal_dt = datetime(1985, 3, 1, tzinfo=timezone.utc)
    natal_cd = {
        "planets": {
            "Sun": {"longitude": 120.0, "latitude": 0.0, "house": 10},
        },
        "houses": [0.0] * 12,
    }

    windows = pd.compute_primary_direction_windows(
        natal_dt,
        2025,
        natal_cd,
        aspects=[0.0],
        window_days=5,
    )

    assert windows, "Expected at least one primary direction window"
    item = windows[0]["item"]

    # 30° arc should translate to ~30.437 days using Morin conversion
    assert pytest.approx(item["arc_degrees"], rel=1e-6) == 30.0
    assert pytest.approx(item["arc_days"], rel=1e-6) == 30.43749

    timestamp = datetime.fromisoformat(windows[0]["timestamp"])
    expected_dt = datetime(2025, 4, 15, tzinfo=timezone.utc) + timedelta(days=30.43749)
    assert abs((timestamp - expected_dt).total_seconds()) < 1.0

    signification = item["signification"]
    assert signification["domain"] == "honors"
    assert signification["label"] == "honors"
    assert signification["source"] == "promittor"
