#!/usr/bin/env python3
"""Test harness for the recovery orchestrator: create demo snapshots and restore."""
import subprocess
import sys
import os
import time

ROOT = os.path.dirname(__file__)
PY = sys.executable
SNAP_ORCH = os.path.join(ROOT, "snapshot_orchestrator.py")
REC = os.path.join(ROOT, "recovery_orchestrator.py")


def run(cmd):
    print("$ ", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
    return res.returncode


def main():
    # create pre and post snapshots
    name_pre = f"pre-test-{int(time.time())}"
    name_post = f"post-test-{int(time.time())}"
    run([PY, SNAP_ORCH, "create", name_pre])
    run([PY, SNAP_ORCH, "create", name_post])
    # validate and dry-run restore
    run([PY, REC, "--dry-run"])  # should pick last-known-good
    # actually restore
    run([PY, REC])


if __name__ == "__main__":
    main()
