#!/usr/bin/env bash
# =============================================================
# Tessaris — Continuous Resonance Synchronization Loop
# Path: backend/scripts/run_resonance_sync_loop.sh
# =============================================================
# This script continuously performs full resonance feedback cycles
# between PAL (Perceptual Layer), PredictiveBias (Temporal Model),
# and SQI (QWave Resonance Field).
# =============================================================

set -e

echo ""
echo "🌀 Tessaris Resonance Synchronization Loop — Active"
echo "──────────────────────────────────────────────────────────"
echo "📂 Base Path: $(pwd)"
echo ""

# Ensure directories
mkdir -p data/logs data/analysis

# Activate venv if available
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  echo "✅ Virtual environment activated."
fi

# Ensure Python path
export PYTHONPATH=".:backend:$PYTHONPATH"

# Default sync interval (seconds)
SYNC_INTERVAL=${1:-300}

# Log file for tracking cycles
LOG_FILE="data/analysis/resonance_feedback.log"

echo "🔁 Synchronization interval: every ${SYNC_INTERVAL}s"
echo "📜 Logging cycles to → ${LOG_FILE}"
echo ""

# =============================================================
# Infinite feedback loop
# =============================================================
while true; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧠 [$(date '+%Y-%m-%d %H:%M:%S')] Starting resonance sync cycle..."

    # 1️⃣ Refresh Predictive Bias Layer (learn from latest PAL events)
    PYTHONPATH=. python backend/modules/aion_prediction/predictive_bias_layer.py >> data/logs/predictive_bias_loop.log 2>&1
    echo "   🔮 Predictive bias layer updated."

    # 2️⃣ Apply Resonance Feedback into PAL Core
    PYTHONPATH=. python backend/modules/aion_perception/pal_core.py --mode=resonance-feedback >> data/logs/pal_feedback_loop.log 2>&1
    echo "   🧩 PAL resonance feedback applied."

    # 3️⃣ SQI Resonance Pulse Reinforcement
    PYTHONPATH=. python backend/modules/aion_perception/qwave.py --pulse=stabilize --gain=0.35 --damping=0.88 >> data/logs/qwave_loop.log 2>&1
    echo "   🌊 SQI pulse reinforcement complete."

    # 4️⃣ Log the successful cycle with timestamp
    echo "$(date '+%Y-%m-%d %H:%M:%S') — Resonance sync cycle completed successfully." >> "${LOG_FILE}"
    echo "✅ Cycle logged and state synchronized."

    # 5️⃣ Wait before next loop
    echo "⏳ Sleeping ${SYNC_INTERVAL}s before next cycle..."
    sleep "${SYNC_INTERVAL}"
done