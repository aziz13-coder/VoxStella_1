from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from election_models.marriage import score_marriage_election


def _houses(start: float = 0.0):
    return [((start + i * 30.0) % 360.0) for i in range(12)]


def _base_event_chart(*, house_start: float = 30.0):
    return {
        "houses": _houses(house_start),
        "planets": {
            "Sun": {"longitude": 40.0, "house": 10},
            "Venus": {"longitude": 20.0, "house": 1},
            "Jupiter": {"longitude": 210.0, "house": 7},
            "Mars": {"longitude": 280.0, "house": 9},
            "Saturn": {"longitude": 320.0, "house": 11},
            "Moon": {"longitude": 35.0, "house": 1, "speed": 13.4},
        },
        "aspects": [],
    }


def _natal_chart():
    return {
        "houses": _houses(30.0),
        "planets": {
            "Venus": {"longitude": 35.0, "house": 1},
            "Jupiter": {"longitude": 210.0, "house": 7},
            "Mars": {"longitude": 300.0, "house": 10},
            "Saturn": {"longitude": 5.0, "house": 12},
        },
    }


def test_alpha_marks_natal_omission_as_natal_aware_gap():
    result = score_marriage_election(_base_event_chart())

    assert "Natal omitted - natal-aware checks unavailable" in result.tags
    assert "Natal omitted - natal-aware checks unavailable" in (result.cautions or [])


def test_alpha_no_longer_uses_unsourced_unfavored_seventh_sign_table():
    chart = _base_event_chart(house_start=120.0)

    result = score_marriage_election(chart)

    assert not any(tag.startswith("Unfavored 7th sign") for tag in result.tags)
    assert not any(tag.startswith("Preferred fixed 7th") for tag in result.tags)


def test_alpha_penalizes_moon_applying_to_retrograde_planet():
    chart = _base_event_chart()
    chart["planets"]["Jupiter"]["retrograde"] = True
    chart["moon_next_aspect"] = {"planet": "Jupiter", "aspect": "Conjunction"}

    result = score_marriage_election(chart)

    assert "Moon applying to retrograde Jupiter" in result.tags
    assert "Moon applying to retrograde Jupiter" in (result.cautions or [])


def test_alpha_penalizes_moon_to_mars_from_venus_sign():
    chart = _base_event_chart()
    chart["planets"]["Moon"] = {"longitude": 35.0, "house": 1, "speed": 13.4}
    chart["moon_next_aspect"] = {"planet": "Mars", "aspect": "Conjunction"}

    result = score_marriage_election(chart)

    assert "Avoid Moon application: Mars from Venus sign (Taurus)" in result.tags
    assert "Avoid Moon application: Mars from Venus sign (Taurus)" in (result.cautions or [])


def test_alpha_uses_return_and_transit_proxies_when_natal_is_present():
    chart = _base_event_chart()
    natal_cd = _natal_chart()
    current_timestamp = datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc)

    without_proxies = score_marriage_election(
        chart,
        options={
            "natal_cd": natal_cd,
            "current_timestamp": current_timestamp,
        },
    )
    with_proxies = score_marriage_election(
        chart,
        natal_hits=[
            {"transiting": "Jupiter", "aspect": "Trine", "target_label": "Venus"},
        ],
        options={
            "natal_cd": natal_cd,
            "current_timestamp": current_timestamp,
            "sr_windows": [(current_timestamp - timedelta(hours=1), current_timestamp + timedelta(hours=1))],
            "lr_list": [current_timestamp + timedelta(hours=6)],
        },
    )

    assert with_proxies.value > without_proxies.value
    assert "Marriage SR window active" in with_proxies.tags
    assert "Near lunar return (<=12h)" in with_proxies.tags
    assert any(tag.startswith("Directions/Transits favorable") for tag in with_proxies.tags)
