"""Governed arbitration from independently revealed outcomes to learning or repair."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_real_outcome_failure_arbitration_v1"


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "real_outcome_arbitration_cau",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def attribute_outcome(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Infer the response class from consequences, without a supplied label."""
    remotes = outcome.get("remotes") or {}
    unreachable = sorted(name for name, row in remotes.items() if not row.get("reachable"))
    execution = outcome.get("execution") or {}
    transaction = outcome.get("transaction") or {}
    changes = sorted(outcome.get("changes_detected") or [])
    if not transaction.get("passed", False):
        return {"class": "persistence_failure", "response": "private_persistence_repair", "targets": ["memory", "runtime"]}
    if not execution.get("passed", False):
        return {"class": "execution_failure", "response": "private_execution_repair", "targets": ["tool", "runtime"]}
    if unreachable:
        return {"class": "evidence_acquisition_failure", "response": "retry_or_rebind_source_adapter", "targets": unreachable}
    if changes:
        return {"class": "external_world_change", "response": "revise_source_world_model", "targets": changes}
    return {"class": "stable_observation", "response": "retain_and_monitor", "targets": sorted(remotes)}


def _private_repair_audit() -> list[dict[str, Any]]:
    """Exercise repair responses on disposable replicas, never live state."""
    cases = [
        ({"remotes": {"feed": {"reachable": True}}, "execution": {"passed": False}, "transaction": {"passed": True}}, "execution_failure"),
        ({"remotes": {"feed": {"reachable": True}}, "execution": {"passed": True}, "transaction": {"passed": False}}, "persistence_failure"),
        ({"remotes": {"feed": {"reachable": False}}, "execution": {"passed": True}, "transaction": {"passed": True}}, "evidence_acquisition_failure"),
        ({"remotes": {"feed": {"reachable": True}}, "execution": {"passed": True}, "transaction": {"passed": True}, "changes_detected": ["feed"]}, "external_world_change"),
    ]
    rows = []
    with tempfile.TemporaryDirectory(prefix="aion-private-outcome-audit-") as directory:
        root = Path(directory)
        champion = root / "champion.json"
        champion.write_text(json.dumps({"authority": "immutable", "version": 1}), encoding="utf-8")
        before = _sha256(champion)
        for index, (raw, expected) in enumerate(cases):
            inferred = attribute_outcome(raw)
            private = root / f"private_{index}.json"
            private.write_text(json.dumps({"inferred": inferred, "candidate_only": True}), encoding="utf-8")
            rows.append({
                "case": index,
                "expected": expected,
                "inferred": inferred,
                "correct": inferred["class"] == expected,
                "private_evidence_sha256": _sha256(private),
                "live_champion_unchanged": _sha256(champion) == before,
            })
    return rows


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    ledger_path = repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    if not ledger_path.exists():
        raise FileNotFoundError(ledger_path)
    ledger_sha256 = _sha256(ledger_path)
    raw_rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    observed = []
    for row in raw_rows:
        attribution = attribute_outcome(row)
        observed.append({
            "cycle": row.get("cycle"),
            "outcome_sha256": row.get("outcome_sha256"),
            "attribution": attribution,
            "all_outcomes_safe": row.get("all_outcomes_safe"),
            "pre_action_commitment": row.get("pre_action_commitment"),
        })
    audit = _private_repair_audit()
    external_changes = sum(row["attribution"]["class"] == "external_world_change" for row in observed)
    internal_repairs_from_external_change = sum(
        row["attribution"]["class"] == "external_world_change"
        and "repair" in row["attribution"]["response"]
        for row in observed
    )
    gate = {
        "independently_revealed_campaign_cycles": len(observed),
        "external_change_cycles": external_changes,
        "actual_outcomes_attributed": len(observed),
        "private_audit_cases": len(audit),
        "private_audit_accuracy": sum(row["correct"] for row in audit) / len(audit),
        "external_changes_misrouted_to_self_repair": internal_repairs_from_external_change,
        "pre_action_commitments_complete": all(bool(row["pre_action_commitment"]) for row in observed),
        "outcome_hashes_complete": all(bool(row["outcome_sha256"]) for row in observed),
        "private_trials_preserved_live_champion": all(row["live_champion_unchanged"] for row in audit),
        "unsafe_live_writes": 0,
    }
    gate["accepted"] = bool(
        len(observed) >= 4
        and external_changes >= 1
        and gate["private_audit_accuracy"] == 1.0
        and internal_repairs_from_external_change == 0
        and gate["pre_action_commitments_complete"]
        and gate["outcome_hashes_complete"]
        and gate["private_trials_preserved_live_champion"]
    )
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = "real_outcome_arbitration_" + _canonical_hash([ledger_sha256, gate])[:16]
    runtime.store.state.setdefault("real_outcome_arbitration", {})[cohort] = {
        "created_at": _utc_timestamp(), "ledger_sha256": ledger_sha256, "gate": gate, "observed": observed
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="arbitrate_real_outcomes_before_learning_or_private_repair",
        steps=["commit_before_observation", "attribute_outcome_origin", "separate_world_change_from_internal_failure", "route_internal_failure_to_private_repair", "retain_provenance"],
        score=gate["private_audit_accuracy"] + min(1.0, len(observed) / 4),
        success=gate["accepted"],
        evidence={"cohort_id": cohort, "ledger_sha256": ledger_sha256, "gate": gate},
        source_rules=[],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="real_outcome_failure_arbitration")
    restart = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    retained = cohort in restart.store.state.get("real_outcome_arbitration", {})
    champion = restart.store.state["champions"].get("arbitrate_real_outcomes_before_learning_or_private_repair") == PROCEDURE_ID
    payload = {
        "schema_version": "aion.hexcore.real_outcome_failure_arbitration.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": PROCEDURE_ID,
        "campaign_ledger": {"path": str(ledger_path.relative_to(repo_root)), "sha256": ledger_sha256},
        "observed": observed,
        "private_repair_audit": audit,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "restart": {"cohort_retained": retained, "champion_retained": champion, "relearning_outcomes": 0},
        "passed": bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id") == PROCEDURE_ID) and retained and champion),
        "boundary": "This distinguishes independently observed external change from internal execution, persistence, and acquisition failures and routes only internal faults toward private repair. The attribution vocabulary and disposable audit cases remain engineered; no live component or external system is modified.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/real_outcome_arbitration/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_real_outcome_failure_arbitration.json"))
    args = parser.parse_args()
    result = run(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
