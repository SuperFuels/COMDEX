"""Continuous local-Qwen teacher for AION's model-free English student.

Qwen may propose lessons and feedback.  It never answers AION's examination
questions, never sees their withheld answer key, and never awards competence.
Promotion is calculated solely from governed native practice attempts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning
from backend.modules.aion_cognition.native_english_coverage import (
    COVERAGE_CASES, NativeEnglishCoverage, expanded_coverage_cases,
)
from backend.modules.aion_cognition.native_semantic_spider import NativeSemanticSpider
from backend.modules.aion_cognition.native_semantic_transfer_academy import NativeSemanticTransferAcademy
from backend.modules.aion_cognition.native_language_workshop import NativeLanguageWorkshop


CURRICULUM: tuple[dict[str, Any], ...] = (
    {"id": "lexical_foundations", "title": "Word meanings and definition matching",
     "family": "definition_match", "minimum_attempts": 24, "pass_accuracy": .82},
    {"id": "semantic_relations", "title": "Synonyms, antonyms and concept relations",
     "family": "synonym_choice", "minimum_attempts": 32, "pass_accuracy": .82},
    {"id": "semantic_contrasts", "title": "Opposites and fine-grained contrasts",
     "family": "antonym_choice", "minimum_attempts": 32, "pass_accuracy": .82},
    {"id": "contextual_meaning", "title": "Meaning from unfamiliar sentence context",
     "family": "context_completion", "minimum_attempts": 40, "pass_accuracy": .84},
    {"id": "mixed_transfer", "title": "Mixed lexical transfer without teacher access",
     "family": "mixed", "minimum_attempts": 48, "pass_accuracy": .86},
    {"id": "sentence_semantics", "title": "Entities, actions, properties, tense and negation",
     "family": "sentence_semantics", "minimum_attempts": 64, "pass_accuracy": .88,
     "require_source_disjoint": True},
    {"id": "discourse_reasoning", "title": "Reference, ambiguity, argument and pragmatics",
     "family": "discourse_reasoning", "minimum_attempts": 80, "pass_accuracy": .90,
     "require_source_disjoint": True},
    {"id": "compositional_syntax", "title": "Complex clauses and compositional syntax",
     "family": "compositional_syntax", "minimum_attempts": 80, "pass_accuracy": .90,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "paragraph_comprehension", "title": "Paragraph comprehension and causal sequence",
     "family": "paragraph_comprehension", "minimum_attempts": 96, "pass_accuracy": .90,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "unseen_document_qa", "title": "Unseen-document reading and exact retrieval",
     "family": "unseen_document_qa", "minimum_attempts": 96, "pass_accuracy": .92,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "dialogue_tracking", "title": "Multi-turn dialogue, reference and instruction tracking",
     "family": "dialogue_tracking", "minimum_attempts": 96, "pass_accuracy": .92,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "ambiguity_pragmatics", "title": "Ambiguity, implication and calibrated uncertainty",
     "family": "ambiguity_pragmatics", "minimum_attempts": 96, "pass_accuracy": .90,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "explanation_generation", "title": "Grounded explanation in Aion's own words",
     "family": "explanation_generation", "minimum_attempts": 96, "pass_accuracy": .90,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "error_correction", "title": "Grammar error detection and precise correction",
     "family": "error_correction", "minimum_attempts": 96, "pass_accuracy": .94,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "cross_domain_transfer", "title": "Cross-domain reading, reasoning and reliability",
     "family": "cross_domain_transfer", "minimum_attempts": 128, "pass_accuracy": .92,
     "require_source_disjoint": True, "require_free_response": True},
    {"id": "productive_semantic_transfer",
     "title": "Native sentence production from acquired meaning",
     "family": "productive_sentence_transfer", "minimum_attempts": 160,
     "pass_accuracy": .75, "minimum_unique_ratio": .95,
     "require_source_disjoint": True, "require_free_response": True,
     "require_acquired_grounding": True,
     "required_evidence_source": "aion_acquired_concepts_v5",
     "minimum_recent_free_transfer_accuracy": .50,
     "minimum_productive_concepts": 10, "track": "advanced"},
    {"id": "scope_counterfactual_reasoning",
     "title": "Scope, conditions, counterfactuals and nested negation",
     "family": "scope_counterfactual_reasoning", "minimum_attempts": 160,
     "pass_accuracy": .80, "minimum_unique_ratio": .95,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
    {"id": "multi_source_evidence_synthesis",
     "title": "Multi-source evidence synthesis and contradiction",
     "family": "multi_source_evidence_synthesis", "minimum_attempts": 192,
     "pass_accuracy": .78, "minimum_unique_ratio": .95,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
    {"id": "paraphrase_revision",
     "title": "Meaning-preserving paraphrase and revision",
     "family": "paraphrase_revision", "minimum_attempts": 160,
     "pass_accuracy": .80, "minimum_unique_ratio": .95,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
    {"id": "conversation_belief_revision",
     "title": "Conversation, correction and belief revision",
     "family": "conversation_belief_revision", "minimum_attempts": 160,
     "pass_accuracy": .82, "minimum_unique_ratio": .95,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
    {"id": "adversarial_uncertainty",
     "title": "Adversarial ambiguity and calibrated abstention",
     "family": "adversarial_uncertainty", "minimum_attempts": 192,
     "pass_accuracy": .85, "minimum_unique_ratio": .97,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
    {"id": "delayed_open_generalisation",
     "title": "Delayed open transfer across vocabulary and structures",
     "family": "delayed_open_generalisation", "minimum_attempts": 256,
     "pass_accuracy": .82, "minimum_unique_ratio": .98,
     "minimum_retention_span_seconds": 86400,
     "require_source_disjoint": True, "require_free_response": True,
     "track": "advanced"},
)

STAGE_TARGETS: tuple[tuple[str, ...], ...] = (
    ("object", "action", "person", "place", "time", "change", "cause", "effect", "true", "false"),
    ("calm", "peaceful", "agitated", "precise", "vague", "similar", "different", "include", "exclude"),
    ("accept", "reject", "increase", "decrease", "possible", "impossible", "certain", "uncertain"),
    ("context", "meaning", "literal", "figurative", "specific", "general", "before", "after"),
    ("evidence", "claim", "reason", "conclusion", "condition", "exception", "compare", "infer"),
    ("entity", "property", "tense", "negation", "subject", "object", "action", "state"),
    ("reference", "ambiguity", "argument", "pragmatic", "speaker", "intention", "implication"),
    ("clause", "modifier", "scope", "attachment", "agent", "patient", "composition"),
    ("paragraph", "sequence", "cause", "consequence", "summary", "detail", "coherence"),
    ("document", "retrieve", "calculate", "constraint", "exception", "evidence", "answer"),
    ("dialogue", "turn", "reference", "revision", "instruction", "speaker", "resolve"),
    ("ambiguity", "implication", "uncertain", "literal", "intention", "context", "abstain"),
    ("explain", "because", "evidence", "reason", "claim", "grounded", "concise"),
    ("grammar", "agreement", "tense", "correct", "diagnose", "revise", "verify"),
    ("transfer", "science", "history", "engineering", "reliability", "generalise", "limits"),
    ("concept", "meaning", "context", "select", "express", "productive", "acquired"),
    ("scope", "condition", "counterfactual", "negation", "necessary", "sufficient"),
    ("evidence", "source", "conflict", "corroborate", "reliability", "synthesise"),
    ("paraphrase", "preserve", "active", "passive", "revise", "equivalent"),
    ("dialogue", "correction", "belief", "revision", "reference", "latest"),
    ("ambiguous", "unknown", "insufficient", "conflict", "abstain", "confidence"),
    ("retain", "delay", "generalise", "unseen", "combine", "transfer"),
)

GOAL = (
    "Develop AION's own English comprehension from verified lexical grounding through "
    "sentence and discourse reasoning. Qwen is a teacher only. AION must pass every "
    "closed-book examination using local memory and native reasoning with Qwen disconnected. "
    "Advanced promotion requires free responses to sealed, unseen material and cross-domain transfer."
)


def _state_path(repo_root: Path) -> Path:
    return repo_root / "data/aion/native_english_teacher/state.json"


def _audit_path(repo_root: Path) -> Path:
    return repo_root / "data/aion/native_english_teacher/cycles.jsonl"


def _load_state(repo_root: Path) -> dict[str, Any]:
    path = _state_path(repo_root)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(state, dict):
            return state
    except (OSError, json.JSONDecodeError):
        pass
    return {"schema_version": "aion.native_english_teacher.v4", "stage_index": 0,
            "consecutive_stage_passes": 0, "cycles": 0}


def _migrate_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve old certificates but never leave the learner on a saturated bank."""
    migrated = dict(state)
    schema = str(migrated.get("schema_version") or "")
    if schema not in {"aion.native_english_teacher.v3", "aion.native_english_teacher.v4"}:
        if bool(migrated.get("curriculum_complete")) and int(migrated.get("stage_index") or 0) >= 6:
            migrated.update({
                "stage_index": 7,
                "stage_id": CURRICULUM[7]["id"],
                "consecutive_stage_passes": 0,
                "foundation_curriculum_complete": True,
                "curriculum_complete": False,
                "advanced_curriculum_started_epoch": time.time(),
            })
    if (schema == "aion.native_english_teacher.v3"
            and bool(migrated.get("curriculum_complete"))
            and int(migrated.get("stage_index") or 0) >= 14):
        migrated.update({
            "stage_index": 15,
            "stage_id": CURRICULUM[15]["id"],
            "consecutive_stage_passes": 0,
            "foundation_curriculum_complete": True,
            "intermediate_curriculum_complete": True,
            "curriculum_complete": False,
            "open_advanced_curriculum_started_epoch": time.time(),
        })
    migrated["schema_version"] = "aion.native_english_teacher.v4"
    return migrated


