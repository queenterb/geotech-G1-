#!/usr/bin/env python3
"""Generate a compliance report from alerts JSONL using `cis.compliance` mappings."""
import argparse
from cis.compliance import load_mappings, load_alerts_from_file, generate_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("alerts_file", help="JSONL file with alert records")
    parser.add_argument("--out", help="output JSON report path")
    args = parser.parse_args()
    mappings = load_mappings()
    alerts = load_alerts_from_file(args.alerts_file)
    rpt = generate_report(alerts, mappings)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            import json
            json.dump(rpt, f, indent=2)
        print(f"Wrote report to {args.out}")
    else:
        import json
        print(json.dumps(rpt, indent=2))


if __name__ == "__main__":
    main()
