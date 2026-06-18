# Causal Immune Sentinel (CIS)

CIS is a research-oriented ransomware detection prototype combining:
- software telemetry capture (eBPF sample)
- side-channel feature sampling
- anticipatory LSTM-GNN prediction
- counterfactual decision logic

## Project Structure
- `cis/` Python runtime and training code
- `ebpf/` Linux kernel-space/user-space telemetry components
- `deploy/` deployment assets (systemd, container, scripts)

## Local Prototype Run
1. `cd cis`
2. `python -m venv .venv`
3. activate virtual environment
4. `pip install -r requirements.txt`
5. `python train.py --epochs 2 --save models/lstm_gnn_scripted.pt`
6. `python main_detector.py`

## Linux Host Deployment
Use `deploy/scripts/install_cis.sh` as root, then configure/build the eBPF loader in `ebpf/` and start systemd services.

## Validation and Smoke Test
- Health check: `sudo /usr/local/bin/cis-health`
- End-to-end prototype smoke test: `sudo /usr/local/bin/cis-smoke-test`

The smoke test verifies model training, daemon startup, synthetic event flow, and alert output.

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
This repository is a prototype for controlled environments. Components that require privileged Linux integration (eBPF loading, Firecracker replay, ZFS rollback) are represented as stubs or examples.
