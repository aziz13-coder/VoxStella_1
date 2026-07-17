from __future__ import annotations

import threading
import time
from pathlib import Path
import sys


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from backend.forensic import local_space as local_space_module


class _BlockingSwe:
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
    SEFLG_SWIEPH = 2
    SEFLG_EQUATORIAL = 2048
    SEFLG_TOPOCTR = 32

    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()
        self.first_calc_entered = threading.Event()
        self.release_first_calc = threading.Event()
        self.calc_count = 0

    def set_topo(self, lon, lat, alt):
        with self._lock:
            self.calls.append(("set_topo", lon, lat, alt))

    def julday(self, *_args):
        return 2460000.5

    def sidtime(self, _jd_ut):
        return 0.0

    def calc_ut(self, _jd_ut, _pid, _flags):
        with self._lock:
            self.calc_count += 1
            calc_count = self.calc_count
        if calc_count == 1:
            self.first_calc_entered.set()
            self.release_first_calc.wait(timeout=2)
        return ((0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0)


def test_compute_local_space_serializes_topocentric_swe_state(monkeypatch):
    fake_swe = _BlockingSwe()
    monkeypatch.setattr(local_space_module, "swe", fake_swe)

    errors = []

    def run_compute(lon, planet):
        try:
            local_space_module.compute_local_space(
                "2026-03-22T06:32:00+00:00",
                31.778,
                lon,
                [planet],
            )
        except Exception as exc:  # pragma: no cover - assertion aid
            errors.append(exc)

    first = threading.Thread(target=run_compute, args=(35.235, "Sun"))
    first.start()
    assert fake_swe.first_calc_entered.wait(timeout=1)

    second = threading.Thread(target=run_compute, args=(-115.1398, "Moon"))
    second.start()
    time.sleep(0.05)

    set_calls_before_release = [
        call for call in fake_swe.calls if call[0] == "set_topo"
    ]
    assert len(set_calls_before_release) == 1

    fake_swe.release_first_calc.set()
    first.join(timeout=1)
    second.join(timeout=1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert not errors
    assert [call for call in fake_swe.calls if call[0] == "set_topo"] == [
        ("set_topo", 35.235, 31.778, 0.0),
        ("set_topo", 0.0, 0.0, 0.0),
        ("set_topo", -115.1398, 31.778, 0.0),
        ("set_topo", 0.0, 0.0, 0.0),
    ]
