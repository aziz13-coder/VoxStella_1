import logging
import math
import re
from collections import OrderedDict
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

import datetime
import pytz
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9
    ZoneInfo = None

try:
    from timezonefinder import TimezoneFinder
    TIMEZONEFINDER_AVAILABLE = True
except ImportError:  # pragma: no cover
    TimezoneFinder = None
    TIMEZONEFINDER_AVAILABLE = False

logger = logging.getLogger(__name__)


class LocationError(Exception):
    """Custom exception for geocoding failures."""
    pass


_GEOCODE_CACHE_MAX = 128
_geocode_cache: "OrderedDict[str, Tuple[float, float, str]]" = OrderedDict()
_geocode_lock = RLock()
_OFFLINE_GEOCODE_BY_LOCATION: Dict[str, Tuple[float, float, str]] = {
    "greenwich": (51.4769, -0.0005, "Greenwich, UK"),
    "greenwich uk": (51.4769, -0.0005, "Greenwich, UK"),
    "greenwich, uk": (51.4769, -0.0005, "Greenwich, UK"),
    "tel aviv, israel": (32.0853, 34.7818, "Tel Aviv, Israel"),
    "10050 cielo drive, los angeles, california": (34.0946, -118.4325, "10050 Cielo Drive, Los Angeles, California"),
    "20 east 65th street, manhattan, new york, usa": (40.7662, -73.9697, "20 East 65th Street, Manhattan, New York, USA"),
    "3301 waverly drive, los angeles, california": (34.1086, -118.2798, "3301 Waverly Drive, Los Angeles, California"),
    "420 east 58th street, manhattan, new york, usa": (40.7597, -73.9602, "420 East 58th Street, Manhattan, New York, USA"),
    "7110 n oracle rd, tucson, az, usa": (32.3375, -110.9788, "7110 N Oracle Rd, Tucson, AZ, USA"),
    "964 old topanga canyon road, topanga, california": (34.1069, -118.6015, "964 Old Topanga Canyon Road, Topanga, California"),
    "adil district, baghdad, iraq": (33.3489, 44.3021, "Adil District, Baghdad, Iraq"),
    "al-istiqlal street, al ashar, basra, iraq": (30.5142, 47.8223, "Al-Istiqlal Street, Al Ashar, Basra, Iraq"),
    "al-jadriya, baghdad, iraq": (33.2778, 44.3775, "Al-Jadriya, Baghdad, Iraq"),
    "amityville, new york": (40.67899, -73.41707, "Amityville, New York"),
    "baghdad university, baghdad, iraq": (33.2756, 44.3799, "Baghdad University, Baghdad, Iraq"),
    "baghdad, iraq": (33.31524, 44.36607, "Baghdad, Iraq"),
    "beverly hills, california": (34.07362, -118.40036, "Beverly Hills, California"),
    "boulder, colorado": (40.01499, -105.27055, "Boulder, Colorado"),
    "catalina island, california": (33.38789, -118.41631, "Catalina Island, California"),
    "civitavecchia, italy": (42.09242, 11.79541, "Civitavecchia, Italy"),
    "cleveland, ohio": (41.49932, -81.69436, "Cleveland, Ohio"),
    "delphi, indiana": (40.58754, -86.67501, "Delphi, Indiana"),
    "east 97th street, manhattan, new york, usa": (40.7857, -73.9488, "East 97th Street, Manhattan, New York, USA"),
    "east amwell, new jersey": (40.43094, -74.84239, "East Amwell, New Jersey"),
    "encino, california": (34.15917, -118.50119, "Encino, California"),
    "fall river, massachusetts": (41.70149, -71.15505, "Fall River, Massachusetts"),
    "gaza city, gaza strip": (31.5017, 34.4668, "Gaza City, Gaza Strip"),
    "haiti": (18.5944, -72.3074, "Haiti"),
    "houston, texas": (29.76043, -95.3698, "Houston, Texas"),
    "kew gardens, queens, new york": (40.7057, -73.8272, "Kew Gardens, Queens, New York"),
    "kristianna circle, salt lake city, ut, usa": (40.76078, -111.89105, "Kristianna Circle, Salt Lake City, UT, USA"),
    "long island, new york": (40.78914, -73.13496, "Long Island, New York"),
    "los angeles, california": (34.05223, -118.24368, "Los Angeles, California, USA"),
    "los angeles, california, usa": (34.05223, -118.24368, "Los Angeles, California, USA"),
    "manhattan, new york": (40.7831, -73.9712, "Manhattan, New York, USA"),
    "manhattan, new york, usa": (40.7831, -73.9712, "Manhattan, New York, USA"),
    "maple avenue near east 17th street, austin, tx, usa": (30.2785, -97.7209, "Maple Avenue near East 17th Street, Austin, TX, USA"),
    "memphis, tennessee": (35.14953, -90.04898, "Memphis, Tennessee"),
    "miami beach, florida": (25.79065, -80.13005, "Miami Beach, Florida"),
    "modesto, california": (37.6391, -120.99688, "Modesto, California"),
    "moscow, idaho": (46.73239, -117.00017, "Moscow, Idaho"),
    "nara, japan": (34.68509, 135.80485, "Nara, Japan"),
    "oak beach, ny, usa": (40.64121, -73.29123, "Oak Beach, NY, USA"),
    "ocala, fl, usa": (29.1872, -82.14009, "Ocala, FL, USA"),
    "oregon": (43.80413, -120.5542, "Oregon"),
    "progress drive and alameda drive, strongsville, oh, usa": (41.3145, -81.836, "Progress Drive and Alameda Drive, Strongsville, OH, USA"),
    "ramadi, iraq": (33.42056, 43.30778, "Ramadi, Iraq"),
    "rio de janeiro, brazil": (-22.90685, -43.1729, "Rio de Janeiro, Brazil"),
    "rowlett, texas": (32.9029, -96.56388, "Rowlett, Texas"),
    "sadr city, baghdad, iraq": (33.3833, 44.4667, "Sadr City, Baghdad, Iraq"),
    "scottsdale, arizona": (33.49417, -111.92605, "Scottsdale, Arizona"),
    "soho house, manhattan, new york, usa": (40.7409, -74.0059, "Soho House, Manhattan, New York, USA"),
    "st. peter's square, vatican city": (41.9022, 12.4573, "St. Peter's Square, Vatican City"),
    "studio city, california": (34.14862, -118.39647, "Studio City, California"),
    "sultan palace hotel, basra, iraq": (30.5085, 47.7804, "Sultan Palace Hotel, Basra, Iraq"),
    "union, south carolina": (34.71541, -81.62371, "Union, South Carolina"),
    "wallburg, nc, usa": (35.99986, -80.13977, "Wallburg, NC, USA"),
    "washington hilton hotel, washington, dc, usa": (38.9168, -77.0453, "Washington Hilton Hotel, Washington, DC, USA"),
    "west adams, los angeles, california": (34.0326, -118.3053, "West Adams, Los Angeles, California"),
    "westfield, new jersey": (40.65899, -74.34737, "Westfield, New Jersey"),
}


