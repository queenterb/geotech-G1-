"""Prototype OT/ICS adapters (Modbus/OPC-UA) and normalization helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class OTEvent:
    timestamp: float
    asset_id: str
    sensor_type: str
    value: Any
    raw: Dict[str, Any]


class ModbusAdapter:
    """Simulated Modbus adapter that polls registers and returns normalized OTEvent objects."""

    def __init__(self, host: str, unit_id: int = 1):
        self.host = host
        self.unit_id = unit_id

    def poll_once(self) -> List[OTEvent]:
        # Prototype: return a small set of fake readings
        now = time.time()
        return [
            OTEvent(timestamp=now, asset_id=f"modbus-{self.host}", sensor_type="register", value=123, raw={"reg": 40001}),
        ]


class OPCUAAdapter:
    """Simulated OPC-UA adapter that reads node values."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def poll_once(self) -> List[OTEvent]:
        now = time.time()
        return [
            OTEvent(timestamp=now, asset_id=f"opc-{self.endpoint}", sensor_type="temperature", value=55.2, raw={"node": "ns=2;i=1085"}),
        ]


def normalize_ot_event(e: OTEvent) -> Dict[str, Any]:
    return {
        "ts": e.timestamp,
        "asset": e.asset_id,
        "type": e.sensor_type,
        "value": e.value,
        "raw": e.raw,
    }


if __name__ == "__main__":
    m = ModbusAdapter("192.0.2.10")
    for ev in m.poll_once():
        print(normalize_ot_event(ev))
