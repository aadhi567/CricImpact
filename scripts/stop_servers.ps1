# scripts/stop_servers.ps1
# Helper script to safely terminate backend and frontend servers started by the launcher

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

$pidsDir = Join-Path $projectRoot ".run"
$backendPidFile = Join-Path $pidsDir "backend.pid"
$frontendPidFile = Join-Path $pidsDir "frontend.pid"
$metaFile = Join-Path $pidsDir "servers.json"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   Cricket Batter Contribution Analytics - Stopping Servers" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

$stoppedAny = $false

# 1. Stop Backend server from tracked PID
if (Test-Path $backendPidFile) {
    $backendPid = (Get-Content $backendPidFile -ErrorAction SilentlyContinue | Out-String).Trim()
    if ($backendPid) {
        $proc = Get-Process -Id $backendPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping Backend server window & child processes (PID: $backendPid)..." -ForegroundColor Yellow
            cmd /c "taskkill /PID $backendPid /T /F 2>nul"
            Write-Host "  [OK] Backend server stopped." -ForegroundColor Green
            $stoppedAny = $true
        } else {
            Write-Host "  [-] Backend server (PID: $backendPid) was already terminated." -ForegroundColor Gray
        }
    }
    Remove-Item -Path $backendPidFile -Force -ErrorAction SilentlyContinue
}

# 2. Stop Frontend server from tracked PID
if (Test-Path $frontendPidFile) {
    $frontendPid = (Get-Content $frontendPidFile -ErrorAction SilentlyContinue | Out-String).Trim()
    if ($frontendPid) {
        $proc = Get-Process -Id $frontendPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Stopping Frontend server window & child processes (PID: $frontendPid)..." -ForegroundColor Yellow
            cmd /c "taskkill /PID $frontendPid /T /F 2>nul"
            Write-Host "  [OK] Frontend server stopped." -ForegroundColor Green
            $stoppedAny = $true
        } else {
            Write-Host "  [-] Frontend server (PID: $frontendPid) was already terminated." -ForegroundColor Gray
        }
    }
    Remove-Item -Path $frontendPidFile -Force -ErrorAction SilentlyContinue
}

# 3. Clean up servers.json
if (Test-Path $metaFile) {
    Remove-Item -Path $metaFile -Force -ErrorAction SilentlyContinue
}

# 4. Fallback check: Verify if port 8000 or 5173 is still occupied by project-specific processes
Start-Sleep -Milliseconds 500

$port8000Conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000Conns) {
    $ownerPid = $port8000Conns[0].OwningProcess
    $ownerProc = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerPid" -ErrorAction SilentlyContinue
    if ($ownerProc -and ($ownerProc.CommandLine -match "app\.main:app" -or $ownerProc.CommandLine -match "contribution")) {
        Write-Host "Stopping lingering backend process on port 8000 (PID: $ownerPid)..." -ForegroundColor Yellow
        cmd /c "taskkill /PID $ownerPid /T /F 2>nul"
        Write-Host "  [OK] Freed port 8000." -ForegroundColor Green
        $stoppedAny = $true
    } else {
        # Check for child worker processes spawned by multiprocessing
        $workers = Get-CimInstance Win32_Process | Where-Object {
            $_.CommandLine -match "parent_pid=$ownerPid" -or
            ($_.CommandLine -match "app\.main:app" -and $_.CommandLine -match "contribution")
        }
        foreach ($worker in $workers) {
            Write-Host "Stopping lingering backend worker process (PID: $($worker.ProcessId))..." -ForegroundColor Yellow
            cmd /c "taskkill /PID $($worker.ProcessId) /T /F 2>nul"
            Write-Host "  [OK] Freed backend worker on port 8000." -ForegroundColor Green
            $stoppedAny = $true
        }
    }
}

$port5173Conns = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port5173Conns) {
    $ownerPid = $port5173Conns[0].OwningProcess
    $ownerProc = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerPid" -ErrorAction SilentlyContinue
    if ($ownerProc -and ($ownerProc.CommandLine -match "vite" -or $ownerProc.CommandLine -match "contribution")) {
        Write-Host "Stopping lingering frontend process on port 5173 (PID: $ownerPid)..." -ForegroundColor Yellow
        cmd /c "taskkill /PID $ownerPid /T /F 2>nul"
        Write-Host "  [OK] Freed port 5173." -ForegroundColor Green
        $stoppedAny = $true
    }
}

Write-Host ""
if ($stoppedAny) {
    Write-Host "========================================================================" -ForegroundColor Green
    Write-Host "   SUCCESS: All Cricket Analytics servers have been stopped." -ForegroundColor White
    Write-Host "========================================================================" -ForegroundColor Green
} else {
    Write-Host "========================================================================" -ForegroundColor Yellow
    Write-Host "   No active Cricket Analytics servers were running." -ForegroundColor White
    Write-Host "========================================================================" -ForegroundColor Yellow
}
Write-Host ""

if (Test-IsLaunchedFromExplorer) {
    Write-Host "Press any key to close this window..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

exit 0
