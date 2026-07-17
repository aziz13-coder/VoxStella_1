from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from swisseph_state import (
    swisseph_ephemeris_path,
    swisseph_topocentric,
    synchronized_swisseph,
)


AMBIENT_STATE_MUTATORS = {
    "set_delta_t_userdef",
    "set_ephe_path",
    "set_jpl_file",
    "set_sid_mode",
    "set_tid_acc",
    "set_topo",
}


def test_synchronized_facades_share_one_process_lock():
    first_entered = threading.Event()
    second_entered = threading.Event()
    release_first = threading.Event()

    class BlockingSwe:
        def calc_ut(self, label):
            if label == "first":
                first_entered.set()
                assert release_first.wait(timeout=2.0)
            else:
                second_entered.set()
            return label

    raw = BlockingSwe()
    first_api = synchronized_swisseph(raw)
    second_api = synchronized_swisseph(raw)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(first_api.calc_ut, "first")
        assert first_entered.wait(timeout=1.0)
        second = executor.submit(second_api.calc_ut, "second")
        assert not second_entered.wait(timeout=0.05)
        release_first.set()
        assert first.result(timeout=1.0) == "first"
        assert second.result(timeout=1.0) == "second"


def test_ephemeris_path_transactions_are_nested_and_restore_state():
    class FakeSwe:
        Error = ValueError

        def __init__(self):
            self.path = ""
            self.paths = []

        def set_ephe_path(self, path):
            self.path = path
            self.paths.append(path)

        def calc_ut(self):
            return self.path

    raw = FakeSwe()
    api = synchronized_swisseph(raw)

    assert api.Error is ValueError
    with swisseph_ephemeris_path("outer", swe_module=api):
        assert api.calc_ut() == "outer"
        with swisseph_ephemeris_path("inner", swe_module=api):
            assert api.calc_ut() == "inner"
        assert api.calc_ut() == "outer"

    assert api.calc_ut() == ""
    assert raw.paths == ["outer", "inner", "outer", ""]


def test_topocentric_transactions_restore_the_outer_observer():
    class FakeSwe:
        def __init__(self):
            self.observer = (0.0, 0.0, 0.0)

        def set_topo(self, longitude, latitude, altitude):
            self.observer = (longitude, latitude, altitude)

        def calc_ut(self):
            return self.observer

    raw = FakeSwe()
    api = synchronized_swisseph(raw)

    with swisseph_topocentric(35.2, 31.8, 10.0, swe_module=api):
        assert api.calc_ut() == (35.2, 31.8, 10.0)
        with swisseph_topocentric(-74.0, 40.7, 5.0, swe_module=api):
            assert api.calc_ut() == (-74.0, 40.7, 5.0)
        assert api.calc_ut() == (35.2, 31.8, 10.0)

    assert api.calc_ut() == (0.0, 0.0, 0.0)


def test_canonical_backend_cannot_bypass_the_synchronized_boundary():
    direct_imports = []
    direct_mutators = []

    for path in sorted(BACKEND_DIR.rglob("*.py")):
        if (
            path.name.startswith("test_")
            or path.name == "swisseph_state.py"
            or "build" in path.parts
            or any(part.lower().endswith("venv") for part in path.parts)
            or "site-packages" in path.parts
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "swisseph":
                        direct_imports.append(f"{path.relative_to(BACKEND_DIR)}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom) and node.module == "swisseph":
                direct_imports.append(f"{path.relative_to(BACKEND_DIR)}:{node.lineno}")
            elif (
                isinstance(node, ast.Call)
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "swisseph"
                and (
                    (isinstance(node.func, ast.Name) and node.func.id == "__import__")
                    or (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "import_module"
                    )
                )
            ):
                direct_imports.append(f"{path.relative_to(BACKEND_DIR)}:{node.lineno}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in AMBIENT_STATE_MUTATORS
            ):
                direct_mutators.append(
                    f"{path.relative_to(BACKEND_DIR)}:{node.lineno}:{node.func.attr}"
                )

    assert direct_imports == []
    assert direct_mutators == []
