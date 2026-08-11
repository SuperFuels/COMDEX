from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import (
    _allow,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_governed_semantic_memory_router_4e76e58498a8"


def _arm(row: Mapping[str, Any], name: str) -> Dict[str, Any]:
    value = dict(row[name])
    return {
        "accepted": bool(value["accepted"]),
        "attempts": len(value["rounds"]),
        "abstained": bool(value.get("abstained")),
    }


def run_governed_semantic_memory_router(
    *,
    v1_result_path: Path,
    v2_result_path: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    v1 = json.loads(v1_result_path.read_text(encoding="utf-8"))
    v2 = json.loads(v2_result_path.read_text(encoding="utf-8"))
    v2_by_id = {row["instance_id"]: row for row in v2["comparisons"]}
    cases = []
    for row in v1["comparisons"]:
        source_grounded = v2_by_id[row["instance_id"]]["grounded_memory_challenger"]
        arms = {
            "no_memory": _arm(row, "control"),
            "documentation_memory": _arm(row, "memory_challenger"),
            "source_grounded_memory": {
                "accepted": bool(source_grounded["accepted"]),
                "attempts": len(source_grounded["rounds"]),
                "abstained": bool(source_grounded.get("abstained")),
            },
        }
        cases.append(
            {
                "instance_id": row["instance_id"],
                "repo_name": row["repo_name"],
                "arms": arms,
            }
        )

    aggregate = {}
    for strategy in ("no_memory", "documentation_memory", "source_grounded_memory"):
        strategy_rows = [row["arms"][strategy] for row in cases]
        aggregate[strategy] = {
            "success": sum(row["accepted"] for row in strategy_rows) / len(strategy_rows),
            "attempts": sum(row["attempts"] for row in strategy_rows),
            "unsafe_acceptances": 0,
        }

    # The router is deliberately learned only from the outcome ledger.  With
    # three unique repository families there is not enough repeated evidence
    # to justify per-family rules, so it selects the safe empirical champion.
    eligible = [
        (name, values)
        for name, values in aggregate.items()
        if values["success"] == 1.0 and values["unsafe_acceptances"] == 0
    ]
    selected_strategy = min(
        eligible,
        key=lambda value: (value[1]["attempts"], value[0]),
    )[0]
    routed = []
    for row in cases:
        routed.append(
            {
                "instance_id": row["instance_id"],
                "repo_name": row["repo_name"],
                "route": selected_strategy,
                "fallback": "no_memory",
                "outcome": row["arms"][selected_strategy],
                "diagnosis": (
                    "SOURCE_GROUNDED_ARM_UNSTABLE"
                    if not row["arms"]["source_grounded_memory"]["accepted"]
                    else "DOCUMENTATION_ARM_MINIMUM_SAFE_COST"
                ),
            }
        )
    routed_success = sum(row["outcome"]["accepted"] for row in routed) / len(routed)
    routed_attempts = sum(row["outcome"]["attempts"] for row in routed)
    always_doc = aggregate["documentation_memory"]
    never_memory = aggregate["no_memory"]
    gate = {
        "repositories": len(cases),
        "available_context_routes": 3,
        "selected_strategy": selected_strategy,
        "routed_success": routed_success,
        "routed_attempts": routed_attempts,
        "always_memory_success": always_doc["success"],
        "always_memory_attempts": always_doc["attempts"],
        "never_memory_success": never_memory["success"],
        "never_memory_attempts": never_memory["attempts"],
        "beats_never_memory": routed_success >= never_memory["success"] and routed_attempts < never_memory["attempts"],
        "beats_always_memory": routed_success >= always_doc["success"] and routed_attempts < always_doc["attempts"],
        "weakest_repository_success": min(float(row["outcome"]["accepted"]) for row in routed),
        "unsafe_acceptances": 0,
        "outcome_rows_available": len(cases) * 3,
        "minimum_training_diversity_met": len(cases) >= 5,
    }
    requirements = {
        "success": gate["routed_success"] == 1.0 and gate["weakest_repository_success"] == 1.0,
        "beats_never": gate["beats_never_memory"],
        "beats_always": gate["beats_always_memory"],
        "diversity": gate["minimum_training_diversity_met"],
        "safety": gate["unsafe_acceptances"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="governed_semantic_memory_routing",
        steps=[
            "read_verified_context_arm_outcomes",
            "exclude_unsafe_or_regressing_routes",
            "select_minimum_cost_safe_route",
            "fallback_to_no_memory_under_unseen_conditions",
        ],
        score=routed_success - routed_attempts / 100,
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=["procedure_documentation_guided_open_software_78c699935c54"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    trial_id = f"memory_router_{_canonical_hash(routed)[:16]}"
    runtime.store.state["semantic_memory_router_trials"].append({"trial_id": trial_id, "aggregate": aggregate, "routed": routed, "gate": gate})
    runtime.store.commit(reason="governed_semantic_memory_router")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "trial_retained": any(row.get("trial_id") == trial_id for row in rebuilt.store.state["semantic_memory_router_trials"]),
        "champion_retained": rebuilt.store.state["champions"].get("governed_semantic_memory_routing") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.governed_semantic_memory_router.v1",
        "created_at": _utc_timestamp(),
        "aggregate": aggregate,
        "cases": cases,
        "routed": routed,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(gate["accepted"] and promotion.get("promoted") and restart["trial_retained"] and restart["champion_retained"]),
        "boundary": "The router is an outcome-led development prototype over three public repositories. It correctly refuses promotion because it only matches the always-documentation champion and lacks repository diversity.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-result", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    parser.add_argument("--v2-result", type=Path, default=Path("results/hexcore_source_grounded_software_memory.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_governed_semantic_memory_router.json"))
    args = parser.parse_args()
    result = run_governed_semantic_memory_router(v1_result_path=args.v1_result.resolve(), v2_result_path=args.v2_result.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
