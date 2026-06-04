#!/usr/bin/env python3
"""Prototype playbook runner that supports dry-run via the digital twin snapshot orchestrator."""
from __future__ import annotations

import argparse
import subprocess
import sys
import os
import time
import yaml
import uuid

ROOT = os.path.dirname(__file__)
SNAP_ORCH = os.path.join(ROOT, "snapshot_orchestrator.py")


def create_snapshot(name: str):
    subprocess.run([sys.executable, SNAP_ORCH, "create", name], check=True)


def validate_snapshot(name: str) -> bool:
    res = subprocess.run([sys.executable, SNAP_ORCH, "validate", name])
    return res.returncode == 0


def rollback_snapshot(name: str, apply: bool = False):
    args = [sys.executable, SNAP_ORCH, "rollback", name]
    if apply:
        args.append("--apply")
    subprocess.run(args, check=True)


def render_template(s: str, ctx: dict) -> str:
    # very small templating
    out = s
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def run_action(action: dict, ctx: dict, dry_run: bool):
    t = action.get("type")
    if t == "snapshot_pre":
        name = render_template(action.get("name", "pre-" + ctx["change_id"]), ctx)
        print(f"[ACTION] create pre-snapshot {name}")
        if not dry_run:
            create_snapshot(name)
    elif t == "snapshot_post":
        name = render_template(action.get("name", "post-" + ctx["change_id"]), ctx)
        print(f"[ACTION] create post-snapshot {name}")
        if not dry_run:
            create_snapshot(name)
    elif t == "kill_process":
        pid = render_template(str(action.get("pid", "-1")), ctx)
        reason = action.get("reason", "")
        print(f"[ACTION] kill_process pid={pid} reason={reason} (dry_run={dry_run})")
        if not dry_run:
            # In prototype: record event to counterfactual simulator via file
            print(f"Simulating kill of pid {pid} in twin")
    elif t == "isolate_network":
        dur = action.get("duration_minutes", 30)
        reason = action.get("reason", "")
        print(f"[ACTION] isolate_network duration={dur}min reason={reason} (dry_run={dry_run})")
        if not dry_run:
            print("Simulating network isolation in twin/prod")
    elif t == "notify":
        method = action.get("method", "log")
        print(f"[ACTION] notify method={method} details={action} (dry_run={dry_run})")
    else:
        print(f"Unknown action type: {t}")


def run_playbook(path: str, variables: dict | None = None, dry_run: bool = True):
    with open(path, "r", encoding="utf-8") as f:
        pb = yaml.safe_load(f)
    change_id = str(uuid.uuid4())[:8]
    ctx = {"change_id": change_id}
    if variables:
        ctx.update(variables)

    print(f"Running playbook {pb.get('id')} name={pb.get('name')} change_id={change_id} dry_run={dry_run}")

    # First pass: run actions sequentially
    for a in pb.get("actions", []):
        run_action(a, ctx, dry_run=dry_run)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("playbook")
    parser.add_argument("--pid", type=int, help="pid to substitute into the playbook")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    vars = {}
    if args.pid:
        vars["pid"] = args.pid
    run_playbook(args.playbook, variables=vars, dry_run=not args.apply)


if __name__ == "__main__":
    main()
