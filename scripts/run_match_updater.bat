@echo off
REM ==============================================================================
REM CricImpact - Automated Match Updater Scheduled Execution Script (Windows)
REM ==============================================================================
setlocal enabledelayedexpansion

REM Resolve project root directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

REM Detect Python executable (virtualenv or system)
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM Ensure logs directory exists
if not exist "logs" mkdir "logs"

echo [%DATE% %TIME%] Starting CricImpact Automated Match Update...
"%PYTHON_EXE%" scripts\automatic_match_updater.py --competition t20i %* >> logs\match_updater.log 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% equ 0 (
    echo [%DATE% %TIME%] Automated Match Update completed successfully.
) else (
    echo [%DATE% %TIME%] Automated Match Update finished with exit code %EXIT_CODE%. Check logs\match_updater.log
)

exit /b %EXIT_CODE%
