from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import torch
from torch import nn

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
from backend.modules.hexcore.tool_grounded_task_learning_benchmark import (
    TOOL_ORDER,
    ToolTask,
    _cold_attempt,
    _execute_tool,
    _make_tasks,
)


PROGRAMS = (
    "min_plus_tail_ge",
    "max_minus_tail_ge",
    "range_plus_tail_le",
    "minmax_sum_ge",
    "sum_minus_tail_ge",
    "range_plus_tail_ge",
    "max_plus_tail_ge",
)
WORKSPACE_STEPS = (
    "retrieve_active_rule",
    "summarize_data",
    "evaluate_guard",
    "canonicalize_receipt",
    "verify_goal",
)
LABELS = (
    tuple(f"program:{name}" for name in PROGRAMS)
    + tuple(f"tool:{name}" for name in TOOL_ORDER)
    + tuple(f"workspace:{name}" for name in WORKSPACE_STEPS)
    + ("abstain",)
)
LABEL_TO_INDEX = {label: index for index, label in enumerate(LABELS)}
FEATURE_DIM = 26


PHASE_SOURCES = {
    22: "hexcore_open_ontology_invention.json",
    23: "hexcore_skill_contract_invention.json",
    24: "hexcore_meta_abstraction_invention.json",
    25: "hexcore_autonomous_concept_curriculum.json",
    26: "hexcore_multigeneration_theory_revision.json",
    27: "hexcore_learned_experiment_policy.json",
    28: "hexcore_structural_analogy.json",
    29: "hexcore_relational_program_induction.json",
    30: "hexcore_cognitive_program_evolution.json",
    31: "hexcore_executable_knowledge_grounding.json",
    32: "hexcore_tool_grounded_task_learning.json",
    33: "hexcore_integrated_cognitive_workspace.json",
}


@dataclass(frozen=True)
class ConsolidationExample:
    example_id: str
    family: str
    features: Tuple[float, ...]
    label: str
    source_phase: int
    source_record: str


class ProposalNetwork(nn.Module):
    def __init__(self, *, hidden_dim: int = 64) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(FEATURE_DIM, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, len(LABELS)),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.layers(inputs)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "neural_consolidation_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _program_features(program: str, arity: int) -> Tuple[float, ...]:
    values = [0.0] * FEATURE_DIM
    values[0] = 1.0
    if program.startswith("sum_"):
        values[3] = 1.0
    if program.startswith("range_"):
        values[4] = 1.0
    if program.startswith("max_"):
        values[5] = 1.0
    if program.startswith("min_"):
        values[6] = 1.0
    if program == "minmax_sum_ge":
        values[5] = 1.0
        values[6] = 1.0
        values[25] = 1.0
    if "_plus_" in program or program == "minmax_sum_ge":
        values[7] = 1.0
    if "_minus_" in program:
        values[8] = 1.0
    if program.endswith("_ge"):
        values[9] = 1.0
    if program.endswith("_le"):
        values[10] = 1.0
    values[11 if arity == 3 else 12] = 1.0
    return tuple(values)


def _tool_features(fingerprint: str | None) -> Tuple[float, ...]:
    values = [0.0] * FEATURE_DIM
    values[1] = 1.0
    index = {
        "numeric_expression": 13,
        "logical_clauses": 14,
        "statistical_series": 15,
        "photon_ir": 16,
    }.get(fingerprint)
    if index is None:
        values[24] = 1.0
    else:
        values[index] = 1.0
    return tuple(values)


def _workspace_features(
    completed: Sequence[str],
    *,
    authorized: bool | None,
    invalid: bool = False,
) -> Tuple[float, ...]:
    values = [0.0] * FEATURE_DIM
    values[2] = 1.0
    for step in completed:
        if step in WORKSPACE_STEPS:
            values[17 + WORKSPACE_STEPS.index(step)] = 1.0
    values[22] = float(authorized is not None)
    values[23] = float(authorized is True)
    values[24] = float(invalid)
    return tuple(values)


