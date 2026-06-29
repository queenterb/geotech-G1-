#!/usr/bin/env bash
# Quick Start: CIS Local Prototype (Cross-Platform)

set -euo pipefail

echo "=== CIS Quick Start (Prototype Mode) ==="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ and try again."
    exit 1
fi

cd "$(dirname "$0")/cis"

echo "📦 Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

echo "📚 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "🧠 Training model..."
python train.py --epochs 1 --save models/lstm_gnn_scripted.pt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the unified service (detector + portal in one terminal):"
echo "  cd .. && python -m cis.service"
echo ""
echo "To inject test events (in another terminal):"
echo "  cd cis && source .venv/bin/activate && python simulate_events.py"
echo ""
echo "To monitor alerts in real-time:"
echo "  tail -f /tmp/cis_alerts.jsonl"
echo ""
echo "To access the web portal:"
echo "  http://localhost:8000"
echo ""
