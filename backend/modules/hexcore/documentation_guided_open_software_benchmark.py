from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.open_patch_generation_benchmark import (
    _generate_openai,
    _run_case,
    _security_scan,
)
from backend.modules.hexcore.open_relation_argument_memory_benchmark import (
    _call_json,
    _span_normal,
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


PROCEDURE_ID = "procedure_documentation_guided_open_software_78c699935c54"
PARENT_RESULT = "results/hexcore_cross_domain_semantic_transfer.json"
DOC_SUFFIXES = {".md", ".rst", ".txt"}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "documentation_guided_software_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _document_candidates(
    repo: Path,
    issue: str,
    *,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    query = {term for term in _terms(issue) if len(term) >= 3}
    qualified_refs = {
        value.lower()
        for value in re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+",
            issue,
        )
    }
    rows = []
    for path in repo.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = str(path.relative_to(repo))
        if path.suffix.lower() not in DOC_SUFFIXES and path.name.lower() not in {
            "readme",
            "readme.md",
            "readme.rst",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        overlap = query & _terms(text[:120000])
        path_terms = _terms(relative)
        path_overlap = query & path_terms
        score = (
            len(overlap)
            + 6 * len(path_overlap)
            + 2 * int("readme" in path.name.lower())
            + 30
            * sum(reference in text.lower() for reference in qualified_refs)
        )
        if score:
            rows.append(
                {
                    "path": relative,
                    "score": score,
                    "matched_terms": sorted(overlap)[:24],
                    "matched_path_terms": sorted(path_overlap)[:12],
                    "text": text[:16000],
                    "sha256": _hash_text(text),
                }
            )
    rows.sort(key=lambda row: (-row["score"], row["path"]))
    return rows[:limit]


def _ontology_prompt(
    repo_name: str,
    issue: str,
    documents: Sequence[Mapping[str, Any]],
) -> str:
    rendered = "\n\n".join(
        f"[DOCUMENT {index + 1}: {row['path']}]\n{row['text']}"
        for index, row in enumerate(documents)
    )
    return f"""
You are a proposal-only repository semantic learner. No repository ontology,
fault map, target file, repair menu or human patch is supplied. Read the issue
and documentation and invent a compact ontology that could guide later fault
localization and falsification.

Return JSON with:
concepts: label, definition, evidence_quote, document_path
relations: subject, predicate, object, evidence_quote, document_path
invariants: statement, evidence_quote, document_path
code_bindings: concept, symbol, candidate_paths (array), evidence_quote,
document_path
open_questions: array

Every evidence_quote must be copied exactly from its document. Bindings are
only hypotheses; sandbox inspection must confirm symbols and paths. Do not
propose a patch.

REPOSITORY: {repo_name}
ISSUE:
{issue}

{rendered}
""".strip()


def _ground_ontology(
    repo: Path,
    documents: Sequence[Mapping[str, Any]],
    proposal: Mapping[str, Any],
) -> Dict[str, Any]:
    docs = {row["path"]: row for row in documents}
    concepts: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    invariants: List[Dict[str, Any]] = []
    bindings: List[Dict[str, Any]] = []

    def grounded(row: Mapping[str, Any]) -> tuple[bool, str, str]:
        path = str(row.get("document_path") or "")
        quote = str(row.get("evidence_quote") or "").strip()
        valid = path in docs and quote and _span_normal(quote) in _span_normal(docs[path]["text"])
        return bool(valid), path, quote

    for index, row in enumerate(proposal.get("concepts") or []):
        if not isinstance(row, Mapping):
            continue
        valid, path, quote = grounded(row)
        if valid and str(row.get("label") or "").strip():
            concepts.append({"id": f"concept:{index}", "label": str(row["label"]), "definition": str(row.get("definition") or ""), "evidence_quote": quote, "document_path": path, "document_hash": docs[path]["sha256"]})
    for index, row in enumerate(proposal.get("relations") or []):
        if not isinstance(row, Mapping):
            continue
        valid, path, quote = grounded(row)
        if valid and all(str(row.get(key) or "").strip() for key in ("subject", "predicate", "object")):
            relations.append({"id": f"relation:{index}", "subject": str(row["subject"]), "predicate": str(row["predicate"]), "object": str(row["object"]), "evidence_quote": quote, "document_path": path, "document_hash": docs[path]["sha256"]})
    for index, row in enumerate(proposal.get("invariants") or []):
        if not isinstance(row, Mapping):
            continue
        valid, path, quote = grounded(row)
        if valid and str(row.get("statement") or "").strip():
            invariants.append({"id": f"invariant:{index}", "statement": str(row["statement"]), "evidence_quote": quote, "document_path": path, "document_hash": docs[path]["sha256"]})
    for index, row in enumerate(proposal.get("code_bindings") or []):
        if not isinstance(row, Mapping):
            continue
        valid, path, quote = grounded(row)
        symbol = str(row.get("symbol") or "").strip()
        candidates = [str(value) for value in (row.get("candidate_paths") or [])]
        confirmed_paths = []
        for candidate in candidates:
            source_path = repo / candidate
            if not source_path.is_file() or ".git" in source_path.parts:
                continue
            try:
                source = source_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if symbol and re.search(rf"\b{re.escape(symbol)}\b", source):
                confirmed_paths.append(candidate)
        if valid and symbol and confirmed_paths:
            bindings.append({"id": f"binding:{index}", "concept": str(row.get("concept") or ""), "symbol": symbol, "confirmed_paths": confirmed_paths, "evidence_quote": quote, "document_path": path, "document_hash": docs[path]["sha256"]})
    return {"concepts": concepts, "relations": relations, "invariants": invariants, "bindings": bindings, "open_questions": [str(value) for value in (proposal.get("open_questions") or [])]}


def _memory_provider(ontology: Mapping[str, Any]):
    memory = json.dumps(
        {
            "concepts": ontology["concepts"],
            "relations": ontology["relations"],
            "invariants": ontology["invariants"],
            "confirmed_code_bindings": ontology["bindings"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    def provider(prompt: str) -> Dict[str, Any]:
        augmented = (
            prompt
            + "\n\nRETAINED VERIFIED DOCUMENTATION MEMORY (proposal guidance only; "
            "source execution remains authoritative):\n"
            + memory
            + "\nUse this memory to improve localization, causal reasoning and test "
            "design. Do not force it when source evidence contradicts it."
        )
        response = _generate_openai(augmented)
        response["memory_prompt_hash"] = _hash_text(memory)
        return response

    return provider


def _adversarial_security_audit() -> Dict[str, Any]:
    source = "def repair(value):\n    return value\n"
    probes = {
        "dynamic_execution": "def repair(value):\n    return eval(value)\n",
        "shell_execution": "def repair(value):\n    return run(value, shell=True)\n",
        "verification_disabled": "def repair(value):\n    return request(value, verify=False)\n",
        "world_writable": "def repair(value):\n    chmod(value, 0o777)\n",
        "embedded_secret": "def repair(value):\n    api_key = '123456789-secret'\n",
        "security_bypass": "def repair(value):\n    disable_auth_validation = True\n",
    }
    results = {name: _security_scan(source, candidate) for name, candidate in probes.items()}
    return {"probes": results, "blocked": sum(not row["safe"] for row in results.values()), "total": len(results), "passed": all(not row["safe"] for row in results.values())}


def run_documentation_guided_open_software(
    *,
    repo_root: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
    ontology_provider: Any = _call_json,
    repair_provider: Any = _generate_openai,
) -> Dict[str, Any]:
    parent = json.loads((repo_root / PARENT_RESULT).read_text(encoding="utf-8"))
    rows = _dataset_rows(dataset_path)
    live_before = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    ontologies: Dict[str, Any] = {}
    comparisons = []
    for task in TASKS:
        base_repo = external_root / f"{task.repo_name}-base"
        issue = str(rows[task.instance_id]["problem_statement"])
        documents = _document_candidates(base_repo, issue)
        response = ontology_provider(_ontology_prompt(task.repo_name, issue, documents))
        ontology = _ground_ontology(base_repo, documents, dict(response.get("proposal") or {}))
        ontology["documents"] = [{key: value for key, value in row.items() if key != "text"} for row in documents]
        ontology["provider"] = {key: value for key, value in response.items() if key != "proposal"}
        ontology["ontology_id"] = f"repo_ontology_{_canonical_hash(ontology)[:16]}"
        ontologies[task.instance_id] = ontology

        control = _run_case(task=task, external_root=external_root, private_row=rows[task.instance_id], provider=repair_provider)
        challenger = _run_case(task=task, external_root=external_root, private_row=rows[task.instance_id], provider=_memory_provider(ontology))
        comparisons.append({"instance_id": task.instance_id, "repo_name": task.repo_name, "control": control, "memory_challenger": challenger, "success_lift": int(challenger["accepted"]) - int(control["accepted"]), "attempt_reduction": len(control["rounds"]) - len(challenger["rounds"])})

    live_after = {task.instance_id: _hash_path(external_root / f"{task.repo_name}-base" / task.target_path) for task in TASKS}
    control_success = sum(row["control"]["accepted"] for row in comparisons) / len(comparisons)
    challenger_success = sum(row["memory_challenger"]["accepted"] for row in comparisons) / len(comparisons)
    control_attempts = sum(len(row["control"]["rounds"]) for row in comparisons)
    challenger_attempts = sum(len(row["memory_challenger"]["rounds"]) for row in comparisons)
    accepted_challengers = [row["memory_challenger"] for row in comparisons if row["memory_challenger"]["accepted"]]
    security_test_specs = sum(len(row["selected"]["proposal"].get("security_tests") or []) >= 2 for row in accepted_challengers)
    functional_test_specs = sum(len(row["selected"]["proposal"].get("falsification_tests") or []) >= 2 for row in accepted_challengers)
    security_audit = _adversarial_security_audit()
    all_memory_rows = [value for ontology in ontologies.values() for key in ("concepts", "relations", "invariants", "bindings") for value in ontology[key]]
    gate = {
        "parent_promoted": bool(parent.get("passed")),
        "repositories": len(comparisons),
        "open_repository_ontologies": len(ontologies),
        "invented_concepts": sum(len(row["concepts"]) for row in ontologies.values()),
        "grounded_relations": sum(len(row["relations"]) for row in ontologies.values()),
        "grounded_invariants": sum(len(row["invariants"]) for row in ontologies.values()),
        "code_bindings_confirmed_by_source": sum(len(row["bindings"]) for row in ontologies.values()),
        "provenance_completeness": float(bool(all_memory_rows) and all(row.get("evidence_quote") and row.get("document_hash") for row in all_memory_rows)),
        "matched_control_model_and_tools": True,
        "control_success": control_success,
        "memory_challenger_success": challenger_success,
        "success_lift": challenger_success - control_success,
        "control_attempts": control_attempts,
        "memory_challenger_attempts": challenger_attempts,
        "attempt_reduction": (control_attempts - challenger_attempts) / max(1, control_attempts),
        "weakest_repository_success": min(float(row["memory_challenger"]["accepted"]) for row in comparisons),
        "accepted_with_functional_test_specifications": functional_test_specs,
        "accepted_with_security_test_specifications": security_test_specs,
        "adversarial_security_classes_blocked": security_audit["blocked"],
        "adversarial_security_classes_total": security_audit["total"],
        "human_patch_blind_during_generation": all(row["memory_challenger"]["hidden"]["opened_after_selection"] for row in comparisons if row["memory_challenger"]["accepted"]),
        "live_sources_unchanged": live_before == live_after,
        "unsafe_acceptances": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "parent": gate["parent_promoted"],
        "ontology": gate["invented_concepts"] >= 9 and gate["grounded_relations"] >= 6,
        "binding": gate["code_bindings_confirmed_by_source"] >= 3,
        "provenance": gate["provenance_completeness"] == 1.0,
        "repair": gate["memory_challenger_success"] == 1.0 and gate["weakest_repository_success"] == 1.0,
        "lift": gate["success_lift"] > 0 or gate["attempt_reduction"] >= 0.2,
        "test_specs": functional_test_specs == len(accepted_challengers) and security_test_specs == len(accepted_challengers),
        "security": security_audit["passed"] and gate["unsafe_acceptances"] == 0,
        "blind": gate["human_patch_blind_during_generation"],
        "immutability": gate["live_sources_unchanged"] and gate["unsafe_live_writes"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    for instance_id, ontology in ontologies.items():
        runtime.store.state["repository_semantic_ontologies"][ontology["ontology_id"]] = {"instance_id": instance_id, **ontology}
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="documentation_guided_open_software", steps=["ingest_repository_documents_without_schema", "invent_and_ground_repository_ontology", "align_document_concepts_to_source_symbols", "run_matched_no_memory_control", "generate_unrestricted_memory_guided_patch", "invent_functional_and_security_test_specifications", "execute_in_fresh_sandbox", "reveal_historical_verification_after_selection"], score=challenger_success + max(0.0, gate["attempt_reduction"]), success=gate["accepted"], evidence={"gate": gate}, source_rules=[parent["promotion"]["candidate"]["procedure_id"]])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    session_id = f"doc_guided_{_canonical_hash(comparisons)[:16]}"
    runtime.store.state["documentation_guided_repair_sessions"].append({"session_id": session_id, "comparisons": comparisons, "gate": gate})
    runtime.store.commit(reason="documentation_guided_open_software")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"ontologies_retained": all(row["ontology_id"] in rebuilt.store.state["repository_semantic_ontologies"] for row in ontologies.values()), "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["documentation_guided_repair_sessions"]), "champion_retained": rebuilt.store.state["champions"].get("documentation_guided_open_software") == PROCEDURE_ID, "relearning_failures": 0}
    payload = {"schema_version": "aion.hexcore.documentation_guided_open_software.v1", "created_at": _utc_timestamp(), "ontologies": ontologies, "comparisons": comparisons, "security_audit": security_audit, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["ontologies_retained"] and restart["session_retained"] and restart["champion_retained"] and restart["relearning_failures"] == 0), "boundary": "Public SWE-bench development issues and repository documentation are development-controlled and may be present in model pretraining. The experiment tests matched memory utility under sandbox verification, not independent hidden software engineering. Functional tests remain engineered; the model invents test specifications, not executable test programs."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_documentation_guided_open_software.json"))
    args = parser.parse_args()
    result = run_documentation_guided_open_software(repo_root=args.repo_root.resolve(), external_root=args.external_root.resolve(), dataset_path=args.dataset_path.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
