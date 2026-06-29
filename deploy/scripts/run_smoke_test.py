#!/usr/bin/env python3
import subprocess
import sys
import tempfile
import time
import os
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
cis_dir = repo_root / "cis"

tmpdir = Path(tempfile.mkdtemp(prefix="cis_smoke_"))
LOG_FILE = tmpdir / "cis_smoke_main.log"
ALERT_FILE = tmpdir / "cis_alerts.jsonl"
SOCK = tmpdir / "cis_ebpf_events.sock"

print("Smoke test temp dir:", tmpdir)

# Train small model
print("Training quick model...")
subprocess.run([sys.executable, str(cis_dir / "train.py"), "--epochs", "1", "--save", str(cis_dir / "models" / "lstm_gnn_scripted.pt")], check=True)

# Ensure no old artifacts
for p in (LOG_FILE, ALERT_FILE, SOCK):
    try:
        if p.exists():
            if p.is_file():
                p.unlink()
            else:
                # remove socket file if exists
                p.unlink()
    except Exception:
        pass

# Start unified service with env overrides
env = os.environ.copy()
env["CIS_ALERTS_FILE"] = str(ALERT_FILE)
env["CIS_EBPF_SOCKET_PATH"] = str(SOCK)

print("Starting cis.service...")
with open(LOG_FILE, "wb") as lf:
    proc = subprocess.Popen([sys.executable, "-m", "cis.service"], cwd=str(repo_root), env=env, stdout=lf, stderr=subprocess.STDOUT)

# Wait for socket to appear
print("Waiting for socket to be created by service...")
for _ in range(100):
    if SOCK.exists():
        break
    time.sleep(0.05)
else:
    print("Socket not created; dumping log tail:")
    try:
        with open(LOG_FILE, "rb") as f:
            data = f.read().decode(errors="ignore")
            print(data[-2000:])
    except Exception:
        pass
    proc.terminate()
    sys.exit(2)

print("Socket present — sending simulated events...")
# Run simulate_events
subprocess.run([sys.executable, str(cis_dir / "simulate_events.py"), "--socket", str(SOCK), "--count", "800", "--pid", "9999", "--interval-ms", "1", "--write-ratio", "0.98"], check=True)

# Give service a moment to write alerts
time.sleep(1)

if ALERT_FILE.exists() and ALERT_FILE.stat().st_size > 0:
    print("SMOKE TEST PASS: alerts generated")
    with open(ALERT_FILE, "r") as f:
        lines = f.readlines()
        print("Last alerts:\n", "".join(lines[-3:]))
    proc.terminate()
    sys.exit(0)
else:
    print("SMOKE TEST FAIL: no alerts generated; showing log tail and alert file status")
    try:
        with open(LOG_FILE, "rb") as f:
            data = f.read().decode(errors="ignore")
            print(data[-2000:])
    except Exception as e:
        print("Could not read log file:", e)
    proc.terminate()
    sys.exit(3)
