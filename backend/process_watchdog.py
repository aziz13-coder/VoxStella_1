"""Backend process watchdog helpers.

The packaged backend is launched as a child of the Electron main process.
If Electron exits unexpectedly on Windows, quit hooks may not always get a
chance to terminate the backend cleanly. This watchdog lets the backend
self-terminate when its parent Electron process disappears.
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
from pathlib import Path
import threading
import time
from typing import Callable, Optional


DEFAULT_PARENT_PID_ENV = "VOX_STELLA_PARENT_PID"
DEFAULT_PARENT_STATE_FILE_ENV = "VOX_STELLA_PARENT_STATE_FILE"
DEFAULT_PARENT_STATE_STALE_SECONDS = 10.0


def parse_parent_pid(raw: Optional[str]) -> Optional[int]:
    """Return a positive parent PID from a string environment value."""
    if raw is None:
        return None
    try:
        pid = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _windows_process_exists(pid: int) -> bool:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )
    if not handle:
        return False
    ctypes.windll.kernel32.CloseHandle(handle)
    return True


def _posix_process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        if exc.errno == errno.EPERM:
            return True
        return False
    return True


def parent_process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_process_exists(pid)
    return _posix_process_exists(pid)


def parent_state_file_fresh(
    path: Optional[str],
    *,
    stale_after_seconds: float = DEFAULT_PARENT_STATE_STALE_SECONDS,
    time_fn: Callable[[], float] = time.time,
) -> bool:
    if not path:
        return True
    try:
        raw = Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw)
    except Exception:
        return False

    updated_at = payload.get("updated_at_ms")
    if updated_at is None:
        updated_at = payload.get("updated_at")
    try:
        updated_at = float(updated_at)
    except (TypeError, ValueError):
        return False

    # Accept either milliseconds or seconds.
    if updated_at > 1_000_000_000_000:
        updated_at = updated_at / 1000.0

    return (time_fn() - updated_at) <= stale_after_seconds


def watchdog_should_exit(
    parent_pid: int,
    *,
    parent_state_file: Optional[str] = None,
    state_file_fresh: Callable[..., bool] = parent_state_file_fresh,
    stale_after_seconds: float = DEFAULT_PARENT_STATE_STALE_SECONDS,
    alive_check: Callable[[int], bool] = parent_process_exists,
) -> bool:
    """Return True when the tracked parent PID is no longer alive."""
    if parent_pid > 0 and not alive_check(parent_pid):
        return True
    if parent_state_file and not state_file_fresh(
        parent_state_file,
        stale_after_seconds=stale_after_seconds,
    ):
        return True
    return False


def _watch_parent_loop(
    parent_pid: int,
    *,
    parent_state_file: Optional[str] = None,
    logger=None,
    exit_func: Callable[[int], None] = os._exit,
    poll_interval: float = 2.0,
    stale_after_seconds: float = DEFAULT_PARENT_STATE_STALE_SECONDS,
    state_file_fresh: Callable[..., bool] = parent_state_file_fresh,
    alive_check: Callable[[int], bool] = parent_process_exists,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    while True:
        sleep_fn(poll_interval)
        if watchdog_should_exit(
            parent_pid,
            parent_state_file=parent_state_file,
            state_file_fresh=state_file_fresh,
            stale_after_seconds=stale_after_seconds,
            alive_check=alive_check,
        ):
            if logger:
                try:
                    logger.warning(
                        "Electron parent liveness lost (pid=%s, state_file=%s); stopping backend",
                        parent_pid,
                        parent_state_file,
                    )
                except Exception:
                    pass
            exit_func(0)


def start_parent_watchdog(
    *,
    logger=None,
    env_key: str = DEFAULT_PARENT_PID_ENV,
    state_file_env_key: str = DEFAULT_PARENT_STATE_FILE_ENV,
    poll_interval: float = 2.0,
    stale_after_seconds: float = DEFAULT_PARENT_STATE_STALE_SECONDS,
    exit_func: Callable[[int], None] = os._exit,
    state_file_fresh: Callable[..., bool] = parent_state_file_fresh,
    alive_check: Callable[[int], bool] = parent_process_exists,
) -> Optional[threading.Thread]:
    """Start a daemon thread that exits when the parent Electron PID dies."""
    parent_pid = parse_parent_pid(os.getenv(env_key))
    parent_state_file = (os.getenv(state_file_env_key) or "").strip() or None
    if not parent_pid and not parent_state_file:
        return None

    thread = threading.Thread(
        target=_watch_parent_loop,
        kwargs={
            "parent_pid": parent_pid,
            "parent_state_file": parent_state_file,
            "logger": logger,
            "exit_func": exit_func,
            "poll_interval": poll_interval,
            "stale_after_seconds": stale_after_seconds,
            "state_file_fresh": state_file_fresh,
            "alive_check": alive_check,
        },
        name="vox-stella-parent-watchdog",
        daemon=True,
    )
    thread.start()
    return thread