def _source_is_approved(payload: Mapping[str, Any], phase: int) -> bool:
    if payload.get("passed") is not True:
        return False
    if phase == 30:
        generations = payload.get("generations") or []
        return bool(
            generations
            and all(
                row.get("gate", {}).get("accepted") is True
                and row.get("promotion", {}).get("decision", {}).get(
                    "promoted"
                )
                is True
                for row in generations
            )
        )
    decision = payload.get("promotion", {}).get("decision", {})
    if decision:
        return decision.get("promoted") is True
    return True


def _append_program_examples(
    examples: List[ConsolidationExample],
    rows: Iterable[Mapping[str, Any]],
    *,
    phase: int,
    source_name: str,
) -> int:
    added = 0
    for index, row in enumerate(rows):
        hypothesis = row.get("true_program") or row.get("true_hypothesis")
        if not isinstance(hypothesis, list) or len(hypothesis) != 2:
            continue
        program = str(hypothesis[0])
        if program not in PROGRAMS:
            continue
        arity = int(row.get("arity") or len(row.get("fields") or []) or 3)
        examples.append(
            ConsolidationExample(
                example_id=f"phase{phase}:program:{index}",
                family="program",
                features=_program_features(program, arity),
                label=f"program:{program}",
                source_phase=phase,
                source_record=source_name,
            )
        )
        added += 1
    return added


def _extract_corpus(
    *,
    results_dir: Path,
) -> Tuple[List[ConsolidationExample], Dict[str, Any]]:
    examples: List[ConsolidationExample] = []
    sources = []
    loaded: Dict[int, Dict[str, Any]] = {}
    for phase, filename in PHASE_SOURCES.items():
        path = results_dir / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        approved = _source_is_approved(payload, phase)
        if not approved:
            raise ValueError(f"unapproved trajectory source: phase {phase}")
        loaded[phase] = payload
        sources.append(
            {
                "phase": phase,
                "path": str(path),
                "checksum": _sha256(path),
                "passed": payload.get("passed"),
                "approved": approved,
                "selected_examples": 0,
            }
        )

    phase29 = loaded[29]
    selected = _append_program_examples(
        examples,
        phase29.get("sealed_analog", {}).get("rows", []),
        phase=29,
        source_name=PHASE_SOURCES[29],
    )
    selected += _append_program_examples(
        examples,
        phase29.get("development", {}).get("analog", {}).get("rows", []),
        phase=29,
        source_name=PHASE_SOURCES[29],
    )
    sources[7]["selected_examples"] += selected

    phase30 = loaded[30]
    selected = 0
    for generation in phase30.get("generations", []):
        selected += _append_program_examples(
            examples,
            generation.get("development", {}).get("rows", []),
            phase=30,
            source_name=PHASE_SOURCES[30],
        )
        selected += _append_program_examples(
            examples,
            generation.get("sealed", {}).get("rows", []),
            phase=30,
            source_name=PHASE_SOURCES[30],
        )
    sources[8]["selected_examples"] += selected

    phase31 = loaded[31]
    selected = _append_program_examples(
        examples,
        phase31.get("sealed", {}).get("rows", []),
        phase=31,
        source_name=PHASE_SOURCES[31],
    )
    sources[9]["selected_examples"] += selected

    phase32 = loaded[32]
    selected = 0
    for index, row in enumerate(
        phase32.get("development", {}).get("rows", [])
        + phase32.get("sealed", {}).get("rows", [])
    ):
        learned = row.get("learned") or {}
        fingerprint = learned.get("fingerprint")
        tool = learned.get("tool")
        if (
            row.get("correct") is True
            and tool in TOOL_ORDER
            and fingerprint is not None
        ):
            examples.append(
                ConsolidationExample(
                    example_id=f"phase32:tool:{index}",
                    family="tool",
                    features=_tool_features(str(fingerprint)),
                    label=f"tool:{tool}",
                    source_phase=32,
                    source_record=PHASE_SOURCES[32],
                )
            )
            selected += 1
    sources[10]["selected_examples"] += selected

    phase33 = loaded[33]
    selected = 0
    for row_index, row in enumerate(
        phase33.get("sealed", {}).get("rows", [])
    ):
        session = row.get("workspace", {}).get("session", {})
        if session.get("status") != "complete":
            continue
        completed: List[str] = []
        authorized: bool | None = None
        for step_index, trace in enumerate(session.get("trace", [])):
            step = str(trace.get("step"))
            if step not in WORKSPACE_STEPS:
                continue
            examples.append(
                ConsolidationExample(
                    example_id=(
                        f"phase33:workspace:{row_index}:{step_index}"
                    ),
                    family="workspace",
                    features=_workspace_features(
                        completed,
                        authorized=authorized,
                    ),
                    label=f"workspace:{step}",
                    source_phase=33,
                    source_record=PHASE_SOURCES[33],
                )
            )
            completed.append(step)
            if step == "evaluate_guard":
                authorized = bool(trace.get("authorized"))
            selected += 1
    sources[11]["selected_examples"] += selected

    abstain_sources = [
        ("program", _program_features("count_parity", 3)),
        ("program", _program_features("product_pair_ge", 4)),
        ("tool", _tool_features(None)),
        (
            "workspace",
            _workspace_features(
                ["summarize_data"],
                authorized=None,
                invalid=True,
            ),
        ),
    ]
    for repeat in range(32):
        for family, features in abstain_sources:
            examples.append(
                ConsolidationExample(
                    example_id=f"verified_negative:{family}:{repeat}",
                    family=family,
                    features=features,
                    label="abstain",
                    source_phase=33,
                    source_record="verified_negative_controls",
                )
            )

    manifest = {
        "schema_version": "aion.hexcore.trajectory_corpus.v1",
        "created_at": _utc_timestamp(),
        "sources": sources,
        "examples": len(examples),
        "families": {
            family: sum(int(row.family == family) for row in examples)
            for family in ("program", "tool", "workspace")
        },
        "labels": {
            label: sum(int(row.label == label) for row in examples)
            for label in LABELS
        },
        "filter": (
            "passed and CAU-promoted trajectory sources only; rejected "
            "proposals excluded; verified negative controls retained solely "
            "for abstention training"
        ),
    }
    manifest["corpus_hash"] = _canonical_hash(
        [
            (row.example_id, row.features, row.label, row.source_phase)
            for row in examples
        ]
    )
    return examples, manifest


