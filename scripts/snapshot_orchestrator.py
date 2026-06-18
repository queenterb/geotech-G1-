#!/usr/bin/env python3
"""Simple snapshot orchestrator prototype.

Snapshots are stored under `snapshots/<name>/` with metadata.json and optional files.
This prototype uses the `FirecrackerTwin` stub for start/stop operations when available.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import time
from typing import Dict

SNAP_ROOT = os.path.join(os.path.dirname(__file__), "..", "snapshots")


def _ensure_root():
    os.makedirs(SNAP_ROOT, exist_ok=True)


def create_snapshot(name: str, description: str = "") -> str:
    _ensure_root()
    path = os.path.join(SNAP_ROOT, name)
    if os.path.exists(path):
        raise FileExistsError(f"Snapshot {name} already exists")
    os.makedirs(path)
    meta = {
        "name": name,
        "description": description,
        "created_at": time.time(),
        "tool_version": "snapshot-orchestrator-0.1",
    }
    with open(os.path.join(path, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    # create a simulated filesystem state file (prototype)
    fs = {"files": ["/etc/passwd", "/var/log/app.log"], "note": "simulated state"}
    with open(os.path.join(path, "fs_state.json"), "w", encoding="utf-8") as f:
        json.dump(fs, f, indent=2)
    return path


def list_snapshots() -> Dict[str, dict]:
    _ensure_root()
    out = {}
    for name in sorted(os.listdir(SNAP_ROOT)):
        p = os.path.join(SNAP_ROOT, name)
        if not os.path.isdir(p):
            continue
        meta_path = os.path.join(p, "metadata.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"name": name, "error": "bad metadata"}
        out[name] = meta
    return out


def validate_snapshot(name: str) -> bool:
    _ensure_root()
    p = os.path.join(SNAP_ROOT, name)
    if not os.path.exists(p):
        raise FileNotFoundError(name)
    # Prototype validations: metadata exists and fs_state.json exists
    meta = os.path.join(p, "metadata.json")
    fs = os.path.join(p, "fs_state.json")
    if not os.path.exists(meta) or not os.path.exists(fs):
        return False
    # Could run counterfactual simulations here; return True for prototype
    return True


def rollback_snapshot(name: str, dry_run: bool = True) -> bool:
    _ensure_root()
    p = os.path.join(SNAP_ROOT, name)
    if not os.path.exists(p):
        raise FileNotFoundError(name)
    if dry_run:
        print(f"[DRY RUN] Would apply snapshot: {name}")
        return True
    # Prototype: copy fs_state.json to a simulated production path
    prod_state = os.path.join(SNAP_ROOT, "_applied_prod_state.json")
    shutil.copyfile(os.path.join(p, "fs_state.json"), prod_state)
    print(f"Applied snapshot {name} to simulated production state")
    return True


async def _start_twin_and_snapshot(name: str):
    try:
        from cis.digital_twin_controller import FirecrackerTwin
    except Exception:
        FirecrackerTwin = None
    twin = FirecrackerTwin() if FirecrackerTwin is not None else None
    if twin is not None:
        await twin.start_vm(name)
        print("Started twin VM")
    path = create_snapshot(name, description="created by orchestrator")
    if twin is not None:
        await twin.stop_vm()
        print("Stopped twin VM")
    return path


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p_create = sub.add_parser("create")
    p_create.add_argument("name")
    p_create.add_argument("--desc", default="")
    sub.add_parser("list")
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("name")
    p_rollback = sub.add_parser("rollback")
    p_rollback.add_argument("name")
    p_rollback.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    if args.cmd == "create":
        asyncio.run(_start_twin_and_snapshot(args.name))
        print(f"Created snapshot {args.name}")
    elif args.cmd == "list":
        s = list_snapshots()
        for n, m in s.items():
            created = m.get("created_at")
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created)) if created else "?"
            print(f"{n}\t{ts}\t{m.get('description','')}")
    elif args.cmd == "validate":
        ok = validate_snapshot(args.name)
        print("VALID" if ok else "INVALID")
        return 0 if ok else 2
    elif args.cmd == "rollback":
        ok = rollback_snapshot(args.name, dry_run=not args.apply)
        return 0 if ok else 2
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
