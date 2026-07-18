from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_API = REPO_ROOT / "backend" / "astro_clock_api.py"
MIRROR_API = REPO_ROOT / "frontend" / "backend" / "astro_clock_api.py"
CANONICAL_LOCAL_SPACE = REPO_ROOT / "backend" / "forensic" / "local_space.py"
MIRROR_LOCAL_SPACE = REPO_ROOT / "frontend" / "backend" / "forensic" / "local_space.py"
CANONICAL_SWISS_STATE = REPO_ROOT / "backend" / "swisseph_state.py"
MIRROR_SWISS_STATE = REPO_ROOT / "frontend" / "backend" / "swisseph_state.py"


def _function_node(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {path}")


def _function_dump(path: Path, name: str) -> str:
    return ast.dump(_function_node(path, name), include_attributes=False)


def _called_names(path: Path, name: str) -> set[str]:
    called: set[str] = set()
    for node in ast.walk(_function_node(path, name)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    return called


def test_mirror_compass_and_directional_routes_use_confirmed_snap_loader():
    for route_name in ("get_compass", "get_directional_3d"):
        assert _function_dump(CANONICAL_API, route_name) == _function_dump(
            MIRROR_API,
            route_name,
        )
        called = _called_names(MIRROR_API, route_name)
        assert "_data_for_optional_confirmed_snap" in called
        assert "_data_for_request_clock_context" not in called

    mirror_loader_calls = _called_names(
        MIRROR_API,
        "_data_for_optional_confirmed_snap",
    )
    assert "_require_confirmed_saved_snap_context" in mirror_loader_calls
    assert _function_dump(
        CANONICAL_API,
        "_saved_snap_context_blocking_reasons",
    ) == _function_dump(
        MIRROR_API,
        "_saved_snap_context_blocking_reasons",
    )
    assert _function_dump(
        CANONICAL_API,
        "_require_confirmed_saved_snap_context",
    ) == _function_dump(
        MIRROR_API,
        "_require_confirmed_saved_snap_context",
    )


def test_mirror_local_space_uses_the_same_state_safe_calculations():
    assert _function_dump(
        CANONICAL_LOCAL_SPACE,
        "compute_local_space",
    ) == _function_dump(
        MIRROR_LOCAL_SPACE,
        "compute_local_space",
    )
    assert _function_dump(
        CANONICAL_LOCAL_SPACE,
        "compute_local_space_diag",
    ) == _function_dump(
        MIRROR_LOCAL_SPACE,
        "compute_local_space_diag",
    )
    assert _function_dump(
        CANONICAL_SWISS_STATE,
        "swisseph_topocentric",
    ) == _function_dump(
        MIRROR_SWISS_STATE,
        "swisseph_topocentric",
    )


def test_mirror_topocentric_context_restores_previous_observer():
    spec = importlib.util.spec_from_file_location(
        "vox_stella_legacy_swisseph_state_test",
        MIRROR_SWISS_STATE,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class _FakeSwiss:
        def __init__(self):
            self.positions = []

        def set_topo(self, longitude, latitude, altitude):
            self.positions.append(
                (float(longitude), float(latitude), float(altitude))
            )

    fake = _FakeSwiss()
    synchronized = module.synchronized_swisseph(fake)
    synchronized.set_topo(2.0, 48.0, 15.0)

    with module.swisseph_topocentric(
        35.2,
        31.8,
        10.0,
        swe_module=synchronized,
    ):
        assert fake.positions[-1] == (35.2, 31.8, 10.0)

    assert fake.positions[-1] == (2.0, 48.0, 15.0)