def _save_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _json_object(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
    try:
        decoded = json.loads(text)
        return decoded if isinstance(decoded, dict) else {"lesson": text}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                decoded = json.loads(match.group(0))
                return decoded if isinstance(decoded, dict) else {"lesson": text}
            except json.JSONDecodeError:
                pass
    return {"lesson": text[:12000], "format_repaired": True}


def _local_qwen_teacher(prompt: str) -> dict[str, Any]:
    from backend.modules.hexcore.prediction_market_research_engine import (
        DEFAULT_MODEL, _local_qwen_runtime_profile,
    )
    from backend.services.aion_mission_mode.pilot_local_model_runtime import run_selected_local_chat

    response = run_selected_local_chat(
        prompt=prompt,
        runtime_profile=_local_qwen_runtime_profile(),
        system_prompt=(
            "You are AION's local English teacher. You may explain and create study material, "
            "but you are never the student, examiner, answer key, or competence authority. "
            "Return only the requested JSON object."
        ),
    )
    return {"content": str(response.get("content") or ""),
            "model": str(response.get("model") or DEFAULT_MODEL)}


def _lesson_targets(
    student: NativeLexicalIntelligence, stage_index: int, cycle_index: int,
) -> list[dict[str, str]]:
    preferred = list(STAGE_TARGETS[stage_index])
    rotation = cycle_index % max(1, len(preferred))
    preferred = preferred[rotation:] + preferred[:rotation]
    offset = 3000 + stage_index * 5000 + cycle_index * 97
    words = preferred[:5] + student._candidate_words(offset=offset, limit=24)
    targets: list[dict[str, str]] = []
    for word in words:
        entry = student.lookup(word)
        if entry and entry["lemma"] not in {row["lemma"] for row in targets}:
            targets.append({"lemma": entry["lemma"], "definition": entry["definition"]})
        if len(targets) >= 10:
            break
    return targets


def build_teacher_prompt(
    *, stage_index: int, stage: Mapping[str, Any], targets: list[dict[str, str]],
    prior_exam: Mapping[str, Any], stats: Mapping[str, Any], cycle_index: int = 0,
) -> str:
    curriculum = [{"order": index + 1, "id": row["id"], "title": row["title"],
                   "pass_accuracy": row["pass_accuracy"]}
                  for index, row in enumerate(CURRICULUM)]
    return f"""GOAL
{GOAL}

FULL CURRICULUM
{json.dumps(curriculum, ensure_ascii=False, separators=(',', ':'))}

CURRENT STAGE
{stage_index + 1}: {stage['id']} — {stage['title']}

LESSON VARIANT
Cycle {cycle_index + 1}. Focus on target set {cycle_index % 12 + 1} of 12. Do not repeat the
same explanation, examples, or guided practice from an earlier cycle.

AION NATIVE MEMORY STATUS
{json.dumps(dict(stats), ensure_ascii=False, separators=(',', ':'))}

PREVIOUS CLOSED-BOOK RESULTS
{json.dumps(dict(prior_exam), ensure_ascii=False, separators=(',', ':'))}

VERIFIED STUDY TARGETS
{json.dumps(targets, ensure_ascii=False, separators=(',', ':'))}

Create a compact lesson that helps AION form distinctions and transfer concepts. Do not create,
answer, grade, or infer the closed-book examination. Use only the supplied verified definitions
as factual grounding. Return JSON with keys: objective, explanation, contrasts (array),
examples (array), guided_practice (array), referenced_lemmas (array), next_focus."""


def run_teacher_cycle(
    *, repo_root: Path | str, teacher_client: Callable[[str], Mapping[str, Any]] | None = None,
    student: NativeLexicalIntelligence | None = None, exam_limit: int = 16,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    learner = student or NativeLexicalIntelligence(repo_root=root)
    state = _migrate_state(_load_state(root))
    stage_index = min(max(0, int(state.get("stage_index") or 0)), len(CURRICULUM) - 1)
    stage = CURRICULUM[stage_index]
    evidence_limit = max(200, int(stage["minimum_attempts"]) * 2)
    prior_exam = learner.practice_summary(
        family=str(stage["family"]), limit=evidence_limit,
    )
    cycle_index = int(state.get("cycles") or 0)
    targets = _lesson_targets(learner, stage_index, cycle_index)
    prompt = build_teacher_prompt(stage_index=stage_index, stage=stage, targets=targets,
                                  prior_exam=prior_exam, stats=learner.stats(),
                                  cycle_index=cycle_index)
    teacher = teacher_client or _local_qwen_teacher
    teacher_error = None
    lesson_record: dict[str, Any] | None = None
    model = "local-qwen-unavailable"
    try:
        response = dict(teacher(prompt))
        model = str(response.get("model") or "local-qwen")
        lesson = _json_object(str(response.get("content") or ""))
        references = lesson.get("referenced_lemmas") or [row["lemma"] for row in targets]
        lesson_record = learner.record_teacher_lesson(
            stage_id=str(stage["id"]), content=lesson, teacher_model=model,
            referenced_lemmas=[str(item) for item in references],
        )
    except Exception as exc:
        teacher_error = f"{type(exc).__name__}:{exc}"

    # The examination starts only after the teacher response is closed. No
    # teacher callback, prompt, lesson, or expected answer enters this path.
    if stage.get("implemented", True):
        exam_offset = (
            int(prior_exam.get("attempts") or 0)
            if bool(stage.get("require_source_disjoint"))
            else (int(state.get("cycles") or 0) * 97 + stage_index * 503)
        )
        exam = learner.run_practice_cycle(
            family=str(stage["family"]), limit=max(4, int(exam_limit)),
            seed=int(state.get("cycles") or 0) + stage_index * 101,
            offset=exam_offset,
            project_family=f"native_english_{stage['id']}_v4",
        )
    else:
        exam = {
            "passed": False, "score": 0.0, "correct": 0, "total": 0,
            "family": stage["family"], "authority": {"allow_learn": False,
                "deny_reason": "NATIVE_EXAM_FAMILY_NOT_IMPLEMENTED"},
            "model_used": False, "cloud_used": False, "expected_withheld": True,
            "attempts": [],
        }
    summary = learner.practice_summary(
        family=str(stage["family"]), limit=evidence_limit,
    )
    from backend.modules.aion_cognition.native_english_conversation import NativeEnglishConversation
    lesson_lemmas = (
        list(lesson_record.get("referenced_lemmas") or [])
        if lesson_record else [row["lemma"] for row in targets]
    )
    native_wordwall = NativeWordwallLearning(
        repo_root=root, lexical=learner,
    ).run_cycle(
        limit=max(8, int(exam_limit)),
        preferred_lemmas=lesson_lemmas,
        teacher_lesson_id=str((lesson_record or {}).get("lesson_id") or ""),
    )
    coverage_cases = (
        (*COVERAGE_CASES, *expanded_coverage_cases(10))
        if cycle_index % 12 == 0 else COVERAGE_CASES
    )
    # Reuse the cycle's lexical authority and connection target. Creating a
    # second runtime here can contend with the active SD-card database while
    # adding no independent evidence.
    native_coverage = NativeEnglishCoverage(
        repo_root=root, lexical=learner,
    ).run(coverage_cases)
    native_improvement = NativeEnglishConversation(
        repo_root=root, lexical=learner,
    ).self_improvement_cycle(limit=16)
    semantic_spider = NativeSemanticSpider(
        repo_root=root, lexical=learner,
    )
    spider_status = semantic_spider.status()
    native_semantic_spider = (
        semantic_spider.cycle(steps=1) if spider_status.get("running") else spider_status
    )
    academy_runtime = NativeSemanticTransferAcademy(repo_root=root, lexical=learner)
    if teacher_error is not None:
        semantic_transfer_academy: dict[str, Any] = {
            "status": "teacher_unavailable", "error": teacher_error,
            "model_used_for_student_answers": False,
        }
    else:
        try:
            semantic_transfer_academy = academy_runtime.run_cycle(
                teacher_client=teacher, limit=1,
            )
        except Exception as exc:
            semantic_transfer_academy = {
                "status": "failed", "error": f"{type(exc).__name__}:{exc}",
                "model_used_for_student_answers": False,
            }
    academy_metrics = academy_runtime.metrics()
    academy_gate = {
        "recent_free_transfer_attempts": int(
            academy_metrics.get("recent_free_transfer_attempts") or 0
        ),
        "recent_free_transfer_accuracy": float(
            academy_metrics.get("recent_free_transfer_accuracy") or 0.0
        ),
        "productive_concepts": int(
            academy_metrics.get("productive_use_concepts") or 0
        ),
    }
    academy_gate["passed"] = bool(
        academy_gate["recent_free_transfer_attempts"] >= 20
        and academy_gate["recent_free_transfer_accuracy"] >= float(
            stage.get("minimum_recent_free_transfer_accuracy") or 0.0
        )
        and academy_gate["productive_concepts"] >= int(
            stage.get("minimum_productive_concepts") or 0
        )
    )
    source_disjoint_required = bool(stage.get("require_source_disjoint"))
    source_disjoint_ready = (
        int(summary.get("source_disjoint_attempts") or 0) >= int(stage["minimum_attempts"])
        if source_disjoint_required else True
    )
    free_response_ready = (
        bool(exam.get("free_response")) if stage.get("require_free_response") else True
    )
    stage_passed = bool(
        summary["attempts"] >= int(stage["minimum_attempts"])
        and int(summary.get("unique_tasks") or 0) >= int(stage["minimum_attempts"])
        and (
            int(summary.get("unique_tasks") or 0) / max(1, int(summary.get("attempts") or 0))
            >= float(stage.get("minimum_unique_ratio") or 0.0)
        )
        and float(summary.get("retention_span_seconds") or 0.0)
            >= float(stage.get("minimum_retention_span_seconds") or 0.0)
        and float(summary["accuracy"] or 0.0) >= float(stage["pass_accuracy"])
        and float(exam.get("score") or 0.0) >= float(stage["pass_accuracy"])
        and bool(exam.get("expected_withheld"))
        and exam.get("model_used") is False
        and source_disjoint_ready
        and free_response_ready
        and exam.get("authority", {}).get("allow_learn")
        and (
            not stage.get("require_acquired_grounding")
            or str(stage.get("required_evidence_source") or "aion_acquired_concepts_v4")
                in set(summary.get("evidence_sources") or [])
        )
        and (
            not stage.get("minimum_recent_free_transfer_accuracy")
            or academy_gate["passed"]
        )
    )
    consecutive = min(2, int(state.get("consecutive_stage_passes") or 0) + 1) if stage_passed else 0
    promoted = bool(stage_passed and consecutive >= 2 and stage_index < len(CURRICULUM) - 1)
    new_index = stage_index + 1 if promoted else stage_index
    state.update({
        "schema_version": "aion.native_english_teacher.v4",
        "stage_index": new_index, "stage_id": CURRICULUM[new_index]["id"],
        "consecutive_stage_passes": 0 if promoted else consecutive,
        "cycles": int(state.get("cycles") or 0) + 1,
        "last_cycle_epoch": time.time(), "last_exam": exam,
        "last_teacher_error": teacher_error, "last_teacher_model": model,
        "curriculum_complete": bool(
            state.get("curriculum_complete")
            or (stage_index == len(CURRICULUM) - 1 and stage_passed and consecutive >= 2)
        ),
    })
    _save_json(_state_path(root), state)
    outcome = {
        "status": "completed" if exam["total"] else "awaiting_native_lexicon",
        "goal": GOAL, "stage_index": stage_index, "stage": dict(stage),
        "teacher_model": model, "teacher_available": teacher_error is None,
        "teacher_error": teacher_error, "lesson": lesson_record,
        "closed_book_exam": exam, "cumulative_exam": summary,
        "native_wordwall_learning": native_wordwall,
        "native_english_coverage": native_coverage,
        "native_conversation_improvement": native_improvement,
        "native_semantic_spider": native_semantic_spider,
        "semantic_transfer_academy": semantic_transfer_academy,
        "advanced_transfer_gate": academy_gate,
        "stage_passed": stage_passed, "promoted": promoted,
        "curriculum_complete": bool(state.get("curriculum_complete")),
        "next_stage": CURRICULUM[new_index]["id"],
        "separation_guarantees": {
            "teacher_saw_exam_answer_key": False,
            "teacher_graded_exam": False,
            "model_used_for_student_answers": False,
            "model_used_for_wordwall_answers": False,
            "lesson_counts_as_competence_evidence": False,
        },
    }
    audit = _audit_path(root)
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(outcome, sort_keys=True) + "\n")
    return outcome


def run_semantic_transfer_academy_cycle(*, repo_root: Path | str) -> dict[str, Any]:
    """Run the high-cadence academy lane without the full curriculum cycle."""
    root = Path(repo_root).resolve()
    batch_size = max(1, min(8, int(os.getenv("AION_SEMANTIC_ACADEMY_BATCH", "4"))))
    return NativeSemanticTransferAcademy(repo_root=root).run_cycle(
        teacher_client=_local_qwen_teacher, limit=batch_size,
    )


def run_native_language_workshop_cycle(*, repo_root: Path | str) -> dict[str, Any]:
    """Run one connected-language workshop with Qwen confined to authorship."""
    root = Path(repo_root).resolve()
    batch_size = max(1, min(10, int(os.getenv("AION_LANGUAGE_WORKSHOP_BATCH", "5"))))
    return NativeLanguageWorkshop(repo_root=root).run_cycle(
        teacher_client=_local_qwen_teacher, limit=batch_size,
    )


__all__ = ["CURRICULUM", "GOAL", "build_teacher_prompt", "run_teacher_cycle",
           "run_semantic_transfer_academy_cycle", "run_native_language_workshop_cycle"]
