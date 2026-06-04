# CIS Complete System Executive Summary

## Purpose

This summary provides a concise overview of the CIS (Causal Immune Sentinel) system, including architecture, deployment, runtime behavior, access control, and current operational status.

## System Overview

CIS is a ransomware detection prototype that combines:
- event ingestion from eBPF or TCP-based sensors
- side-channel telemetry sampling
- anticipatory machine learning prediction
- custom alert rule and heuristic detection
- explainable alert output
- realtime dashboard monitoring
- billing and trial-based access control

## Core Components

- `cis/main_detector.py`: main runtime, event ingestion, model scoring, alert generation, status writing
- `cis/alert_explanation.py`: generates alert summary, root cause, impact, and recommended action
- `cis/dashboard_new.py`: modern dashboard server, login, billing, status and alert APIs
- `cis/auth.py` & `cis/database.py`: user authentication, password hashing, trial/subscription storage
- `cis/side_channel_daemon.py`: host telemetry sampling for power, CPU temperature, acoustic intensity
- `cis/billing_api.py`: subscription lifecycle and billing routes
- `cis/cis_alerts.jsonl`: alert stream storage
- `cis/cis_status.json`: realtime telemetry for dashboard

## Deployment Options

### Local prototype

- Windows: use `quickstart.bat`
- Linux: use `quickstart.sh`
- Setup includes creating a Python venv, installing dependencies, and running the detector and dashboard

### Containers

- Container definitions in `deploy/container/docker-compose.yml`
- Dockerfile in `deploy/container/Dockerfile`
- Use compose or container build for service orchestration

### Systemd

- Linux service units are available under `deploy/systemd/`
- Use systemd to manage long-running daemons in production-like deployments

## Current Status & Notes

- Dashboard process is running at `http://127.0.0.1:5000`
- Detector process is active in the local virtual environment
- Login now accepts either email or username
- Existing active accounts in `~/.cis_billing.db` include:
  - `fonkemgodson7@gmal.com` / username `fonkemgodson`
  - `fonkemgodson7@gmail.com` / username `godson1`
  - `godson1@gmail.com` / username `godsonfonkem`

## Key Recommendations

- Add external monitoring and health endpoints
- Harden secret storage and session management
- Consolidate dashboard assets and remove legacy duplicates
- Add CI to run tests and deploy container images
- Backup critical state files: `cis/immune_memory`, `cis/cis_alerts.jsonl`, `cis/acknowledged_alerts.json`

## How to Use

1. Start the detector: `cd cis && .venv\Scripts\python.exe main_detector.py`
2. Start the dashboard: `cd cis && .venv\Scripts\python.exe dashboard_new.py`
3. Access the UI at `http://127.0.0.1:5000`
4. Login with email or username and your password

## File Locations

- `COMPLETE_SYSTEM_REPORT.md`: full system report
- `COMPLETE_SYSTEM_SUMMARY.md`: this executive summary
- `cis/dashboard_new.py`: active dashboard and login server
- `cis/main_detector.py`: runtime event engine
- `cis/database.py`: login and subscription storage
- `deploy/container/`: container artifacts
- `ebpf/`: eBPF detector sources
