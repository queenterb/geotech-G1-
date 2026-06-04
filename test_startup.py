#!/usr/bin/env python3
import sys
import os

# Set PYTHONUNBUFFERED to see output immediately
os.environ['PYTHONUNBUFFERED'] = '1'

print("TEST 1: Basic imports", flush=True)
try:
    import argparse
    import asyncio
    import json
    import logging
    print("  ✓ Basic imports work", flush=True)
except Exception as e:
    print(f"  ✗ Basic imports failed: {e}", flush=True)
    sys.exit(1)

print("TEST 2: CIS imports", flush=True)
try:
    import cis.immune_memory
    import cis.intervention_engine
    import cis.side_channel_daemon
    import cis.digital_twin_controller
    import cis.model
    print("  ✓ CIS module imports work", flush=True)
except Exception as e:
    print(f"  ✗ CIS module imports failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("TEST 3: main_detector module", flush=True)
try:
    import cis.main_detector as m
    print("  ✓ main_detector module imported", flush=True)
except Exception as e:
    print(f"  ✗ main_detector failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("TEST 4: load_config", flush=True)
try:
    cfg = m.load_config(None)
    print(f"  ✓ config loaded with {len(cfg)} keys", flush=True)
except Exception as e:
    print(f"  ✗ config load failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("TEST 5: CISMain init", flush=True)
try:
    cis = m.CISMain(cfg)
    print("  ✓ CISMain initialized", flush=True)
except Exception as e:
    print(f"  ✗ CISMain init failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ ALL TESTS PASSED!", flush=True)
