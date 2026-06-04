#!/usr/bin/env python3
"""CLI to ingest a STIX/indicator JSON file into the local intel store."""
from __future__ import annotations

import argparse
from cis.threat_intel import ThreatIntelStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="STIX JSON file to ingest")
    args = parser.parse_args()
    store = ThreatIntelStore()
    n = store.ingest_stix(args.file)
    print(f"Ingested {n} indicators into {store.path}")


if __name__ == "__main__":
    main()
