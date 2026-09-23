"""Independent disk-rereading CAU review for the completed Arena v15 campaign."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.long_duration_real_outcome_campaign import PROCEDURE_ID
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "arena_v15_disk_rereading_cau", "S": 1.0, "H": 0.0}


def review(*, repo_root: Path, state_path: Path, ledger_path: Path,
           result_path: Path, learning_path: Path) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    cycles = list(state.get("cycles") or [])
    ledger_by_cycle = {int(row["cycle"]): row for row in ledger}
    exact_rows = 0
    commitments = set()
    outcomes = set()
    for cycle in cycles:
        row = ledger_by_cycle.get(int(cycle["cycle"]))
        if not row:
            continue
        body = dict(row)
        claimed_hash = body.pop("outcome_sha256", None)
        recomputed = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (claimed_hash == recomputed == cycle.get("outcome_sha256")
                and row.get("pre_action_commitment") == cycle.get("commitment")):
            exact_rows += 1
        commitments.add(str(row.get("pre_action_commitment")))
        outcomes.add(str(row.get("outcome_sha256")))
    gate0 = state.get("gate") or {}
    gate = {
        "campaign_gate_previously_accepted": gate0.get("accepted") is True,
        "disk_reread_rows": len(ledger),
        "state_cycles": len(cycles),
        "exact_commitment_and_outcome_rows": exact_rows,
        "unique_pre_action_commitments": len(commitments),
        "unique_outcomes": len(outcomes),
        "elapsed_hours": float(gate0.get("actual_elapsed_hours") or 0.0),
        "minimum_hours": float(gate0.get("minimum_elapsed_hours") or 24.0),
        "remote_authorities": int(gate0.get("independent_remote_authorities") or 0),
        "all_safe": gate0.get("all_execution_and_transaction_outcomes_safe") is True,
    }
    gate["accepted"] = bool(
        gate["campaign_gate_previously_accepted"]
        and len(cycles) >= int(gate0.get("minimum_cycles") or 12)
        and exact_rows == len(cycles)
        and len(commitments) == len(cycles)
        and len(outcomes) == len(cycles)
        and gate["elapsed_hours"] >= gate["minimum_hours"]
        and gate["remote_authorities"] >= 4
        and gate["all_safe"]
    )
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID,
        "operate_safely_across_wall_clock_and_independently_changing_outcomes",
        ["commit_before_action", "observe_independent_outcomes", "separate_world_change_from_failure",
         "execute_and_transact", "recover_after_restart", "retain_complete_ledger"],
        min(3.0, len(cycles) / max(1, int(gate0.get("minimum_cycles") or 12))
            + gate["elapsed_hours"] / max(1.0, gate["minimum_hours"])),
        gate["accepted"],
        {"gate": gate, "campaign_state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
         "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest()},
        [],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="arena_v15_cau_review")
    promoted_or_retained = bool(decision.get("promoted") or (
        decision.get("reason") == "NO_CHAMPION_IMPROVEMENT" and decision.get("champion_id") == PROCEDURE_ID
    ))
    if gate["accepted"] and promoted_or_retained:
        state["status"] = "INTERNALLY_PROMOTED_BY_CAU"
        state["promotion"] = "INTERNAL_CAU_PROMOTED"
        state["cau_review"] = {"reviewed_at": datetime.now(timezone.utc).isoformat(),
                               "result_path": str(result_path.relative_to(repo_root)),
                               "decision": decision}
        _write(state_path, state)
    result = {
        "schema_version": "aion.hexcore.long_duration_campaign_cau_review.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "procedure_id": PROCEDURE_ID,
        "passed": gate["accepted"] and promoted_or_retained,
        "status": "INTERNALLY_PROMOTED_BY_CAU" if gate["accepted"] and promoted_or_retained else "REJECTED",
        "gate": gate,
        "decision": decision,
        "boundary": "This is an internal CAU review of 24-hour continual operation. It does not satisfy the separate seven-day AGA retention gate or external certification.",
    }
    _write(result_path, result)
    return result

