#!/usr/bin/env bash
# =============================================================
# Tessaris — Full Resonance Cycle Launcher (Aion Stack)
# Path: backend/scripts/run_full_resonance_cycle.sh
# =============================================================
# Launches all core Aion intelligence modules in correct dependency order.
# Performs automated resonance feedback & SQI lock-in stabilization.
# =============================================================

set -e

echo ""
echo "🌐 Tessaris Resonance Stack Boot Sequence"
echo "─────────────────────────────────────────────"
echo "📦 Base Path: $(pwd)"
echo ""

# Activate Python environment if present
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  echo "✅ Virtual environment activated."
fi

# Ensure Python can locate backend modules
export PYTHONPATH=".:backend:$PYTHONPATH"

# Ensure required directories exist
mkdir -p data/logs data/prediction data/predictive data/analysis

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
# 🌊 Resonance Feedback Integration (Aion ↔ PBL ↔ SQI)
# ─────────────────────────────────────────────
echo ""
echo "🔁 Integrating Resonance Feedback Loop with Aion Core..."
LOG_FILE="data/analysis/resonance_feedback.log"
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

{
  echo "───────────────────────────────────────────────"
  echo "🕓 Feedback Cycle @ $timestamp"
  echo "🔮 Refreshing Predictive Bias Layer..."
} >> "$LOG_FILE"

# Refresh predictive model (rebuild temporal bias)
PYTHONPATH=. python backend/modules/aion_prediction/predictive_bias_layer.py --refresh >> "$LOG_FILE" 2>&1

{
  echo "🧠 Applying PAL Resonance Feedback..."
} >> "$LOG_FILE"

# Inject predictive transitions into PAL for reinforcement
PYTHONPATH=. python backend/modules/aion_perception/pal_core.py --mode=resonance-feedback --sync=1 >> "$LOG_FILE" 2>&1

# SQI resonance pulse — reinforces PAL adaptation based on predictive state
if [ -f "backend/modules/aion_perception/qwave.py" ]; then
  {
    echo "🌊 Executing SQI stabilization pulse..."
  } >> "$LOG_FILE"
  PYTHONPATH=. python backend/modules/aion_perception/qwave.py --pulse=stabilize --gain=0.35 --damping=0.88 >> "$LOG_FILE" 2>&1
fi

{
  echo "💾 SQI lock-in checkpoint: pal_state_SQI_Stabilized_v2.json"
  echo "✅ Resonance feedback cycle complete — Aion Core synchronized."
  echo ""
} >> "$LOG_FILE"

echo "✅ Resonance feedback cycle complete — Aion Core synchronized."
echo "📜 Log written to: $LOG_FILE"

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
echo "📈 Feedback Cycles: data/analysis/resonance_feedback.log"
echo ""
echo "🧩 Tessaris Aion stack initialized — ready for Uvicorn."
echo "Example: uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo ""

exit 0