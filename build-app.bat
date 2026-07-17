@echo off
setlocal
echo [ERROR] build-app.bat is retired and must not be used for application packaging.
echo [INFO] Use the canonical source build from the repository root:
echo        package-app-new.bat
echo [INFO] That workflow enforces pinned runtimes, audits, tests, runtime staging, installer creation, and the packaged smoke test.
endlocal
exit /b 1
