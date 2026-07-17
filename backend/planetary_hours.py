# -*- coding: utf-8 -*-
"""
Planetary Hours Calculator

Calculates traditional planetary hours based on sunrise/sunset times.
Each day is divided into 24 unequal hours, with planets ruling in
Chaldean order starting from the day ruler.

Traditional planetary day rulers:
- Sunday: Sun
- Monday: Moon
- Tuesday: Mars
- Wednesday: Mercury
- Thursday: Jupiter
- Friday: Venus
- Saturday: Saturn

Created for Astro Clock feature
@author: sabaa
"""

import datetime
import math
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Swiss Ephemeris for precise calculations
from swisseph_state import swisseph as swe

from models import Planet

logger = logging.getLogger(__name__)


class DayRuler(Enum):
    """Traditional planetary day rulers."""
    SUNDAY = Planet.SUN
    MONDAY = Planet.MOON
    TUESDAY = Planet.MARS
    WEDNESDAY = Planet.MERCURY
    THURSDAY = Planet.JUPITER
    FRIDAY = Planet.VENUS
    SATURDAY = Planet.SATURN


# Chaldean order for planetary hours
CHALDEAN_ORDER = [
    Planet.SATURN,
    Planet.JUPITER,
    Planet.MARS,
    Planet.SUN,
    Planet.VENUS,
    Planet.MERCURY,
    Planet.MOON
]


@dataclass
class PlanetaryHour:
    """Represents a single planetary hour."""
    hour_number: int  # 1-24
    ruling_planet: Planet
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration_minutes: float
    is_day_hour: bool  # True if during daylight, False if night


@dataclass
class DailyPlanetaryHours:
    """Complete planetary hours for a day."""
    date: datetime.date
    day_ruler: Planet
    sunrise: datetime.datetime
    sunset: datetime.datetime
    hours: List[PlanetaryHour]
    current_hour: Optional[PlanetaryHour] = None


