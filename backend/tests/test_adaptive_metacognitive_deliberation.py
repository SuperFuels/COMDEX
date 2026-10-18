from pathlib import Path
from backend.modules.hexcore.adaptive_metacognitive_deliberation_benchmark import run
def test_adaptive_metacognition_prevents_traps_without_overthinking(tmp_path:Path):
 r=run(state_path=tmp_path/"state.json",result_path=tmp_path/"result.json")
 assert r["passed"] is True
 assert r["gate"]["metacognitive_success"] == 1
 assert r["gate"]["actor_only_success"] <= .5
 assert r["gate"]["tempting_traps_prevented"] == 5
 assert r["gate"]["routine_actions_preserved"] == 5
 assert r["gate"]["deliberation_reduction"] >= .25
 assert r["gate"]["llm_calls"] == 0
