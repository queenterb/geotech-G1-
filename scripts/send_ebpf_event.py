#!/usr/bin/env python3
"""Send a sample EBPF-like JSON event to the local collector socket (unix or TCP)."""
import json
import os
import socket


def send_unix(path, msg: str):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendall(msg.encode("utf-8") + b"\n")
    s.close()


def send_tcp(host, port, msg: str):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(msg.encode("utf-8") + b"\n")
    s.close()


def main():
    payload = {
        "pid": os.getpid(),
        "timestamp": float("%.6f" % (os.times().elapsed if hasattr(os.times(), 'elapsed') else  time.time())),
        "filename": "/tmp/testfile.txt",
        "op_type": 2,
        "comm": "test_sender",
    }
    msg = json.dumps(payload)
    # Try unix socket first
    unix_path = "/tmp/cis_ebpf_events.sock"
    try:
        if os.path.exists(unix_path):
            send_unix(unix_path, msg)
            print(f"Sent event to unix socket {unix_path}")
            return
    except Exception as e:
        print(f"Unix send failed: {e}")
    # Fallback to TCP
    try:
        send_tcp("127.0.0.1", 9999, msg)
        print("Sent event to TCP 127.0.0.1:9999")
        return
    except Exception as e:
        print(f"TCP send failed: {e}")
        print("No collector available to receive event.")


if __name__ == "__main__":
    import time

    main()
