import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_INCLUDE = (
    REPO_ROOT / "frontend" / "build-resources" / "installer.nsh"
)


def test_installer_migrates_legacy_310_without_updated_rollback():
    source = INSTALLER_INCLUDE.read_text(encoding="utf-8")

    assert "!macro customInit" in source
    assert "!macro customCheckAppRunning" in source
    assert "!insertmacro _CHECK_APP_RUNNING" in source
    assert '"3.1.0"' in source
    assert '"${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"' in source
    assert '"${INSTALL_REGISTRY_KEY}" "InstallLocation"' in source
    assert 'ReadRegStr $voxLegacyVersion HKLM' in source
    assert 'ReadRegStr $voxLegacyVersion HKCU' in source
    assert "${If} ${UAC_IsAdmin}" in source
    assert '$installMode == "CurrentUser"' in source
    assert 'SHELL_CONTEXT "/currentuser"' in source
    assert 'HKEY_CURRENT_USER "/currentuser"' not in source
    assert "/KEEP_APP_DATA" in source
    assert "--updated" not in _active_nsis_lines(source)
    assert '${FileExists} "$voxLegacyInstallDir\\*.*"' in source
    assert "SetErrorLevel 1603" in source
    assert "Your license and saved charts will be kept." in source

    check_macro = source[source.index("!macro customCheckAppRunning") :]
    elevated_recheck = check_macro.index("${If} ${UAC_IsAdmin}")
    unelevated_migration = check_macro.index(
        '${ElseIf} $installMode == "CurrentUser"'
    )
    assert elevated_recheck < unelevated_migration


def test_installer_include_is_auto_discovered_and_uninstall_preserves_app_data():
    package = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )

    assert package["build"]["directories"]["buildResources"] == "build-resources"
    assert package["build"]["nsis"]["deleteAppDataOnUninstall"] is False
    assert INSTALLER_INCLUDE.is_file()


def _active_nsis_lines(source: str) -> str:
    return "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith(";")
    )
