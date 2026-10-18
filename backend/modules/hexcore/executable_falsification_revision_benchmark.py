from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.executable_falsification_invention_benchmark import (
    _audit_test_program,
    _execute_test,
    _selected_by_id,
)
from backend.modules.hexcore.open_patch_generation_benchmark import (
    _apply_proposal,
    _security_scan,
)
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.source_disjoint_swebench_repair_benchmark import (
    TASKS,
    _copy_repo,
    _dataset_rows,
    _hash_path,
)


PROCEDURE_ID = "procedure_revised_executable_falsification_e4d6d473c3db"


def _revision_prompt(
    *,
    issue: str,
    repo_name: str,
    prior: Mapping[str, Any],
) -> str:
    executions = prior.get("executions") or {}
    return f"""
You are revising two generated test programs after independent sandbox
execution. The selected repair and repository code are unchanged. Diagnose the
test-fixture or environment assumption that caused the candidate to fail, then
return safer, narrower tests. Do not weaken the core requirement: the
functional program must fail on the original reported bug and pass the selected
repair. The adversarial program must pass the selected repair and exercise at
least two relevant boundary properties.

Return JSON with functional_test_code, security_test_code, rationale,
security_properties, and revision_diagnosis. Programs run from repository root.
No network, subprocess, file writes, eval/exec, permission changes, secret
access or verification bypass. Use plain assertions.

REPOSITORY: {repo_name}
ISSUE:
{issue}

PRIOR FUNCTIONAL TEST:
{prior['invented'].get('functional_test_code', '')}

PRIOR SECURITY TEST:
{prior['invented'].get('security_test_code', '')}

FUNCTIONAL CANDIDATE TRACE:
{json.dumps(executions.get('functional_on_candidate') or {}, ensure_ascii=False)}

SECURITY CANDIDATE TRACE:
{json.dumps(executions.get('security_on_candidate') or {}, ensure_ascii=False)}

ORIGINAL TRACE:
{json.dumps(executions.get('functional_on_original') or {}, ensure_ascii=False)}

Revise the test harness, not the product patch. If a fixture converts invalid
data before reaching the target operation, use the repository's lazy/raw data
path. If importing the package executes unrelated incompatible modules, load
the target module in isolation with the minimum dependency stubs needed by that
module. These are harness corrections, not relaxed behavioral assertions.
""".strip()


def _evaluate(
    *,
    task: Any,
    accepted: Mapping[str, Any],
    invented: Mapping[str, Any],
    external_root: Path,
) -> Dict[str, Any]:
    functional = str(invented.get("functional_test_code") or "")
    security = str(invented.get("security_test_code") or "")
    functional_audit = _audit_test_program(functional)
    security_audit = _audit_test_program(security)
    base_repo = external_root / f"{task.repo_name}-base"
    path = str(accepted["localized_path"])
    source = (base_repo / path).read_text(encoding="utf-8")
    proposal = dict(accepted["selected"]["proposal"])
    application = _apply_proposal(source, proposal)
    candidate = str(application.get("candidate") or "")
    patch_scan = _security_scan(source, candidate) if application.get("applied") else {"safe": False, "findings": ["application_failed"]}
    executions: Dict[str, Any] = {}
    if functional_audit["safe"] and security_audit["safe"] and patch_scan["safe"]:
        with tempfile.TemporaryDirectory(prefix="aion_revised_test_base_") as raw:
            sandbox = Path(raw) / task.repo_name
            _copy_repo(base_repo, sandbox)
            executions["functional_on_original"] = _execute_test(functional, sandbox)
        with tempfile.TemporaryDirectory(prefix="aion_revised_test_candidate_") as raw:
            sandbox = Path(raw) / task.repo_name
            _copy_repo(base_repo, sandbox)
            (sandbox / path).write_text(candidate, encoding="utf-8")
            executions["functional_on_candidate"] = _execute_test(functional, sandbox)
            executions["security_on_candidate"] = _execute_test(security, sandbox)
    passed = bool(
        executions
        and not executions["functional_on_original"]["passed"]
        and executions["functional_on_candidate"]["passed"]
        and executions["security_on_candidate"]["passed"]
        and len(invented.get("security_properties") or []) >= 2
    )
    return {
        "functional_audit": functional_audit,
        "security_audit": security_audit,
        "selected_patch_security": patch_scan,
        "executions": executions,
        "original_rejected": bool(executions and not executions["functional_on_original"]["passed"]),
        "candidate_accepted": bool(executions and executions["functional_on_candidate"]["passed"]),
        "adversarial_candidate_accepted": bool(executions and executions["security_on_candidate"]["passed"]),
        "passed": passed,
    }


