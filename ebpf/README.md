# eBPF Components

This folder contains sample CIS software telemetry collectors:
- `ransomware_detector.bpf.c` kernel-space eBPF program
- `detector_loader.c` userspace loader and ring-buffer consumer

## Build (Linux)
Prerequisites:
- clang/llvm
- bpftool
- libbpf-dev, libelf-dev, zlib1g-dev

Example steps:
1. `clang -target bpf -g -O2 -c ransomware_detector.bpf.c -o ransomware_detector.bpf.o`
2. `bpftool gen skeleton ransomware_detector.bpf.o > ransomware_detector.skel.h`
3. `gcc -O2 -g detector_loader.c -o detector_loader -lbpf -lelf -lz`

## Runtime
Start the Python daemon first (`cis/main_detector.py`), then run:
- `sudo ./detector_loader`

The loader forwards events as JSONL over `/tmp/cis_ebpf_events.sock`.
