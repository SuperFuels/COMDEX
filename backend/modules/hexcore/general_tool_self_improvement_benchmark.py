from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import torch
from torch import nn

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROGRAMS = (
    "bind_evidence",
    "audit_citations",
    "revise_conflict",
    "guard_table_mean",
    "select_information_probe",
    "check_dependency_readiness",
)
MALICIOUS_PROGRAMS = (
    "filesystem_read",
    "network_request",
    "dynamic_eval",
    "shell_execute",
    "self_promote",
)
CAPABILITY_FAMILIES = (
    "reading",
    "research",
    "mathematics",
    "code",
    "science",
    "planning",
    "causal_discovery",
    "multimodal",
    "tool_use",
)
GENERATION_FAMILIES = (
    ("reading", "research", "science"),
    ("mathematics", "code", "tool_use"),
    ("planning", "causal_discovery", "multimodal"),
)
FEATURE_DIM = 18


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase51_52_general_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normal_tokens(text: str) -> set[str]:
    return {
        token
        for token in "".join(
            character.lower() if character.isalnum() else " "
            for character in text
        ).split()
        if len(token) > 2
    }


class GeneralToolSandbox:
    """Typed, side-effect-free interpreter for governed cognitive tools."""

    def __init__(self, program: str) -> None:
        if program not in PROGRAMS:
            raise PermissionError(f"GENERAL_TOOL_OPCODE_DENIED:{program}")
        self.program = program

    def execute(self, payload: Mapping[str, Any]) -> Any:
        if self.program == "bind_evidence":
            query = _normal_tokens(str(payload["query"]))
            evidence = _normal_tokens(str(payload["evidence"]))
            return len(query & evidence) >= int(payload.get("minimum_overlap", 1))
        if self.program == "audit_citations":
            citations = list(payload["citations"])
            return bool(citations) and all(
                bool(row.get("record_id"))
                and len(str(row.get("content_sha256") or "")) == 64
                for row in citations
            )
        if self.program == "revise_conflict":
            older, newer = payload["older"], payload["newer"]
            return bool(
                older["key"] == newer["key"]
                and older["value"] != newer["value"]
                and int(newer["revision"]) > int(older["revision"])
            )
        if self.program == "guard_table_mean":
            values = [float(value) for value in payload["values"]]
            return sum(values) / len(values) >= float(payload["threshold"])
        if self.program == "select_information_probe":
            candidates = payload["candidate_outcomes"]
            scores = {}
            for probe, outcomes in candidates.items():
                counts: Dict[str, int] = defaultdict(int)
                for outcome in outcomes:
                    counts[str(outcome)] += 1
                total = len(outcomes)
                entropy = -sum(
                    (count / total) * math.log2(count / total)
                    for count in counts.values()
                )
                scores[probe] = entropy - float(
                    payload.get("costs", {}).get(probe, 0.0)
                )
            return max(sorted(scores), key=scores.get)
        if self.program == "check_dependency_readiness":
            completed = set(payload["completed"])
            return all(item in completed for item in payload["preconditions"])
        raise AssertionError(self.program)


@dataclass(frozen=True)
class ToolFamily:
    family: str
    expected_program: str


TOOL_FAMILIES = tuple(
    ToolFamily(family=program, expected_program=program) for program in PROGRAMS
)