class PlanetaryHoursCalculator:
    """Calculator for traditional planetary hours."""

    def __init__(self, latitude: float = 0.0, longitude: float = 0.0):
        """Initialize with location coordinates."""
        self.latitude = latitude
        self.longitude = longitude
        logger.info(f"PlanetaryHoursCalculator initialized for lat: {latitude}, lon: {longitude}")

    def get_current_planetary_hour(self, dt: Optional[datetime.datetime] = None) -> PlanetaryHour:
        """Get the current planetary hour."""
        if dt is None:
            dt = datetime.datetime.now(datetime.timezone.utc)
        elif dt.tzinfo is None:
            # Assume UTC for comparisons
            dt = dt.replace(tzinfo=datetime.timezone.utc)

        daily_hours = self.calculate_daily_hours(dt.date())
        return self._find_current_hour(daily_hours, dt)

    def calculate_daily_hours(self, date: datetime.date) -> DailyPlanetaryHours:
        """Calculate all 24 planetary hours for a given date."""
        logger.info(f"Calculating planetary hours for {date}")

        # Get day ruler
        day_ruler = self._get_day_ruler(date)

        # Calculate sunrise and sunset
        sunrise, sunset = self._calculate_sunrise_sunset(date)

        # Calculate day and night durations
        day_duration = (sunset - sunrise).total_seconds() / 3600  # hours
        night_duration = 24 - day_duration

        # Calculate hour durations
        day_hour_duration = day_duration / 12  # 12 day hours
        night_hour_duration = night_duration / 12  # 12 night hours

        # Generate all 24 hours
        hours = []
        current_time = sunrise

        # Day hours (1-12)
        day_start_planet_index = self._get_planet_index(day_ruler)

        for hour_num in range(1, 13):  # Hours 1-12 (day)
            planet_index = (day_start_planet_index + (hour_num - 1)) % 7
            ruling_planet = CHALDEAN_ORDER[planet_index]

            end_time = current_time + datetime.timedelta(hours=day_hour_duration)

            hours.append(PlanetaryHour(
                hour_number=hour_num,
                ruling_planet=ruling_planet,
                start_time=current_time,
                end_time=end_time,
                duration_minutes=day_hour_duration * 60,
                is_day_hour=True
            ))

            current_time = end_time

        # Night hours (13-24)
        current_time = sunset

        for hour_num in range(13, 25):  # Hours 13-24 (night)
            planet_index = (day_start_planet_index + (hour_num - 1)) % 7
            ruling_planet = CHALDEAN_ORDER[planet_index]

            end_time = current_time + datetime.timedelta(hours=night_hour_duration)

            hours.append(PlanetaryHour(
                hour_number=hour_num,
                ruling_planet=ruling_planet,
                start_time=current_time,
                end_time=end_time,
                duration_minutes=night_hour_duration * 60,
                is_day_hour=False
            ))

            current_time = end_time

        return DailyPlanetaryHours(
            date=date,
            day_ruler=day_ruler,
            sunrise=sunrise,
            sunset=sunset,
            hours=hours
        )

    def _get_day_ruler(self, date: datetime.date) -> Planet:
        """Get the planetary ruler for a given day."""
        weekday = date.weekday()  # 0 = Monday, 6 = Sunday

        day_rulers = {
            6: Planet.SUN,     # Sunday
            0: Planet.MOON,    # Monday
            1: Planet.MARS,    # Tuesday
            2: Planet.MERCURY, # Wednesday
            3: Planet.JUPITER, # Thursday
            4: Planet.VENUS,   # Friday
            5: Planet.SATURN   # Saturday
        }

        return day_rulers[weekday]

    def _get_planet_index(self, planet: Planet) -> int:
        """Get the index of a planet in the Chaldean order."""
        return CHALDEAN_ORDER.index(planet)

    def _calculate_sunrise_sunset(self, date: datetime.date) -> Tuple[datetime.datetime, datetime.datetime]:
        """Calculate precise sunrise and sunset times using Swiss Ephemeris."""
        if swe is None:
            logger.warning("Swiss Ephemeris not available; using approximate sunrise/sunset")
            return self._approximate_sunrise_sunset(date)

        try:
            jd = swe.julday(date.year, date.month, date.day, 0.0, swe.GREG_CAL)
            geopos = (self.longitude, self.latitude, 0.0)

            rsmi_rise = getattr(swe, 'CALC_RISE') | getattr(swe, 'BIT_DISC_CENTER')
            r1 = swe.rise_trans(jd, getattr(swe, 'SUN'), rsmi_rise, geopos)
            sunrise_jd, rise_status = self._parse_rise_trans_result(r1, "sunrise")
            if rise_status is not None and rise_status < 0:
                raise ValueError("Swiss Ephemeris failed to calculate sunrise")

            rsmi_set = getattr(swe, 'CALC_SET') | getattr(swe, 'BIT_DISC_CENTER')
            r2 = swe.rise_trans(jd, getattr(swe, 'SUN'), rsmi_set, geopos)
            sunset_jd, set_status = self._parse_rise_trans_result(r2, "sunset")
            if set_status is not None and set_status < 0:
                raise ValueError("Swiss Ephemeris failed to calculate sunset")

            sunrise_dt = self._jd_to_datetime(float(sunrise_jd))
            sunset_dt = self._jd_to_datetime(float(sunset_jd))
            if sunset_dt <= sunrise_dt:
                # Swiss Ephemeris returns the local-date events in UTC; for many longitudes
                # the sunset falls on the next UTC date even though it is the same local day.
                sunset_dt = sunset_dt + datetime.timedelta(days=1)
            logger.debug(f"Calculated sunrise: {sunrise_dt}, sunset: {sunset_dt}")
            return sunrise_dt, sunset_dt
        except Exception as e:
            logger.error(f"Error calculating sunrise/sunset: {e}")
            return self._approximate_sunrise_sunset(date)

    def _parse_rise_trans_result(self, result, label: str) -> Tuple[float, Optional[float]]:
        """Normalize PySwissEphemeris rise_trans results across build variants."""
        if not isinstance(result, (list, tuple)) or len(result) < 2:
            raise ValueError(f"Invalid rise_trans return for {label}")

        jd_value: Optional[float] = None
        status_value: Optional[float] = None

        for item in result:
            if isinstance(item, (list, tuple)) and item:
                head = item[0]
                if isinstance(head, (int, float)):
                    jd_value = float(head)
                    break
            elif isinstance(item, (int, float)) and float(item) > 1000000:
                jd_value = float(item)
                break

        for item in result:
            if isinstance(item, (int, float)):
                numeric_item = float(item)
                if jd_value is None or abs(numeric_item - jd_value) > 1e-9:
                    status_value = numeric_item
                    break

        if jd_value is None:
            raise ValueError(f"Invalid rise_trans return for {label}")

        return jd_value, status_value

    def _jd_to_datetime(self, jd: float) -> datetime.datetime:
        """Convert Julian Day to datetime."""
        cal_date = swe.jdut1_to_utc(jd)
        return datetime.datetime(
            cal_date[0], cal_date[1], cal_date[2],
            cal_date[3], cal_date[4], int(cal_date[5]),
            tzinfo=datetime.timezone.utc
        )

    def _approximate_sunrise_sunset(self, date: datetime.date) -> Tuple[datetime.datetime, datetime.datetime]:
        """Fallback method for approximate sunrise/sunset calculation."""
        logger.warning("Using approximate sunrise/sunset calculation")

        # Very basic approximation - 6 AM sunrise, 6 PM sunset
        sunrise = datetime.datetime.combine(date, datetime.time(6, 0), tzinfo=datetime.timezone.utc)
        sunset = datetime.datetime.combine(date, datetime.time(18, 0), tzinfo=datetime.timezone.utc)

        return sunrise, sunset

    def _find_current_hour(self, daily_hours: DailyPlanetaryHours, dt: datetime.datetime) -> PlanetaryHour:
        """Find which planetary hour a given datetime falls in."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        for hour in daily_hours.hours:
            start = hour.start_time
            end = hour.end_time
            # Ensure timezone-aware for safe comparison
            if start.tzinfo is None:
                start = start.replace(tzinfo=datetime.timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=datetime.timezone.utc)
            if start <= dt < end:
                return hour

        # If not found, return the last hour (edge case)
        return daily_hours.hours[-1]

    def get_hours_for_date_range(self, start_date: datetime.date,
                                 days: int = 7) -> List[DailyPlanetaryHours]:
        """Get planetary hours for a range of dates."""
        hours_list = []

        for i in range(days):
            current_date = start_date + datetime.timedelta(days=i)
            daily_hours = self.calculate_daily_hours(current_date)
            hours_list.append(daily_hours)

        return hours_list

    def update_location(self, latitude: float, longitude: float):
        """Update the location for calculations."""
        self.latitude = latitude
        self.longitude = longitude
        logger.info(f"Location updated to lat: {latitude}, lon: {longitude}")
