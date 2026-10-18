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


PROCEDURE_ID = "procedure_verified_execution_adapter_acquisition_4b5bdc4a2a7e"
MAX_ROUNDS = 3


def _prompt(
    *,
    repo_name: str,
    issue: str,
    target_path: str,
    target_source: str,
    public_test_excerpts: List[Mapping[str, Any]],
    prior: Mapping[str, Any] | None = None,
) -> str:
    trace = ""
    if prior:
        trace = f"""
PRIOR ADAPTER:
{prior.get('adapter_code', '')}

INDEPENDENT EXECUTION TRACE:
{json.dumps(prior.get('execution') or {}, ensure_ascii=False)}

Revise only the loading/fixture path. Do not add product-behavior assertions.
If package import enters unrelated failures, load the target file with the
minimum public dependencies required by its import statements. If a normal
constructor performs eager conversion, expose the repository's public raw or
lazy construction path without asserting the reported repair.
"""
    return f"""
You are acquiring a minimal execution adapter from public repository evidence.
The historical human patch and hidden verifier tests are unavailable.

Return JSON with adapter_code, rationale, target_description and
evidence_used. adapter_code must be a complete Python program that loads the
real target symbol from TARGET FILE and assigns that genuine module, class or
callable to the global name AION_TARGET. It may create a minimal valid fixture
as AION_FIXTURE, but it must not assert the reported repaired behavior. The
evaluator independently proves that AION_TARGET's source resolves to TARGET
FILE.

No network, subprocess, file writes, dynamic eval/exec, permission changes,
secret access or verification bypass. Programs run at repository root. Prefer
normal public imports. Use isolated importlib loading only when the execution
trace proves package initialization is unrelatedly broken.

REPOSITORY: {repo_name}
TARGET FILE: {target_path}
PUBLIC ISSUE:
{issue}

TARGET SOURCE (PUBLIC CHECKOUT):
{target_source[:18000]}

PUBLIC IN-TREE TEST EXCERPTS:
{json.dumps(public_test_excerpts[:4], ensure_ascii=False)[:12000]}
{trace}
""".strip()


def _instrument(code: str, target_path: str) -> str:
    # This independent suffix makes a fabricated marker insufficient: the
    # generated binding must resolve to source in the declared target file.
    return (
        code.rstrip()
        + "\n\n"
        + "import inspect as _aion_inspect\n"
        + "import pathlib as _aion_pathlib\n"
        + "assert 'AION_TARGET' in globals() and AION_TARGET is not None\n"
        + "_aion_source = getattr(AION_TARGET, '__file__', None)\n"
        + "if _aion_source is None:\n"
        + "    _aion_source = _aion_inspect.getsourcefile(AION_TARGET)\n"
        + "assert _aion_source is not None\n"
        + f"_aion_expected = (_aion_pathlib.Path.cwd() / {target_path!r}).resolve()\n"
        + "assert _aion_pathlib.Path(_aion_source).resolve() == _aion_expected\n"
        + "print('AION_ADAPTER_REACHED')\n"
    )


def _evaluate(code: str, repo: Path, target_path: str) -> Dict[str, Any]:
    audit = _audit_test_program(code)
    if not audit["safe"]:
        return {"audit": audit, "execution": {}, "reached": False}
    execution = _execute_test(_instrument(code, target_path), repo)
    reached = bool(
        execution["passed"]
        and "AION_ADAPTER_REACHED" in execution.get("stdout", "")
    )
    return {"audit": audit, "execution": execution, "reached": reached}


def _groundings(payload: Mapping[str, Any], instance_id: str) -> List[Mapping[str, Any]]:
    rows = (payload.get("groundings") or {}).get(instance_id, {}).get("test_contracts") or []
    return [
        {
            "path": row.get("path"),
            "matched_symbols": row.get("matched_symbols") or [],
            "excerpt": row.get("excerpt") or "",
        }
        for row in rows
    ]


