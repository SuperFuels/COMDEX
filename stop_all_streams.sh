#!/usr/bin/env bash
# ============================================
# Tessaris / Symatics Stream Terminator
# Stops all active resonance modules
# ============================================

echo "🛑 Stopping Tessaris Resonant Stream Stack..."

# Kill anything listening on ports 8001–8002
lsof -ti:8001 -ti:8002 | xargs -r kill -9

# Also catch any backend resonance modules still running
ps aux | grep -E "symbolic_resonance_export_layer|resonant_analytics_layer|meta_resonant_telemetry_consolidator|resonant_quantum_feedback_synchronizer" \
  | grep -v grep \
  | awk '{print $2}' \
  | xargs -r kill -9

echo "✅ All resonance processes terminated."
echo ""
echo "💡 You can verify cleanup using: lsof -i :8001 -i :8002"
echo "🔁 To restart, run: ./start_all_streams.sh"