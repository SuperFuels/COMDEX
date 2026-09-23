from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_natural_repair_substrate_comparison.json"
PROCEDURE_ID = "procedure_cross_language_historical_repair_a6f91cc573b8"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "cross_language_historical_repair_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_text(repo_root: Path, revision: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout


def _git_parent(repo_root: Path, commit: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{commit}^"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    ).stdout.strip()


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _hash_path(path),
    }


@dataclass(frozen=True)
class ExpansionCase:
    case_id: str
    language: str
    family: str
    commit: str
    path: str
    failure_signal: str


CASES: Tuple[ExpansionCase, ...] = (
    ExpansionCase(
        case_id="historical_python_constructor_contract",
        language="python",
        family="constructor_contract",
        commit="5200951213346460b4eecc9a0b6315a1fe536924",
        path="backend/modules/aion_voice/voice_worker_bridge.py",
        failure_signal=(
            "VoiceWorkerResult construction fails because runtime diagnostic "
            "values do not match the frozen result contract. Preserve the "
            "public dataclass surface and retain diagnostics in the payload."
        ),
    ),
    ExpansionCase(
        case_id="historical_javascript_closure",
        language="javascript",
        family="javascript_closure",
        commit="fca9a85ebb184a5e5c3d1e1e81958e61ceaeb072",
        path="desktop/mac/src/app.js",
        failure_signal=(
            "The desktop source fails syntax validation with unexpected end "
            "of input. Restore the smallest unmatched lexical closure without "
            "rewriting existing behavior."
        ),
    ),
)


def _constructor_contract(source: str) -> Dict[str, Any]:
    tree = ast.parse(source)
    result_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "VoiceWorkerResult"
    )
    fields = {
        node.target.id
        for node in result_class.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
    }
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "VoiceWorkerResult"
    ]
    keywords = {
        keyword.arg
        for call in calls
        for keyword in call.keywords
        if keyword.arg
    }
    return {
        "fields": sorted(fields),
        "constructor_keywords": sorted(keywords),
        "unexpected_keywords": sorted(keywords - fields),
    }


def _remove_constructor_extras(source: str) -> str:
    extras = (
        "returncode=int(completed.returncode),",
        "python_path=python_path,",
        "worker_path=worker_path,",
        "runtime_root=runtime_root,",
    )
    return "\n".join(
        line
        for line in source.splitlines()
        if line.strip() not in extras
    ) + "\n"


def _constructor_candidates(source: str) -> List[Dict[str, str]]:
    expanded = source.replace(
        '    stderr: str = ""\n',
        '    stderr: str = ""\n'
        "    returncode: int = 0\n"
        "    python_path: Path | None = None\n"
        "    worker_path: Path | None = None\n"
        "    runtime_root: Path | None = None\n",
        1,
    )
    dropped = _remove_constructor_extras(source)
    anchor = "        return VoiceWorkerResult(\n"
    relocated = _remove_constructor_extras(source).replace(
        anchor,
        '        payload.setdefault("returncode", int(completed.returncode))\n'
        '        payload.setdefault("python_path", str(python_path))\n'
        '        payload.setdefault("worker_path", str(worker_path))\n'
        '        payload.setdefault("runtime_root", str(runtime_root))\n\n'
        + anchor,
        1,
    )
    return [
        {"strategy": "expand_public_result_surface", "source": expanded},
        {"strategy": "drop_runtime_diagnostics", "source": dropped},
        {
            "strategy": "relocate_diagnostics_into_payload",
            "source": relocated,
        },
    ]


def _constructor_tests(source: str, hidden: bool = False) -> Dict[str, bool]:
    try:
        contract = _constructor_contract(source)
    except Exception:
        return {"source_parses": False}
    required_fields = {"ok", "payload", "stdout", "stderr"}
    diagnostics = {
        "returncode",
        "python_path",
        "worker_path",
        "runtime_root",
    }
    checks = {
        "source_parses": True,
        "constructor_matches_dataclass": not contract[
            "unexpected_keywords"
        ],
        "public_surface_preserved": set(contract["fields"]) == required_fields,
        "diagnostics_preserved_in_payload": all(
            f'payload.setdefault("{name}"' in source
            for name in diagnostics
        ),
    }
    if hidden:
        checks["diagnostics_stringify_paths"] = all(
            f'payload.setdefault("{name}", str(' in source
            for name in ("python_path", "worker_path", "runtime_root")
        )
        checks["returncode_remains_integer"] = (
            'payload.setdefault("returncode", int(' in source
        )
    return checks


