#!/usr/bin/env bash
# ============================================
# Tessaris / Symatics Resonance Status Utility
# Shows running resonance module processes
# ============================================

echo "📡 Tessaris Resonant Stream Status"
echo "-----------------------------------"

check_module() {
  local name=$1
  local port=$2
  local emoji=$3
  local pids
  pids=$(lsof -ti:$port)

  if [ -n "$pids" ]; then
    echo "$emoji $name — 🟢 RUNNING on port $port (PID: $pids)"
  else
    echo "$emoji $name — 🔴 STOPPED"
  fi
}

check_module "Symbolic Resonance Export Layer (SREL)" 8001 "🪶"
check_module "Resonant Analytics Layer (RAL)" 8002 "📈"

echo "-----------------------------------"
echo "💡 Use ./start_all_streams.sh to start or ./stop_all_streams.sh to stop."