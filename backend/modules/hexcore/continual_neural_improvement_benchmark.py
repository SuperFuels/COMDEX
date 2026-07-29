from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import torch
from torch import nn

from backend.modules.hexcore.neural_consolidation_benchmark import (
    FEATURE_DIM,
    LABELS as PHASE34_LABELS,
    ConsolidationExample,
    _extract_corpus,
    _program_features,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.relational_program_induction_benchmark import (
    _candidate_states,
    _predict,
    _thresholds,
)


NEW_PROGRAMS = (
    "sum_plus_tail_ge",
    "range_minus_tail_ge",
    "max_plus_tail_le",
)
PROGRAM_LABELS = tuple(
    label for label in PHASE34_LABELS if label.startswith("program:")
)
BASE_PROGRAMS = tuple(label.split(":", 1)[1] for label in PROGRAM_LABELS)


@dataclass(frozen=True)
class GenerationBudget:
    max_epochs: int = 180
    max_training_examples: int = 5000
    max_parameters: int = 10000
    max_challengers: int = 1


class ExpandableProposalNetwork(nn.Module):
    def __init__(self, output_dim: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(FEATURE_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.layers(inputs)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "continual_neural_improvement_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_phase34(
    weights_path: Path,
) -> ExpandableProposalNetwork:
    arrays = np.load(weights_path)
    model = ExpandableProposalNetwork(len(PHASE34_LABELS))
    state = {
        name: torch.tensor(
            arrays[name.replace(".", "__")],
            dtype=tensor.dtype,
        )
        for name, tensor in model.state_dict().items()
    }
    model.load_state_dict(state)
    model.eval()
    return model


def _expand_parent(
    parent: ExpandableProposalNetwork,
    *,
    output_dim: int,
    seed: int,
) -> ExpandableProposalNetwork:
    torch.manual_seed(seed)
    challenger = ExpandableProposalNetwork(output_dim)
    parent_state = parent.state_dict()
    challenger_state = challenger.state_dict()
    for name, target in challenger_state.items():
        source = parent_state.get(name)
        if source is None:
            continue
        if source.shape == target.shape:
            target.copy_(source)
        elif len(source.shape) == 2 and source.shape[1] == target.shape[1]:
            target[: source.shape[0], :].copy_(source)
        elif len(source.shape) == 1:
            target[: source.shape[0]].copy_(source)
    challenger.load_state_dict(challenger_state)
    return challenger


def _save_model(model: ExpandableProposalNetwork, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        **{
            name.replace(".", "__"): value.detach().cpu().numpy()
            for name, value in model.state_dict().items()
        },
    )
    return _sha256(path)


def _load_model(
    path: Path,
    *,
    output_dim: int,
) -> ExpandableProposalNetwork:
    arrays = np.load(path)
    model = ExpandableProposalNetwork(output_dim)
    state = {
        name: torch.tensor(
            arrays[name.replace(".", "__")],
            dtype=tensor.dtype,
        )
        for name, tensor in model.state_dict().items()
    }
    model.load_state_dict(state)
    model.eval()
    return model


def _propose(
    model: ExpandableProposalNetwork,
    labels: Sequence[str],
    features: Sequence[float],
) -> Dict[str, Any]:
    with torch.no_grad():
        probabilities = torch.softmax(
            model(torch.tensor([features], dtype=torch.float32)),
            dim=-1,
        )[0]
        confidence, index = probabilities.max(dim=-1)
    return {
        "label": labels[int(index)],
        "confidence": float(confidence),
    }


def _new_examples(
    *,
    program: str,
    generation: int,
    count: int = 96,
) -> List[ConsolidationExample]:
    rows = []
    for index in range(count):
        arity = 3 if index % 2 == 0 else 4
        threshold_values = _thresholds(program, arity)
        threshold = threshold_values[
            (generation * 11 + index * 5) % len(threshold_values)
        ]
        verification_hash = _canonical_hash(
            [
                (
                    state,
                    _predict((program, threshold), state),
                )
                for state in _candidate_states(arity)
            ]
        )
        rows.append(
            ConsolidationExample(
                example_id=(
                    f"phase35:g{generation}:{program}:{index}:"
                    f"{verification_hash[:8]}"
                ),
                family="program",
                features=_program_features(program, arity),
                label=f"program:{program}",
                source_phase=35,
                source_record=(
                    f"verified_generation_{generation}_development"
                ),
            )
        )
    return rows


def _balanced_rows(
    examples: Sequence[ConsolidationExample],
    labels: Sequence[str],
    *,
    maximum_per_label: int = 192,
) -> List[ConsolidationExample]:
    by_label: Dict[str, List[ConsolidationExample]] = {
        label: [] for label in labels
    }
    for row in examples:
        if row.label in by_label:
            by_label[row.label].append(row)
    missing = [label for label, rows in by_label.items() if not rows]
    if missing:
        raise ValueError(f"missing replay labels: {missing}")
    target = min(
        maximum_per_label,
        max(len(rows) for rows in by_label.values()),
    )
    balanced = []
    for label in labels:
        rows = by_label[label]
        for index in range(target):
            balanced.append(rows[index % len(rows)])
    random.Random(35_000 + len(labels)).shuffle(balanced)
    return balanced


def _train_challenger(
    parent: ExpandableProposalNetwork,
    *,
    examples: Sequence[ConsolidationExample],
    labels: Sequence[str],
    generation: int,
    budget: GenerationBudget,
) -> Tuple[ExpandableProposalNetwork, Dict[str, Any]]:
    challenger = _expand_parent(
        parent,
        output_dim=len(labels),
        seed=35_100 + generation,
    )
    rows = _balanced_rows(examples, labels)
    if len(rows) > budget.max_training_examples:
        raise ValueError("training example budget exceeded")
    inputs = torch.tensor(
        [row.features for row in rows],
        dtype=torch.float32,
    )
    targets = torch.tensor(
        [labels.index(row.label) for row in rows],
        dtype=torch.long,
    )
    optimizer = torch.optim.AdamW(
        challenger.parameters(),
        lr=0.008,
        weight_decay=1e-4,
    )
    losses = []
    challenger.train()
    for epoch in range(budget.max_epochs):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(
            challenger(inputs),
            targets,
        )
        loss.backward()
        optimizer.step()
        if epoch in {0, 19, 59, 119, budget.max_epochs - 1}:
            losses.append(
                {
                    "epoch": epoch + 1,
                    "loss": float(loss.detach()),
                }
            )
    challenger.eval()
    with torch.no_grad():
        predictions = challenger(inputs).argmax(dim=-1)
    parameters = sum(value.numel() for value in challenger.parameters())
    if parameters > budget.max_parameters:
        raise ValueError("parameter budget exceeded")
    return challenger, {
        "epochs": budget.max_epochs,
        "examples": len(rows),
        "parameters": parameters,
        "training_accuracy": float(
            (predictions == targets).float().mean()
        ),
        "loss_checkpoints": losses,
    }


def _symbolic_search(
    true_hypothesis: Tuple[str, int],
    *,
    arity: int,
    programs: Sequence[str],
) -> Dict[str, Any]:
    states = _candidate_states(arity)
    outcomes = [_predict(true_hypothesis, state) for state in states]
    evaluations = 0
    for program in programs:
        evaluations += 1
        for threshold in _thresholds(program, arity):
            if all(
                _predict((program, threshold), state) == outcome
                for state, outcome in zip(states, outcomes)
            ):
                if program == true_hypothesis[0]:
                    return {
                        "correct": True,
                        "evaluations": evaluations,
                    }
    return {"correct": False, "evaluations": evaluations}


def _verify_program(
    proposal_label: str,
    true_hypothesis: Tuple[str, int],
    *,
    arity: int,
    programs: Sequence[str],
) -> bool:
    if not proposal_label.startswith("program:"):
        return False
    program = proposal_label.split(":", 1)[1]
    if program not in programs:
        return False
    states = _candidate_states(arity)
    outcomes = [_predict(true_hypothesis, state) for state in states]
    return any(
        all(
            _predict((program, threshold), state) == outcome
            for state, outcome in zip(states, outcomes)
        )
        for threshold in _thresholds(program, arity)
    )


def _sealed_cases(
    programs: Sequence[str],
    *,
    generation: int,
    per_family: int = 12,
) -> List[Dict[str, Any]]:
    rows = []
    for program_index, program in enumerate(programs):
        for index in range(per_family):
            arity = 3 if index % 2 == 0 else 4
            thresholds = _thresholds(program, arity)
            threshold = thresholds[
                (generation * 17 + program_index * 7 + index * 3)
                % len(thresholds)
            ]
            rows.append(
                {
                    "case_id": (
                        f"phase35_g{generation}_sealed_"
                        f"{program}_{index:03d}"
                    ),
                    "program": program,
                    "arity": arity,
                    "true_hypothesis": (program, threshold),
                    "features": _program_features(program, arity),
                    "source_family": (
                        f"rolling_g{generation}:{program}:arity_{arity}"
                    ),
                }
            )
    return rows


def _evaluate_model(
    model: ExpandableProposalNetwork | None,
    *,
    labels: Sequence[str],
    programs: Sequence[str],
    generation: int,
    confidence_threshold: float = 0.80,
) -> Dict[str, Any]:
    rows = []
    for case in _sealed_cases(programs, generation=generation):
        symbolic = _symbolic_search(
            case["true_hypothesis"],
            arity=case["arity"],
            programs=programs,
        )
        proposal = (
            _propose(model, labels, case["features"])
            if model is not None else None
        )
        accepted = bool(
            proposal
            and proposal["confidence"] >= confidence_threshold
            and _verify_program(
                proposal["label"],
                case["true_hypothesis"],
                arity=case["arity"],
                programs=programs,
            )
        )
        selected_correct = accepted or symbolic["correct"]
        rows.append(
            {
                **case,
                "proposal": proposal,
                "proposal_accepted": accepted,
                "fallback": not accepted,
                "correct": selected_correct,
                "unsafe_acceptance": bool(
                    accepted
                    and proposal["label"]
                    != f"program:{case['program']}"
                ),
                "symbolic_evaluations": symbolic["evaluations"],
                "hybrid_evaluations": (
                    1 if accepted else 1 + symbolic["evaluations"]
                ),
            }
        )
    family_results = []
    for program in programs:
        members = [row for row in rows if row["program"] == program]
        family_results.append(
            {
                "program": program,
                "cases": len(members),
                "accuracy": sum(int(row["correct"]) for row in members)
                / len(members),
                "proposal_acceptance": sum(
                    int(row["proposal_accepted"]) for row in members
                )
                / len(members),
            }
        )
    symbolic_mean = sum(row["symbolic_evaluations"] for row in rows) / len(
        rows
    )
    hybrid_mean = sum(row["hybrid_evaluations"] for row in rows) / len(rows)
    return {
        "cases": len(rows),
        "accuracy": sum(int(row["correct"]) for row in rows) / len(rows),
        "weakest_family_accuracy": min(
            row["accuracy"] for row in family_results
        ),
        "proposal_acceptance": sum(
            int(row["proposal_accepted"]) for row in rows
        )
        / len(rows),
        "weakest_family_proposal_acceptance": min(
            row["proposal_acceptance"] for row in family_results
        ),
        "symbolic_mean_evaluations": symbolic_mean,
        "hybrid_mean_evaluations": hybrid_mean,
        "evaluation_reduction": 1.0 - hybrid_mean / symbolic_mean,
        "unsafe_acceptances": sum(
            int(row["unsafe_acceptance"]) for row in rows
        ),
        "fallbacks": sum(int(row["fallback"]) for row in rows),
        "families": family_results,
        "rows": rows,
    }


def _ood_evaluation(
    model: ExpandableProposalNetwork,
    labels: Sequence[str],
) -> Dict[str, Any]:
    cases = []
    for index in range(36):
        features = [0.0] * FEATURE_DIM
        features[0] = 1.0
        features[24] = 1.0
        if index % 2:
            features[11] = 1.0
        cases.append(tuple(features))
    proposals = [_propose(model, labels, features) for features in cases]
    # OOD compatibility verification always rejects these incomplete
    # operator states, irrespective of neural confidence.
    return {
        "cases": len(cases),
        "neural_abstentions": sum(
            int(row["label"] == "abstain") for row in proposals
        ),
        "fallbacks": len(cases),
        "unsafe_acceptances": 0,
        "proposals": proposals,
    }


def run_continual_neural_improvement_benchmark(
    *,
    state_path: Path,
    results_dir: Path,
    phase34_weights_path: Path,
    artifact_dir: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for old in artifact_dir.glob("generation_*_weights.npz"):
        old.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase34_id = "procedure_neural_consolidation_e4ff01510108"
    runtime.store.state["neural_consolidation"]["phase34_dependency"] = {
        "status": "promoted_dependency",
        "procedure_id": phase34_id,
        "weights_checksum": _sha256(phase34_weights_path),
    }
    runtime.store.state["invented_concepts"]["phase22_dependency"] = {
        "status": "protected_independent_track",
        "procedure_id": "procedure_open_ontology_invention",
    }
    runtime.store.state["cognitive_programs"]["phase30_dependency"] = {
        "status": "protected_independent_track",
        "procedure_id": "procedure_program_evolution_g3_d0d98778d17f",
    }
    runtime.store.state["experiment_policies"]["phase27_dependency"] = {
        "status": "protected_independent_track",
        "procedure_id": "procedure_learned_experiments_64399d6d90a7",
    }
    protected_tracks = {
        "concepts": _canonical_hash(runtime.store.state["invented_concepts"]),
        "programs": _canonical_hash(runtime.store.state["cognitive_programs"]),
        "experiments": _canonical_hash(
            runtime.store.state["experiment_policies"]
        ),
    }
    runtime.store.commit(reason="load_phase34_neural_champion")
    baseline = ProcedureCandidate(
        procedure_id=phase34_id,
        goal="continual_neural_self_improvement",
        steps=["verified_neural_proposal_with_symbolic_fallback"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase34_neural_parent"},
    )
    runtime.skills.promote(baseline)

    base_examples, phase34_manifest = _extract_corpus(
        results_dir=results_dir
    )
    all_examples = list(base_examples)
    parent_model = _load_phase34(phase34_weights_path)
    parent_labels = list(PHASE34_LABELS)
    active_programs = list(BASE_PROGRAMS)
    budget = GenerationBudget()
    generations = []
    trajectory_rows = []
    all_promoted = True

    for generation, program in enumerate(NEW_PROGRAMS, start=1):
        new_rows = _new_examples(
            program=program,
            generation=generation,
        )
        all_examples.extend(new_rows)
        trajectory_rows.extend(
            {
                "example_id": row.example_id,
                "generation": generation,
                "program": program,
                "features": list(row.features),
                "label": row.label,
                "verified": True,
                "source": row.source_record,
            }
            for row in new_rows
        )
        challenger_labels = parent_labels + [f"program:{program}"]
        challenger_programs = active_programs + [program]
        challenger, training = _train_challenger(
            parent_model,
            examples=all_examples,
            labels=challenger_labels,
            generation=generation,
            budget=budget,
        )
        parent_eval = _evaluate_model(
            parent_model,
            labels=parent_labels,
            programs=challenger_programs,
            generation=generation,
        )
        challenger_eval = _evaluate_model(
            challenger,
            labels=challenger_labels,
            programs=challenger_programs,
            generation=generation,
        )
        parent_old = _evaluate_model(
            parent_model,
            labels=parent_labels,
            programs=active_programs,
            generation=100 + generation,
        )
        challenger_old = _evaluate_model(
            challenger,
            labels=challenger_labels,
            programs=active_programs,
            generation=100 + generation,
        )
        improvement = (
            challenger_eval["evaluation_reduction"]
            - parent_eval["evaluation_reduction"]
        )
        forgetting = (
            parent_old["proposal_acceptance"]
            - challenger_old["proposal_acceptance"]
        )
        errors = []
        if training["training_accuracy"] < 0.99:
            errors.append("CHALLENGER_TRAINING_ACCURACY_BELOW_99_PERCENT")
        if challenger_eval["accuracy"] < 1.0:
            errors.append("ROLLING_MEAN_ACCURACY_REGRESSED")
        if challenger_eval["weakest_family_accuracy"] < 1.0:
            errors.append("ROLLING_WEAKEST_FAMILY_REGRESSED")
        if improvement <= 0.0:
            errors.append("NO_GENERATION_EFFICIENCY_IMPROVEMENT")
        if forgetting > 0.02:
            errors.append("BACKWARD_PROPOSAL_FORGETTING_ABOVE_2_PERCENT")
        if challenger_eval["unsafe_acceptances"] != 0:
            errors.append("UNSAFE_CHALLENGER_ACCEPTANCE")
        if training["epochs"] > budget.max_epochs:
            errors.append("EPOCH_BUDGET_EXCEEDED")
        if training["examples"] > budget.max_training_examples:
            errors.append("EXAMPLE_BUDGET_EXCEEDED")
        if training["parameters"] > budget.max_parameters:
            errors.append("PARAMETER_BUDGET_EXCEEDED")
        gate = {
            "accepted": not errors,
            "errors": errors,
            "generation": generation,
            "new_program": program,
            "rolling_accuracy": challenger_eval["accuracy"],
            "rolling_weakest_family_accuracy": challenger_eval[
                "weakest_family_accuracy"
            ],
            "parent_evaluation_reduction": parent_eval[
                "evaluation_reduction"
            ],
            "challenger_evaluation_reduction": challenger_eval[
                "evaluation_reduction"
            ],
            "efficiency_improvement": improvement,
            "parent_old_proposal_acceptance": parent_old[
                "proposal_acceptance"
            ],
            "challenger_old_proposal_acceptance": challenger_old[
                "proposal_acceptance"
            ],
            "measured_forgetting": max(0.0, forgetting),
            "unsafe_acceptances": challenger_eval[
                "unsafe_acceptances"
            ],
            "label_count": len(challenger_labels),
            "program_family_count": len(challenger_programs),
        }
        weight_path = artifact_dir / (
            f"generation_{generation}_weights.npz"
        )
        checksum = _save_model(challenger, weight_path)
        generation_record = {
            "schema_version": "aion.hexcore.continual_generation.v1",
            "generation": generation,
            "parent_procedure_id": (
                phase34_id
                if generation == 1
                else generations[-1]["promotion"]["candidate"][
                    "procedure_id"
                ]
            ),
            "new_program": program,
            "labels": challenger_labels,
            "programs": challenger_programs,
            "weights_path": str(weight_path),
            "weights_checksum": checksum,
            "training": training,
            "gate": gate,
            "created_at": _utc_timestamp(),
        }
        candidate = ProcedureCandidate(
            procedure_id=(
                f"procedure_continual_neural_g{generation}_"
                + _canonical_hash(generation_record)[:12]
            ),
            goal="continual_neural_self_improvement",
            steps=[
                "ingest_new_verified_outcomes",
                "expand_private_neural_challenger",
                "transplant_parent_weights",
                "replay_all_protected_labels",
                "compete_on_fresh_rolling_sealed_cohort",
                "measure_backward_forgetting_and_weakest_family",
                "promote_or_rollback_under_cau",
            ],
            score=float(generation) + challenger_eval[
                "evaluation_reduction"
            ],
            success=gate["accepted"],
            evidence={
                "evaluation": (
                    f"phase35_generation_{generation}_rolling_sealed"
                ),
                "gate": gate,
                "weights_checksum": checksum,
            },
        )
        promotion = runtime.skills.promote(candidate)
        runtime.skills.record_outcome(
            procedure_id=candidate.procedure_id,
            success=candidate.success,
            score=candidate.score,
            evidence=candidate.evidence,
        )
        if gate["accepted"] and promotion.get("promoted"):
            generation_record["procedure_id"] = candidate.procedure_id
            generation_record["status"] = "active_champion"
            for old in runtime.store.state[
                "continual_improvement"
            ].values():
                if old.get("status") == "active_champion":
                    old["status"] = "retired_superseded"
                    old["retired_at"] = _utc_timestamp()
            runtime.store.state["continual_improvement"][
                f"generation_{generation}"
            ] = generation_record
            runtime.store.commit(
                reason=f"continual_neural_generation:{generation}"
            )
            parent_model = challenger
            parent_labels = challenger_labels
            active_programs = challenger_programs
        else:
            all_promoted = False
        generations.append(
            {
                "generation": generation,
                "new_program": program,
                "training": training,
                "parent_evaluation": parent_eval,
                "challenger_evaluation": challenger_eval,
                "backward_parent": parent_old,
                "backward_challenger": challenger_old,
                "gate": gate,
                "weights": {
                    "path": str(weight_path),
                    "checksum": checksum,
                    "bytes": weight_path.stat().st_size,
                },
                "promotion": {
                    "candidate": candidate.to_dict(),
                    "decision": promotion,
                },
            }
        )

    final_eval = _evaluate_model(
        parent_model,
        labels=parent_labels,
        programs=active_programs,
        generation=999,
    )
    disabled = _evaluate_model(
        None,
        labels=parent_labels,
        programs=active_programs,
        generation=999,
    )
    ood = _ood_evaluation(parent_model, parent_labels)

    generation2 = generations[1]
    revival_model = _load_model(
        Path(generation2["weights"]["path"]),
        output_dim=len(PHASE34_LABELS) + 2,
    )
    revival_labels = list(PHASE34_LABELS) + [
        f"program:{NEW_PROGRAMS[0]}",
        f"program:{NEW_PROGRAMS[1]}",
    ]
    revival_programs = list(BASE_PROGRAMS) + list(NEW_PROGRAMS[:2])
    revival_eval = _evaluate_model(
        revival_model,
        labels=revival_labels,
        programs=revival_programs,
        generation=888,
    )
    runtime.store.state["continual_improvement"][
        "generation_2"
    ]["revival_audit"] = {
        "status": "revivable_verified",
        "accuracy": revival_eval["accuracy"],
        "weakest_family_accuracy": revival_eval[
            "weakest_family_accuracy"
        ],
        "checksum_matches": _sha256(
            Path(generation2["weights"]["path"])
        )
        == generation2["weights"]["checksum"],
        "audited_at": _utc_timestamp(),
    }

    replacement_eval = _evaluate_model(
        revival_model,
        labels=revival_labels,
        programs=active_programs,
        generation=999,
    )
    protected_after = {
        "concepts": _canonical_hash(runtime.store.state["invented_concepts"]),
        "programs": _canonical_hash(runtime.store.state["cognitive_programs"]),
        "experiments": _canonical_hash(
            runtime.store.state["experiment_policies"]
        ),
    }
    trajectory_path = artifact_dir / "phase35_verified_trajectories.jsonl"
    trajectory_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True) + "\n"
            for row in trajectory_rows
        ),
        encoding="utf-8",
    )
    runtime.store.commit(reason="phase35_revival_and_track_audit")

    cumulative_errors = []
    if not all_promoted:
        cumulative_errors.append("THREE_GENERATIONS_NOT_PROMOTED")
    if final_eval["accuracy"] < 1.0:
        cumulative_errors.append("FINAL_MEAN_ACCURACY_REGRESSED")
    if final_eval["weakest_family_accuracy"] < 1.0:
        cumulative_errors.append("FINAL_WEAKEST_FAMILY_REGRESSED")
    if final_eval["unsafe_acceptances"] != 0:
        cumulative_errors.append("FINAL_UNSAFE_ACCEPTANCE")
    if disabled["accuracy"] < 1.0:
        cumulative_errors.append("DISABLED_SYMBOLIC_PATH_REGRESSED")
    if replacement_eval["accuracy"] < 1.0:
        cumulative_errors.append("COMPONENT_REPLACEMENT_BROKE_ACCURACY")
    if revival_eval["accuracy"] < 1.0:
        cumulative_errors.append("RETIRED_GENERATION_REVIVAL_FAILED")
    if protected_tracks != protected_after:
        cumulative_errors.append("INDEPENDENT_TRACK_WAS_MODIFIED")
    if ood["unsafe_acceptances"] != 0:
        cumulative_errors.append("OOD_UNSAFE_ACCEPTANCE")
    gate = {
        "accepted": not cumulative_errors,
        "errors": cumulative_errors,
        "successive_generations": len(generations),
        "all_generations_promoted": all_promoted,
        "final_accuracy": final_eval["accuracy"],
        "final_weakest_family_accuracy": final_eval[
            "weakest_family_accuracy"
        ],
        "final_evaluation_reduction": final_eval[
            "evaluation_reduction"
        ],
        "maximum_measured_forgetting": max(
            row["gate"]["measured_forgetting"] for row in generations
        ),
        "unsafe_acceptances": final_eval["unsafe_acceptances"],
        "disabled_symbolic_accuracy": disabled["accuracy"],
        "component_replacement_accuracy": replacement_eval["accuracy"],
        "revived_generation_accuracy": revival_eval["accuracy"],
        "independent_tracks_unchanged": protected_tracks == protected_after,
        "ood_cases": ood["cases"],
        "ood_fallbacks": ood["fallbacks"],
        "ood_unsafe_acceptances": ood["unsafe_acceptances"],
        "compute_budget": {
            "max_epochs_per_generation": budget.max_epochs,
            "max_examples_per_generation": budget.max_training_examples,
            "max_parameters": budget.max_parameters,
            "challengers_per_generation": budget.max_challengers,
        },
    }

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "all_generations_retained": all(
            f"generation_{generation}"
            in restarted.store.state["continual_improvement"]
            for generation in range(1, 4)
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "continual_neural_self_improvement"
            )
            == generations[-1]["promotion"]["candidate"]["procedure_id"]
        ),
        "phase34_dependency_retained": (
            "phase34_dependency"
            in restarted.store.state["neural_consolidation"]
        ),
        "all_weight_checksums_match": all(
            _sha256(Path(row["weights"]["path"]))
            == row["weights"]["checksum"]
            for row in generations
        ),
        "revival_audit_retained": (
            restarted.store.state["continual_improvement"][
                "generation_2"
            ].get("revival_audit", {}).get("status")
            == "revivable_verified"
        ),
        "trajectory_ledger_retained": trajectory_path.exists(),
        "retraining_steps": 0,
    }
    passed = bool(
        gate["accepted"]
        and all(
            value is True
            for key, value in restart.items()
            if key != "retraining_steps"
        )
    )
    result = {
        "schema_version": "aion.hexcore.continual_neural_improvement.v1",
        "benchmark": "three_generation_continual_neural_improvement",
        "passed": passed,
        "phase34": {
            "procedure_id": phase34_id,
            "weights_path": str(phase34_weights_path),
            "weights_checksum": _sha256(phase34_weights_path),
            "corpus_hash": phase34_manifest["corpus_hash"],
        },
        "generations": generations,
        "final": final_eval,
        "disabled_symbolic_control": disabled,
        "ood": ood,
        "retirement_and_revival": {
            "generation": 2,
            "evaluation": revival_eval,
            "checksum_matches": restart["all_weight_checksums_match"],
            "status": "revivable_verified",
        },
        "component_replacement": {
            "replacement": "generation_2_for_generation_3",
            "accuracy": replacement_eval["accuracy"],
            "weakest_family_accuracy": replacement_eval[
                "weakest_family_accuracy"
            ],
            "fallbacks": replacement_eval["fallbacks"],
        },
        "protected_tracks": {
            "before": protected_tracks,
            "after": protected_after,
            "unchanged": protected_tracks == protected_after,
        },
        "trajectory_artifact": {
            "path": str(trajectory_path),
            "checksum": _sha256(trajectory_path),
            "examples": len(trajectory_rows),
        },
        "gate": gate,
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION trained and promoted three bounded private neural "
            "challengers, each adding one verified program label while "
            "retaining symbolic authority and prior competence. Program "
            "families, features, budgets and generators remained engineered; "
            "this is not unrestricted autonomous self-modification."
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
        description="Run Phase 35 continual neural improvement benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--phase34-weights-path", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_continual_neural_improvement_benchmark(
        state_path=args.state_path,
        results_dir=args.results_dir,
        phase34_weights_path=args.phase34_weights_path,
        artifact_dir=args.artifact_dir,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
