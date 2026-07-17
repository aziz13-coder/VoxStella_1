from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from house_influence import compute_house_influences
from sect import compute_sect_info


def _planet(name, longitude, sign, house, latitude=0.0):
    return {
        "planet": name,
        "longitude": longitude,
        "latitude": latitude,
        "sign": sign,
        "house": house,
    }


def _row(result, planet):
    return next(item for item in result["planets"] if item["planet"] == planet)


def test_sun_altitude_takes_precedence_over_house_number():
    above = compute_sect_info({
        "sun_altitude_deg": 3.0,
        "planets": [_planet("Sun", 280.0, "Capricorn", 1)],
    })
    below = compute_sect_info({
        "sun_altitude_deg": -0.5,
        "planets": [_planet("Sun", 280.0, "Capricorn", 12)],
    })

    assert above["chart_sect"] == "diurnal"
    assert above["sect_light"] == "Sun"
    assert below["chart_sect"] == "nocturnal"
    assert below["sect_light"] == "Moon"


def test_sun_altitude_can_be_computed_from_serialized_chart_context():
    result = compute_sect_info({
        "timezone_info": {
            "utc_time": "2026-01-01T05:00:00+00:00",
            "coordinates": {"latitude": 31.778, "longitude": 35.235},
        },
        "planets": [
            _planet("Sun", 280.78085060340607, "Capricorn", 1, latitude=0.00017714706270663841),
        ],
    })

    assert result["chart_sect"] == "diurnal"
    assert result["sun_altitude_deg"] > 0


def test_nocturnal_planet_above_horizon_can_be_hayz_in_night_chart():
    result = compute_sect_info({
        "sun_altitude_deg": -10.0,
        "planets": [
            _planet("Sun", 300.0, "Aquarius", 4),
            _planet("Moon", 40.0, "Taurus", 10),
        ],
    })

    moon = _row(result, "Moon")
    assert result["chart_sect"] == "nocturnal"
    assert moon["in_sect"] is True
    assert moon["sign_polarity_match"] is True
    assert moon["preferred_hemisphere"] == "above"
    assert moon["hemisphere_match"] is True
    assert moon["hayz"] is True
    assert result["hayz_planets"] == ["Moon"]


def test_missing_sun_does_not_default_to_day_chart():
    result = compute_sect_info({
        "planets": [_planet("Moon", 40.0, "Taurus", 10)],
    })

    moon = _row(result, "Moon")
    assert result["chart_sect"] is None
    assert result["sect_light"] is None
    assert moon["in_sect"] is None
    assert result["in_sect_planets"] == []
    assert result["out_of_sect_planets"] == []


def test_sign_polarity_follows_planet_assigned_sect():
    result = compute_sect_info({
        "sun_altitude_deg": 5.0,
        "planets": [
            _planet("Sun", 20.0, "Aries", 10),
            _planet("Mars", 40.0, "Taurus", 3),
        ],
    })

    mars = _row(result, "Mars")
    assert result["chart_sect"] == "diurnal"
    assert mars["assigned_sect"] == "nocturnal"
    assert mars["in_sect"] is False
    assert mars["preferred_sign_polarity"] == "feminine"
    assert mars["sign_polarity_match"] is True
    assert mars["preferred_hemisphere"] == "below"


def test_malefic_of_sect_does_not_receive_out_of_sect_keywords():
    chart_data = {
        "sun_altitude_deg": 5.0,
        "houses": [i * 30.0 for i in range(12)],
        "house_rulers": {
            "1": "Mars",
            "2": "Venus",
            "3": "Mercury",
            "4": "Moon",
            "5": "Sun",
            "6": "Mercury",
            "7": "Venus",
            "8": "Mars",
            "9": "Jupiter",
            "10": "Saturn",
            "11": "Saturn",
            "12": "Jupiter",
        },
        "planets": [
            _planet("Sun", 20.0, "Aries", 10),
            _planet("Mars", 40.0, "Taurus", 3),
            _planet("Saturn", 280.0, "Capricorn", 10),
        ],
    }

    result = compute_house_influences(chart_data, {})
    influences = [
        influence
        for house in result["houses"]
        for influence in house["influences"]
    ]
    saturn = next(
        influence for influence in influences
        if influence["planet"] == "Saturn" and influence["type"] == "occupation"
    )
    mars = next(
        influence for influence in influences
        if influence["planet"] == "Mars" and influence["type"] == "occupation"
    )

    assert "malefic_of_sect" in saturn["keywords"]
    assert "in_sect" in saturn["keywords"]
    assert "harsher_effects" not in saturn["keywords"]
    assert "out_of_sect" in mars["keywords"]
    assert "harsher_effects" in mars["keywords"]
