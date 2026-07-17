# -*- coding: utf-8 -*-
"""Shared guard for Swiss Ephemeris process-global state."""

from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Iterator


_SWISSEPH_LOCK = RLock()


@contextmanager
def swisseph_lock() -> Iterator[None]:
    with _SWISSEPH_LOCK:
        yield


__all__ = ["swisseph_lock"]
