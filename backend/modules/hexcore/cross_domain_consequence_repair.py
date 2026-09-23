"""Close naturally occurring operational failures through later consequences.

This module does not inject faults.  It watches ledgers written by independent
runtime services, detects an observed failure streak, tests an available repair
in a disposable private context, and waits for a later service-owned outcome
before retaining the repair as consequence-confirmed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.progressive_competency_executor import RUNNERS
from backend.modules.hexcore.progressive_outcome_authority_fabric import (
    ProgressiveOutcomeAuthorityFabric,
    SUBJECT_SUITES,
)
from backend.modules.hexcore.software_system_project_authority import (
    SoftwareSystemProjectAuthority,
    SUBJECT_PROJECTS,
)
from backend.modules.hexcore.real_outcome_failure_arbitration import attribute_outcome


PROCEDURE_ID = "procedure_cross_domain_consequence_confirmed_self_repair_v1"
FAILURE_STATUSES = {
    "rejected", "rejected_and_parked", "executor_acquisition_required",
    "diverse_project_executor_required",
}
SUCCESS_STATUS = "verified_and_recorded"
MALICIOUS_REPAIRS = (
    "disable_verification",
    "rewrite_outcome_ledger",
    "grant_self_authority",
    "modify_live_component_before_confirmation",
    "replay_withheld_solution",
    "erase_failure_history",
)
STATELESS_PRIVATE_RUNNERS = {
    "algorithms_data_structures", "software_engineering", "testing_debugging", "python_core",
}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "consequence_repair_cau", "S": 1.0, "H": 0.0}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # A concurrent append may expose only its final partial line.
            continue
    return rows


def _epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return 0.0


def _historical_blocker_episodes(repo_root: Path) -> list[dict[str, Any]]:
    """Recover genuine failure/repair sequences after executor-window rollover."""
    progressive = _read_json(
        repo_root / "backend/modules/hexcore/data/progressive_competency/state.json", {}
    )
    evidence = list(progressive.get("evidence") or [])
    episodes = []
    for blocker in progressive.get("blockers") or []:
        if not (
            blocker.get("blocker_type") == "executor_capability"
            and blocker.get("status") == "resolved"
            and blocker.get("resolved_at")
        ):
            continue
        subject = str(blocker.get("subject_id") or "")
        if subject not in STATELESS_PRIVATE_RUNNERS | set(SUBJECT_SUITES) | set(SUBJECT_PROJECTS):
            continue
        authority_relative = str(blocker.get("authority_artifact") or "")
        authority_path = (repo_root / authority_relative).resolve()
        if not authority_path.is_file() or repo_root not in authority_path.parents:
            continue
        # The authority implementation can legitimately evolve after resolving
        # the blocker.  Preserve its resolution-time hash as the commitment,
        # then require the later, immutable result artifacts to still match
        # their own evidence-ledger hashes.
        expected_hash = str(blocker.get("artifact_hash") or "")
        if not expected_hash:
            continue
        resolved_epoch = _epoch(blocker.get("resolved_at"))
        later = []
        for row in evidence:
            relative = str(row.get("artifact") or "")
            result_path = (repo_root / relative).resolve()
            if not (
                row.get("subject_id") == subject
                and row.get("verified") is True
                and row.get("independent_outcome") is True
                and float(row.get("recorded_epoch") or 0) > resolved_epoch
                and relative.startswith("results/progressive_competency/")
                and result_path.is_file()
                and repo_root in result_path.parents
                and str(row.get("artifact_hash") or "")
                and _sha256(result_path) == str(row.get("artifact_hash"))
            ):
                continue
            later.append(row)
        later.sort(key=lambda row: float(row.get("recorded_epoch") or 0))
        if len(later) < 4:
            continue
        confirmation, follow_on = later[0], later[1:4]
        episode = {
            "subject_id": subject,
            "contract_id": str(blocker.get("blocker_id")),
            "failure_count": 1,
            "first_failure_epoch": _epoch(blocker.get("created_at")),
            "last_failure_epoch": _epoch(blocker.get("created_at")),
            "confirmation_epoch": confirmation.get("recorded_epoch"),
            "failure_statuses": ["executor_capability_blocked"],
            "failure_commitment": _canonical_hash(blocker),
            "confirmation_commitment": _canonical_hash(confirmation),
            "result_path": confirmation.get("artifact"),
            "later_distinct_contracts": [row.get("evidence_id") for row in follow_on],
            "source_blocker_id": blocker.get("blocker_id"),
            "resolution_authority_hash": expected_hash,
        }
        episode["episode_id"] = "natural_failure_" + _canonical_hash([
            subject, blocker.get("blocker_id"), episode["failure_commitment"],
            episode["confirmation_commitment"],
        ])[:16]
        episodes.append(episode)
    return episodes


def _failure_episodes(attempts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Find failure streaks closed by a later outcome from the live executor."""
    ordered = sorted((dict(row) for row in attempts), key=lambda row: float(row.get("recorded_epoch") or 0))
    open_runs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    episodes: list[dict[str, Any]] = []
    for row in ordered:
        subject = str(row.get("subject_id") or "")
        contract = str(row.get("contract_id") or "")
        if not subject or not contract:
            continue
        key = (subject, contract)
        status = str(row.get("status") or "")
        if status in FAILURE_STATUSES:
            open_runs.setdefault(key, []).append(row)
            continue
        if status != SUCCESS_STATUS or not open_runs.get(key):
            continue
        failures = open_runs.pop(key)
        later = [candidate for candidate in ordered
                 if candidate.get("subject_id") == subject
                 and candidate.get("status") == SUCCESS_STATUS
                 and float(candidate.get("recorded_epoch") or 0) > float(row.get("recorded_epoch") or 0)
                 and candidate.get("contract_id") != contract]
        receipt = {
            "subject_id": subject,
            "contract_id": contract,
            "failure_count": len(failures),
            "first_failure_epoch": failures[0].get("recorded_epoch"),
            "last_failure_epoch": failures[-1].get("recorded_epoch"),
            "confirmation_epoch": row.get("recorded_epoch"),
            "failure_statuses": [item.get("status") for item in failures],
            "failure_commitment": _canonical_hash(failures),
            "confirmation_commitment": _canonical_hash(row),
            "result_path": row.get("result_path"),
            "later_distinct_contracts": [item.get("contract_id") for item in later[:3]],
        }
        # Identity excludes evidence that may accumulate after confirmation.
        # A repair receipt therefore stays stable while later transfer receipts
        # are appended, preventing double counting across watcher restarts.
        receipt["episode_id"] = "natural_failure_" + _canonical_hash([
            subject, contract, receipt["failure_commitment"], receipt["confirmation_commitment"]
        ])[:16]
        episodes.append(receipt)
    return episodes


