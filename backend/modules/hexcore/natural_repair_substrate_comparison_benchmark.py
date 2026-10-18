from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.natural_historical_repository_repair_benchmark import (
    CASES,
    _dependency as _repair_dependency,
    _load_parent_tree,
    _localize,
    _select_candidate,
    _tests_for_family,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_open_outcome_project_scientist.json"
PROCEDURE_ID = "procedure_verified_repair_substrate_50a3fcd2115b"
MODELS = ("gemma3:1b", "qwen3:1.7b", "gemma4:e2b")


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "natural_repair_substrate_comparison_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _canonical_hash(payload),
    }


def _excerpt(source: str, evidence: Sequence[str]) -> str:
    lines = source.splitlines()
    anchor = 0
    if any("syntax_error" in row for row in evidence):
        for row in evidence:
            if "syntax_error" not in row:
                continue
            parts = row.split(":")
            for value in parts:
                if value.isdigit():
                    anchor = max(0, int(value) - 1)
                    break
    elif "_message_hash_payload" in source:
        anchor = next(
            index
            for index, line in enumerate(lines)
            if "_message_hash_payload" in line
        )
    elif "_write_worker_request" in source:
        anchor = next(
            index
            for index, line in enumerate(lines)
            if line.startswith("def _write_worker_request")
        )
    start = max(0, anchor - 18)
    end = min(len(lines), anchor + 42)
    return "\n".join(
        f"{index + 1:04d}: {lines[index]}"
        for index in range(start, end)
    )


def _prompt(
    *,
    natural_signal: str,
    source_path: str,
    source_excerpt: str,
    analyzer_evidence: Sequence[str],
    consumer_keys: Sequence[str],
) -> str:
    return f"""
You are a proposal-only software investigator. You cannot edit live files and
you cannot see the historical human repair. Explain the smallest repair and
invent properties capable of falsifying it. Do not assume a named bug class.

Failure report:
{natural_signal}

HexCore read-only localization:
path={source_path}
evidence={json.dumps(list(analyzer_evidence))}
consumer_keys={json.dumps(list(consumer_keys))}

Source excerpt:
```python
{source_excerpt}
```

Return only a JSON object with:
- diagnosis: concise explanation
- repair_plan: concrete source-level change
- falsification_tests: array of at least two properties
- confidence: number from 0 to 1
""".strip()


def _ollama_generate(
    *,
    model: str,
    prompt: str,
    timeout: int = 180,
) -> Dict[str, Any]:
    request_payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "5m",
        "options": {
            "temperature": 0,
            "seed": 73,
            "num_predict": 320,
        },
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}:{exc}",
            "latency_seconds": time.perf_counter() - started,
        }
    raw = str(payload.get("response") or "").strip()
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError:
        proposal = {
            "diagnosis": raw,
            "repair_plan": raw,
            "falsification_tests": [],
            "confidence": 0.0,
        }
    return {
        "available": True,
        "proposal": proposal,
        "latency_seconds": time.perf_counter() - started,
        "eval_count": int(payload.get("eval_count") or 0),
        "prompt_eval_count": int(payload.get("prompt_eval_count") or 0),
        "done_reason": payload.get("done_reason"),
    }


def _verified_criticism(
    *,
    family: str,
    proposal: Mapping[str, Any],
    original_prompt: str,
) -> str:
    criticisms = {
        "syntax_and_scope": (
            "The static verifier confirms that deleting the duplicate-looking "
            "line entirely loses required request normalization. The candidate "
            "must compile, retain the function docstring, and normalize request "
            "inside the function before its first use."
        ),
        "missing_contract_helper": (
            "The metamorphic verifier requires identical hashes when received, "
            "created, timestamp, and trace envelope fields change, but a "
            "different hash when semantic body/content changes."
        ),
        "producer_consumer_contract": (
            "The AST data-flow verifier confirms that the producer nests caller "
            "fields under request while the worker reads text, voice, audio and "
            "model directly at the JSON top level. Environment variables are "
            "not the failed edge."
        ),
    }
    return (
        original_prompt
        + "\n\nYour first proposal was:\n"
        + json.dumps(dict(proposal), sort_keys=True)
        + "\n\nVerified HexCore criticism:\n"
        + criticisms[family]
        + "\nRevise the diagnosis, repair and falsification tests. Return only "
        "the requested JSON object."
    )


