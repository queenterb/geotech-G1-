#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}/cis"

python3 train.py --epochs 1 --save models/lstm_gnn_scripted.pt

LOG_FILE="/tmp/cis_smoke_main.log"
ALERT_FILE="/tmp/cis_alerts.jsonl"
rm -f "${LOG_FILE}" "${ALERT_FILE}" /tmp/cis_ebpf_events.sock

# Start unified service and point alerts file via env var
CIS_ALERTS_FILE="${ALERT_FILE}" python3 -m cis.service > "${LOG_FILE}" 2>&1 &
MAIN_PID=$!
trap 'kill ${MAIN_PID} >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 50); do
  [[ -S /tmp/cis_ebpf_events.sock ]] && break
  sleep 0.1
done

python3 simulate_events.py --count 800 --pid 9999 --interval-ms 1 --write-ratio 0.98
sleep 1

if [[ -s "${ALERT_FILE}" ]]; then
  echo "SMOKE TEST PASS: alerts generated"
  tail -n 3 "${ALERT_FILE}"
else
  echo "SMOKE TEST WARN: no alerts generated; check ${LOG_FILE}"
  exit 2
fi
