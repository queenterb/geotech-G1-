#!/usr/bin/env python3
"""Recovery orchestrator prototype.

Uses snapshots created by `snapshot_orchestrator.py` to validate and restore
production state. Prototype implements a simple 'restore last-known-good'
behavior by selecting the most recent snapshot whose name starts with 'post-'
or a specified snapshot name.
"""
from __future__ import annotations

import argparse
import os
import json
import subprocess
import time

ROOT = os.path.dirname(__file__)
SNAP_ROOT = os.path.join(ROOT, "..", "snapshots")
SNAP_ORCH = os.path.join(ROOT, "snapshot_orchestrator.py")


def list_snapshots():
    snaps = []
    if not os.path.exists(SNAP_ROOT):
        return snaps
    for name in sorted(os.listdir(SNAP_ROOT)):
        path = os.path.join(SNAP_ROOT, name)
        meta = os.path.join(path, "metadata.json")
        if os.path.exists(meta):
            try:
                with open(meta, "r", encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                m = {"name": name}
        else:
            m = {"name": name}
        m["dir"] = path
        snaps.append(m)
    return snaps


def find_last_known_good() -> str | None:
    snaps = list_snapshots()
    # Prefer snapshots named post-* then pre-* then any
    for pref in ("post-", "pre-"):
        for s in reversed(snaps):
            if s.get("name", "").startswith(pref):
                return s.get("name")
    if snaps:
        return snaps[-1].get("name")
    return None


def restore_snapshot(name: str, apply: bool = True) -> bool:
    # Call snapshot_orchestrator rollback
    cmd = ["python", SNAP_ORCH, "rollback", name]
    if apply:
        cmd.append("--apply")
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("Restore failed:", res.stderr)
        return False
    return True


def validate_snapshot(name: str) -> bool:
    cmd = ["python", SNAP_ORCH, "validate", name]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", help="snapshot name to restore (optional)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    target = args.snapshot or find_last_known_good()
    if not target:
        print("No snapshots available to restore")
        return 2
    print(f"Selected snapshot to restore: {target}")
    valid = validate_snapshot(target)
    print(f"Validation result for {target}: {valid}")
    if not valid:
        print("Snapshot validation failed; aborting")
        return 3
    if args.dry_run:
        print("Dry-run: would restore snapshot", target)
        return 0
    ok = restore_snapshot(target, apply=True)
    print("Restore completed?", ok)
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
