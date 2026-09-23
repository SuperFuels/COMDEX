#!/usr/bin/env bash
set -euo pipefail

echo "=== AION-LRM Phase 20 focused lock suite ==="

python -m pytest -q \
  backend/tests/workflow_capsules/test_aion_phase20a_reasoning_packet_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20a_reasoning_packet_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20b_reasoning_memory_snapshot_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20b_reasoning_memory_snapshot_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20c_reasoning_replay_trace_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20c_reasoning_replay_trace_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20d_reasoning_replay_boardroom_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20d_reasoning_replay_boardroom_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20e_reasoning_recommendation_card_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20e_reasoning_recommendation_card_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20f_human_review_decision_envelope_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20f_human_review_decision_envelope_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20g_evidence_gap_envelope_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20g_evidence_gap_envelope_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20h_evidence_satisfaction_envelope_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20h_evidence_satisfaction_envelope_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20i_lrm_end_to_end_decision_loop_lock.py \
  backend/tests/workflow_capsules/test_aion_phase20i_lrm_end_to_end_decision_loop_lock_doc.py \
  backend/tests/workflow_capsules/test_aion_phase20_lrm_closeout_lock_doc.py

echo
echo "=== Compile AION-LRM modules ==="
python -m compileall backend/modules/aion_lrm

echo
echo "=== AION-LRM Phase 20 focused lock suite passed ==="
