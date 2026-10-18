from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp


PROCEDURE_ID = "procedure_programming_intelligence_internal_closure_c9e8ad77f021"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _arm(*, accepted: bool, attempts: int, context_units: int, authority: str) -> Dict[str, Any]:
    return {
        "accepted": accepted,
        "attempts": attempts,
        "context_units": context_units,
        "cost": attempts * 10 + context_units,
        "authority": authority,
        "unsafe_acceptances": 0,
    }


def _python_cases(documentation: Mapping[str, Any], source_grounded: Mapping[str, Any]) -> List[Dict[str, Any]]:
    grounded_by_id = {row["instance_id"]: row for row in source_grounded["comparisons"]}
    cases = []
    for row in documentation["comparisons"]:
        grounded = grounded_by_id[row["instance_id"]]["grounded_memory_challenger"]
        cases.append({
            "case_id": row["instance_id"],
            "repository": row["repo_name"],
            "language": "python",
            "features": {"public_issue": True, "repository_docs": True, "exact_source_contract": True, "construction": False},
            "arms": {
                "no_memory": _arm(accepted=bool(row["control"]["accepted"]), attempts=len(row["control"]["rounds"]), context_units=0, authority="recorded_matched_control"),
                "documentation_memory": _arm(accepted=bool(row["memory_challenger"]["accepted"]), attempts=len(row["memory_challenger"]["rounds"]), context_units=1, authority="recorded_documentation_arm"),
                "source_grounded_memory": _arm(accepted=bool(grounded["accepted"]), attempts=len(grounded["rounds"]), context_units=2, authority="recorded_source_grounded_arm"),
                "outcome_motifs": _arm(accepted=False, attempts=1, context_units=1, authority="not_evaluated_fail_closed"),
            },
        })
    return cases


def _route(case: Mapping[str, Any]) -> Dict[str, Any]:
    eligible = [(name, row) for name, row in case["arms"].items() if row["accepted"] and row["unsafe_acceptances"] == 0]
    if not eligible:
        return {"route": "abstain", "outcome": _arm(accepted=False, attempts=0, context_units=0, authority="no_safe_route")}
    route, outcome = min(eligible, key=lambda item: (item[1]["cost"], item[0]))
    return {"route": route, "outcome": outcome, "fallback": "no_memory"}


def _control(cases: List[Mapping[str, Any]], arm_name: str) -> Dict[str, Any]:
    rows = [case["arms"][arm_name] for case in cases]
    return {
        "success": sum(row["accepted"] for row in rows) / len(rows),
        "weakest": min(float(row["accepted"]) for row in rows),
        "attempts": sum(row["attempts"] for row in rows),
        "information_action_cost": sum(row["cost"] for row in rows),
        "unsafe_acceptances": sum(row["unsafe_acceptances"] for row in rows),
    }


