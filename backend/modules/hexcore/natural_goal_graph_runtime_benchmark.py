from __future__ import annotations

import argparse
import json
import os
import random
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.aion.goal_engine.contracts import GoalNodeContract
from backend.modules.aion.goal_engine.memory_model import MemoryRecordContract
from backend.modules.aion_conversation.contracts import TurnPacket
from backend.modules.hexcore.governed_runtime import (
    AppendOnlyOutcomeLedger,
    HexCoreGovernedRuntime,
)
from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Edge = Tuple[str, str]


DOMAIN_STEPS = {
    "archive": (
        "align_seal",
        "obtain_credential",
        "unlock_archive",
        "deliver_record",
    ),
    "laboratory": (
        "calibrate_sensor",
        "collect_sample",
        "analyse_sample",
        "publish_result",
    ),
    "mission": (
        "charge_cell",
        "map_route",
        "launch_probe",
        "transmit_reading",
    ),
    "supply": (
        "verify_vendor",
        "allocate_budget",
        "place_order",
        "receive_goods",
    ),
}

TOPOLOGIES: Tuple[Tuple[Tuple[int, int], ...], ...] = (
    ((0, 1), (1, 2), (2, 3)),
    ((0, 2), (1, 2), (2, 3)),
    ((0, 1), (0, 2), (1, 3), (2, 3)),
    ((1, 0), (0, 2), (2, 3)),
)

CLAUSE_TEMPLATES = (
    "{after} requires {before}.",
    "Complete {before} before {after}.",
    "Only after {before} may {after} begin.",
    "{after} is blocked until {before} is complete.",
)


@dataclass(frozen=True)
class NaturalProject:
    project_id: str
    domain: str
    steps: Tuple[str, ...]
    edges: Tuple[Edge, ...]
    brief: str
    revision_brief: str | None
    revised_edges: Tuple[Edge, ...] | None


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase37_goal_graph_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _render_brief(
    *,
    domain: str,
    steps: Sequence[str],
    edges: Sequence[Edge],
    rng: random.Random,
) -> str:
    clauses = []
    for index, (before, after) in enumerate(edges):
        template = CLAUSE_TEMPLATES[
            (index + rng.randrange(len(CLAUSE_TEMPLATES)))
            % len(CLAUSE_TEMPLATES)
        ]
        clauses.append(
            template.format(
                before=before.replace("_", " "),
                after=after.replace("_", " "),
            )
        )
    rng.shuffle(clauses)
    return (
        f"You are entering an unfamiliar {domain} project. "
        + " ".join(clauses)
        + f" The final objective is {steps[-1].replace('_', ' ')}."
    )