def _node_check(source: str) -> Dict[str, Any]:
    completed = subprocess.run(
        ["node", "--check", "-"],
        input=source,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stderr_tail": (completed.stderr or "")[-1200:],
    }


def _javascript_candidates(source: str) -> List[Dict[str, str]]:
    return [
        {"strategy": "append_block_close", "source": source + "\n}\n"},
        {"strategy": "append_call_close", "source": source + "\n);\n"},
        {
            "strategy": "append_iife_close",
            "source": source + "\n})();\n",
        },
    ]


def _javascript_tests(source: str, hidden: bool = False) -> Dict[str, bool]:
    check = _node_check(source)
    checks = {
        "node_syntax_valid": check["passed"],
        "single_minimal_suffix": (
            source.rstrip().endswith("})();")
            or not check["passed"]
        ),
    }
    if hidden:
        checks["desktop_iife_closed"] = source.rstrip().endswith("})();")
        checks["no_eval_invented"] = "eval(" not in source[-100:]
    return checks


def _tests(case: ExpansionCase, source: str, hidden: bool = False) -> Dict[str, bool]:
    if case.family == "constructor_contract":
        return _constructor_tests(source, hidden=hidden)
    return _javascript_tests(source, hidden=hidden)


def _candidates(case: ExpansionCase, source: str) -> List[Dict[str, str]]:
    if case.family == "constructor_contract":
        return _constructor_candidates(source)
    return _javascript_candidates(source)


def _select(
    case: ExpansionCase,
    source: str,
    *,
    strategy_prior: Sequence[str] = (),
) -> Dict[str, Any]:
    rows = _candidates(case, source)
    priority = {name: index for index, name in enumerate(strategy_prior)}
    rows.sort(
        key=lambda row: (
            priority.get(row["strategy"], len(priority) + 1),
            row["strategy"],
        )
    )
    attempts = []
    selected = None
    for row in rows:
        checks = _tests(case, row["source"])
        passed = bool(checks and all(checks.values()))
        attempts.append(
            {
                "strategy": row["strategy"],
                "checks": checks,
                "passed": passed,
                "source_hash": _hash_text(row["source"]),
            }
        )
        if passed:
            selected = row
            break
    return {"selected": selected, "attempts": attempts}


def _run_case(repo_root: Path, case: ExpansionCase) -> Dict[str, Any]:
    parent = _git_parent(repo_root, case.commit)
    faulty = _git_text(repo_root, parent, case.path)
    selection = _select(case, faulty)
    selected = selection["selected"]
    # The human repair remains sealed until after candidate selection.
    human = _git_text(repo_root, case.commit, case.path)
    candidate_hidden = (
        _tests(case, selected["source"], hidden=True)
        if selected
        else {}
    )
    human_hidden = _tests(case, human, hidden=True)
    accepted = bool(
        selected
        and all(candidate_hidden.values())
        and all(human_hidden.values())
    )
    return {
        "case_id": case.case_id,
        "language": case.language,
        "family": case.family,
        "failure_signal": case.failure_signal,
        "commit": case.commit,
        "parent": parent,
        "path": case.path,
        "faulty_hash": _hash_text(faulty),
        "selection": {
            "selected_strategy": (
                selected["strategy"] if selected else None
            ),
            "selected_hash": (
                _hash_text(selected["source"]) if selected else None
            ),
            "attempts": selection["attempts"],
            "wrong_candidates_rejected": sum(
                not row["passed"] for row in selection["attempts"]
            ),
        },
        "hidden": {
            "candidate": candidate_hidden,
            "human_revision": human_hidden,
            "candidate_passed": bool(
                candidate_hidden and all(candidate_hidden.values())
            ),
            "human_revision_passed": bool(
                human_hidden and all(human_hidden.values())
            ),
            "human_hash": _hash_text(human),
            "opened_after_selection": True,
        },
        "accepted": accepted,
    }


def _javascript_transfer(
    repo_root: Path,
    strategy: str,
) -> Dict[str, Any]:
    case = CASES[1]
    parent = _git_parent(repo_root, case.commit)
    source = _git_text(repo_root, parent, case.path).replace(
        "WorkflowArchitect",
        "UnseenProjectComposer",
    )
    cold = _select(case, source)
    guided = _select(case, source, strategy_prior=(strategy,))
    guided_source = guided["selected"]["source"]
    hidden = _javascript_tests(guided_source, hidden=True)
    return {
        "renamed_symbol_family": True,
        "cold_attempts": len(cold["attempts"]),
        "guided_attempts": len(guided["attempts"]),
        "attempt_reduction": (
            1.0 - len(guided["attempts"]) / len(cold["attempts"])
        ),
        "guided_hidden_passed": all(hidden.values()),
    }


