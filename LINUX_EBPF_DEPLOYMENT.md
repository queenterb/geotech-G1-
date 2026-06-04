# CIS eBPF Linux Deployment Guide

**Target**: Linux 5.8+, root/CAP_SYS_RESOURCE privileges  
**Status**: Production-ready eBPF kernel module with userspace loader  
**Compilation**: clang/LLVM + libbpf + bpftool

---

## Table of Contents

1. [Quick Start (WSL2 on Windows)](#quick-start-wsl2)
2. [Native Linux Deployment](#native-linux)
3. [Container-Based Deployment](#container-deployment)
4. [eBPF Compilation Details](#ebpf-compilation)
5. [Production Validation](#production-validation)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start (WSL2)

### Prerequisites

- Windows 11 with WSL2 enabled
- Ubuntu 22.04 LTS or later in WSL2
- ~2GB disk space, ~500MB RAM

### Step 1: Set Up WSL2 Ubuntu

```powershell
# From Windows PowerShell (admin)
wsl --install -d Ubuntu-22.04
wsl --set-version Ubuntu-22.04 2
```

Wait for Ubuntu to initialize, then set your username/password.

### Step 2: Enter WSL2 Environment

```bash
# From Windows PowerShell
wsl -d Ubuntu-22.04

# Or directly from Windows Terminal (if installed)
# Select Ubuntu-22.04 from dropdown
```

### Step 3: Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
  clang llvm libbpf-dev libelf-dev zlib1g-dev \
  bpftool gcc make git \
  python3 python3-pip python3-venv python3-dev \
  linux-headers-$(uname -r)
```

### Step 4: Clone/Copy CIS Repository

**Option A**: From Windows, copy the project folder:

```bash
# In WSL2 terminal
cp -r /mnt/c/Users/TECHWAVE/Desktop/GEOTECH\\(G1\\) ~/cis_project
cd ~/cis_project
```

**Option B**: Or re-download if you prefer:

```bash
cd ~
git clone <your-repo-url>  # If using version control
cd GEOTECH_G1
```

### Step 5: Compile eBPF Components

```bash
cd ebpf
make clean
make all
ls -la detector_loader
```

Expected output:
```
-rwxr-xr-x 1 user user 45K Apr 13 11:45 detector_loader
```

### Step 6: Install Python Dependencies

```bash
cd ~/cis_project/cis
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt
```

### Step 7: Run the System (Non-Root for Initial Test)

```bash
# Terminal 1: Start main detector (uses Unix socket on Linux)
cd ~/cis_project/cis
python3 main_detector.py

# Terminal 2: Inject synthetic events
cd ~/cis_project/cis
python3 simulate_events.py --count 500 --write-ratio 0.98

# Terminal 3: Monitor alerts
tail -f /tmp/cis_alerts.jsonl
```

### Step 8: Run Full Smoke Test (Root Required)

```bash
cd ~/cis_project
chmod +x deploy/scripts/smoke_test.sh
sudo ./deploy/scripts/smoke_test.sh
```

---

## Native Linux Deployment

### Prerequisites

- Ubuntu 22.04 LTS or RHEL/CentOS 8+
- Linux kernel 5.8 or later
- Root access or CAP_SYS_RESOURCE capability
- 2GB RAM, 1GB disk

### Step 1: Download Repository

```bash
cd /tmp
git clone <your-repo-url>
cd GEOTECH_G1
```

### Step 2: Run Automated Installation

```bash
sudo ./deploy/scripts/install_cis.sh
```

This script will:
- Install all build and runtime dependencies
- Create `cis` system user
- Create `/opt/cis` and `/var/log/cis` directories
- Install Python dependencies
- Copy systemd service files

### Step 3: Build eBPF Loader

```bash
cd /opt/cis/../ebpf
sudo make clean
sudo make all
sudo cp detector_loader /opt/cis/
```

### Step 4: Verify Installation

```bash
sudo systemctl enable cis-ebpf-loader.service
sudo systemctl enable cis-main.service
sudo systemctl enable cis-sidechannel.service

sudo systemctl daemon-reload
```

### Step 5: Start Services

```bash
# Start eBPF loader first
sudo systemctl start cis-ebpf-loader.service
sleep 2

# Start main detector
sudo systemctl start cis-main.service

# Start side-channel sampler
sudo systemctl start cis-sidechannel.service
```

### Step 6: Monitor Alerts

```bash
# Real-time alert stream
sudo tail -f /var/log/cis/alerts.jsonl

# Or use journalctl
sudo journalctl -u cis-main.service -f
```

### Step 7: Verify Functionality

```bash
# Check if socket is listening
sudo netstat -an | grep cis_ebpf

# Check systemd status
sudo systemctl status cis-main.service
sudo systemctl status cis-ebpf-loader.service

# View recent logs
sudo journalctl -u cis-main.service -n 20
```

---

## Container-Based Deployment

### Prerequisites

- Docker 20.10+ or Podman 3.0+
- ~1GB available disk
- Internet access (for base image pull)

### Step 1: Build Docker Image

```bash
cd ~/cis_project/deploy/container
docker build -f Dockerfile -t cis-detector:latest .
```

### Step 2: Run Container

```bash
# Using Docker Compose
cd ~/cis_project/deploy/container
docker-compose up -d

# Or with Podman
podman-compose up -d

# Check it's running
docker ps | grep cis
```

### Step 3: Access Running Container

```bash
# Monitoring alerts from host
docker exec cis-detector tail -f /var/log/cis/alerts.jsonl

# Shell into container
docker exec -it cis-detector /bin/bash

# Inside container, inject events
python3 /opt/cis/simulate_events.py --count 500 --write-ratio 0.98
```

### Step 4: Stop and Clean Up

```bash
docker-compose down
docker image rm cis-detector:latest
```

---

## eBPF Compilation Details

### What Gets Compiled

**Input Files:**
- `ransomware_detector.bpf.c` — eBPF kernel program (GPL licensed)
- `detector_loader.c` — Userspace loader application

**Output Files:**
- `ransomware_detector.bpf.o` — Compiled BPF object file
- `ransomware_detector.skel.h` — Generated header with skeleton
- `detector_loader` — Linked userspace binary

### Compilation Steps (Manual)

```bash
# Step 1: Compile eBPF bytecode
clang -target bpf -g -O2 -c ransomware_detector.bpf.c -o ransomware_detector.bpf.o

# Step 2: Generate skeleton header
bpftool gen skeleton ransomware_detector.bpf.o > ransomware_detector.skel.h

# Step 3: Compile userspace loader
gcc -O2 -g detector_loader.c -o detector_loader -lbpf -lelf -lz

# Step 4: Verify
file detector_loader ransomware_detector.bpf.o
```

### Verifier Output (Expected on Linux 5.8+)

When you run the loader, the kernel eBPF verifier will check safety:

```
libbpf: loaded object 'ransomware_detector'
libbpf: prog 'trace_openat': BPF program has 18 instructions
libbpf: prog 'trace_openat': BPF verifier passed
libbpf: prog 'trace_unlinkat': BPF program has 14 instructions
libbpf: prog 'trace_unlinkat': BPF verifier passed
```

---

## Production Validation

### Test 1: Verify eBPF Loading

```bash
# This should show loaded eBPF programs
sudo bpftool prog list

# Expected output:
# 1: tracepoint  name trace_openat  tag ab12cd34... 
# 2: tracepoint  name trace_unlinkat tag ef56gh78...
```

### Test 2: Monitor Real File Operations

```bash
# Terminal 1: Start detector
sudo /opt/cis/ebpf/detector_loader

# Terminal 2: Create files and watch events
cd /tmp
for i in {1..100}; do
  echo "test data" > test_file_$i.txt
  rm test_file_$i.txt
done

# Terminal 3: Should see events flowing through CIS
```

### Test 3: Trigger Real Detection

```bash
# Create a simulated encryption pattern
cd /tmp
for i in {1..500}; do
  dd if=/dev/urandom of=critical_file_$i.bin bs=1K count=1 2>/dev/null
  shred -fvz critical_file_$i.bin
done

# Monitor alerts
tail -f /var/log/cis/alerts.jsonl
```

### Test 4: Performance Baseline

```bash
# Run synthetic workload and measure
time python3 /opt/cis/simulate_events.py --count 10000 --write-ratio 0.95

# Check resource consumption
# In another terminal:
watch -n 1 'ps aux | grep detector_loader'
```

---

## Systemd Service Management

### Start/Stop

```bash
# Start all CIS services
sudo systemctl start cis-ebpf-loader
sudo systemctl start cis-main

# Stop all
sudo systemctl stop cis-main
sudo systemctl stop cis-ebpf-loader

# Restart with fresh state
sudo systemctl restart cis-main
```

### Logs

```bash
# Follow real-time logs
sudo journalctl -u cis-main.service -f

# Last 50 lines
sudo journalctl -u cis-main.service -n 50

# Since this morning
sudo journalctl -u cis-main.service --since today

# All eBPF loader errors
sudo journalctl -u cis-ebpf-loader.service -p err
```

### Health Checks

```bash
# Systemd timer runs periodic health checks
sudo systemctl status cis-health.timer

# View last health check results
sudo systemctl status cis-health.service

# View output of last 5 checks
sudo journalctl -u cis-health.service -n 5
```

---

## Troubleshooting

### Issue: "Permission denied" compiling eBPF

**Solution**: Run with sudo or ensure user is in `root` group
```bash
sudo make clean && sudo make all
```

### Issue: "libbpf not found" during compilation

**Solution**: Install libbpf development packages
```bash
sudo apt-get install libbpf-dev libelf-dev zlib1g-dev
```

### Issue: eBPF program fails to load (kernel 5.7 or older)

**Solution**: Update kernel to 5.8+
```bash
# Check current version
uname -r

# On Ubuntu, update kernel packages
sudo apt-get install linux-image-generic-hwe
sudo reboot
```

### Issue: "Operation not permitted" when starting detector_loader

**Solution**: Must run as root or with CAP_SYS_RESOURCE
```bash
sudo ./detector_loader

# Or if using systemd, it will handle privileges automatically
sudo systemctl start cis-ebpf-loader
```

### Issue: No events appearing in alerts

**Debugging steps:**
```bash
# 1. Verify eBPF programs loaded
sudo bpftool prog list | grep trace_

# 2. Check if socket is listening
sudo netstat -an | grep cis_ebpf

# 3. Verify detector is running
sudo systemctl status cis-main

# 4. Generate test events
python3 /opt/cis/simulate_events.py --count 100 --write-ratio 0.9

# 5. Check alert file
sudo tail -f /var/log/cis/alerts.jsonl
```

### Issue: High CPU/memory consumption

**Solution**: Tune event buffer sizes
```bash
# Edit /opt/cis/main_detector.py
# Reduce event_queue maxsize from 50000 to 10000
# Reduce side_samples buffer

# Or increase snapshot interval
# CONFIG["snapshot_interval"] = 10.0  # instead of 5.0
```

---

## Performance Tuning

### For High-Volume Environments

```python
# In cis/main_detector.py CONFIG:
CONFIG = {
    # Increase buffer capacities
    "ebpf_socket_buffer": 256 * 1024,      # 256KB ring buffer
    "event_queue_maxsize": 100000,         # High capacity
    "side_sample_buffer_size": 10000,
    
    # Tune prediction windows
    "prediction_window": 10.0,              # Longer lookahead
    "counterfactual_lookback_ms": 100,     # More history
    
    # Adjust thresholds
    "divergence_threshold": 0.25,          # More sensitive
    "heuristic_write_threshold": 50,       # Lower threshold
}
```

### For Resource-Constrained Environments

```python
CONFIG = {
    # Minimal buffers
    "event_queue_maxsize": 5000,
    "side_sample_buffer_size": 1000,
    
    # Less frequent snapshots
    "snapshot_interval": 15.0,              # Every 15 seconds
    
    # Relaxed thresholds
    "divergence_threshold": 0.5,
    "heuristic_write_threshold": 200,
}
```

---

## Next: Real Attack Simulation

Once the Linux eBPF system is running:

```bash
# Run comprehensive attack scenarios
cd ~/cis_project
./run_full_attack_suite.sh

# Expected output:
# Scenario 1: Locker ransomware (high entropy)
# Scenario 2: Wiper malware (complete deletion)
# Scenario 3: Cryptolocker variant (staged encryption)
# Scenario 4: Multi-process attack coordination
```

---

## Support & References

- **Linux eBPF Docs**: https://ebpf.io/
- **libbpf Reference**: https://github.com/libbpf/libbpf
- **Kernel Tracepoints**: `/sys/kernel/debug/tracing/events/syscalls/`
- **Project Issues**: See GitHub repository

---

## Summary

| Platform | Time to Deploy | Complexity | Best For |
|----------|----------------|-----------|----------|
| **WSL2** | 15 minutes | Low | Testing on Windows |
| **Native Linux** | 30 minutes | Medium | Production server |
| **Container** | 10 minutes | Low | Isolated environments |
| **eBPF Only** | 5 minutes | Medium | Kernel integration testing |

Choose your path above and report back with results!