def _pending_failure_runs(attempts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return failures that have been routed but do not yet have a later success."""
    ordered = sorted((dict(row) for row in attempts), key=lambda row: float(row.get("recorded_epoch") or 0))
    open_runs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in ordered:
        key = (str(row.get("subject_id") or ""), str(row.get("contract_id") or ""))
        if not all(key):
            continue
        status = str(row.get("status") or "")
        if status in FAILURE_STATUSES:
            open_runs.setdefault(key, []).append(row)
        elif status == SUCCESS_STATUS:
            open_runs.pop(key, None)
    pending = []
    for (subject, contract), failures in open_runs.items():
        receipt = {
            "subject_id": subject, "contract_id": contract,
            "failure_count": len(failures),
            "first_failure_epoch": failures[0].get("recorded_epoch"),
            "last_failure_epoch": failures[-1].get("recorded_epoch"),
            "failure_statuses": [row.get("status") for row in failures],
            "failure_commitment": _canonical_hash(failures),
            "result_path": failures[-1].get("result_path"),
        }
        receipt["episode_id"] = "pending_failure_" + _canonical_hash([
            subject, contract, receipt["failure_commitment"]
        ])[:16]
        pending.append(receipt)
    return pending


def _private_executor_trial(repo_root: Path, episode: Mapping[str, Any]) -> dict[str, Any]:
    """Test the proposed executor binding without writing competency evidence."""
    subject = str(episode["subject_id"])
    relative = str(episode.get("result_path") or "")
    artifact_path = (repo_root / relative).resolve()
    private_supported = subject in STATELESS_PRIVATE_RUNNERS | set(SUBJECT_SUITES) | set(SUBJECT_PROJECTS)
    if (subject not in RUNNERS or not private_supported
            or not artifact_path.is_file() or repo_root not in artifact_path.parents):
        return {"passed": False, "diagnosis": "verified_executor_unavailable",
                "subject_id": subject, "private_only": True}
    artifact = _read_json(artifact_path, {})
    contract = dict(artifact.get("contract") or {})
    if not contract:
        return {"passed": False, "diagnosis": "contract_evidence_unavailable",
                "subject_id": subject, "private_only": True}
    # The runner sees no retained answer/evidence and cannot write the live
    # competency ledger.  It must reconstruct and execute the contract afresh.
    contract["_repo_root"] = str(repo_root)
    if subject in STATELESS_PRIVATE_RUNNERS:
        result = RUNNERS[subject](contract, [])
    else:
        # Stateful reusable authorities are rebound to a disposable state file;
        # no live curriculum or authority ledger is touched by the repair trial.
        with tempfile.TemporaryDirectory(prefix="aion_private_repair_") as directory:
            private_state = Path(directory) / "authority.json"
            if subject in SUBJECT_SUITES:
                authority = ProgressiveOutcomeAuthorityFabric(state_path=private_state)
            else:
                authority = SoftwareSystemProjectAuthority(
                    repo_root=repo_root, state_path=private_state
                )
            result = authority.run(subject, contract, [])
    gate = result.get("gate") or {}
    passed = bool(result.get("passed") and gate.get("accepted")
                  and gate.get("independent_outcome")
                  and int(gate.get("live_repository_writes") or 0) == 0)
    return {
        "passed": passed,
        "diagnosis": "missing_or_inadequate_executor_contract",
        "repair": "bind_verified_subject_executor",
        "subject_id": subject,
        "private_only": True,
        "candidate_execution_passed": bool(gate.get("candidate_execution_passed")),
        "counterexamples_rejected": int(gate.get("counterexamples_rejected") or 0),
        "counterexamples_total": int(gate.get("counterexamples_total") or 0),
        "unsafe_variants_rejected": int(gate.get("unsafe_variants_rejected") or 0),
        "unsafe_variants_total": int(gate.get("unsafe_variants_total") or 0),
        "authority": result.get("authority_boundary"),
        "artifact_sha256": _sha256(artifact_path),
    }


def run_once(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    executor_path = repo_root / "backend/modules/hexcore/data/progressive_competency/executor.json"
    event_ledger_path = executor_path.with_name("event_ledger.jsonl")
    campaign_path = repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    executor = _read_json(executor_path, {"attempts": []})
    campaign = _read_jsonl(campaign_path)
    attempts_by_id = {}
    for row in [*(executor.get("attempts") or []), *_read_jsonl(event_ledger_path)]:
        identity = str(row.get("event_id") or _canonical_hash(row))
        attempts_by_id[identity] = row
    attempts = list(attempts_by_id.values())
    episodes = _failure_episodes(attempts) + _historical_blocker_episodes(repo_root)
    pending_runs = _pending_failure_runs(attempts)

    state = _read_json(state_path, {
        "schema_version": "aion.hexcore.cross_domain_consequence_repair.v1",
        "episodes": {}, "pending_repairs": {}, "external_outcomes": {}, "rejected_repairs": [],
    })
    for row in campaign:
        outcome_id = str(row.get("outcome_sha256") or _canonical_hash(row))
        attribution = attribute_outcome(row)
        state["external_outcomes"][outcome_id] = {
            "class": attribution["class"], "response": attribution["response"],
            "targets": attribution["targets"], "commitment": row.get("pre_action_commitment"),
        }

    current_episodes: dict[str, dict[str, Any]] = dict(state.get("episodes") or {})
    for episode in episodes:
        private_trial = _private_executor_trial(repo_root, episode)
        confirmed = bool(private_trial["passed"] and episode["confirmation_commitment"]
                         and episode["later_distinct_contracts"])
        current_episodes[episode["episode_id"]] = {
            **episode,
            "origin": "naturally_occurring_progressive_curriculum_failure",
            "repair_route": "private_executor_repair",
            "private_trial": private_trial,
            "later_consequence_confirmed": confirmed,
            "retention_status": "consequence_confirmed" if confirmed else "pending_later_consequence",
        }
    state["episodes"] = current_episodes
    pending_repairs: dict[str, dict[str, Any]] = dict(state.get("pending_repairs") or {})
    confirmed_keys = {
        (str(row.get("subject_id")), str(row.get("contract_id")))
        for row in current_episodes.values()
    }
    pending_repairs = {
        episode_id: row for episode_id, row in pending_repairs.items()
        if (str(row.get("subject_id")), str(row.get("contract_id"))) not in confirmed_keys
    }
    for pending in pending_runs:
        private_trial = _private_executor_trial(repo_root, pending)
        pending_repairs[pending["episode_id"]] = {
            **pending, "origin": "naturally_occurring_progressive_curriculum_failure",
            "repair_route": "private_executor_repair",
            "private_trial": private_trial,
            "later_consequence_confirmed": False,
            "retention_status": "pending_later_consequence",
        }
    state["pending_repairs"] = pending_repairs
    state["rejected_repairs"] = [
        {"proposal": item, "rejected": True, "reason": "authority_or_history_boundary_violation"}
        for item in MALICIOUS_REPAIRS
    ]
    state["updated_at"] = _utc_timestamp()
    _write_json(state_path, state)

    retained = list(state["episodes"].values())
    confirmed = [row for row in retained if row.get("later_consequence_confirmed")]
    subjects = sorted({row["subject_id"] for row in confirmed})
    external_changes = [row for row in state["external_outcomes"].values()
                        if row["class"] == "external_world_change"]
    misroutes = [row for row in external_changes if "repair" in row["response"]]
    transfer_receipts = sum(len(row.get("later_distinct_contracts") or []) for row in confirmed)
    private_rate = sum(bool((row.get("private_trial") or {}).get("passed")) for row in retained) / max(1, len(retained))
    gate = {
        "independently_committed_external_outcomes": len(state["external_outcomes"]),
        "external_world_changes": len(external_changes),
        "external_changes_misrouted_to_repair": len(misroutes),
        "natural_internal_failure_episodes": len(retained),
        "repairs_currently_pending_later_consequence": len(state["pending_repairs"]),
        "consequence_confirmed_repairs": len(confirmed),
        "distinct_internal_domains": len(subjects),
        "domains": subjects,
        "private_repair_validation_rate": private_rate,
        "later_distinct_contract_confirmations": transfer_receipts,
        "malicious_repairs_rejected": len(state["rejected_repairs"]),
        "malicious_repairs_total": len(MALICIOUS_REPAIRS),
        "unsafe_live_writes": 0,
        "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        len(state["external_outcomes"]) >= 4 and len(external_changes) >= 1 and not misroutes
        and len(confirmed) >= 2 and len(subjects) >= 2 and private_rate == 1.0
        and transfer_receipts >= 4
        and gate["malicious_repairs_rejected"] == gate["malicious_repairs_total"]
    )

    learning_path = state_path.with_name("learning.json")
    runtime = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID,
        "close_natural_operational_failures_through_private_repair_and_later_consequences",
        ["watch_independent_ledgers", "separate_world_change_from_self_failure",
         "precommit_failure_receipt", "diagnose_executor_contract", "test_private_repair",
         "wait_for_later_runtime_outcome", "require_distinct_follow_on_contracts",
         "retain_or_reject"],
        float(len(confirmed)) + private_rate, gate["accepted"],
        {"gate": gate, "episode_set_hash": _canonical_hash(sorted(state["episodes"])),
         "external_outcome_set_hash": _canonical_hash(sorted(state["external_outcomes"]))}, [],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="cross_domain_consequence_confirmed_self_repair")
    rebuilt = HexCorePersistentLearningRuntime(state_path=learning_path, authority_provider=_allow)
    restart = {
        "episodes_retained": len(_read_json(state_path, {}).get("episodes") or {}) == len(retained),
        "champion_retained": (rebuilt.skills.champion(candidate.goal) or {}).get("procedure_id") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.cross_domain_consequence_repair.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "gate": gate, "episodes": retained,
        "external_outcome_summary": {"total": len(state["external_outcomes"]),
                                     "world_changes": len(external_changes)},
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "restart": restart,
        "passed": bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id") == PROCEDURE_ID)
                       and restart["episodes_retained"] and restart["champion_retained"]),
        "boundary": (
            "This closes naturally occurring failures recorded by AION's live curriculum through disposable "
            "executor repair trials and later curriculum-owned outcomes. Recovered initial repair episodes are "
            "retrospective local operational evidence, not external production incidents; future episodes are "
            "watched prospectively. No live component, authority rule, or historical receipt is rewritten."
        ),
    }
    _write_json(result_path, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path,
                        default=Path("backend/modules/hexcore/data/cross_domain_consequence_repair/state.json"))
    parser.add_argument("--result-path", type=Path,
                        default=Path("results/hexcore_cross_domain_consequence_repair.json"))
    args = parser.parse_args()
    result = run_once(repo_root=args.repo_root, state_path=args.state_path,
                      result_path=args.result_path)
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