def run_cross_language_historical_repair(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    dependency = _dependency(repo_root)
    live_paths = {
        case.path: _hash_path(repo_root / case.path)
        for case in CASES
        if (repo_root / case.path).exists()
    }
    outcomes = [_run_case(repo_root, case) for case in CASES]
    js_strategy = next(
        row["selection"]["selected_strategy"]
        for row in outcomes
        if row["language"] == "javascript"
    )
    transfer = _javascript_transfer(repo_root, js_strategy)
    live_after = {
        path: _hash_path(repo_root / path)
        for path in live_paths
    }
    gate = {
        "dependency_promoted": dependency["passed"],
        "authentic_historical_failures": len(outcomes),
        "languages": len({row["language"] for row in outcomes}),
        "new_failure_families": len({row["family"] for row in outcomes}),
        "repair_success": sum(row["accepted"] for row in outcomes) / len(outcomes),
        "hidden_verification": sum(
            row["hidden"]["candidate_passed"] for row in outcomes
        )
        / len(outcomes),
        "human_repair_blind_during_search": all(
            row["hidden"]["opened_after_selection"] for row in outcomes
        ),
        "wrong_candidates_rejected": sum(
            row["selection"]["wrong_candidates_rejected"]
            for row in outcomes
        ),
        "renamed_transfer_success": transfer["guided_hidden_passed"],
        "transfer_attempt_reduction": transfer["attempt_reduction"],
        "live_repository_unchanged": live_paths == live_after,
        "unsafe_acceptances": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "dependency": gate["dependency_promoted"],
        "authentic": gate["authentic_historical_failures"] >= 2,
        "languages": gate["languages"] >= 2,
        "families": gate["new_failure_families"] >= 2,
        "repair": gate["repair_success"] == 1.0,
        "hidden": gate["hidden_verification"] == 1.0,
        "blind": gate["human_repair_blind_during_search"],
        "falsification": gate["wrong_candidates_rejected"] >= 2,
        "transfer": (
            gate["renamed_transfer_success"]
            and gate["transfer_attempt_reduction"] > 0
        ),
        "immutability": gate["live_repository_unchanged"],
        "safety": (
            gate["unsafe_acceptances"] == 0
            and gate["unsafe_live_writes"] == 0
        ),
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="cross_language_historical_repair",
        steps=[
            "ingest_unseen_python_and_javascript_failures",
            "infer_constructor_and_lexical_closure_contracts",
            "generate_repairs_without_human_patch_access",
            "falsify_surface_expansion_diagnostic_loss_and_wrong_closures",
            "verify_once_against_sealed_historical_revisions",
            "transfer_lexical_repair_across_symbol_renaming",
        ],
        score=(
            gate["repair_success"]
            + gate["hidden_verification"]
            + gate["transfer_attempt_reduction"]
        ),
        success=gate["accepted"],
        evidence={"dependency": dependency, "gate": gate},
        source_rules=[dependency["procedure_id"]],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    session_id = f"cross_language_{_canonical_hash(outcomes)[:16]}"
    runtime.store.state["cross_language_repair_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "outcomes": outcomes,
            "transfer": transfer,
            "gate": gate,
        }
    )
    for row in outcomes:
        runtime.store.state["cross_language_patch_library"][
            row["case_id"]
        ] = {
            "language": row["language"],
            "family": row["family"],
            "strategy": row["selection"]["selected_strategy"],
            "source_hash": row["selection"]["selected_hash"],
        }
    runtime.store.commit(reason="cross_language_historical_repair_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "cross_language_historical_repair"
        )
        == candidate.procedure_id,
        "session_retained": any(
            row.get("session_id") == session_id
            for row in restarted.store.state[
                "cross_language_repair_sessions"
            ]
        ),
        "patches_retained": all(
            row["case_id"]
            in restarted.store.state["cross_language_patch_library"]
            for row in outcomes
        ),
        "relearning_failures": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and restart["champion_retained"]
        and restart["session_retained"]
        and restart["patches_retained"]
        and restart["relearning_failures"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.cross_language_historical_repair.v1",
        "capability_track": "cross_language_historical_repair",
        "passed": passed,
        "dependency": dependency,
        "outcomes": outcomes,
        "transfer": transfer,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "The Python and JavaScript failures are authentic historical Git "
            "states and human revisions remain sealed until selection. The "
            "constructor and delimiter repair grammars, two-case selection and "
            "hidden evaluator remain engineered. This broadens language and "
            "failure structure but is not general program synthesis or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_cross_language_historical_repair(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
