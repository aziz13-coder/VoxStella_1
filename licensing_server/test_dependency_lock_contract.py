import re
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parent
DIRECT_REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)(?P<extra>\[[^\]]+\])?==(?P<version>[^\s;]+)$"
)
LOCK_REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;\\]+)(?:\s*;.*)?\s*\\?$"
)


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_lock_contains_every_direct_pin_and_hashes_every_locked_package():
    direct_lines = [
        line.strip()
        for line in (SERVER_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    lock_lines = (SERVER_DIR / "requirements-lock.txt").read_text(encoding="utf-8").splitlines()

    direct_pins = {}
    for line in direct_lines:
        match = DIRECT_REQUIREMENT_RE.fullmatch(line)
        assert match, f"Direct requirement must be an exact pin: {line}"
        direct_pins[_normalized(match.group("name"))] = match.group("version")

    locked_pins = {}
    current_package = None
    hashed_packages = set()
    for line in lock_lines:
        match = LOCK_REQUIREMENT_RE.match(line)
        if match:
            current_package = _normalized(match.group("name"))
            locked_pins[current_package] = match.group("version")
        elif "--hash=sha256:" in line and current_package:
            hashed_packages.add(current_package)

    assert direct_pins.items() <= locked_pins.items()
    assert locked_pins
    assert set(locked_pins) == hashed_packages


def test_local_setup_paths_enforce_the_hash_lock():
    for relative_path in ("run-licensing-server.bat", "generate_keys.bat"):
        content = (SERVER_DIR / relative_path).read_text(encoding="utf-8")
        assert "--require-hashes requirements-lock.txt" in content
        assert "pip install -r requirements.txt" not in content
        assert "uv venv --python 3.12 .venv" in content
        assert "|| (" not in content


def test_server_launcher_fails_closed_and_reports_success_explicitly():
    content = (SERVER_DIR / "run-licensing-server.bat").read_text(encoding="utf-8")
    assert 'set "EXIT_CODE=1"' in content
    assert 'set "EXIT_CODE=0"' in content
    assert "endlocal & exit /b %EXIT_CODE%" in content
    assert content.index('set "EXIT_CODE=0"') > content.index("[DONE] Licensing server is running.")