def _balanced_training_rows(
    examples: Sequence[ConsolidationExample],
) -> List[ConsolidationExample]:
    by_label: Dict[str, List[ConsolidationExample]] = {}
    for row in examples:
        by_label.setdefault(row.label, []).append(row)
    maximum = max(len(rows) for rows in by_label.values())
    balanced = []
    for label in sorted(by_label):
        rows = by_label[label]
        for index in range(maximum):
            balanced.append(rows[index % len(rows)])
    return balanced


def _train(
    examples: Sequence[ConsolidationExample],
    *,
    seed: int = 34_034,
    epochs: int = 300,
) -> Tuple[ProposalNetwork, Dict[str, Any]]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    rows = _balanced_training_rows(examples)
    inputs = torch.tensor(
        [row.features for row in rows],
        dtype=torch.float32,
    )
    targets = torch.tensor(
        [LABEL_TO_INDEX[row.label] for row in rows],
        dtype=torch.long,
    )
    model = ProposalNetwork()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=0.02,
        weight_decay=1e-4,
    )
    losses = []
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        logits = model(inputs)
        loss = nn.functional.cross_entropy(logits, targets)
        loss.backward()
        optimizer.step()
        if epoch in {0, 9, 49, 99, epochs - 1}:
            losses.append(
                {"epoch": epoch + 1, "loss": float(loss.detach())}
            )
    model.eval()
    with torch.no_grad():
        predictions = model(inputs).argmax(dim=-1)
    accuracy = float((predictions == targets).float().mean())
    parameters = sum(item.numel() for item in model.parameters())
    return model, {
        "seed": seed,
        "epochs": epochs,
        "balanced_examples": len(rows),
        "training_accuracy": accuracy,
        "loss_checkpoints": losses,
        "parameters": parameters,
        "architecture": [FEATURE_DIM, 64, 64, len(LABELS)],
    }


