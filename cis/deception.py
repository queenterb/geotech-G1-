"""Deception & honeypot manager prototype.

Provides a DecoyManager to create and manage decoys (simulated services/files).
Decoys emit telemetry when interacted with to help profile attackers.
"""
from __future__ import annotations

import time
import threading
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List

DECOY_STORE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "decoys")
os.makedirs(DECOY_STORE, exist_ok=True)


@dataclass
class Decoy:
    id: str
    kind: str
    config: Dict[str, Any]
    created_at: float = field(default_factory=lambda: time.time())


class DecoyManager:
    def __init__(self):
        self.decoys: Dict[str, Decoy] = {}

    def create_decoy(self, decoy_id: str, kind: str = "file", config: Dict[str, Any] | None = None) -> Decoy:
        cfg = config or {}
        d = Decoy(id=decoy_id, kind=kind, config=cfg)
        self.decoys[decoy_id] = d
        # persist metadata
        path = os.path.join(DECOY_STORE, f"{decoy_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"id": d.id, "kind": d.kind, "config": d.config, "created_at": d.created_at}, f, indent=2)
        return d

    def list_decoys(self) -> List[Dict[str, Any]]:
        out = []
        for d in self.decoys.values():
            out.append({"id": d.id, "kind": d.kind, "created_at": d.created_at, "config": d.config})
        return out

    def simulate_interaction(self, decoy_id: str, actor_ip: str = "1.2.3.4") -> Dict[str, Any]:
        d = self.decoys.get(decoy_id)
        if not d:
            raise KeyError(decoy_id)
        # Produce telemetry record describing the interaction
        record = {
            "decoy_id": d.id,
            "kind": d.kind,
            "actor_ip": actor_ip,
            "timestamp": time.time(),
            "details": {"path": d.config.get("path", "/tmp/secret.txt"), "action": "read"},
        }
        # write to a decoy telemetry file
        tel_path = os.path.join(DECOY_STORE, f"{decoy_id}.telemetry.jsonl")
        with open(tel_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record


_MANAGER: DecoyManager | None = None


def manager() -> DecoyManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = DecoyManager()
    return _MANAGER


if __name__ == "__main__":
    m = manager()
    d = m.create_decoy("decoy1", kind="file", config={"path": "/var/secret/passwords.txt"})
    print("Created", d)
    rec = m.simulate_interaction("decoy1", actor_ip="203.0.113.5")
    print("Telemetry:", rec)