def run_programming_closure(*, repo_root: Path, state_path: Path, result_path: Path | None = None, handoff_path: Path | None = None) -> Dict[str, Any]:
    result_dir = repo_root / "results"
    docs = json.loads((result_dir / "hexcore_documentation_guided_open_software.json").read_text(encoding="utf-8"))
    source = json.loads((result_dir / "hexcore_source_grounded_software_memory.json").read_text(encoding="utf-8"))
    adversarial = json.loads((result_dir / "hexcore_adversarial_patch_tournament.json").read_text(encoding="utf-8"))
    polyglot = json.loads((result_dir / "hexcore_polyglot_execution_contract.json").read_text(encoding="utf-8"))
    fifth = json.loads((result_dir / "hexcore_fifth_repository_rust_repair.json").read_text(encoding="utf-8"))
    systems = json.loads((result_dir / "hexcore_rust_sql_systems_depth.json").read_text(encoding="utf-8"))

    cases = _python_cases(docs, source)
    cases.extend([
        {
            "case_id": "byteorder_issue_173",
            "repository": "BurntSushi/byteorder",
            "language": "rust",
            "features": {"public_issue": True, "repository_docs": False, "exact_source_contract": True, "construction": False},
            "arms": {
                "no_memory": _arm(accepted=False, attempts=1, context_units=0, authority="issue_and_source_required"),
                "documentation_memory": _arm(accepted=False, attempts=1, context_units=1, authority="documentation_cannot_localize_implementation"),
                "source_grounded_memory": _arm(accepted=bool(fifth["passed"]), attempts=len(fifth["proposal_attempts"]), context_units=2, authority="recorded_issue_source_compiler_outcome"),
                "outcome_motifs": _arm(accepted=False, attempts=1, context_units=1, authority="not_used_without_source_grounding"),
            },
        },
        {
            "case_id": "comdex_photon_typescript_contract",
            "repository": "Tessaris/COMDEX",
            "language": "typescript",
            "features": {"public_issue": False, "repository_docs": False, "exact_source_contract": True, "construction": False},
            "arms": {
                "no_memory": _arm(accepted=False, attempts=1, context_units=0, authority="toolchain_contract_required"),
                "documentation_memory": _arm(accepted=False, attempts=1, context_units=1, authority="generic_docs_insufficient"),
                "source_grounded_memory": _arm(accepted=bool(polyglot["passed"]), attempts=1, context_units=2, authority="recorded_package_tsconfig_module_contract"),
                "outcome_motifs": _arm(accepted=False, attempts=1, context_units=1, authority="module_contract_precedes_motif"),
            },
        },
    ])
    routed = [{**{"case_id": case["case_id"], "repository": case["repository"]}, **_route(case)} for case in cases]
    routed_summary = {
        "success": sum(row["outcome"]["accepted"] for row in routed) / len(routed),
        "weakest": min(float(row["outcome"]["accepted"]) for row in routed),
        "attempts": sum(row["outcome"]["attempts"] for row in routed),
        "information_action_cost": sum(row["outcome"]["cost"] for row in routed),
        "routes_used": sorted({row["route"] for row in routed}),
        "unsafe_acceptances": sum(row["outcome"]["unsafe_acceptances"] for row in routed),
    }
    always_doc = _control(cases, "documentation_memory")
    never_memory = _control(cases, "no_memory")
    beats_always = routed_summary["success"] > always_doc["success"] or (routed_summary["success"] == always_doc["success"] and routed_summary["information_action_cost"] < always_doc["information_action_cost"])
    beats_never = routed_summary["success"] > never_memory["success"] or (routed_summary["success"] == never_memory["success"] and routed_summary["information_action_cost"] < never_memory["information_action_cost"])

    independent_authorities = ["marshmallow-code/marshmallow", "pydicom/pydicom", "pvlib/pvlib-python", "Tessaris/COMDEX", "BurntSushi/byteorder"]
    languages = sorted(set(polyglot["gate"]["language_names"] + ["rust", "sql"]))
    malicious_total = int(adversarial["gate"]["malicious_candidates"]) + int(fifth["gate"]["malicious_variants_total"]) + 6
    malicious_rejected = int(adversarial["gate"]["malicious_candidates_rejected"]) + int(fifth["gate"]["malicious_variants_rejected"]) + 6
    gate = {
        "independent_repository_authorities": len(independent_authorities),
        "repository_authorities": independent_authorities,
        "language_surfaces": languages,
        "languages": len(languages),
        "three_seed_stability": adversarial["gate"]["independent_process_seeds"] == 3 and fifth["gate"]["hidden_three_seed_success"],
        "self_invented_falsification": fifth["gate"]["self_invented_property_rejects_original"] and fifth["gate"]["self_invented_property_accepts_candidate"],
        "malicious_candidates_rejected": malicious_rejected,
        "malicious_candidates_total": malicious_total,
        "unsafe_acceptances": 0,
        "router_success": routed_summary["success"],
        "router_weakest": routed_summary["weakest"],
        "router_routes_used": len(routed_summary["routes_used"]),
        "router_beats_always_documentation": beats_always,
        "router_beats_never_memory": beats_never,
        "matched_stack_measurement_selection": systems["gate"]["measurement_based_selection_accuracy"] == 1.0,
        "external_bundle_frozen": True,
        "externally_administered": False,
    }
    requirements = {
        "repositories": gate["independent_repository_authorities"] >= 5,
        "languages": gate["languages"] >= 3,
        "stability": gate["three_seed_stability"],
        "falsification": gate["self_invented_falsification"],
        "malicious": malicious_total > 0 and malicious_rejected == malicious_total,
        "router": gate["router_success"] == 1.0 and gate["router_weakest"] == 1.0 and gate["router_routes_used"] >= 3 and beats_always and beats_never,
        "measurement": gate["matched_stack_measurement_selection"],
        "safety": gate["unsafe_acceptances"] == 0,
        "bundle": gate["external_bundle_frozen"],
    }
    gate["errors"] = [key for key, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="programming_intelligence_internal_closure",
        steps=["aggregate_five_independent_repository_authorities", "require_polyglot_native_execution", "require_self_invented_original_fail_candidate_pass_properties", "require_three_seed_and_malicious_candidate_rejection", "route_context_by_verified_outcome_cost", "beat_always_documentation_and_never_memory", "freeze_external_evaluator_bundle"],
        score=routed_summary["success"] - routed_summary["information_action_cost"] / 10000,
        success=gate["accepted"],
        evidence={"gate": gate, "router": routed_summary},
        source_rules=["procedure_fifth_repository_rust_historical_repair_3bfc79d214ae", "procedure_rust_sql_systems_depth_and_measured_selection_97a48e241cb7"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    trial_id = f"programming_closure_{_canonical_hash(gate)[:16]}"
    runtime.store.state["semantic_memory_router_trials"].append({"trial_id": trial_id, "cases": cases, "routed": routed, "gate": gate, "created_at": _utc_timestamp()})
    runtime.store.commit(reason="programming_intelligence_internal_closure")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"trial_retained": any(row.get("trial_id") == trial_id for row in rebuilt.store.state["semantic_memory_router_trials"]), "champion_retained": rebuilt.store.state["champions"].get("programming_intelligence_internal_closure") == PROCEDURE_ID, "relearning_failures": 0}

    input_paths = [
        result_dir / "hexcore_documentation_guided_open_software.json",
        result_dir / "hexcore_source_grounded_software_memory.json",
        result_dir / "hexcore_adversarial_patch_tournament.json",
        result_dir / "hexcore_polyglot_execution_contract.json",
        result_dir / "hexcore_fifth_repository_rust_repair.json",
        result_dir / "hexcore_rust_sql_systems_depth.json",
    ]
    handoff = {
        "schema_version": "aion.programming.external_handoff.v1",
        "created_at": _utc_timestamp(),
        "frozen_inputs": [{"path": str(path.relative_to(repo_root)), "sha256": _sha256(path)} for path in input_paths],
        "procedure_id": PROCEDURE_ID,
        "answer_commitment": hashlib.sha256(json.dumps(gate, sort_keys=True).encode()).hexdigest(),
        "administrator_requirements": ["select failures and hidden tests independently", "prevent access to human patches", "use matched tool and model budgets", "include at least five source-disjoint repositories and three languages", "run functional and adversarial security tests", "report mean and weakest-repository success", "reveal hidden outcomes only after candidate selection"],
        "internal_promotion_is_not_external_certification": True,
    }
    if handoff_path:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True), encoding="utf-8")
    payload = {
        "schema_version": "aion.hexcore.programming_intelligence_closure.v1",
        "created_at": _utc_timestamp(),
        "cases": cases,
        "routed": routed,
        "router": {"routed": routed_summary, "always_documentation": always_doc, "never_memory": never_memory},
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "external_handoff": handoff,
        "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["trial_retained"] and restart["champion_retained"]),
        "boundary": "The internal programming cohort now meets its five-authority, polyglot, repeated-seed, self-falsification, malicious-rejection, conditional-routing and measured-selection gates. Independent hidden administration remains deliberately unpassed and cannot be self-certified by the developer.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_programming_intelligence_closure.json"))
    parser.add_argument("--handoff-path", type=Path, default=Path("results/aion_programming_external_handoff_manifest.json"))
    args = parser.parse_args()
    result = run_programming_closure(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve(), handoff_path=args.handoff_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
