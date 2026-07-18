# -*- coding: utf-8 -*-
"""Shared synchronization boundary for Swiss Ephemeris ambient C state.

Swiss Ephemeris keeps configuration and calculation caches in ambient C state
whose scope depends on the native build (process-global or thread-local). A
lock around only ``set_ephe_path``/``set_topo`` is therefore not a sufficient
cross-build contract. All calls cross one re-entrant boundary, while the
transaction contexts below keep state mutation and dependent calculations on
the same thread and restore the previous state afterward.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import importlib
from threading import RLock
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

try:
    import swisseph as _RAW_SWISSEPH  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    _RAW_SWISSEPH = None  # type: ignore


_SWISSEPH_LOCK = RLock()
_EPHEMERIS_PATHS: Dict[int, str] = {}
_TOPOCENTRIC_POSITIONS: Dict[int, Tuple[float, float, float]] = {}


@contextmanager
def swisseph_lock() -> Iterator[None]:
    with _SWISSEPH_LOCK:
        yield


class _SynchronizedSwissEphemeris:
    """Attribute-compatible facade that serializes Swiss Ephemeris calls."""

    def __init__(self, module: Any):
        self._module = module

    @property
    def raw_module(self) -> Any:
        return self._module

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._module, name)
        if isinstance(value, type) or not callable(value):
            return value

        @wraps(value)
        def synchronized_call(*args: Any, **kwargs: Any) -> Any:
            with _SWISSEPH_LOCK:
                target: Callable[..., Any] = getattr(self._module, name)
                result = target(*args, **kwargs)
                module_key = id(self._module)
                if name == "set_ephe_path":
                    _EPHEMERIS_PATHS[module_key] = _normalize_ephemeris_path(
                        args[0] if args else kwargs.get("path")
                    )
                elif name == "set_topo":
                    longitude = (
                        args[0]
                        if len(args) > 0
                        else kwargs.get("lon", kwargs.get("longitude", 0.0))
                    )
                    latitude = (
                        args[1]
                        if len(args) > 1
                        else kwargs.get("lat", kwargs.get("latitude", 0.0))
                    )
                    altitude = (
                        args[2]
                        if len(args) > 2
                        else kwargs.get("alt", kwargs.get("altitude", 0.0))
                    )
                    _TOPOCENTRIC_POSITIONS[module_key] = (
                        float(longitude),
                        float(latitude),
                        float(altitude),
                    )
                return result

        return synchronized_call


def _normalize_ephemeris_path(path: Any) -> str:
    return "" if path is None else str(path)


def synchronized_swisseph(module: Any = None) -> Optional[_SynchronizedSwissEphemeris]:
    """Return a synchronized facade for ``module`` or the installed binding."""
    target = _RAW_SWISSEPH if module is None else module
    if target is None:
        return None
    if isinstance(target, _SynchronizedSwissEphemeris):
        return target
    return _SynchronizedSwissEphemeris(target)


def require_swisseph() -> _SynchronizedSwissEphemeris:
    """Load the current binding and return its synchronized facade."""
    module = importlib.import_module("swisseph")
    api = synchronized_swisseph(module)
    if api is None:  # pragma: no cover - import_module either returns or raises
        raise ImportError("Swiss Ephemeris is unavailable")
    return api


swisseph = synchronized_swisseph()


def _raw_module(api: Any) -> Any:
    if isinstance(api, _SynchronizedSwissEphemeris):
        return api.raw_module
    return api


def configure_swisseph_ephemeris_path(path: Any) -> None:
    """Set the current native-state baseline outside a temporary block."""
    if swisseph is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")
    swisseph.set_ephe_path(_normalize_ephemeris_path(path))


@contextmanager
def swisseph_ephemeris_path(
    path: Any,
    *,
    swe_module: Any = None,
) -> Iterator[Any]:
    """Temporarily select an ephemeris path for an atomic calculation block."""
    api = synchronized_swisseph(swe_module)
    if api is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")

    with _SWISSEPH_LOCK:
        module_key = id(_raw_module(api))
        previous_path = _EPHEMERIS_PATHS.get(module_key, "")
        selected_path = _normalize_ephemeris_path(path)
        api.set_ephe_path(selected_path)
        try:
            yield api
        finally:
            api.set_ephe_path(previous_path)


@contextmanager
def swisseph_topocentric(
    longitude: float,
    latitude: float,
    altitude: float = 0.0,
    *,
    swe_module: Any = None,
) -> Iterator[Any]:
    """Set an observer and keep all dependent topocentric calls atomic."""
    api = synchronized_swisseph(swe_module)
    if api is None:
        raise RuntimeError("Swiss Ephemeris is unavailable")

    with _SWISSEPH_LOCK:
        module_key = id(_raw_module(api))
        previous_position = _TOPOCENTRIC_POSITIONS.get(module_key, (0.0, 0.0, 0.0))
        api.set_topo(float(longitude), float(latitude), float(altitude))
        try:
            yield api
        finally:
            api.set_topo(*previous_position)


__all__ = [
    "configure_swisseph_ephemeris_path",
    "swisseph",
    "swisseph_ephemeris_path",
    "swisseph_lock",
    "swisseph_topocentric",
    "require_swisseph",
    "synchronized_swisseph",
]
