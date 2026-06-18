#!/usr/bin/env python3
"""Quick test for threat intel ingestion and enrichment."""
import json
import tempfile
from cis.threat_intel import ThreatIntelStore


def make_sample_stix(path: str):
    doc = {
        "type": "bundle",
        "objects": [
            {"type": "indicator", "pattern": "[file:path = '/tmp/malware.bin']"},
            {"type": "indicator", "pattern": "[ipv4-addr:value = '10.0.0.5']"},
            {"type": "indicator", "pattern": "[domain-name:value = 'bad.example.com']"},
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


def main():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.close()
    make_sample_stix(tmp.name)
    store = ThreatIntelStore()
    added = store.ingest_stix(tmp.name)
    print(f"Added {added} indicators")
    print("Indicators:")
    for i in store.list_indicators():
        print(i)

    # Test enrichment
    ev1 = {"filename": "/tmp/malware.bin", "src_ip": "10.0.0.5", "hostname": "victim.local"}
    print("Event1 matches:", store.enrich_event(ev1))

    ev2 = {"filename": "/tmp/other", "src_ip": "1.2.3.4", "hostname": "bad.example.com"}
    print("Event2 matches:", store.enrich_event(ev2))


if __name__ == "__main__":
    main()
