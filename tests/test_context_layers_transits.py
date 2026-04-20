import os
from datetime import datetime, timezone

import pytest

try:
    from backend.context_layers import (
        compute_solar_return_timestamp,
        compute_solar_arc_windows,
        compute_sr_similarity,
        score_lr_concordance,
    )
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover - swe or module missing in env
    compute_solar_return_timestamp = None
    compute_solar_arc_windows = None
    compute_sr_similarity = None
    score_lr_concordance = None
    swe = None


@pytest.mark.parametrize("year", [2001, 2005])
def test_compute_solar_return_timestamp_precision(year):
    if swe is None or compute_solar_return_timestamp is None:
        pytest.skip("swisseph not available in test env")
    # Pick a stable natal date and compute natal Sun longitude
    natal_dt = datetime(2000, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    jd = swe.julday(natal_dt.year, natal_dt.month, natal_dt.day,
                    natal_dt.hour + natal_dt.minute/60.0 + natal_dt.second/3600.0)
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    natal_lon = float(pos[0]) % 360.0

    ts = compute_solar_return_timestamp(natal_lon, year)
    assert ts is not None, "SR timestamp should be computed"
    jd2 = swe.julday(ts.year, ts.month, ts.day, ts.hour + ts.minute/60.0 + ts.second/3600.0)
    pos2, _ = swe.calc_ut(jd2, swe.SUN, swe.FLG_SWIEPH)
    lon2 = float(pos2[0]) % 360.0
    # Require ≤ ~0.008° difference (~<= 1 minute UT for Sun motion)
    diff = abs(((lon2 - natal_lon + 180.0) % 360.0) - 180.0)
    assert diff < 0.008, f"SR root refinement too coarse: {diff} deg"


def test_compute_solar_arc_windows_basic():
    if swe is None or compute_solar_arc_windows is None:
        pytest.skip("swisseph not available in test env")
    natal_dt = datetime(2000, 3, 20, 0, 0, 0, tzinfo=timezone.utc)
    # Minimal natal chart_data with houses and a couple of planets
    natal_cd = {
        'houses': [0.0]*12,
        'planets': {
            'Sun': {'longitude': 0.0, 'latitude': 0.0},
            'Mars': {'longitude': 120.0, 'latitude': 0.0},
        }
    }
    wins = compute_solar_arc_windows(natal_dt, 2001, natal_cd)
    assert isinstance(wins, list)
    # Expect at least one SA window for directed Sun/Mars to angles or each other
    assert len(wins) > 0
    # Windows must have valid ISO start/end and start < end
    from datetime import datetime as _dt
    for w in wins[:5]:
        s = _dt.fromisoformat(str(w['start']).replace('Z','+00:00'))
        e = _dt.fromisoformat(str(w['end']).replace('Z','+00:00'))
        assert e > s


def test_solar_similarity_does_not_award_sun_return_tautology():
    if compute_sr_similarity is None:
        pytest.skip("context_layers unavailable")
    natal_cd = {
        'houses': [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        'planets': {
            'Sun': {'longitude': 14.0, 'house': 1},
            'Mars': {'longitude': 120.0, 'house': 5},
        },
    }
    sr_cd = {
        'houses': [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        'planets': {
            'Sun': {'longitude': 14.0, 'house': 1},
            'Mars': {'longitude': 240.0, 'house': 9},
        },
    }
    sim = compute_sr_similarity(natal_cd, sr_cd)
    tags = sim.get('tags') or []
    assert 'Sun returns to place' not in tags
    assert 'Sun same sign' not in tags


def test_lunar_concordance_does_not_award_moon_return_tautology():
    if score_lr_concordance is None:
        pytest.skip("context_layers unavailable")
    natal_cd = {
        'timestamp': '2026-01-01T00:00:00+00:00',
        'houses': [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        'planets': {
            'Moon': {'longitude': 50.0, 'house': 2},
            'Mars': {'longitude': 120.0, 'house': 5},
        },
    }
    sr_cd = {
        'houses': [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        'planets': {
            'Moon': {'longitude': 10.0, 'house': 1},
            'Mars': {'longitude': 160.0, 'house': 6},
        },
    }
    lr_cd = {
        'timestamp': '2026-02-01T00:00:00+00:00',
        'houses': [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        'planets': {
            'Moon': {'longitude': 50.0, 'house': 2},
            'Mars': {'longitude': 180.0, 'house': 7},
        },
    }
    score, tags = score_lr_concordance(natal_cd, sr_cd, lr_cd, [])
    assert isinstance(score, (int, float))
    assert 'Moon LR~Natal place' not in tags
