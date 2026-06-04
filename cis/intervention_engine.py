from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass


@dataclass
class InterventionResult:
    pid: int
    isolated: bool
    snapshot: str | None
    rolled_back: bool


class InterventionEngine:
    """Best-effort intervention engine.

    In prototype mode, process isolation is performed with SIGSTOP.
    Snapshot/rollback are optional shell commands and are no-op if unset.
    """

    def __init__(self, snapshot_cmd: str = "", rollback_cmd_template: str = ""):
        self.snapshot_cmd = snapshot_cmd.strip()
        self.rollback_cmd_template = rollback_cmd_template.strip()
        self.last_snapshot_id: str | None = None

    def take_snapshot(self) -> str | None:
        snap_id = f"cis_pre_{int(time.time())}"
        if self.snapshot_cmd:
            cmd = self.snapshot_cmd.replace("{snapshot_id}", snap_id)
            subprocess.run(cmd, shell=True, check=False)
        self.last_snapshot_id = snap_id
        return snap_id

    def isolate_process(self, pid: int) -> bool:
        try:
            os.kill(int(pid), signal.SIGSTOP)
            return True
        except Exception:
            return False

    def rollback(self, snapshot_id: str | None) -> bool:
        if not snapshot_id or not self.rollback_cmd_template:
            return False
        cmd = self.rollback_cmd_template.replace("{snapshot_id}", snapshot_id)
        subprocess.run(cmd, shell=True, check=False)
        return True

    def intervene(self, pid: int, rollback_needed: bool = False) -> InterventionResult:
        isolated = self.isolate_process(pid)
        rolled_back = self.rollback(self.last_snapshot_id) if rollback_needed else False
        return InterventionResult(
            pid=pid,
            isolated=isolated,
            snapshot=self.last_snapshot_id,
            rolled_back=rolled_back,
        )
