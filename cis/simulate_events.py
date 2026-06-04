from __future__ import annotations

import argparse
import json
import os
import platform
import random
import socket
import time


def send_events(socket_path: str, count: int, pid: int, interval_ms: int, write_ratio: float) -> None:
    is_windows = platform.system() == "Windows"
    if is_windows:
        print("[SIM] Connecting to TCP 127.0.0.1:9999...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9999))
        print("[SIM] Connected!")
    else:
        if not os.path.exists(socket_path):
            raise FileNotFoundError(f"socket not found: {socket_path}")
        print(f"[SIM] Connecting to Unix socket {socket_path}...")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socket_path)
        print("[SIM] Connected!")
    try:
        sent = 0
        for i in range(count):
            op_type = 2 if random.random() < write_ratio else 1
            ev = {
                "pid": pid,
                "uid": 1000,
                "timestamp": time.time(),
                "comm": "simulator",
                "filename": f"/tmp/cis_sim_{i}.dat",
                "op_type": op_type,
            }
            s.sendall((json.dumps(ev) + "\n").encode("utf-8"))
            sent += 1
            if sent % 100 == 0:
                print(f"[SIM] Sent {sent} events...")
            time.sleep(max(0.0, interval_ms / 1000.0))
        print(f"[SIM] Finished sending {sent} events.")
    finally:
        s.close()
        print("[SIM] Connection closed.")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--socket", default="/tmp/cis_ebpf_events.sock")
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--pid", type=int, default=4242)
    p.add_argument("--interval-ms", type=int, default=2)
    p.add_argument("--write-ratio", type=float, default=0.95)
    args = p.parse_args()
    send_events(args.socket, args.count, args.pid, args.interval_ms, args.write_ratio)


if __name__ == "__main__":
    main()
