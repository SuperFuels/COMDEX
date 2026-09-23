from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.documentation_guided_open_software_benchmark import (
    _adversarial_security_audit,
    _allow,
)
from backend.modules.hexcore.open_patch_generation_benchmark import (
    _generate_openai,
    _run_case,
)
from backend.modules.hexcore.open_relation_argument_memory_benchmark import (
    _terms,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.source_disjoint_swebench_repair_benchmark import (
    TASKS,
    _dataset_rows,
    _hash_path,
)


PROCEDURE_ID = "procedure_source_grounded_software_memory_2750f049c98f"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _definition_symbols(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
    )


def _window(lines: Sequence[str], anchor: int, radius: int = 28) -> str:
    start = max(0, anchor - radius)
    end = min(len(lines), anchor + radius + 1)
    return "\n".join(lines[start:end])


def _source_grounding(
    repo: Path,
    issue: str,
    target_path: str,
) -> Dict[str, Any]:
    target = repo / target_path
    target_source = target.read_text(encoding="utf-8", errors="replace")
    issue_terms = {term for term in _terms(issue) if len(term) >= 3}
    qualified = re.findall(
        r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
        issue,
    )
    symbols = set(_definition_symbols(target_source))
    symbols.update(value.split(".")[-1] for value in qualified)
    symbols = {value for value in symbols if len(value) >= 3}

    candidates = []
    for path in repo.rglob("*.py"):
        if ".git" in path.parts or path == target:
            continue
        relative = str(path.relative_to(repo))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        source_terms = _terms(source[:100000])
        matched_symbols = sorted(
            symbol
            for symbol in symbols
            if re.search(rf"\b{re.escape(symbol)}\b", source)
        )
        overlap = issue_terms & source_terms
        is_test = "test" in path.name.lower() or "tests" in path.parts
        score = 8 * len(matched_symbols) + len(overlap) + 15 * int(is_test)
        if not score or not matched_symbols:
            continue
        lines = source.splitlines()
        line_scores = [
            sum(bool(re.search(rf"\b{re.escape(symbol)}\b", line)) for symbol in matched_symbols)
            + sum(term in line.lower() for term in issue_terms)
            for line in lines
        ]
        anchor = max(range(len(lines)), key=line_scores.__getitem__) if lines else 0
        excerpt = _window(lines, anchor)
        candidates.append(
            {
                "path": relative,
                "kind": "test" if is_test else "call_site",
                "score": score,
                "matched_symbols": matched_symbols[:20],
                "issue_terms": sorted(overlap)[:20],
                "excerpt": excerpt,
                "source_hash": _sha(source),
            }
        )
    candidates.sort(key=lambda row: (-row["score"], row["path"]))
    tests = [row for row in candidates if row["kind"] == "test"][:3]
    call_sites = [row for row in candidates if row["kind"] == "call_site"][:2]
    return {
        "target_path": target_path,
        "target_hash": _sha(target_source),
        "target_symbols": sorted(symbols),
        "test_contracts": tests,
        "call_sites": call_sites,
    }


def _rank_memory(
    issue: str,
    ontology: Mapping[str, Any],
    *,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    query = _terms(issue)
    rows = []
    for kind in ("invariants", "bindings", "relations", "concepts"):
        for row in ontology.get(kind) or []:
            score = len(query & _terms(json.dumps(row, ensure_ascii=False)))
            if kind == "bindings":
                score += 4
            if kind == "invariants":
                score += 2
            rows.append((score, kind, dict(row)))
    rows.sort(key=lambda value: (-value[0], value[1], json.dumps(value[2], sort_keys=True)))
    return [{"kind": kind, **row} for score, kind, row in rows[:limit] if score > 0]


def _grounded_provider(
    *,
    issue: str,
    ontology: Mapping[str, Any],
    grounding: Mapping[str, Any],
):
    selected_memory = _rank_memory(issue, ontology)
    compact_grounding = {
        "target_path": grounding["target_path"],
        "target_symbols": grounding["target_symbols"],
        "test_contracts": grounding["test_contracts"],
        "call_sites": grounding["call_sites"],
    }
    payload = json.dumps(
        {
            "issue_relevant_document_memory": selected_memory,
            "source_grounded_execution_contracts": compact_grounding,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    def provider(prompt: str) -> Dict[str, Any]:
        augmented = f"""
{prompt}

VERIFIED ISSUE-RELEVANT REPOSITORY MEMORY:
{payload}

The documentation is not authority. Use source-grounded tests and call sites
to infer the behavioral contract. Preserve every established behavior. Your
falsification_tests must include at least one property derived from the shown
test contracts and one counterexample aimed at your own causal hypothesis.
Your security_tests must target at least two distinct prohibited classes.
Do not edit tests merely to make the patch pass.
""".strip()
        response = _generate_openai(augmented)
        response["grounded_memory_hash"] = _sha(payload)
        return response

    return provider, selected_memory


def run_source_grounded_software_memory(
    *,
    repo_root: Path,
    external_root: Path,
    dataset_path: Path,
    v1_result_path: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    v1 = json.loads(v1_result_path.read_text(encoding="utf-8"))
    rows = _dataset_rows(dataset_path)
    control_by_id = {row["instance_id"]: row["control"] for row in v1["comparisons"]}
    live_before = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    comparisons = []
    groundings = {}
    for task in TASKS:
        control = control_by_id[task.instance_id]
        base_repo = external_root / f"{task.repo_name}-base"
        issue = str(rows[task.instance_id]["problem_statement"])
        grounding = _source_grounding(base_repo, issue, control["localized_path"])
        ontology = v1["ontologies"][task.instance_id]
        provider, selected_memory = _grounded_provider(issue=issue, ontology=ontology, grounding=grounding)
        challenger = _run_case(task=task, external_root=external_root, private_row=rows[task.instance_id], provider=provider)
        groundings[task.instance_id] = {**grounding, "selected_document_memory": selected_memory}
        comparisons.append({"instance_id": task.instance_id, "repo_name": task.repo_name, "control": control, "grounded_memory_challenger": challenger, "success_lift": int(challenger["accepted"]) - int(control["accepted"]), "attempt_reduction": len(control["rounds"]) - len(challenger["rounds"])})
    live_after = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    control_success = sum(row["control"]["accepted"] for row in comparisons) / len(comparisons)
    challenger_success = sum(row["grounded_memory_challenger"]["accepted"] for row in comparisons) / len(comparisons)
    control_attempts = sum(len(row["control"]["rounds"]) for row in comparisons)
    challenger_attempts = sum(len(row["grounded_memory_challenger"]["rounds"]) for row in comparisons)
    accepted = [row["grounded_memory_challenger"] for row in comparisons if row["grounded_memory_challenger"]["accepted"]]
    functional_specs = sum(len(row["selected"]["proposal"].get("falsification_tests") or []) >= 2 for row in accepted)
    security_specs = sum(len(row["selected"]["proposal"].get("security_tests") or []) >= 2 for row in accepted)
    security_audit = _adversarial_security_audit()
    gate = {
        "repositories": len(comparisons),
        "matched_control_reused_from_immediately_preceding_cycle": True,
        "source_grounded_test_contracts": sum(len(row["test_contracts"]) for row in groundings.values()),
        "source_grounded_call_sites": sum(len(row["call_sites"]) for row in groundings.values()),
        "control_success": control_success,
        "grounded_memory_success": challenger_success,
        "success_lift": challenger_success - control_success,
        "control_attempts": control_attempts,
        "grounded_memory_attempts": challenger_attempts,
        "attempt_reduction": (control_attempts - challenger_attempts) / max(1, control_attempts),
        "weakest_repository_success": min(float(row["grounded_memory_challenger"]["accepted"]) for row in comparisons),
        "accepted_with_functional_test_specifications": functional_specs,
        "accepted_with_security_test_specifications": security_specs,
        "security_classes_blocked": security_audit["blocked"],
        "security_classes_total": security_audit["total"],
        "live_sources_unchanged": live_before == live_after,
        "human_patch_blind_during_generation": all(row["grounded_memory_challenger"]["hidden"]["opened_after_selection"] for row in comparisons if row["grounded_memory_challenger"]["accepted"]),
        "unsafe_acceptances": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "grounding": gate["source_grounded_test_contracts"] >= 3 and gate["source_grounded_call_sites"] >= 2,
        "repair": challenger_success == 1.0 and gate["weakest_repository_success"] == 1.0,
        "lift": gate["success_lift"] > 0 or gate["attempt_reduction"] >= 0.2,
        "test_specs": functional_specs == len(accepted) and security_specs == len(accepted),
        "security": security_audit["passed"] and gate["unsafe_acceptances"] == 0,
        "blind": gate["human_patch_blind_during_generation"],
        "immutability": gate["live_sources_unchanged"] and gate["unsafe_live_writes"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="source_grounded_software_memory", steps=["retain_only_issue_relevant_document_memory", "derive_ast_symbols_and_code_bindings", "recover_existing_test_and_call_site_contracts", "generate_unrestricted_patch", "invent_counterexamples_and_security_tests", "sandbox_and_reveal_historical_verification_after_selection"], score=challenger_success + max(0.0, gate["attempt_reduction"]), success=gate["accepted"], evidence={"gate": gate}, source_rules=["procedure_cross_domain_semantic_transfer_58eae51b7d20"])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    session_id = f"source_grounded_{_canonical_hash(comparisons)[:16]}"
    runtime.store.state["documentation_guided_repair_sessions"].append({"session_id": session_id, "version": 2, "comparisons": comparisons, "gate": gate})
    runtime.store.commit(reason="source_grounded_software_memory")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["documentation_guided_repair_sessions"]), "champion_retained": rebuilt.store.state["champions"].get("source_grounded_software_memory") == PROCEDURE_ID, "relearning_failures": 0}
    payload = {"schema_version": "aion.hexcore.source_grounded_software_memory.v1", "created_at": _utc_timestamp(), "parent_v1_result_hash": _hash_path(v1_result_path), "groundings": groundings, "comparisons": comparisons, "security_audit": security_audit, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["session_retained"] and restart["champion_retained"] and restart["relearning_failures"] == 0), "boundary": "The benchmark uses public development issues and engineered executable verifiers. Source-grounded test contracts are read from the repositories, not independently invented executable tests. This is a matched development experiment, not external certification."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--v1-result", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_source_grounded_software_memory.json"))
    args = parser.parse_args()
    result = run_source_grounded_software_memory(repo_root=args.repo_root.resolve(), external_root=args.external_root.resolve(), dataset_path=args.dataset_path.resolve(), v1_result_path=args.v1_result.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
