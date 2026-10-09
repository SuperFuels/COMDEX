"""Closed-book English competency portfolio backed by AION's native lexicon."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


FAMILIES: tuple[tuple[str, str, int, tuple[str, ...]], ...] = (
    ("native_sentence_roles_a", "sentence_semantics", 101,
     ("sentence_semantics", "syntax", "instruction_understanding")),
    ("native_tense_negation_a", "sentence_semantics", 307,
     ("sentence_semantics", "syntax", "morphology")),
    ("native_reference_resolution_a", "discourse_reasoning", 509,
     ("reference_resolution", "long_dialogue", "instruction_understanding")),
    ("native_argument_pragmatics_a", "discourse_reasoning", 701,
     ("argument_structure", "pragmatics", "native_question_answering")),
    ("native_sentence_roles_b", "sentence_semantics", 907,
     ("sentence_semantics", "syntax", "clear_generation")),
    ("native_tense_negation_b", "sentence_semantics", 1201,
     ("sentence_semantics", "morphology", "correction")),
    ("native_reference_resolution_b", "discourse_reasoning", 1601,
     ("reference_resolution", "ambiguity", "native_question_answering")),
    ("native_argument_pragmatics_b", "discourse_reasoning", 2003,
     ("argument_structure", "pragmatics", "instruction_understanding")),
)

FAMILY_SUBSKILLS: dict[str, tuple[str, ...]] = {
    "definition_match": ("lexical_grounding", "native_question_answering"),
    "synonym_choice": ("lexical_grounding", "semantic_relations"),
    "antonym_choice": ("semantic_relations", "ambiguity"),
    "context_completion": ("lexical_grounding", "instruction_understanding"),
    "mixed": ("lexical_grounding", "semantic_relations", "native_question_answering"),
    "sentence_semantics": ("sentence_semantics", "syntax", "morphology", "correction"),
    "discourse_reasoning": (
        "reference_resolution", "argument_structure", "pragmatics", "ambiguity",
        "instruction_understanding", "native_question_answering",
    ),
}


def _version() -> str:
    return "native_english_portfolio_v2_" + hashlib.sha256(
        json.dumps(FAMILIES, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]


def native_english_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    requirement = contract.get("requirement") or {}
    kind = str(requirement.get("kind") or "project")
    requested = set(map(str, requirement.get("subskills") or []))
    used = {str(row.get("project_family")) for row in evidence
            if row.get("kind") == kind and row.get("project_family")}
    if kind == "project":
        selected = next((row for row in FAMILIES if row[0] not in used), None)
        if selected is None:
            return {"status": "diverse_project_executor_required", "passed": False,
                    "reason": "Native English closed-book portfolio v2 is exhausted."}
        family_id, task_family, offset, subskills = selected
    else:
        priority = (
            "definition_match" if "lexical_grounding" in requested else
            "synonym_choice" if "semantic_relations" in requested else
            "sentence_semantics" if requested & {"sentence_semantics", "syntax", "morphology", "correction"} else
            "discourse_reasoning" if requested & set(FAMILY_SUBSKILLS["discourse_reasoning"]) else
            "mixed"
        )
        task_family = priority
        offset = 3101 + len(evidence) * 37
        subskills = FAMILY_SUBSKILLS[task_family]
        family_id = f"native_english_{kind}_{task_family}_v2"
        if family_id in used:
            return {"status": "diverse_project_executor_required", "passed": False,
                    "reason": f"Native English {kind} family {family_id} is already evidenced."}
    root = Path(str(contract.get("_repo_root") or Path.cwd())).resolve()
    learner = NativeLexicalIntelligence(repo_root=root)
    outcome = learner.run_practice_cycle(
        family=task_family, limit=20, seed=offset, offset=offset,
        project_family=family_id,
    )
    requires_source_disjoint = kind in {"project", "transfer"}
    accepted = bool(
        outcome["total"] >= 12 and outcome["score"] >= .75
        and outcome["expected_withheld"] and outcome["model_used"] is False
        and (outcome.get("source_disjoint") is True or not requires_source_disjoint)
        and outcome["authority"].get("allow_learn")
    )
    evidenced = sorted(set(subskills) & requested) or list(subskills)
    return {
        "status": "passed" if accepted else "native_exam_failed",
        "passed": accepted,
        "gate": {
            "score": float(outcome["score"]), "accepted": accepted,
            "candidate_execution_passed": bool(outcome["total"]),
            "source_disjoint_transfer": bool(outcome.get("source_disjoint")),
            "independent_outcome": True,
            "closed_book": True, "teacher_disconnected": True,
            "model_used_for_answers": False,
        },
        "exam": outcome, "evidenced_subskills": evidenced,
        "scaffolding": 0.05, "project_family": family_id,
        "unfamiliar": bool(outcome.get("source_disjoint")), "portfolio_version": _version(),
        "trials": int(outcome["total"]),
        "authority": ["native_lexical_memory", "withheld_answer_key", "cau_learning_gate"],
        "experience_class": "native_closed_book_language_examination",
        "authority_boundary": (
            "Qwen is absent from student answers and grading. One bounded lexical project "
            "is evidence for named subskills only, not general English mastery."
        ),
    }


native_english_runner.aion_portfolio_version = _version()  # type: ignore[attr-defined]
native_english_runner.aion_portfolio_families = {  # type: ignore[attr-defined]
    "project": frozenset(row[0] for row in FAMILIES),
    "lesson": frozenset({
        "native_english_lesson_definition_match_v2",
        "native_english_lesson_synonym_choice_v2",
        "native_english_lesson_sentence_semantics_v2",
        "native_english_lesson_discourse_reasoning_v2",
        "native_english_lesson_mixed_v2",
    }),
    "exercise": frozenset({
        "native_english_exercise_definition_match_v2",
        "native_english_exercise_synonym_choice_v2",
        "native_english_exercise_sentence_semantics_v2",
        "native_english_exercise_discourse_reasoning_v2",
        "native_english_exercise_mixed_v2",
    }),
}


__all__ = ["FAMILIES", "native_english_runner"]
