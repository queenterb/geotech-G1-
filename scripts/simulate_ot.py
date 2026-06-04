#!/usr/bin/env python3
"""Simulate OT events and write JSONL to stdout or file."""
import time
import json
import argparse
from cis.ot_adapters import ModbusAdapter, OPCUAAdapter, normalize_ot_event


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--out", help="output file (JSONL)")
    args = parser.parse_args()
    sources = [ModbusAdapter("192.0.2.10"), OPCUAAdapter("opc.local")]
    events = []
    for s in sources:
        for ev in s.poll_once():
            events.append(normalize_ot_event(ev))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        print(f"Wrote {len(events)} events to {args.out}")
    else:
        for e in events:
            print(json.dumps(e))


if __name__ == "__main__":
    main()