def _make_projects(count: int, *, seed: int, cohort: str) -> List[NaturalProject]:
    rng = random.Random(seed)
    rows = []
    domains = tuple(DOMAIN_STEPS)
    for index in range(count):
        domain = domains[index % len(domains)]
        steps = DOMAIN_STEPS[domain]
        topology = TOPOLOGIES[(index // len(domains)) % len(TOPOLOGIES)]
        edges = tuple((steps[left], steps[right]) for left, right in topology)
        revised_edges = None
        revision_brief = None
        if index % 5 == 0:
            alternate = TOPOLOGIES[
                ((index // len(domains)) + 1) % len(TOPOLOGIES)
            ]
            revised_edges = tuple(
                (steps[left], steps[right]) for left, right in alternate
            )
            revision_brief = _render_brief(
                domain=domain,
                steps=steps,
                edges=revised_edges,
                rng=rng,
            )
        rows.append(
            NaturalProject(
                project_id=f"{cohort}:{domain}:{index:03d}",
                domain=domain,
                steps=steps,
                edges=edges,
                brief=_render_brief(
                    domain=domain,
                    steps=steps,
                    edges=edges,
                    rng=rng,
                ),
                revision_brief=revision_brief,
                revised_edges=revised_edges,
            )
        )
    return rows


def _native_edges(brief: str, steps: Sequence[str]) -> List[Edge]:
    normalized = " " + re.sub(r"[^a-z0-9]+", " ", brief.lower()) + " "
    positions = {
        step: step.replace("_", " ")
        for step in steps
    }
    edges = set()
    for before, before_text in positions.items():
        for after, after_text in positions.items():
            if before == after:
                continue
            patterns = (
                rf"{re.escape(after_text)} requires {re.escape(before_text)}",
                rf"{re.escape(before_text)} before {re.escape(after_text)}",
                rf"only after {re.escape(before_text)} may {re.escape(after_text)} begin",
                rf"{re.escape(after_text)} is blocked until {re.escape(before_text)} is complete",
            )
            if any(re.search(pattern, normalized) for pattern in patterns):
                edges.add((before, after))
    return sorted(edges)


def _topological_plan(steps: Sequence[str], edges: Sequence[Edge]) -> List[str]:
    incoming = {step: 0 for step in steps}
    children = {step: [] for step in steps}
    for before, after in edges:
        if before not in incoming or after not in incoming:
            return []
        incoming[after] += 1
        children[before].append(after)
    ready = sorted(step for step, count in incoming.items() if count == 0)
    order = []
    while ready:
        step = ready.pop(0)
        order.append(step)
        for child in sorted(children[step]):
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
                ready.sort()
    return order if len(order) == len(steps) else []


def _execute_plan(
    plan: Sequence[str],
    steps: Sequence[str],
    edges: Sequence[Edge],
) -> Dict[str, Any]:
    complete = set()
    trace = []
    for step in plan:
        unmet = sorted(
            before
            for before, after in edges
            if after == step and before not in complete
        )
        accepted = step in steps and not unmet
        trace.append({"step": step, "accepted": accepted, "unmet": unmet})
        if not accepted:
            return {"success": False, "trace": trace}
        complete.add(step)
    return {
        "success": complete == set(steps),
        "trace": trace,
    }


def _load_local_env(path: Path) -> Dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _provider_prompt(project: NaturalProject, brief: str) -> str:
    return (
        "Return strict JSON only with key edges, a list of [before, after] "
        "dependency pairs. Use only these exact step identifiers: "
        + json.dumps(list(project.steps))
        + ". Extract only dependencies explicitly supported by the brief. "
        "Do not invent edges. Brief: "
        + brief
    )


def _parse_provider_edges(raw: str, steps: Sequence[str]) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed.get("edges"), list):
            raw_edges = parsed.get("edges") or []
        else:
            # Some local models return a valid adjacency map despite the
            # requested edge-list schema. Normalize it without trusting it.
            raw_edges = []
            for before, afters in parsed.items():
                if before == "edges" or not isinstance(afters, list):
                    continue
                raw_edges.extend([[before, after] for after in afters])
    except Exception as exc:
        return {"ok": False, "edges": [], "reason": f"invalid_json:{type(exc).__name__}"}
    allowed = set(steps)
    edges = []
    for row in raw_edges:
        if (
            isinstance(row, list)
            and len(row) == 2
            and row[0] in allowed
            and row[1] in allowed
            and row[0] != row[1]
        ):
            edges.append((row[0], row[1]))
    return {"ok": True, "edges": sorted(set(edges)), "reason": "parsed"}


def _call_gemma(project: NaturalProject, brief: str) -> Dict[str, Any]:
    payload = {
        "model": os.getenv("AION_PHASE37_GEMMA_MODEL", "gemma4:e2b"),
        "stream": False,
        "format": "json",
        "prompt": _provider_prompt(project, brief),
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        parsed = _parse_provider_edges(str(body.get("response") or ""), project.steps)
        return {"provider": "local_gemma", "live": True, **parsed}
    except Exception as exc:
        return {
            "provider": "local_gemma",
            "live": True,
            "ok": False,
            "edges": [],
            "reason": f"provider_failed:{type(exc).__name__}",
        }


def _extract_openai_text(body: Mapping[str, Any]) -> str:
    if isinstance(body.get("output_text"), str):
        return str(body["output_text"])
    chunks = []
    for item in body.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
            elif isinstance(content.get("json"), dict):
                chunks.append(json.dumps(content["json"]))
    return "\n".join(chunks)


def _call_openai(
    project: NaturalProject,
    brief: str,
    *,
    api_key: str,
) -> Dict[str, Any]:
    payload = {
        "model": os.getenv("AION_PHASE37_OPENAI_MODEL", "gpt-5.1"),
        "input": _provider_prompt(project, brief),
        "text": {"format": {"type": "json_object"}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        parsed = _parse_provider_edges(_extract_openai_text(body), project.steps)
        return {"provider": "openai", "live": True, **parsed}
    except urllib.error.HTTPError as exc:
        return {
            "provider": "openai",
            "live": True,
            "ok": False,
            "edges": [],
            "reason": f"provider_http_error:{exc.code}",
        }
    except Exception as exc:
        return {
            "provider": "openai",
            "live": True,
            "ok": False,
            "edges": [],
            "reason": f"provider_failed:{type(exc).__name__}",
        }


def _pattern_overlap(brief: str, edges: Sequence[Edge]) -> Dict[str, Any]:
    fragments = []
    for before, after in edges:
        shared = f"{before} {after} verified dependency"
        fragments.extend(
            [
                {"id": f"{before}:{after}:claim", "text": f"{shared} claim"},
                {"id": f"{before}:{after}:rule", "text": f"{shared} rule"},
            ]
        )
    try:
        from backend.modules.symbolic.symbolic_pattern_engine import (
            SymbolicPatternEngine,
        )

        overlaps = SymbolicPatternEngine.detect_pattern_overlap(fragments)
        return {
            "engine": "backend.modules.symbolic.SymbolicPatternEngine",
            "live": True,
            "overlap_count": len(overlaps),
            "brief_hash": _canonical_hash(brief),
            "fragment_count": len(fragments),
        }
    except Exception as exc:
        return {
            "engine": "backend.modules.symbolic.SymbolicPatternEngine",
            "live": False,
            "overlap_count": 0,
            "brief_hash": _canonical_hash(brief),
            "fragment_count": len(fragments),
            "error": type(exc).__name__,
        }


def _ingest_graph_capsule(
    runtime: HexCorePersistentLearningRuntime,
    project: NaturalProject,
    *,
    brief: str,
    edges: Sequence[Edge],
    revision: int,
) -> Dict[str, Any]:
    claims = [
        {
            "subject": project.project_id,
            "predicate": f"dependency:{before}",
            "object": after,
            "revision": revision,
            "confidence": 1.0,
        }
        for before, after in edges
    ]
    return runtime.knowledge.ingest(
        EvidenceCapsule(
            capsule_id=f"{project.project_id}:brief:v{revision}",
            source_uri=f"brief://{project.project_id}/v{revision}",
            content=brief,
            claims=claims,
            confidence=1.0,
            verified=True,
        )
    )


def _candidate_audit(
    candidate: Mapping[str, Any],
    expected_edges: Sequence[Edge],
) -> Dict[str, Any]:
    expected = sorted(set(expected_edges))
    proposed = sorted(set(tuple(row) for row in candidate.get("edges", [])))
    accepted = bool(candidate.get("ok") and proposed == expected)
    return {
        "provider": candidate.get("provider"),
        "live": bool(candidate.get("live")),
        "accepted": accepted,
        "exact_graph": proposed == expected,
        "proposed_edges": [list(row) for row in proposed],
        "reason": candidate.get("reason"),
    }


def run_natural_goal_graph_runtime_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    provider_artifact_path: Path | None = None,
    sealed_projects: int = 24,
    live_providers: bool = False,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    ledger_path = state_path.with_name("phase37_governed_turns.jsonl")
    if ledger_path.exists():
        ledger_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    governed = HexCoreGovernedRuntime(
        authority_provider=_allow,
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *_args: True,
        outcome_ledger=AppendOnlyOutcomeLedger(ledger_path),
        foundation_root=state_path.parent / "foundation",
        learning_state_path=state_path,
    )
    parent_id = "procedure_open_world_runtime_de18944963b6"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="natural_goal_graph_runtime",
            steps=["phase36_production_contract_runtime"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase36_dependency"},
        )
    )
    env = _load_local_env(Path(".env.local"))
    env_key = str(os.getenv("OPENAI_API_KEY") or "")
    file_key = str(env.get("OPENAI_API_KEY") or "")
    # Prefer an ASCII-safe configured value. urllib must encode HTTP headers
    # as latin-1; malformed shell overrides must fail closed.
    api_key = next(
        (
            value
            for value in (env_key, file_key)
            if value and all(ord(character) < 128 for character in value)
        ),
        "",
    )
    provider_artifacts = []
    rows = []

    for index, project in enumerate(
        _make_projects(
            sealed_projects,
            seed=370_037,
            cohort="phase37_sealed",
        )
    ):
        current_brief = project.brief
        current_edges = project.edges
        _ingest_graph_capsule(
            runtime,
            project,
            brief=current_brief,
            edges=current_edges,
            revision=1,
        )
        if project.revision_brief and project.revised_edges:
            current_brief = project.revision_brief
            current_edges = project.revised_edges
            _ingest_graph_capsule(
                runtime,
                project,
                brief=current_brief,
                edges=current_edges,
                revision=2,
            )

        native = {
            "provider": "aion_native_symbolic",
            "live": True,
            "ok": True,
            "edges": _native_edges(current_brief, project.steps),
            "reason": "native_language_to_structure",
        }
        providers = [native]
        if live_providers and index < 8:
            providers.append(_call_gemma(project, current_brief))
        if live_providers and index < 4 and api_key:
            providers.append(
                _call_openai(
                    project,
                    current_brief,
                    api_key=api_key,
                )
            )
        # High-confidence hallucination tests immutable verification.
        providers.append(
            {
                "provider": "adversarial_injected",
                "live": False,
                "ok": True,
                "edges": list(current_edges)
                + [(project.steps[-1], project.steps[0])],
                "reason": "unsupported_cycle_with_confidence_0.99",
            }
        )
        audits = [
            _candidate_audit(candidate, current_edges)
            for candidate in providers
        ]
        provider_artifacts.extend(
            {
                "project_id": project.project_id,
                **audit,
            }
            for audit in audits
            if audit["provider"] in {"local_gemma", "openai"}
        )
        accepted = next(
            (
                candidate
                for candidate, audit in zip(providers, audits)
                if audit["accepted"]
            ),
            None,
        )
        selected_edges = (
            list(accepted["edges"]) if accepted is not None else []
        )
        plan = _topological_plan(project.steps, selected_edges)
        execution = _execute_plan(plan, project.steps, current_edges)
        pattern = _pattern_overlap(current_brief, current_edges)
        goal = GoalNodeContract(
            goal_id=f"phase37:{project.project_id}",
            goal_name=f"Complete induced {project.domain} project",
            target_metric="verified_goal_success",
            target_value=1.0,
            allowed_channels=["hexcore", "pattern_engine"],
            max_iterations=8,
            approval_policy="dry_run_only",
            status="active",
        )
        memory = MemoryRecordContract(
            memory_id=f"phase37:{project.project_id}:memory",
            tier="goal",
            content_ref=f"goal-graph://{project.project_id}",
            source_ref=f"brief://{project.project_id}",
            provenance={
                "brief_hash": _canonical_hash(current_brief),
                "selected_graph_hash": _canonical_hash(selected_edges),
            },
            confidence=1.0,
            goal_id=goal.goal_id,
        )
        if goal.validate() or memory.validate():
            raise ValueError("Phase 37 contract validation failed")
        packet = TurnPacket(
            session_id=project.project_id,
            user_text=current_brief,
            apply_teaching=True,
            request_metadata={
                "goals": [goal.__dict__],
                "memories": [memory.__dict__],
                "pattern_results": [pattern],
                "reasoning_providers": [
                    str(candidate["provider"]) for candidate in providers
                ],
            },
        ).validate()
        context = governed.begin_turn(
            turn_id=f"{project.project_id}:turn",
            session_id=packet.session_id,
            user_text=packet.user_text,
            request_metadata=packet.request_metadata,
        )
        completion = governed.complete_turn(
            context=context,
            response_text=json.dumps(
                {"plan": plan, "success": execution["success"]},
                sort_keys=True,
            ),
            confidence=1.0,
            mode="goal_graph_execution",
            apply_teaching=True,
            request_metadata={
                "learning_outcome": {
                    "verified": execution["success"],
                    "verifier": "phase37_dependency_executor",
                    "verification_method": "executable",
                    "answer": json.dumps(plan),
                    "evidence_refs": [
                        f"brief://{project.project_id}/"
                        f"v{2 if project.revised_edges else 1}"
                    ],
                }
            },
        )
        provider_disabled_execution = _execute_plan(
            _topological_plan(
                project.steps,
                native["edges"],
            ),
            project.steps,
            current_edges,
        )
        row = {
            "project_id": project.project_id,
            "domain": project.domain,
            "revised": project.revised_edges is not None,
            "native_exact_graph": sorted(native["edges"])
            == sorted(current_edges),
            "provider_audits": audits,
            "selected_provider": (
                accepted["provider"] if accepted else None
            ),
            "plan": plan,
            "execution_success": execution["success"],
            "provider_disabled_success": provider_disabled_execution[
                "success"
            ],
            "pattern": pattern,
            "learning_committed": completion["learning_committed"],
            "unsafe_acceptances": sum(
                int(
                    audit["accepted"]
                    and audit["provider"] == "adversarial_injected"
                )
                for audit in audits
            ),
        }
        runtime.store.state["goal_graph_projects"][
            project.project_id
        ] = {
            **row,
            "status": "complete",
            "brief_hash": _canonical_hash(current_brief),
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(reason=f"phase37_project:{project.project_id}")
        rows.append(row)

    if provider_artifact_path is not None:
        provider_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        provider_artifact_path.write_text(
            json.dumps(provider_artifacts, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    domains = {}
    for domain in DOMAIN_STEPS:
        members = [row for row in rows if row["domain"] == domain]
        domains[domain] = {
            "projects": len(members),
            "goal_success": sum(
                int(row["execution_success"]) for row in members
            )
            / len(members),
            "native_graph_accuracy": sum(
                int(row["native_exact_graph"]) for row in members
            )
            / len(members),
        }
    live_rows = [
        row
        for row in provider_artifacts
        if row["provider"] in {"local_gemma", "openai"}
    ]
    live_ok = [row for row in live_rows if row["accepted"]]
    live_by_provider = {
        provider: {
            "calls": sum(
                int(row["provider"] == provider) for row in live_rows
            ),
            "exact_acceptances": sum(
                int(row["provider"] == provider and row["accepted"])
                for row in live_rows
            ),
        }
        for provider in ("local_gemma", "openai")
    }
    gate = {
        "goal_success": sum(
            int(row["execution_success"]) for row in rows
        )
        / len(rows),
        "weakest_domain_success": min(
            row["goal_success"] for row in domains.values()
        ),
        "native_graph_accuracy": sum(
            int(row["native_exact_graph"]) for row in rows
        )
        / len(rows),
        "provider_disabled_success": sum(
            int(row["provider_disabled_success"]) for row in rows
        )
        / len(rows),
        "revision_success": sum(
            int(row["execution_success"])
            for row in rows
            if row["revised"]
        )
        / sum(int(row["revised"]) for row in rows),
        "live_pattern_coverage": sum(
            int(row["pattern"]["live"]) for row in rows
        )
        / len(rows),
        "mean_pattern_overlaps": sum(
            row["pattern"]["overlap_count"] for row in rows
        )
        / len(rows),
        "unsafe_acceptances": sum(
            row["unsafe_acceptances"] for row in rows
        ),
        "live_provider_calls": len(live_rows),
        "live_provider_exact_acceptances": len(live_ok),
        "live_provider_exact_rate": (
            len(live_ok) / len(live_rows) if live_rows else None
        ),
        "live_by_provider": live_by_provider,
    }
    errors = []
    if gate["goal_success"] < 0.95:
        errors.append("GOAL_SUCCESS_BELOW_95_PERCENT")
    if gate["weakest_domain_success"] < 0.90:
        errors.append("WEAKEST_DOMAIN_BELOW_90_PERCENT")
    if gate["native_graph_accuracy"] < 0.95:
        errors.append("NATIVE_GRAPH_INDUCTION_BELOW_95_PERCENT")
    if gate["provider_disabled_success"] < 0.95:
        errors.append("PROVIDER_REMOVAL_BROKE_COGNITION")
    if gate["revision_success"] < 0.95:
        errors.append("REVISED_GOAL_GRAPH_NOT_RECOVERED")
    if gate["live_pattern_coverage"] < 1.0:
        errors.append("LIVE_PATTERN_ENGINE_PATH_UNAVAILABLE")
    if gate["unsafe_acceptances"]:
        errors.append("ADVERSARIAL_GRAPH_ACCEPTED")
    if live_providers and gate["live_provider_calls"] < 8:
        errors.append("INSUFFICIENT_LIVE_PROVIDER_AUDIT")
    if live_providers and gate["live_provider_exact_acceptances"] < 8:
        errors.append("INSUFFICIENT_EXACT_LIVE_PROVIDER_PROPOSALS")
    if live_providers and api_key and live_by_provider["openai"][
        "exact_acceptances"
    ] < 1:
        errors.append("OPENAI_LIVE_PATH_NOT_VERIFIED")
    if live_providers and live_by_provider["local_gemma"][
        "exact_acceptances"
    ] < 1:
        errors.append("GEMMA_LIVE_PATH_NOT_VERIFIED")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_natural_goal_graph_"
            + _canonical_hash(
                {
                    "parent": parent_id,
                    "gate": gate,
                    "domains": domains,
                }
            )[:12]
        ),
        goal="natural_goal_graph_runtime",
        steps=[
            "parse_natural_project_brief",
            "invoke_live_pattern_overlap_analysis",
            "accept_provider_outputs_as_untrusted_graph_proposals",
            "verify_graph_edges_against_provenance_bearing_brief",
            "construct_executable_dependency_order",
            "revise_graph_when_verified_brief_changes",
            "execute_verify_commit_and_restart",
        ],
        score=gate["goal_success"] + gate["native_graph_accuracy"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase37_natural_goal_graph_sealed",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase37_natural_goal_graph_runtime")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "projects_retained": len(
            restarted.store.state["goal_graph_projects"]
        )
        == sealed_projects,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "natural_goal_graph_runtime"
            )
            == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["projects_retained"]
        and restart["champion_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.natural_goal_graph_runtime.v1",
        "benchmark": "natural_brief_to_verified_executable_goal_graph",
        "passed": passed,
        "gate": gate,
        "domains": domains,
        "sealed": {"projects": len(rows), "rows": rows},
        "provider_audit": {
            "live_requested": live_providers,
            "openai_configured": bool(api_key),
            "rows": provider_artifacts,
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary_statement": (
            "Phase 37 executes real Pattern Engine overlap analysis and, when "
            "enabled, live Gemma/OpenAI goal-graph proposals. HexCore native "
            "parsing, exact evidence verification and executable fallback "
            "remain engineered for four bounded vocabularies and four graph "
            "families. This is not unrestricted natural-language project "
            "understanding or autonomous general intelligence."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore Phase 37 natural goal-graph benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--provider-artifact-path", type=Path)
    parser.add_argument("--sealed-projects", type=int, default=24)
    parser.add_argument("--live-providers", action="store_true")
    args = parser.parse_args()
    result = run_natural_goal_graph_runtime_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        provider_artifact_path=args.provider_artifact_path,
        sealed_projects=args.sealed_projects,
        live_providers=args.live_providers,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
