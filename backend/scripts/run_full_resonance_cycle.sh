#!/usr/bin/env bash
# =============================================================
# Tessaris — Full Resonance Cycle Launcher (Aion Stack)
# Path: backend/scripts/run_full_resonance_cycle.sh
# =============================================================
# Launches all core Aion intelligence modules in correct dependency order.
# Designed to run in parallel with Uvicorn without blocking it.
# =============================================================

set -e

echo ""
echo "🌐 Tessaris Resonance Stack Boot Sequence"
echo "─────────────────────────────────────────────"
echo "📦 Base Path: $(pwd)"
echo ""

# Activate Python environment if needed
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  echo "✅ Virtual environment activated."
fi

# Ensure Python can find backend modules
export PYTHONPATH=".:backend:$PYTHONPATH"

# Ensure log directory
mkdir -p data/logs

# ─────────────────────────────────────────────
# 1️⃣ Aion Perception — PAL Core
# ─────────────────────────────────────────────
echo "🧠 Launching PAL Core (Perceptual Association Layer)..."
nohup python backend/modules/aion_perception/pal_core.py > data/logs/pal_core.log 2>&1 &
PAL_PID=$!
sleep 3

# ─────────────────────────────────────────────
# 2️⃣ Aion Prediction — Temporal Model / Predictive Bias
# ─────────────────────────────────────────────
echo "🔮 Launching Predictive Bias Layer..."
nohup python backend/modules/aion_prediction/predictive_bias_layer.py > data/logs/predictive_bias.log 2>&1 &
PB_PID=$!
sleep 3

# ─────────────────────────────────────────────
# 3️⃣ Aion Resonance — QWave / SQI Field
# ─────────────────────────────────────────────
if [ -f "backend/modules/aion_perception/qwave.py" ]; then
  echo "🌊 Launching QWave Resonance Field (SQI Engine)..."
  nohup python backend/modules/aion_perception/qwave.py > data/logs/qwave.log 2>&1 &
  QW_PID=$!
  sleep 3
else
  echo "⚠️ QWave module not found (backend/modules/aion_perception/qwave.py)"
fi

# ─────────────────────────────────────────────
# 4️⃣ Aion Analysis — PAL Snapshot
# ─────────────────────────────────────────────
if [ -f "backend/modules/aion_analysis/pal_snapshot.py" ]; then
  echo "📊 Launching PAL Snapshot Analyzer..."
  nohup python backend/modules/aion_analysis/pal_snapshot.py > data/logs/pal_snapshot.log 2>&1 &
  SNAP_PID=$!
  sleep 2
fi

# ─────────────────────────────────────────────
# ✅ Summary
# ─────────────────────────────────────────────
echo ""
echo "🚀 Aion Intelligence Stack Online"
echo "----------------------------------------------"
echo "PAL Core PID:          ${PAL_PID:-not running}"
echo "Predictive Bias PID:   ${PB_PID:-not running}"
echo "QWave Resonance PID:   ${QW_PID:-not running}"
echo "PAL Snapshot PID:      ${SNAP_PID:-not running}"
echo "----------------------------------------------"
echo "💠 Logs: data/logs/"
echo ""
echo "🧩 Aion stack initialized. Safe to start Uvicorn now."
echo "Example: uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo ""

exit 0