#!/usr/bin/env bash
# ==============================================================================
# CricImpact - Automated Match Updater Scheduled Execution Script (POSIX/Linux)
# Suitable for cron, systemd timers, or cloud worker jobs (e.g. Render Cron Jobs)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Activate virtualenv if present
if [ -d ".venv" ]; then
    PYTHON_EXE="${PROJECT_ROOT}/.venv/bin/python"
elif [ -d "venv" ]; then
    PYTHON_EXE="${PROJECT_ROOT}/venv/bin/python"
else
    PYTHON_EXE="python3"
fi

mkdir -p logs
LOG_FILE="logs/match_updater.log"

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting CricImpact Automated Match Update..." | tee -a "${LOG_FILE}"

if "${PYTHON_EXE}" scripts/automatic_match_updater.py --competition t20i "$@" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Automated Match Update completed successfully." | tee -a "${LOG_FILE}"
    exit 0
else
    EXIT_CODE=$?
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Automated Match Update failed with exit code ${EXIT_CODE}. Check ${LOG_FILE}" | tee -a "${LOG_FILE}" >&2
    exit "${EXIT_CODE}"
fi
