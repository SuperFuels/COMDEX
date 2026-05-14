#!/usr/bin/env bash
set -u

echo "🚀 Launching Tessaris Resonant Cognitive Stack..."

# Resolve repo root (script may be run from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
cd "$REPO_ROOT" || exit 1

LOG_DIR="$REPO_ROOT/data/logs"
mkdir -p "$LOG_DIR"

# Force venv python if present
PY_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3 || true)"
fi
if [[ -z "$PY_BIN" ]]; then
  echo "❌ No python found. Activate venv or install python3."
  exit 1
fi
echo "🐍 Using python: $PY_BIN"

# How long to wait before ready check (seconds)
READY_WAIT_SECS="${READY_WAIT_SECS:-4}"

# If STRICT_READY=1, script exits non-zero on failed ready check
STRICT_READY="${STRICT_READY:-0}"

# ─────────────────────────────────────────────
# 🧹 Cleanup old module processes (NOT uvicorn)
# ─────────────────────────────────────────────
echo "🧹 Cleaning up old Tessaris module processes (keeping API/uvicorn)..."

for pat in \
  "symbolic_resonance_export_layer.py" \
  "resonant_analytics_layer.py" \
  "meta_resonant_telemetry_consolidator.py" \
  "resonant_quantum_feedback_synchronizer.py" \
  "resonant_optimizer_loop.py" \
  "resonant_feedback_daemon.py" \
  "tessaris_cognitive_fusion_kernel.py" \
  "stream_qfc_from_fusion.py" \
  "theta_orchestrator.py" \
  "adaptive_quantum_control_interface.py" \
  "pal_snapshot.py"
do
  pkill -f "$pat" 2>/dev/null || true
done

sleep 2

# Helper: start process only if target port is free (when a port is specified)
start_bg() {
  local name="$1"
  local logfile="$2"
  local cmd="$3"
  local port="${4:-}"

  if [[ -n "$port" ]]; then
    if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "⏭️  Skipping $name (port $port already in use)"
      return 0
    fi
  fi

  echo "$name"
  # shellcheck disable=SC2086
  PYTHONPATH=. nohup bash -lc "$cmd" >> "$logfile" 2>&1 &
  sleep 0.2
}

# ─────────────────────────────────────────────
# 🔧 Start Core Aion/Tessaris Modules
# ─────────────────────────────────────────────
start_bg "🪶 Starting Symbolic Resonance Export Layer (SREL) [port 8001]" \
  "$LOG_DIR/srel.log" \
  "$PY_BIN backend/modules/aion_integrity/symbolic_resonance_export_layer.py" \
  "8001"

start_bg "📈 Starting Resonant Analytics Layer (RAL) [port 8002]" \
  "$LOG_DIR/ral.log" \
  "$PY_BIN backend/modules/aion_integrity/resonant_analytics_layer.py" \
  "8002"

start_bg "📡 Starting Meta-Resonant Telemetry Consolidator (MRTC)" \
  "$LOG_DIR/mrtc.log" \
  "$PY_BIN backend/modules/aion_integrity/meta_resonant_telemetry_consolidator.py"

start_bg "🔁 Starting Resonant Quantum Feedback Synchronizer (RQFS) [port 8006]" \
  "$LOG_DIR/rqfs.log" \
  "$PY_BIN backend/modules/aion_integrity/resonant_quantum_feedback_synchronizer.py" \
  "8006"

start_bg "⚙️ Starting Resonant Optimizer Loop (ROL)" \
  "$LOG_DIR/rol.log" \
  "$PY_BIN backend/modules/aion_resonance/resonant_optimizer_loop.py"

start_bg "🌀 Starting Resonant Feedback Daemon (RFD)" \
  "$LOG_DIR/rfd.log" \
  "$PY_BIN backend/modules/aion_resonance/resonant_feedback_daemon.py"

start_bg "🧠 Starting Tessaris Cognitive Fusion Kernel (TCFK) [port 8005]" \
  "$LOG_DIR/tcfk.log" \
  "$PY_BIN backend/modules/aion_cognition/tessaris_cognitive_fusion_kernel.py" \
  "8005"

start_bg "🔗 Starting Fusion → QFC bridge (streams TCFK into HUD/QFC)" \
  "$LOG_DIR/fusion_qfc_bridge.log" \
  "$PY_BIN backend/modules/visualization/stream_qfc_from_fusion.py"

start_bg "🧠 Starting Θ Orchestrator (Thinking Loop Controller)" \
  "$LOG_DIR/theta_orchestrator.log" \
  "$PY_BIN backend/modules/aion_thinking/theta_orchestrator.py"

start_bg "🧬 Starting Adaptive Quantum Control Interface (AQCI) [port 8004]" \
  "$LOG_DIR/aqci.log" \
  "$PY_BIN backend/modules/aion_control/adaptive_quantum_control_interface.py" \
  "8004"

# 🖥️ Uvicorn is NOT launched here — assume already running
echo "🖥️ Skipping Uvicorn launch (handled externally at port 8000)"

start_bg "🧪 Starting PAL snapshot watcher (every 60s)" \
  "$LOG_DIR/pal_snapshot.log" \
  "$PY_BIN backend/modules/aion_analysis/pal_snapshot.py --watch 60 --export-csv --plot"

echo "✅ All Tessaris modules launched."
echo "   - SREL → ws://localhost:8001/ws/symatics"
echo "   - RAL  → ws://localhost:8002/ws/analytics"
echo "   - MRTC → internal consolidation"
echo "   - RQFS → ws://localhost:8006/ws/rqfs_feedback"
echo "   - TCFK → ws://localhost:8005/ws/fusion"
echo "   - AQCI → ws://localhost:8004/ws/control"
echo "   - API  → http://localhost:8000"
echo "💡 Tip: monitor live ports with → lsof -i :8000 -i :8001 -i :8002 -i :8004 -i :8005 -i :8006"

echo "⏳ Waiting ${READY_WAIT_SECS}s for services to bind..."
sleep "$READY_WAIT_SECS"

echo "🔎 Port status snapshot:"
for p in 8000 8001 8002 8004 8005 8006; do
  if lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "   ✅ :$p listening"
  else
    echo "   ❌ :$p not listening"
  fi
done

echo "🩺 Running AION ready check..."
if ! PYTHONPATH=. "$PY_BIN" backend/modules/aion_runtime/aion_ready_check.py; then
  echo "⚠️ Ready check failed (required services not all up). Review logs in $LOG_DIR"
  echo "📄 Recent log tails:"
  for f in "$LOG_DIR"/*.log; do
    [[ -f "$f" ]] || continue
    echo "----- $(basename "$f") -----"
    tail -n 20 "$f" || true
  done

  if [[ "$STRICT_READY" == "1" ]]; then
    exit 1
  fi
fi