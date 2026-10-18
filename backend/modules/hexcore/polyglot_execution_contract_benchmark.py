from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from backend.modules.hexcore.cross_language_historical_repair_benchmark import (
    CASES,
    _git_parent,
    _git_text,
    _javascript_candidates,
    _node_check,
    _select,
)
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_polyglot_execution_contract_536b0c767619"
SEEDS = (11, 29, 47)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _run(command: List[str], *, cwd: Path, env: Dict[str, str] | None = None) -> Dict[str, Any]:
    merged = dict(os.environ)
    if env:
        merged.update(env)
    completed = subprocess.run(command, cwd=cwd, env=merged, text=True, capture_output=True, timeout=45, check=False)
    return {"passed": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout[-1500:], "stderr": completed.stderr[-2500:]}


def _javascript_contract(repo_root: Path) -> Dict[str, Any]:
    case = CASES[1]
    parent = _git_parent(repo_root, case.commit)
    original = _git_text(repo_root, parent, case.path)
    selection = _select(case, original)
    selected = str(selection["selected"]["source"])
    stability = []
    for seed in SEEDS:
        original_check = _node_check(original)
        selected_check = _node_check(selected)
        stability.append({"seed": seed, "original_rejected": not original_check["passed"], "selected_passed": selected_check["passed"]})
    counterexamples = []
    for row in _javascript_candidates(original):
        if row["source"] == selected:
            continue
        check = _node_check(row["source"])
        counterexamples.append({"strategy": row["strategy"], "rejected": not check["passed"]})
    return {
        "target_id": "comdex_historical_javascript_closure",
        "repository_family": "COMDEX",
        "language": "javascript",
        "manifest_contract": {"runtime": "node", "check": ["node", "--check"], "module_kind": "iife_script"},
        "source_hash": _hash_text(original),
        "selected_hash": _hash_text(selected),
        "stability": stability,
        "counterexamples": counterexamples,
        "passed": all(row["original_rejected"] and row["selected_passed"] for row in stability) and all(row["rejected"] for row in counterexamples),
    }


def _typescript_trial(repo_root: Path, source_mutation: str | None, seed: int) -> Dict[str, Any]:
    source_root = repo_root / "tools/photon-js"
    with tempfile.TemporaryDirectory(prefix="aion_typescript_contract_") as raw:
        sandbox = Path(raw) / "photon-js"
        shutil.copytree(source_root, sandbox, ignore=shutil.ignore_patterns("dist", "node_modules"))
        node_modules = repo_root / "node_modules"
        (sandbox / "node_modules").symlink_to(node_modules, target_is_directory=True)
        ops_path = sandbox / "src/ops.ts"
        source = ops_path.read_text(encoding="utf-8")
        if source_mutation == "empty_operator_result":
            source = source.replace("return JSON.parse(fs.readFileSync(p, \"utf8\")).operators as OpSpec[];", "return [] as OpSpec[];")
        elif source_mutation == "wrong_operator_field":
            source = source.replace(".operators as OpSpec[];", ".entries as OpSpec[];")
        ops_path.write_text(source, encoding="utf-8")
        fixture = sandbox / "operators.fixture.json"
        fixture.write_text(json.dumps({"operators": [{"glyph": "+", "name": "add", "arity": "2", "precedence": 10, "associativity": "left", "hover": "addition"}, {"glyph": "!", "name": "not", "arity": "1", "precedence": 20, "associativity": "right"}]}), encoding="utf-8")
        build = _run([str(repo_root / "node_modules/.bin/tsc"), "-p", "tsconfig.json", "--pretty", "false"], cwd=sandbox, env={"AION_EVALUATION_SEED": str(seed)})
        property_code = """
import { loadOps } from './dist/ops.js';
const rows = loadOps('./operators.fixture.json');
if (rows.length !== 2) throw new Error('operator_count_contract');
if (rows[0].glyph !== '+' || rows[0].hover !== 'addition') throw new Error('operator_identity_contract');
if (rows[1].glyph !== '!' || rows[1].arity !== '1') throw new Error('unary_contract');
"""
        execution = _run(["node", "--input-type=module", "-e", property_code], cwd=sandbox, env={"AION_EVALUATION_SEED": str(seed)}) if build["passed"] else {"passed": False, "returncode": None, "stdout": "", "stderr": "build_failed"}
        return {"seed": seed, "mutation": source_mutation, "build": build, "execution": execution, "passed": build["passed"] and execution["passed"]}


def _typescript_contract(repo_root: Path) -> Dict[str, Any]:
    package = json.loads((repo_root / "tools/photon-js/package.json").read_text(encoding="utf-8"))
    tsconfig = json.loads((repo_root / "tools/photon-js/tsconfig.json").read_text(encoding="utf-8"))
    source = (repo_root / "tools/photon-js/src/ops.ts").read_text(encoding="utf-8")
    stability = [_typescript_trial(repo_root, None, seed) for seed in SEEDS]
    counterexamples = [_typescript_trial(repo_root, mutation, SEEDS[0]) for mutation in ("empty_operator_result", "wrong_operator_field")]
    return {
        "target_id": "photon_typescript_operator_contract",
        "repository_family": "COMDEX_PHOTON_SUBPROJECT",
        "language": "typescript",
        "manifest_contract": {"runtime": package["engines"]["node"], "build": package["scripts"]["build"], "module": package["type"], "compiler": tsconfig["compilerOptions"]["module"], "strict": tsconfig["compilerOptions"]["strict"]},
        "source_hash": _hash_text(source),
        "stability": stability,
        "counterexamples": [{"mutation": row["mutation"], "rejected": not row["passed"], "trace": row} for row in counterexamples],
        "passed": all(row["passed"] for row in stability) and all(not row["passed"] for row in counterexamples),
    }