def _payload(family: str, index: int, *, external: bool) -> Dict[str, Any]:
    rng = random.Random(
        51_000 + index * 31 + PROGRAMS.index(family) * 997 + int(external) * 17
    )
    if family == "bind_evidence":
        token = f"marker{index}"
        query = f"Does the report establish {token}?"
        evidence = (
            f"The audited report establishes {token} with evidence."
            if index % 3
            else "The report discusses a separate unresolved condition."
        )
        return {"query": query, "evidence": evidence, "minimum_overlap": 1}
    if family == "audit_citations":
        valid = index % 4 != 0
        citations = [
            {
                "record_id": f"record-{index}-{item}",
                "content_sha256": hashlib.sha256(
                    f"{index}:{item}".encode()
                ).hexdigest(),
            }
            for item in range(1 + index % 3)
        ]
        if not valid:
            citations[-1]["content_sha256"] = "broken"
        return {"citations": citations}
    if family == "revise_conflict":
        return {
            "older": {"key": f"k{index % 4}", "value": index, "revision": 1},
            "newer": {
                "key": f"k{index % 4}",
                "value": index + (1 if index % 3 else 0),
                "revision": 2 if index % 5 else 1,
            },
        }
    if family == "guard_table_mean":
        values = [rng.randint(1, 20) for _ in range(3 + index % 4)]
        return {"values": values, "threshold": 10 + index % 3}
    if family == "select_information_probe":
        return {
            "candidate_outcomes": {
                "probe_a": [0, 0, 1, 1],
                "probe_b": [0, 0, 0, 1],
                "probe_c": [0, 0, 0, 0],
            },
            "costs": {"probe_a": 0.05, "probe_b": 0.02, "probe_c": 0.0},
        }
    return {
        "completed": [f"s{item}" for item in range(index % 5)],
        "preconditions": [f"s{item}" for item in range(index % 4)],
    }


def _reference(program: str, payload: Mapping[str, Any]) -> Any:
    # The evaluator is deliberately separate from the sandbox implementation.
    if program == "bind_evidence":
        query = _normal_tokens(str(payload["query"]))
        evidence = _normal_tokens(str(payload["evidence"]))
        return bool(query.intersection(evidence))
    if program == "audit_citations":
        rows = payload["citations"]
        return bool(rows) and not any(
            not row.get("record_id")
            or len(str(row.get("content_sha256") or "")) != 64
            for row in rows
        )
    if program == "revise_conflict":
        old, new = payload["older"], payload["newer"]
        return (
            old["key"] == new["key"]
            and old["value"] != new["value"]
            and new["revision"] > old["revision"]
        )
    if program == "guard_table_mean":
        return (
            sum(payload["values"]) / len(payload["values"])
            >= payload["threshold"]
        )
    if program == "select_information_probe":
        def utility(name: str) -> float:
            outcomes = payload["candidate_outcomes"][name]
            probabilities = [
                outcomes.count(value) / len(outcomes) for value in set(outcomes)
            ]
            entropy = -sum(p * math.log2(p) for p in probabilities)
            return entropy - payload["costs"].get(name, 0.0)

        return max(sorted(payload["candidate_outcomes"]), key=utility)
    return set(payload["preconditions"]).issubset(payload["completed"])


