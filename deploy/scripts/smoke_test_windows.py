#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    cis_dir = repo_root / "cis"

    tmpdir = Path(tempfile.mkdtemp(prefix="cis_smoke_"))
    log_file = tmpdir / "cis_smoke_main.log"
    alert_file = tmpdir / "cis_alerts.jsonl"
    socket_file = tmpdir / "cis_ebpf_events.sock"

    print("Smoke test temp dir:", tmpdir)

    # Train a lightweight model for the smoke test.
    print("Training quick model...")
    subprocess.run(
        [sys.executable, str(cis_dir / "train.py"), "--epochs", "1", "--save", str(cis_dir / "models" / "lstm_gnn_scripted.pt")],
        check=True,
    )

    for path in (log_file, alert_file, socket_file):
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

    env = os.environ.copy()
    env["CIS_ALERTS_FILE"] = str(alert_file)
    env["CIS_EBPF_SOCKET_PATH"] = str(socket_file)
    env["CIS_HOST"] = "127.0.0.1"
    env["CIS_PORT"] = "8000"

    print("Starting cis.service...")
    with open(log_file, "wb") as lf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "cis.service"],
            cwd=str(repo_root),
            env=env,
            stdout=lf,
            stderr=subprocess.STDOUT,
        )

    try:
        import platform as _platform
        import socket as _socket

        is_windows = _platform.system() == "Windows"
        if is_windows:
            print("Waiting for service to open TCP port 9999...")
            for _ in range(120):
                try:
                    with _socket.create_connection(("127.0.0.1", 9999), timeout=0.5):
                        break
                except Exception:
                    time.sleep(0.1)
            else:
                print("ERROR: TCP port 9999 not opened by service")
                dump_log_tail(log_file)
                return 2
            socket_arg = str(socket_file)
        else:
            print("Waiting for Unix socket to appear...")
            for _ in range(120):
                if socket_file.exists():
                    break
                time.sleep(0.1)
            else:
                print("ERROR: socket did not appear")
                dump_log_tail(log_file)
                return 2
            socket_arg = str(socket_file)

        print("Service ready — running simulate_events.py...")
        subprocess.run(
            [sys.executable, str(cis_dir / "simulate_events.py"), "--socket", socket_arg, "--count", "800", "--pid", "9999", "--interval-ms", "1", "--write-ratio", "0.98"],
            check=True,
        )

        time.sleep(1)

        if alert_file.exists() and alert_file.stat().st_size > 0:
            print("SMOKE TEST PASS: alerts generated")
            with open(alert_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("Last alerts:\n", "".join(lines[-3:]))
            return 0

        print("SMOKE TEST FAIL: alert file empty")
        dump_log_tail(log_file)
        return 3

    finally:
        if proc.poll() is None:
            proc.terminate()
            time.sleep(1)
            if proc.poll() is None:
                proc.kill()


def dump_log_tail(log_path: Path, lines: int = 40) -> None:
    print("--- log tail ---")
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line, end="")
        except Exception as exc:
            print("Could not read log file:", exc)
    else:
        print("Log file missing:", log_path)


if __name__ == "__main__":
    raise SystemExit(main())
