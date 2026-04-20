# -*- coding: utf-8 -*-
"""
Astro Clock Engine - Real-time Astrological Information Calculator

Provides live astrological data including:
- Current chart generation
- Moon state (VOC, position)
- Planetary positions and dignities
- Solar conditions
- Rulers and dispositors
- Real-time aspects

Integrated with existing horary engine and geolocation services.

Created for Astro Clock feature
@author: sabaa
"""

import datetime
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, replace
from enum import Enum
from zoneinfo import ZoneInfo

# Import existing infrastructure
from horary_engine.engine import HoraryEngine
from models import Planet, Sign, PlanetPosition, HoraryChart, Aspect, SolarCondition
from horary_engine.services.geolocation import TimezoneManager, LocationError, safe_geocode

logger = logging.getLogger(__name__)

_DEFAULT_GREENWICH_COORDS = (51.4769, -0.0005)


@dataclass
class DispositorChain:
    """Represents a planet's dispositor chain."""
    planet: Planet
    dispositor: Planet
    chain: List[Planet]
    final_dispositor: Planet
    mutual_reception: bool = False
    reception_partner: Optional[Planet] = None


@dataclass
class MoonState:
    """Current state of the Moon."""
    position: PlanetPosition
    void_of_course: bool
    last_aspect: Optional[Any] = None
    next_aspect: Optional[Any] = None
    void_duration: Optional[float] = None  # hours until next aspect


class ClockMode(Enum):
    """Astro Clock operation modes."""
    REALTIME = "realtime"  # Continuously updates with current time
    MANUAL = "manual"      # User-specified time and location
    PAUSED = "paused"      # Frozen at specific moment


@dataclass
class AstroClockSettings:
    """Settings for astro clock operation."""
    mode: ClockMode = ClockMode.REALTIME
    location: Optional[str] = None
    custom_time: Optional[datetime.datetime] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    paused_at: Optional[datetime.datetime] = None
    # Optional house system override for Astro Clock (Swiss code: R, P, W, E, etc.)
    house_system_code: Optional[str] = None


@dataclass
class RealTimeData:
    """Complete real-time astrological data."""
    timestamp: datetime.datetime
    settings: AstroClockSettings
    chart_result: Dict[str, Any]  # Full horary engine result
    moon_state: MoonState
    dispositor_chains: Dict[Planet, DispositorChain]
    current_aspects: List[Dict[str, Any]]
    planetary_hours: Optional[Dict[str, Any]] = None


