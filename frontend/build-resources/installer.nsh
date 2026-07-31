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
  Var voxFallbackNeeded
  Var voxFallbackVersion
  Var voxFallbackInstallDir
  Var voxFallbackUninstallString
  Var voxFallbackUninstaller
  Var voxFallbackTempUninstaller
  Var voxFallbackResult
  Var voxFallbackRemainingInstallDir
!endif

!macro VoxStellaUpgradeFailure REASON
  DetailPrint "Vox Stella upgrade removal failed: ${REASON}"
  MessageBox MB_OK|MB_ICONEXCLAMATION|MB_TOPMOST \
    "The installed Vox Stella version could not be removed automatically.$\r$\n$\r$\nClose Vox Stella and run this installer again. If the problem continues, uninstall Vox Stella from Windows Settings > Apps > Installed apps, then rerun setup. Your license, saved charts, and preferences will be kept." \
    /SD IDOK
  SetErrorLevel 1603
  Quit
!macroend

!macro VoxStellaElevatedPerUserUpgradeFailure
  DetailPrint "A per-user Vox Stella installation cannot be upgraded by an elevated setup process."
  MessageBox MB_OK|MB_ICONEXCLAMATION|MB_TOPMOST \
    "Vox Stella is installed only for your Windows account, but setup is running as administrator.$\r$\n$\r$\nClose setup and run the installer normally (do not choose Run as administrator). You do not need to uninstall the app first." \
    /SD IDOK
  SetErrorLevel 1603
  Quit
!macroend

!macro VoxStellaRemoveLegacy310 ROOT_KEY MODE_FLAG
  !insertmacro readReg $voxLegacyVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"

  ${If} $voxLegacyVersion == "3.1.0"
    !insertmacro readReg $voxLegacyInstallDir "${ROOT_KEY}" "${INSTALL_REGISTRY_KEY}" "InstallLocation"

    ${If} $voxLegacyInstallDir == ""
      !insertmacro VoxStellaUpgradeFailure "the registered installation directory is missing"
    ${EndIf}

    StrCpy $voxLegacyUninstaller "$voxLegacyInstallDir\${UNINSTALL_FILENAME}"
    ${IfNot} ${FileExists} "$voxLegacyUninstaller"
      !insertmacro VoxStellaUpgradeFailure "the registered uninstaller is missing"
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
      !insertmacro VoxStellaUpgradeFailure "the legacy uninstaller could not be staged"
    ${EndIf}

    DetailPrint "Preparing Vox Stella 3.1.0 for an in-place upgrade..."
    ClearErrors
    ExecWait '"$voxLegacyTempUninstaller" /S /KEEP_APP_DATA ${MODE_FLAG} _?=$voxLegacyInstallDir' $voxLegacyUninstallResult
    ${If} ${Errors}
      !insertmacro VoxStellaUpgradeFailure "the legacy uninstaller could not be started"
    ${EndIf}
    ${If} $voxLegacyUninstallResult != 0
      !insertmacro VoxStellaUpgradeFailure "the legacy uninstaller returned $voxLegacyUninstallResult"
    ${EndIf}

    ; Do not let the standard update path retry an incompletely removed 3.1.0.
    !insertmacro readReg $voxLegacyVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ${If} $voxLegacyVersion != ""
      !insertmacro VoxStellaUpgradeFailure "the legacy uninstall registration is still present"
    ${EndIf}
    !insertmacro readReg $voxLegacyInstallDir "${ROOT_KEY}" "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    ${If} $voxLegacyInstallDir != ""
      !insertmacro VoxStellaUpgradeFailure "the legacy install registration is still present"
    ${EndIf}
  ${EndIf}
!macroend