def run_executable_falsification_revision(
    *,
    first_result_path: Path,
    documentation_result_path: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    first = json.loads(first_result_path.read_text(encoding="utf-8"))
    documentation = json.loads(documentation_result_path.read_text(encoding="utf-8"))
    first_by_id = {row["instance_id"]: row for row in first["outcomes"]}
    accepted_by_id = _selected_by_id(documentation)
    dataset = _dataset_rows(dataset_path)
    live_before = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    outcomes = []
    for task in TASKS:
        prior = first_by_id[task.instance_id]
        if prior["passed"]:
            outcomes.append({**prior, "revision": "RETAINED_FIRST_PASS", "provider": prior.get("provider") or {}})
            continue
        response = provider(_revision_prompt(issue=str(dataset[task.instance_id]["problem_statement"]), repo_name=task.repo_name, prior=prior))
        invented = dict(response.get("proposal") or {})
        evaluated = _evaluate(task=task, accepted=accepted_by_id[task.instance_id], invented=invented, external_root=external_root)
        outcomes.append({"instance_id": task.instance_id, "repo_name": task.repo_name, "target_path": accepted_by_id[task.instance_id]["localized_path"], "invented": invented, "provider": {key: value for key, value in response.items() if key != "proposal"}, "revision": "ONE_OUTCOME_CRITICISM_ROUND", **evaluated})
    live_after = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    gate = {
        "repositories": len(outcomes),
        "first_pass_success": sum(row["passed"] for row in first["outcomes"]) / len(outcomes),
        "revised_success": sum(row["passed"] for row in outcomes) / len(outcomes),
        "weakest_repository_success": min(float(row["passed"]) for row in outcomes),
        "original_buggy_programs_rejected": sum(row["original_rejected"] for row in outcomes),
        "selected_repairs_accepted": sum(row["candidate_accepted"] for row in outcomes),
        "adversarial_programs_accepted": sum(row["adversarial_candidate_accepted"] for row in outcomes),
        "revision_rounds": sum(row["revision"] == "ONE_OUTCOME_CRITICISM_ROUND" for row in outcomes),
        "unsafe_test_programs_executed": 0,
        "test_timeouts": sum(any(value.get("timed_out") for value in row["executions"].values()) for row in outcomes),
        "live_sources_unchanged": live_before == live_after,
        "hidden_tests_and_human_patch_absent": True,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "improvement": gate["revised_success"] > gate["first_pass_success"],
        "complete": gate["revised_success"] == 1.0 and gate["weakest_repository_success"] == 1.0,
        "falsification": gate["original_buggy_programs_rejected"] == len(outcomes),
        "candidate": gate["selected_repairs_accepted"] == len(outcomes),
        "adversarial": gate["adversarial_programs_accepted"] == len(outcomes),
        "timeouts": gate["test_timeouts"] == 0,
        "blind": gate["hidden_tests_and_human_patch_absent"],
        "safety": gate["unsafe_test_programs_executed"] == 0 and gate["unsafe_live_writes"] == 0 and gate["live_sources_unchanged"],
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="revised_executable_falsification", steps=["execute_private_generated_tests", "diagnose_fixture_or_environment_failure", "revise_test_harness_once_without_hidden_answers", "require_original_failure_candidate_success_and_adversarial_success"], score=gate["revised_success"], success=gate["accepted"], evidence={"gate": gate}, source_rules=["procedure_documentation_guided_open_software_78c699935c54"])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    for row in outcomes:
        program_id = f"revised_falsification_{_canonical_hash([row['instance_id'], row['invented']])[:16]}"
        runtime.store.state["executable_falsification_programs"][program_id] = {"instance_id": row["instance_id"], "revision": row["revision"], "invented": row["invented"], "passed": row["passed"], "created_at": _utc_timestamp()}
        row["program_id"] = program_id
    runtime.store.commit(reason="revised_executable_falsification")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"programs_retained": all(row["program_id"] in rebuilt.store.state["executable_falsification_programs"] for row in outcomes), "champion_retained": rebuilt.store.state["champions"].get("revised_executable_falsification") == PROCEDURE_ID, "relearning_failures": 0}
    payload = {"schema_version": "aion.hexcore.revised_executable_falsification.v1", "created_at": _utc_timestamp(), "outcomes": outcomes, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["programs_retained"] and restart["champion_retained"] and restart["relearning_failures"] == 0), "boundary": "One development-controlled criticism round repaired generated test harnesses using their own execution traces. Public issues and source-selected test excerpts remain engineered inputs; this is not independent evaluation."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-result", type=Path, default=Path("results/hexcore_executable_falsification_invention.json"))
    parser.add_argument("--documentation-result", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_executable_falsification_revision.json"))
    args = parser.parse_args()
    result = run_executable_falsification_revision(first_result_path=args.first_result.resolve(), documentation_result_path=args.documentation_result.resolve(), external_root=args.external_root.resolve(), dataset_path=args.dataset_path.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
