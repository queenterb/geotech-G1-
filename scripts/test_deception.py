#!/usr/bin/env python3
"""Test deception flow: deploy a decoy, simulate an interaction, and print telemetry."""
import subprocess
import sys
import os
import json

ROOT = os.path.dirname(__file__)
PY = sys.executable
DEPLOY = os.path.join(ROOT, "deploy_decoy.py")


def run(cmd):
    print("$ ", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
    return res.returncode


def main():
    decoy_id = "decoy-test-1"
    run([PY, DEPLOY, decoy_id, "--simulate"]) 
    # read telemetry
    decoy_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "decoys")
    tel_file = os.path.join(decoy_dir, f"{decoy_id}.telemetry.jsonl")
    if os.path.exists(tel_file):
        print("Telemetry lines:")
        with open(tel_file, "r", encoding="utf-8") as f:
            for line in f:
                print(json.dumps(json.loads(line), indent=2))
    else:
        print("No telemetry file found at", tel_file)


if __name__ == "__main__":
    main()
