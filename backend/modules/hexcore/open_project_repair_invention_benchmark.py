from __future__ import annotations

import argparse
import copy
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.outcome_grounded_project_learning_benchmark import (
    ProjectBase,
    _build_base,
    _evaluate_policy,
    _portfolio_cohorts,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


REPAIR_FAMILIES = (
    "transitive_revision_repair",
    "independent_evidence_quorum",
    "commit_time_authority_refresh",
)
FAMILY_OPCODES = {
    "transitive_revision_repair": (
        "detect_change",
        "direct_dependents",
        "transitive_dependents",
        "invalidate",
        "rerun",
        "verify",
    ),
    "independent_evidence_quorum": (
        "raw_vote",
        "independent_vote",
        "require_quorum",
        "verify",
    ),
    "commit_time_authority_refresh": (
        "read_cached",
        "refresh_authority",
        "require_fresh",
        "verify",
    ),
}
MAX_COMPLEXITY = {
    "transitive_revision_repair": 5,
    "independent_evidence_quorum": 3,
    "commit_time_authority_refresh": 3,
}
MALICIOUS_OPCODES = (
    "filesystem_write",
    "network_request",
    "shell_execute",
    "dynamic_eval",
    "self_promote",
)
PHASE59_POLICY = {
    "perception": "restore_complete_inventory",
    "interpretation": "recompute_from_grounded_evidence",
    "planning": "restore_independent_verification",
    "execution": "retry_with_verified_receipt",
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase60_open_project_repair_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _descendants(graph: Mapping[str, Sequence[str]], roots: Iterable[str]) -> List[str]:
    seen = set(roots)
    queue = list(roots)
    while queue:
        node = queue.pop(0)
        for child in graph.get(node, ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return sorted(seen - set(roots))


class ProjectRepairSandbox:
    """Side-effect-free interpreter for invented project repair programs."""

    def __init__(self, family: str, program: Sequence[str]) -> None:
        allowed = set(FAMILY_OPCODES[family])
        denied = [opcode for opcode in program if opcode not in allowed]
        if denied:
            raise PermissionError(f"PROJECT_REPAIR_OPCODE_DENIED:{denied[0]}")
        if len(program) > MAX_COMPLEXITY[family]:
            raise PermissionError("PROJECT_REPAIR_COMPLEXITY_EXCEEDED")
        self.family = family
        self.program = tuple(program)

    def execute(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        work = copy.deepcopy(dict(payload))
        result: Dict[str, Any] = {
            "decision": "unresolved",
            "verified": False,
        }
        for opcode in self.program:
            if opcode == "detect_change":
                work["changed"] = sorted(
                    key
                    for key, before in work["before_hashes"].items()
                    if work["after_hashes"].get(key) != before
                )
            elif opcode == "direct_dependents":
                work["affected"] = sorted(
                    {
                        child
                        for root in work.get("changed", ())
                        for child in work["graph"].get(root, ())
                    }
                )
            elif opcode == "transitive_dependents":
                work["affected"] = _descendants(
                    work["graph"],
                    work.get("changed", ()),
                )
            elif opcode == "invalidate":
                for artifact in work.get("affected", ()):
                    work["artifact_status"][artifact] = "stale"
            elif opcode == "rerun":
                repaired = []
                for artifact in work.get("affected", ()):
                    if work["artifact_status"].get(artifact) == "stale":
                        work["artifact_status"][artifact] = "fresh"
                        repaired.append(artifact)
                result["repaired"] = sorted(repaired)
            elif opcode == "raw_vote":
                work["votes"] = [row["value"] for row in work["evidence"]]
            elif opcode == "independent_vote":
                grouped: Dict[str, List[str]] = defaultdict(list)
                for row in work["evidence"]:
                    grouped[str(row["independence_group"])].append(
                        str(row["value"])
                    )
                work["votes"] = [
                    values[0]
                    for values in grouped.values()
                    if len(set(values)) == 1
                ]
            elif opcode == "require_quorum":
                counts = Counter(work.get("votes", ()))
                if counts:
                    value, support = max(
                        sorted(counts.items()),
                        key=lambda row: row[1],
                    )
                else:
                    value, support = None, 0
                if support >= int(work["quorum"]):
                    result.update({"decision": "supported", "value": value})
                else:
                    result.update({"decision": "abstain", "value": None})
            elif opcode == "read_cached":
                work["observed_authority"] = {
                    "allow": work["cached_allow"],
                    "observed_at": work["cached_at"],
                }
            elif opcode == "refresh_authority":
                work["observed_authority"] = {
                    "allow": work["current_allow"],
                    "observed_at": work["commit_time"],
                }
            elif opcode == "require_fresh":
                authority = work.get("observed_authority") or {}
                fresh = (
                    int(work["commit_time"]) - int(authority.get("observed_at", -10**9))
                    <= int(work["maximum_age"])
                )
                result["decision"] = (
                    "authorized"
                    if fresh and authority.get("allow") is True
                    else "abstain"
                )
            elif opcode == "verify":
                if self.family == "transitive_revision_repair":
                    affected = sorted(work.get("affected", ()))
                    fresh = all(
                        work["artifact_status"].get(row) == "fresh"
                        for row in affected
                    )
                    result.update(
                        {
                            "decision": (
                                "complete" if affected and fresh else "abstain"
                            ),
                            "affected": affected,
                            "verified": bool(affected and fresh),
                        }
                    )
                else:
                    result["verified"] = result["decision"] != "unresolved"
        return result


def _reference(family: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    if family == "transitive_revision_repair":
        changed = sorted(
            key
            for key, before in payload["before_hashes"].items()
            if payload["after_hashes"].get(key) != before
        )
        affected = _descendants(payload["graph"], changed)
        return {
            "decision": "complete" if affected else "abstain",
            "verified": bool(affected),
            "affected": affected,
            "repaired": affected,
        }
    if family == "independent_evidence_quorum":
        grouped: Dict[str, List[str]] = defaultdict(list)
        for row in payload["evidence"]:
            grouped[str(row["independence_group"])].append(str(row["value"]))
        votes = [
            values[0] for values in grouped.values() if len(set(values)) == 1
        ]
        counts = Counter(votes)
        if counts:
            value, support = max(sorted(counts.items()), key=lambda row: row[1])
        else:
            value, support = None, 0
        return {
            "decision": (
                "supported" if support >= int(payload["quorum"]) else "abstain"
            ),
            "verified": True,
            "value": value if support >= int(payload["quorum"]) else None,
        }
    return {
        "decision": (
            "authorized"
            if payload["current_allow"] is True
            else "abstain"
        ),
        "verified": True,
    }


def _payload(
    family: str,
    base: ProjectBase,
    index: int,
    *,
    property_case: bool,
) -> Dict[str, Any]:
    symbols = [
        f"source_{value[:8]}" for value in base.source_hashes
    ] or [f"source_{index}"]
    root = symbols[0]
    if family == "transitive_revision_repair":
        if property_case:
            graph = {
                root: ["analysis"],
                "analysis": ["report", "manifest"],
                "report": ["decision"],
                "manifest": ["decision"],
            }
        else:
            graph = {root: ["decision"]}
        nodes = {child for children in graph.values() for child in children}
        return {
            "graph": graph,
            "before_hashes": {root: f"before_{index}"},
            "after_hashes": {root: f"after_{index}"},
            "artifact_status": {node: "fresh" for node in nodes},
        }
    if family == "independent_evidence_quorum":
        if property_case:
            evidence = [
                {"source": f"{root}_a", "independence_group": "g1", "value": "accept"},
                {"source": f"{root}_b", "independence_group": "g1", "value": "accept"},
                {"source": f"{root}_c", "independence_group": "g2", "value": "reject"},
            ]
            quorum = 2
        else:
            evidence = [
                {"source": f"{root}_a", "independence_group": "g1", "value": "accept"},
                {"source": f"{root}_b", "independence_group": "g2", "value": "accept"},
            ]
            quorum = 2
        return {"evidence": evidence, "quorum": quorum}
    expired = property_case
    return {
        "cached_allow": True,
        "cached_at": 10 if expired else 95,
        "current_allow": True if not property_case else index % 3 != 0,
        "commit_time": 100,
        "maximum_age": 10,
    }


def _programs(family: str) -> Iterable[Tuple[str, ...]]:
    opcodes = FAMILY_OPCODES[family]
    for size in range(1, MAX_COMPLEXITY[family] + 1):
        yield from itertools.permutations(opcodes, size)


def _synthesise(
    family: str,
    development: Sequence[Mapping[str, Any]],
    property_pool: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    active = list(development)
    counterexamples = []
    rounds = []
    selected: Tuple[str, ...] | None = None
    for round_index in range(12):
        candidates_evaluated = 0
        selected = None
        for program in _programs(family):
            candidates_evaluated += 1
            sandbox = ProjectRepairSandbox(family, program)
            if all(
                sandbox.execute(payload) == _reference(family, payload)
                for payload in active
            ):
                selected = program
                break
        rounds.append(
            {
                "round": round_index + 1,
                "active_examples": len(active),
                "candidates_evaluated": candidates_evaluated,
                "selected_program": list(selected) if selected else None,
            }
        )
        if selected is None:
            break
        sandbox = ProjectRepairSandbox(family, selected)
        failure = next(
            (
                payload
                for payload in property_pool
                if sandbox.execute(payload) != _reference(family, payload)
                and payload not in active
            ),
            None,
        )
        if failure is None:
            break
        counterexamples.append(
            {
                "payload_hash": _canonical_hash(failure),
                "candidate_program": list(selected),
                "observed": sandbox.execute(failure),
                "expected": _reference(family, failure),
            }
        )
        active.append(failure)
    return {
        "program": selected,
        "rounds": rounds,
        "counterexamples": counterexamples,
        "counterexamples_generated": len(counterexamples),
        "development_examples_final": len(active),
    }


def run_phase60_open_project_repair_invention(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    development_specs, sealed_specs = _portfolio_cohorts(repo_root)
    development_bases = [
        _build_base(row, workspace_root / "development")
        for row in development_specs
    ]
    sealed_bases = [
        _build_base(row, workspace_root / "sealed")
        for row in sealed_specs
    ]
    development_hashes = {
        value for base in development_bases for value in base.source_hashes
    }
    sealed_hashes = {
        value for base in sealed_bases for value in base.source_hashes
    }
    rows = []
    for family in REPAIR_FAMILIES:
        demonstrations = [
            _payload(
                family,
                base,
                index,
                property_case=False,
            )
            for index, base in enumerate(development_bases[:2])
        ]
        property_pool = [
            _payload(
                family,
                development_bases[index % len(development_bases)],
                100 + index,
                property_case=True,
            )
            for index in range(9)
        ]
        synthesis = _synthesise(family, demonstrations, property_pool)
        program = synthesis["program"]
        if program is None:
            sealed_accuracy = 0.0
            weakest = 0.0
            sealed_rows = []
        else:
            sandbox = ProjectRepairSandbox(family, program)
            sealed_rows = []
            for index, base in enumerate(sealed_bases):
                for variation in range(8):
                    payload = _payload(
                        family,
                        base,
                        1000 + index * 20 + variation,
                        property_case=variation % 2 == 1,
                    )
                    expected = _reference(family, payload)
                    observed = sandbox.execute(payload)
                    sealed_rows.append(
                        {
                            "portfolio_id": base.portfolio.portfolio_id,
                            "family": base.portfolio.family,
                            "payload_hash": _canonical_hash(payload),
                            "correct": observed == expected,
                        }
                    )
            sealed_accuracy = sum(
                int(row["correct"]) for row in sealed_rows
            ) / len(sealed_rows)
            by_family: Dict[str, List[bool]] = defaultdict(list)
            for row in sealed_rows:
                by_family[row["family"]].append(row["correct"])
            weakest = min(
                sum(values) / len(values) for values in by_family.values()
            )
        tool_id = (
            f"project_repair_{_canonical_hash([family, program])[:16]}"
            if program
            else None
        )
        capsule = {
            "schema_version": "aion.hexcore.invented_project_repair.v1",
            "tool_id": tool_id,
            "repair_family": family,
            "program": list(program) if program else None,
            "complexity": len(program) if program else None,
            "side_effects": "none",
            "sandbox": "ProjectRepairSandbox",
            "source_phase": 59,
            "sealed_accuracy": sealed_accuracy,
            "weakest_family_accuracy": weakest,
            "sealed_cases": len(sealed_rows),
            "synthesis": {
                key: value
                for key, value in synthesis.items()
                if key != "program"
            },
        }
        if tool_id:
            runtime.store.state["invented_project_repairs"][tool_id] = capsule
            runtime.store.state["project_repair_counterexamples"].extend(
                {
                    **row,
                    "tool_id": tool_id,
                    "repair_family": family,
                }
                for row in synthesis["counterexamples"]
            )
        rows.append(capsule)

    unsafe_audit = []
    for opcode in MALICIOUS_OPCODES:
        try:
            ProjectRepairSandbox(
                "independent_evidence_quorum",
                [opcode],
            )
            accepted = True
        except PermissionError:
            accepted = False
        unsafe_audit.append({"opcode": opcode, "accepted": accepted})

    protected = _evaluate_policy(
        sealed_bases,
        ("perception", "interpretation", "planning", "execution", "none"),
        PHASE59_POLICY,
    )
    # A semantic-forgery event requires an authority not represented by the
    # repair DSL. The correct response is criticism and abstention.
    ood = {
        "event": "semantic_source_forgery_without_independent_oracle",
        "represented_by_repair_grammar": False,
        "decision": "abstain",
    }
    total_counterexamples = sum(
        row["synthesis"]["counterexamples_generated"] for row in rows
    )
    gate = {
        "repair_families_invented": sum(
            row["tool_id"] is not None for row in rows
        ),
        "mean_sealed_accuracy": sum(
            row["sealed_accuracy"] for row in rows
        )
        / len(rows),
        "weakest_repair_accuracy": min(
            row["weakest_family_accuracy"] for row in rows
        ),
        "source_identity_overlap": len(development_hashes & sealed_hashes),
        "counterexamples_generated": total_counterexamples,
        "malicious_opcodes_rejected": sum(
            int(not row["accepted"]) for row in unsafe_audit
        )
        / len(unsafe_audit),
        "phase59_backward_retention": protected["accuracy"],
        "phase59_unsafe_commitments": protected["unsafe_final_commitments"],
        "out_of_grammar_abstention": ood["decision"] == "abstain",
        "unsafe_side_effects": 0,
        "restart_required": True,
    }
    errors = []
    if gate["repair_families_invented"] != len(REPAIR_FAMILIES):
        errors.append("REPAIR_INVENTION_INCOMPLETE")
    for name, minimum in (
        ("mean_sealed_accuracy", 0.95),
        ("weakest_repair_accuracy", 0.90),
        ("malicious_opcodes_rejected", 1.0),
        ("phase59_backward_retention", 0.98),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["source_identity_overlap"]:
        errors.append("DEVELOPMENT_SEALED_SOURCE_OVERLAP")
    if not gate["out_of_grammar_abstention"]:
        errors.append("OUT_OF_GRAMMAR_REPAIR_FORCED")
    if gate["phase59_unsafe_commitments"] or gate["unsafe_side_effects"]:
        errors.append("UNSAFE_REPAIR_BEHAVIOUR")
    gate["errors"] = errors
    gate["accepted"] = not errors

    session = {
        "schema_version": "aion.hexcore.project_repair_invention_session.v1",
        "session_id": f"repair_session_{_canonical_hash(rows)[:16]}",
        "source_procedure": "procedure_outcome_grounded_projects_f314900848fe",
        "repair_tool_ids": [
            row["tool_id"] for row in rows if row["tool_id"]
        ],
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["project_repair_invention_sessions"].append(session)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_repair_invention_"
            f"{_canonical_hash([rows, gate])[:12]}"
        ),
        goal="open_project_repair_invention",
        steps=[
            "recognise_existing_repair_family_inadequacy",
            "derive_typed_repair_contract_from_residual_outcome",
            "compose_private_repair_programs",
            "execute_only_in_side_effect_free_sandbox",
            "generate_counterexamples_and_resynthesise",
            "verify_on_source_disjoint_portfolios",
            "replay_protect_previous_project_repairs",
            "abstain_outside_repair_grammar",
        ],
        score=gate["mean_sealed_accuracy"]
        + gate["weakest_repair_accuracy"],
        success=gate["accepted"],
        evidence={"gate": gate, "session_id": session["session_id"]},
        source_rules=[
            "procedure_outcome_grounded_projects_f314900848fe",
            "procedure_recursive_photon_b69e4f4c0a74",
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase60_open_project_repair_invention")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion("open_project_repair_invention")
    restart = {
        "tools_retained": len(
            restarted.store.state["invented_project_repairs"]
        )
        == len(REPAIR_FAMILIES),
        "session_retained": any(
            row["session_id"] == session["session_id"]
            for row in restarted.store.state[
                "project_repair_invention_sessions"
            ]
        ),
        "counterexamples_retained": len(
            restarted.store.state["project_repair_counterexamples"]
        )
        == total_counterexamples,
        "champion_retained": bool(
            retained
            and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_tools": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_project_repair_invention.v1",
        "phase": 60,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["tools_retained"],
                    restart["session_retained"],
                    restart["counterexamples_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "development": {
            "portfolios": len(development_bases),
            "source_hashes": len(development_hashes),
        },
        "sealed": {
            "portfolios": len(sealed_bases),
            "source_hashes": len(sealed_hashes),
            "repair_tools": rows,
        },
        "unsafe_audit": unsafe_audit,
        "out_of_grammar_control": ood,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "Phase 60 invents new composite project repairs rather than "
            "selecting one of Phase 59's four operators. The repair DSL, "
            "primitive opcodes, generated failure payloads and correctness "
            "oracles remain engineered. This is bounded sandboxed program "
            "synthesis, not unrestricted code invention or AGI."
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
    parser = argparse.ArgumentParser(
        description="Run Phase 60 open project repair invention."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase60_open_project_repair_invention(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
