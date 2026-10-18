import json
from pathlib import Path

from backend.modules.hexcore.continuous_real_outcome_learning import run_once


def _ledger(path: Path) -> None:
    rows=[]
    for cycle in range(1,5):
        remotes={"feed":{"reachable":True,"revision":f"rev-{1 if cycle<4 else 2}","authority":"public-feed"}}
        row={"cycle":cycle,"observed_at":f"time-{cycle}","pre_action_commitment":f"commit-{cycle}","outcome_sha256":f"outcome-{cycle}","remotes":remotes,"execution":{"passed":True},"transaction":{"passed":True},"changes_detected":["feed"] if cycle==4 else [],"all_outcomes_safe":True}
        rows.append(json.dumps(row))
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(rows)+"\n",encoding="utf-8")


def test_committed_outcomes_become_governed_responses_and_resume(tmp_path: Path):
    ledger=tmp_path/"ledger.jsonl"; _ledger(ledger); workspace=tmp_path/"workspace"
    first=run_once(workspace_root=workspace,ledger_path=ledger,result_path=tmp_path/"result.json")
    assert first["passed"] is True
    assert first["gate"]["total_events_retained"] == 4
    assert first["gate"]["world_change_events_retained"] == 1
    assert first["gate"]["source_models_retained"] == 1
    second=run_once(workspace_root=workspace,ledger_path=ledger,result_path=tmp_path/"result2.json")
    assert second["passed"] is True
    assert second["gate"]["new_events_processed"] == 0
    assert second["gate"]["duplicate_actions_after_restart"] == 0
