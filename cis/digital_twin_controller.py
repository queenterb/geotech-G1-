from __future__ import annotations

import asyncio
import time
from typing import Any


class FirecrackerTwin:
    """Prototype twin interface.

    Replace stubs with Firecracker API calls in production.
    """

    def __init__(self):
        self.started = False

    async def start_vm(self, vm_id: str = "cis-twin") -> bool:
        _ = vm_id
        self.started = True
        return True

    async def stop_vm(self):
        self.started = False


class CounterfactualSimulator:
    def __init__(self, twin: FirecrackerTwin):
        self.twin = twin
        self.event_log: list[dict[str, Any]] = []

    def record_event(self, event: dict[str, Any]):
        self.event_log.append(event)
        if len(self.event_log) > 10000:
            self.event_log = self.event_log[-10000:]

    async def simulate_kill(self, pid: int, lookback_ms: int = 50, ahead_sec: float = 5.0) -> float:
        _ = lookback_ms
        # Prototype heuristic: estimate residual write pressure after removing target PID.
        await asyncio.sleep(min(0.05, ahead_sec))
        now = time.time()
        recent = [e for e in self.event_log if now - float(e.get("timestamp", now)) <= 2.0]
        writes_by_pid: dict[int, int] = {}
        for e in recent:
            if int(e.get("op_type", 0)) != 2:
                continue
            ep = int(e.get("pid", -1))
            writes_by_pid[ep] = writes_by_pid.get(ep, 0) + 1

        total_writes = sum(writes_by_pid.values())
        removed = writes_by_pid.get(int(pid), 0)
        residual = max(0, total_writes - removed)
        return min(1.0, residual / 200.0)


async def _run_daemon() -> None:
    twin = FirecrackerTwin()
    await twin.start_vm("cis-twin")
    try:
        while True:
            await asyncio.sleep(1.0)
    finally:
        await twin.stop_vm()


if __name__ == "__main__":
    asyncio.run(_run_daemon())
