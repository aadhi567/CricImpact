@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Cricket Batter Contribution Analytics - One-Command Startup (start.bat)
:: ============================================================================

:: 1. Navigate to project root
cd /d "%~dp0"

:: Handle help arguments
if "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help
if "%~1"=="/?" goto :help

:: 2. Pre-flight Checks

:: Check Python virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ======================================================================
    echo  [ERROR] Python virtual environment not found at .venv\
    echo ======================================================================
    echo  The FastAPI backend requires the project's Python environment.
    echo.
    echo  To set it up, run:
    echo    python -m venv .venv
    echo    .\.venv\Scripts\pip install -r requirements.txt
    echo ======================================================================
    echo.
    goto :pause_and_exit
)

:: Check Python dependencies [fastapi, uvicorn]
".venv\Scripts\python.exe" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo  [ERROR] Required Python packages [fastapi, uvicorn] are missing!
    echo ======================================================================
    echo  Please install dependencies in the virtual environment:
    echo    .\.venv\Scripts\pip install -r requirements.txt
    echo ======================================================================
    echo.
    goto :pause_and_exit
)

:: Check Node.js and npm
where npm >nul 2>nul
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo  [ERROR] Node.js / npm not found in system PATH!
    echo ======================================================================
    echo  Node.js is required to run the React/Vite frontend development server.
    echo  Please install Node.js from https://nodejs.org/ and restart your shell.
    echo ======================================================================
    echo.
    goto :pause_and_exit
)

:: Check frontend directory and package.json
if not exist "frontend\package.json" (
    echo.
    echo ======================================================================
    echo  [ERROR] Frontend directory or package.json not found!
    echo ======================================================================
    echo  Expected: %~dp0frontend\package.json
    echo  Please ensure start.bat is run from the project root.
    echo ======================================================================
    echo.
    goto :pause_and_exit
)

:: Check frontend dependencies [node_modules]
if not exist "frontend\node_modules" (
    echo.
    echo ======================================================================
    echo  [ERROR] Frontend dependencies are missing [node_modules not found]!
    echo ======================================================================
    echo  Please install frontend dependencies by running:
    echo    cd frontend
    echo    npm install
    echo ======================================================================
    echo.
    goto :pause_and_exit
)

:: 3. Launch servers via PowerShell launcher with PID tracking and health verification
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_servers.ps1" %*
exit /b %ERRORLEVEL%

:help
echo.
echo Cricket Batter Contribution Analytics - Startup Launcher
echo.
echo Usage:
echo   start.bat           Start both Backend and Frontend servers
echo   start.bat --help    Display this help message
echo.
echo Servers started:
echo   Backend API:   http://127.0.0.1:8000  (FastAPI / Uvicorn)
echo   Frontend App:  http://localhost:5173/ (React / Vite)
echo.
echo To stop servers:
echo   stop.bat
echo.
exit /b 0

:pause_and_exit
pause
exit /b 1