def _normalize_location(location_string: str) -> str:
    """Normalize location string for stable cache keys."""
    return " ".join(str(location_string).strip().lower().split())


def _looks_like_serialized_object(location_string: str) -> bool:
    normalized = _normalize_location(location_string)
    if not normalized:
        return False
    return normalized == "[object object]" or normalized.startswith("[object object],")


def _parse_coordinate_pair(location_string: str) -> Optional[Tuple[float, float, str]]:
    """Parse explicit 'lat, lon' coordinates without any geocoding service."""
    text = str(location_string or "").strip()
    match = re.fullmatch(
        r"\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*",
        text,
    )
    if not match:
        return None
    lat = float(match.group(1))
    lon = float(match.group(2))
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise LocationError("Coordinate location must be latitude,longitude within valid ranges.")
    return (lat, lon, f"{lat:.6f}, {lon:.6f}")


def _catalog_query_variants(location_string: str) -> List[str]:
    """Build punctuation-safe queries for the bundled GeoNames city catalog."""
    raw = str(location_string or "").strip()
    if not raw:
        return []
    no_punctuation = re.sub(r"[,;|]+", " ", raw)
    first_segment = raw.split(",", 1)[0].strip()
    variants = [
        raw,
        no_punctuation,
        first_segment,
        no_punctuation.replace(" UK", " United Kingdom").replace(" U.K.", " United Kingdom"),
    ]
    out: List[str] = []
    seen = set()
    for variant in variants:
        cleaned = " ".join(str(variant or "").split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _search_offline_city_catalog(location_string: str, limit: int = 1) -> List[Dict[str, Any]]:
    """Search the shipped GeoNames city catalog. This must never hit the network."""
    try:
        from astrocartography_city_catalog import search_city_catalog
    except Exception:
        logger.debug("Bundled city catalog unavailable for offline location lookup", exc_info=True)
        return []

    for query in _catalog_query_variants(location_string):
        try:
            results = search_city_catalog(query=query, limit=limit, resolution="ultra")
        except Exception:
            logger.debug("Offline city catalog query failed for %r", query, exc_info=True)
            results = []
        if results:
            return [item for item in results if isinstance(item, dict)]
    return []


def _catalog_result_to_geocode_tuple(item: Dict[str, Any]) -> Optional[Tuple[float, float, str]]:
    try:
        lat = float(item.get("latitude"))
        lon = float(item.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    label = str(item.get("label") or item.get("query") or item.get("name") or "").strip()
    if not label:
        label = f"{lat:.6f}, {lon:.6f}"
    return (lat, lon, label)


def _nearest_catalog_timezone(lat: float, lon: float) -> Optional[str]:
    """Offline fallback timezone using the nearest shipped city catalog entry."""
    try:
        from astrocartography_city_catalog import list_city_catalog_entries
    except Exception:
        return None
    best_tz: Optional[str] = None
    best_distance = float("inf")
    lat_rad = math.radians(float(lat))
    for item in list_city_catalog_entries():
        try:
            city_lat = float(item.get("latitude"))
            city_lon = float(item.get("longitude"))
        except (TypeError, ValueError):
            continue
        tz = str(item.get("timezone") or "").strip()
        if not tz:
            continue
        # Equirectangular distance is enough to rank nearest catalog entries.
        x = math.radians(city_lon - float(lon)) * math.cos((lat_rad + math.radians(city_lat)) / 2.0)
        y = math.radians(city_lat - float(lat))
        distance = x * x + y * y
        if distance < best_distance:
            best_distance = distance
            best_tz = tz
    return best_tz


def safe_geocode(location_string: str, timeout: int = 10) -> Tuple[float, float, str]:
    """Resolve a location string from shipped offline data only.

    Args:
        location_string: Location to geocode.
        timeout: Ignored. Kept for API compatibility with existing callers.

    Returns:
        Tuple of (latitude, longitude, full_address).

    Raises:
        LocationError: If the location is invalid or unavailable offline.
    """
    if not location_string or not str(location_string).strip():
        raise LocationError("Location not provided.")
    if _looks_like_serialized_object(location_string):
        raise LocationError("Invalid location payload received. Please choose the city again.")

    cache_key = _normalize_location(location_string)

    with _geocode_lock:
        cached = _geocode_cache.get(cache_key)
        if cached is not None:
            _geocode_cache.move_to_end(cache_key)
            return cached
        offline_result = _OFFLINE_GEOCODE_BY_LOCATION.get(cache_key)
        if offline_result is not None:
            _geocode_cache[cache_key] = offline_result
            _geocode_cache.move_to_end(cache_key)
            return offline_result

    coordinate_result = _parse_coordinate_pair(location_string)
    if coordinate_result is not None:
        with _geocode_lock:
            _geocode_cache[cache_key] = coordinate_result
            if len(_geocode_cache) > _GEOCODE_CACHE_MAX:
                _geocode_cache.popitem(last=False)
        return coordinate_result

    for candidate in _search_offline_city_catalog(location_string, limit=5):
        catalog_result = _catalog_result_to_geocode_tuple(candidate)
        if catalog_result is None:
            continue
        with _geocode_lock:
            _geocode_cache[cache_key] = catalog_result
            if len(_geocode_cache) > _GEOCODE_CACHE_MAX:
                _geocode_cache.popitem(last=False)
        return catalog_result

    raise LocationError(
        f"Location not found in the bundled offline location catalog: '{location_string}'. "
        "Use a shipped city/place name or explicit latitude,longitude."
    )


def search_live_location_candidates(location_string: str, limit: int = 6, timeout: int = 12) -> List[Dict[str, Any]]:
    """Return query candidates from the bundled offline city catalog.

    The function name is kept for API compatibility. It must not call the network.
    """
    if not location_string or not str(location_string).strip():
        return []
    if _looks_like_serialized_object(location_string):
        return []

    results = _search_offline_city_catalog(
        location_string,
        limit=max(1, min(int(limit or 6), 10)),
    )
    out: List[Dict[str, Any]] = []
    seen = set()
    for location in results:
        catalog_result = _catalog_result_to_geocode_tuple(location)
        if catalog_result is None:
            continue
        latitude, longitude, display_name = catalog_result
        name = str(location.get("name") or location.get("ascii_name") or display_name).strip()
        country_code = str(location.get("country_code") or "").upper()
        country_name = str(location.get("country_name") or country_code or "Unknown")
        admin1 = str(location.get("admin1_code") or "")
        dedupe_key = (round(float(latitude), 4), round(float(longitude), 4), display_name.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(
            {
                "name": str(name or display_name),
                "ascii_name": str(name or display_name),
                "label": display_name,
                "query": display_name,
                "latitude": round(float(latitude), 6),
                "longitude": round(float(longitude), 6),
                "country_code": country_code,
                "country_name": country_name,
                "admin1_code": admin1,
                "population": int(location.get("population") or 0),
                "timezone": str(location.get("timezone") or ""),
                "feature_code": str(location.get("feature_code") or "CATALOG"),
                "live_source": "offline_city_catalog",
                "raw_type": "",
            }
        )
    return out


class TimezoneManager:
    """Handles timezone operations for horary calculations."""

    def __init__(self) -> None:
        if TIMEZONEFINDER_AVAILABLE:
            try:
                self.tf = TimezoneFinder()
                logger.info("TimezoneFinder initialized successfully")
            except Exception as e:  # pragma: no cover - initialization failure
                logger.error(f"Failed to initialize TimezoneFinder: {e}")
                self.tf = None
        else:  # pragma: no cover - library missing
            logger.warning(
                "TimezoneFinder library not available - using fallback timezone detection only"
            )
            self.tf = None

        self.geolocator = None

    def get_timezone_for_location(self, lat: float, lon: float) -> Optional[str]:
        """Get timezone string for given coordinates with enhanced debugging."""
        logger.info(f"=== TIMEZONE DETECTION STARTED for {lat}, {lon} ===")

        try:
            if self.tf is not None:
                logger.info("Using TimezoneFinder library")
                timezone_result = self.tf.timezone_at(lat=lat, lng=lon)
                logger.info(f"TimezoneFinder raw result: {timezone_result}")

                if timezone_result:
                    logger.info("Validating timezone result...")
                    validated_tz = self._validate_timezone_for_coordinates(
                        timezone_result, lat, lon
                    )
                    if validated_tz:
                        logger.info(
                            f"=== FINAL TIMEZONE: {validated_tz} (after validation) ==="
                        )
                        return validated_tz
            else:
                logger.info(
                    f"TimezoneFinder not available, using fallback for {lat}, {lon}"
                )
                timezone_result = None

            fallback_tz = self._get_fallback_timezone(lat, lon)
            if fallback_tz:
                logger.warning(
                    f"Using fallback timezone {fallback_tz} for {lat}, {lon} (TimezoneFinder returned: {timezone_result})"
                )
                return fallback_tz

            return timezone_result
        except Exception as e:  # pragma: no cover - unexpected errors
            logger.error(f"Error getting timezone for {lat}, {lon}: {e}")
            try:
                fallback_tz = self._get_fallback_timezone(lat, lon)
                if fallback_tz:
                    logger.warning(
                        f"Using fallback timezone {fallback_tz} after TimezoneFinder error"
                    )
                    return fallback_tz
            except Exception:
                pass
            return None

    def _validate_timezone_for_coordinates(
        self, timezone_str: str, lat: float, lon: float
    ) -> Optional[str]:
        """Validate that timezone makes geographic sense for coordinates."""

        logger.info(
            f"TIMEZONE VALIDATION: Checking {timezone_str} for coordinates {lat}, {lon}"
        )

        geographic_validations = {
            (29.5, 33.5, 34.0, 36.0): "Asia/Jerusalem",
        }

        for (lat_min, lat_max, lon_min, lon_max), expected_tz in geographic_validations.items():
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                logger.info(
                    f"COORDINATE MATCH: {lat},{lon} falls in range {lat_min}-{lat_max}, {lon_min}-{lon_max}"
                )
                if timezone_str != expected_tz:
                    logger.warning(
                        f"TIMEZONE OVERRIDE: TimezoneFinder returned {timezone_str} for {lat},{lon} but expected {expected_tz} - CORRECTING"
                    )
                    return expected_tz
                else:
                    logger.info(
                        f"TIMEZONE OK: {timezone_str} is correct for coordinates {lat},{lon}"
                    )
                    return timezone_str

        suspicious_combinations = [
            (29.5, 33.5, 34.0, 36.0, ["America/"])
        ]

        for (
            lat_min,
            lat_max,
            lon_min,
            lon_max,
            forbidden_prefixes,
        ) in suspicious_combinations:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                if any(timezone_str.startswith(prefix) for prefix in forbidden_prefixes):
                    logger.warning(
                        f"TIMEZONE OVERRIDE: Suspicious combination {lat},{lon} with timezone {timezone_str}"
                    )
                    return geographic_validations.get(
                        (29.5, 33.5, 34.0, 36.0), timezone_str
                    )

        return timezone_str

    def _get_fallback_timezone(self, lat: float, lon: float) -> Optional[str]:
        """Offline fallback timezone detection if TimezoneFinder fails."""
        catalog_tz = _nearest_catalog_timezone(lat, lon)
        if catalog_tz:
            logger.info(
                "Using bundled city catalog timezone fallback %s for %s, %s",
                catalog_tz,
                lat,
                lon,
            )
            return catalog_tz

        try:
            if TIMEZONEFINDER_AVAILABLE and self.tf is not None:
                return self.tf.timezone_at(lat=lat, lng=lon)
        except Exception:
            logger.warning("TimezoneFinder fallback failed", exc_info=True)
        return None

    def parse_datetime_with_timezone(
        self,
        date_str: str,
        time_str: str,
        timezone_str: Optional[str] = None,
        lat: float = None,
        lon: float = None,
    ) -> Tuple[datetime.datetime, datetime.datetime, str]:
        """Parse datetime string and return both local and UTC datetime objects."""
        datetime_str = f"{date_str} {time_str}"

        date_formats = [
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%Y/%m/%d %H:%M",
        ]

        dt_naive = None
        format_used = None
        for date_format in date_formats:
            try:
                dt_naive = datetime.datetime.strptime(datetime_str, date_format)
                format_used = date_format
                logger.info(
                    f"Successfully parsed datetime '{datetime_str}' using format '{date_format}'"
                )
                break
            except ValueError:
                continue

        if dt_naive is None:
            raise ValueError(
                f"Unable to parse date '{date_str}'. Please use DD/MM/YYYY format (e.g., 02/03/2004 for March 2, 2004)"
            )

        logger.info(f"Parsed date: {dt_naive} using format: {format_used}")

        if timezone_str:
            try:
                if ZoneInfo:
                    tz = ZoneInfo(timezone_str)
                else:
                    tz = pytz.timezone(timezone_str)
                timezone_used = timezone_str
            except Exception:
                tz = pytz.UTC
                timezone_used = "UTC"
        elif lat is not None and lon is not None:
            tz_str = self.get_timezone_for_location(lat, lon)
            if tz_str:
                try:
                    if ZoneInfo:
                        tz = ZoneInfo(tz_str)
                    else:
                        tz = pytz.timezone(tz_str)
                    timezone_used = tz_str
                except Exception:
                    tz = pytz.UTC
                    timezone_used = "UTC"
            else:
                tz = pytz.UTC
                timezone_used = "UTC"
        else:
            tz = pytz.UTC
            timezone_used = "UTC"

        if ZoneInfo or hasattr(tz, "localize"):
            if hasattr(tz, "localize"):
                try:
                    dt_local = tz.localize(dt_naive)
                except pytz.AmbiguousTimeError:
                    dt_local = tz.localize(dt_naive, is_dst=False)
                    logger.warning(
                        f"Ambiguous time {dt_naive} - using standard time"
                    )
                except pytz.NonExistentTimeError:
                    dt_adjusted = dt_naive + datetime.timedelta(hours=1)
                    dt_local = tz.localize(dt_adjusted)
                    logger.warning(
                        f"Non-existent time {dt_naive} - using {dt_adjusted}"
                    )
            else:
                dt_local = dt_naive.replace(tzinfo=tz)
        else:
            dt_local = dt_naive.replace(tzinfo=tz)

        dt_utc = dt_local.astimezone(pytz.UTC)
        return dt_local, dt_utc, timezone_used

    def get_current_time_for_location(
        self, lat: float, lon: float
    ) -> Tuple[datetime.datetime, datetime.datetime, str]:
        """Get current time for a specific location."""
        tz_str = self.get_timezone_for_location(lat, lon)

        if tz_str:
            try:
                if ZoneInfo:
                    tz = ZoneInfo(tz_str)
                else:
                    tz = pytz.timezone(tz_str)
                timezone_used = tz_str
            except Exception:
                tz = pytz.UTC
                timezone_used = "UTC"
        else:
            tz = pytz.UTC
            timezone_used = "UTC"

        utc_now = datetime.datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(tz)

        return local_now, utc_now, timezone_used
