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
    assert 'ReadRegStr $voxLegacyVersion HKCU' in source
    assert "${If} ${UAC_IsAdmin}" in source
    assert '$installMode == "CurrentUser"' in source
    assert 'SHELL_CONTEXT "/currentuser"' in source
    assert "VoxStellaRemoveLegacy310 HKEY_CURRENT_USER" not in source
    assert "/KEEP_APP_DATA" in source
    assert "--updated" not in _active_nsis_lines(source)
    assert '${FileExists} "$voxLegacyInstallDir\\*.*"' not in source
    assert "SetErrorLevel 1603" in source
    assert "Your license, saved charts, and preferences will be kept." in source
    assert "machine-wide installation requires manual removal" not in source

    check_macro = source[source.index("!macro customCheckAppRunning") :]
    elevated_recheck = check_macro.index("${If} ${UAC_IsAdmin}")
    unelevated_migration = check_macro.index(
        '${ElseIf} $installMode == "CurrentUser"'
    )
    assert elevated_recheck < unelevated_migration


def test_installer_retries_failed_atomic_upgrade_without_updated_rollback():
    source = INSTALLER_INCLUDE.read_text(encoding="utf-8")

    assert "!macro VoxStellaRetryFailedUpgradeRemoval ROOT_KEY MODE_FLAG" in source
    assert "!macro customUnInstallCheck" in source
    assert "!macro customUnInstallCheckCurrentUser" in source
    assert (
        '!insertmacro readReg $voxFallbackInstallDir "${ROOT_KEY}" '
        '"${INSTALL_REGISTRY_KEY}" "InstallLocation"'
        in source
    )
    assert (
        '!insertmacro readReg $voxFallbackUninstallString "${ROOT_KEY}" '
        '"${UNINSTALL_REGISTRY_KEY}" "UninstallString"'
        in source
    )
    assert "$installationDir" not in source
    assert "$uninstallerFileName" not in source
    assert "vox-stella-fallback-uninstaller.exe" in source
    assert (
        "Retrying removal of Vox Stella $voxFallbackVersion without the long rollback path"
        in source
    )
    assert (
        'ExecWait \'"$voxFallbackTempUninstaller" /S /KEEP_APP_DATA '
        '${MODE_FLAG} _?=$voxFallbackInstallDir\''
        in source
    )
    assert (
        '${FileExists} "$voxFallbackInstallDir\\${APP_EXECUTABLE_FILENAME}"'
        in source
    )
    assert "ClearErrors\n    StrCpy $R0 0" in source
    assert "--updated" not in _active_nsis_lines(source)


def test_elevated_per_user_upgrade_tells_user_to_rerun_normally():
    source = INSTALLER_INCLUDE.read_text(encoding="utf-8")

    assert "!macro VoxStellaElevatedPerUserUpgradeFailure" in source
    assert "setup is running as administrator" in source
    assert "run the installer normally (do not choose Run as administrator)" in source
    assert "You do not need to uninstall the app first." in source


def test_installer_include_is_auto_discovered_and_uninstall_preserves_app_data():
    package = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )

    assert package["build"]["directories"]["buildResources"] == "build-resources"
    assert package["build"]["nsis"]["deleteAppDataOnUninstall"] is False
    assert (
        package["build"]["nsis"]["guid"]
        == "c7765e19-78c9-5b2a-a935-14614127ff63"
    )
    assert INSTALLER_INCLUDE.is_file()


def _active_nsis_lines(source: str) -> str:
    return "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith(";")
    )
