from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/"results/hexcore_long_duration_campaign_v15_state.json"
LEDGER=ROOT/"results/hexcore_long_duration_campaign_v15_ledger.jsonl"

def state():return json.loads(STATE.read_text())
def test_campaign_promotion_never_precedes_real_time_gate():
 s=state();g=s["gate"];assert g["minimum_elapsed_hours"]>=24
 if g["accepted"]: assert g["wall_clock_requirement_met"]
 else: assert not g["wall_clock_requirement_met"]
def test_independent_and_executable_outcomes_are_recorded():
 s=state();assert len(s["source_models"])==4;assert all(m["observations"]>=1 for m in s["source_models"].values());assert s["cycles"][-1]["execution_passed"];assert s["cycles"][-1]["transaction_passed"]
def test_append_only_commitment_ledger_matches_state():
 s=state();rows=[json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()];assert rows[-1]["pre_action_commitment"]==s["cycles"][-1]["commitment"];assert len(rows[-1]["outcome_sha256"])==64