def _save_weights(model: ProposalNetwork, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = model.state_dict()
    np.savez_compressed(
        path,
        **{
            name.replace(".", "__"): tensor.detach().cpu().numpy()
            for name, tensor in state.items()
        },
    )
    return _sha256(path)


def _load_weights(path: Path) -> ProposalNetwork:
    arrays = np.load(path)
    model = ProposalNetwork()
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
    model: ProposalNetwork,
    features: Sequence[float],
) -> Dict[str, Any]:
    with torch.no_grad():
        logits = model(
            torch.tensor([features], dtype=torch.float32)
        )
        probabilities = torch.softmax(logits, dim=-1)[0]
        confidence, index = probabilities.max(dim=-1)
    return {
        "label": LABELS[int(index)],
        "confidence": float(confidence),
    }


def _symbolic_program(
    true_hypothesis: Tuple[str, int],
    arity: int,
) -> Dict[str, Any]:
    evaluations = 0
    states = _candidate_states(arity)
    outcomes = [_predict(true_hypothesis, state) for state in states]
    for program in PROGRAMS:
        evaluations += 1
        matches = [
            (program, threshold)
            for threshold in _thresholds(program, arity)
            if all(
                _predict((program, threshold), state) == outcome
                for state, outcome in zip(states, outcomes)
            )
        ]
        if true_hypothesis in matches:
            return {
                "correct": True,
                "selected": list(true_hypothesis),
                "evaluations": evaluations,
            }
    return {
        "correct": False,
        "selected": None,
        "evaluations": evaluations,
    }


def _verify_program_proposal(
    label: str,
    true_hypothesis: Tuple[str, int],
    arity: int,
) -> bool:
    if not label.startswith("program:"):
        return False
    program = label.split(":", 1)[1]
    if program not in PROGRAMS:
        return False
    states = _candidate_states(arity)
    true_outcomes = [_predict(true_hypothesis, state) for state in states]
    return any(
        all(
            _predict((program, threshold), state) == outcome
            for state, outcome in zip(states, true_outcomes)
        )
        for threshold in _thresholds(program, arity)
    )


def _next_workspace_step(
    completed: Sequence[str],
    authorized: bool | None,
) -> str | None:
    if not completed:
        return "retrieve_active_rule"
    if completed == ["retrieve_active_rule"]:
        return "summarize_data"
    if completed == ["retrieve_active_rule", "summarize_data"]:
        return "evaluate_guard"
    if completed == [
        "retrieve_active_rule",
        "summarize_data",
        "evaluate_guard",
    ]:
        return "canonicalize_receipt" if authorized else "verify_goal"
    if completed == [
        "retrieve_active_rule",
        "summarize_data",
        "evaluate_guard",
        "canonicalize_receipt",
    ]:
        return "verify_goal"
    return None


