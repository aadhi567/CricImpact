@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Cricket Batter Contribution Analytics - Stop Script (stop.bat)
:: ============================================================================

:: 1. Navigate to project root
cd /d "%~dp0"

:: Handle help arguments
if "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help
if "%~1"=="/?" goto :help

:: 2. Execute PowerShell stop script with process-tree cleanup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_servers.ps1" %*
exit /b %ERRORLEVEL%

:help
echo.
echo Cricket Batter Contribution Analytics - Stop Launcher
echo.
echo Usage:
echo   stop.bat           Stop both Backend and Frontend servers
echo   stop.bat --help    Display this help message
echo.
echo Stops the processes launched by start.bat using tracked PIDs.
echo Does not terminate unrelated Python or Node.js processes.
echo.
exit /b 0

:pause_and_exit
pause
exit /b 1
