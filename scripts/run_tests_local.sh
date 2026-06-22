#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
python -m pip install -r cis/requirements.txt
python -m pip install Flask pytest
: ${CIS_DASHBOARD_SECRET:=ci_test_secret_local_01234567890123456789}
export CIS_DASHBOARD_SECRET
export PYTHONPATH=cis
# Run lightweight validation scripts (non-fatal)
python scripts/test_snapshot.py || true
python scripts/test_playbook_runner.py || true
# Run full test suite
python -m pytest cis/tests -q
