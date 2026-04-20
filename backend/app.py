# -*- coding: utf-8 -*-

"""

Enhanced Traditional Horary Astrology Flask API with All New Features

UPDATED to use Enhanced Engine with Solar Conditions and New Features



Created on Wed May 28 11:10:58 2025

Updated with enhanced engine and all new capabilities



@author: sabaa (enhanced)

"""



from flask import Flask, request, jsonify, g

from flask_cors import CORS

import json

import traceback

import time

import logging
import math
import secrets

import sys

import os

from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse

from functools import wraps

from collections import defaultdict, OrderedDict
from threading import RLock
from uuid import uuid4

from runtime_import_paths import extend_backend_runtime_import_paths

_runtime_import_paths = extend_backend_runtime_import_paths()


# UPDATED IMPORT: Use the new enhanced engine

from horary_engine.engine import HoraryEngine, serialize_planet_with_solar
from horary_engine.serialization import (
    serialize_lunar_aspect,
    deserialize_chart_for_evaluation,
)
from horary_engine.services.geolocation import LocationError
from evaluate_chart import evaluate_chart
from horary_engine.utils import token_to_string
from process_watchdog import start_parent_watchdog
from licensing import (
    LicenseConfigError,
    LicenseError,
    extract_bearer_token,
    should_bypass_license,
    verify_license_token,
)
from build_metadata import load_build_metadata



# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Ensure standard streams can handle Unicode output (e.g., on Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Determine log directory (priority: HORARY_LOG_DIR -> executable dir -> LOCALAPPDATA/TEMP)
def _default_log_dir():
    try:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()

log_dir = os.getenv("HORARY_LOG_DIR") or _default_log_dir()
try:
    os.makedirs(log_dir, exist_ok=True)
except Exception:
    # Fall back to a writable user location
    alt_root = os.getenv('LOCALAPPDATA') or os.getenv('TEMP') or os.getcwd()
    log_dir = os.path.join(alt_root, 'VoxStella', 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = os.getcwd()

# Packaged builds ship a bundled backend executable, so writing a log file on
# end-user machines can quickly bloat storage.  We therefore disable file logs
# by default when `sys.frozen` is set (PyInstaller) while still letting power
# users opt back in via HORARY_ENABLE_FILE_LOGS.
def _should_enable_file_logging() -> bool:
    env_flag = os.getenv("HORARY_ENABLE_FILE_LOGS")
    if env_flag is not None:
        return env_flag.lower() in {"1", "true", "yes"}
    return not getattr(sys, "frozen", False)


handlers = [logging.StreamHandler(sys.stdout)]
if _should_enable_file_logging():
    try:
        file_path = os.path.join(log_dir, "horary_api.log")
        handlers.insert(0, logging.FileHandler(file_path, encoding="utf-8"))
    except Exception as e:
        # Fall back to stdout-only if file handler fails (e.g., permission denied)
        print(f"[logging] FileHandler disabled: {e}")
else:
    print("[logging] File logging disabled (HORARY_ENABLE_FILE_LOGS not set)")

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Directory: {log_dir}")
if _runtime_import_paths:
    logger.info("Extended backend import paths: %s", _runtime_import_paths)

# Suppress noisy third-party logging
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)
logging.getLogger('geopy.geocoders').setLevel(logging.ERROR)



logger = logging.getLogger(__name__)
APP_VERSION = os.getenv("VOX_STELLA_APP_VERSION", "2.1.4")
API_VERSION = os.getenv("VOX_STELLA_API_VERSION", "2.0.0")
ENGINE_VERSION = os.getenv("VOX_STELLA_ENGINE_VERSION", "Enhanced Traditional Horary 2.0")
RELEASE_DATE = os.getenv("VOX_STELLA_RELEASE_DATE", "2026-04-16")
BACKEND_BUILD_METADATA = load_build_metadata(os.getenv("HORARY_BACKEND_DIR"))


def _chart_request_log_summary(
    *,
    question: str | None = None,
    location: str | None = None,
    date_str: str | None = None,
    time_str: str | None = None,
    timezone_str: str | None = None,
    use_current_time: bool = True,
    manual_houses: str | None = None,
    use_reasoning_v1: bool = False,
) -> dict:
    return {
        "question_chars": len((question or "").strip()),
        "location_chars": len((location or "").strip()),
        "custom_date_supplied": bool(date_str),
        "custom_time_supplied": bool(time_str),
        "timezone_supplied": bool(timezone_str),
        "use_current_time": bool(use_current_time),
        "manual_houses": bool((manual_houses or "").strip()),
        "use_reasoning_v1": bool(use_reasoning_v1),
    }


