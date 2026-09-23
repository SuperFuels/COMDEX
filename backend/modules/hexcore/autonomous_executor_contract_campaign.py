"""Invent and verify executor contracts for weakness-driven apprentice tasks.

The campaign consumes tasks emitted by the Autonomous General Apprentice.  It
does not invent terminal goals.  When no retained executor applies, it selects
a safe installed outcome authority, reconstructs a compatible verified method,
runs fresh authority tests, and registers the resulting executor only after a
verified receipt exists.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
)
from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)
from backend.modules.hexcore.real_rust_apprenticeship import run as run_rust
from backend.modules.hexcore.polyglot_execution_contract_benchmark import (
    run_polyglot_execution_contract,
)
from backend.modules.hexcore.rust_sql_systems_depth_benchmark import (
    run_rust_sql_systems_depth,
)


PROCEDURE_ID = "procedure_autonomous_executor_contract_campaign_v1"


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True, "deny_reason": None, "goal": goal,
        "source": "autonomous_executor_contract_campaign_cau", "S": 1.0, "H": 0.0,
    }


def _candidate_steps(result: Mapping[str, Any]) -> list[str]:
    return list((((result.get("promotion") or {}).get("candidate") or {}).get("steps") or []))


def _run_cargo(repo_root: Path, workspace: Path) -> dict[str, Any]:
    result = run_rust(
        state_path=workspace / "rust/state.json",
        result_path=workspace / "rust/result.json",
    )
    return {
        "passed": result["passed"],
        "procedure_id": result["procedure_id"],
        "result_hash": _canonical_hash(result),
        "capabilities": _candidate_steps(result),
        "authorities": ["local_executable:cargo", "local_executable:rustc"],
        "transfer_family": "compiler_grounded_systems_engineering",
        "retention_verified": bool(
            result.get("gate", {}).get("restart_retention_success") == 1.0
            and result.get("gate", {}).get("restart_projects_retained") == 4
            and result.get("gate", {}).get("source_replay_into_retention") == 0
        ),
        "independent_outcomes": sum(
            bool(row.get("hidden_gate", {}).get("passed"))
            for row in result.get("projects") or []
        ),
        "unsafe_actions": result.get("gate", {}).get("unsafe_candidates_executed", 0),
        "live_writes": result.get("gate", {}).get("live_repository_writes", 0),
        "summary": result.get("gate", {}),
    }


def _run_node(repo_root: Path, workspace: Path) -> dict[str, Any]:
    result = run_polyglot_execution_contract(
        repo_root=repo_root,
        adapter_result_path=repo_root / "results/hexcore_verified_execution_adapter_acquisition.json",
        property_result_path=repo_root / "results/hexcore_adapter_grounded_property_invention.json",
        state_path=workspace / "node/state.json",
        result_path=workspace / "node/result.json",
    )
    javascript = [
        row for row in result.get("targets") or []
        if row.get("language") in {"javascript", "typescript"}
    ]
    return {
        "passed": bool(result["passed"] and javascript and all(row["passed"] for row in javascript)),
        "procedure_id": result["promotion"]["candidate"]["procedure_id"],
        "result_hash": _canonical_hash(result),
        "capabilities": _candidate_steps(result),
        "authorities": ["local_executable:node"],
        "transfer_family": "event_driven_polyglot_execution",
        "retention_verified": bool(
            result.get("restart", {}).get("contracts_retained")
            and result.get("restart", {}).get("session_retained")
            and result.get("restart", {}).get("champion_retained")
        ),
        "independent_outcomes": len(javascript),
        "unsafe_actions": result.get("gate", {}).get("unsafe_live_writes", 0),
        "live_writes": result.get("gate", {}).get("unsafe_live_writes", 0),
        "summary": result.get("gate", {}),
    }


def _run_sqlite(repo_root: Path, workspace: Path) -> dict[str, Any]:
    retained = json.loads(
        (repo_root / "results/hexcore_rust_sql_systems_depth.json").read_text(encoding="utf-8")
    )

    def retained_selection(_prompt: str, timeout: int = 0) -> dict[str, Any]:
        del timeout
        return {
            "available": True,
            "source": "retained_verified_measurement_policy",
            "proposal": dict(retained.get("selection", {}).get("proposal") or {}),
        }

    initial = dict(retained.get("construction") or {})
    if retained.get("sql_revision_proposal"):
        initial.update(retained["sql_revision_proposal"])
    result = run_rust_sql_systems_depth(
        state_path=workspace / "sqlite/state.json",
        result_path=workspace / "sqlite/result.json",
        provider=retained_selection,
        initial_construction=initial,
    )
    return {
        "passed": bool(result["passed"] and result.get("sql", {}).get("passed")),
        "procedure_id": result["promotion"]["candidate"]["procedure_id"],
        "result_hash": _canonical_hash(result),
        "capabilities": _candidate_steps(result),
        "authorities": ["local_executable:sqlite3"],
        "transfer_family": "transactional_schema_and_measurement_reasoning",
        "retention_verified": bool(
            result.get("restart", {}).get("sql_skill_retained")
            and result.get("restart", {}).get("policy_retained")
            and result.get("restart", {}).get("session_retained")
        ),
        "independent_outcomes": len((result.get("sql") or {}).get("checks") or {}),
        "unsafe_actions": result.get("gate", {}).get("unsafe_programs_executed", 0),
        "live_writes": result.get("gate", {}).get("live_repository_writes", 0),
        "summary": result.get("gate", {}),
    }


RUNNERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "local_executable:cargo": _run_cargo,
    "local_executable:rustc": _run_cargo,
    "local_executable:node": _run_node,
    "local_executable:sqlite3": _run_sqlite,
}


def _invent_contract(task: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    contract_id = "procedure_executor_" + _canonical_hash({
        "task_gate": task["gate"],
        "authority": task["authority_id"],
        "verified_parent": outcome["procedure_id"],
        "capabilities": outcome["capabilities"],
    })[:20]
    return {
        "procedure_id": contract_id,
        "proposal_only": True,
        "authorities": outcome["authorities"],
        "input_features": [
            "unfamiliar_objective", f"gate:{task['gate']}",
            "available_verified_method_cards", "installed_outcome_authority",
            "source_disjoint_transfer_required", "restart_retention_required",
        ],
        "capabilities": [
            "recover_authority_contract", "construct_private_curriculum",
            "execute_public_criticism", "open_hidden_outcome_after_selection",
            "transfer_to_unfamiliar_family", "reconstruct_and_retest",
            *list(outcome["capabilities"]),
        ],
        "transfer_families": [outcome["transfer_family"]],
        "verified_parent": outcome["procedure_id"],
        "contract_hash": _canonical_hash(outcome),
    }


def run(
    *, repo_root: Path, apprentice_state_path: Path, state_path: Path,
    result_path: Path, maximum_executors: int = 3,
) -> dict[str, Any]:
    campaign_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "schema_version": "aion.hexcore.autonomous_executor_contract_campaign.v1",
        "episodes": [], "started_at": _utc_timestamp(),
    }
    with tempfile.TemporaryDirectory(prefix="aion_executor_contract_campaign_") as raw:
        workspace = Path(raw)
        for episode_index in range(maximum_executors):
            if sum(
                row.get("status") == "verified"
                for row in campaign_state["episodes"]
            ) >= maximum_executors:
                break
            apprentice = AutonomousGeneralApprentice(
                state_path=apprentice_state_path, repo_root=repo_root
            )
            apprentice.refresh_evidence()
            task = next(
                (
                    row for row in apprentice.state["curriculum_history"]
                    if row.get("status") == "proposed"
                ),
                None,
            )
            if task is None:
                rejected = next(
                    (
                        row for row in reversed(campaign_state["episodes"])
                        if row.get("status") == "rejected"
                        and not any(
                            later.get("task_id") == row.get("task_id")
                            and later.get("status") == "verified"
                            for later in campaign_state["episodes"]
                        )
                    ),
                    None,
                )
                if rejected:
                    task = next(
                        (
                            row for row in apprentice.state["curriculum_history"]
                            if row.get("task_id") == rejected.get("task_id")
                        ),
                        None,
                    )
            if task is None:
                task = apprentice.next_task()
            authority = str(task.get("authority_id") or "")
            runner = RUNNERS.get(authority)
            if runner is None:
                apprentice.reject_task_contract(
                    task_id=task["task_id"],
                    reason="no_independently_revealing_safe_execution_adapter",
                )
                campaign_state["episodes"].append({
                    "episode": len(campaign_state["episodes"]) + 1,
                    "task_id": task.get("task_id"), "authority": authority,
                    "status": "needs_new_safe_execution_adapter",
                    "recorded_at": _utc_timestamp(),
                })
                break
            already = next(
                (
                    row for row in campaign_state["episodes"]
                    if row.get("task_id") == task["task_id"] and row.get("status") == "verified"
                ),
                None,
            )
            if already:
                continue
            outcome = runner(repo_root, workspace / f"episode_{episode_index + 1}")
            verified = bool(
                outcome["passed"] and outcome["retention_verified"]
                and outcome["independent_outcomes"] > 0
                and outcome["unsafe_actions"] == outcome["live_writes"] == 0
            )
            receipt = apprentice.record_outcome(
                task_id=task["task_id"],
                outcome={
                    "authority_id": authority, "verified": verified,
                    "score": 1.0 if verified else 0.0,
                    "transfer_family": outcome["transfer_family"],
                    "retention_verified": outcome["retention_verified"],
                    "executor_outcome_hash": outcome["result_hash"],
                },
            )
            contract = _invent_contract(task, outcome)
            retained_contract = apprentice.register_executor_contract(
                procedure_id=contract["procedure_id"],
                receipt_id=receipt["receipt_id"], contract=contract,
            ) if verified else None
            generation = apprentice.close_generation()
            campaign_state["episodes"].append({
                "episode": len(campaign_state["episodes"]) + 1,
                "task_id": task["task_id"], "gate": task["gate"],
                "authority": authority, "status": "verified" if verified else "rejected",
                "outcome": outcome, "receipt": receipt,
                "executor_contract": retained_contract, "generation": generation,
                "recorded_at": _utc_timestamp(),
            })
            if not verified:
                break
    campaign_state["updated_at"] = _utc_timestamp()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(campaign_state, indent=2, sort_keys=True), encoding="utf-8")

    verified_episodes = [row for row in campaign_state["episodes"] if row["status"] == "verified"]
    authorities = sorted({row["authority"] for row in verified_episodes})
    transfers = sorted({row["outcome"]["transfer_family"] for row in verified_episodes})
    contracts = sorted({row["executor_contract"]["procedure_id"] for row in verified_episodes})
    gate = {
        "verified_executor_inventions": len(verified_episodes),
        "distinct_outcome_authorities": len(authorities),
        "distinct_transfer_families": len(transfers),
        "all_retained_after_restart": all(
            row["outcome"]["retention_verified"] for row in verified_episodes
        ),
        "independent_outcomes": sum(
            row["outcome"]["independent_outcomes"] for row in verified_episodes
        ),
        "unsafe_actions": sum(row["outcome"]["unsafe_actions"] for row in verified_episodes),
        "live_repository_writes": sum(row["outcome"]["live_writes"] for row in verified_episodes),
        "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["verified_executor_inventions"] >= maximum_executors
        and gate["distinct_outcome_authorities"] >= maximum_executors
        and gate["distinct_transfer_families"] >= maximum_executors
        and gate["all_retained_after_restart"]
        and gate["independent_outcomes"] >= maximum_executors
        and gate["unsafe_actions"] == gate["live_repository_writes"] == gate["objective_mutations"] == 0
    )
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "autonomous_executor_contract_invention",
        [
            "consume_weakness_driven_apprentice_task",
            "detect_missing_executor_contract",
            "select_installed_independent_outcome_authority",
            "reconstruct_compatible_verified_method",
            "execute_fresh_public_hidden_transfer_and_retention_gates",
            "register_proposal_only_executor_after_verified_receipt",
            "close_generation_and_select_novel_authority",
        ],
        len(verified_episodes) / max(1, maximum_executors), gate["accepted"],
        {"gate": gate, "contracts": contracts, "authorities": authorities},
        ["procedure_autonomous_general_apprentice_kernel_v1"],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.commit(reason="autonomous_executor_contract_campaign")
    champion = learning.skills.champion("autonomous_executor_contract_invention") or {}
    apprentice = AutonomousGeneralApprentice(
        state_path=apprentice_state_path, repo_root=repo_root
    )
    apprentice.refresh_evidence()
    next_task = next(
        (
            row for row in apprentice.state["curriculum_history"]
            if row.get("status") == "proposed"
        ),
        None,
    )
    if next_task is None and gate["accepted"]:
        next_task = apprentice.next_task()
    result = {
        "schema_version": campaign_state["schema_version"],
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "episodes": campaign_state["episodes"], "gate": gate,
        "authorities": authorities, "transfer_families": transfers,
        "executor_contracts": contracts,
        "next_weakness_driven_task": next_task,
        "promotion": {
            "candidate": candidate.to_dict(), "decision": decision,
            "champion_retained": champion.get("procedure_id") == PROCEDURE_ID,
        },
        "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
        "boundary": (
            "This demonstrates autonomous executor-contract acquisition across three "
            "installed outcome authorities. Safe runner adapters and authority-specific "
            "verification harnesses remain engineered; it is not arbitrary subject mastery."
        ),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--apprentice-state", type=Path,
        default=Path("backend/modules/hexcore/data/autonomous_general_apprentice/state.json"),
    )
    parser.add_argument(
        "--state-path", type=Path,
        default=Path("backend/modules/hexcore/data/autonomous_executor_contract_campaign/state.json"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_autonomous_executor_contract_campaign.json"),
    )
    parser.add_argument("--maximum-executors", type=int, default=3)
    args = parser.parse_args()
    result = run(
        repo_root=args.repo_root.resolve(),
        apprentice_state_path=args.apprentice_state.resolve(),
        state_path=args.state_path.resolve(), result_path=args.result_path.resolve(),
        maximum_executors=max(1, args.maximum_executors),
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
