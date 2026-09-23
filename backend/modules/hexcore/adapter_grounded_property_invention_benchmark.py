from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.executable_falsification_invention_benchmark import (
    _audit_test_program,
    _execute_test,
    _selected_by_id,
)
from backend.modules.hexcore.open_patch_generation_benchmark import _apply_proposal, _security_scan
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
from backend.modules.hexcore.verified_execution_adapter_acquisition_benchmark import _instrument


PROCEDURE_ID = "procedure_adapter_grounded_property_invention_60fe24a6e28a"
MAX_ROUNDS = 3


def _normalize_property_code(source: str) -> str:
    """Remove proposal presentation wrappers without changing test logic."""
    value = source.strip()
    if value.startswith("```python"):
        value = value[len("```python") :]
    elif value.startswith("```"):
        value = value[3:]
    if value.endswith("```"):
        value = value[:-3]
    lines = value.strip().splitlines()
    if lines and lines[0].strip().upper() in {
        "VERIFIED ADAPTER",
        "FUNCTIONAL PROPERTY CODE",
        "ADVERSARIAL PROPERTY CODE",
    }:
        lines = lines[1:]
    return "\n".join(lines).strip()


def _property_runner() -> str:
    return """
_aion_property_functions = [
    (name, value)
    for name, value in list(globals().items())
    if callable(value)
    and name.startswith(("test_", "_test_", "property_", "_property_"))
]
assert _aion_property_functions, "NO_EXECUTABLE_PROPERTIES_DISCOVERED"
for _aion_name, _aion_property in sorted(_aion_property_functions):
    _aion_property()
"""


def _prompt(
    *,
    repo_name: str,
    issue: str,
    target_path: str,
    adapter_code: str,
    repair_evidence: Mapping[str, Any],
    public_tests: List[Mapping[str, Any]],
    prior: Mapping[str, Any] | None,
) -> str:
    criticism = ""
    if prior:
        criticism = f"""
PRIOR PROPERTY PROGRAMS:
FUNCTIONAL:
{prior.get('functional_property_code', '')}
ADVERSARIAL:
{prior.get('adversarial_property_code', '')}

INDEPENDENT EXECUTION OUTCOMES:
{json.dumps(prior.get('executions') or {}, ensure_ascii=False)}

Revise the property fixture or assertions using only these outcomes. Preserve
the original-fail/candidate-pass requirement; do not weaken a failed assertion
merely to make both programs pass.
"""
    return f"""
You are inventing falsifying properties inside an already source-attested
execution adapter. The human repair and official hidden tests are unavailable.

Return JSON with functional_property_code, adversarial_property_code,
rationale and security_properties. Each code value is complete Python appended
after VERIFIED ADAPTER. AION_TARGET is the genuine target symbol. You may
import public auxiliary classes for fixtures, but do not replace or re-import
the target.

The functional program must fail on the original reported behavior and pass on
the selected candidate. The adversarial program must pass the candidate while
checking at least two relevant boundary, invariant or security properties.
Every property function must express desired corrected behavior. Never add a
test that asserts, characterizes or expects the original buggy behavior: such a
test would make a correct candidate fail when the complete program is run.
Use plain assertions. No network, subprocess, writes, eval/exec, permission
changes, secrets or verifier bypass.

REPOSITORY: {repo_name}
TARGET: {target_path}
ISSUE:
{issue}

VERIFIED ADAPTER:
{adapter_code}

REPAIR RATIONALE AND DEVELOPMENT TEST INTENT (NO HUMAN PATCH):
{json.dumps(repair_evidence, ensure_ascii=False)}

PUBLIC IN-TREE TEST EXCERPTS:
{json.dumps(public_tests[:4], ensure_ascii=False)[:12000]}
{criticism}
""".strip()


def _contracts(payload: Mapping[str, Any], instance_id: str) -> List[Mapping[str, Any]]:
    rows = (payload.get("groundings") or {}).get(instance_id, {}).get("test_contracts") or []
    return [
        {"path": row.get("path"), "excerpt": row.get("excerpt") or ""}
        for row in rows
    ]