class AstroClockEngine:
    """Main engine for real-time astrological calculations."""

    def __init__(self):
        """Initialize with default settings."""
        self.horary_engine = HoraryEngine()
        self.timezone_manager = TimezoneManager()
        self.settings = AstroClockSettings()
        self._location_cache = {}  # Cache resolved locations
        self._lock = threading.RLock()
        logger.info("AstroClockEngine initialized")

    def get_current_data(self, settings: Optional[AstroClockSettings] = None) -> RealTimeData:
        """
        Get complete real-time astrological data based on current settings.

        Args:
            settings: Optional settings override, uses instance settings if None

        Returns:
            RealTimeData object with all current astrological information
        """
        with self._lock:
            prev_settings = None
            if settings is not None:
                prev_settings = self.settings
                try:
                    self.settings = replace(settings)
                except Exception:
                    self.settings = settings
            try:
                return self._build_real_time_payload()
            finally:
                if prev_settings is not None:
                    self.settings = prev_settings

    def _build_real_time_payload(self) -> RealTimeData:
        """Compute RealTimeData snapshot. Caller must hold self._lock."""
        # Determine effective datetime based on mode
        effective_time = self._get_effective_time()

        logger.info(f"Calculating astro clock data - Mode: {self.settings.mode.value}, Time: {effective_time}")

        # Generate chart using existing horary infrastructure
        chart_result = self._generate_chart_with_horary_engine(effective_time)

        # Extract chart data from result
        chart_data = chart_result.get('chart_data', {})
        planet_positions = self._extract_planet_positions(chart_data)

        # Calculate derived data
        moon_state = self._calculate_moon_state(chart_data, planet_positions, chart_result)
        dispositor_chains = self._calculate_dispositor_chains(planet_positions)
        current_aspects = self._extract_aspects_from_result(chart_result)

        return RealTimeData(
            timestamp=effective_time,
            settings=self.settings,
            chart_result=chart_result,
            moon_state=moon_state,
            dispositor_chains=dispositor_chains,
            current_aspects=current_aspects
        )

    def _get_effective_time(self) -> datetime.datetime:
        """Get the effective time based on current mode."""
        if self.settings.mode == ClockMode.REALTIME:
            return datetime.datetime.now(datetime.timezone.utc)
        elif self.settings.mode == ClockMode.MANUAL and self.settings.custom_time:
            return self.settings.custom_time
        elif self.settings.mode == ClockMode.PAUSED and self.settings.paused_at:
            return self.settings.paused_at
        else:
            # Fallback to current time
            return datetime.datetime.now(datetime.timezone.utc)

    def get_effective_datetime(self) -> datetime.datetime:
        """Public accessor for the engine's effective timestamp."""
        return self._get_effective_time()

    def _generate_chart_with_horary_engine(self, dt: datetime.datetime) -> Dict[str, Any]:
        """Generate chart using the existing horary engine infrastructure."""
        try:
            # Prepare settings for horary engine
            location_str = self.settings.location or "Greenwich, UK"
            coords: Optional[Tuple[float, float]] = None
            if self.settings.latitude is not None and self.settings.longitude is not None:
                try:
                    coords = (float(self.settings.latitude), float(self.settings.longitude))
                except Exception:
                    coords = None
            if coords is None:
                normalized_location = " ".join(str(location_str or "").strip().lower().split())
                if normalized_location in {"", "greenwich", "greenwich uk", "greenwich, uk"}:
                    coords = _DEFAULT_GREENWICH_COORDS

            # Default: realtime
            use_current_time = True
            date_str = None
            time_str = None
            timezone_str = self.settings.timezone

            def _is_placeholder_tz(tz_name: Optional[str]) -> bool:
                if not tz_name:
                    return True
                s = str(tz_name).strip()
                return s in {"UTC", "Etc/UTC", "Etc/GMT", "GMT"}

            if _is_placeholder_tz(timezone_str) and location_str:
                try:
                    if coords is None:
                        lat, lon, _ = safe_geocode(location_str)
                        coords = (float(lat), float(lon))
                    guess = self.timezone_manager.get_timezone_for_location(coords[0], coords[1])
                    if guess:
                        timezone_str = guess
                except Exception:
                    pass

            # For non-realtime modes, pass the effective timestamp explicitly.
            # This keeps PAUSED snapshots stable and MANUAL mode deterministic.
            if self.settings.mode != ClockMode.REALTIME:
                ct = dt
                if not isinstance(ct, datetime.datetime):
                    ct = datetime.datetime.now(datetime.timezone.utc)
                if ct.tzinfo is None:
                    if timezone_str and (not _is_placeholder_tz(timezone_str)):
                        try:
                            ct = ct.replace(tzinfo=ZoneInfo(timezone_str))
                        except Exception:
                            ct = ct.replace(tzinfo=datetime.timezone.utc)
                    else:
                        ct = ct.replace(tzinfo=datetime.timezone.utc)
                if timezone_str and (not _is_placeholder_tz(timezone_str)):
                    try:
                        ct = ct.astimezone(ZoneInfo(timezone_str))
                    except Exception:
                        timezone_str = "UTC"
                        ct = ct.astimezone(datetime.timezone.utc)
                else:
                    timezone_str = "UTC"
                    ct = ct.astimezone(datetime.timezone.utc)
                use_current_time = False
                # Avoid strftime for pre-1900 years (Python limitation)
                try:
                    if ct.year >= 1900:
                        date_str = ct.strftime("%Y-%m-%d")
                        time_str = ct.strftime("%H:%M")
                    else:
                        date_str = f"{ct.year:04d}-{ct.month:02d}-{ct.day:02d}"
                        time_str = f"{ct.hour:02d}:{ct.minute:02d}"
                except Exception:
                    # Fallback to manual formatting in any unexpected error
                    date_str = f"{ct.year:04d}-{ct.month:02d}-{ct.day:02d}"
                    time_str = f"{ct.hour:02d}:{ct.minute:02d}"

            horary_settings = {
                "location": location_str,
                "use_current_time": use_current_time,
                "date": date_str,
                "time": time_str,
                "timezone": timezone_str,
                "latitude": coords[0] if coords else None,
                "longitude": coords[1] if coords else None,
                "location_name": location_str,
                "manual_houses": None,
                # Optional house system override
                "house_system_code": self.settings.house_system_code,
                # Astro Clock stays in-process, so keep the live chart object
                # available for internal consumers that can avoid re-deserializing.
                "include_internal_chart": True,
                # Enhanced features disabled for clean calculation
                "ignore_radicality": True,
                "ignore_void_moon": True,
                "ignore_combustion": True,
                "ignore_saturn_7th": True,
                "exaltation_confidence_boost": 0.0
            }

            # Use horary engine exactly like app.py does
            question = "Astro Clock Real-time Chart"  # Required but not used for calculations
            result = self.horary_engine.judge(question, horary_settings)
            # Normalize to dict if engine returned a JSON string
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    logger.error("AstroClockEngine: failed to parse JSON result from horary engine")
                    raise
            # Normalize nested chart_data if it is a JSON string
            try:
                chart_data_obj = result.get('chart_data')
                if isinstance(chart_data_obj, str):
                    result['chart_data'] = json.loads(chart_data_obj)
            except Exception:
                logger.warning("AstroClockEngine: chart_data was a JSON string but failed to parse; using raw")

            logger.info("Successfully generated chart via horary engine (%s)",
                        "manual" if not use_current_time else "realtime")
            return result

        except Exception as e:
            logger.error(f"Error generating chart with horary engine: {e}")
            raise

    def _extract_planet_positions(self, chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract planet positions from horary engine result."""
        planets = chart_data.get('planets', [])
        # Normalize planets to a list of dicts (engine may return dict keyed by planet name)
        if isinstance(planets, dict):
            normalized: List[Dict[str, Any]] = []
            for name, info in planets.items():
                if isinstance(info, dict):
                    p = dict(info)
                    p.setdefault('planet', name)
                    normalized.append(p)
            return normalized
        if isinstance(planets, list):
            return [p for p in planets if isinstance(p, dict)]
        return []

    def _calculate_moon_state(
        self,
        chart_data: Dict[str, Any],
        planet_positions: List[Dict[str, Any]],
        chart_result: Optional[Dict[str, Any]] = None,
    ) -> MoonState:
        """Calculate current Moon state including VOC status and nearby lunar aspect info."""

        def _normalize_moon_aspect(payload: Any) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            return {
                "planet": payload.get("planet"),
                "aspect": payload.get("aspect"),
                "perfection_eta_days": payload.get("perfection_eta_days"),
                "perfection_eta_description": payload.get("perfection_eta_description"),
                "applying": payload.get("applying"),
                "orb": payload.get("orb"),
                "degrees_difference": payload.get("degrees_difference"),
            }

        moon_data = None
        for planet in planet_positions:
            if str(planet.get('planet') or '').strip().lower() == 'moon':
                moon_data = planet
                break
        if not moon_data and isinstance(chart_result, dict):
            for payload in (chart_result.get('chart_data'), chart_result):
                if not isinstance(payload, dict):
                    continue
                for planet in self._extract_planet_positions(payload):
                    if str(planet.get('planet') or '').strip().lower() == 'moon':
                        moon_data = planet
                        break
                if moon_data:
                    break

        considerations = chart_data.get('considerations', {}) if isinstance(chart_data, dict) else {}
        if (not isinstance(considerations, dict) or not considerations) and isinstance(chart_result, dict):
            considerations = chart_result.get("considerations", {})
        void_of_course = bool((considerations or {}).get('moon_void', False))

        last_aspect_payload = None
        next_aspect_payload = None
        if isinstance(chart_data, dict):
            last_aspect_payload = _normalize_moon_aspect(chart_data.get("moon_last_aspect"))
            next_aspect_payload = _normalize_moon_aspect(chart_data.get("moon_next_aspect"))
        if isinstance(chart_result, dict):
            if not last_aspect_payload:
                last_aspect_payload = _normalize_moon_aspect(chart_result.get("moon_last_aspect"))
            if not next_aspect_payload:
                next_aspect_payload = _normalize_moon_aspect(chart_result.get("moon_next_aspect"))

        if not moon_data:
            logger.warning("Moon position not found in chart; returning fallback moon state")
            from types import SimpleNamespace
            fallback = SimpleNamespace()
            fallback.longitude = 0.0
            fallback.sign = SimpleNamespace()
            fallback.sign.sign_name = 'Aries'
            fallback.house = 1
            return MoonState(
                position=fallback,
                void_of_course=void_of_course,
                last_aspect=last_aspect_payload,
                next_aspect=next_aspect_payload,
                void_duration=None,
            )

        # Extract Moon information
        try:
            moon_longitude = float(moon_data.get('longitude', 0.0))
        except Exception:
            moon_longitude = 0.0
        moon_sign = moon_data.get('sign', 'Unknown')
        moon_house = moon_data.get('house', 1)

        # Create a minimal position object for MoonState
        from types import SimpleNamespace
        position = SimpleNamespace()
        position.longitude = moon_longitude
        position.sign = SimpleNamespace()
        position.sign.sign_name = moon_sign
        position.house = moon_house

        return MoonState(
            position=position,
            void_of_course=void_of_course,
            last_aspect=last_aspect_payload,
            next_aspect=next_aspect_payload,
            void_duration=None
        )


    def _calculate_dispositor_chains(self, planet_positions: List[Dict[str, Any]]) -> Dict[str, DispositorChain]:
        """Calculate dispositor chains for all planets."""
        dispositor_chains = {}

        # Map sign names to their traditional rulers
        sign_rulers = {
            'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury',
            'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury',
            'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter',
            'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'
        }

        # Create planet position lookup
        planet_signs = {}
        for planet_data in planet_positions:
            planet_name = planet_data.get('planet')
            planet_sign = planet_data.get('sign')
            if planet_name and planet_sign and planet_name not in ['Ascendant', 'Midheaven']:
                planet_signs[planet_name] = planet_sign

        # Build dispositor chains
        for planet_name, planet_sign in planet_signs.items():
            if planet_sign in sign_rulers:
                chain = self._build_dispositor_chain_from_data(planet_name, planet_sign, sign_rulers, planet_signs)
                dispositor_chains[planet_name] = chain

        return dispositor_chains

    def _build_dispositor_chain_from_data(self, planet_name: str, planet_sign: str,
                                         sign_rulers: Dict[str, str], planet_signs: Dict[str, str]) -> DispositorChain:
        """Build the dispositor chain for a given planet using data dictionaries."""
        chain = [planet_name]
        current_sign = planet_sign
        # Track results explicitly
        final_dispositor: Optional[str] = None
        mutual_reception: bool = False
        reception_partner: Optional[str] = None

        # Follow the chain until we find a final dispositor or mutual reception
        hops = 0
        while True:
            ruler = sign_rulers.get(current_sign)
            if not ruler:
                # No known ruler for this sign; stop without changing defaults
                break

            if ruler in chain:
                # Loop detected — check strict mutual reception (two-step loop back to anchor)
                if len(chain) == 2 and ruler == planet_name:
                    mutual_reception = True
                    # Partner is the first ruler encountered
                    reception_partner = chain[1]
                    # In mutual reception, treat dispositor as the partner
                    final_dispositor = reception_partner
                else:
                    final_dispositor = ruler
                break

            chain.append(ruler)

            # Determine the sign the current ruler is placed in
            ruler_sign = planet_signs.get(ruler)
            if ruler_sign is None:
                # Cannot continue chain; treat current ruler as final
                final_dispositor = ruler
                break

            current_sign = ruler_sign
            hops += 1
            # Safety to avoid pathological loops
            if hops > 10:
                final_dispositor = ruler
                break

        # Create minimal DispositorChain with string data
        from types import SimpleNamespace
        chain_obj = SimpleNamespace()
        chain_obj.planet = planet_name
        chain_obj.dispositor = sign_rulers.get(planet_sign, planet_name)
        chain_obj.chain = chain
        chain_obj.final_dispositor = final_dispositor or (chain[-1] if chain else planet_name)
        chain_obj.mutual_reception = bool(mutual_reception)
        chain_obj.reception_partner = reception_partner

        return chain_obj







    def _extract_aspects_from_result(self, chart_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract current aspects from horary engine result.

        Prefer top-level `aspects` if present; otherwise fall back to
        `chart_data['aspects']` (handling possible stringified chart_data).
        """
        try:
            aspects = chart_result.get('aspects')
            if not aspects:
                chart_data = chart_result.get('chart_data', {})
                if isinstance(chart_data, str):
                    try:
                        chart_data = json.loads(chart_data)
                    except Exception:
                        chart_data = {}
                if isinstance(chart_data, dict):
                    aspects = chart_data.get('aspects', [])
            # Ensure list output
            return aspects if isinstance(aspects, list) else []
        except Exception:
            return []

    def update_settings(self, **kwargs):
        """Update astro clock settings."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                    logger.info(f"Updated setting {key} to {value}")

    def set_mode(self, mode: ClockMode, **kwargs):
        """Set the clock mode and related parameters."""
        with self._lock:
            def _same_location(a: Optional[str], b: Optional[str]) -> bool:
                return " ".join(str(a or "").strip().lower().split()) == " ".join(str(b or "").strip().lower().split())

            self.settings.mode = mode

            if mode == ClockMode.MANUAL:
                location_changed = False
                if 'location' in kwargs:
                    location_changed = not _same_location(self.settings.location, kwargs['location'])
                    self.settings.location = kwargs['location']
                if 'custom_time' in kwargs:
                    custom_time = kwargs['custom_time']
                    if isinstance(custom_time, datetime.datetime) and custom_time.tzinfo is None:
                        custom_time = custom_time.replace(tzinfo=datetime.timezone.utc)
                    self.settings.custom_time = custom_time
                if 'timezone' in kwargs:
                    self.settings.timezone = kwargs['timezone']
                if 'latitude' in kwargs and 'longitude' in kwargs:
                    self.settings.latitude = kwargs['latitude']
                    self.settings.longitude = kwargs['longitude']
                elif location_changed:
                    self.settings.latitude = None
                    self.settings.longitude = None
                # Leaving paused state
                self.settings.paused_at = None

            elif mode == ClockMode.PAUSED:
                paused_at = kwargs.get('paused_at', datetime.datetime.now(datetime.timezone.utc))
                if isinstance(paused_at, datetime.datetime) and paused_at.tzinfo is None:
                    paused_at = paused_at.replace(tzinfo=datetime.timezone.utc)
                self.settings.paused_at = paused_at

            elif mode == ClockMode.REALTIME:
                location_changed = False
                if 'location' in kwargs:
                    location_changed = not _same_location(self.settings.location, kwargs['location'])
                    self.settings.location = kwargs['location']
                if 'timezone' in kwargs:
                    self.settings.timezone = kwargs['timezone']
                if 'latitude' in kwargs and 'longitude' in kwargs:
                    self.settings.latitude = kwargs['latitude']
                    self.settings.longitude = kwargs['longitude']
                elif location_changed:
                    self.settings.latitude = None
                    self.settings.longitude = None
                # Reset manual overrides when resuming realtime
                self.settings.custom_time = None
                self.settings.paused_at = None

            logger.info(f"Clock mode set to {mode.value}")

    def pause_at_current_time(self):
        """Pause the clock at the current moment."""
        with self._lock:
            self.settings.mode = ClockMode.PAUSED
            self.settings.paused_at = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"Clock paused at {self.settings.paused_at}")

    def resume_realtime(self):
        """Resume real-time mode."""
        with self._lock:
            self.settings.mode = ClockMode.REALTIME
            self.settings.paused_at = None
            self.settings.custom_time = None
            logger.info("Clock resumed to real-time mode")
