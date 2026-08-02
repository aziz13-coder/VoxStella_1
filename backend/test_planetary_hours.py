from pathlib import Path
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

import planetary_hours


class _FakeSwe:
    GREG_CAL = 1
    CALC_RISE = 2
    CALC_SET = 4
    BIT_DISC_CENTER = 8
    SUN = 0

    def __init__(self, rise_jd, set_jd):
        self.rise_jd = rise_jd
        self.set_jd = set_jd
        self.julday_calls = []

    def julday(self, year, month, day, hour, _calendar):
        self.julday_calls.append((year, month, day, hour))
        return 2461149.0

    def rise_trans(self, _jd, _body, flags, _geopos):
        if flags & self.CALC_RISE:
            return (0, (self.rise_jd, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        return (0, (self.set_jd, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))


def test_sunrise_sunset_parser_handles_status_first_shape(monkeypatch):
    fake_swe = _FakeSwe(101.25, 101.75)
    calc = planetary_hours.PlanetaryHoursCalculator(latitude=51.4769, longitude=-0.0005)
    converted = {
        101.25: datetime(2026, 4, 18, 4, 59, tzinfo=timezone.utc),
        101.75: datetime(2026, 4, 18, 19, 0, tzinfo=timezone.utc),
    }

    monkeypatch.setattr(planetary_hours, "swe", fake_swe)
    monkeypatch.setattr(calc, "_jd_to_datetime", lambda jd: converted[jd])

    sunrise, sunset = calc._calculate_sunrise_sunset(date(2026, 4, 18))

    assert sunrise == converted[101.25]
    assert sunset == converted[101.75]
    assert fake_swe.julday_calls == [(2026, 4, 18, 0.0)]


def test_sunset_rolls_forward_when_same_local_day_wraps_utc(monkeypatch):
    fake_swe = _FakeSwe(201.75, 201.25)
    calc = planetary_hours.PlanetaryHoursCalculator(latitude=35.6895, longitude=139.6917)
    converted = {
        201.75: datetime(2026, 4, 18, 20, 5, tzinfo=timezone.utc),
        201.25: datetime(2026, 4, 18, 9, 15, tzinfo=timezone.utc),
    }

    monkeypatch.setattr(planetary_hours, "swe", fake_swe)
    monkeypatch.setattr(calc, "_jd_to_datetime", lambda jd: converted[jd])

    sunrise, sunset = calc._calculate_sunrise_sunset(date(2026, 4, 18))

    assert sunrise == converted[201.75]
    assert sunset == datetime(2026, 4, 19, 9, 15, tzinfo=timezone.utc)
    assert sunset > sunrise


def test_local_date_resolution_does_not_skip_eastern_longitude_sunrise(monkeypatch):
    calc = planetary_hours.PlanetaryHoursCalculator(latitude=35.6762, longitude=139.6503)
    zone = ZoneInfo("Asia/Tokyo")

    def fake_events(seed_date):
        events = {
            date(2026, 7, 30): (
                datetime(2026, 7, 30, 19, 50, tzinfo=timezone.utc),
                datetime(2026, 7, 31, 9, 45, tzinfo=timezone.utc),
            ),
            date(2026, 7, 31): (
                datetime(2026, 7, 31, 19, 51, tzinfo=timezone.utc),
                datetime(2026, 8, 1, 9, 44, tzinfo=timezone.utc),
            ),
            date(2026, 8, 1): (
                datetime(2026, 8, 1, 19, 52, tzinfo=timezone.utc),
                datetime(2026, 8, 2, 9, 43, tzinfo=timezone.utc),
            ),
            date(2026, 8, 2): (
                datetime(2026, 8, 2, 19, 53, tzinfo=timezone.utc),
                datetime(2026, 8, 3, 9, 42, tzinfo=timezone.utc),
            ),
        }
        return events[seed_date]

    monkeypatch.setattr(calc, "_calculate_sunrise_sunset", fake_events)
    daily = calc.calculate_daily_hours_for_local_date(date(2026, 8, 1), "Asia/Tokyo")

    assert daily.sunrise.astimezone(zone).date() == date(2026, 8, 1)
    assert daily.sunset.astimezone(zone).date() == date(2026, 8, 1)
    assert daily.hours[-1].end_time.astimezone(zone).date() == date(2026, 8, 2)
    assert daily.hours[-1].end_time.hour == 19
