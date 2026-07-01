@echo off
python -m pip install --upgrade pip
python -m pip install -r cis\requirements.txt
python -m pip install Flask pytest
if "%CIS_DASHBOARD_SECRET%"=="" set CIS_DASHBOARD_SECRET=ci_test_secret_local_01234567890123456789
set PYTHONPATH=cis
rem Run lightweight validation scripts (non-fatal)
python scripts\test_snapshot.py || echo "snapshot test failed"
python -m pytest cis\tests -q
