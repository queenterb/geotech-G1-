import json
import os
from typing import Any, Dict
import os as _os

from .main_detector import validate_event_payload


class TelemetryIngestionService:
    """Telemetry ingestion service. If `CIS_SIEM_HTTP_ENDPOINT` is configured
    this will POST validated events to the backend SIEM endpoint so they are
    recorded and broadcast via the backend WebSocket manager. Otherwise it
    falls back to file-backed logging (development).
    """

    def __init__(self, storage_path: str = "/tmp/cis_live_events.jsonl"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path) or ".", exist_ok=True)
        self.siem_endpoint = _os.environ.get("CIS_SIEM_HTTP_ENDPOINT")

    def ingest_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = validate_event_payload(payload)
        if event is None:
            raise ValueError("Invalid telemetry payload")

        record = {
            "pid": event.pid,
            "timestamp": event.timestamp,
            "filename": event.filename,
            "op_type": event.op_type,
            "uid": event.uid,
            "comm": event.comm,
        }

        # If backend SIEM endpoint is configured, POST the event
        if self.siem_endpoint:
            try:
                import requests

                requests.post(self.siem_endpoint, json={
                    "event_type": "telemetry",
                    "severity": "INFO",
                    "source": "cis_ingest",
                    "payload": record,
                    "description": "Telemetry ingestion event",
                }, timeout=3)
                return {"accepted": True, **record}
            except Exception:
                # If network call fails, fall through to file logging
                pass

        # Fallback: append to local file for development / offline use
        with open(self.storage_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

        return {
            "accepted": True,
            **record,
            "storage_path": self.storage_path,
        }
