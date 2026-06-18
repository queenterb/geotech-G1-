#!/usr/bin/env python3
"""Test harness for compliance report generation."""
import json
from cis.compliance import generate_report, load_mappings


def main():
    mappings = load_mappings()
    # sample alerts
    alerts = [
        {"rule_name": "ransomware-write-spike", "severity": "HIGH", "event": {"filename": "/tmp/malware"}},
        {"rule_name": "decoy-interaction", "severity": "MEDIUM", "event": {"decoy": "decoy1"}},
        {"rule_name": "unknown-rule", "severity": "LOW", "event": {}},
    ]
    rpt = generate_report(alerts, mappings)
    print(json.dumps(rpt, indent=2))


if __name__ == "__main__":
    main()