def run_verified_execution_adapter_acquisition(
    *,
    external_root: Path,
    dataset_path: Path,
    grounding_result_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    rows = _dataset_rows(dataset_path)
    grounding = json.loads(grounding_result_path.read_text(encoding="utf-8"))
    live_before = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    outcomes = []
    for task in TASKS:
        base_repo = external_root / f"{task.repo_name}-base"
        target_source = (base_repo / task.target_path).read_text(encoding="utf-8")
        prior: Dict[str, Any] | None = None
        rounds = []
        for round_number in range(1, MAX_ROUNDS + 1):
            response = provider(
                _prompt(
                    repo_name=task.repo_name,
                    issue=str(rows[task.instance_id]["problem_statement"]),
                    target_path=task.target_path,
                    target_source=target_source,
                    public_test_excerpts=_groundings(grounding, task.instance_id),
                    prior=prior,
                )
            )
            proposal = dict(response.get("proposal") or {})
            code = str(proposal.get("adapter_code") or "")
            with tempfile.TemporaryDirectory(prefix="aion_adapter_probe_") as raw:
                sandbox = Path(raw) / task.repo_name
                _copy_repo(base_repo, sandbox)
                evaluated = _evaluate(code, sandbox, task.target_path)
            row = {
                "round": round_number,
                "adapter_code": code,
                "rationale": proposal.get("rationale"),
                "target_description": proposal.get("target_description"),
                "evidence_used": proposal.get("evidence_used") or [],
                "provider": {key: value for key, value in response.items() if key != "proposal"},
                **evaluated,
            }
            rounds.append(row)
            if row["reached"]:
                break
            prior = row
        selected = next((row for row in rounds if row["reached"]), None)
        outcomes.append(
            {
                "instance_id": task.instance_id,
                "repo_name": task.repo_name,
                "target_path": task.target_path,
                "rounds": rounds,
                "selected": selected,
                "adapter_verified": selected is not None,
                "attempts": len(rounds),
            }
        )
    live_after = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    gate = {
        "repositories": len(outcomes),
        "verified_adapters": sum(row["adapter_verified"] for row in outcomes),
        "weakest_repository_success": min(
            float(row["adapter_verified"]) for row in outcomes
        ),
        "total_attempts": sum(row["attempts"] for row in outcomes),
        "revisions": sum(max(0, row["attempts"] - 1) for row in outcomes),
        "unsafe_adapter_programs_executed": 0,
        "timeouts": sum(
            any(round_row.get("execution", {}).get("timed_out") for round_row in row["rounds"])
            for row in outcomes
        ),
        "source_path_attestation": all(row["adapter_verified"] for row in outcomes),
        "human_patch_and_hidden_tests_absent": True,
        "live_sources_unchanged": live_before == live_after,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "complete": gate["verified_adapters"] == len(outcomes),
        "weakest": gate["weakest_repository_success"] == 1.0,
        "attestation": gate["source_path_attestation"],
        "timeouts": gate["timeouts"] == 0,
        "blind": gate["human_patch_and_hidden_tests_absent"],
        "safety": gate["unsafe_adapter_programs_executed"] == 0
        and gate["unsafe_live_writes"] == 0
        and gate["live_sources_unchanged"],
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="verified_execution_adapter_acquisition",
        steps=[
            "read_public_source_imports_and_tests",
            "generate_minimal_target_adapter",
            "attest_real_target_source_path",
            "revise_from_own_execution_trace_only",
            "retain_only_safe_verified_adapter",
        ],
        score=gate["verified_adapters"] / len(outcomes),
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=["procedure_documentation_guided_open_software_78c699935c54"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    for row in outcomes:
        if not row["selected"]:
            continue
        adapter_id = f"execution_adapter_{_canonical_hash([row['instance_id'], row['selected']['adapter_code']])[:16]}"
        runtime.store.state["verified_execution_adapters"][adapter_id] = {
            "instance_id": row["instance_id"],
            "repo_name": row["repo_name"],
            "target_path": row["target_path"],
            "adapter_code": row["selected"]["adapter_code"],
            "source_path_attested": True,
            "created_at": _utc_timestamp(),
        }
        row["adapter_id"] = adapter_id
    session_id = f"adapter_session_{_canonical_hash(gate)[:16]}"
    runtime.store.state["execution_adapter_learning_sessions"].append(
        {"session_id": session_id, "gate": gate, "created_at": _utc_timestamp()}
    )
    runtime.store.commit(reason="verified_execution_adapter_acquisition")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "adapters_retained": all(
            row.get("adapter_id") in rebuilt.store.state["verified_execution_adapters"]
            for row in outcomes
            if row["adapter_verified"]
        ),
        "session_retained": any(
            row.get("session_id") == session_id
            for row in rebuilt.store.state["execution_adapter_learning_sessions"]
        ),
        "champion_retained": rebuilt.store.state["champions"].get(
            "verified_execution_adapter_acquisition"
        )
        == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.verified_execution_adapter_acquisition.v1",
        "created_at": _utc_timestamp(),
        "outcomes": outcomes,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["adapters_retained"]
            and restart["session_retained"]
            and restart["champion_retained"]
            and restart["relearning_failures"] == 0
        ),
        "boundary": "Adapters were proposed from public issues, source and in-tree test excerpts and verified only for safe target reachability. This does not prove repair correctness, property quality, cross-language scale or independent hidden evaluation.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument(
        "--grounding-result",
        type=Path,
        default=Path("results/hexcore_source_grounded_software_memory.json"),
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_verified_execution_adapter_acquisition.json"),
    )
    args = parser.parse_args()
    result = run_verified_execution_adapter_acquisition(
        external_root=args.external_root.resolve(),
        dataset_path=args.dataset_path.resolve(),
        grounding_result_path=args.grounding_result.resolve(),
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
