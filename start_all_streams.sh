#!/usr/bin/env bash
# ============================================
# Tessaris / Symatics Stream Launcher
# Phase 26 — Resonant Analytics Layer (RAL)
# ============================================

echo "🚀 Launching Tessaris Resonant Stream Stack..."
cd "$(dirname "$0")"

# Ensure PYTHONPATH includes project root
export PYTHONPATH=.

# Kill any previous instances on 8001–8002 to prevent 'address in use'
echo "🧹 Cleaning old processes..."
lsof -ti:8001 -ti:8002 | xargs -r kill -9

echo "🪶 Starting Symbolic Resonance Export Layer (SREL) [port 8001]"
python backend/modules/aion_integrity/symbolic_resonance_export_layer.py &

sleep 1
echo "📈 Starting Resonant Analytics Layer (RAL) [port 8002]"
python backend/modules/aion_integrity/resonant_analytics_layer.py &

sleep 1
echo "📡 Starting Meta-Resonant Telemetry Consolidator (MRTC)"
python backend/modules/aion_integrity/meta_resonant_telemetry_consolidator.py &

sleep 1
echo "🔁 Starting Resonant Quantum Feedback Synchronizer (RQFS)"
python backend/modules/aion_quantum/resonant_quantum_feedback_synchronizer.py &

sleep 1
echo "✅ All active modules launched."
echo "   - SREL → ws://localhost:8001/ws/symatics"
echo "   - RAL  → ws://localhost:8002/ws/analytics"
echo "   - MRTC → feeds consolidated resonance"
echo "   - RQFS → manages phase bias feedback"
echo ""
echo "💡 Tip: check live ports with → lsof -i :8001 -i :8002"
echo "💻 Then open dashboard → http://localhost:3000/symatics"