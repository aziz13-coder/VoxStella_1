#!/usr/bin/env python3
"""Fail a release when projected Windows install paths exceed legacy MAX_PATH.

Electron-builder's per-user NSIS default is below LocalAppData. The conservative
profile name below is twenty characters long, which keeps the release gate
independent of the shorter account name on the build machine.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable, Sequence


WINDOWS_MAX_PATH_CHARS = 259
WINDOWS_PATH_HEADROOM_CHARS = 12
DEFAULT_RELEASE_PATH_LIMIT = WINDOWS_MAX_PATH_CHARS - WINDOWS_PATH_HEADROOM_CHARS
DEFAULT_WINDOWS_INSTALL_ROOT = PureWindowsPath(
    r"C:\Users\VoxStellaReleaseUser\AppData\Local\Programs\Vox Stella"
)


@dataclass(frozen=True)
class ProjectedPath:
    relative_path: str
    projected_path: str
    length: int


def project_windows_path(
    relative_path: str | Path,
    install_root: str | PureWindowsPath = DEFAULT_WINDOWS_INSTALL_ROOT,
) -> ProjectedPath:
    """Project one unpacked-app relative path below the NSIS install root."""
    relative = PureWindowsPath(str(relative_path))
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError(f"Expected a safe relative packaged path, got: {relative_path}")

    projected = PureWindowsPath(install_root).joinpath(relative)
    return ProjectedPath(
        relative_path=str(relative),
        projected_path=str(projected),
        length=len(str(projected)),
    )


def evaluate_projected_paths(
    relative_paths: Iterable[str | Path],
    *,
    install_root: str | PureWindowsPath = DEFAULT_WINDOWS_INSTALL_ROOT,
    max_path_chars: int = DEFAULT_RELEASE_PATH_LIMIT,
) -> tuple[list[ProjectedPath], ProjectedPath | None]:
    """Return over-limit paths and the longest projected path."""
    projected = [
        project_windows_path(relative_path, install_root)
        for relative_path in relative_paths
    ]
    projected.sort(key=lambda item: (-item.length, item.relative_path.lower()))
    violations = [item for item in projected if item.length > max_path_chars]
    return violations, projected[0] if projected else None


def scan_unpacked_app(
    unpacked_root: Path,
    *,
    install_root: str | PureWindowsPath = DEFAULT_WINDOWS_INSTALL_ROOT,
    max_path_chars: int = DEFAULT_RELEASE_PATH_LIMIT,
) -> tuple[list[ProjectedPath], ProjectedPath | None]:
    """Evaluate every file and directory shipped by an unpacked Electron app."""
    root = unpacked_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Unpacked Electron app is missing: {root}")

    relative_paths = [
        entry.relative_to(root)
        for entry in root.rglob("*")
        if entry.is_file() or entry.is_dir()
    ]
    return evaluate_projected_paths(
        relative_paths,
        install_root=install_root,
        max_path_chars=max_path_chars,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate projected default Windows installation paths."
    )
    parser.add_argument(
        "--unpacked-root",
        required=True,
        type=Path,
        help="Path to electron-builder's unpacked application directory.",
    )
    parser.add_argument(
        "--install-root",
        default=str(DEFAULT_WINDOWS_INSTALL_ROOT),
        help="Conservative NSIS installation root used for projection.",
    )
    parser.add_argument(
        "--max-path-chars",
        default=DEFAULT_RELEASE_PATH_LIMIT,
        type=int,
        help=(
            "Release path limit. The default is 247 characters, reserving "
            "12 visible characters below Windows' 259-character ceiling."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    violations, longest = scan_unpacked_app(
        args.unpacked_root,
        install_root=args.install_root,
        max_path_chars=args.max_path_chars,
    )

    if longest is None:
        print(f"[ERROR] Unpacked application is empty: {args.unpacked_root}")
        return 1

    print(
        "[path-gate] "
        f"install_root={args.install_root} "
        f"max_length={longest.length} "
        f"limit={args.max_path_chars}"
    )
    print(f"[path-gate] longest={longest.projected_path}")

    if not violations:
        print("[OK] All projected Windows install paths are within the safe limit.")
        return 0

    print(f"[ERROR] {len(violations)} projected install paths exceed the safe limit:")
    for item in violations[:20]:
        print(f"  - {item.length}: {item.projected_path}")
    if len(violations) > 20:
        print(f"  ... and {len(violations) - 20} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
