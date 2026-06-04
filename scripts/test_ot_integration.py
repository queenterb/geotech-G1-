#!/usr/bin/env python3
"""Test IT-OT correlation using sample IT event and simulated OT events."""
import json
import os
import sys
from cis.correlation import correlate_it_ot
from cis.ot_adapters import ModbusAdapter, OPCUAAdapter, normalize_ot_event


def main():
    # Sample IT event (from EBPF collector)
    it_event = {"pid": 1234, "timestamp": __import__("time").time(), "filename": "modbus-192.0.2.10-logs.txt"}
    # Simulate OT events
    m = ModbusAdapter("192.0.2.10")
    o = OPCUAAdapter("opc.local")
    ot_events = [normalize_ot_event(e) for e in m.poll_once()] + [normalize_ot_event(e) for e in o.poll_once()]
    print("OT events:")
    for ev in ot_events:
        print(ev)

    cor = correlate_it_ot(it_event, ot_events, time_window_sec=10.0)
    print("Correlation results:")
    print(json.dumps(cor, indent=2))


if __name__ == "__main__":
    main()
