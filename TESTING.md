Testing
=======

Local testing
-------------

Prerequisites:
- Python 3.14 in a virtual environment (recommended)

Run (Linux/macOS):

```bash
bash scripts/run_tests_local.sh
```

Run (Windows cmd/PowerShell):

```
scripts\run_tests_local.bat
```

Notes:
- The scripts set a default `CIS_DASHBOARD_SECRET` used only for tests.
- To override, set the environment variable before running, e.g.

```bash
export CIS_DASHBOARD_SECRET="my_secret_value"
```

CI testing
----------

- The GitHub Actions workflow `/.github/workflows/ci.yml` runs the full test matrix
  (Ubuntu, Windows, macOS). The workflow provides a CI-only `CIS_DASHBOARD_SECRET`.
- To trigger CI, open a pull request. The PR runs the matrix and reports results in GitHub.

Troubleshooting
---------------
- If tests fail locally, ensure your virtualenv has the dependencies installed:

```bash
python -m pip install -r cis/requirements.txt
```

- For flaky failures related to environment variables, set `CIS_DASHBOARD_SECRET` locally.