def _optional_finite_float(value, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be a finite number")
    return parsed


def make_reason(rule: str, stage: str = "error", weight: float = 0) -> dict:
    """Helper to build structured reasoning entries for error responses."""
    return {"stage": stage, "rule": rule, "weight": weight}




app = Flask(__name__)

def _cors_origins():
    raw = (os.getenv("HORARY_CORS_ORIGINS") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    # Electron packaged renderer usually has `Origin: null`; dev uses Vite localhost.
    return [
        "null",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


CORS(
    app,
    resources={r"/api/*": {"origins": _cors_origins()}},
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-License-Token"],
)

PROTECTED_ENDPOINT_PREFIXES = (
    "/api/calculate-chart",
    "/api/moon-debug",
    "/api/metrics",
)
LICENSE_EXEMPT_PATHS = {
    "/api/health",
    "/api/version",
    "/api/get-timezone",
    "/api/current-time",
}
ASTRO_CLOCK_PUBLIC_PREFIXES = (
    "/api/astro-clock/current",
    "/api/astro-clock/dashboard",
    "/api/astro-clock/planetary-hours",
    "/api/astro-clock/receptions",
    "/api/astro-clock/compass",
)
STREAM_TICKET_ALLOWED_PREFIXES = (
    "/api/astro-clock/stream",
    "/api/astro-clock/transits/window/stream",
    "/api/astro-clock/election/suggest/stream",
)
_STREAM_TICKET_TTL_SECONDS = max(15, int(os.getenv("STREAM_TICKET_TTL_SECONDS", "90")))
_STREAM_TICKET_MAX_ACTIVE = max(32, int(os.getenv("STREAM_TICKET_MAX_ACTIVE", "2048")))
_stream_ticket_cache = OrderedDict()
_stream_ticket_lock = RLock()
_HEALTH_VERBOSE_ERRORS = str(os.getenv("HORARY_HEALTH_VERBOSE_ERRORS", "")).strip().lower() in {
    "1",
    "true",
    "yes",
}


def _health_error_detail(exc: Exception) -> str:
    if _HEALTH_VERBOSE_ERRORS:
        return str(exc)
    return type(exc).__name__


def _canonicalize_stream_query_items(items) -> list[tuple[str, str]]:
    canonical: list[tuple[str, str]] = []
    for key, value in items:
        key_text = str(key or "")
        if key_text == "stream_ticket":
            continue
        canonical.append((key_text, "" if value is None else str(value)))
    canonical.sort(key=lambda item: (item[0], item[1]))
    return canonical


def _build_stream_target(path: str, items, *, validate_path: bool) -> str:
    path_text = str(path or "").strip()
    if validate_path:
        if not path_text.startswith("/api/astro-clock/"):
            raise ValueError("invalid stream path")
        if not any(path_text.startswith(prefix) for prefix in STREAM_TICKET_ALLOWED_PREFIXES):
            raise ValueError("unsupported stream path")
    canonical_items = _canonicalize_stream_query_items(items)
    query = urlencode(canonical_items, doseq=True)
    return f"{path_text}?{query}" if query else path_text


def _normalize_stream_target(path_with_query: str) -> str:
    parsed = urlparse(str(path_with_query or "").strip())
    if parsed.scheme or parsed.netloc:
        raise ValueError("path must be relative")
    path = parsed.path or ""
    items = parse_qsl(parsed.query, keep_blank_values=True)
    return _build_stream_target(path, items, validate_path=True)


def _current_stream_target() -> str:
    items = []
    try:
        for key in request.args.keys():
            if key == "stream_ticket":
                continue
            values = request.args.getlist(key)
            if not values:
                items.append((key, ""))
            else:
                for value in values:
                    items.append((key, str(value)))
    except Exception:
        items = []
    path = request.path or ""
    return _build_stream_target(path, items, validate_path=False)


def _prune_stream_tickets(now_ts: float) -> None:
    expired_keys = []
    for tk, entry in _stream_ticket_cache.items():
        if float(entry.get("exp", 0.0)) <= now_ts:
            expired_keys.append(tk)
    for tk in expired_keys:
        _stream_ticket_cache.pop(tk, None)


def _mint_stream_ticket(claims: dict, stream_target: str) -> str:
    now_ts = time.time()
    ticket = secrets.token_urlsafe(32)
    with _stream_ticket_lock:
        _prune_stream_tickets(now_ts)
        _stream_ticket_cache[ticket] = {
            "claims": claims,
            "target": stream_target,
            "exp": now_ts + _STREAM_TICKET_TTL_SECONDS,
        }
        _stream_ticket_cache.move_to_end(ticket)
        while len(_stream_ticket_cache) > _STREAM_TICKET_MAX_ACTIVE:
            _stream_ticket_cache.popitem(last=False)
    return ticket


def _consume_stream_ticket(ticket: str, stream_target: str) -> dict | None:
    now_ts = time.time()
    with _stream_ticket_lock:
        _prune_stream_tickets(now_ts)
        entry = _stream_ticket_cache.pop(ticket, None)
    if not entry:
        return None
    if float(entry.get("exp", 0.0)) <= now_ts:
        return None
    if entry.get("target") != stream_target:
        return None
    claims = entry.get("claims")
    if not isinstance(claims, dict):
        return None
    return claims


@app.before_request
def enforce_license_guard():
    """Require a valid license token for protected endpoints."""
    if should_bypass_license():
        return None

    # Let Flask/CORS answer preflight requests before any license validation.
    # The actual follow-up request still goes through the normal guard.
    if request.method == "OPTIONS":
        return None

    path = request.path or ""
    if path in LICENSE_EXEMPT_PATHS:
        return None
    if any(path.startswith(prefix) for prefix in ASTRO_CLOCK_PUBLIC_PREFIXES):
        return None

    needs_license = any(path.startswith(prefix) for prefix in PROTECTED_ENDPOINT_PREFIXES)
    if path.startswith("/api/astro-clock"):
        needs_license = True
    if not needs_license:
        return None

    stream_ticket = request.args.get("stream_ticket")
    if stream_ticket:
        stream_claims = _consume_stream_ticket(stream_ticket, _current_stream_target())
        if stream_claims:
            g.license_claims = stream_claims
            return None

    token = extract_bearer_token(request.headers) or request.headers.get("X-License-Token")
    if not token:
        return (
            jsonify(
                {
                    "error": "license_required",
                    "detail": "License token missing. Please activate Vox Stella before continuing.",
                }
            ),
            402,
        )

    try:
        claims = verify_license_token(token)
        g.license_claims = claims
    except LicenseConfigError as exc:
        logger.error(f"License configuration error: {exc}")
        return (
            jsonify(
                {
                    "error": "license_config_error",
                    "detail": "License system is not configured. Contact support.",
                }
            ),
            500,
        )
    except LicenseError as exc:
        logger.warning(f"License validation failed: {exc}")
        return (
            jsonify(
                {
                    "error": "license_invalid",
                    "detail": str(exc),
                }
            ),
            403,
        )

    return None


@app.route("/api/astro-clock/stream-ticket", methods=["POST"])
def issue_stream_ticket():
    claims = getattr(g, "license_claims", None)
    if not isinstance(claims, dict):
        return jsonify({"error": "license_required"}), 402
    payload = request.get_json(silent=True) or {}
    raw_path = payload.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return jsonify({"error": "path is required"}), 400
    try:
        canonical_target = _normalize_stream_target(raw_path)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    ticket = _mint_stream_ticket(claims, canonical_target)
    return jsonify({"ticket": ticket, "expires_in": _STREAM_TICKET_TTL_SECONDS})



# UPDATED: Initialize the enhanced horary engine

horary_engine = HoraryEngine()

# ASTRO CLOCK: Initialize Astro Clock API (robust import)
def _register_astro_clock_blueprint():
    try:
        from astro_clock_api import astro_clock_bp as _bp  # type: ignore
        app.register_blueprint(_bp)
        logger.info("Astro Clock API registered (local)")
        return True
    except Exception as exc:
        logger.error(f"Failed to register Astro Clock API from backend source: {exc}")
        return False

_register_astro_clock_blueprint()



def make_json_safe(obj):
    """Recursively convert objects to JSON-safe format, handling Planet enums and other non-serializable types."""
    from enum import Enum
    
    # Handle primitive types first (most common case)
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(item) for item in obj]
    elif isinstance(obj, Enum):
        # Handle enum objects (like Planet) by using their value
        return obj.value if hasattr(obj, 'value') else str(obj)
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, bytes)):
        # Handle custom objects with attributes, but avoid string-like objects
        try:
            return {k: make_json_safe(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
        except:
            return str(obj)
    else:
        # Fallback to string representation for unknown types
        return str(obj)

# Simple metrics collection

class SimpleMetrics:

    def __init__(self):

        self.request_count = defaultdict(int)

        self.error_count = defaultdict(int)

        self.response_times = defaultdict(list)

    

    def record_request(self, endpoint):

        self.request_count[endpoint] += 1

    

    def record_error(self, endpoint, error_type):

        self.error_count[f"{endpoint}_{error_type}"] += 1

    

    def record_response_time(self, endpoint, duration):

        self.response_times[endpoint].append(duration)

        # Keep only last 100 response times per endpoint

        if len(self.response_times[endpoint]) > 100:

            self.response_times[endpoint] = self.response_times[endpoint][-100:]

    

    def get_stats(self):

        stats = {

            'requests': dict(self.request_count),

            'errors': dict(self.error_count),

            'avg_response_times': {}

        }

        

        for endpoint, times in self.response_times.items():

            if times:

                stats['avg_response_times'][endpoint] = sum(times) / len(times)

        

        return stats



metrics = SimpleMetrics()



def timing_decorator(endpoint_name):

    """Decorator to time API endpoints"""

    def decorator(func):

        @wraps(func)

        def wrapper(*args, **kwargs):

            metrics.record_request(endpoint_name)

            start_time = time.time()

            

            try:

                result = func(*args, **kwargs)

                duration = time.time() - start_time

                metrics.record_response_time(endpoint_name, duration)

                

                logger.info(f"{endpoint_name} completed in {duration:.2f}s")

                return result

                

            except Exception as e:

                duration = time.time() - start_time

                metrics.record_response_time(endpoint_name, duration)

                metrics.record_error(endpoint_name, type(e).__name__)

                

                logger.error(f"{endpoint_name} failed after {duration:.2f}s: {str(e)}")

                raise

        

        return wrapper

    return decorator



@app.route('/api/health', methods=['GET'])

@timing_decorator('health')

def health_check():

    """Enhanced health check with service validation"""

    # Check for skip network tests parameter
    skip_network = request.args.get('skip_network', 'false').lower() == 'true'

    

    health_status = {

        'status': 'healthy',

        'timestamp': datetime.now(timezone.utc).isoformat(),

        'version': APP_VERSION,
        'api_version': API_VERSION,
        'engine_version': ENGINE_VERSION,
        'release_date': RELEASE_DATE,
        'backend_build': BACKEND_BUILD_METADATA,

        'services': {},

        'metrics': metrics.get_stats(),

        'enhanced_features': {  # NEW: Show enhanced capabilities

            'future_retrograde_frustration': True,

            'directional_sign_exit': True,

            'translation_sequence_enforcement': True,

            'refranation_abscission_detection': True,

            'enhanced_reception_weighting': True,

            'venus_mercury_combustion_exceptions': True,

            'variable_moon_speed_timing': True,

            'fail_fast_geocoding': True,

            'optional_override_flags': True

        }

    }

    

    # Test timezone finder

    try:

        from timezonefinder import TimezoneFinder

        tf = TimezoneFinder()

        test_tz = tf.timezone_at(lat=51.5074, lng=-0.1278)  # London

        health_status['services']['timezone_finder'] = {

            'status': 'healthy' if test_tz else 'degraded',

            'test_result': test_tz

        }

    except Exception as e:

        health_status['services']['timezone_finder'] = {

            'status': 'unhealthy',

            'error': _health_error_detail(e)

        }

    

    # Test Swiss Ephemeris

    try:

        import swisseph as swe

        jd = swe.julday(2025, 5, 29, 12.0)

        sun_pos = swe.calc_ut(jd, swe.SUN)

        health_status['services']['swiss_ephemeris'] = {

            'status': 'healthy',

            'test_calculation': f"Sun at {sun_pos[0][0]:.2f}°"

        }

    except Exception as e:

        health_status['services']['swiss_ephemeris'] = {

            'status': 'unhealthy',

            'error': _health_error_detail(e)

        }

    

    # Test geocoding with enhanced error handling and faster timeout

    if skip_network:

        health_status['services']['geocoding'] = {

            'status': 'skipped',

            'note': 'Network tests disabled via skip_network=true parameter'

        }

    else:

        try:

            from geopy.geocoders import Nominatim

            geolocator = Nominatim(user_agent="enhanced_health_check")

            # Use shorter timeout and catch specific timeout errors

            location = geolocator.geocode("London, UK", timeout=1)

            health_status['services']['geocoding'] = {

                'status': 'healthy' if location else 'degraded',

                'test_result': location.address if location else None

            }

        except Exception as e:

            # Categorize timeout errors as degraded rather than unhealthy

            error_str = str(e).lower()

            if any(word in error_str for word in ['timeout', 'connection', 'network']):

                health_status['services']['geocoding'] = {

                    'status': 'degraded',

                    'error': 'Network timeout - service may be slow but functional'

                }

            else:

                health_status['services']['geocoding'] = {

                    'status': 'unhealthy',

                    'error': _health_error_detail(e)

                }

    

    # Test computational helpers

    try:

        from horary_engine.calculation.helpers import calculate_elongation, normalize_longitude

        test_elongation = calculate_elongation(120.0, 90.0)

        test_normalize = normalize_longitude(380.0)

        health_status['services']['computational_helpers'] = {

            'status': 'healthy',

            'test_calculations': {

                'elongation_120_90': f"{test_elongation:.2f}°",

                'normalize_380': f"{test_normalize:.2f}°"

            }

        }

    except Exception as e:

        health_status['services']['computational_helpers'] = {

            'status': 'unhealthy',

            'error': _health_error_detail(e)

        }

    

    # Overall status determination

    service_statuses = [s['status'] for s in health_status['services'].values()]

    if 'unhealthy' in service_statuses:

        health_status['status'] = 'unhealthy'

        return jsonify(health_status), 200

    elif 'degraded' in service_statuses:

        health_status['status'] = 'degraded'

        return jsonify(health_status), 200

    

    return jsonify(health_status), 200



# Simple in-memory cache for timezone requests
_timezone_cache_max = max(64, int(os.getenv("HORARY_TIMEZONE_CACHE_MAX", "256")))
_timezone_cache = OrderedDict()
_timezone_cache_lock = RLock()

@app.route('/api/get-timezone', methods=['POST'])

@timing_decorator('get_timezone')

def get_timezone():

    """Get timezone information for a given location with enhanced error handling"""

    try:

        data = request.get_json()

        

        if not data:

            return jsonify({'error': 'No JSON data provided', 'success': False}), 400

        

        location = data.get('location', '').strip()

        

        if not location:

            return jsonify({'error': 'Location is required', 'success': False}), 400

        

        # Check cache first
        cache_key = location.lower()
        with _timezone_cache_lock:
            cached_result = _timezone_cache.get(cache_key)
            if cached_result is not None:
                _timezone_cache.move_to_end(cache_key)
        if cached_result is not None:
            logger.info(
                "Using cached timezone result for get-timezone request (location_chars=%s)",
                len(location),
            )
            return jsonify(cached_result)

        logger.info(
            "Resolving timezone for request (location_chars=%s)",
            len(location),
        )

        

        # ENHANCED: Use fail-fast geocoding

        try:

            from horary_engine.services.geolocation import safe_geocode

            lat, lon, full_location = safe_geocode(location)

            

            # Get timezone using enhanced timezone manager

            from horary_engine.services.geolocation import TimezoneManager

            timezone_manager = TimezoneManager()

            timezone_str = timezone_manager.get_timezone_for_location(lat, lon)

            

            result = {

                'location': full_location,

                'latitude': lat,

                'longitude': lon,

                'timezone': timezone_str,

                'success': True,

                'enhanced_geocoding': True  # NEW: Indicate enhanced processing

            }

            
            # Cache the result
            with _timezone_cache_lock:
                _timezone_cache[cache_key] = result
                _timezone_cache.move_to_end(cache_key)
                while len(_timezone_cache) > _timezone_cache_max:
                    _timezone_cache.popitem(last=False)

            logger.info(
                "Timezone resolution succeeded (timezone=%s, location_chars=%s)",
                timezone_str,
                len(full_location or location),
            )

            return jsonify(result)

            

        except LocationError as e:

            # ENHANCED: Proper location error handling

            error_msg = str(e)

            logger.warning(f"Location error: {error_msg}")

            return jsonify({

                'error': error_msg,

                'success': False,

                'error_type': 'LocationError'

            }), 404

            

        except Exception as e:

            error_msg = f'Error getting timezone for {location}: {str(e)}'

            logger.error(error_msg)

            return jsonify({

                'error': error_msg,

                'success': False

            }), 500

            

    except Exception as e:

        logger.error(f"Unexpected error in get_timezone: {str(e)}")

        return jsonify({

            'error': f'Internal server error: {str(e)}',

            'success': False

        }), 500



@app.route('/api/current-time', methods=['POST'])

@timing_decorator('current_time')

def get_current_time():

    """Get current time for a specific location with enhanced processing"""

    try:

        data = request.get_json()

        

        if not data:

            return jsonify({'error': 'No JSON data provided', 'success': False}), 400

        

        location = data.get('location', '').strip()

        

        if not location:

            return jsonify({'error': 'Location is required', 'success': False}), 400

        

        logger.info(
            "Resolving current time for request (location_chars=%s)",
            len(location),
        )

        

        # ENHANCED: Use fail-fast geocoding

        try:

            from horary_engine.services.geolocation import safe_geocode

            lat, lon, full_location = safe_geocode(location)

            

            # Get current time using enhanced timezone manager

            from horary_engine.services.geolocation import TimezoneManager

            timezone_manager = TimezoneManager()

            dt_local, dt_utc, timezone_used = timezone_manager.get_current_time_for_location(lat, lon)

            

            result = {

                'location': full_location,

                'latitude': lat,

                'longitude': lon,

                'local_time': dt_local.isoformat(),

                'utc_time': dt_utc.isoformat(),

                'timezone': timezone_used,

                'utc_offset': dt_local.strftime("%z") if hasattr(dt_local, 'strftime') else "Unknown",

                'success': True,

                'enhanced_processing': True  # NEW: Indicate enhanced processing

            }

            

            logger.info(
                "Current-time resolution succeeded (timezone=%s, location_chars=%s)",
                timezone_used,
                len(full_location or location),
            )

            return jsonify(result)

            

        except LocationError as e:

            # ENHANCED: Proper location error handling

            error_msg = str(e)

            logger.warning(f"Location error: {error_msg}")

            return jsonify({

                'error': error_msg,

                'success': False,

                'error_type': 'LocationError'

            }), 404

            

        except Exception as e:

            error_msg = f'Error getting current time for {location}: {str(e)}'

            logger.error(error_msg)

            return jsonify({

                'error': error_msg,

                'success': False

            }), 500

            

    except Exception as e:

        logger.error(f"Unexpected error in get_current_time: {str(e)}")

        return jsonify({

            'error': f'Internal server error: {str(e)}',

            'success': False

        }), 500



@app.route('/api/calculate-chart', methods=['POST'])

@timing_decorator('calculate_chart')

def calculate_chart():

    """

    ENHANCED: Calculate horary chart with all new features

    Now includes future retrograde, directional motion, enhanced reception, and more

    """

    try:

        data = request.get_json()

        

        if not data:

            return jsonify({

                'error': 'No JSON data provided',

                'judgment': 'ERROR',

                'confidence': 0,

                'reasoning': [make_reason('No JSON data provided')]

            }), 400

        

        # Extract basic parameters

        question = data.get('question', '').strip()

        location = data.get('location', 'London, UK').strip()

        date_str = data.get('date')

        time_str = data.get('time')

        timezone_str = data.get('timezone')

        raw_location_name = data.get('locationName')
        if raw_location_name in (None, ""):
            raw_location_name = data.get('location_name')
        location_name = str(raw_location_name).strip() if raw_location_name not in (None, "") else None

        try:
            latitude = _optional_finite_float(data.get('latitude'), 'latitude')
            longitude = _optional_finite_float(data.get('longitude'), 'longitude')
        except ValueError as exc:
            return jsonify({
                'error': str(exc),
                'judgment': 'ERROR',
                'confidence': 0,
                'reasoning': [make_reason(str(exc))],
            }), 400

        if (latitude is None) != (longitude is None):
            return jsonify({
                'error': 'latitude and longitude must be supplied together',
                'judgment': 'ERROR',
                'confidence': 0,
                'reasoning': [make_reason('Coordinate override requires both latitude and longitude')],
            }), 400

        if latitude is not None and not location_name:
            location_name = location

        use_current_time = data.get('useCurrentTime', True)

        manual_houses = data.get('manualHouses')

        use_reasoning_v1 = request.headers.get('X-Use-Reasoning-V1')
        if use_reasoning_v1 is None:
            use_reasoning_v1 = request.args.get('useReasoningV1')
        if use_reasoning_v1 is None:
            use_reasoning_v1 = os.getenv('USE_REASONING_V1', 'false')
        use_reasoning_v1 = str(use_reasoning_v1).lower() == 'true'

        

        # NEW: Extract enhanced parameters

        ignore_radicality = data.get('ignoreRadicality', False)

        ignore_void_moon = data.get('ignoreVoidMoon', False)

        ignore_combustion = data.get('ignoreCombustion', False)

        ignore_saturn_7th = data.get('ignoreSaturn7th', False)

        exaltation_confidence_boost = data.get('exaltationConfidenceBoost', 15.0)

        

        logger.info(
            "Horary chart calculation request summary: %s",
            json.dumps(
                _chart_request_log_summary(
                    question=question,
                    location=location,
                    date_str=date_str,
                    time_str=time_str,
                    timezone_str=timezone_str,
                    use_current_time=use_current_time,
                    manual_houses=manual_houses,
                    use_reasoning_v1=use_reasoning_v1,
                ),
                sort_keys=True,
            ),
        )

        if any([ignore_radicality, ignore_void_moon, ignore_combustion, ignore_saturn_7th]):
            logger.info(
                "Horary override flags active (radicality=%s, void_moon=%s, combustion=%s, saturn_7th=%s)",
                ignore_radicality,
                ignore_void_moon,
                ignore_combustion,
                ignore_saturn_7th,
            )

        if exaltation_confidence_boost != 15.0:
            logger.info(
                "Horary exaltation confidence boost overridden to %s%%",
                exaltation_confidence_boost,
            )

        

        # Validate required fields

        if not question:

            return jsonify({

                'error': 'Question is required',

                'judgment': 'ERROR',

                'confidence': 0,

                'reasoning': [make_reason('No horary question provided')]

            }), 400

        

        if not location:

            return jsonify({

                'error': 'Location is required',

                'judgment': 'ERROR', 

                'confidence': 0,

                'reasoning': [make_reason('No location provided')]

            }), 400

        

        # Validate manual time inputs

        if not use_current_time:

            if not date_str or not time_str:

                return jsonify({

                    'error': 'Date and time are required when not using current time',

                    'judgment': 'ERROR',

                    'confidence': 0,

                    'reasoning': [make_reason('Date and time must be provided for manual time entry')]

                }), 400

        

        # Convert manual houses if provided

        houses_list = None

        if manual_houses:

            try:

                houses_list = [int(h.strip()) for h in manual_houses.split(',') if h.strip()]

                if len(houses_list) < 2:

                    return jsonify({

                        'error': 'Manual houses must include at least querent and quesited houses (e.g., "1,7")',

                        'judgment': 'ERROR',

                        'confidence': 0,

                        'reasoning': [make_reason('Invalid manual house specification')]

                    }), 400

            except ValueError:

                return jsonify({

                    'error': 'Manual houses must be numbers separated by commas (e.g., "1,7")',

                    'judgment': 'ERROR',

                    'confidence': 0,

                    'reasoning': [make_reason('Invalid manual house format')]

                }), 400

        

        # ENHANCED: Calculate chart using new enhanced engine with all features

        start_time = time.time()

        

        try:

            settings = {

                "location": location,

                "location_name": location_name,

                "date": date_str,

                "time": time_str,

                "timezone": timezone_str,

                "latitude": latitude,

                "longitude": longitude,

                "use_current_time": use_current_time,

                "manual_houses": houses_list,

                # NEW: Enhanced features

                "ignore_radicality": ignore_radicality,

                "ignore_void_moon": ignore_void_moon,

                "ignore_combustion": ignore_combustion,

                "ignore_saturn_7th": ignore_saturn_7th,

                # Same-process API callers can reuse the in-memory chart object
                # and avoid an unnecessary serialize -> deserialize round trip.
                "include_internal_chart": True,

                "exaltation_confidence_boost": exaltation_confidence_boost

            }

            
            logger.info("About to call horary_engine.judge()...")
            try:
                result = horary_engine.judge(question, settings)
                logger.info(f"horary_engine.judge() completed successfully, got result type: {type(result)}")
            except Exception as judge_error:
                logger.error(f"ERROR in horary_engine.judge(): {str(judge_error)}")
                logger.error(f"Exception type: {type(judge_error)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise

            

        except LocationError as e:

            # ENHANCED: Proper location error handling

            logger.error(f"Location error: {str(e)}")

            return jsonify({

                'error': str(e),

                'judgment': 'LOCATION_ERROR',

                'confidence': 0,

                'reasoning': [make_reason(f'Location error: {str(e)}')],

                'error_type': 'LocationError'

            }), 400

        

        calculation_time = time.time() - start_time

        logger.info(f"ENHANCED chart calculation completed in {calculation_time:.2f} seconds")

        

        # Check for calculation errors

        if result.get('error'):

            logger.error(f"Chart calculation error: {result['error']}")

            return jsonify(result), 500

        

        # ENHANCED: Add enhanced calculation metadata

        result['calculation_metadata'] = {

            'calculation_time_seconds': calculation_time,

            'timestamp': datetime.now(timezone.utc).isoformat(),

            'app_version': APP_VERSION,

            'api_version': API_VERSION,

            'engine_version': ENGINE_VERSION,

            'enhanced_features_used': {

                'future_retrograde_checks': True,

                'directional_motion_awareness': True,

                'sequence_enforcement': True,

                'enhanced_denial_conditions': True,

                'reception_weighting_nuance': True,

                'solar_condition_enhancements': True,

                'variable_moon_timing': True,

                'fail_fast_geocoding': True

            },

            'override_flags_applied': {

                'ignore_radicality': ignore_radicality,

                'ignore_void_moon': ignore_void_moon,

                'ignore_combustion': ignore_combustion,

                'ignore_saturn_7th': ignore_saturn_7th

            },

            'enhanced_parameters': {

                'exaltation_confidence_boost': exaltation_confidence_boost

            }

        }

        

        logger.info(f"ENHANCED chart calculation successful - Judgment: {result.get('judgment')} (Confidence: {result.get('confidence')}%)")

        

        # NEW: Log enhanced solar factors if present

        solar_factors = result.get('solar_factors', {})

        if solar_factors.get('significant'):

            logger.info(f"Enhanced solar factors: {solar_factors.get('summary', 'None')}")

            if solar_factors.get('cazimi_count', 0) > 0:

                logger.info(f"Cazimi planets detected: {solar_factors['cazimi_count']}")

            if solar_factors.get('combustion_count', 0) > 0:

                logger.info(f"Combusted planets detected: {solar_factors['combustion_count']}")

        

        # NEW: Log enhanced features if they affected judgment

        traditional_factors = result.get('traditional_factors', {})

        if traditional_factors.get('perfection_type'):

            logger.info(f"Perfection type: {traditional_factors['perfection_type']}")

        # Attach structured evaluation results
        try:
            chart_data = result.get('chart_data')
            if chart_data:
                chart_obj = result.pop('_raw_chart', None)
                if chart_obj is None:
                    chart_obj = deserialize_chart_for_evaluation(chart_data)
                evaluation = evaluate_chart(chart_obj, use_dsl=False)
                ledger = evaluation.get('ledger', [])
                for entry in ledger:
                    entry['key'] = token_to_string(entry.get('key'))
                    if 'polarity' in entry and hasattr(entry['polarity'], 'name'):
                        entry['polarity'] = entry['polarity'].name
                result['ledger'] = ledger
                if use_reasoning_v1:
                    result['reasoning_v1'] = evaluation.get('rationale', [])
                else:
                    result['rationale'] = evaluation.get('rationale', [])
            else:
                if use_reasoning_v1:
                    result['reasoning_v1'] = result.get('reasoning', [])
                else:
                    result['rationale'] = result.get('reasoning', [])
        except Exception as eval_error:
            logger.warning(f"evaluate_chart failed: {eval_error}")
            if use_reasoning_v1:
                result['reasoning_v1'] = result.get('reasoning', [])
            else:
                result['rationale'] = result.get('reasoning', [])

        # Internal passthrough chart must never cross the JSON boundary.
        result.pop('_raw_chart', None)

        # Make result JSON-safe by converting Planet enums and other non-serializable objects
        safe_result = make_json_safe(result)
        return jsonify(safe_result)

        

    except Exception as e:
        incident_id = uuid4().hex[:12]
        logger.error(
            "Error calculating enhanced chart [incident=%s]: %s",
            incident_id,
            str(e),
        )
        logger.error(traceback.format_exc())

        return jsonify({
            'error': 'internal_error',
            'detail': 'An internal server error occurred while calculating the chart.',
            'incident_id': incident_id,
            'judgment': 'ERROR',
            'confidence': 0,
            'reasoning': [make_reason('Enhanced calculation error')],
            'calculation_metadata': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'app_version': APP_VERSION,
                'api_version': API_VERSION,
                'engine_version': ENGINE_VERSION
            }
        }), 500



@app.route('/api/moon-debug', methods=['POST'])

@timing_decorator('moon_debug')

def moon_debug():

    """Get detailed Moon void of course debug information"""

    try:

        data = request.get_json()

        

        if not data:

            return jsonify({'error': 'No JSON data provided'}), 400

        

        return jsonify({

            'message': 'Enhanced Moon debug information is included in chart calculation results',

            'instructions': 'Check the moon_aspects field in the calculate-chart response',

            'enhanced_features': {

                'variable_moon_speed': 'Real-time Moon speed from ephemeris',

                'directional_sign_exit': 'Motion-aware sign boundary calculations',

                'enhanced_void_detection': 'Improved future aspect calculations',

                'solar_conditions': 'Check response.solar_factors for detailed analysis'

            },

            'example_usage': {

                'endpoint': '/api/calculate-chart',

                'moon_debug_location': 'response.moon_aspects',

                'solar_analysis_location': 'response.solar_factors'

            },

            'new_override_options': {

                'ignore_void_moon': 'Set to true to bypass void Moon restrictions',

                'ignore_combustion': 'Set to true to ignore solar condition penalties'

            }

        })

        

    except Exception as e:

        logger.error(f"Error in enhanced moon_debug endpoint: {str(e)}")

        return jsonify({'error': str(e)}), 500



@app.route('/api/metrics', methods=['GET'])

@timing_decorator('metrics')

def get_metrics():

    """Get enhanced API performance metrics"""

    try:

        return jsonify({

            'status': 'success',

            'metrics': metrics.get_stats(),

            'enhanced_engine_stats': {

                'version': API_VERSION,

                'features_enabled': 9,  # Count of major enhanced features

                'classical_sources_implemented': 5

            },

            'timestamp': datetime.now(timezone.utc).isoformat()

        })

    except Exception as e:

        logger.error(f"Error getting enhanced metrics: {str(e)}")

        return jsonify({'error': str(e)}), 500



@app.route('/api/version', methods=['GET'])

def get_version():

    """ENHANCED: Get comprehensive API version information"""

    return jsonify({

        'app_version': APP_VERSION,

        'api_version': API_VERSION,

        'engine_version': ENGINE_VERSION,

        'release_date': RELEASE_DATE,

        'backend_build': BACKEND_BUILD_METADATA,

        'features': [

            'Traditional horary analysis',

            'Timezone support',

            'Swiss Ephemeris calculations',

            'Enhanced Moon void of course analysis',

            'Automatic timezone detection',

            'DST handling',

            'Enhanced dignity calculations',

            'Regiomontanus house system',

            'Enhanced Cazimi detection',

            'Enhanced Combustion analysis',

            'Enhanced Under the Beams calculation',

            'Traditional solar exceptions',

            # NEW ENHANCED FEATURES

            'Future retrograde frustration protection',

            'Directional sign-exit awareness',

            'Translation/collection sequence enforcement',

            'Refranation and abscission detection',

            'Enhanced reception weighting nuance',

            'Venus/Mercury combustion exceptions',

            'Variable Moon speed timing',

            'Fail-fast geocoding',

            'Optional override flags'

        ],

        'enhanced_features': {  # NEW: Detailed enhanced features

            'future_retrograde': {

                'description': 'Checks if planets will station before aspect perfection',

                'classical_source': 'Lilly III Chap. XXI - Frustration of planets'

            },

            'directional_motion': {

                'description': 'Respects actual planetary motion for sign boundaries',

                'classical_source': 'Firmicus Maternus - Sign boundaries and motion'

            },

            'sequence_enforcement': {

                'description': 'Validates proper temporal order for translation/collection',

                'classical_source': 'Lilly III Chap. XXVI - Translation of light'

            },

            'denial_conditions': {

                'description': 'Refranation and abscission detection',

                'classical_source': 'Medieval astrological doctrine'

            },

            'reception_weighting': {

                'description': 'Mutual rulership unconditional power, configurable exaltation boost',

                'implementation': 'Traditional dignity hierarchy preserved'

            },

            'enhanced_solar_conditions': {

                'description': 'Visibility-aware Venus/Mercury combustion exceptions',

                'classical_source': 'Ptolemy Almagest, Al-Biruni visibility calculations'

            },

            'variable_timing': {

                'description': 'Real-time Moon speed from ephemeris',

                'classical_source': 'Lilly III Chap. XXV - Moon variable motion'

            },

            'fail_fast_geocoding': {

                'description': 'No silent defaults, clear error messages',

                'enhancement': 'Better user experience and error handling'

            },

            'override_capabilities': {

                'description': 'Optional bypass for radicality, void Moon, combustion',

                'use_case': 'Special circumstances and edge cases'

            }

        },

        'solar_conditions': {

            'implementation': 'Enhanced traditional medieval and renaissance methods',

            'cazimi': {

                'orb': '17 arcminutes (0.28°)',

                'dignity_bonus': '+6 (exact cazimi +8)',

                'description': 'Heart of the Sun - maximum planetary dignity',

                'enhancement': 'Exact cazimi detection within 3 arcminutes'

            },

            'combustion': {

                'orb': '8 degrees 30 arcminutes',

                'dignity_penalty': '-5 (enhanced gradation by distance)',

                'description': 'Planet burnt by Sun - severely weakened',

                'enhanced_exceptions': [

                    'Mercury in own sign (Gemini/Virgo) with visibility check',

                    'Venus as morning/evening star with elongation ≥10° and civil twilight'

                ]

            },

            'under_beams': {

                'orb': '15 degrees',

                'dignity_penalty': '-3 (enhanced gradation by distance)',

                'description': 'Planet obscured by solar rays - moderately weakened',

                'enhancement': 'Distance-based penalty gradation'

            }

        },

        'classical_sources': [

            'William Lilly - Christian Astrology',

            'Guido Bonatti - Liber Astronomicus',

            'Claudius Ptolemy - Tetrabiblos & Almagest',

            'Firmicus Maternus - Mathesis',

            'Al-Biruni - Elements of Astrology'

        ],

        'backward_compatibility': {

            'preserved': True,

            'old_api_supported': True,

            'migration_required': False,

            'enhancement_note': 'All existing code works unchanged'

        },

        'timestamp': datetime.now(timezone.utc).isoformat()

    })



def serialize_moon_debug(debug_data):

    """Convert moon debug data to JSON-serializable format (preserved)"""

    try:

        serialized = {

            'moon_position': debug_data.get('moon_position', {}),

            'sign_analysis': debug_data.get('sign_analysis', {}),

            'current_aspects': debug_data.get('current_aspects', []),

            'void_result': {

                'void': debug_data.get('void_result', {}).get('void', False),

                'exception': debug_data.get('void_result', {}).get('exception', False),

                'reason': debug_data.get('void_result', {}).get('reason', 'Unknown'),

                'degrees_left_in_sign': debug_data.get('void_result', {}).get('degrees_left_in_sign', 0),

                'first_applying_aspect': serialize_lunar_aspect(
                    debug_data.get('void_result', {}).get('first_applying_aspect')
                ),

            },

            'future_aspects': []

        }

        

        # Convert future aspects with enhanced processing

        void_result = debug_data.get('void_result', {})

        future_aspects = void_result.get('future_aspects', [])

        

        for aspect in future_aspects:

            try:

                serialized['future_aspects'].append({

                    'planet': aspect['planet'].value if hasattr(aspect['planet'], 'value') else str(aspect['planet']),

                    'aspect': aspect['aspect'].display_name if hasattr(aspect['aspect'], 'display_name') else str(aspect['aspect']),

                    'target_degree': float(aspect.get('target_degree', 0)),

                    'degrees_to_reach': float(aspect.get('degrees_to_reach', 0)),

                    'days_to_aspect': float(aspect.get('days_to_aspect', 0)),

                    'will_perfect': bool(aspect.get('will_perfect', False))

                })

            except Exception as e:

                logger.error(f"Error serializing future aspect: {e}")

                continue

        

        return serialized

        

    except Exception as e:

        logger.error(f"Error serializing moon debug: {e}")

        return {

            'error': 'Could not serialize moon debug data',

            'details': str(e)

        }



# Enhanced error handlers

@app.errorhandler(404)

def not_found(error):

    return jsonify({

        'error': 'Endpoint not found',

        'message': 'The requested API endpoint does not exist',

        'app_version': APP_VERSION,

        'api_version': API_VERSION,

        'available_endpoints': [

            '/api/health',

            '/api/calculate-chart',

            '/api/get-timezone',

            '/api/current-time',

            '/api/moon-debug',

            '/api/metrics',

            '/api/version'

        ],

        'enhanced_features': 'See /api/version for full feature list'

    }), 404



@app.errorhandler(405)

def method_not_allowed(error):

    return jsonify({

        'error': 'Method not allowed',

        'message': 'The HTTP method is not allowed for this endpoint',

        'app_version': APP_VERSION,

        'api_version': API_VERSION

    }), 405



@app.errorhandler(500)

def internal_error(error):

    logger.error(f"Internal server error: {str(error)}")

    return jsonify({

        'error': 'Internal server error',

        'message': 'An unexpected error occurred in the enhanced engine',

        'app_version': APP_VERSION,

        'api_version': API_VERSION,

        'timestamp': datetime.now(timezone.utc).isoformat()

    }), 500



# Request logging middleware (preserved)

@app.before_request

def log_request():

    logger.info(f"{request.method} {request.path} - {request.remote_addr}")



@app.after_request

def log_response(response):

    logger.info(f"Response: {response.status_code} - {request.method} {request.path}")

    return response



def is_packaged_executable():
    """Detect if running as a PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def is_development_mode():
    """Detect if running in development mode"""
    return not is_packaged_executable() and os.environ.get('FLASK_ENV') != 'production'

def enable_dev_license_bypass_for_source_runtime():
    """Enable local dev licensing bypass for source-run localhost development."""
    os.environ.setdefault('VOX_STELLA_ENV', 'development')
    os.environ.setdefault('ALLOW_DEV_LICENSE_BYPASS', '1')
    return {
        'VOX_STELLA_ENV': os.environ.get('VOX_STELLA_ENV'),
        'ALLOW_DEV_LICENSE_BYPASS': os.environ.get('ALLOW_DEV_LICENSE_BYPASS'),
    }

if __name__ == '__main__':
    
    logger.info(f"Starting Enhanced Traditional Horary Astrology API Server app={APP_VERSION} api={API_VERSION}")
    logger.info("Enhanced Features: Future retrograde, directional motion, enhanced reception")
    logger.info("New Capabilities: Refranation/abscission detection, enhanced solar conditions")
    logger.info("Override Options: Radicality, void Moon, combustion, Saturn 7th")
    logger.info("Classical Sources: Lilly, Bonatti, Ptolemy, Firmicus, Al-Biruni")
    logger.info("Backward Compatibility: All existing code works unchanged")

    parent_watchdog = start_parent_watchdog(logger=logger)
    if parent_watchdog:
        logger.info("Electron parent watchdog enabled")
    
    # Determine runtime environment
    packaged = is_packaged_executable()
    dev_mode = is_development_mode()
    
    # Determine port (overridable by HORARY_PORT)
    try:
        desired_port = int(os.getenv('HORARY_PORT', '52525'))
    except Exception:
        desired_port = 52525

    if packaged:
        logger.info("Running as packaged executable - PRODUCTION MODE")
        logger.info("PyInstaller bundle detected")
        
        # Use production server to suppress development warnings
        try:
            from production_server import create_production_server
            server = create_production_server(host='127.0.0.1', port=desired_port)
            logger.info(f"Production server starting on http://127.0.0.1:{desired_port}")
            server.serve_forever()
        except ImportError:
            # Fallback to basic production configuration
            logger.warning("Production server module not available, using basic production mode")
            # Suppress werkzeug development warnings
            werkzeug_logger = logging.getLogger('werkzeug')
            werkzeug_logger.setLevel(logging.ERROR)
            
            app.run(
                debug=False,
                host='127.0.0.1',
                port=desired_port,
                threaded=True,
                use_reloader=False
            )
    elif dev_mode:
        enable_dev_license_bypass_for_source_runtime()
        logger.info("Running in DEVELOPMENT MODE")
        logger.info("Local development license bypass enabled for source runtime")
        debug_enabled = str(os.getenv('HORARY_DEBUG', '0')).strip().lower() in {'1', 'true', 'yes'}
        logger.info("Debug mode %s", "enabled" if debug_enabled else "disabled")
        logger.info("Development bind address forced to localhost (127.0.0.1)")
        # Development configuration
        app.run(
            debug=debug_enabled,
            host='127.0.0.1',
            port=desired_port,
            use_reloader=debug_enabled
        )
    else:
        logger.info("Running in PRODUCTION MODE (Python script)")
        logger.info("Production configuration applied")
        # Production configuration for Python script
        app.run(
            debug=False,
            host='127.0.0.1',
            port=desired_port,
            threaded=True,
            use_reloader=False
        )
    
    # Note: For high-traffic production deployments, consider using:
    # gunicorn -w 4 -b 127.0.0.1:5000 app:app
