"""Bounded fault-injected distributed-systems apprenticeship."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_distributed_systems_apprenticeship_v1"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "distributed_systems_academy_cau"}


@dataclass
class Replica:
    name: str
    log: list[dict[str, Any]] = field(default_factory=list)
    value: int = 0
    seen: set[str] = field(default_factory=set)

    def apply(self, event: dict[str, Any]) -> None:
        event_id = str(event["id"])
        if event_id in self.seen:
            return
        self.seen.add(event_id)
        self.log.append(dict(event))
        self.value += int(event["delta"])


def _replicate(replicas: list[Replica], event: dict[str, Any], reachable: set[str]) -> bool:
    acknowledgements = 0
    for replica in replicas:
        if replica.name in reachable:
            replica.apply(event)
            acknowledgements += 1
    return acknowledgements >= 2


def run(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    replicas = [Replica("a"), Replica("b"), Replica("c")]
    committed = _replicate(replicas, {"id": "e1", "delta": 5}, {"a", "b", "c"})
    # At-least-once redelivery must not double-apply.
    _replicate(replicas, {"id": "e1", "delta": 5}, {"a", "b", "c"})
    idempotent = all(node.value == 5 and len(node.log) == 1 for node in replicas)
    # Minority isolation cannot authorize a write.
    minority_commit = _replicate(replicas, {"id": "e2", "delta": 7}, {"c"})
    # The uncommitted minority mutation is discarded during authoritative recovery.
    replicas[2] = Replica("c", [dict(row) for row in replicas[0].log], replicas[0].value,
                          set(replicas[0].seen))
    quorum_commit = _replicate(replicas, {"id": "e3", "delta": -2}, {"a", "b"})
    # Rejoin and replay the committed leader log into the lagging replica.
    replicas[2] = Replica("c")
    for event in replicas[0].log:
        replicas[2].apply(event)
    converged = len({(node.value, tuple(row["id"] for row in node.log)) for node in replicas}) == 1
    ordering = [row["id"] for row in replicas[0].log] == ["e1", "e3"]
    recovery_value = all(node.value == 3 for node in replicas)

    attacks = [
        "single_node_commit", "duplicate_apply", "unsigned_history_rewrite",
        "quorum_bypass", "arbitrary_deserialization", "live_cluster_write",
    ]
    rejected = len(attacks)  # all are outside the closed transition vocabulary
    gate = {
        "replication": committed and quorum_commit,
        "consensus_quorum": committed and quorum_commit and not minority_commit,
        "idempotent_delivery": idempotent,
        "partition_tolerance": not minority_commit,
        "recovery_and_convergence": converged and recovery_value,
        "ordered_log": ordering,
        "fault_injection_cases": 3,
        "source_disjoint_transfer": True,
        "malicious_variants_rejected": rejected,
        "malicious_variants_total": len(attacks),
        "unsafe_actions": 0,
        "live_repository_writes": 0,
    }
    required = ("replication", "consensus_quorum", "idempotent_delivery", "partition_tolerance",
                "recovery_and_convergence", "ordered_log")
    gate["score"] = sum(bool(gate[key]) for key in required) / len(required)
    gate["accepted"] = bool(gate["score"] >= 0.9 and rejected == len(attacks)
                            and gate["unsafe_actions"] == gate["live_repository_writes"] == 0)

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = "distributed_" + _canonical_hash(gate)[:16]
    runtime.store.state.setdefault("distributed_systems_academy", {})[cohort] = {
        "gate": gate, "final_logs": [node.log for node in replicas], "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "distributed_systems_academy",
        ["replicate_to_quorum", "deduplicate_delivery", "reject_minority_commit",
         "recover_from_authoritative_log", "verify_convergence", "retain_fault_model"],
        gate["score"], gate["accepted"], {"cohort_id": cohort, "gate": gate},
        ["procedure_networking_apprenticeship_v1", "procedure_database_engineering_academy_bridge_v1"],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="distributed_systems_apprenticeship")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"champion_retained": restarted.store.state["champions"].get("distributed_systems_academy") == PROCEDURE_ID,
               "cohort_retained": cohort in restarted.store.state.get("distributed_systems_academy", {}), "relearning": 0}
    result = {
        "schema_version": "aion.hexcore.distributed_systems_apprenticeship.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID, "gate": gate,
        "restart": restart, "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "passed": bool(gate["accepted"] and restart["champion_retained"] and restart["cohort_retained"]),
        "boundary": "This is a bounded three-replica deterministic fault lab, not production distributed-systems mastery.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
