from backend.election_models.conception import score_conception_election


def _make_planet(name, lon, sign, house):
    return {
        "planet": name,
        "longitude": lon,
        "sign": sign,
        "house": house,
    }


def _base_chart():
    # Asc 0° Aries, 5th cusp 120° (Leo)
    cusps = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
    planets = [
        _make_planet("Moon", 310.0, "Aquarius", 11),
        _make_planet("Sun", 250.0, "Sagittarius", 9),
        _make_planet("Venus", 50.0, "Taurus", 2),
        _make_planet("Jupiter", 240.0, "Sagittarius", 9),
        _make_planet("Mars", 20.0, "Aries", 1),
        _make_planet("Saturn", 280.0, "Capricorn", 10),
        _make_planet("Mercury", 70.0, "Gemini", 3),
    ]
    aspects = [
        {"planet1": "Moon", "planet2": "Sun", "aspect": "Trine", "phase": "Applying"},
        {"planet1": "Moon", "planet2": "Venus", "aspect": "Square", "phase": "Separating"},
        {"planet1": "Sun", "planet2": "Mars", "aspect": "Trine", "phase": "Applying"},
    ]
    return {
        "house_cusps": cusps,
        "planets": planets,
        "planetary_aspects": aspects,
    }


def test_conception_gender_bias_masculine():
    chart = _base_chart()

    male_score = score_conception_election(chart, options={"gender": "male"})
    female_score = score_conception_election(chart, options={"gender": "female"})

    assert male_score.value > female_score.value, "Masculine setup should favor male preference"
    assert any("Sex focus (boy)" in tag for tag in male_score.tags), "Missing male focus tag"
    assert any("Sex focus (girl)" in tag for tag in female_score.tags), "Missing female focus tag"


def test_conception_gender_bias_feminine():
    chart = _base_chart()
    # Flip key signs to feminine placements
    chart["planets"] = [
        _make_planet("Moon", 80.0, "Cancer", 4),
        _make_planet("Sun", 130.0, "Leo", 5),
        _make_planet("Venus", 190.0, "Libra", 7),
        _make_planet("Jupiter", 220.0, "Scorpio", 8),
        _make_planet("Mars", 200.0, "Scorpio", 8),
        _make_planet("Saturn", 40.0, "Taurus", 2),
        _make_planet("Mercury", 155.0, "Virgo", 6),
    ]
    chart["house_cusps"] = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 0]
    chart["planetary_aspects"] = [
        {"planet1": "Moon", "planet2": "Venus", "aspect": "Trine", "phase": "Applying"},
        {"planet1": "Moon", "planet2": "Saturn", "aspect": "Sextile", "phase": "Applying"},
    ]

    female_score = score_conception_election(chart, options={"gender": "female"})
    male_score = score_conception_election(chart, options={"gender": "male"})

    assert female_score.value > male_score.value, "Feminine setup should favor female preference"
    assert any("Sex testimonies favor" in tag for tag in female_score.tags)
