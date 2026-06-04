#!/usr/bin/env python3
import sys
import traceback

try:
    print("Starting import...", file=sys.stderr)
    from cis import main_detector
    print("Import successful!", file=sys.stderr)
except Exception as e:
    print(f"Import failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

try:
    print("Loading config...", file=sys.stderr)
    cfg = main_detector.load_config(None)
    print(f"Config keys: {list(cfg.keys())}", file=sys.stderr)
except Exception as e:
    print(f"Config load failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

try:
    print("Creating CISMain...", file=sys.stderr)
    cis = main_detector.CISMain(cfg)
    print("CISMain created successfully!", file=sys.stderr)
except Exception as e:
    print(f"CISMain creation failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print("All tests passed!", file=sys.stderr)
