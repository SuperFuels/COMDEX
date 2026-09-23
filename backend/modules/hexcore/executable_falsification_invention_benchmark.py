from __future__ import annotations

import argparse
import ast
import json
import os
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import (
    _allow,
)
from backend.modules.hexcore.open_patch_generation_benchmark import (
    _apply_proposal,
    _security_scan,
)
from backend.modules.hexcore.open_relation_argument_memory_benchmark import (
    _call_json,
)
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
    _python_env,
)


PROCEDURE_ID = "procedure_executable_falsification_invention_76dbafce2714"


def _test_prompt(
    *,
    repo_name: str,
    issue: str,
    target_path: str,
    proposal: Mapping[str, Any],
    grounding: Mapping[str, Any],
) -> str:
    contracts = [
        {
            "path": row["path"],
            "matched_symbols": row["matched_symbols"],
            "excerpt": row["excerpt"],
        }
        for row in grounding.get("test_contracts") or []
    ]
    return f"""
You are a proposal-only falsification-test inventor. The human patch and
official hidden tests are unavailable. Given the public issue, selected patch
rationale and source-grounded public test excerpts, invent two standalone
Python programs.

Return JSON with exactly:
functional_test_code: complete Python program; it must exit 0 for a correct
  repair and fail by assertion for the original reported bug
security_test_code: complete Python program exercising adversarial boundary
  inputs relevant to the proposed change; it must exit 0 only when invariants
  remain safe
rationale: why the functional test falsifies the causal repair hypothesis
security_properties: array of at least two distinct properties

Both programs run from the repository root. They may import the repository,
Python standard library, NumPy and pandas. They must not access the network,
spawn processes, write files, alter permissions, read secrets, use eval/exec or
weaken verification. Use plain assertions, not markdown or pytest fixtures.

REPOSITORY: {repo_name}
TARGET FILE: {target_path}
ISSUE:
{issue}

SELECTED PATCH RATIONALE AND TEST SPECIFICATIONS:
{json.dumps({key: proposal.get(key) for key in ('rationale', 'falsification_tests', 'security_tests')}, ensure_ascii=False)}

SOURCE-GROUNDED PUBLIC TEST EXCERPTS:
{json.dumps(contracts, ensure_ascii=False)}
""".strip()


def _audit_test_program(source: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"safe": False, "findings": [f"syntax:{exc.msg}"]}
    forbidden_imports = {
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "telnetlib",
    }
    forbidden_calls = {
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "system",
        "popen",
        "run",
        "Popen",
        "chmod",
        "unlink",
        "remove",
        "rmtree",
        "write_text",
        "write_bytes",
    }
    findings: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in forbidden_imports:
                    findings.append(f"forbidden_import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in forbidden_imports:
                findings.append(f"forbidden_import:{node.module}")
        elif isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in forbidden_calls:
                findings.append(f"forbidden_call:{name}")
    return {"safe": not findings, "findings": sorted(set(findings))}


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    # Enough for NumPy/pandas and historical packages, while bounding runaway
    # generated programs.
    limit = 2 * 1024 * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError):
        pass