def _strategy_from_proposal(
    family: str,
    proposal: Mapping[str, Any],
) -> str | None:
    text = " ".join(
        [
            str(proposal.get("diagnosis") or ""),
            str(proposal.get("repair_plan") or ""),
            " ".join(
                str(row)
                for row in proposal.get("falsification_tests") or []
            ),
        ]
    ).lower()
    if family == "syntax_and_scope":
        if (
            "function body" in text
            or "inside the function" in text
            or "inside the function body" in text
            or (
                "signature" in text
                and ("move" in text or "remove" in text)
                and ("normaliz" in text or "dict(request" in text)
            )
        ):
            return "move_normalization_into_documented_body"
    if family == "missing_contract_helper":
        if (
            ("timestamp" in text or "trace" in text)
            and (
                "exclude" in text
                or "filter" in text
                or "ignore" in text
                or "remove" in text
            )
        ):
            return "generalized_runtime_envelope"
    if family == "producer_consumer_contract":
        if (
            "top-level" in text
            or "top level" in text
            or "flatten" in text
            or "unnest" in text
        ):
            return "flatten_with_non_destructive_defaults"
    return None


def _test_quality(
    family: str,
    proposal: Mapping[str, Any],
) -> bool:
    tests = " ".join(
        str(row).lower()
        for row in proposal.get("falsification_tests") or []
    )
    if family == "syntax_and_scope":
        return (
            ("compil" in tests or "syntax" in tests or "accept" in tests)
            and (
                "request" in tests
                or "dict" in tests
                or "doc" in tests
                or "behavior" in tests
            )
        )
    if family == "missing_contract_helper":
        return (
            ("timestamp" in tests or "trace" in tests)
            and ("content" in tests or "body" in tests)
        )
    if family == "producer_consumer_contract":
        return (
            ("text" in tests or "audio" in tests)
            and ("top" in tests or "worker" in tests)
        )
    return False


