#!/usr/bin/env bash
set -euo pipefail

HEARTBEAT_FILE="/tmp/cis_heartbeat"
MAX_AGE_SEC=120

if pgrep -f "detector_loader" > /dev/null; then
  echo "eBPF loader OK"
else
  echo "eBPF loader not running"
  exit 1
fi

if systemctl is-active --quiet cis-main; then
  echo "cis-main OK"
else
  echo "cis-main not active"
  exit 1
fi

if [[ -f "${HEARTBEAT_FILE}" ]]; then
  NOW=$(date +%s)
  LAST=$(cat "${HEARTBEAT_FILE}" | cut -d'.' -f1)
  AGE=$((NOW - LAST))
  if [[ ${AGE} -le ${MAX_AGE_SEC} ]]; then
    echo "heartbeat OK (${AGE}s old)"
  else
    echo "heartbeat stale (${AGE}s old)"
    exit 1
  fi
else
  echo "heartbeat missing"
  exit 1
fi

echo "CIS healthy"