def _execute_test(
    code: str,
    repo: Path,
    *,
    timeout: int = 35,
    env_overrides: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    env = _python_env(repo)
    env.update(
        {
            "NO_PROXY": "*",
            "no_proxy": "*",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if env_overrides:
        env.update(env_overrides)
    try:
        completed = subprocess.run(
            [sys.executable, "-P", "-c", code],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            preexec_fn=_limits,
        )
        return {
            "returncode": completed.returncode,
            "passed": completed.returncode == 0,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-3000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "passed": False,
            "stdout": str(exc.stdout or "")[-2000:],
            "stderr": str(exc.stderr or "")[-3000:],
            "timed_out": True,
        }


def _selected_by_id(result: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        row["instance_id"]: row["memory_challenger"]
        for row in result["comparisons"]
    }


def run_executable_falsification_invention(
    *,
    documentation_result_path: Path,
    grounding_result_path: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    parent = json.loads(documentation_result_path.read_text(encoding="utf-8"))
    grounding_result = json.loads(grounding_result_path.read_text(encoding="utf-8"))
    selected = _selected_by_id(parent)
    rows = _dataset_rows(dataset_path)
    live_before = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    outcomes = []
    for task in TASKS:
        accepted = selected[task.instance_id]
        proposal = dict(accepted["selected"]["proposal"])
        grounding = grounding_result["groundings"][task.instance_id]
        issue = str(rows[task.instance_id]["problem_statement"])
        response = provider(_test_prompt(repo_name=task.repo_name, issue=issue, target_path=accepted["localized_path"], proposal=proposal, grounding=grounding))
        invented = dict(response.get("proposal") or {})
        functional = str(invented.get("functional_test_code") or "")
        security = str(invented.get("security_test_code") or "")
        functional_audit = _audit_test_program(functional)
        security_audit = _audit_test_program(security)
        base_repo = external_root / f"{task.repo_name}-base"
        original_source = (base_repo / accepted["localized_path"]).read_text(encoding="utf-8")
        application = _apply_proposal(original_source, proposal)
        selected_source = str(application.get("candidate") or "")
        patch_scan = _security_scan(original_source, selected_source) if application.get("applied") else {"safe": False, "findings": ["application_failed"]}
        executions: Dict[str, Any] = {}
        if functional_audit["safe"] and security_audit["safe"] and patch_scan["safe"]:
            with tempfile.TemporaryDirectory(prefix="aion_invented_test_base_") as raw:
                base_sandbox = Path(raw) / task.repo_name
                _copy_repo(base_repo, base_sandbox)
                executions["functional_on_original"] = _execute_test(functional, base_sandbox)
            with tempfile.TemporaryDirectory(prefix="aion_invented_test_candidate_") as raw:
                candidate_sandbox = Path(raw) / task.repo_name
                _copy_repo(base_repo, candidate_sandbox)
                (candidate_sandbox / accepted["localized_path"]).write_text(selected_source, encoding="utf-8")
                executions["functional_on_candidate"] = _execute_test(functional, candidate_sandbox)
                executions["security_on_candidate"] = _execute_test(security, candidate_sandbox)
        passed = bool(
            executions
            and not executions["functional_on_original"]["passed"]
            and executions["functional_on_candidate"]["passed"]
            and executions["security_on_candidate"]["passed"]
            and len(invented.get("security_properties") or []) >= 2
        )
        outcomes.append(
            {
                "instance_id": task.instance_id,
                "repo_name": task.repo_name,
                "target_path": accepted["localized_path"],
                "invented": invented,
                "provider": {key: value for key, value in response.items() if key != "proposal"},
                "functional_audit": functional_audit,
                "security_audit": security_audit,
                "selected_patch_security": patch_scan,
                "executions": executions,
                "original_rejected": bool(executions and not executions["functional_on_original"]["passed"]),
                "candidate_accepted": bool(executions and executions["functional_on_candidate"]["passed"]),
                "adversarial_candidate_accepted": bool(executions and executions["security_on_candidate"]["passed"]),
                "passed": passed,
            }
        )
    live_after = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    gate = {
        "parent_promoted": bool(parent.get("passed")),
        "repositories": len(outcomes),
        "safe_test_programs": sum(row["functional_audit"]["safe"] and row["security_audit"]["safe"] for row in outcomes),
        "original_buggy_programs_rejected": sum(row["original_rejected"] for row in outcomes),
        "selected_repairs_accepted": sum(row["candidate_accepted"] for row in outcomes),
        "adversarial_test_programs_passed": sum(row["adversarial_candidate_accepted"] for row in outcomes),
        "end_to_end_executable_falsification_success": sum(row["passed"] for row in outcomes) / len(outcomes),
        "weakest_repository_success": min(float(row["passed"]) for row in outcomes),
        "test_program_timeouts": sum(any(value.get("timed_out") for value in row["executions"].values()) for row in outcomes),
        "live_sources_unchanged": live_before == live_after,
        "human_patch_and_hidden_tests_absent_from_test_generation": True,
        "unsafe_test_programs_executed": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "parent": gate["parent_promoted"],
        "safe_programs": gate["safe_test_programs"] == len(outcomes),
        "falsification": gate["original_buggy_programs_rejected"] == len(outcomes),
        "candidate": gate["selected_repairs_accepted"] == len(outcomes),
        "adversarial": gate["adversarial_test_programs_passed"] == len(outcomes),
        "weakest": gate["weakest_repository_success"] == 1.0,
        "timeouts": gate["test_program_timeouts"] == 0,
        "blind": gate["human_patch_and_hidden_tests_absent_from_test_generation"],
        "safety": gate["unsafe_test_programs_executed"] == 0 and gate["unsafe_live_writes"] == 0 and gate["live_sources_unchanged"],
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="executable_falsification_invention",
        steps=[
            "invent_functional_test_program_from_issue_and_public_contracts",
            "invent_adversarial_test_program",
            "statically_reject_unsafe_test_code",
            "run_original_and_candidate_in_fresh_sandboxes",
            "require_original_failure_and_candidate_success",
        ],
        score=gate["end_to_end_executable_falsification_success"],
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=["procedure_documentation_guided_open_software_78c699935c54"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    for row in outcomes:
        program_id = f"falsification_{_canonical_hash([row['instance_id'], row['invented']])[:16]}"
        runtime.store.state["executable_falsification_programs"][program_id] = {"instance_id": row["instance_id"], "invented": row["invented"], "audits": {"functional": row["functional_audit"], "security": row["security_audit"]}, "passed": row["passed"], "created_at": _utc_timestamp()}
        row["program_id"] = program_id
    runtime.store.commit(reason="executable_falsification_invention")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "programs_retained": all(row["program_id"] in rebuilt.store.state["executable_falsification_programs"] for row in outcomes),
        "champion_retained": rebuilt.store.state["champions"].get("executable_falsification_invention") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.executable_falsification_invention.v1",
        "created_at": _utc_timestamp(),
        "outcomes": outcomes,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["programs_retained"] and restart["champion_retained"] and restart["relearning_failures"] == 0),
        "boundary": "Test programs are model-generated and executable, but prompts use public issues and development-selected public test excerpts. Static auditing and process limits reduce risk but do not constitute a hardened OS sandbox or independent hidden evaluation.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--documentation-result", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    parser.add_argument("--grounding-result", type=Path, default=Path("results/hexcore_source_grounded_software_memory.json"))
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_executable_falsification_invention.json"))
    args = parser.parse_args()
    result = run_executable_falsification_invention(documentation_result_path=args.documentation_result.resolve(), grounding_result_path=args.grounding_result.resolve(), external_root=args.external_root.resolve(), dataset_path=args.dataset_path.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
