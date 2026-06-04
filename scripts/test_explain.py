#!/usr/bin/env python3
"""Test explainable layer by generating an explanation for a sample alert."""
import json
from cis.alert_explanation import explain_alert


def main():
    alert = {
        "event_data": {
            "pid": 4321,
            "filename": "/tmp/malware.bin",
            "timestamp": __import__("time").time(),
            "modified_files_count": 200,
            "encryption_indicator": 0.8,
            "entropy": 7.5,
            "power_pkg_watts": 95.0,
        },
        "severity": "HIGH",
        "rule_name": "ransomware-write-spike",
        "immune_alarm": True,
    }
    explanation = explain_alert(alert)
    print(json.dumps(explanation, indent=2))


if __name__ == "__main__":
    main()
