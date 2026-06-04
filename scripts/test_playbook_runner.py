#!/usr/bin/env python3
"""Test runner for playbook_runner using the sample playbook."""
import subprocess
import sys
import os

ROOT = os.path.dirname(__file__)
PY = sys.executable
PB = os.path.join(ROOT, "..", "playbooks", "sample_kill_playbook.yaml")
RUNNER = os.path.join(ROOT, "playbook_runner.py")


def run(cmd):
    print("$ ", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
    return res.returncode


def main():
    # Dry run
    run([PY, RUNNER, PB, "--pid", "12345"]) 
    # Apply (will create snapshots)
    run([PY, RUNNER, PB, "--pid", "12345", "--apply"]) 


if __name__ == "__main__":
    sys.exit(main())
