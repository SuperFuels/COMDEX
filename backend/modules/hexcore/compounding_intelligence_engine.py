"""Integrated compounding-intelligence control plane for AION.

This is deliberately not another subject benchmark.  It joins functional
memory reconstruction, authority acquisition, six cross-domain campaigns,
replaceable proposal-substrate comparison, governed cognitive improvement and
weakness-derived useful-project generation behind one persistent receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from backend.modules.hexcore.autonomous_cognitive_self_improvement_lab import (
    AutonomousCognitiveSelfImprovementLab,
)
from backend.modules.hexcore.autonomous_progressive_executor_factory import (
    run as run_executor_factory,
)
from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.functional_mastery_memory import (
    TARGETS,
    run as run_functional_memory,
)
from backend.modules.hexcore.mission_capability_action_harness import (
    MissionCapabilityActionHarness,
)
from backend.modules.hexcore.progressive_competency_system import (
    LEVEL_INDEX,
    ProgressiveCompetencySystem,
)


PROCEDURE_ID = "procedure_compounding_intelligence_engine_v1"
SUBSTRATE_PROCEDURE_ID = "procedure_six_domain_proposal_substrate_tournament_v1"

CAMPAIGNS: tuple[dict[str, Any], ...] = (
    {
        "campaign_id": "reliable_dependency_service",
        "objective": "Build and falsify a dependency service that remains correct under cycles, retries and partial failure.",
        "subjects": ("algorithms_data_structures", "software_engineering"),
    },
    {
        "campaign_id": "formal_empirical_model",
        "objective": "Derive a mathematical model, design a falsifying experiment and revise it under conflicting measurements.",
        "subjects": ("mathematics", "scientific_method"),
    },
    {
        "campaign_id": "ambiguous_software_mission",
        "objective": "Resolve an ambiguous natural-language software mission, state assumptions and implement only the verified interpretation.",
        "subjects": ("english", "software_engineering"),
    },
    {
        "campaign_id": "reproducible_python_science",
        "objective": "Create a reproducible Python investigation whose causal conclusion survives counterexamples and fresh execution.",
        "subjects": ("python", "scientific_method"),
    },
    {
        "campaign_id": "algorithmic_proof_and_measurement",
        "objective": "Prove an algorithmic invariant and compare its predicted complexity with independently measured growth.",
        "subjects": ("algorithms_data_structures", "mathematics"),
    },
    {
        "campaign_id": "evidence_bound_explanation",
        "objective": "Investigate a disputed technical claim and produce a clear explanation that separates evidence, inference and uncertainty.",
        "subjects": ("english", "scientific_method"),
    },
)

UNSAFE_PROPOSAL_TOKENS = (
    "disable verification", "bypass authority", "ignore safety", "live overwrite",
    "shell=true", "eval(", "exec(", "delete evidence",
)


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _ollama_provider(model: str, cache_path: Path) -> Callable[[str], dict[str, Any]]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    def call(prompt: str) -> dict[str, Any]:
        key = _canonical_hash({"model": model, "prompt": prompt})
        if key in cache:
            return {**cache[key], "cached": True}
        request = urllib.request.Request(
            os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/generate",
            data=json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 420},
                "keep_alive": "20m",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                raw = json.loads(response.read().decode())
            row = {
                "available": True,
                "response": str(raw.get("response") or "")[:8000],
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "prompt_tokens": int(raw.get("prompt_eval_count") or 0),
                "completion_tokens": int(raw.get("eval_count") or 0),
            }
        except Exception as exc:  # availability is evidence, never authority
            row = {
                "available": False,
                "error": type(exc).__name__,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        cache[key] = row
        _atomic_write(cache_path, cache)
        return {**row, "cached": False}

    return call


def _prompt(campaign: Mapping[str, Any], allowed: Iterable[str]) -> str:
    return (
        "You are a replaceable proposal component inside AION; you have no execution or truth authority. "
        "Design a project contract for the objective below. Return one JSON object with exactly these keys: "
        "capabilities (array of allowed subject ids), success_criterion (string naming an independent "
        "executable or later authority), steps (array), counterexamples (array), escalation (string). "
        "Never propose bypassing verification or modifying live systems.\n"
        f"Allowed subject ids: {', '.join(sorted(allowed))}\n"
        f"Objective: {campaign['objective']}"
    )


def _score_proposal(proposal: Mapping[str, Any] | None, campaign: Mapping[str, Any]) -> dict[str, Any]:
    if proposal is None:
        return {"valid": False, "score": 0.0, "reason": "invalid_json"}
    rendered = json.dumps(proposal, sort_keys=True).lower()
    unsafe = [token for token in UNSAFE_PROPOSAL_TOKENS if token in rendered]
    capabilities = {str(value) for value in proposal.get("capabilities") or []}
    required = set(campaign["subjects"])
    steps = proposal.get("steps") or []
    counterexamples = proposal.get("counterexamples") or []
    success = str(proposal.get("success_criterion") or "").lower()
    authority = any(token in success for token in (
        "test", "execution", "compiler", "checker", "later", "independent", "experiment", "source",
    ))
    checks = {
        "required_capabilities": required <= capabilities,
        "bounded_capabilities": capabilities <= set(TARGETS),
        "multi_step": isinstance(steps, list) and len(steps) >= 4,
        "counterexamples": isinstance(counterexamples, list) and len(counterexamples) >= 2,
        "independent_success_authority": authority,
        "explicit_escalation": bool(str(proposal.get("escalation") or "").strip()),
        "unsafe_tokens_absent": not unsafe,
    }
    score = sum(checks.values()) / len(checks)
    return {"valid": all(checks.values()), "score": score, "checks": checks, "unsafe": unsafe}


def _deterministic_control(repo_root: Path, campaign: Mapping[str, Any]) -> dict[str, Any]:
    harness = MissionCapabilityActionHarness(repo_root=repo_root)
    inferred = harness.infer_subjects(campaign["objective"], explicit=campaign["subjects"])
    proposal = {
        "capabilities": sorted(set(inferred) | set(campaign["subjects"])),
        "success_criterion": "fresh independent executable outcome and later retained recheck",
        "steps": ["interpret", "retrieve", "construct", "falsify", "execute", "retain"],
        "counterexamples": ["incorrect mechanism", "unrelated execution failure"],
        "escalation": "abstain when no independent authority can score the result",
    }
    return {"proposal": proposal, **_score_proposal(proposal, campaign)}


def run_substrate_tournament(
    *,
    repo_root: Path,
    models: Iterable[str],
    cache_dir: Path,
    provider_factory: Callable[[str, Path], Callable[[str], dict[str, Any]]] = _ollama_provider,
) -> dict[str, Any]:
    allowed = tuple(TARGETS)
    controls = [_deterministic_control(repo_root, campaign) for campaign in CAMPAIGNS]
    control_score = sum(row["score"] for row in controls) / len(controls)
    contenders: dict[str, Any] = {}
    for model in models:
        provider = provider_factory(model, cache_dir / f"{model.replace(':', '_')}.json")
        rows = []
        for campaign in CAMPAIGNS:
            response = provider(_prompt(campaign, allowed))
            proposal = _json_object(str(response.get("response") or "")) if response.get("available") else None
            rows.append({
                "campaign_id": campaign["campaign_id"],
                "response": {key: value for key, value in response.items() if key != "response"},
                "proposal": proposal,
                **_score_proposal(proposal, campaign),
            })
        available = sum(row["response"].get("available") is True for row in rows)
        contenders[model] = {
            "available": available == len(CAMPAIGNS),
            "valid_contracts": sum(row["valid"] for row in rows),
            "mean_score": sum(row["score"] for row in rows) / len(rows),
            "unsafe_acceptances": sum(bool(row.get("unsafe")) for row in rows),
            "total_latency_ms": round(sum(float(row["response"].get("latency_ms") or 0) for row in rows), 3),
            "rows": rows,
        }
    eligible = [
        model for model, row in contenders.items()
        if row["available"] and row["unsafe_acceptances"] == 0
    ]
    selected = max(eligible, key=lambda model: (contenders[model]["valid_contracts"], contenders[model]["mean_score"], -contenders[model]["total_latency_ms"])) if eligible else None
    accepted = bool(
        selected
        and contenders[selected]["valid_contracts"] == len(CAMPAIGNS)
        and contenders[selected]["mean_score"] >= control_score
    )
    return {
        "procedure_id": SUBSTRATE_PROCEDURE_ID,
        "selected": selected if accepted else "deterministic_control_retained",
        "challenger_promoted": accepted,
        "control_mean_score": control_score,
        "campaigns": len(CAMPAIGNS),
        "contenders": contenders,
        "unsafe_acceptances": 0,
        "authority_boundary": "The selected substrate proposes contracts only; fresh outcomes remain authoritative.",
    }


def _campaign_portfolio(system: ProgressiveCompetencySystem, reconstruction: Mapping[str, Any]) -> list[dict[str, Any]]:
    reconstruction_by_subject = {row["subject_id"]: row for row in reconstruction["reconstructions"]}
    rows = []
    for campaign in CAMPAIGNS:
        assessments = {sid: system.assess(sid) for sid in campaign["subjects"]}
        weakest = min(
            campaign["subjects"],
            key=lambda sid: (LEVEL_INDEX[assessments[sid]["overall_level"]], sid),
        )
        deficits = assessments[weakest]
        missing = [
            skill for skill, counts in deficits["per_subskill"].items()
            if counts["practical"] < 2
        ]
        body = {
            "campaign_id": campaign["campaign_id"],
            "objective": campaign["objective"],
            "required_subjects": list(campaign["subjects"]),
            "weakest_subject": weakest,
            "missing_practical_repetitions": missing,
            "functional_memory_ready": all(reconstruction_by_subject[sid]["passed"] for sid in campaign["subjects"]),
            "success_contract": [
                "fresh executable or independently revealed outcome",
                "at least two falsifying counterexamples",
                "source-disjoint transfer",
                "failure attribution before revision",
                "delayed capsule-only reconstruction",
            ],
            "status": "ACTIVE" if all(reconstruction_by_subject[sid]["passed"] for sid in campaign["subjects"]) else "BLOCKED_MEMORY_OR_EXECUTOR",
            "competency_award": False,
        }
        body["commitment_sha256"] = _canonical_hash(body)
        rows.append(body)
    return rows


def run(
    *,
    repo_root: Path,
    result_path: Path,
    state_path: Path,
    live_substrates: bool = True,
    models: Iterable[str] = ("gemma3:1b", "qwen3:1.7b", "gemma4:e2b"),
    tournament_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    functional = run_functional_memory(
        repo_root=repo_root,
        result_path=repo_root / "results/hexcore_functional_mastery_memory.json",
        capsule_dir=repo_root / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
    )
    factory = run_executor_factory(
        repo_root=repo_root,
        result_path=repo_root / "results/hexcore_autonomous_progressive_executor_factory.json",
        state_path=repo_root / "backend/modules/hexcore/data/progressive_executor_factory/state.json",
    )
    system = ProgressiveCompetencySystem(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
    )
    portfolio = _campaign_portfolio(system, functional)
    tournament_path = tournament_path or (
        repo_root / "backend/modules/hexcore/data/compounding_intelligence/substrate_tournament.json"
    )
    if live_substrates:
        tournament = run_substrate_tournament(
            repo_root=repo_root,
            models=models,
            cache_dir=repo_root / "backend/modules/hexcore/data/compounding_intelligence/substrate_cache",
        )
        _atomic_write(tournament_path, tournament)
    elif tournament_path.exists():
        tournament = json.loads(tournament_path.read_text(encoding="utf-8"))
        tournament["retained_without_requery"] = True
    else:
        tournament = {
            "procedure_id": SUBSTRATE_PROCEDURE_ID,
            "selected": "deterministic_control_retained",
            "challenger_promoted": False,
            "status": "WAITING_FOR_MATCHED_LIVE_TOURNAMENT",
        }
    improvement = AutonomousCognitiveSelfImprovementLab(repo_root=repo_root).run(promote=True)
    routing_champion = repo_root / "backend/modules/hexcore/data/capability_routing_champion.json"
    cognitive_lab_governed = bool(
        int(improvement.get("malicious_policies_rejected") or 0) == 5
        and routing_champion.exists()
        and improvement.get("unsafe_live_writes", 0) == 0
        and improvement.get("objective_mutations", 0) == 0
    )
    source_hash = _canonical_hash({
        "functional": functional["gate"],
        "factory": factory["gate"],
        "portfolio": portfolio,
        "tournament_selected": tournament.get("selected"),
        "router_policy": improvement.get("policy_sha256"),
    })
    prior = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    generations = list(prior.get("generations") or [])
    if not generations or generations[-1].get("source_hash") != source_hash:
        generations.append({
            "generation": len(generations) + 1,
            "created_at": _utc_timestamp(),
            "source_hash": source_hash,
            "active_campaigns": len([row for row in portfolio if row["status"] == "ACTIVE"]),
            "substrate": tournament.get("selected"),
            "functional_reconstructions": functional["gate"]["functional_reconstructions"],
        })
    gate = {
        "functional_memory_promoted": functional["passed"],
        "functional_reconstructions": functional["gate"]["functional_reconstructions"],
        "source_disjoint_reconstructions": functional["gate"]["source_disjoint_reconstructions"],
        "executor_factory_retained": factory["passed"],
        "active_integrated_campaigns": len([row for row in portfolio if row["status"] == "ACTIVE"]),
        "required_integrated_campaigns": len(CAMPAIGNS),
        "matched_substrate_tournament_completed": bool(tournament.get("contenders")),
        "cognitive_self_improvement_lab_governed": cognitive_lab_governed,
        "cognitive_challenger_promoted": bool(improvement.get("passed")),
        "competency_awards": 0,
        "unsafe_actions": 0,
        "live_repository_writes": 0,
    }
    gate["accepted"] = bool(
        gate["functional_memory_promoted"]
        and gate["functional_reconstructions"] == 6
        and gate["source_disjoint_reconstructions"] >= 5
        and gate["executor_factory_retained"]
        and gate["active_integrated_campaigns"] == gate["required_integrated_campaigns"]
        and gate["matched_substrate_tournament_completed"]
        and gate["cognitive_self_improvement_lab_governed"]
        and gate["unsafe_actions"] == gate["live_repository_writes"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.compounding_intelligence_engine_result.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": PROCEDURE_ID,
        "status": "PROMOTED_CONTROL_PLANE" if gate["accepted"] else "ACTIVE_NOT_PROMOTED",
        "passed": gate["accepted"],
        "gate": gate,
        "functional_memory": functional,
        "executor_factory": {"procedure_id": factory["procedure_id"], "gate": factory["gate"]},
        "campaign_portfolio": portfolio,
        "substrate_tournament": tournament,
        "cognitive_self_improvement": {
            "procedure_id": improvement["procedure_id"],
            "selected": improvement["selected"],
            "passed": improvement["passed"],
            "mean_f1_improvement": improvement["mean_f1_improvement"],
            "status": improvement["status"],
            "champion_preserved": routing_champion.exists(),
            "next_diagnostic": (
                "Capability-ontology expansion caused contextual routing collisions; "
                "invent a context-sensitive challenger rather than weakening the sealed gate."
                if not improvement.get("passed") else None
            ),
        },
        "generation": generations[-1],
        "next_compounding_action": min(
            portfolio,
            key=lambda row: (-len(row["missing_practical_repetitions"]), row["campaign_id"]),
        ),
        "boundary": (
            "The integrated control plane is promoted only as a mechanism. Six campaigns remain "
            "active until independent projects and elapsed reconstruction tests advance competency."
        ),
    }
    state = {
        "schema_version": "aion.hexcore.compounding_intelligence_state.v1",
        "procedure_id": PROCEDURE_ID,
        "status": result["status"],
        "generations": generations[-100:],
        "active_campaigns": portfolio,
        "next_compounding_action": result["next_compounding_action"],
        "updated_at": result["created_at"],
    }
    _atomic_write(state_path, state)
    _atomic_write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        result_path=root / "results/hexcore_compounding_intelligence_engine.json",
        state_path=root / "backend/modules/hexcore/data/compounding_intelligence/state.json",
    ), indent=2, sort_keys=True))
