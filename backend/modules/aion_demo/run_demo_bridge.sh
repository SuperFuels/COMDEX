#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=.
export AION_DEMO_PORT="${AION_DEMO_PORT:-8011}"
echo "Starting AION Demo Bridge on :$AION_DEMO_PORT"
python -m backend.modules.aion_demo.demo_bridge
