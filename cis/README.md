# Causal Immune Sentinel (CIS) Prototype

This repository contains a research-oriented prototype of a ransomware detection pipeline with these modules:
- Sensor and side-channel acquisition
- Anticipatory LSTM-GNN model
- Counterfactual simulation stub
- Main orchestration daemon
- eBPF sample sources for software telemetry capture

## Scope
This code is defensive and intended for controlled lab environments only.

## Repository Layout
- `cis/`: Python modules for model training and runtime orchestration.
- `ebpf/`: Linux eBPF probe and userspace loader sample code.
- `deploy/systemd/`: systemd unit files for host deployment.
- `deploy/container/`: container image and compose example.
- `deploy/scripts/`: host install and health-check scripts.

## Quick Start (Prototype Mode)
1. Create a Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Train a baseline model and export TorchScript:
   - `python train.py --epochs 2 --save models/lstm_gnn_scripted.pt`
4. Start the detector daemon:
   - `python main_detector.py`

The prototype mode uses:
- pseudo-power estimates (instead of Intel RAPL)
- disk I/O derived acoustic fallback (instead of microphone)
- heuristic counterfactual simulation (instead of full Firecracker replay)

## Files
- `dataset_preparation.py`: sequence dataset utilities
- `model.py`: Anticipatory LSTM-GNN definition
- `train.py`: baseline training script
- `side_channel_daemon.py`: side-channel sampling daemon (fallback mode)
- `digital_twin_controller.py`: counterfactual simulation interface
- `immune_memory.py`: clonal-selection immune memory module
- `intervention_engine.py`: process isolation and optional rollback wrapper
- `simulate_events.py`: synthetic eBPF-like JSON event generator
- `main_detector.py`: integration loop

## Smoke Test
On Linux, run:
- `bash ../deploy/scripts/smoke_test.sh`

This will train a quick model, start the daemon, inject synthetic events, and verify that alerts are produced.

## Sending Test Events to the Daemon
`main_detector.py` listens for JSON lines on `/tmp/cis_ebpf_events.sock`.

Example JSON line format:

`{"pid":1234,"uid":1000,"timestamp":1710000000.1,"comm":"proc","filename":"/tmp/a.txt","op_type":2}`

You can use the Linux eBPF loader sample in `../ebpf` or any local test sender that writes JSONL over a Unix domain socket.

## Linux Deployment (systemd)
1. Build and install binaries/scripts on a Linux host.
2. Copy `cis/` to `/opt/cis`.
3. Install Python dependencies from `/opt/cis/requirements.txt`.
4. Install unit files from `../deploy/systemd` to `/etc/systemd/system`.
5. Enable services:
   - `cis-ebpf-loader.service`
   - `cis-sidechannel.service`
   - `cis-digital-twin.service`
   - `cis-main.service`
   - `cis-health.timer`

The helper script `../deploy/scripts/install_cis.sh` automates the majority of these steps.

## Container Notes
The container image in `../deploy/container/Dockerfile` is for prototype packaging only.
Kernel eBPF loading and full hardware access still require host-level privileges and Linux support.

## Notes
- `main_detector.py` expects JSONL events over a Unix domain socket at `/tmp/cis_ebpf_events.sock`.
- Firecracker and ZFS integration are represented as stubs/placeholders in this prototype.
- eBPF code is under `../ebpf` and requires Linux to compile/run.

## Runtime Artifacts
- Status file: `/tmp/cis_status.json`
- Heartbeat file: `/tmp/cis_heartbeat`
- Alerts file: `/tmp/cis_alerts.jsonl`
- Rotating daemon log: `/tmp/cis_main.log`

## Config Overrides
`main_detector.py` supports `--config path/to/config.json` and merges with defaults.
Useful keys include:
- `divergence_threshold`
- `heuristic_write_threshold`
- `alerts_file`
- `status_file`
- `heartbeat_file`
- `log_file`
- `log_max_bytes`
- `log_backup_count`
