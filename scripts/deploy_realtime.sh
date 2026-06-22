#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [ -f "$ROOT_DIR/.VENV/Scripts/python.exe" ]; then
  PYTHON="$ROOT_DIR/.VENV/Scripts/python.exe"
else
  echo ".venv Python not found. Activate or create a virtualenv at .venv/."
  exit 1
fi

: ${CIS_DASHBOARD_SECRET:=ci_test_secret_local_01234567890123456789}
export CIS_DASHBOARD_SECRET

ALERTS_FILE="${TMPDIR:-/tmp}/cis_alerts.jsonl"
touch "$ALERTS_FILE"

echo "Using Python: $PYTHON"
echo "Starting CIS main detector in background..."
$PYTHON -u -m cis.main_detector --alerts-file "$ALERTS_FILE" &
MAIN_PID=$!

echo "Starting CIS portal in background..."
$PYTHON -u -m cis.run_portal &
PORTAL_PID=$!

echo "Started detector PID=$MAIN_PID and portal PID=$PORTAL_PID"
echo "Tailing alerts file: $ALERTS_FILE"

tail -n 0 -f "$ALERTS_FILE"
