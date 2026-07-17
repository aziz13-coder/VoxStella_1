!include "LogicLib.nsh"
!include "getProcessInfo.nsh"

; Defining customCheckAppRunning makes electron-builder leave these declarations
; to this include. The built-in check is still called before legacy migration.
Var pid
!ifndef BUILD_UNINSTALLER
  Var voxLegacyVersion
  Var voxLegacyInstallDir
  Var voxLegacyUninstaller
  Var voxLegacyTempUninstaller
  Var voxLegacyUninstallResult
!endif

!macro VoxStellaLegacyUpgradeFailure REASON
  DetailPrint "Vox Stella 3.1.0 migration failed: ${REASON}"
  MessageBox MB_OK|MB_ICONEXCLAMATION|MB_TOPMOST \
    "Vox Stella 3.1.0 could not be removed automatically.$\r$\n$\r$\nUninstall Vox Stella 3.1.0 from Windows Settings > Apps > Installed apps, then run this installer again. Your license and saved charts will be kept." \
    /SD IDOK
  SetErrorLevel 1603
  Quit
!macroend

!macro VoxStellaRemoveLegacy310 ROOT_KEY MODE_FLAG
  !insertmacro readReg $voxLegacyVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"

  ${If} $voxLegacyVersion == "3.1.0"
    !insertmacro readReg $voxLegacyInstallDir "${ROOT_KEY}" "${INSTALL_REGISTRY_KEY}" "InstallLocation"

    ${If} $voxLegacyInstallDir == ""
      !insertmacro VoxStellaLegacyUpgradeFailure "the registered installation directory is missing"
    ${EndIf}

    StrCpy $voxLegacyUninstaller "$voxLegacyInstallDir\${UNINSTALL_FILENAME}"
    ${IfNot} ${FileExists} "$voxLegacyUninstaller"
      !insertmacro VoxStellaLegacyUpgradeFailure "the registered uninstaller is missing"
    ${EndIf}

    ; electron-builder normally passes --updated to the previous uninstaller.
    ; The 3.1.0 payload has paths that fit in-place but overflow the longer
    ; transactional rollback directory used only by --updated. Run that exact
    ; legacy uninstaller without --updated so it uses its normal removal path.
    ; No --delete-app-data flag is passed, and this application's uninstaller is
    ; configured not to delete AppData. The license, saved charts, and user
    ; preferences therefore stay outside this removal.
    InitPluginsDir
    StrCpy $voxLegacyTempUninstaller "$PLUGINSDIR\vox-stella-3.1.0-uninstaller.exe"
    Delete "$voxLegacyTempUninstaller"
    ClearErrors
    CopyFiles /SILENT "$voxLegacyUninstaller" "$voxLegacyTempUninstaller"
    ${If} ${Errors}
      !insertmacro VoxStellaLegacyUpgradeFailure "the legacy uninstaller could not be staged"
    ${EndIf}

    DetailPrint "Preparing Vox Stella 3.1.0 for an in-place upgrade..."
    ClearErrors
    ExecWait '"$voxLegacyTempUninstaller" /S /KEEP_APP_DATA ${MODE_FLAG} _?=$voxLegacyInstallDir' $voxLegacyUninstallResult
    ${If} ${Errors}
      !insertmacro VoxStellaLegacyUpgradeFailure "the legacy uninstaller could not be started"
    ${EndIf}
    ${If} $voxLegacyUninstallResult != 0
      !insertmacro VoxStellaLegacyUpgradeFailure "the legacy uninstaller returned $voxLegacyUninstallResult"
    ${EndIf}

    ; Do not let the standard update path retry an incompletely removed 3.1.0.
    !insertmacro readReg $voxLegacyVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ${If} $voxLegacyVersion == "3.1.0"
      !insertmacro VoxStellaLegacyUpgradeFailure "the legacy registration is still present"
    ${EndIf}
    ${If} ${FileExists} "$voxLegacyInstallDir\*.*"
      !insertmacro VoxStellaLegacyUpgradeFailure "the legacy installation directory is not empty"
    ${EndIf}
  ${EndIf}
!macroend

!macro customInit
  ; A machine-wide 3.1.0 must be removed by its administrator-owned
  ; uninstaller. Also refuse an elevated per-user migration: HKCU is writable
  ; by the standard user and must never select an executable for an admin token.
  ReadRegStr $voxLegacyVersion HKLM "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
  ${If} $voxLegacyVersion == "3.1.0"
    !insertmacro VoxStellaLegacyUpgradeFailure "the machine-wide installation requires manual removal"
  ${EndIf}

  ${If} ${UAC_IsAdmin}
    ReadRegStr $voxLegacyVersion HKCU "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ${If} $voxLegacyVersion == "3.1.0"
      !insertmacro VoxStellaLegacyUpgradeFailure "the per-user installation cannot be migrated from an elevated installer"
    ${EndIf}
  ${EndIf}
!macroend

!macro customCheckAppRunning
  ; Preserve electron-builder's normal close/kill handling for every version.
  !insertmacro IS_POWERSHELL_AVAILABLE
  !insertmacro _CHECK_APP_RUNNING

  !ifndef BUILD_UNINSTALLER
    ; Automatic migration is intentionally limited to the current unelevated
    ; user's own installation. customInit handles machine/elevated cases.
    ; Re-check here to close the wizard-time window after customInit.
    ${If} ${UAC_IsAdmin}
      ReadRegStr $voxLegacyVersion HKCU "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
      ${If} $voxLegacyVersion == "3.1.0"
        !insertmacro VoxStellaLegacyUpgradeFailure "the per-user installation cannot be migrated from an elevated installer"
      ${EndIf}
    ${ElseIf} $installMode == "CurrentUser"
      !insertmacro VoxStellaRemoveLegacy310 SHELL_CONTEXT "/currentuser"
    ${EndIf}
  !endif
!macroend
