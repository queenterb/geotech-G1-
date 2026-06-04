"""Continuous compliance mapping and report generation.

Loads mapping rules (alert -> controls) and generates simple compliance reports
from recent alerts.
"""
from __future__ import annotations

import yaml
import os
import json
from typing import Dict, Any, List

MAPPING_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies", "compliance_mapping.yaml")


def load_mappings(path: str | None = None) -> Dict[str, List[Dict[str, Any]]]:
    p = path or MAPPING_PATH
    try:
        with open(p, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except Exception:
        return {}
    return doc.get("mappings", {}) or {}


def map_alert_to_controls(alert: Dict[str, Any], mappings: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rule = alert.get("rule_name") or alert.get("rule") or alert.get("alert_type")
    if not rule:
        return []
    return mappings.get(rule, [])


def generate_report(alerts: List[Dict[str, Any]], mappings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    report = {"total_alerts": len(alerts), "controls": {}, "alerts": []}
    for a in alerts:
        ctrls = map_alert_to_controls(a, mappings)
        report["alerts"].append({"alert": a, "controls": ctrls})
        for c in ctrls:
            key = f"{c.get('framework')}|{c.get('control')}"
            report["controls"].setdefault(key, {"framework": c.get("framework"), "control": c.get("control"), "description": c.get("description"), "count": 0})
            report["controls"][key]["count"] += 1
    return report


def load_alerts_from_file(path: str) -> List[Dict[str, Any]]:
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    # skip malformed lines
                    continue
    except Exception:
        pass
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("alerts_file", help="JSONL file with alerts")
    parser.add_argument("--out", help="output JSON report path")
    args = parser.parse_args()
    mappings = load_mappings()
    alerts = load_alerts_from_file(args.alerts_file)
    rpt = generate_report(alerts, mappings)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rpt, f, indent=2)
        print(f"Wrote report to {args.out}")
    else:
        print(json.dumps(rpt, indent=2))
