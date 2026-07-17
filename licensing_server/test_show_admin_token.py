from pathlib import Path

import pytest

from licensing_server import show_admin_token


def test_admin_token_environment_value_takes_precedence(tmp_path):
    token_file = tmp_path / "admin_token.txt"
    token_file.write_text("file-token", encoding="utf-8")

    token = show_admin_token.read_token(
        {
            "ADMIN_TOKEN": " environment-token ",
            "ADMIN_TOKEN_FILE": str(token_file),
            "LOCALAPPDATA": str(tmp_path),
        }
    )

    assert token == "environment-token"


def test_explicit_admin_token_file_is_used(tmp_path):
    token_file = tmp_path / "configured-token.txt"
    token_file.write_text(" configured-token \n", encoding="utf-8")

    token = show_admin_token.read_token(
        {
            "ADMIN_TOKEN_FILE": str(token_file),
            "LOCALAPPDATA": str(tmp_path / "other-local-app-data"),
        }
    )

    assert token == "configured-token"


def test_standalone_viewer_uses_launcher_canonical_token_file(tmp_path):
    token_file = (
        tmp_path
        / "VoxStella"
        / "licensing"
        / "admin_token.txt"
    )
    token_file.parent.mkdir(parents=True)
    token_file.write_text(" canonical-token \n", encoding="utf-8")

    assert show_admin_token.default_token_file(
        {"LOCALAPPDATA": str(tmp_path)}
    ) == token_file
    assert show_admin_token.read_token(
        {"LOCALAPPDATA": str(tmp_path)}
    ) == "canonical-token"


def test_missing_admin_token_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="admin token is not configured"):
        show_admin_token.read_token(
            {"LOCALAPPDATA": str(tmp_path)}
        )


def test_missing_local_app_data_fails_closed():
    assert show_admin_token.default_token_file({}) is None
    with pytest.raises(RuntimeError, match="admin token is not configured"):
        show_admin_token.read_token({})


def test_batch_wrapper_sets_launcher_token_path_and_propagates_failure():
    wrapper = Path(show_admin_token.__file__).with_name("show-admin-token.bat")
    source = wrapper.read_text(encoding="utf-8").lower()

    assert (
        r"%localappdata%\voxstella\licensing\admin_token.txt"
        in source
    )
    assert "exit /b %exit_code%" in source