; electron-builder normally removes an old version transactionally with
; --updated. That preserves rollback and remains the first choice. Some older
; Vox Stella payloads contain paths that fit in the install directory but exceed
; legacy MAX_PATH after electron-builder adds $PLUGINSDIR\old-install. When that
; atomic removal fails, retry the registered uninstaller once without --updated,
; which is the same path used by a successful manual uninstall.
!macro VoxStellaRetryFailedUpgradeRemoval ROOT_KEY MODE_FLAG
  StrCpy $voxFallbackNeeded "0"
  ${If} ${Errors}
    StrCpy $voxFallbackNeeded "1"
  ${ElseIf} $R0 != 0
    StrCpy $voxFallbackNeeded "1"
  ${EndIf}

  ${If} $voxFallbackNeeded == "1"
    !insertmacro readReg $voxFallbackVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    !insertmacro readReg $voxFallbackInstallDir "${ROOT_KEY}" "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    !insertmacro readReg $voxFallbackUninstallString "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "UninstallString"
    StrCpy $voxFallbackUninstaller ""
    ${If} $voxFallbackUninstallString != ""
      !insertmacro GetInQuotes $voxFallbackUninstaller "$voxFallbackUninstallString"
    ${EndIf}

    ${If} $voxFallbackInstallDir == ""
      !insertmacro VoxStellaUpgradeFailure "the fallback installation directory is missing"
    ${EndIf}
    ${If} $voxFallbackUninstaller == ""
      !insertmacro VoxStellaUpgradeFailure "the fallback uninstaller path is missing"
    ${EndIf}
    ${IfNot} ${FileExists} "$voxFallbackUninstaller"
      !insertmacro VoxStellaUpgradeFailure "the fallback uninstaller is missing"
    ${EndIf}

    InitPluginsDir
    StrCpy $voxFallbackTempUninstaller "$PLUGINSDIR\vox-stella-fallback-uninstaller.exe"
    Delete "$voxFallbackTempUninstaller"
    ClearErrors
    CopyFiles /SILENT "$voxFallbackUninstaller" "$voxFallbackTempUninstaller"
    ${If} ${Errors}
      !insertmacro VoxStellaUpgradeFailure "the fallback uninstaller could not be staged"
    ${EndIf}

    DetailPrint "Retrying removal of Vox Stella $voxFallbackVersion without the long rollback path..."
    ClearErrors
    ExecWait '"$voxFallbackTempUninstaller" /S /KEEP_APP_DATA ${MODE_FLAG} _?=$voxFallbackInstallDir' $voxFallbackResult
    ${If} ${Errors}
      !insertmacro VoxStellaUpgradeFailure "the fallback uninstaller could not be started"
    ${EndIf}
    ${If} $voxFallbackResult != 0
      !insertmacro VoxStellaUpgradeFailure "the fallback uninstaller returned $voxFallbackResult"
    ${EndIf}

    !insertmacro readReg $voxFallbackVersion "${ROOT_KEY}" "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ${If} $voxFallbackVersion != ""
      !insertmacro VoxStellaUpgradeFailure "the old uninstall registration is still present after fallback"
    ${EndIf}
    !insertmacro readReg $voxFallbackRemainingInstallDir "${ROOT_KEY}" "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    ${If} $voxFallbackRemainingInstallDir != ""
      !insertmacro VoxStellaUpgradeFailure "the old install registration is still present after fallback"
    ${EndIf}
    ${If} ${FileExists} "$voxFallbackInstallDir\${APP_EXECUTABLE_FILENAME}"
      !insertmacro VoxStellaUpgradeFailure "the old application executable is still present after fallback"
    ${EndIf}

    ClearErrors
    StrCpy $R0 0
  ${EndIf}
!macroend

!macro customInit
  ; Never select an HKCU-registered executable for an already elevated token.
  ; A normal launch can upgrade the same per-user installation automatically.
  ${If} ${UAC_IsAdmin}
    ReadRegStr $voxLegacyVersion HKCU "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ${If} $voxLegacyVersion == "3.1.0"
      !insertmacro VoxStellaElevatedPerUserUpgradeFailure
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
        !insertmacro VoxStellaElevatedPerUserUpgradeFailure
      ${EndIf}
    ${ElseIf} $installMode == "CurrentUser"
      !insertmacro VoxStellaRemoveLegacy310 SHELL_CONTEXT "/currentuser"
    ${EndIf}
  !endif
!macroend

!macro customUnInstallCheck
  ${If} $installMode == "all"
    !insertmacro VoxStellaRetryFailedUpgradeRemoval SHELL_CONTEXT "/allusers"
  ${Else}
    !insertmacro VoxStellaRetryFailedUpgradeRemoval SHELL_CONTEXT "/currentuser"
  ${EndIf}
!macroend

!macro customUnInstallCheckCurrentUser
  !insertmacro VoxStellaRetryFailedUpgradeRemoval HKEY_CURRENT_USER "/currentuser"
!macroend
