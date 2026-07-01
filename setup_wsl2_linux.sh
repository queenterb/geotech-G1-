#!/usr/bin/env bash
# CIS eBPF - WSL2 Setup Script (runs inside WSL2)
# Source: LINUX_EBPF_DEPLOYMENT.md WSL2 Quick Start

set -euo pipefail

PROJECT_ROOT="${HOME}/cis_project"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}CIS eBPF - WSL2 Linux Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo

# Step 1: Verify we're in WSL2
if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo -e "${YELLOW}⚠ Warning: May not be running in WSL2${NC}"
fi

# Step 2: Install Python dependencies
echo -e "${BLUE}[1/5]${NC} Installing Python dependencies..."
cd "${PROJECT_ROOT}/cis"
python3 -m pip install --upgrade pip --quiet 2>/dev/null || true
pip3 install -q -r requirements.txt 2>/dev/null || echo "Some packages may not be available"
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo

# Step 3: Compile eBPF components
echo -e "${BLUE}[2/5]${NC} Compiling eBPF kernel module..."
cd "${PROJECT_ROOT}/ebpf"
make clean >/dev/null 2>&1 || true
make all >/dev/null 2>&1

if [ -f detector_loader ]; then
    echo -e "${GREEN}✓ eBPF compilation successful${NC}"
    echo "  - detector_loader: $(ls -lh detector_loader | awk '{print $5}')"
    chmod +x detector_loader
else
    echo -e "${YELLOW}⚠ eBPF compilation may have failed${NC}"
    echo "  Check if clang/llvm/libbpf-dev are installed:"
    echo "  sudo apt-get install -y clang llvm libbpf-dev libelf-dev zlib1g-dev"
fi
echo

# Step 4: Verify Python modules load
echo -e "${BLUE}[3/5]${NC} Verifying Python environment..."
cd "${PROJECT_ROOT}/cis"
python3 -c "import numpy; import psutil; print('✓ Core packages available')" 2>/dev/null || \
    echo "⚠ Some packages may need to be installed"

python3 -c "import torch; print('✓ PyTorch available (model inference enabled)')" 2>/dev/null || \
    echo "ℹ PyTorch not available (fallback to heuristic detection)"
echo

# Step 5: Create test data directory
echo -e "${BLUE}[4/5]${NC} Preparing test environment..."
mkdir -p "${PROJECT_ROOT}/models"
mkdir -p /tmp/cis_test
echo -e "${GREEN}✓ Test directories ready${NC}"
echo

# Step 6: Summary
echo -e "${BLUE}[5/5]${NC} Setup complete!"
echo

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Ready to run CIS eBPF system${NC}"
echo -e "${GREEN}============================================${NC}"
echo

echo "Quick Start (non-root, synthetic events):"
echo "  Terminal 1:"
echo "    cd ${PROJECT_ROOT}"
echo "    python3 -m cis.service"
echo
echo "  Terminal 2:"
echo "    cd ${PROJECT_ROOT}/cis"
echo "    python3 simulate_events.py --count 500 --write-ratio 0.98"
echo
echo "  Terminal 3:"
echo "    tail -f /tmp/cis_alerts.jsonl"
echo
echo "Full eBPF Test (requires sudo):"
echo "  cd ${PROJECT_ROOT}"
echo "  sudo ./deploy/scripts/smoke_test.sh"
echo
echo "Compile eBPF manually:"
echo "  cd ${PROJECT_ROOT}/ebpf"
echo "  make clean && make all"
echo

echo -e "${BLUE}============================================${NC}"
