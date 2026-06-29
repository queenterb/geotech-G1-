import json
import os
from typing import Any, Dict

from .main_detector import validate_event_payload


class TelemetryIngestionService:
    """A simple persistence-backed telemetry ingestion service for live events."""

    def __init__(self, storage_path: str = "/tmp/cis_live_events.jsonl"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path) or ".", exist_ok=True)

    def ingest_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = validate_event_payload(payload)
        if event is None:
            raise ValueError("Invalid telemetry payload")

        with open(self.storage_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "pid": event.pid,
                "timestamp": event.timestamp,
                "filename": event.filename,
                "op_type": event.op_type,
                "uid": event.uid,
                "comm": event.comm,
            }) + "\n")

        return {
            "accepted": True,
            "pid": event.pid,
            "filename": event.filename,
            "op_type": event.op_type,
            "storage_path": self.storage_path,
        }
