#!/usr/bin/env python3
"""Simple script to deploy a decoy and optionally simulate an interaction."""
import argparse
from cis.deception import manager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("id")
    parser.add_argument("--kind", default="file")
    parser.add_argument("--path", default="/var/secret/passwords.txt")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--actor", default="203.0.113.5")
    args = parser.parse_args()
    m = manager()
    d = m.create_decoy(args.id, kind=args.kind, config={"path": args.path})
    print(f"Deployed decoy {d.id} kind={d.kind}")
    if args.simulate:
        rec = m.simulate_interaction(d.id, actor_ip=args.actor)
        print("Simulated interaction:", rec)


if __name__ == "__main__":
    main()
