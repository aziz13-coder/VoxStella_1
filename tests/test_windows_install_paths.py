from pathlib import Path, PureWindowsPath
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_windows_install_paths import (  # noqa: E402
    DEFAULT_RELEASE_PATH_LIMIT,
    DEFAULT_WINDOWS_INSTALL_ROOT,
    WINDOWS_MAX_PATH_CHARS,
    WINDOWS_PATH_HEADROOM_CHARS,
    evaluate_projected_paths,
    project_windows_path,
)


def test_project_windows_path_uses_conservative_default_profile():
    projected = project_windows_path(r"resources\app.asar")

    assert str(DEFAULT_WINDOWS_INSTALL_ROOT).startswith(
        r"C:\Users\VoxStellaReleaseUser"
    )
    assert projected.projected_path.endswith(r"resources\app.asar")
    assert projected.length == len(projected.projected_path)


def test_release_gate_reports_projected_max_path_violation():
    too_long = PureWindowsPath("resources", "backend", "x" * 210)

    violations, longest = evaluate_projected_paths([r"resources\app.asar", too_long])

    assert longest is not None
    assert longest.length > DEFAULT_RELEASE_PATH_LIMIT
    assert violations == [longest]


def test_release_gate_accepts_short_packaged_paths():
    relative_paths = [
        r"Vox Stella.exe",
        r"resources\app.asar",
        r"resources\backend\runtime\horary_backend\_internal\tc\chunk_index.jsonl",
    ]

    violations, longest = evaluate_projected_paths(relative_paths)

    assert violations == []
    assert longest is not None
    assert longest.length <= DEFAULT_RELEASE_PATH_LIMIT


def test_release_gate_reserves_explicit_windows_path_headroom():
    assert WINDOWS_MAX_PATH_CHARS == 259
    assert WINDOWS_PATH_HEADROOM_CHARS == 12
    assert DEFAULT_RELEASE_PATH_LIMIT == 247
    assert DEFAULT_RELEASE_PATH_LIMIT + WINDOWS_PATH_HEADROOM_CHARS == (
        WINDOWS_MAX_PATH_CHARS
    )


def test_package_workflow_runs_path_gate_before_nsis_build():
    package_script = (
        Path(__file__).resolve().parents[1] / "package-app-new.bat"
    ).read_text(encoding="utf-8")
    gate_command = "check_windows_install_paths.py --unpacked-root dist-electron\\win-unpacked"
    nsis_command = "npx electron-builder --win nsis --publish never"

    assert gate_command in package_script
    assert package_script.index(gate_command) < package_script.index(nsis_command)


@pytest.mark.parametrize(
    "relative_path",
    [r"C:\absolute\file.txt", r"..\outside.txt"],
)
def test_release_gate_rejects_unsafe_relative_paths(relative_path):
    with pytest.raises(ValueError):
        project_windows_path(relative_path)
