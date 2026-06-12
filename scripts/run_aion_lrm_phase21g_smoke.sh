#!/usr/bin/env bash
set -euo pipefail

echo "=== AION-LRM Phase 21G local smoke suite ==="

python -m pytest -q \
  backend/tests/workflow_capsules/test_aion_phase21g_lrm_pilot_boardroom_e2e_smoke_lock.py \
  backend/tests/workflow_capsules/test_aion_phase21g_lrm_pilot_boardroom_e2e_smoke_lock_doc.py

python -m compileall backend/modules/aion_lrm backend/services/aion_mission_mode backend/api

echo "AION-LRM Phase 21G local smoke suite passed"
