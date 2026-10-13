# scripts/start_servers.ps1
# Helper script to launch FastAPI backend and React/Vite frontend in separate windows with PID tracking

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

$projectRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $projectRoot

function Test-IsLaunchedFromExplorer {
    try {
        $myPid = $PID
        $parentPid = (Get-CimInstance Win32_Process -Filter "ProcessId = $myPid").ParentProcessId
        $grandParentPid = (Get-CimInstance Win32_Process -Filter "ProcessId = $parentPid").ParentProcessId
        $parentName = (Get-Process -Id $parentPid -ErrorAction SilentlyContinue).ProcessName
        $grandParentName = (Get-Process -Id $grandParentPid -ErrorAction SilentlyContinue).ProcessName
        if ($parentName -eq "explorer" -or $grandParentName -eq "explorer") {
            return $true
        }
    } catch {}
    return $false
}

function Start-TerminalProcess {
    param(
        [string]$Title,
        [string]$Command,
        [string]$WorkingDirectory
    )

    $fullCmd = "cmd.exe /k title $Title && $Command"
    try {
        $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
            CommandLine = $fullCmd
            CurrentDirectory = $WorkingDirectory
        }
        if ($result.ReturnValue -eq 0 -and $result.ProcessId) {
            return $result.ProcessId
        }
    } catch {}

    # Fallback to Start-Process
    $proc = Start-Process cmd.exe -WorkingDirectory $WorkingDirectory -ArgumentList '/k', "title $Title && $Command" -PassThru
    return $proc.Id
}

$pidsDir = Join-Path $projectRoot ".run"
if (-not (Test-Path $pidsDir)) {
    New-Item -ItemType Directory -Path $pidsDir -Force | Out-Null
}

$backendPidFile = Join-Path $pidsDir "backend.pid"
$frontendPidFile = Join-Path $pidsDir "frontend.pid"
$metaFile = Join-Path $pidsDir "servers.json"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   Cricket Batter Contribution Analytics - Startup Launcher" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if servers are already running according to tracked PIDs
if (Test-Path $backendPidFile) {
    $existingBackendPid = (Get-Content $backendPidFile -ErrorAction SilentlyContinue | Out-String).Trim()
    if ($existingBackendPid -and (Get-Process -Id $existingBackendPid -ErrorAction SilentlyContinue)) {
        Write-Host "[WARNING] Backend is already running (PID: $existingBackendPid)." -ForegroundColor Yellow
        Write-Host "To stop the current servers, run: .\stop.bat" -ForegroundColor Yellow
        Write-Host ""
        if (Test-IsLaunchedFromExplorer) {
            Write-Host "Press any key to exit..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        exit 1
    }
}

if (Test-Path $frontendPidFile) {
    $existingFrontendPid = (Get-Content $frontendPidFile -ErrorAction SilentlyContinue | Out-String).Trim()
    if ($existingFrontendPid -and (Get-Process -Id $existingFrontendPid -ErrorAction SilentlyContinue)) {
        Write-Host "[WARNING] Frontend is already running (PID: $existingFrontendPid)." -ForegroundColor Yellow
        Write-Host "To stop the current servers, run: .\stop.bat" -ForegroundColor Yellow
        Write-Host ""
        if (Test-IsLaunchedFromExplorer) {
            Write-Host "Press any key to exit..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        exit 1
    }
}

# 2. Check if ports 8000 or 5173 are already bound by any process
$port8000Conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000Conns) {
    $ownerPid = $port8000Conns[0].OwningProcess
    $ownerProc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
    $ownerName = if ($ownerProc) { $ownerProc.ProcessName } else { "Unknown" }
    Write-Host "[ERROR] Port 8000 is already in use by process '$ownerName' (PID: $ownerPid)!" -ForegroundColor Red
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - If this is a previously started backend, run: .\stop.bat" -ForegroundColor Yellow
    Write-Host "  - Or terminate PID $ownerPid before restarting." -ForegroundColor Yellow
    Write-Host ""
    if (Test-IsLaunchedFromExplorer) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit 1
}

$port5173Conns = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port5173Conns) {
    $ownerPid = $port5173Conns[0].OwningProcess
    $ownerProc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
    $ownerName = if ($ownerProc) { $ownerProc.ProcessName } else { "Unknown" }
    Write-Host "[ERROR] Port 5173 is already in use by process '$ownerName' (PID: $ownerPid)!" -ForegroundColor Red
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - If this is a previously started frontend, run: .\stop.bat" -ForegroundColor Yellow
    Write-Host "  - Or terminate PID $ownerPid before restarting." -ForegroundColor Yellow
    Write-Host ""
    if (Test-IsLaunchedFromExplorer) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit 1
}

