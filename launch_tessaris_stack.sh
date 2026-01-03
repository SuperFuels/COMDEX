
#!/usr/bin/env bash
echo "🚀 Launching Tessaris Resonant Cognitive Stack..."
echo "🧹 Cleaning up old processes..."
pkill -f symbolic_resonance_export_layer.py
pkill -f resonant_analytics_layer.py
pkill -f meta_resonant_telemetry_consolidator.py
pkill -f resonant_quantum_feedback_synchronizer.py
pkill -f tessaris_cognitive_fusion_kernel.py
pkill -f adaptive_quantum_control_interface.py
# ⚠️ Do NOT kill uvicorn — handled externally
sleep 2

# ─────────────────────────────────────────────
# 🔧 Start Core Aion/Tessaris Modules
# ─────────────────────────────────────────────
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

echo "🪶 Starting Symbolic Resonance Export Layer (SREL) [port 8001]"
PYTHONPATH=. nohup python backend/modules/aion_integrity/symbolic_resonance_export_layer.py > "$LOG_DIR/srel.log" 2>&1 &

echo "📈 Starting Resonant Analytics Layer (RAL) [port 8002]"
PYTHONPATH=. nohup python backend/modules/aion_integrity/resonant_analytics_layer.py > "$LOG_DIR/ral.log" 2>&1 &

echo "📡 Starting Meta-Resonant Telemetry Consolidator (MRTC)"
PYTHONPATH=. nohup python backend/modules/aion_integrity/meta_resonant_telemetry_consolidator.py > "$LOG_DIR/mrtc.log" 2>&1 &

echo "🔁 Starting Resonant Quantum Feedback Synchronizer (RQFS)"
PYTHONPATH=. nohup python backend/modules/aion_integrity/resonant_quantum_feedback_synchronizer.py > "$LOG_DIR/rqfs.log" 2>&1 &

echo "⚙️ Starting Resonant Optimizer Loop (ROL)"
PYTHONPATH=. nohup python backend/modules/aion_resonance/resonant_optimizer_loop.py > "$LOG_DIR/rol.log" 2>&1 &

echo "🌀 Starting Resonant Feedback Daemon (RFD)"
PYTHONPATH=. nohup python backend/modules/aion_resonance/resonant_feedback_daemon.py > "$LOG_DIR/rfd.log" 2>&1 &

echo "🧠 Starting Tessaris Cognitive Fusion Kernel (TCFK) [port 8005]"
PYTHONPATH=. nohup python backend/modules/aion_cognition/tessaris_cognitive_fusion_kernel.py > "$LOG_DIR/tcfk.log" 2>&1 &

echo "🔗 Starting Fusion → QFC bridge (streams TCFK into HUD/QFC)"
PYTHONPATH=. nohup python backend/modules/visualization/stream_qfc_from_fusion.py > "$LOG_DIR/fusion_qfc_bridge.log" 2>&1 &

echo "🧠 Starting Θ Orchestrator (Thinking Loop Controller)"
PYTHONPATH=. nohup python backend/modules/aion_thinking/theta_orchestrator.py > "$LOG_DIR/theta_orchestrator.log" 2>&1 &

echo "🧬 Starting Adaptive Quantum Control Interface (AQCI) [port 8004]"
PYTHONPATH=. nohup python backend/modules/aion_control/adaptive_quantum_control_interface.py > "$LOG_DIR/aqci.log" 2>&1 &

# 🖥️ Uvicorn is NOT launched here — assume already running
echo "🖥️ Skipping Uvicorn launch (handled externally at port 8000)"

echo "🧪 Starting PAL snapshot watcher (every 60s)"
PYTHONPATH=. nohup python backend/modules/aion_analysis/pal_snapshot.py --watch 60 --export-csv --plot > "$LOG_DIR/pal_snapshot.log" 2>&1 &

# ─────────────────────────────────────────────
# 🧩 Optional: Local Perceptual Learning Monitor
# ─────────────────────────────────────────────
# Uncomment to auto-run Aion's perceptual training in background
# PYTHONPATH=. nohup python backend/modules/aion_perception/pal_core.py > "$LOG_DIR/pal.log" 2>&1 &

echo "✅ All Tessaris modules launched."
echo "   - SREL → ws://localhost:8001/ws/symatics"
echo "   - RAL  → ws://localhost:8002/ws/analytics"
echo "   - MRTC → internal consolidation"
echo "   - RQFS → ws://localhost:8006/ws/rqfs_feedback"
echo "   - TCFK → ws://localhost:8005/ws/fusion"
echo "   - AQCI → ws://localhost:8004/ws/control"
echo "   - API  → http://localhost:8000"
echo "💡 Tip: monitor live ports with → lsof -i :8000 -i :8001 -i :8002 -i :8004 -i :8005"