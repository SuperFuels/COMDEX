#!/usr/bin/env bash
LOG="$1"
if [ -z "$LOG" ] || [ ! -f "$LOG" ]; then
  echo "Usage: $0 path/to/logfile"
  exit 1
fi

echo "== Equilibrium summary for: $LOG =="
ALL=$(grep -i "equilibrium" "$LOG" | wc -l | xargs)
FAIL=$(grep -i "without resonance equilibrium" "$LOG" | wc -l | xargs)
OK=$((ALL - FAIL))

echo "Total 'equilibrium' mentions: $ALL"
echo "Successful equilibria:       $OK"
echo "Failures (no equilibrium):   $FAIL"
echo
echo "Most recent success context (if any):"
LINE=$(grep -n -i "equilibrium" "$LOG" | grep -vi "without" | tail -1 | cut -d: -f1)
if [ -n "$LINE" ]; then
  sed -n "$((LINE-5)),$((LINE+5))p" "$LOG"
else
  echo "  (none found)"
fi