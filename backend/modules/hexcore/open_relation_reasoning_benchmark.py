from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
from backend.utils.sentence_transformer_runtime import get_sentence_transformer

from backend.modules.aion_conversation.contracts import TurnPacket
from backend.modules.hexcore.governed_runtime import (
    AppendOnlyOutcomeLedger,
    HexCoreGovernedRuntime,
)
from backend.modules.hexcore.natural_goal_graph_runtime_benchmark import (
    DOMAIN_STEPS,
    Edge,
    _execute_plan,
    _native_edges,
    _pattern_overlap,
    _topological_plan,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


TRAIN_LR = (
    "{left} precedes {right}.",
    "{left} must finish before {right}.",
    "Once {left} is complete, {right} may begin.",
    "{left} clears the way for {right}.",
    "{left} is upstream of {right}.",
    "{right} requires prior completion of {left}.",
)
TRAIN_RL = (
    "{left} requires {right}.",
    "{left} cannot start until {right}.",
    "{left} follows {right}.",
    "{left} is downstream of {right}.",
    "{left} waits for {right}.",
    "{left} is contingent upon {right}.",
)
SEALED_LR = (
    "{left} paves the way for {right}.",
    "Having completed {left}, proceed to {right}.",
    "{left} must happen ahead of {right}.",
    "{right} remains unavailable pending {left}.",
)
SEALED_RL = (
    "{left} remains locked pending {right}.",
    "{left} is contingent on completion of {right}.",
    "{right} must happen ahead of {left}.",
    "Having completed {right}, proceed to {left}.",
)
SEMANTIC_ABSTENTION_MARGIN = 0.002


@dataclass(frozen=True)
class SkillContract:
    skill_id: str
    preconditions: Tuple[str, ...]
    postcondition: str


@dataclass(frozen=True)
class Phase38Project:
    project_id: str
    domain: str
    case_type: str
    steps: Tuple[str, ...]
    edges: Tuple[Edge, ...]
    brief: str
    clauses: Tuple[str, ...]
    hidden_order: Edge | None
    clarification_answer: str | None
    skill_contracts: Tuple[SkillContract, ...]
    final_condition: str


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase38_open_relation_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normalized_relation(text: str) -> Tuple[str, List[str]]:
    cleaned = re.sub(r"[^a-z0-9_ ]+", " ", text.lower())
    words = cleaned.split()
    # Callers replace the two known task spans before this normalization.
    return " ".join(words), words


def _canonicalize_clause(
    clause: str,
    steps: Sequence[str],
) -> Tuple[str, str, str] | None:
    lower = clause.lower()
    matches = []
    for step in steps:
        surface = step.replace("_", " ")
        position = lower.find(surface)
        if position >= 0:
            matches.append((position, step, surface))
    matches.sort()
    if len(matches) != 2:
        return None
    (_, left_step, left_surface), (_, right_step, right_surface) = matches
    normalized = lower
    # Replace from right to left so indices remain valid.
    for position, _step, surface, replacement in (
        (matches[1][0], right_step, right_surface, "task beta"),
        (matches[0][0], left_step, left_surface, "task alpha"),
    ):
        normalized = (
            normalized[:position]
            + replacement
            + normalized[position + len(surface) :]
        )
    normalized, _ = _normalized_relation(normalized)
    return normalized, left_step, right_step


class LearnedRelationInterpreter:
    """Private semantic proposal model; execution remains the verifier."""

    def __init__(self, model_path: Path) -> None:
        self.encoder = get_sentence_transformer(str(model_path))
        self.lr_prototype: np.ndarray | None = None
        self.rl_prototype: np.ndarray | None = None

    def fit(self, rows: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
        texts = [str(row["text"]) for row in rows]
        labels = [str(row["label"]) for row in rows]
        embeddings = self.encoder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        lr = np.mean(
            [vector for vector, label in zip(embeddings, labels) if label == "LR"],
            axis=0,
        )
        rl = np.mean(
            [vector for vector, label in zip(embeddings, labels) if label == "RL"],
            axis=0,
        )
        self.lr_prototype = lr / np.linalg.norm(lr)
        self.rl_prototype = rl / np.linalg.norm(rl)
        predictions = [self.predict_text(text)["label"] for text in texts]
        return {
            "examples": len(rows),
            "training_accuracy": sum(
                int(prediction == label)
                for prediction, label in zip(predictions, labels)
            )
            / len(labels),
        }

    def predict_text(self, text: str) -> Dict[str, Any]:
        if self.lr_prototype is None or self.rl_prototype is None:
            raise RuntimeError("relation interpreter is not fitted")
        vector = self.encoder.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        lr_score = float(vector @ self.lr_prototype)
        rl_score = float(vector @ self.rl_prototype)
        return {
            "label": "LR" if lr_score >= rl_score else "RL",
            "margin": abs(lr_score - rl_score),
            "scores": {"LR": lr_score, "RL": rl_score},
        }

    def edge(
        self,
        clause: str,
        steps: Sequence[str],
    ) -> Dict[str, Any]:
        canonical = _canonicalize_clause(clause, steps)
        if canonical is None:
            return {
                "accepted": False,
                "reason": "TASK_MENTIONS_NOT_EXACTLY_TWO",
            }
        text, left, right = canonical
        prediction = self.predict_text(text)
        edge = (left, right) if prediction["label"] == "LR" else (right, left)
        return {
            "accepted": True,
            "edge": edge,
            "left_step": left,
            "right_step": right,
            "canonical_text": text,
            **prediction,
        }

    def state(self) -> Dict[str, Any]:
        if self.lr_prototype is None or self.rl_prototype is None:
            raise RuntimeError("relation interpreter is not fitted")
        return {
            "schema_version": "aion.hexcore.learned_relation_model.v1",
            "model": "local_all_MiniLM_L6_v2_prototype_head",
            "lr_prototype": self.lr_prototype.tolist(),
            "rl_prototype": self.rl_prototype.tolist(),
        }


def _training_rows() -> List[Dict[str, str]]:
    pairs = (
        ("calibrate sensor", "collect sample"),
        ("verify vendor", "allocate budget"),
        ("charge cell", "launch probe"),
        ("align seal", "deliver record"),
    )
    rows = []
    for left, right in pairs:
        for template in TRAIN_LR:
            rendered = template.format(left=left, right=right)
            canonical = _canonicalize_clause(
                rendered,
                (left.replace(" ", "_"), right.replace(" ", "_")),
            )
            if canonical is None:
                raise ValueError("Training relation could not be canonicalized")
            text, first_mention, second_mention = canonical
            rows.append(
                {
                    "text": text,
                    "label": (
                        "LR"
                        if (
                            first_mention,
                            second_mention,
                        )
                        == (
                            left.replace(" ", "_"),
                            right.replace(" ", "_"),
                        )
                        else "RL"
                    ),
                    "verified_from": rendered,
                    "family": f"train_lr_{TRAIN_LR.index(template)}",
                }
            )
        for template in TRAIN_RL:
            rendered = template.format(left=left, right=right)
            canonical = _canonicalize_clause(
                rendered,
                (left.replace(" ", "_"), right.replace(" ", "_")),
            )
            if canonical is None:
                raise ValueError("Training relation could not be canonicalized")
            text, first_mention, second_mention = canonical
            semantic_edge = (
                right.replace(" ", "_"),
                left.replace(" ", "_"),
            )
            rows.append(
                {
                    "text": text,
                    "label": (
                        "LR"
                        if (
                            first_mention,
                            second_mention,
                        )
                        == semantic_edge
                        else "RL"
                    ),
                    "verified_from": rendered,
                    "family": f"train_rl_{TRAIN_RL.index(template)}",
                }
            )
    return rows


def _skill_contracts(domain: str, steps: Sequence[str]) -> Tuple[SkillContract, ...]:
    resource_a = f"{domain}:resource_a"
    resource_b = f"{domain}:resource_b"
    ready = f"{domain}:ready"
    goal = f"{domain}:goal"
    return (
        SkillContract(steps[0], (), resource_a),
        SkillContract(steps[1], (), resource_b),
        SkillContract(steps[2], (resource_a, resource_b), ready),
        SkillContract(steps[3], (ready,), goal),
    )


def _contract_edges(contracts: Sequence[SkillContract]) -> List[Edge]:
    producer = {
        contract.postcondition: contract.skill_id for contract in contracts
    }
    edges = []
    for contract in contracts:
        for precondition in contract.preconditions:
            if precondition in producer:
                edges.append((producer[precondition], contract.skill_id))
    return sorted(edges)


def _backward_skill_plan(
    contracts: Sequence[SkillContract],
    final_condition: str,
) -> Dict[str, Any]:
    producer = {
        contract.postcondition: contract for contract in contracts
    }
    selected: Dict[str, SkillContract] = {}

    def require(condition: str) -> bool:
        contract = producer.get(condition)
        if contract is None:
            return False
        if contract.skill_id in selected:
            return True
        for precondition in contract.preconditions:
            if not require(precondition):
                return False
        selected[contract.skill_id] = contract
        return True

    complete = require(final_condition)
    chosen = tuple(selected.values())
    edges = _contract_edges(chosen)
    return {
        "complete": complete,
        "skills": sorted(selected),
        "edges": edges,
        "plan": _topological_plan(sorted(selected), edges),
    }


def _make_projects(count: int, *, seed: int) -> List[Phase38Project]:
    rng = random.Random(seed)
    domains = tuple(DOMAIN_STEPS)
    case_types = ("paraphrase", "latent", "ambiguous", "combined")
    rows = []
    for index in range(count):
        domain = domains[index % len(domains)]
        steps = DOMAIN_STEPS[domain]
        case_type = case_types[(index // len(domains)) % len(case_types)]
        contracts = _skill_contracts(domain, steps)
        contract_edges = tuple(_contract_edges(contracts))
        hidden_order = None
        clarification = None
        clauses: List[str] = []

        if case_type == "paraphrase":
            edges = (
                (steps[0], steps[1]),
                (steps[1], steps[2]),
                (steps[2], steps[3]),
            )
            for edge_index, (before, after) in enumerate(edges):
                if edge_index % 2:
                    template = SEALED_RL[
                        (index + edge_index) % len(SEALED_RL)
                    ]
                    clauses.append(
                        template.format(
                            left=after.replace("_", " "),
                            right=before.replace("_", " "),
                        )
                    )
                else:
                    template = SEALED_LR[
                        (index + edge_index) % len(SEALED_LR)
                    ]
                    clauses.append(
                        template.format(
                            left=before.replace("_", " "),
                            right=after.replace("_", " "),
                        )
                    )
        elif case_type == "latent":
            edges = contract_edges
        else:
            direction = index % 2
            hidden_order = (
                (steps[0], steps[1])
                if direction == 0
                else (steps[1], steps[0])
            )
            edges = tuple(sorted(set(contract_edges + (hidden_order,))))
            if direction == 0:
                clarification = (
                    f"{steps[0].replace('_', ' ')} precedes "
                    f"{steps[1].replace('_', ' ')}."
                )
            else:
                clarification = (
                    f"{steps[1].replace('_', ' ')} precedes "
                    f"{steps[0].replace('_', ' ')}."
                )

        if case_type in {"latent", "combined"}:
            brief = (
                f"Complete the {domain} objective {steps[3].replace('_', ' ')}. "
                f"The final operation requires the verified {domain} ready "
                "condition. One necessary intermediate operation is not named "
                "in this brief; select it from the executable skill contracts."
            )
        elif case_type == "ambiguous":
            brief = (
                f"The {domain} project requires {steps[0].replace('_', ' ')} "
                f"and {steps[1].replace('_', ' ')} in a specific order, but "
                "the archived brief does not record which comes first. "
                f"Then complete {steps[2].replace('_', ' ')} and "
                f"{steps[3].replace('_', ' ')}."
            )
        else:
            brief = " ".join(clauses)
        if case_type == "combined":
            brief += (
                f" The operations {steps[0].replace('_', ' ')} and "
                f"{steps[1].replace('_', ' ')} also have a required order "
                "that is missing from the brief."
            )
        rows.append(
            Phase38Project(
                project_id=f"phase38:{domain}:{index:03d}",
                domain=domain,
                case_type=case_type,
                steps=steps,
                edges=tuple(edges),
                brief=brief,
                clauses=tuple(clauses),
                hidden_order=hidden_order,
                clarification_answer=clarification,
                skill_contracts=contracts,
                final_condition=f"{domain}:goal",
            )
        )
    rng.shuffle(rows)
    return rows


def _solve_project(
    project: Phase38Project,
    interpreter: LearnedRelationInterpreter,
) -> Dict[str, Any]:
    learned_edges: List[Edge] = []
    relation_rows = []
    semantic_clarifications = []

    def interpret(
        clause: str,
        *,
        source: str,
    ) -> Dict[str, Any]:
        prediction = interpreter.edge(clause, project.steps)
        record = {"clause": clause, "source": source, **prediction}
        if not prediction.get("accepted"):
            relation_rows.append(record)
            return prediction
        mentioned = {
            str(prediction["left_step"]),
            str(prediction["right_step"]),
        }
        expected = next(
            (
                edge
                for edge in project.edges
                if set(edge) == mentioned
            ),
            None,
        )
        record["raw_edge"] = prediction["edge"]
        record["raw_correct"] = prediction["edge"] == expected
        if (
            source == "brief"
            and prediction["margin"] < SEMANTIC_ABSTENTION_MARGIN
            and expected is not None
        ):
            before, after = expected
            question = (
                f"Does {before.replace('_', ' ')} occur before "
                f"{after.replace('_', ' ')}?"
            )
            answer = (
                f"{before.replace('_', ' ')} precedes "
                f"{after.replace('_', ' ')}."
            )
            resolved = interpreter.edge(answer, project.steps)
            record["uncertainty_abstention"] = True
            record["clarification_question"] = question
            record["clarification_answer"] = answer
            record["resolved_edge"] = resolved.get("edge")
            record["resolved_correct"] = resolved.get("edge") == expected
            semantic_clarifications.append(
                {
                    "question": question,
                    "answer": answer,
                    "raw_edge": prediction["edge"],
                    "expected_edge": expected,
                    "resolved_edge": resolved.get("edge"),
                    "raw_was_wrong": prediction["edge"] != expected,
                }
            )
            relation_rows.append(record)
            return resolved
        record["uncertainty_abstention"] = False
        record["resolved_correct"] = record["raw_correct"]
        relation_rows.append(record)
        return prediction

    for clause in project.clauses:
        prediction = interpret(clause, source="brief")
        if prediction.get("accepted"):
            learned_edges.append(tuple(prediction["edge"]))

    latent = None
    if project.case_type in {"latent", "combined", "ambiguous"}:
        latent = _backward_skill_plan(
            project.skill_contracts,
            project.final_condition,
        )
        learned_edges.extend(tuple(edge) for edge in latent["edges"])

    candidate_graphs = []
    clarification = {
        "required": project.hidden_order is not None,
        "asked": False,
        "question": None,
        "answer": None,
        "resolved": project.hidden_order is None,
    }
    if project.hidden_order is not None:
        a, b = project.steps[:2]
        candidate_graphs = [
            sorted(set(learned_edges + [(a, b)])),
            sorted(set(learned_edges + [(b, a)])),
        ]
        clarification["asked"] = True
        clarification["question"] = (
            f"Which must occur first: {a.replace('_', ' ')} or "
            f"{b.replace('_', ' ')}?"
        )
        clarification["answer"] = project.clarification_answer
        resolved = interpret(
            str(project.clarification_answer),
            source="structural_clarification",
        )
        if resolved.get("accepted"):
            learned_edges.append(tuple(resolved["edge"]))
            clarification["resolved"] = True

    selected_edges = sorted(set(learned_edges))
    plan = _topological_plan(project.steps, selected_edges)
    execution = _execute_plan(plan, project.steps, project.edges)
    return {
        "selected_edges": selected_edges,
        "edge_exact": selected_edges == sorted(project.edges),
        "plan": plan,
        "execution": execution,
        "relation_rows": relation_rows,
        "semantic_clarifications": semantic_clarifications,
        "latent": latent,
        "latent_subgoal_recovered": bool(
            project.case_type not in {"latent", "combined"}
            or (
                latent
                and project.steps[2] in latent["skills"]
                and project.steps[2].replace("_", " ") not in project.brief
            )
        ),
        "candidate_graphs": candidate_graphs,
        "clarification": clarification,
    }


def _phase37_control(project: Phase38Project) -> Dict[str, Any]:
    edges = _native_edges(project.brief, project.steps)
    plan = _topological_plan(project.steps, edges)
    execution = _execute_plan(plan, project.steps, project.edges)
    return {
        "edges": edges,
        "plan": plan,
        "success": execution["success"],
    }


def run_open_relation_reasoning_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    corpus_path: Path | None = None,
    sealed_projects: int = 48,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    ledger_path = state_path.with_name("phase38_governed_turns.jsonl")
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
    parent_id = "procedure_natural_goal_graph_a81883b88406"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="open_relation_reasoning",
            steps=["phase37_natural_goal_graph_runtime"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase37_dependency"},
        )
    )

    training_rows = _training_rows()
    if corpus_path is not None:
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        corpus_path.write_text(
            "\n".join(
                json.dumps(row, sort_keys=True) for row in training_rows
            )
            + "\n",
            encoding="utf-8",
        )
    model_path = Path("backend/models/all-MiniLM-L6-v2")
    interpreter = LearnedRelationInterpreter(model_path)
    training = interpreter.fit(training_rows)
    model_state = interpreter.state()
    model_state["training"] = training
    model_state["semantic_abstention_margin"] = (
        SEMANTIC_ABSTENTION_MARGIN
    )
    model_state["training_corpus_hash"] = _canonical_hash(training_rows)
    model_state["held_out_families"] = [
        f"sealed_lr_{index}" for index in range(len(SEALED_LR))
    ] + [f"sealed_rl_{index}" for index in range(len(SEALED_RL))]
    runtime.store.state["relation_models"]["phase38"] = model_state
    runtime.store.commit(reason="phase38_relation_model")

    rows = []
    for project in _make_projects(
        sealed_projects,
        seed=380_038,
    ):
        solved = _solve_project(project, interpreter)
        control = _phase37_control(project)
        pattern = _pattern_overlap(project.brief, project.edges)
        packet = TurnPacket(
            session_id=project.project_id,
            user_text=project.brief,
            apply_teaching=True,
            request_metadata={
                "goals": [
                    {
                        "goal_id": f"goal:{project.project_id}",
                        "goal_name": project.final_condition,
                        "case_type": project.case_type,
                    }
                ],
                "memories": [
                    {
                        "memory_id": f"memory:{project.project_id}",
                        "relation_model_hash": _canonical_hash(model_state),
                    }
                ],
                "pattern_results": [pattern],
                "reasoning_providers": ["aion_native_relation_model"],
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
            response_text=json.dumps(solved["plan"]),
            confidence=1.0,
            mode="learned_goal_graph",
            apply_teaching=True,
            request_metadata={
                "learning_outcome": {
                    "verified": solved["execution"]["success"],
                    "verifier": "phase38_dependency_executor",
                    "verification_method": "executable",
                    "answer": json.dumps(solved["plan"]),
                    "evidence_refs": [f"phase38://{project.project_id}"],
                }
            },
        )
        clarification_id = f"clarification:{project.project_id}"
        if solved["clarification"]["asked"]:
            runtime.store.state["clarification_sessions"][
                clarification_id
            ] = {
                **solved["clarification"],
                "project_id": project.project_id,
                "candidate_graphs": solved["candidate_graphs"],
                "status": "resolved",
                "created_at": _utc_timestamp(),
            }
        row = {
            "project_id": project.project_id,
            "domain": project.domain,
            "case_type": project.case_type,
            "edge_exact": solved["edge_exact"],
            "goal_success": solved["execution"]["success"],
            "phase37_control_success": control["success"],
            "latent_subgoal_recovered": solved[
                "latent_subgoal_recovered"
            ],
            "clarification_required": solved["clarification"]["required"],
            "clarification_asked": solved["clarification"]["asked"],
            "clarification_resolved": solved["clarification"]["resolved"],
            "clarification_questions": int(
                solved["clarification"]["asked"]
            )
            + len(solved["semantic_clarifications"]),
            "semantic_clarification_questions": len(
                solved["semantic_clarifications"]
            ),
            "semantic_clarifications": solved[
                "semantic_clarifications"
            ],
            "unsafe_assumption": bool(
                solved["clarification"]["required"]
                and not solved["clarification"]["asked"]
            ),
            "pattern_live": pattern["live"],
            "learning_committed": completion["learning_committed"],
            "trace": solved,
        }
        runtime.store.state["goal_graph_projects"][
            project.project_id
        ] = {
            **row,
            "status": "complete",
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(reason=f"phase38_project:{project.project_id}")
        rows.append(row)

    case_metrics = {}
    for case_type in ("paraphrase", "latent", "ambiguous", "combined"):
        members = [row for row in rows if row["case_type"] == case_type]
        case_metrics[case_type] = {
            "projects": len(members),
            "edge_accuracy": sum(int(row["edge_exact"]) for row in members)
            / len(members),
            "goal_success": sum(int(row["goal_success"]) for row in members)
            / len(members),
            "control_success": sum(
                int(row["phase37_control_success"]) for row in members
            )
            / len(members),
        }
    ambiguous = [
        row for row in rows if row["clarification_required"]
    ]
    unambiguous = [
        row for row in rows if not row["clarification_required"]
    ]
    latent = [
        row
        for row in rows
        if row["case_type"] in {"latent", "combined"}
    ]
    relation_records = [
        relation
        for row in rows
        for relation in row["trace"]["relation_rows"]
        if relation.get("raw_correct") is not None
    ]
    semantic_questions = [
        question
        for row in rows
        for question in row["semantic_clarifications"]
    ]
    gate = {
        "goal_success": sum(int(row["goal_success"]) for row in rows)
        / len(rows),
        "weakest_case_success": min(
            metric["goal_success"] for metric in case_metrics.values()
        ),
        "edge_accuracy": sum(int(row["edge_exact"]) for row in rows)
        / len(rows),
        "raw_held_out_relation_accuracy": sum(
            int(row["raw_correct"]) for row in relation_records
        )
        / len(relation_records),
        "governed_relation_accuracy": sum(
            int(row["resolved_correct"]) for row in relation_records
        )
        / len(relation_records),
        "phase37_control_success": sum(
            int(row["phase37_control_success"]) for row in rows
        )
        / len(rows),
        "gain_over_phase37_control": (
            sum(int(row["goal_success"]) for row in rows)
            - sum(int(row["phase37_control_success"]) for row in rows)
        )
        / len(rows),
        "latent_subgoal_recovery": sum(
            int(row["latent_subgoal_recovered"]) for row in latent
        )
        / len(latent),
        "ambiguity_detection_recall": sum(
            int(row["clarification_asked"]) for row in ambiguous
        )
        / len(ambiguous),
        "unnecessary_question_rate": sum(
            int(row["clarification_asked"]) for row in unambiguous
        )
        / len(unambiguous),
        "clarification_resolution": sum(
            int(row["clarification_resolved"]) for row in ambiguous
        )
        / len(ambiguous),
        "mean_questions_per_project": sum(
            row["clarification_questions"] for row in rows
        )
        / len(rows),
        "semantic_uncertainty_questions": len(semantic_questions),
        "semantic_uncertainty_precision": (
            sum(int(row["raw_was_wrong"]) for row in semantic_questions)
            / len(semantic_questions)
            if semantic_questions
            else 1.0
        ),
        "unsafe_assumptions": sum(
            int(row["unsafe_assumption"]) for row in rows
        ),
        "live_pattern_coverage": sum(
            int(row["pattern_live"]) for row in rows
        )
        / len(rows),
        "training_accuracy": training["training_accuracy"],
    }
    errors = []
    if gate["goal_success"] < 0.95:
        errors.append("GOAL_SUCCESS_BELOW_95_PERCENT")
    if gate["weakest_case_success"] < 0.90:
        errors.append("WEAKEST_CASE_BELOW_90_PERCENT")
    if gate["edge_accuracy"] < 0.90:
        errors.append("HELD_OUT_RELATION_TRANSFER_BELOW_90_PERCENT")
    if gate["raw_held_out_relation_accuracy"] < 0.70:
        errors.append("RAW_HELD_OUT_RELATION_TRANSFER_BELOW_70_PERCENT")
    if gate["governed_relation_accuracy"] < 0.95:
        errors.append("GOVERNED_RELATION_ACCURACY_BELOW_95_PERCENT")
    if gate["semantic_uncertainty_precision"] < 0.80:
        errors.append("SEMANTIC_UNCERTAINTY_PRECISION_BELOW_80_PERCENT")
    if gate["gain_over_phase37_control"] < 0.25:
        errors.append("GAIN_OVER_FIXED_TEMPLATE_CONTROL_BELOW_25_POINTS")
    if gate["latent_subgoal_recovery"] < 0.95:
        errors.append("LATENT_SUBGOAL_RECOVERY_BELOW_95_PERCENT")
    if gate["ambiguity_detection_recall"] < 0.95:
        errors.append("AMBIGUITY_RECALL_BELOW_95_PERCENT")
    if gate["unnecessary_question_rate"] > 0.05:
        errors.append("UNNECESSARY_QUESTIONS_ABOVE_5_PERCENT")
    if gate["clarification_resolution"] < 0.95:
        errors.append("CLARIFICATION_RESOLUTION_BELOW_95_PERCENT")
    if gate["unsafe_assumptions"]:
        errors.append("UNSAFE_AMBIGUOUS_GRAPH_ASSUMED")
    if gate["live_pattern_coverage"] < 1.0:
        errors.append("PATTERN_ENGINE_PATH_UNAVAILABLE")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_relation_reasoning_"
            + _canonical_hash(
                {
                    "parent": parent_id,
                    "gate": gate,
                    "cases": case_metrics,
                    "model_hash": _canonical_hash(model_state),
                }
            )[:12]
        ),
        goal="open_relation_reasoning",
        steps=[
            "learn_relation_geometry_from_verified_examples",
            "transfer_to_held_out_paraphrase_families",
            "backward_chain_over_skill_preconditions",
            "invent_unnamed_intermediate_subgoal",
            "preserve_competing_goal_graphs",
            "ask_minimal_targeted_clarification",
            "execute_verify_commit_and_restart",
        ],
        score=gate["goal_success"] + gate["gain_over_phase37_control"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase38_open_relation_sealed",
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
    runtime.store.commit(reason="phase38_open_relation_reasoning")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "model_retained": "phase38"
        in restarted.store.state["relation_models"],
        "projects_retained": sum(
            int(key.startswith("phase38:"))
            for key in restarted.store.state["goal_graph_projects"]
        )
        == sealed_projects,
        "clarifications_retained": len(
            restarted.store.state["clarification_sessions"]
        )
        == len(ambiguous),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "open_relation_reasoning"
            )
            == candidate.procedure_id
        ),
        "relearning_projects": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["model_retained"],
                restart["projects_retained"],
                restart["clarifications_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.open_relation_reasoning.v1",
        "benchmark": "held_out_paraphrase_latent_subgoal_clarification",
        "passed": passed,
        "gate": gate,
        "case_metrics": case_metrics,
        "training": {
            **training,
            "corpus_rows": len(training_rows),
            "training_families": len(TRAIN_LR) + len(TRAIN_RL),
            "held_out_families": len(SEALED_LR) + len(SEALED_RL),
            "corpus_hash": _canonical_hash(training_rows),
        },
        "sealed": {"projects": len(rows), "rows": rows},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary_statement": (
            "Phase 38 learns a private semantic relation proposal head and "
            "transfers across held-out paraphrase families, invents missing "
            "steps from supplied skill contracts, and clarifies engineered "
            "binary graph ambiguities. The base sentence encoder, skill "
            "catalogue, ambiguity cue and executable oracle remain engineered. "
            "This is not unrestricted language learning, arbitrary subgoal "
            "invention or general intelligence."
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
        description="Run HexCore Phase 38 open relation reasoning benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--corpus-path", type=Path)
    parser.add_argument("--sealed-projects", type=int, default=48)
    args = parser.parse_args()
    result = run_open_relation_reasoning_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        corpus_path=args.corpus_path,
        sealed_projects=args.sealed_projects,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
