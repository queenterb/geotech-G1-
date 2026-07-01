# Causal Immune Sentinel (CIS)

CIS is a real-time ransomware detection and response platform combining:
- software telemetry capture
- side-channel feature sampling
- anticipatory detection logic
- response orchestration and alerting

## Project Structure
- `cis/` Python runtime and training code
- `ebpf/` Linux kernel-space/user-space telemetry components
- `deploy/` deployment assets (systemd, container, scripts)

## Local Production Run
1. From the repository root, create or activate the workspace virtual environment.
2. Install runtime dependencies: `pip install -r cis/requirements.txt`
3. Start the service: `python -m cis.service`
4. Open the portal at `http://127.0.0.1:8000` once the service is running.

## Local Run with ngrok Tunnel (Windows)
1. From the repository root, activate the workspace virtual environment.
2. Run `deploy\scripts\start_cis_and_ngrok.ps1 -AuthToken <your-ngrok-token>`.
3. Keep the PowerShell session open while the tunnel is active.
4. The script prints the public ngrok URL once it is ready.

## Linux Host Deployment
Use `deploy/scripts/install_cis.sh` as root, then configure/build the eBPF loader in `ebpf/` and start systemd services.

## Validation and Smoke Test
- Health check: `python test_startup.py`
- End-to-end readiness check: `python -m pytest cis/tests/test_production_foundation.py -q`

These checks verify that the service starts, loads configuration, and maintains the required runtime foundation.

## Unit Tests
From the repository root run:
- `python -m unittest discover -s cis/tests -p "test_*.py" -v`

Alternatively, from `cis/` run:
- `python -m pytest tests -q`

> Note: the tests use package imports from `cis`, so the discover path must include `cis/tests`.

## Hardening Applied
- Strict event payload validation before queueing
- Rotating runtime logs for detector daemon
- systemd service sandboxing (no new privileges, protected system paths, constrained write paths)
- Container runtime hardening (read-only rootfs, dropped capabilities, no-new-privileges)

## Important
The service is intended for real deployment use and now uses live configuration selection, persistent authentication, and runtime logging. Components that require privileged Linux integration may still need platform-specific deployment steps.

## Planned Modern Dashboard
A future CIS dashboard implementation is planned as a full-stack system with:
- React + TypeScript + Tailwind CSS + Framer Motion for the frontend
- FastAPI backend with WebSocket live event streaming
- PostgreSQL for persistence and Redis for caching / queueing
- JWT authentication with role-based access control
- Docker + Nginx deployment
- Recharts or Apache ECharts for charts, and Mapbox GL / Leaflet for the attack map

See `CIS_DASHBOARD_ARCHITECTURE.md` for the proposed dashboard architecture and implementation roadmap.
