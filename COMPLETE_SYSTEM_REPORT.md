# Complete System Report

## 1. Executive Summary

This repository contains the CIS (Causal Immune Sentinel) prototype: a ransomware detection and response system built from sensor ingestion, machine learning prediction, alert explainability, and an integrated realtime dashboard.

The system supports:
- event ingestion through eBPF or TCP event streams
- anticipatory model-based detection
- custom alert rule and counterfactual-based intervention
- realtime status monitoring and alert visualization
- billing, trial signup, and subscription-based access control

This report documents the architecture, components, deployment, runtime behavior, and validation guidance for the complete system.

## 2. System Structure

### 2.1 Key folders

- `cis/`
  - Main detection runtime and supporting Python modules
  - `dashboard_new.py` and `dashboard.py` for UI and alert management
  - `main_detector.py` for the event processing loop and status writer
  - `alert_explanation.py` for human-readable alert recommendations
  - `auth.py`, `billing_api.py`, `database.py` for user and subscription management
  - `side_channel_daemon.py` for host telemetry and side-channel sampling
  - `tests/` for unit and integration test coverage

- `dashboard/`
  - Standalone frontend assets for legacy dashboard display
  - `dashboard.js` and `index.html`

- `deploy/`
  - Container orchestration and systemd service definitions
  - `deploy/container/docker-compose.yml`, `Dockerfile`
  - `deploy/systemd/*.service` for Linux deployments

- `ebpf/`
  - eBPF source and build Makefile
  - `ransomware_detector.bpf.c` and `detector_loader.c`

- `installer/`
  - Windows packaging scripts and auto-update helper

### 2.2 Important runtime files

- `cis/config.example.json` — sample runtime configuration
- `cis/config.json` — active environment config when present
- `cis/cis_alerts.jsonl` — serialized alert stream
- `cis/cis_status.json` — current system status for dashboard polling
- `cis/acknowledged_alerts.json` — persisted alert acknowledgements

## 3. Architecture & Data Flow

### 3.1 Runtime pipeline

1. `cis/main_detector.py` starts the EBPF collector and side-channel sampler.
2. System events arrive through the configured socket or TCP endpoint.
3. Events are validated and enqueued by `EBpfCollector`.
4. The detector drains queues, builds feature vectors, and updates `FileSystemState`.
5. An anticipatory model predicts future encryption behavior and computes divergence.
6. Custom alert rules, immune detection, and heuristic thresholds are evaluated.
7. Alerts are emitted with explainable summaries and optionally forwarded or emailed.
8. Status metrics are written to `cis_status.json` for the dashboard.

### 3.2 Dashboard & monitoring

- `cis/dashboard_new.py` serves the modern realtime dashboard UI.
- The `/status` endpoint returns telemetry including:
  - `event_buffer`, `side_buffer`
  - `connections`, `suspicious_ips`, `out_kbps`
  - `renames_per_min`, `modifications_per_min`
  - `divergence`, `encryption_indicator`, alarm flags
  - `false_positive_count`
- The `/alerts-json` endpoint returns recent annotated alerts.
- UI components render charts, status cards, and alert feed.

### 3.3 Billing & access control

- `cis/auth.py` provides user validation and password hashing.
- `cis/database.py` stores users, subscriptions, endpoints, and payments in `~/.cis_billing.db`.
- The new dashboard login now accepts either email or username.
- Billing routes are mounted by `cis/billing_api.py` under `/api/billing`.
- Trial signup and subscription validation are enforced before accessing core monitoring views.

## 4. Deployment and Installation

### 4.1 Local prototype

For Windows:
  1. Run `quickstart.bat` from the repository root.
  2. Activate `.venv\Scripts\activate.bat`.
  3. Run `python -m cis.service` to start the unified service (detector + portal).

