"""Simple IT-OT correlation utilities."""
from __future__ import annotations

import time
from typing import Dict, Any, List


def correlate_it_ot(it_event: Dict[str, Any], ot_events: List[Dict[str, Any]], time_window_sec: float = 5.0):
    """Return a list of OT events that correlate with the given IT event.

    Correlation heuristics (prototype):
    - timestamp within `time_window_sec`
    - filename or asset substring matches
    """
    out = []
    its_ts = float(it_event.get("timestamp", time.time()))
    filename = str(it_event.get("filename", "")).lower()
    for o in ot_events:
        ots = float(o.get("ts", 0))
        if abs(its_ts - ots) > time_window_sec:
            continue
        asset = str(o.get("asset", "")).lower()
        typ = str(o.get("type", "")).lower()
        # filename contains asset id or vice versa
        if asset and (asset in filename or filename in asset):
            out.append({"ot": o, "reason": "asset_filename_match"})
            continue
        # heuristic: certain sensor types + spike correlate to write activity
        if typ in ("register", "power", "temperature") and float(o.get("value", 0)) > 100:
            out.append({"ot": o, "reason": "sensor_spike"})
    return out
