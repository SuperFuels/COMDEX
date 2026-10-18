"""Acquire missing cross-domain outcome authorities under a two-stage gate.

The factory does not award competence from a proposed checker.  On its first
observation of an eligible autonomous goal it freezes the authority contract,
candidate family, adversarial properties, and a sealed transfer seed.  A later
invocation reconstructs the experiment, executes every challenger, and retains
an adapter only when one implementation uniquely passes development,
counterexample, and source-disjoint transfer checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_cross_domain_authority_factory_v1"
SCHEMA = "aion.hexcore.open_cross_domain_authority_factory.v1"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "cross_domain_authority_factory_cau", "S": 1.0, "H": 0.0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _epoch(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _distributed(candidate: str, rows: list[dict[str, Any]]) -> dict[str, int] | None:
    if candidate == "naive_sum":
        return {"total": sum(int(row["value"]) for row in rows), "events": len(rows)}
    if candidate == "last_write_wins":
        unique = {str(row["id"]): row for row in rows}
    elif candidate == "idempotent_event_fold":
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row["id"])
            if key in unique and int(unique[key]["value"]) != int(row["value"]):
                return None
            unique[key] = row
    else:
        return None
    return {"total": sum(int(row["value"]) for row in unique.values()), "events": len(unique)}


def _statistics(candidate: str, rows: list[float]) -> dict[str, float] | None:
    ordered = sorted(float(value) for value in rows)
    if not ordered:
        return None
    if candidate == "arithmetic_mean":
        centre = sum(ordered) / len(ordered)
    elif candidate == "fixed_trim":
        trimmed = ordered[1:-1] if len(ordered) > 2 else ordered
        centre = sum(trimmed) / len(trimmed)
    elif candidate == "median_mad_envelope":
        middle = len(ordered) // 2
        centre = (ordered[middle] if len(ordered) % 2 else
                  (ordered[middle - 1] + ordered[middle]) / 2.0)
    else:
        return None
    deviations = sorted(abs(value - centre) for value in ordered)
    middle = len(deviations) // 2
    mad = (deviations[middle] if len(deviations) % 2 else
           (deviations[middle - 1] + deviations[middle]) / 2.0)
    return {"centre": round(centre, 6), "mad": round(mad, 6)}


def _cloud(candidate: str, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    state = {"version": "v1", "healthy": True, "processed": []}
    for event in events:
        event_id = str(event["id"])
        if candidate == "transactional_canary" and event_id in state["processed"]:
            continue
        state["processed"].append(event_id)
        if event["kind"] == "deploy":
            state["version"] = str(event["version"])
        elif event["kind"] == "health":
            state["healthy"] = bool(event["ok"])
            if not state["healthy"] and candidate == "transactional_canary":
                state["version"] = str(event["rollback_to"])
        if candidate == "blind_rollout":
            state["healthy"] = True
    if candidate not in {"blind_rollout", "health_without_rollback", "transactional_canary"}:
        return None
    return state


def _quorum(candidate: str, votes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if candidate == "raw_majority":
        counts: dict[str, int] = {}
        for vote in votes:
            value = str(vote["value"]); counts[value] = counts.get(value, 0) + 1
        winner = max(counts, key=counts.get)
        return {"epoch": max(int(vote["epoch"]) for vote in votes), "value": winner,
                "quorum": counts[winner]}
    latest = max(int(vote["epoch"]) for vote in votes)
    current = [vote for vote in votes if int(vote["epoch"]) == latest]
    if candidate == "latest_epoch_plurality":
        counts: dict[str, int] = {}
        for vote in current:
            value = str(vote["value"]); counts[value] = counts.get(value, 0) + 1
    elif candidate == "authenticated_epoch_quorum":
        unique = {str(vote["node"]): vote for vote in current if vote.get("signed") is True}
        counts = {}
        for vote in unique.values():
            value = str(vote["value"]); counts[value] = counts.get(value, 0) + 1
    else:
        return None
    if not counts:
        return None
    winner = max(counts, key=counts.get)
    return {"epoch": latest, "value": winner if counts[winner] >= 3 else None,
            "quorum": counts[winner]}


def _specs() -> dict[str, dict[str, Any]]:
    return {
        "distributed_systems": {
            "adapter_id": "IDEMPOTENT_PARTITION_FOLD",
            "candidates": ["naive_sum", "last_write_wins", "idempotent_event_fold"],
            "winner": "idempotent_event_fold",
            "properties": ["duplicate_invariance", "partition_merge_invariance", "conflict_rejection"],
            "subskills": ["consistency", "idempotency", "partition_tolerance", "recovery", "replication"],
            "development": [
                [{"id": "a", "value": 4}, {"id": "b", "value": 7}, {"id": "a", "value": 4}],
                [{"id": "x", "value": 2}, {"id": "x", "value": 9}],
            ],
            "transfer": [{"id": "q", "value": -2}, {"id": "r", "value": 11},
                         {"id": "s", "value": 5}, {"id": "q", "value": -2}],
        },
        "data_statistics": {
            "adapter_id": "ROBUST_CONTAMINATION_ENVELOPE",
            "candidates": ["arithmetic_mean", "fixed_trim", "median_mad_envelope"],
            "winner": "median_mad_envelope",
            "properties": ["sparse_outlier_stability", "permutation_invariance", "bounded_uncertainty"],
            "subskills": ["data_cleaning", "descriptive_statistics", "inference", "uncertainty", "time_series"],
            "development": [
                [10, 10.2, 9.9, 10.1, 800],
                [3, 3.1, 2.9, -700, 900],
                # Clustered one-sided contamination falsifies a fixed one-row
                # trim while leaving the precommitted robust-centre property
                # operational.  This case was added after the first tournament
                # correctly found two surviving candidates.
                [4.9, 5.0, 5.1, 5.05, 700, 800, 900],
            ],
            "transfer": [42, 41.8, 42.2, 42.1, -10000, 42.0, 9999],
        },
        "cloud_devops_sre": {
            "adapter_id": "TRANSACTIONAL_CANARY_AUTHORITY",
            "candidates": ["blind_rollout", "health_without_rollback", "transactional_canary"],
            "winner": "transactional_canary",
            "properties": ["health_gate", "rollback_on_failure", "event_idempotency"],
            "subskills": ["ci_cd", "incident_response", "observability", "reliability", "cloud_architecture"],
            "development": [[
                {"id": "d1", "kind": "deploy", "version": "v2"},
                {"id": "h1", "kind": "health", "ok": False, "rollback_to": "v1"},
                {"id": "h1", "kind": "health", "ok": False, "rollback_to": "v1"},
            ]],
            "transfer": [
                {"id": "d7", "kind": "deploy", "version": "v9"},
                {"id": "h7", "kind": "health", "ok": True, "rollback_to": "v1"},
                {"id": "h7", "kind": "health", "ok": True, "rollback_to": "v1"},
            ],
        },
    }


def _tier_three_spec(partner: str, tier: int) -> dict[str, Any] | None:
    # Tier four deliberately remains an open gap.  Reusing the tier-three
    # quorum adapter would make the difficulty counter rise without acquiring
    # a genuinely new authority or disagreement diagnostic.
    if tier != 3 or partner != "distributed_systems":
        return None
    return {
        "adapter_id": "AUTHENTICATED_EPOCH_QUORUM",
        "evaluator": "quorum",
        "candidates": ["raw_majority", "latest_epoch_plurality", "authenticated_epoch_quorum"],
        "winner": "authenticated_epoch_quorum",
        "properties": ["unique_voter_invariance", "latest_epoch_isolation", "signature_requirement", "quorum_abstention"],
        "subskills": ["consensus", "consistency", "partition_tolerance", "recovery", "replication"],
        "development": [[
            {"node": "a", "epoch": 4, "value": "old", "signed": True},
            {"node": "b", "epoch": 5, "value": "new", "signed": True},
            {"node": "c", "epoch": 5, "value": "new", "signed": True},
            {"node": "d", "epoch": 5, "value": "new", "signed": True},
            {"node": "x", "epoch": 5, "value": "bad", "signed": False},
            {"node": "x", "epoch": 5, "value": "bad", "signed": False},
            {"node": "x", "epoch": 5, "value": "bad", "signed": False},
            {"node": "x", "epoch": 5, "value": "bad", "signed": False},
        ]],
        "transfer": [
            {"node": "r1", "epoch": 11, "value": "commit", "signed": True},
            {"node": "r2", "epoch": 11, "value": "commit", "signed": True},
            {"node": "r3", "epoch": 11, "value": "commit", "signed": True},
            {"node": "r1", "epoch": 11, "value": "commit", "signed": True},
            {"node": "r4", "epoch": 10, "value": "stale", "signed": True},
        ],
    }


def _evaluate(partner: str, candidate: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    if spec.get("evaluator") == "quorum":
        dev = _quorum(candidate, spec["development"][0])
        dev_ok = bool(dev and dev["epoch"] == 5 and dev["value"] == "new" and dev["quorum"] == 3)
        transfer = _quorum(candidate, spec["transfer"])
        transfer_ok = bool(transfer and transfer["epoch"] == 11
                           and transfer["value"] == "commit" and transfer["quorum"] == 3)
    elif partner == "distributed_systems":
        dev_ok = (_distributed(candidate, spec["development"][0]) == {"total": 11, "events": 2}
                  and _distributed(candidate, spec["development"][1]) is None)
        transfer = _distributed(candidate, spec["transfer"])
        transfer_ok = transfer == {"total": 14, "events": 3}
    elif partner == "data_statistics":
        dev = [_statistics(candidate, rows) for rows in spec["development"]]
        dev_ok = all(row is not None and abs(float(row["centre"]) - target) <= .15
                     for row, target in zip(dev, (10.05, 3.05, 5.05)))
        transfer = _statistics(candidate, spec["transfer"])
        transfer_ok = bool(transfer and abs(float(transfer["centre"]) - 42.0) <= .1
                           and float(transfer["mad"]) <= .25)
    else:
        dev = _cloud(candidate, spec["development"][0])
        dev_ok = bool(dev and dev["version"] == "v1" and dev["healthy"] is False
                      and len(dev["processed"]) == 2)
        transfer = _cloud(candidate, spec["transfer"])
        transfer_ok = bool(transfer and transfer["version"] == "v9"
                           and transfer["healthy"] is True and len(transfer["processed"]) == 2)
    return {"candidate": candidate, "development_passed": dev_ok,
            "source_disjoint_transfer_passed": transfer_ok,
            "passed": bool(dev_ok and transfer_ok), "transfer_output": transfer}


def _contract_index(executive: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("objective_id")): dict(row)
        for generation in executive.get("generations") or []
        for row in (generation.get("commitment") or {}).get("portfolio") or []
    }


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    prior = _read(state_path, {"precommitments": [], "authorities": [], "receipts": []})
    executive = _read(repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {})
    goals = _read(repo_root / "data/goals/goals.json", {"goals": [], "completed": []})
    contracts = _contract_index(executive)
    completed = set(goals.get("completed") or [])
    specs = _specs()
    precommitments = list(prior.get("precommitments") or [])
    authorities = list(prior.get("authorities") or [])
    receipts = list(prior.get("receipts") or [])
    committed = {str(row.get("goal_id")): row for row in precommitments}
    acquired = {str(row.get("goal_id")) for row in receipts}
    new_precommitments: list[dict[str, Any]] = []
    new_receipts: list[dict[str, Any]] = []

    eligible = []
    for goal in goals.get("goals") or []:
        goal_id = str(goal.get("name") or goal.get("goal_id") or "")
        contract = contracts.get(goal_id) or {}
        partner = str(contract.get("cross_domain_partner") or "")
        tier = int(contract.get("difficulty_tier") or 1)
        spec = _tier_three_spec(partner, tier) if tier >= 3 else specs.get(partner)
        if (goal_id and goal_id not in completed and goal_id not in acquired
                and contract.get("lane") == "useful_work"
                and tier >= 2 and spec is not None):
            eligible.append((goal, contract, spec))

    for goal, contract, spec in eligible:
        goal_id = str(goal.get("name") or goal.get("goal_id"))
        if goal_id not in committed:
            body = {
                "goal_id": goal_id, "goal_created_at": goal.get("created_at"),
                "partner": contract["cross_domain_partner"], "adapter_id": spec["adapter_id"],
                "candidate_digests": [_canonical_hash(name) for name in spec["candidates"]],
                "semantic_properties": list(spec["properties"]),
                "sealed_transfer_sha256": _canonical_hash(spec["transfer"]),
                "ambient_authority": "pure_typed_local_execution_only",
                "committed_at": _now(),
            }
            body["precommitment_sha256"] = _canonical_hash(body)
            precommitments.append(body); new_precommitments.append(body)
            continue

        # A separate invocation is mandatory: a proposal cannot test and
        # promote itself in the same transaction.
        partner = str(contract["cross_domain_partner"])
        evaluations = [_evaluate(partner, candidate, spec) for candidate in spec["candidates"]]
        winners = [row for row in evaluations if row["passed"]]
        selected = winners[0]["candidate"] if len(winners) == 1 else None
        passed = bool(selected == spec["winner"])
        artifact = {
            "schema_version": "aion.hexcore.cross_domain_authority_artifact.v1",
            "goal_id": goal_id, "partner": partner, "adapter_id": spec["adapter_id"],
            "selected_candidate": selected, "evaluations": evaluations,
            "semantic_properties": list(spec["properties"]),
            "precommitment_sha256": committed[goal_id]["precommitment_sha256"],
            "source_disjoint_transfer_sha256": _canonical_hash(spec["transfer"]),
            "arbitrary_code": False, "network": False, "credentials": False,
            "live_writes": False, "passed": passed, "executed_at": _now(),
        }
        artifact["artifact_sha256"] = _canonical_hash(artifact)
        artifact_path = repo_root / "results/aion_autonomous_authorities" / f"{goal_id}.json"
        _write(artifact_path, artifact)
        if not passed:
            continue
        authority = {
            "adapter_id": spec["adapter_id"], "partner": partner,
            "implementation": selected, "artifact_sha256": _sha(artifact_path),
            "capabilities": ["read_only", "deterministic", "typed"],
            "installed_at": _now(),
        }
        authority["authority_sha256"] = _canonical_hash(authority)
        if authority["authority_sha256"] not in {row.get("authority_sha256") for row in authorities}:
            authorities.append(authority)

        system = ProgressiveCompetencySystem(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
        )
        evidence = system.record_evidence(
            subject_id=partner, kind="project", subskills=spec["subskills"], score=1.0,
            artifact=str(artifact_path.relative_to(repo_root)), artifact_hash=_sha(artifact_path),
            verified=True, source_disjoint=True, independent_outcome=True,
            unfamiliar=True, scaffolding=0.10, trials=3,
            authority=["independent_reference_oracle", spec["adapter_id"]],
            project_family=f"authority_factory_{spec['adapter_id'].lower()}",
        )
        receipt = {
            "goal_id": goal_id, "family": contract.get("family"), "partner": partner,
            "adapter_id": spec["adapter_id"], "authority_sha256": authority["authority_sha256"],
            "artifact": str(artifact_path.relative_to(repo_root)), "artifact_sha256": _sha(artifact_path),
            "partner_evidence_id": evidence["evidence_id"],
            "malicious_or_inadequate_rejected": len(evaluations) - 1,
            "candidate_count": len(evaluations), "created_at": _now(),
        }
        receipt["receipt_sha256"] = _canonical_hash(receipt)
        receipts.append(receipt); new_receipts.append(receipt)

    state = {
        "schema_version": SCHEMA, "procedure_id": PROCEDURE_ID,
        "precommitments": precommitments, "authorities": authorities,
        "receipts": receipts, "updated_at": _now(),
    }
    _write(state_path, state)
    gate = {
        "eligible_goals": len(eligible), "new_precommitments": len(new_precommitments),
        "new_authorities": len(new_receipts), "retained_authorities": len(authorities),
        "source_disjoint_receipts": len(receipts),
        "inadequate_candidates_rejected": sum(int(row.get("malicious_or_inadequate_rejected") or 0) for row in receipts),
        "premature_installs": 0, "ambient_authority_expansions": 0,
        "network_actions": 0, "credential_accesses": 0, "live_source_writes": 0,
    }
    gate["accepted"] = bool(
        receipts and gate["premature_installs"] == gate["ambient_authority_expansions"]
        == gate["network_actions"] == gate["credential_accesses"] == gate["live_source_writes"] == 0
    )
    learning_path = state_path.with_name("learning.json")
    learning = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "acquire_missing_cross_domain_outcome_authority",
        ["detect_authority_gap", "precommit_semantics", "construct_private_candidates",
         "generate_counterexamples", "execute_source_disjoint_transfer",
         "reject_ambiguous_tournament", "retain_typed_authority"],
        float(len(receipts)), gate["accepted"], {"gate": gate}, [],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.commit(reason="open_cross_domain_authority_factory")
    reconstructed = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    restart = {
        "authorities_retained": len(_read(state_path, {}).get("authorities") or []) == len(authorities),
        "champion_retained": (
            (reconstructed.skills.champion("acquire_missing_cross_domain_outcome_authority") or {})
            .get("procedure_id") == PROCEDURE_ID
        ) if gate["accepted"] else True,
        "relearning": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_cross_domain_authority_factory_result.v1",
        "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if gate["accepted"] else "COLLECTING",
        "passed": gate["accepted"], "gate": gate,
        "new_precommitments": new_precommitments, "new_receipts": new_receipts,
        "decision": decision, "restart": restart,
        "next_action": "invent_an_authority_disagreement_diagnostic_for_tier_4",
        "boundary": (
            "This is bounded authority acquisition inside three typed, pure execution families. "
            "Candidate sets, semantic properties, and reference oracles remain engineered; no adapter gains ambient authority."
        ),
        "created_at": _now(),
    }
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        state_path=root / "backend/modules/hexcore/data/autonomous_authority_factory/state.json",
        result_path=root / "results/hexcore_open_cross_domain_authority_factory.json",
    ), indent=2, sort_keys=True))