For Linux:
  1. Run `quickstart.sh` or manually create a Python environment.
  2. Install dependencies from `cis/requirements.txt`.
  3. Build eBPF programs in `ebpf/` using `make`.
  4. Launch the unified service: `python3 -m cis.service` (or use systemd/container assets).

### 4.2 Container deployment

- Build and run with Docker Compose from `deploy/container/`.
- Review `deploy/container/docker-compose.yml` for service definitions and environment variables.
- Use `deploy/systemd/` service units to manage production-style Linux deployment.

### 4.3 Windows installer support

- `installer/build_installer_windows.bat` builds a Windows installer.
- `installer/auto_update.py` supports remote update checks and self-upgrade workflows.

## 5. Key Features

### 5.1 Detection and alerting

- Event validation for process telemetry
- Side-channel sampling for CPU, power, and acoustic signals
- Machine learning prediction via `AnticipatoryModel`
- Heuristic and policy-based alerting
- Counterfactual simulation for suspicious process intervention
- Structured alert payloads with explainability metadata

### 5.2 Alert explanation

- `cis/alert_explanation.py` generates human-readable `summary`, `root_cause`, `impact`, and `recommended_action` fields.
- Alerts are annotated before being written to `cis_alerts.jsonl`.
- The dashboard shows explainable alert summaries in realtime.

### 5.3 Realtime status telemetry

- Dashboard sees both event and side-channel load
- Tracks network output and active client connections
- Reports suspicious IP counts and buffer sizes
- Includes false positive acknowledgement metrics

## 6. Validation and Testing

### 6.1 Unit tests

- Run tests under `cis/tests/` using `pytest` or `python -m unittest`.
- Existing tests cover detector validation, alert policy, immune memory, and intervention engine.

### 6.2 Operational checks

- Confirm the detector is writing `cis_status.json` correctly.
- Confirm the dashboard can fetch `/status` and `/alerts-json`.
- Verify the login flow with active user accounts in the SQLite database.

### 6.3 Current validation status

- Local dependency installation completed successfully via `cis/requirements.txt`.
- `pytest -q` passed with all tests green.
- `ruff check .` passed after auto-fixes and manual lint cleanup.
- `test_startup.py` passed, validating imports and CIS runtime initialization.
- CI-style validation scripts were executed successfully with `PYTHONPATH` set to the repository root.
- The branch `feature/autonomous-cis` was pushed successfully and the active PR was updated.

### 6.4 Known system checks

- The dashboard now accepts either email or username for login.
- If login still fails, confirm the account exists in `~/.cis_billing.db`.
- Recent active user accounts include:
  - `fonkemgodson7@gmal.com` / `fonkemgodson`
  - `fonkemgodson7@gmail.com` / `godson1`
  - `godson1@gmail.com` / `godsonfonkem`

## 7. Observations and Recommendations

- The prototype supports a full end-to-end demo flow, but production deployment requires hardened secret management and stronger session handling.
- Add a formal user-management UI for account creation and password reset.
- Add metrics export and health-check endpoints for external monitoring.
- Consider consolidating the legacy dashboard assets with the new `dashboard_new.py` UI.
- Implement a backup strategy for `cis/immune_memory`, `cis/cis_alerts.jsonl`, and `cis/acknowledged_alerts.json`.

## 8. Appendix — Important Files

- `cis/main_detector.py` — core detection engine
- `cis/dashboard_new.py` — modern dashboard server
- `cis/alert_explanation.py` — alert explainability module
- `cis/billing_api.py` — subscription and billing routes
- `cis/auth.py` — login/password utilities
- `cis/database.py` — SQLite user and subscription storage
- `cis/config.example.json` — sample runtime configuration
- `deploy/container/docker-compose.yml` — container orchestration
- `ebpf/Makefile` — eBPF build script
- `installer/build_installer_windows.bat` — Windows installer build

---

This report is now saved to `COMPLETE_SYSTEM_REPORT.md` and reflects the current system status, architecture, and deployment guidance.
