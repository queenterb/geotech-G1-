import json
import os
import time
from typing import Dict, Any

from .database import get_db_connection, log_audit_event


class OperationalMonitor:
    """Lightweight operational monitoring for a live deployment."""

    def __init__(self, status_path: str = "/tmp/cis_status.json"):
        self.status_path = status_path
        os.makedirs(os.path.dirname(status_path) or ".", exist_ok=True)

    def write_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = {
            "timestamp": time.time(),
            "status": "running",
            **payload,
        }
        with open(self.status_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        log_audit_event("status_written", details=json.dumps(payload))
        return data

    def get_status(self) -> Dict[str, Any]:
        if not os.path.exists(self.status_path):
            return {"status": "unknown"}
        with open(self.status_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
