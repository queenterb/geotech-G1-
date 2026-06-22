#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

: ${CIS_DASHBOARD_SECRET:=ci_test_secret_local_01234567890123456789}
export CIS_DASHBOARD_SECRET

echo "Installing Python dependencies (may take a moment)..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r cis/requirements.txt Flask pytest >/dev/null

ALERTS_FILE="${TMPDIR:-/tmp}/cis_alerts.jsonl"
touch "$ALERTS_FILE"

echo "Starting CIS main detector in background..."
python -u -m cis.main_detector --alerts-file "$ALERTS_FILE" &
MAIN_PID=$!

echo "Starting CIS portal (Flask) in background..."
python -u -m cis.run_portal &
PORTAL_PID=$!

echo "Services started (main=$MAIN_PID, portal=$PORTAL_PID). Tailing $ALERTS_FILE"
tail -n 0 -f "$ALERTS_FILE"