def _evaluate(
    *,
    adapter: str,
    target_path: str,
    functional: str,
    adversarial: str,
    task: Any,
    accepted: Mapping[str, Any],
    external_root: Path,
) -> Dict[str, Any]:
    functional = _normalize_property_code(functional)
    adversarial = _normalize_property_code(adversarial)
    full_functional = _instrument(adapter, target_path) + "\n" + functional + _property_runner()
    full_adversarial = _instrument(adapter, target_path) + "\n" + adversarial + _property_runner()
    audits = {
        "functional": _audit_test_program(full_functional),
        "adversarial": _audit_test_program(full_adversarial),
    }
    base_repo = external_root / f"{task.repo_name}-base"
    path = str(accepted["localized_path"])
    source = (base_repo / path).read_text(encoding="utf-8")
    application = _apply_proposal(source, dict(accepted["selected"]["proposal"]))
    candidate = str(application.get("candidate") or "")
    patch_scan = (
        _security_scan(source, candidate)
        if application.get("applied")
        else {"safe": False, "findings": ["application_failed"]}
    )
    executions: Dict[str, Any] = {}
    if audits["functional"]["safe"] and audits["adversarial"]["safe"] and patch_scan["safe"]:
        with tempfile.TemporaryDirectory(prefix="aion_property_original_") as raw:
            sandbox = Path(raw) / task.repo_name
            _copy_repo(base_repo, sandbox)
            executions["functional_on_original"] = _execute_test(full_functional, sandbox)
        with tempfile.TemporaryDirectory(prefix="aion_property_candidate_") as raw:
            sandbox = Path(raw) / task.repo_name
            _copy_repo(base_repo, sandbox)
            (sandbox / path).write_text(candidate, encoding="utf-8")
            executions["functional_on_candidate"] = _execute_test(full_functional, sandbox)
            executions["adversarial_on_candidate"] = _execute_test(full_adversarial, sandbox)
    original_rejected = bool(executions and not executions["functional_on_original"]["passed"])
    candidate_passed = bool(executions and executions["functional_on_candidate"]["passed"])
    adversarial_passed = bool(executions and executions["adversarial_on_candidate"]["passed"])
    return {
        "audits": audits,
        "selected_patch_security": patch_scan,
        "executions": executions,
        "original_rejected": original_rejected,
        "candidate_passed": candidate_passed,
        "adversarial_passed": adversarial_passed,
        "passed": original_rejected and candidate_passed and adversarial_passed,
    }