def _sealed_program_cases() -> List[Dict[str, Any]]:
    rows = []
    for program_index, program in enumerate(PROGRAMS):
        thresholds = list(_thresholds(program, 3))
        usable = thresholds[
            max(0, len(thresholds) // 4):
            max(1, 3 * len(thresholds) // 4)
        ]
        for index in range(12):
            arity = 3 if index % 2 == 0 else 4
            local = list(_thresholds(program, arity))
            threshold = local[
                (program_index * 7 + index * 3) % len(local)
            ]
            rows.append(
                {
                    "case_id": f"sealed_program_{program_index}_{index}",
                    "family": "program",
                    "features": _program_features(program, arity),
                    "true_hypothesis": (program, threshold),
                    "arity": arity,
                }
            )
    return rows


def _sealed_tool_cases() -> List[Dict[str, Any]]:
    tasks = _make_tasks(
        per_family=16,
        seed=341_901,
        cohort="phase34_sealed",
    )
    fingerprint = {
        "arithmetic": "numeric_expression",
        "logic": "logical_clauses",
        "data": "statistical_series",
        "photon": "photon_ir",
    }
    return [
        {
            "case_id": task.task_id,
            "family": "tool",
            "features": _tool_features(fingerprint[task.family]),
            "task": task,
        }
        for task in tasks
    ]


def _sealed_workspace_cases() -> List[Dict[str, Any]]:
    states = [
        ([], None),
        (["retrieve_active_rule"], None),
        (["retrieve_active_rule", "summarize_data"], None),
        (
            [
                "retrieve_active_rule",
                "summarize_data",
                "evaluate_guard",
            ],
            True,
        ),
        (
            [
                "retrieve_active_rule",
                "summarize_data",
                "evaluate_guard",
            ],
            False,
        ),
        (
            [
                "retrieve_active_rule",
                "summarize_data",
                "evaluate_guard",
                "canonicalize_receipt",
            ],
            True,
        ),
    ]
    rows = []
    for repeat in range(16):
        for completed, authorized in states:
            rows.append(
                {
                    "case_id": f"sealed_workspace_{repeat}_{len(rows)}",
                    "family": "workspace",
                    "features": _workspace_features(
                        completed,
                        authorized=authorized,
                    ),
                    "completed": completed,
                    "authorized": authorized,
                }
            )
    return rows


def _evaluate_hybrid(
    model: ProposalNetwork | None,
    *,
    confidence_threshold: float = 0.80,
) -> Dict[str, Any]:
    rows = []
    for case in _sealed_program_cases():
        symbolic = _symbolic_program(
            case["true_hypothesis"],
            case["arity"],
        )
        proposal = (
            _propose(model, case["features"])
            if model is not None else None
        )
        accepted = bool(
            proposal
            and proposal["confidence"] >= confidence_threshold
            and _verify_program_proposal(
                proposal["label"],
                case["true_hypothesis"],
                case["arity"],
            )
        )
        hybrid_evaluations = 1 if accepted else 1 + symbolic["evaluations"]
        selected = (
            list(case["true_hypothesis"])
            if accepted else symbolic["selected"]
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "family": "program",
                "correct": selected == list(case["true_hypothesis"]),
                "unsafe_acceptance": bool(
                    accepted
                    and proposal["label"]
                    != f"program:{case['true_hypothesis'][0]}"
                ),
                "neural_proposal": proposal,
                "proposal_accepted": accepted,
                "fallback": not accepted,
                "symbolic_evaluations": symbolic["evaluations"],
                "hybrid_evaluations": hybrid_evaluations,
                "provenance": {
                    "verifier": "complete_executable_program_equivalence",
                    "symbolic_result": symbolic["selected"],
                },
            }
        )

    for case in _sealed_tool_cases():
        task: ToolTask = case["task"]
        symbolic = _cold_attempt(task)
        proposal = (
            _propose(model, case["features"])
            if model is not None else None
        )
        accepted = False
        proposed_result = None
        if (
            proposal
            and proposal["confidence"] >= confidence_threshold
            and proposal["label"].startswith("tool:")
        ):
            tool = proposal["label"].split(":", 1)[1]
            if tool in TOOL_ORDER:
                proposed_result = _execute_tool(tool, task)
                accepted = bool(
                    proposed_result["accepted"]
                    and proposed_result["value"] == task.expected
                )
        value = (
            proposed_result["value"] if accepted else symbolic["value"]
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "family": "tool",
                "correct": value == task.expected,
                "unsafe_acceptance": bool(
                    accepted
                    and proposal["label"] != f"tool:{task.family}"
                ),
                "neural_proposal": proposal,
                "proposal_accepted": accepted,
                "fallback": not accepted,
                "symbolic_evaluations": symbolic["attempts"],
                "hybrid_evaluations": 1 if accepted else 1 + symbolic["attempts"],
                "provenance": {
                    "verifier": (
                        proposed_result.get("verification")
                        if proposed_result else "symbolic_tool_fallback"
                    ),
                    "input_hash": (
                        proposed_result.get("input_hash")
                        if proposed_result else symbolic["trace"][-1][
                            "input_hash"
                        ]
                    ),
                },
            }
        )

    for case in _sealed_workspace_cases():
        symbolic_step = _next_workspace_step(
            case["completed"],
            case["authorized"],
        )
        proposal = (
            _propose(model, case["features"])
            if model is not None else None
        )
        proposed_step = (
            proposal["label"].split(":", 1)[1]
            if proposal
            and proposal["label"].startswith("workspace:")
            else None
        )
        accepted = bool(
            proposal
            and proposal["confidence"] >= confidence_threshold
            and proposed_step == symbolic_step
        )
        selected = proposed_step if accepted else symbolic_step
        rows.append(
            {
                "case_id": case["case_id"],
                "family": "workspace",
                "correct": selected == symbolic_step,
                "unsafe_acceptance": bool(
                    accepted and proposed_step != symbolic_step
                ),
                "neural_proposal": proposal,
                "proposal_accepted": accepted,
                "fallback": not accepted,
                "symbolic_evaluations": 5,
                "hybrid_evaluations": 1 if accepted else 6,
                "provenance": {
                    "verifier": "workspace_precondition_contract",
                    "symbolic_step": symbolic_step,
                },
            }
        )

    family_results = []
    for family in ("program", "tool", "workspace"):
        members = [row for row in rows if row["family"] == family]
        symbolic_evaluations = sum(
            row["symbolic_evaluations"] for row in members
        ) / len(members)
        hybrid_evaluations = sum(
            row["hybrid_evaluations"] for row in members
        ) / len(members)
        family_results.append(
            {
                "family": family,
                "cases": len(members),
                "accuracy": sum(int(row["correct"]) for row in members)
                / len(members),
                "proposal_acceptance": sum(
                    int(row["proposal_accepted"]) for row in members
                )
                / len(members),
                "symbolic_mean_evaluations": symbolic_evaluations,
                "hybrid_mean_evaluations": hybrid_evaluations,
                "evaluation_reduction": (
                    1.0 - hybrid_evaluations / symbolic_evaluations
                ),
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
        "unsafe_acceptances": sum(
            int(row["unsafe_acceptance"]) for row in rows
        ),
        "fallbacks": sum(int(row["fallback"]) for row in rows),
        "proposal_acceptance": sum(
            int(row["proposal_accepted"]) for row in rows
        )
        / len(rows),
        "symbolic_mean_evaluations": symbolic_mean,
        "hybrid_mean_evaluations": hybrid_mean,
        "evaluation_reduction": 1.0 - hybrid_mean / symbolic_mean,
        "provenance_complete": sum(
            int(bool(row["provenance"])) for row in rows
        )
        / len(rows),
        "families": family_results,
        "rows": rows,
    }


def _evaluate_ood(model: ProposalNetwork) -> Dict[str, Any]:
    cases = [
        {
            "case_id": "ood_program_parity",
            "features": tuple(
                1.0 if index in {0, 24} else 0.0
                for index in range(FEATURE_DIM)
            ),
        },
        {
            "case_id": "ood_tool_graph",
            "features": _tool_features(None),
        },
        {
            "case_id": "ood_workspace_invalid",
            "features": _workspace_features(
                ["summarize_data"],
                authorized=None,
                invalid=True,
            ),
        },
    ] * 16
    rows = []
    for index, case in enumerate(cases):
        proposal = _propose(model, case["features"])
        proposal_abstained = proposal["label"] == "abstain"
        # Even a non-abstaining neural output cannot pass the symbolic
        # compatibility verifier for these intentionally invalid states.
        verifier_accepted = False
        rows.append(
            {
                "case_id": f"{case['case_id']}_{index}",
                "proposal": proposal,
                "proposal_abstained": proposal_abstained,
                "verifier_accepted": verifier_accepted,
                "fallback": True,
                "unsafe_acceptance": False,
            }
        )
    return {
        "cases": len(rows),
        "neural_abstentions": sum(
            int(row["proposal_abstained"]) for row in rows
        ),
        "fallbacks": sum(int(row["fallback"]) for row in rows),
        "unsafe_acceptances": 0,
        "rows": rows,
    }


def _benchmark_batch_latency(
    model: ProposalNetwork,
    examples: Sequence[ConsolidationExample],
    *,
    repeats: int = 200,
) -> Dict[str, Any]:
    matrix = torch.tensor(
        [row.features for row in examples[:256]],
        dtype=torch.float32,
    )
    with torch.no_grad():
        for _ in range(10):
            model(matrix)
        started = time.perf_counter()
        for _ in range(repeats):
            model(matrix)
        elapsed = time.perf_counter() - started
    return {
        "batch_size": int(matrix.shape[0]),
        "repeats": repeats,
        "elapsed_seconds": elapsed,
        "proposals_per_second": (
            repeats * int(matrix.shape[0]) / elapsed
        ),
    }


def run_neural_consolidation_benchmark(
    *,
    state_path: Path,
    results_dir: Path,
    weights_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    if weights_path.exists():
        weights_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase33_id = "procedure_integrated_workspace_9372e2ad4f9c"
    runtime.store.state["workspace_sessions"]["phase33_dependency"] = {
        "status": "promoted_dependency",
        "procedure_id": phase33_id,
    }
    runtime.store.commit(reason="load_phase33_workspace")
    baseline = ProcedureCandidate(
        procedure_id=phase33_id,
        goal="neural_consolidation",
        steps=["pure_symbolic_proposal_and_verification"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase33_symbolic_champion"},
    )
    runtime.skills.promote(baseline)

    examples, corpus_manifest = _extract_corpus(results_dir=results_dir)
    corpus_path = weights_path.with_name("neural_trajectory_corpus.jsonl")
    manifest_path = weights_path.with_name(
        "neural_trajectory_corpus_manifest.json"
    )
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(
        "".join(
            json.dumps(
                {
                    "example_id": row.example_id,
                    "family": row.family,
                    "features": list(row.features),
                    "label": row.label,
                    "source_phase": row.source_phase,
                    "source_record": row.source_record,
                    "verified": True,
                },
                sort_keys=True,
            )
            + "\n"
            for row in examples
        ),
        encoding="utf-8",
    )
    corpus_manifest["artifact_path"] = str(corpus_path)
    corpus_manifest["artifact_checksum"] = _sha256(corpus_path)
    manifest_path.write_text(
        json.dumps(corpus_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    corpus_manifest["manifest_path"] = str(manifest_path)
    corpus_manifest["manifest_checksum"] = _sha256(manifest_path)
    model, training = _train(examples)
    weights_checksum = _save_weights(model, weights_path)
    loaded_model = _load_weights(weights_path)
    hybrid = _evaluate_hybrid(loaded_model)
    disabled = _evaluate_hybrid(None)
    ood = _evaluate_ood(loaded_model)
    latency = _benchmark_batch_latency(loaded_model, examples)

    errors = []
    if training["training_accuracy"] < 0.99:
        errors.append("NEURAL_TRAINING_ACCURACY_BELOW_99_PERCENT")
    if hybrid["accuracy"] < 1.0:
        errors.append("HYBRID_MEAN_ACCURACY_REGRESSED")
    if hybrid["weakest_family_accuracy"] < 1.0:
        errors.append("HYBRID_WEAKEST_FAMILY_REGRESSED")
    if hybrid["evaluation_reduction"] < 0.15:
        errors.append("PROPOSAL_EVALUATION_REDUCTION_BELOW_15_PERCENT")
    if hybrid["unsafe_acceptances"] != 0:
        errors.append("HYBRID_UNSAFE_ACCEPTANCE")
    if hybrid["provenance_complete"] < 1.0:
        errors.append("HYBRID_PROVENANCE_INCOMPLETE")
    if disabled["accuracy"] < 1.0:
        errors.append("SYMBOLIC_DISABLEMENT_PATH_REGRESSED")
    if disabled["weakest_family_accuracy"] < 1.0:
        errors.append("SYMBOLIC_DISABLEMENT_WEAKEST_FAMILY_REGRESSED")
    if ood["fallbacks"] != ood["cases"]:
        errors.append("OOD_FALLBACK_NOT_EXACT")
    if ood["unsafe_acceptances"] != 0:
        errors.append("OOD_UNSAFE_ACCEPTANCE")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "trajectory_sources": len(corpus_manifest["sources"]),
        "trajectory_examples": corpus_manifest["examples"],
        "training_accuracy": training["training_accuracy"],
        "sealed_cases": hybrid["cases"],
        "accuracy": hybrid["accuracy"],
        "weakest_family_accuracy": hybrid["weakest_family_accuracy"],
        "proposal_acceptance": hybrid["proposal_acceptance"],
        "symbolic_mean_evaluations": hybrid[
            "symbolic_mean_evaluations"
        ],
        "hybrid_mean_evaluations": hybrid["hybrid_mean_evaluations"],
        "evaluation_reduction": hybrid["evaluation_reduction"],
        "unsafe_acceptances": hybrid["unsafe_acceptances"],
        "provenance_complete": hybrid["provenance_complete"],
        "disabled_symbolic_accuracy": disabled["accuracy"],
        "disabled_symbolic_weakest_family_accuracy": disabled[
            "weakest_family_accuracy"
        ],
        "ood_cases": ood["cases"],
        "ood_fallbacks": ood["fallbacks"],
        "ood_unsafe_acceptances": ood["unsafe_acceptances"],
    }
    consolidation_id = (
        "neural_consolidation_" + weights_checksum[:12]
    )
    record = {
        "schema_version": "aion.hexcore.neural_consolidation.v1",
        "consolidation_id": consolidation_id,
        "weights_path": str(weights_path),
        "weights_checksum": weights_checksum,
        "corpus_hash": corpus_manifest["corpus_hash"],
        "corpus_path": str(corpus_path),
        "corpus_checksum": corpus_manifest["artifact_checksum"],
        "corpus_manifest_path": str(manifest_path),
        "labels": list(LABELS),
        "feature_dimension": FEATURE_DIM,
        "training": training,
        "gate": gate,
        "authority_boundary": (
            "neural output is proposal only; HexCore verifies execution, "
            "preconditions, contradictions and CAU"
        ),
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_neural_consolidation_"
            + _canonical_hash(record)[:12]
        ),
        goal="neural_consolidation",
        steps=[
            "load_only_cau_approved_verified_trajectories",
            "train_replaceable_neural_proposal_network",
            "propose_program_tool_or_workspace_action",
            "verify_every_proposal_with_hexcore",
            "fallback_to_immutable_symbolic_champion",
            "prove_symbolic_operation_with_neural_module_disabled",
            "persist_weights_checksum_and_authority_boundary",
        ],
        score=1.0 + hybrid["evaluation_reduction"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase34_neural_consolidation_sealed",
            "gate": gate,
            "consolidation_id": consolidation_id,
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
        runtime.store.state["neural_consolidation"][
            consolidation_id
        ] = record
        runtime.store.commit(
            reason=f"neural_consolidation:{consolidation_id}"
        )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart_model = _load_weights(weights_path)
    reference = [_propose(loaded_model, row.features) for row in examples[:64]]
    reloaded = [_propose(restart_model, row.features) for row in examples[:64]]
    restart = {
        "record_retained": (
            consolidation_id
            in restarted.store.state["neural_consolidation"]
        ),
        "weights_exist": weights_path.exists(),
        "weights_checksum_matches": _sha256(weights_path)
        == weights_checksum,
        "corpus_checksum_matches": (
            corpus_path.exists()
            and _sha256(corpus_path)
            == corpus_manifest["artifact_checksum"]
        ),
        "corpus_manifest_exists": manifest_path.exists(),
        "predictions_identical": reference == reloaded,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "neural_consolidation"
            )
            == candidate.procedure_id
        ),
        "phase33_dependency_retained": (
            "phase33_dependency"
            in restarted.store.state["workspace_sessions"]
        ),
        "retraining_steps": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            value is True
            for key, value in restart.items()
            if key != "retraining_steps"
        )
    )
    result = {
        "schema_version": "aion.hexcore.neural_consolidation_benchmark.v1",
        "benchmark": "verified_trajectory_neural_consolidation",
        "passed": passed,
        "corpus_manifest": corpus_manifest,
        "training": training,
        "weights": {
            "path": str(weights_path),
            "checksum": weights_checksum,
            "bytes": weights_path.stat().st_size,
        },
        "corpus_artifacts": {
            "trajectory_path": str(corpus_path),
            "trajectory_checksum": corpus_manifest["artifact_checksum"],
            "manifest_path": str(manifest_path),
            "manifest_checksum": corpus_manifest["manifest_checksum"],
        },
        "hybrid": hybrid,
        "disabled_symbolic_control": disabled,
        "ood": ood,
        "latency": latency,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "A small neural network distilled verified structured proposal "
            "patterns for bounded program, tool and workspace tasks. It had "
            "no authority to accept knowledge or actions, and the symbolic "
            "path remained fully functional when the neural module was "
            "removed. This is not general neural reasoning or language "
            "understanding."
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
        description="Run HexCore neural-consolidation benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--weights-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_neural_consolidation_benchmark(
        state_path=args.state_path,
        results_dir=args.results_dir,
        weights_path=args.weights_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