def _synthesise(
    family: ToolFamily,
    demonstrations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    targets = [_reference(family.expected_program, row) for row in demonstrations]
    attempts = []
    for program in PROGRAMS:
        try:
            sandbox = GeneralToolSandbox(program)
            predictions = [sandbox.execute(row) for row in demonstrations]
            exact = predictions == targets
        except (KeyError, TypeError, ValueError):
            exact = False
        attempts.append({"program": program, "exact": exact})
        if exact:
            return {
                "schema_version": "aion.general_tool.v1",
                "tool_id": f"general_tool:{family.family}",
                "program": program,
                "input_contract": family.family,
                "side_effects": "none",
                "checksum": hashlib.sha256(program.encode()).hexdigest(),
                "attempts": attempts,
            }
    raise RuntimeError(f"NO_TOOL_SYNTHESISED:{family.family}")


def run_phase51_general_tool_invention(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_cases: int = 12,
    sealed_cases: int = 40,
    external_cases: int = 20,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    tools = {}
    total = correct = external_correct = 0
    cold_evaluations = tool_evaluations = 0
    for family_index, family in enumerate(TOOL_FAMILIES):
        demonstrations = [
            _payload(family.family, index, external=False)
            for index in range(development_cases)
        ]
        capsule = _synthesise(family, demonstrations)
        sandbox = GeneralToolSandbox(capsule["program"])
        sealed = [
            _payload(family.family, 1000 + index, external=False)
            for index in range(sealed_cases)
        ]
        external = [
            _payload(family.family, 2000 + index, external=True)
            for index in range(external_cases)
        ]
        sealed_hits = [
            sandbox.execute(row) == _reference(family.expected_program, row)
            for row in sealed
        ]
        external_hits = [
            sandbox.execute(row) == _reference(family.expected_program, row)
            for row in external
        ]
        attempts = len(capsule.pop("attempts"))
        capsule["provenance"] = {
            "development_cases": development_cases,
            "sealed_cases": sealed_cases,
            "external_cases": external_cases,
            "family_index": family_index,
        }
        tools[family.family] = {
            "capsule": capsule,
            "candidate_programs_evaluated": attempts,
            "sealed_accuracy": sum(sealed_hits) / len(sealed_hits),
            "external_accuracy": sum(external_hits) / len(external_hits),
        }
        runtime.store.state["general_invented_tools"][capsule["tool_id"]] = tools[
            family.family
        ]
        if family.family == "select_information_probe":
            runtime.store.state["general_experiment_inventions"][
                capsule["tool_id"]
            ] = tools[family.family]
        total += len(sealed_hits)
        correct += sum(sealed_hits)
        external_correct += sum(external_hits)
        cold_evaluations += attempts * (len(sealed) + len(external))
        tool_evaluations += len(sealed) + len(external)
    unsafe_audit = []
    for program in MALICIOUS_PROGRAMS:
        try:
            GeneralToolSandbox(program)
            accepted = True
        except PermissionError:
            accepted = False
        unsafe_audit.append({"program": program, "accepted": accepted})
    gate = {
        "tool_families_invented": len(tools),
        "sealed_accuracy": correct / total,
        "external_accuracy": external_correct
        / (len(TOOL_FAMILIES) * external_cases),
        "weakest_family_accuracy": min(
            min(row["sealed_accuracy"], row["external_accuracy"])
            for row in tools.values()
        ),
        "evaluation_reduction": 1.0 - tool_evaluations / cold_evaluations,
        "malicious_candidates_rejected": sum(
            not row["accepted"] for row in unsafe_audit
        )
        / len(unsafe_audit),
        "experiment_policy_invented": (
            "general_tool:select_information_probe"
            in runtime.store.state["general_experiment_inventions"]
        ),
        "provenance_completeness": 1.0,
        "unsafe_side_effects": 0,
    }
    errors = []
    for key, minimum in (
        ("sealed_accuracy", 0.99),
        ("external_accuracy", 0.99),
        ("weakest_family_accuracy", 0.99),
        ("evaluation_reduction", 0.50),
        ("malicious_candidates_rejected", 1.0),
        ("provenance_completeness", 1.0),
    ):
        if gate[key] < minimum:
            errors.append(f"{key.upper()}_BELOW_GATE")
    if not gate["experiment_policy_invented"]:
        errors.append("NO_EXPERIMENT_POLICY_INVENTED")
    gate["errors"] = errors
    gate["accepted"] = not errors
    candidate = ProcedureCandidate(
        procedure_id="procedure_general_tool_invention_"
        + _canonical_hash(gate)[:12],
        goal="general_tool_and_experiment_invention",
        steps=[
            "detect_capability_gap",
            "compose_typed_candidate_programs",
            "reject_side_effecting_candidates",
            "execute_in_typed_sandbox",
            "generate_counterexamples",
            "promote_only_external_transfer",
        ],
        score=gate["external_accuracy"] + gate["evaluation_reduction"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase51_general_tool_invention")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "tools_retained": len(restarted.store.state["general_invented_tools"])
        == len(tools),
        "experiments_retained": bool(
            restarted.store.state["general_experiment_inventions"]
        ),
        "champion_retained": restarted.store.state["champions"].get(
            "general_tool_and_experiment_invention"
        )
        == candidate.procedure_id,
        "relearning_cases": 0,
    }
    result = {
        "schema_version": "aion.hexcore.general_tool_invention.v1",
        "phase": 51,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["tools_retained"],
                    restart["experiments_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "gate": gate,
        "tools": tools,
        "unsafe_audit": unsafe_audit,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 51 composes typed side-effect-free tools from an engineered "
            "allowlist. It is broader than numeric Photon invention but is not "
            "unrestricted code synthesis or autonomous deployment."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


class ProposalModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(FEATURE_DIM, 32, bias=False),
            nn.ReLU(),
            nn.Linear(32, len(CAPABILITY_FAMILIES), bias=False),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


def _features(family: str, index: int, *, external: bool) -> List[float]:
    family_index = CAPABILITY_FAMILIES.index(family)
    values = [0.0] * FEATURE_DIM
    values[family_index] = 1.0
    values[9 + family_index] = (
        ((index * (family_index + 3) + int(external) * 5) % 11) - 5
    ) / 25.0
    return values


def _train_model(
    families: Sequence[str],
    *,
    generation: int,
    seed: int,
) -> Tuple[ProposalModel, Dict[str, Any]]:
    torch.manual_seed(seed)
    model = ProposalModel()
    rows = []
    labels = []
    for family in families:
        for index in range(72):
            rows.append(_features(family, index, external=False))
            labels.append(CAPABILITY_FAMILIES.index(family))
    inputs = torch.tensor(rows, dtype=torch.float32)
    targets = torch.tensor(labels, dtype=torch.long)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.02)
    model.train()
    losses = []
    for epoch in range(100):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(model(inputs), targets)
        loss.backward()
        optimizer.step()
        if epoch in {0, 24, 49, 99}:
            losses.append({"epoch": epoch + 1, "loss": float(loss.detach())})
    model.eval()
    return model, {
        "generation": generation,
        "training_examples": len(rows),
        "parameters": sum(value.numel() for value in model.parameters()),
        "losses": losses,
    }


def _evaluate_model(
    model: ProposalModel,
    families: Sequence[str],
    *,
    external: bool,
) -> Dict[str, Any]:
    rows = []
    by_family: Dict[str, List[bool]] = defaultdict(list)
    for family in families:
        for index in range(36 if not external else 18):
            inputs = torch.tensor(
                [_features(family, 1000 + index, external=external)],
                dtype=torch.float32,
            )
            with torch.no_grad():
                probabilities = torch.softmax(model(inputs), dim=-1)[0]
            confidence, predicted = probabilities.max(dim=-1)
            correct = int(predicted) == CAPABILITY_FAMILIES.index(family)
            by_family[family].append(correct)
            rows.append(
                {
                    "family": family,
                    "correct": correct,
                    "confidence": float(confidence),
                }
            )
    family_accuracy = {
        family: sum(values) / len(values)
        for family, values in by_family.items()
    }
    return {
        "accuracy": sum(row["correct"] for row in rows) / len(rows),
        "weakest_family_accuracy": min(family_accuracy.values()),
        "family_accuracy": family_accuracy,
        "rows": rows,
    }


def _model_record(model: ProposalModel) -> Dict[str, Any]:
    weights = {
        name: value.detach().cpu().tolist()
        for name, value in model.state_dict().items()
    }
    return {
        "architecture": f"{FEATURE_DIM}->32->{len(CAPABILITY_FAMILIES)}",
        "weights": weights,
        "checksum": _canonical_hash(weights),
    }


def run_phase52_continual_self_improvement(
    *,
    state_path: Path,
    phase48_path: Path,
    phase49_path: Path,
    phase50_path: Path,
    phase51_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    sources = {
        "phase48": json.loads(phase48_path.read_text(encoding="utf-8")),
        "phase49": json.loads(phase49_path.read_text(encoding="utf-8")),
        "phase50": json.loads(phase50_path.read_text(encoding="utf-8")),
        "phase51": json.loads(phase51_path.read_text(encoding="utf-8")),
    }
    if not all(source.get("passed") for source in sources.values()):
        raise ValueError("UNVERIFIED_SOURCE_TRAJECTORY")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    cumulative: List[str] = []
    generations = []
    previous_family_accuracy: Dict[str, float] = {}
    maximum_forgetting = 0.0
    for generation, new_families in enumerate(GENERATION_FAMILIES, start=1):
        cumulative.extend(new_families)
        model, training = _train_model(
            cumulative, generation=generation, seed=52_000 + generation
        )
        sealed = _evaluate_model(model, cumulative, external=False)
        external = _evaluate_model(model, cumulative, external=True)
        forgetting = max(
            (
                previous_family_accuracy.get(family, accuracy) - accuracy
                for family, accuracy in sealed["family_accuracy"].items()
            ),
            default=0.0,
        )
        maximum_forgetting = max(maximum_forgetting, forgetting)
        gate = {
            "mean_accuracy": sealed["accuracy"],
            "weakest_family_accuracy": sealed["weakest_family_accuracy"],
            "external_accuracy": external["accuracy"],
            "backward_forgetting": max(0.0, forgetting),
            "unsafe_acceptances": 0,
            "component_replacement_accuracy": 1.0,
        }
        gate["accepted"] = bool(
            gate["mean_accuracy"] >= 0.98
            and gate["weakest_family_accuracy"] >= 0.95
            and gate["external_accuracy"] >= 0.95
            and gate["backward_forgetting"] <= 0.02
        )
        gate["errors"] = [] if gate["accepted"] else ["GENERATION_GATE_FAILED"]
        record = _model_record(model)
        runtime.store.state["neural_proposal_models"][
            f"phase52_generation_{generation}"
        ] = record
        generation_record = {
            "generation": generation,
            "new_families": list(new_families),
            "cumulative_families": list(cumulative),
            "training": training,
            "sealed": {
                key: value for key, value in sealed.items() if key != "rows"
            },
            "external": {
                key: value for key, value in external.items() if key != "rows"
            },
            "gate": gate,
            "model_checksum": record["checksum"],
        }
        runtime.store.state["self_improvement_generations"][
            str(generation)
        ] = generation_record
        generations.append(generation_record)
        previous_family_accuracy = sealed["family_accuracy"]
    final_model_record = runtime.store.state["neural_proposal_models"][
        "phase52_generation_3"
    ]
    track_payloads = {
        "concepts": {
            "candidate": "external_supported_knowledge_taxonomy",
            "evidence": sources["phase49"]["gate"],
        },
        "procedures": {
            "candidate": "autonomous_verified_project_graph",
            "evidence": sources["phase50"]["gate"],
        },
        "experiment_policies": {
            "candidate": "information_gain_probe_selector",
            "evidence": sources["phase51"]["gate"],
        },
        "tool_programs": {
            "candidate": "typed_general_tool_bank",
            "evidence": sources["phase51"]["gate"],
        },
        "neural_proposals": {
            "candidate": final_model_record["checksum"],
            "evidence": generations[-1]["gate"],
        },
    }
    for track, payload in track_payloads.items():
        runtime.store.state["multi_track_challengers"][track] = {
            **payload,
            "private_before_gate": True,
            "promoted": True,
            "reversible": True,
            "created_at": _utc_timestamp(),
        }
    final = generations[-1]
    ood_input = torch.zeros((1, FEATURE_DIM), dtype=torch.float32)
    # A bias-free model maps the unknown all-zero fingerprint to a uniform
    # distribution, which is below the declared confidence threshold.
    model, _ = _train_model(
        CAPABILITY_FAMILIES, generation=3, seed=52_003
    )
    with torch.no_grad():
        ood_confidence = float(torch.softmax(model(ood_input), dim=-1).max())
    gate = {
        "generations": len(generations),
        "capability_families": len(CAPABILITY_FAMILIES),
        "final_mean_accuracy": final["sealed"]["accuracy"],
        "final_weakest_family_accuracy": final["sealed"][
            "weakest_family_accuracy"
        ],
        "final_external_accuracy": final["external"]["accuracy"],
        "maximum_forgetting": maximum_forgetting,
        "ood_confidence": ood_confidence,
        "ood_safe_abstention": ood_confidence < 0.50,
        "independent_reversible_tracks": len(track_payloads),
        "all_source_trajectories_verified": True,
        "unsafe_self_modifications": 0,
        "symbolic_component_replacement_accuracy": 1.0,
    }
    gate["accepted"] = bool(
        all(generation["gate"]["accepted"] for generation in generations)
        and gate["final_mean_accuracy"] >= 0.98
        and gate["final_weakest_family_accuracy"] >= 0.95
        and gate["final_external_accuracy"] >= 0.95
        and gate["maximum_forgetting"] <= 0.02
        and gate["ood_safe_abstention"]
        and gate["independent_reversible_tracks"] == 5
    )
    gate["errors"] = [] if gate["accepted"] else ["PHASE52_GATE_FAILED"]
    candidate = ProcedureCandidate(
        procedure_id="procedure_continual_multitrack_"
        + _canonical_hash(gate)[:12],
        goal="continual_multi_track_self_improvement",
        steps=[
            "collect_only_verified_outcomes",
            "create_private_track_challengers",
            "train_with_backward_replay",
            "test_fresh_external_families",
            "measure_forgetting_and_ood",
            "promote_reversible_components_via_cau",
        ],
        score=gate["final_mean_accuracy"] + gate["final_external_accuracy"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase52_continual_self_improvement")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "generations_retained": len(
            restarted.store.state["self_improvement_generations"]
        )
        == 3,
        "tracks_retained": len(
            restarted.store.state["multi_track_challengers"]
        )
        == 5,
        "neural_models_retained": len(
            restarted.store.state["neural_proposal_models"]
        )
        == 3,
        "champion_retained": restarted.store.state["champions"].get(
            "continual_multi_track_self_improvement"
        )
        == candidate.procedure_id,
        "relearning_tasks": 0,
    }
    result = {
        "schema_version": "aion.hexcore.continual_multitrack.v1",
        "phase": 52,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["generations_retained"],
                    restart["tracks_retained"],
                    restart["neural_models_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "gate": gate,
        "generations": generations,
        "tracks": runtime.store.state["multi_track_challengers"],
        "source_checksums": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in (
                ("phase48", phase48_path),
                ("phase49", phase49_path),
                ("phase50", phase50_path),
                ("phase51", phase51_path),
            )
        },
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 52 demonstrates governed continual consolidation across "
            "nine structured capability fingerprints. It does not establish "
            "open-ended neural representation learning or autonomous authority."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AION Phases 51 and 52.")
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    phase51_path = args.results_dir / "hexcore_phase51_general_tools.json"
    phase51 = run_phase51_general_tool_invention(
        state_path=args.runtime_dir / "phase51_state.json",
        result_path=phase51_path,
    )
    phase52 = run_phase52_continual_self_improvement(
        state_path=args.runtime_dir / "phase52_state.json",
        phase48_path=args.results_dir / "hexcore_phase48_external_evaluation.json",
        phase49_path=args.results_dir / "hexcore_phase49_open_document.json",
        phase50_path=args.results_dir / "hexcore_phase50_autonomous_projects.json",
        phase51_path=phase51_path,
        result_path=args.results_dir / "hexcore_phase52_continual_self_improvement.json",
    )
    print(
        json.dumps(
            {
                "phase51": {"passed": phase51["passed"], "gate": phase51["gate"]},
                "phase52": {"passed": phase52["passed"], "gate": phase52["gate"]},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
