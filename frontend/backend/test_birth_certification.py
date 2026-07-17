from datetime import date, datetime, time
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

os.environ.setdefault("ALLOW_DEV_LICENSE_BYPASS", "1")
os.environ.setdefault("VOX_STELLA_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import birth_certification as bc


def test_galaxy_default_aspects_include_minor_hard_and_positive_opposition():
    aspects = {name: (angle, coeff) for name, angle, coeff in bc._ASPECTS}

    assert aspects["semisquare"] == (45.0, -0.50)
    assert aspects["sesquiquadrate"] == (135.0, -0.40)
    assert aspects["quincunx"] == (150.0, -0.20)
    assert aspects["opposition"] == (180.0, 0.90)


def test_galaxy_default_instruments_cover_reference_rectificator_set():
    ids = [bc._instrument_id(item) for item in bc._DEFAULT_INSTRUMENTS]

    assert ids == [
        "transit",
        "direction_reverse",
        "profection_reverse",
        "primary_progression",
        "secondary_progression_local",
        "secondary_progression_natal",
        "tertiary_progression",
        "minor_progression",
    ]


def test_build_points_adds_galaxy_cusps_lots_and_south_node(monkeypatch):
    class FakeSwe:
        GREG_CAL = 1
        FLG_SWIEPH = 2
        FLG_SPEED = 256
        SUN = 0
        MOON = 1
        MERCURY = 2
        VENUS = 3
        MARS = 4
        JUPITER = 5
        SATURN = 6
        URANUS = 7
        NEPTUNE = 8
        PLUTO = 9
        MEAN_NODE = 10
        CHIRON = 15
        MEAN_APOG = 12
        CERES = 17
        PALLAS = 18
        JUNO = 19
        VESTA = 20

        @staticmethod
        def julday(_year, _month, _day, _hour, _calendar):
            return 2450000.0

        @staticmethod
        def set_ephe_path(_path):
            return None

        @staticmethod
        def calc_ut(_jd_ut, point_id, _flags):
            return ([float(point_id * 10 % 360), 0.0, 0.0, 0.0], 0)

        @staticmethod
        def houses(_jd_ut, _latitude, _longitude, _house_code):
            cusps = [10.0, 40.0, 70.0, 100.0, 130.0, 160.0, 190.0, 220.0, 250.0, 280.0, 310.0, 340.0]
            ascmc = [15.0, 105.0, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0]
            return cusps, ascmc

    monkeypatch.setattr(bc, "swe", FakeSwe)

    points = bc._build_points(datetime(1990, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")), 31.0, 35.0)

    assert points["Asc"].longitude == 15.0
    assert points["MC"].longitude == 105.0
    assert points["Dsc"].longitude == 195.0
    assert points["IC"].longitude == 285.0
    assert points["Cusp 2"].longitude == 40.0
    assert points["Cusp 12"].longitude == 340.0
    assert points["South Node"].longitude == 280.0
    assert points["Fortuna"].kind == "lot"
    assert points["Cross"].kind == "lot"


def test_normalization_uses_reference_min_floor_formula():
    rows = [
        bc._RawRow(timestamp=datetime(1990, 1, 1, 0, 0), raw_plus=10.0, raw_minus=0.0),
        bc._RawRow(timestamp=datetime(1990, 1, 1, 0, 1), raw_plus=20.0, raw_minus=0.0),
        bc._RawRow(timestamp=datetime(1990, 1, 1, 0, 2), raw_plus=0.0, raw_minus=-30.0),
    ]

    normalized, amplitude = bc.normalize_rectification_rows(rows)

    assert amplitude == 30.0
    assert normalized[0]["favorable"] == 33.33
    assert normalized[1]["favorable"] == 66.67
    assert normalized[2]["tense"] == 100.0


def test_precision_filter_drops_fast_points_for_day_level_events():
    base = {
        "Sun": bc._Point("Sun", 20.0, "planet"),
        "Moon": bc._Point("Moon", 10.0, "planet"),
        "Asc": bc._Point("Asc", 30.0, "angle"),
    }
    shifted = {
        "Sun": bc._Point("Sun", 20.5, "planet"),
        "Moon": bc._Point("Moon", 11.0, "planet"),
        "Asc": bc._Point("Asc", 30.2, "angle"),
    }

    allowed = bc._allowed_dynamic_points(base, shifted, precision=4)

    assert allowed["Sun"] is True
    assert allowed["Moon"] is False
    assert allowed["Asc"] is False


def test_month_precision_uses_calendar_month_shift():
    shifted = bc._shift_datetime_for_precision(
        datetime(2024, 1, 31, 12, 0, tzinfo=ZoneInfo("UTC")),
        precision=6,
    )

    assert shifted == datetime(2024, 4, 30, 12, 0, tzinfo=ZoneInfo("UTC"))


def test_rectification_scan_returns_ranked_candidate_with_fake_points(monkeypatch):
    def fake_points(dt_utc, _latitude, _longitude, _house_system="T"):
        minute_of_day = dt_utc.hour * 60 + dt_utc.minute
        if dt_utc.year == 1990:
            return {"Asc": bc._Point("Asc", float(minute_of_day % 360), "angle")}
        return {"Mars": bc._Point("Mars", 60.0, "planet")}

    monkeypatch.setattr(bc, "_build_points", fake_points)
    settings = bc.RectificationSettings(
        birth_date=date(1990, 1, 1),
        birth_latitude=31.0,
        birth_longitude=35.0,
        birth_timezone="UTC",
        search_start_time=time(0, 0),
        search_end_time=time(2, 0),
        instruments=[{"id": "transit", "weight": 1.0}],
        include_series=False,
    )
    events = [
        bc.RectificationEvent(
            label="test event",
            timestamp=datetime(2020, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")),
            latitude=31.0,
            longitude=35.0,
            precision=1,
        )
    ]

    result = bc.rectify_birth_time(settings, events)

    assert result["meta"]["row_count"] == 121
    assert result["top_candidates"][0]["timestamp"].endswith("01:00:00+00:00")
    assert result["top_candidates"][0]["favorable"] == 100.0
    assert result["top_candidates"][0]["strength"] == 100.0
    assert result["top_candidates"][0]["rank"] == 1


def test_galaxy_instrument_split_weights_change_angle_vs_planet_contribution(monkeypatch):
    def fake_points(_dt_utc, _latitude, _longitude, _house_system="T"):
        return {
            "Mars": bc._Point("Mars", 0.0, "planet"),
            "Asc": bc._Point("Asc", 0.0, "angle"),
        }

    monkeypatch.setattr(bc, "_build_points", fake_points)
    settings = bc.RectificationSettings(
        birth_date=date(1990, 1, 1),
        birth_latitude=31.0,
        birth_longitude=35.0,
        birth_timezone="UTC",
        search_start_time=time(0, 0),
        search_end_time=time(0, 0),
        instruments=[{"id": "primary_progression", "weight": 1.0}],
        include_series=True,
    )
    events = [
        bc.RectificationEvent(
            label="same minute",
            timestamp=datetime(1990, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")),
            latitude=31.0,
            longitude=35.0,
            precision=1,
        )
    ]

    result = bc.rectify_birth_time(settings, events)

    assert result["instruments"][0]["planet_weight"] == 0.0
    assert result["instruments"][0]["angle_weight"] == 0.99
    assert result["series"][0]["hit_count"] == 1
    assert result["series"][0]["raw_plus"] == 1.323135
    assert result["top_candidates"][0]["favorable"] == 100.0


def test_route_rejects_non_object_json():
    import app as app_module

    client = app_module.app.test_client()

    response = client.post("/api/astro-clock/certification/rectify", json=[])
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "JSON object body is required"


def test_route_returns_rectification_contract(monkeypatch):
    import app as app_module

    def fake_points(dt_utc, _latitude, _longitude, _house_system="T"):
        minute_of_day = dt_utc.hour * 60 + dt_utc.minute
        if dt_utc.year == 1990:
            return {"Asc": bc._Point("Asc", float(minute_of_day % 360), "angle")}
        return {"Mars": bc._Point("Mars", 60.0, "planet")}

    monkeypatch.setattr(bc, "_build_points", fake_points)
    client = app_module.app.test_client()

    response = client.post(
        "/api/astro-clock/certification/rectify",
        json={
            "birth": {
                "date": "1990-01-01",
                "latitude": 31.0,
                "longitude": 35.0,
                "timezone": "UTC",
            },
            "search": {"start_time": "00:58", "end_time": "01:02"},
            "include_series": False,
            "instruments": [{"id": "transit", "weight": 1.0}],
            "events": [
                {
                    "label": "test event",
                    "timestamp": "2020-01-01T12:00:00+00:00",
                    "latitude": 31.0,
                    "longitude": 35.0,
                    "precision": 1,
                }
            ],
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    data = payload["data"]
    assert data["meta"]["row_count"] == 5
    assert data["top_candidates"][0]["rank"] == 1
    assert data["top_candidates"][0]["timestamp"].endswith("01:00:00+00:00")
    assert data["certification"]["status"] == "unresolved_rectification"
