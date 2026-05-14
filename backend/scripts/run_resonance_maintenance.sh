#!/usr/bin/env bash
# Tessaris — Adaptive Resonance Maintenance Cycle
set -e
export PYTHONPATH=".:backend:$PYTHONPATH"

echo ""
echo "🌀 Tessaris Resonance Maintenance Cycle"
echo "──────────────────────────────────────────"

# Step 1 — Update PredictiveBias transitions from latest PAL logs
PYTHONPATH=. python backend/modules/aion_prediction/predictive_bias_layer.py --mode=update

# Step 2 — Apply Resonance Feedback Reinforcement to PAL
PYTHONPATH=. python backend/modules/aion_perception/pal_core.py --mode=resonance-feedback

# Step 3 — Apply QWave stabilization pulse (auto-tuned)
PYTHONPATH=. python backend/modules/aion_perception/qwave.py --pulse=auto --gain=0.31 --damping=0.89

echo "✅ Maintenance cycle complete — Tessaris Core equilibrated."