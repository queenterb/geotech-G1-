#!/usr/bin/env python3
"""Quick test harness for snapshot orchestrator."""
import subprocess
import sys
import os


def run(cmd):
    print("$ ", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
    return res.returncode


def main():
    root = os.path.dirname(__file__)
    py = sys.executable
    name = "ci-demo-snap"
    run([py, os.path.join(root, "snapshot_orchestrator.py"), "create", name])
    run([py, os.path.join(root, "snapshot_orchestrator.py"), "list"])
    run([py, os.path.join(root, "snapshot_orchestrator.py"), "validate", name])
    run([py, os.path.join(root, "snapshot_orchestrator.py"), "rollback", name, "--apply"])  # apply for test


if __name__ == "__main__":
    sys.exit(main())