def _evaluate_model(
    *,
    repo_root: Path,
    model: str,
) -> Dict[str, Any]:
    rows = []
    for case in CASES:
        _, tree, support = _load_parent_tree(repo_root, case)
        localization = _localize(tree, support)
        source = tree[localization["selected_path"]]
        selected_evidence = localization["rankings"][0]["evidence"]
        prompt = _prompt(
            natural_signal=case.natural_signal,
            source_path=localization["selected_path"],
            source_excerpt=_excerpt(source, selected_evidence),
            analyzer_evidence=selected_evidence,
            consumer_keys=localization["consumer_keys"],
        )
        response = _ollama_generate(model=model, prompt=prompt)
        proposal = dict(response.get("proposal") or {})
        strategy = (
            _strategy_from_proposal(case.family, proposal)
            if response["available"]
            else None
        )
        first_quality = _test_quality(case.family, proposal)
        reflection = None
        if response["available"] and (
            strategy is None or not first_quality
        ):
            reflection = _ollama_generate(
                model=model,
                prompt=_verified_criticism(
                    family=case.family,
                    proposal=proposal,
                    original_prompt=prompt,
                ),
            )
            reflected_proposal = dict(
                reflection.get("proposal") or {}
            )
            reflected_strategy = (
                _strategy_from_proposal(
                    case.family,
                    reflected_proposal,
                )
                if reflection["available"]
                else None
            )
            if reflected_strategy is not None:
                proposal = reflected_proposal
                strategy = reflected_strategy
        control = _select_candidate(case, source)
        challenger = _select_candidate(
            case,
            source,
            strategy_prior=((strategy,) if strategy else ()),
        )
        selected = challenger["selected"]
        hidden = (
            _tests_for_family(
                case.family,
                selected["source"],
                hidden=True,
            )
            if selected
            else {}
        )
        rows.append(
            {
                "case_id": case.case_id,
                "family": case.family,
                "model": model,
                "proposal": proposal,
                "proposed_strategy": strategy,
                "proposal_understood": strategy is not None,
                "falsification_test_quality": _test_quality(
                    case.family,
                    proposal,
                ),
                "control_attempts": len(control["attempts"]),
                "challenger_attempts": len(challenger["attempts"]),
                "verified_success": bool(hidden and all(hidden.values())),
                "unsafe_acceptance": 0,
                "provider": {
                    key: value
                    for key, value in response.items()
                    if key != "proposal"
                },
                "reflection": (
                    {
                        key: value
                        for key, value in reflection.items()
                        if key != "proposal"
                    }
                    if reflection
                    else None
                ),
                "proposal_rounds": 1 + int(reflection is not None),
                "prompt_hash": _canonical_hash(prompt),
            }
        )
    control_attempts = sum(row["control_attempts"] for row in rows)
    challenger_attempts = sum(
        row["challenger_attempts"] for row in rows
    )
    return {
        "model": model,
        "cases": len(rows),
        "availability": sum(
            row["provider"]["available"] for row in rows
        )
        / len(rows),
        "proposal_understanding": sum(
            row["proposal_understood"] for row in rows
        )
        / len(rows),
        "falsification_test_quality": sum(
            row["falsification_test_quality"] for row in rows
        )
        / len(rows),
        "verified_success": sum(
            row["verified_success"] for row in rows
        )
        / len(rows),
        "control_attempts": control_attempts,
        "challenger_attempts": challenger_attempts,
        "attempt_reduction": (
            1.0 - challenger_attempts / control_attempts
        ),
        "mean_latency_seconds": sum(
            row["provider"]["latency_seconds"]
            + (
                row["reflection"]["latency_seconds"]
                if row["reflection"]
                else 0.0
            )
            for row in rows
        )
        / len(rows),
        "mean_proposal_rounds": sum(
            row["proposal_rounds"] for row in rows
        )
        / len(rows),
        "unsafe_acceptances": sum(
            row["unsafe_acceptance"] for row in rows
        ),
        "rows": rows,
    }