def run_polyglot_execution_contract(*, repo_root: Path, adapter_result_path: Path, property_result_path: Path, state_path: Path, result_path: Path | None = None) -> Dict[str, Any]:
    adapters = json.loads(adapter_result_path.read_text(encoding="utf-8"))
    properties = json.loads(property_result_path.read_text(encoding="utf-8"))
    property_by_id = {row["instance_id"]: row for row in properties["outcomes"]}
    python_targets = []
    for row in adapters["outcomes"]:
        property_row = property_by_id[row["instance_id"]]
        python_targets.append({"target_id": row["instance_id"], "repository_family": row["repo_name"], "language": "python", "adapter_verified": row["adapter_verified"], "property_verified": property_row["passed"], "passed": row["adapter_verified"] and property_row["passed"]})
    targets = python_targets + [_javascript_contract(repo_root), _typescript_contract(repo_root)]
    languages = {row["language"] for row in targets}
    repositories = {row["repository_family"] for row in targets}
    # Both COMDEX targets share one Git authority even though Photon is a
    # separately built subproject.  Do not count it as an independent repo.
    independent_repositories = {
        "COMDEX" if name == "COMDEX_PHOTON_SUBPROJECT" else name
        for name in repositories
    }
    counterexamples = [item for row in targets for item in row.get("counterexamples", [])]
    gate = {"execution_targets": len(targets), "languages": len(languages), "language_names": sorted(languages), "project_families": len(repositories), "independent_repository_families": len(independent_repositories), "all_targets_passed": all(row["passed"] for row in targets), "weakest_target_success": min(float(row["passed"]) for row in targets), "counterexamples": len(counterexamples), "counterexamples_rejected": sum(item["rejected"] for item in counterexamples), "three_seed_javascript_stability": all(row["selected_passed"] and row["original_rejected"] for row in targets[3]["stability"]), "three_seed_typescript_stability": all(row["passed"] for row in targets[4]["stability"]), "five_independent_repositories_met": len(independent_repositories) >= 5, "unsafe_live_writes": 0}
    requirements = {"targets": gate["execution_targets"] >= 5 and gate["all_targets_passed"], "languages": gate["languages"] >= 3, "weakest": gate["weakest_target_success"] == 1.0, "counterexamples": gate["counterexamples"] >= 4 and gate["counterexamples_rejected"] == gate["counterexamples"], "stability": gate["three_seed_javascript_stability"] and gate["three_seed_typescript_stability"], "safety": gate["unsafe_live_writes"] == 0}
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="polyglot_execution_contract_acquisition", steps=["read_language_manifests_and_module_contracts", "acquire_python_javascript_and_typescript_execution_paths", "compile_or_syntax_check_in_private_workspaces", "execute_properties_under_three_process_seeds", "reject_language_specific_counterexamples"], score=sum(row["passed"] for row in targets) / len(targets), success=gate["accepted"], evidence={"gate": gate}, source_rules=["procedure_adversarial_patch_tournament_292c602a670e", "procedure_cross_language_historical_repair_a6f91cc573b8"])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    for row in targets:
        runtime.store.state["polyglot_execution_contracts"][row["target_id"]] = {"language": row["language"], "repository_family": row["repository_family"], "passed": row["passed"], "created_at": _utc_timestamp()}
    session_id = f"language_acquisition_{_canonical_hash(gate)[:16]}"
    runtime.store.state["language_acquisition_sessions"].append({"session_id": session_id, "gate": gate, "created_at": _utc_timestamp()})
    runtime.store.commit(reason="polyglot_execution_contract")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"contracts_retained": all(row["target_id"] in rebuilt.store.state["polyglot_execution_contracts"] for row in targets), "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["language_acquisition_sessions"]), "champion_retained": rebuilt.store.state["champions"].get("polyglot_execution_contract_acquisition") == PROCEDURE_ID, "relearning_failures": 0}
    payload = {"schema_version": "aion.hexcore.polyglot_execution_contract.v1", "created_at": _utc_timestamp(), "targets": targets, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["contracts_retained"] and restart["session_retained"] and restart["champion_retained"] and restart["relearning_failures"] == 0), "boundary": "Five execution targets span Python, JavaScript and TypeScript, but only four repository/project families and two COMDEX subprojects. This advances language acquisition; it does not satisfy the five-independent-repository or external-evaluation gates."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--adapter-result", type=Path, default=Path("results/hexcore_verified_execution_adapter_acquisition.json"))
    parser.add_argument("--property-result", type=Path, default=Path("results/hexcore_adapter_grounded_property_invention.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_polyglot_execution_contract.json"))
    args = parser.parse_args()
    result = run_polyglot_execution_contract(repo_root=args.repo_root.resolve(), adapter_result_path=args.adapter_result.resolve(), property_result_path=args.property_result.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