# 3. Launch Backend in a separate terminal window
Write-Host "[1/3] Launching FastAPI backend server on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$backendCmd = ".\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
$backendPid = Start-TerminalProcess -Title "Cricket Analytics - Backend API" -Command $backendCmd -WorkingDirectory $projectRoot

if ($backendPid) {
    $backendPid | Out-File -FilePath $backendPidFile -Encoding ascii -Force
    Write-Host "      Backend window launched (PID: $backendPid)." -ForegroundColor Gray
} else {
    Write-Host "[ERROR] Failed to start backend server." -ForegroundColor Red
    if (Test-IsLaunchedFromExplorer) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit 1
}

# 4. Launch Frontend in a separate terminal window
Write-Host "[2/3] Launching React/Vite frontend server on http://localhost:5173/ ..." -ForegroundColor Cyan
$frontendDir = Join-Path $projectRoot "frontend"
$frontendCmd = "npm run dev -- --host 127.0.0.1"
$frontendPid = Start-TerminalProcess -Title "Cricket Analytics - Frontend" -Command $frontendCmd -WorkingDirectory $frontendDir

if ($frontendPid) {
    $frontendPid | Out-File -FilePath $frontendPidFile -Encoding ascii -Force
    Write-Host "      Frontend window launched (PID: $frontendPid)." -ForegroundColor Gray
} else {
    Write-Host "[ERROR] Failed to start frontend server." -ForegroundColor Red
    if (Test-IsLaunchedFromExplorer) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit 1
}

# Save servers metadata
$metadata = @{
    backend_pid = $backendPid
    frontend_pid = $frontendPid
    backend_url = "http://127.0.0.1:8000"
    frontend_url = "http://localhost:5173/"
    backend_port = 8000
    frontend_port = 5173
    started_at = (Get-Date).ToString("o")
}
$metadata | ConvertTo-Json | Out-File -FilePath $metaFile -Encoding utf8 -Force

# 5. Wait for servers to become available
Write-Host "[3/3] Verifying server health and connectivity..." -ForegroundColor Cyan
$backendReady = $false
$frontendReady = $false
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$maxWaitSec = 20

while ($stopwatch.Elapsed.TotalSeconds -lt $maxWaitSec) {
    Start-Sleep -Milliseconds 600

    if (-not $backendReady) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 1 -ErrorAction Stop
            if ($health.status -eq "healthy") {
                $backendReady = $true
                Write-Host "      [+] Backend is responding and healthy." -ForegroundColor Green
            }
        } catch {}
    }

    if (-not $frontendReady) {
        try {
            $feResponse = Invoke-WebRequest -Uri "http://localhost:5173/" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            if ($feResponse.StatusCode -eq 200) {
                $frontendReady = $true
                Write-Host "      [+] Frontend Vite development server is ready." -ForegroundColor Green
            }
        } catch {
            try {
                $feResponse2 = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
                if ($feResponse2.StatusCode -eq 200) {
                    $frontendReady = $true
                    Write-Host "      [+] Frontend Vite development server is ready." -ForegroundColor Green
                }
            } catch {}
        }
    }

    if ($backendReady -and $frontendReady) {
        break
    }
}

if (-not $backendReady) {
    Write-Host "      [!] Backend did not respond on http://127.0.0.1:8000 within ${maxWaitSec}s." -ForegroundColor Yellow
    Write-Host "          Check the 'Cricket Analytics - Backend API' window for error messages." -ForegroundColor Yellow
}

if (-not $frontendReady) {
    Write-Host "      [!] Frontend did not respond on http://localhost:5173/ within ${maxWaitSec}s." -ForegroundColor Yellow
    Write-Host "          Check the 'Cricket Analytics - Frontend' window for error messages." -ForegroundColor Yellow
}

# 6. Display complete status banner with URLs
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "   CRICKET CONTRIBUTION ANALYTICS - APPLICATION READY" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "   Frontend Application:  http://localhost:5173/" -ForegroundColor Cyan
Write-Host "   Backend API:           http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   Interactive API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "   Health Check:          http://127.0.0.1:8000/api/health" -ForegroundColor Gray
Write-Host ""
Write-Host "------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "   Window & Logging Information:" -ForegroundColor White
Write-Host "   * Backend PID: $backendPid ('Cricket Analytics - Backend API')" -ForegroundColor Gray
Write-Host "   * Frontend PID: $frontendPid ('Cricket Analytics - Frontend')" -ForegroundColor Gray
Write-Host "   * Both servers run in separate terminal windows to preserve live logs." -ForegroundColor Gray
Write-Host "   * Closing or restarting one window will not affect the other." -ForegroundColor Gray
Write-Host ""
Write-Host "   How to Stop:" -ForegroundColor White
Write-Host "   * Run 'stop.bat' or '.\stop.bat' in the project root to stop both servers." -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

if (Test-IsLaunchedFromExplorer) {
    Write-Host "Press any key to close this launcher window (servers will remain active)..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

exit 0