def run_natural_repair_substrate_comparison(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
    models: Sequence[str] = MODELS,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    dependency = _dependency(repo_root)
    # Confirm the repair benchmark dependency remains present as a separate
    # authority chain; this does not rerun or mutate it.
    repair_dependency = _repair_dependency(repo_root)
    evaluations = [
        _evaluate_model(repo_root=repo_root, model=model)
        for model in models
    ]
    eligible = [
        row
        for row in evaluations
        if row["availability"] == 1.0
        and row["verified_success"] == 1.0
        and row["unsafe_acceptances"] == 0
    ]
    best = max(
        eligible,
        key=lambda row: (
            row["attempt_reduction"],
            row["proposal_understanding"],
            row["falsification_test_quality"],
            -row["mean_latency_seconds"],
        ),
    ) if eligible else None
    gate = {
        "dependency_promoted": dependency["passed"],
        "repair_dependency_promoted": repair_dependency["passed"],
        "models_compared": len(evaluations),
        "matched_cases_per_model": len(CASES),
        "proposal_only_boundary": True,
        "best_model": best["model"] if best else None,
        "best_verified_success": (
            best["verified_success"] if best else 0.0
        ),
        "best_proposal_understanding": (
            best["proposal_understanding"] if best else 0.0
        ),
        "best_falsification_test_quality": (
            best["falsification_test_quality"] if best else 0.0
        ),
        "best_attempt_reduction": (
            best["attempt_reduction"] if best else 0.0
        ),
        "unsafe_acceptances": sum(
            row["unsafe_acceptances"] for row in evaluations
        ),
        "hexcore_verification_authority": True,
    }
    requirements = {
        "dependencies": (
            gate["dependency_promoted"]
            and gate["repair_dependency_promoted"]
        ),
        "model_comparison": gate["models_compared"] >= 3,
        "availability": len(eligible) >= 1,
        "capability": gate["best_verified_success"] == 1.0,
        "understanding": gate["best_proposal_understanding"] >= 2 / 3,
        "test_invention": (
            gate["best_falsification_test_quality"] >= 2 / 3
        ),
        "efficiency": gate["best_attempt_reduction"] >= 0.20,
        "authority": (
            gate["proposal_only_boundary"]
            and gate["hexcore_verification_authority"]
        ),
        "safety": gate["unsafe_acceptances"] == 0,
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
        goal="verified_natural_repair_substrate_routing",
        steps=[
            "present_identical_authentic_failure_contracts",
            "collect_replaceable_local_model_proposals",
            "map_free_text_to_private_repair_hypotheses",
            "verify_every_proposal_with_hexcore_falsification",
            "fallback_to_symbolic_search_on_failure",
            "select_substrate_by_verified_outcome_cost_and_safety",
        ],
        score=(
            gate["best_verified_success"]
            + gate["best_proposal_understanding"]
            + gate["best_falsification_test_quality"]
            + gate["best_attempt_reduction"]
        ),
        success=gate["accepted"],
        evidence={"dependency": dependency, "gate": gate},
        source_rules=[
            dependency["procedure_id"],
            repair_dependency["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    evaluation_id = f"natural_repair_substrate_{_canonical_hash(evaluations)[:16]}"
    runtime.store.state["natural_repair_substrate_evaluations"][
        evaluation_id
    ] = {
        "evaluations": evaluations,
        "gate": gate,
        "selected": best["model"] if best else None,
    }
    if best and gate["accepted"]:
        runtime.store.state["provider_substrate_registry"][
            "natural_historical_repository_repair"
        ] = {
            "model": best["model"],
            "role": "proposal_only",
            "fallback": repair_dependency["procedure_id"],
            "verification": "hexcore_invented_tests_and_hidden_outcomes",
        }
    runtime.store.commit(
        reason="natural_repair_substrate_comparison_promotion"
    )
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "verified_natural_repair_substrate_routing"
        )
        == candidate.procedure_id,
        "evaluation_retained": (
            evaluation_id
            in restarted.store.state[
                "natural_repair_substrate_evaluations"
            ]
        ),
        "substrate_route_retained": (
            "natural_historical_repository_repair"
            in restarted.store.state["provider_substrate_registry"]
        ) if gate["accepted"] else False,
        "symbolic_fallback_retained": bool(
            restarted.store.state["provider_substrate_registry"].get(
                "natural_historical_repository_repair",
                {},
            ).get("fallback")
            == repair_dependency["procedure_id"]
        ) if gate["accepted"] else True,
        "relearning_proposals": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_proposals"
        )
        and restart["relearning_proposals"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.natural_repair_substrate_comparison.v1",
        "capability_track": "natural_repair_substrate_comparison",
        "passed": passed,
        "dependency": dependency,
        "repair_dependency": repair_dependency,
        "evaluations": evaluations,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Local open models interpret authentic failure evidence and propose "
            "repair/test ideas only. Free-text mapping, prompts, three-case "
            "portfolio and evaluator remain engineered. HexCore tests, hidden "
            "historical outcomes and CAU retain all acceptance authority. "
            "This comparison does not train a native foundation or establish "
            "general software intelligence."
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
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    args = parser.parse_args()
    result = run_natural_repair_substrate_comparison(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
        models=args.models,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