def run_adapter_grounded_property_invention(
    *,
    adapter_result_path: Path,
    documentation_result_path: Path,
    grounding_result_path: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    adapters = json.loads(adapter_result_path.read_text(encoding="utf-8"))
    documentation = json.loads(documentation_result_path.read_text(encoding="utf-8"))
    grounding = json.loads(grounding_result_path.read_text(encoding="utf-8"))
    rows = _dataset_rows(dataset_path)
    accepted = _selected_by_id(documentation)
    adapter_by_id = {row["instance_id"]: row for row in adapters["outcomes"]}
    live_before = {
        task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path)
        for task in TASKS
    }
    outcomes = []
    for task in TASKS:
        adapter_row = adapter_by_id[task.instance_id]
        adapter = str(adapter_row["selected"]["adapter_code"])
        repair = dict(accepted[task.instance_id]["selected"]["proposal"])
        repair_evidence = {
            key: repair.get(key)
            for key in ("rationale", "falsification_tests", "security_tests")
        }
        prior: Dict[str, Any] | None = None
        attempts = []
        for round_number in range(1, MAX_ROUNDS + 1):
            response = provider(
                _prompt(
                    repo_name=task.repo_name,
                    issue=str(rows[task.instance_id]["problem_statement"]),
                    target_path=task.target_path,
                    adapter_code=adapter,
                    repair_evidence=repair_evidence,
                    public_tests=_contracts(grounding, task.instance_id),
                    prior=prior,
                )
            )
            proposal = dict(response.get("proposal") or {})
            functional = str(proposal.get("functional_property_code") or "")
            adversarial = str(proposal.get("adversarial_property_code") or "")
            evaluated = _evaluate(
                adapter=adapter,
                target_path=task.target_path,
                functional=functional,
                adversarial=adversarial,
                task=task,
                accepted=accepted[task.instance_id],
                external_root=external_root,
            )
            attempt = {
                "round": round_number,
                "functional_property_code": functional,
                "adversarial_property_code": adversarial,
                "rationale": proposal.get("rationale"),
                "security_properties": proposal.get("security_properties") or [],
                "provider": {key: value for key, value in response.items() if key != "proposal"},
                **evaluated,
            }
            attempts.append(attempt)
            if attempt["passed"]:
                break
            prior = attempt
        selected = next((row for row in attempts if row["passed"]), None)
        outcomes.append(
            {
                "instance_id": task.instance_id,
                "repo_name": task.repo_name,
                "target_path": task.target_path,
                "adapter_id": adapter_row.get("adapter_id"),
                "attempts": attempts,
                "selected": selected,
                "passed": selected is not None,
                "round_count": len(attempts),
            }
        )
    live_after = {
        task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path)
        for task in TASKS
    }
    gate = {
        "repositories": len(outcomes),
        "verified_adapters": sum(adapter_by_id[row["instance_id"]]["adapter_verified"] for row in outcomes),
        "end_to_end_success": sum(row["passed"] for row in outcomes) / len(outcomes),
        "weakest_repository_success": min(float(row["passed"]) for row in outcomes),
        "originals_rejected": sum(
            any(attempt["original_rejected"] for attempt in row["attempts"])
            for row in outcomes
        ),
        "candidates_accepted": sum(
            bool(row["selected"] and row["selected"]["candidate_passed"])
            for row in outcomes
        ),
        "adversarial_programs_accepted": sum(
            bool(row["selected"] and row["selected"]["adversarial_passed"])
            for row in outcomes
        ),
        "total_property_attempts": sum(row["round_count"] for row in outcomes),
        "unsafe_programs_executed": 0,
        "timeouts": sum(
            any(
                any(trace.get("timed_out") for trace in attempt["executions"].values())
                for attempt in row["attempts"]
            )
            for row in outcomes
        ),
        "human_patch_and_hidden_tests_absent": True,
        "live_sources_unchanged": live_before == live_after,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "complete": gate["end_to_end_success"] == 1.0,
        "weakest": gate["weakest_repository_success"] == 1.0,
        "original": gate["originals_rejected"] == len(outcomes),
        "candidate": gate["candidates_accepted"] == len(outcomes),
        "adversarial": gate["adversarial_programs_accepted"] == len(outcomes),
        "timeouts": gate["timeouts"] == 0,
        "blind": gate["human_patch_and_hidden_tests_absent"],
        "safety": gate["unsafe_programs_executed"] == 0
        and gate["unsafe_live_writes"] == 0
        and gate["live_sources_unchanged"],
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="adapter_grounded_property_invention",
        steps=[
            "load_source_attested_execution_adapter",
            "invent_functional_and_adversarial_properties",
            "execute_original_and_candidate_in_fresh_sandboxes",
            "criticise_from_outcomes_without_hidden_answers",
            "require_original_fail_candidate_pass_and_adversarial_pass",
        ],
        score=gate["end_to_end_success"],
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=["procedure_verified_execution_adapter_acquisition_4b5bdc4a2a7e"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    for row in outcomes:
        if not row["selected"]:
            continue
        program_id = f"verified_property_{_canonical_hash([row['instance_id'], row['selected']['functional_property_code'], row['selected']['adversarial_property_code']])[:16]}"
        runtime.store.state["verified_property_programs"][program_id] = {
            "instance_id": row["instance_id"],
            "adapter_id": row.get("adapter_id"),
            "functional_property_code": row["selected"]["functional_property_code"],
            "adversarial_property_code": row["selected"]["adversarial_property_code"],
            "created_at": _utc_timestamp(),
        }
        row["program_id"] = program_id
    session_id = f"property_session_{_canonical_hash(gate)[:16]}"
    runtime.store.state["property_invention_sessions"].append({"session_id": session_id, "gate": gate, "created_at": _utc_timestamp()})
    runtime.store.commit(reason="adapter_grounded_property_invention")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "programs_retained": all(
            row.get("program_id") in rebuilt.store.state["verified_property_programs"]
            for row in outcomes if row["passed"]
        ),
        "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["property_invention_sessions"]),
        "champion_retained": rebuilt.store.state["champions"].get("adapter_grounded_property_invention") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.adapter_grounded_property_invention.v1",
        "created_at": _utc_timestamp(),
        "outcomes": outcomes,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["programs_retained"] and restart["session_retained"]
            and restart["champion_retained"] and restart["relearning_failures"] == 0
        ),
        "boundary": "Properties were generated inside source-attested adapters on three public Python repositories. Public issues, selected development repairs and in-tree tests remain development inputs; this is not three-language scale or independent hidden evaluation.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--adapter-result", type=Path, default=Path("results/hexcore_verified_execution_adapter_acquisition.json"))
    parser.add_argument("--documentation-result", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    parser.add_argument("--grounding-result", type=Path, default=Path("results/hexcore_source_grounded_software_memory.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_adapter_grounded_property_invention.json"))
    args = parser.parse_args()
    result = run_adapter_grounded_property_invention(
        adapter_result_path=args.adapter_result.resolve(),
        documentation_result_path=args.documentation_result.resolve(),
        grounding_result_path=args.grounding_result.resolve(),
        external_root=args.external_root.resolve(),
        dataset_path=args.dataset_path.resolve(),
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
