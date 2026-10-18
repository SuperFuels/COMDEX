import json
import sqlite3
from pathlib import Path

from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence,
)
from backend.modules.aion_cognition.native_english_teacher import (
    CURRICULUM,
    _migrate_state,
    run_teacher_cycle,
)
from backend.modules.hexcore.native_english_competency_portfolio import native_english_runner


RECORDS = (
    {
        "lemma": "calm", "definition": "A peaceful state without agitation.",
        "definitions": ["A peaceful state without agitation."],
        "examples": ["The calm room helped everyone think."],
        "synonyms": ["peaceful"], "antonyms": ["agitated"],
    },
    {
        "lemma": "peaceful", "definition": "Free from disturbance or conflict.",
        "definitions": ["Free from disturbance or conflict."],
        "examples": ["The peaceful garden was quiet."],
        "synonyms": ["calm"], "antonyms": ["agitated"],
    },
    {
        "lemma": "agitated", "definition": "Troubled, disturbed, or restless.",
        "definitions": ["Troubled, disturbed, or restless."],
        "examples": ["The agitated crowd became restless."],
        "synonyms": ["restless"], "antonyms": ["calm"],
    },
    {
        "lemma": "restless", "definition": "Unable to remain still or calm.",
        "definitions": ["Unable to remain still or calm."],
        "examples": ["The restless child moved constantly."],
        "synonyms": ["agitated"], "antonyms": ["peaceful"],
    },
)


def _runtime(tmp_path: Path) -> NativeLexicalIntelligence:
    runtime = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test_authority"},
    )
    outcome = runtime.ingest_records(RECORDS, source="sealed_test_lexicon")
    assert outcome["stored"] == 4
    return runtime


def test_native_lexicon_answers_without_a_model(tmp_path: Path):
    runtime = _runtime(tmp_path)

    definition = runtime.answer("What does calm mean?")
    synonym = runtime.answer("Synonym for calm")
    comparison = runtime.answer("Compare calm and agitated")

    assert definition["answered"] is True
    assert "peaceful state" in definition["answer"]
    assert synonym["answered"] is True
    assert "peaceful" in synonym["answer"]
    assert comparison["answered"] is True
    assert comparison["evidence"]["direct_relation"]["relation"] == "antonym"


def test_practice_hides_expected_answer_until_after_student_response(tmp_path: Path):
    runtime = _runtime(tmp_path)
    tasks = runtime.generate_tasks(family="synonym_choice", limit=2, seed=3)
    assert tasks
    student_view = tasks[0].student_view()
    assert "expected" not in student_view
    assert runtime.answer_task(student_view) == tasks[0].expected

    outcome = runtime.run_practice_cycle(
        family="synonym_choice", limit=2, seed=3,
        project_family="native_lexical_synonym_holdout_v1",
    )
    assert outcome["model_used"] is False
    assert outcome["cloud_used"] is False
    assert outcome["expected_withheld"] is True
    assert outcome["passed"] is True
    assert runtime.stats()["verified_correct_attempts"] >= 1


def test_learning_authority_blocks_reinforcement_but_not_reading(tmp_path: Path):
    runtime = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": False, "deny_reason": "test_deny"},
    )
    seeded = runtime.ingest_records(
        RECORDS, source="sealed_test_lexicon", require_authority=False,
    )
    assert seeded["stored"] == 4
    assert runtime.answer("Define calm")["answered"] is True

    outcome = runtime.run_practice_cycle(
        family="synonym_choice", limit=1, seed=2,
        project_family="native_lexical_governance_test",
    )
    assert outcome["passed"] is False
    assert outcome["authority"]["deny_reason"] == "test_deny"


def test_qwen_teaches_but_is_disconnected_from_native_exam(tmp_path: Path):
    runtime = _runtime(tmp_path)
    prompts: list[str] = []

    def fake_qwen(prompt: str):
        prompts.append(prompt)
        return {
            "model": "qwen-test-local",
            "content": (
                '{"objective":"contrast states","explanation":"study",'
                '"contrasts":[],"examples":[],"guided_practice":[],'
                '"referenced_lemmas":["calm","agitated"],"next_focus":"context"}'
            ),
        }

    outcome = run_teacher_cycle(
        repo_root=tmp_path, teacher_client=fake_qwen, student=runtime, exam_limit=4,
    )

    assert len(prompts) == 1
    assert "FULL CURRICULUM" in prompts[0]
    assert "Qwen is a teacher only" in prompts[0]
    assert outcome["teacher_model"] == "qwen-test-local"
    assert outcome["lesson"]["counts_as_exam_evidence"] is False
    assert outcome["closed_book_exam"]["model_used"] is False
    assert outcome["closed_book_exam"]["expected_withheld"] is True
    assert outcome["separation_guarantees"] == {
        "teacher_saw_exam_answer_key": False,
        "teacher_graded_exam": False,
        "model_used_for_student_answers": False,
        "model_used_for_wordwall_answers": False,
        "lesson_counts_as_competence_evidence": False,
    }


def test_mixed_exam_attempts_count_toward_the_mixed_curriculum_stage(tmp_path: Path):
    runtime = _runtime(tmp_path)
    outcome = runtime.run_practice_cycle(
        family="mixed", limit=4, seed=11, offset=0,
        project_family="native_english_mixed_transfer_v1",
    )

    summary = runtime.practice_summary(family="mixed")

    assert outcome["total"] > 0
    assert summary["attempts"] == outcome["total"]
    assert summary["unique_tasks"] == outcome["total"]
    assert summary["model_used_for_answers"] is False


def test_unbounded_practice_summary_preserves_delayed_retention_history(tmp_path: Path):
    runtime = _runtime(tmp_path)
    first = runtime.run_practice_cycle(
        family="mixed", limit=2, seed=21, offset=0,
        project_family="native_english_retention_window_test",
    )
    second = runtime.run_practice_cycle(
        family="mixed", limit=2, seed=22, offset=2,
        project_family="native_english_retention_window_test",
    )
    assert first["total"] == second["total"] == 2
    with runtime._connect() as connection:
        oldest = connection.execute(
            "SELECT task_id FROM practice_attempts ORDER BY created_epoch LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE practice_attempts SET created_epoch=created_epoch-90000 WHERE task_id=?",
            (oldest,),
        )

    recent = runtime.practice_summary(family="mixed", limit=2)
    cumulative = runtime.practice_summary(family="mixed", limit=None)

    assert recent["attempts"] == 2
    assert recent["retention_span_seconds"] < 86400
    assert cumulative["attempts"] == 4
    assert cumulative["retention_span_seconds"] >= 86400


def test_sentence_and_discourse_exams_are_held_out_and_model_free(tmp_path: Path):
    runtime = _runtime(tmp_path)

    sentence = runtime.run_practice_cycle(
        family="sentence_semantics", limit=20, seed=1, offset=0,
        project_family="native_sentence_roles_test",
    )
    discourse = runtime.run_practice_cycle(
        family="discourse_reasoning", limit=20, seed=2, offset=0,
        project_family="native_discourse_reasoning_test",
    )

    for outcome in (sentence, discourse):
        assert outcome["total"] == 20
        assert outcome["correct"] == 20
        assert outcome["expected_withheld"] is True
        assert outcome["model_used"] is False
        assert outcome["cloud_used"] is False
        assert outcome["source_disjoint"] is True
        assert all(row["source_disjoint"] for row in outcome["attempts"])

    sentence_summary = runtime.practice_summary(family="sentence_semantics")
    discourse_summary = runtime.practice_summary(family="discourse_reasoning")
    assert sentence_summary["unique_tasks"] == 20
    assert discourse_summary["unique_tasks"] == 20
    assert sentence_summary["source_disjoint_attempts"] == 20
    assert discourse_summary["source_disjoint_attempts"] == 20


def test_advanced_english_banks_are_unique_free_response_and_model_free(tmp_path: Path):
    runtime = _runtime(tmp_path)
    families = (
        "compositional_syntax", "paragraph_comprehension", "unseen_document_qa",
        "dialogue_tracking", "ambiguity_pragmatics", "explanation_generation",
        "error_correction", "cross_domain_transfer",
    )

    for family in families:
        tasks = runtime.generate_tasks(family=family, limit=128, seed=7, offset=0)
        assert len(tasks) == 128
        assert len({task.task_id for task in tasks}) == 128
        assert all(not task.choices for task in tasks)
        assert all("expected" not in task.student_view() for task in tasks)
        outcome = runtime.run_practice_cycle(
            family=family, limit=16, seed=7, offset=0,
            project_family=f"native_english_{family}_v3_test",
        )
        assert outcome["total"] == 16
        assert outcome["correct"] == 16
        assert outcome["free_response"] is True
        assert outcome["response_modes"] == ["free_response"]
        assert outcome["model_used"] is False
        assert outcome["cloud_used"] is False
        assert outcome["expected_withheld"] is True
        assert outcome["source_disjoint"] is True


def test_completed_foundation_migrates_into_advanced_curriculum():
    migrated = _migrate_state({
        "schema_version": "aion.native_english_teacher.v2",
        "stage_index": 6,
        "stage_id": "discourse_reasoning",
        "consecutive_stage_passes": 2,
        "curriculum_complete": True,
        "cycles": 40,
    })

    assert len(CURRICULUM) == 22
    assert migrated["schema_version"] == "aion.native_english_teacher.v4"
    assert migrated["foundation_curriculum_complete"] is True
    assert migrated["stage_index"] == 7
    assert migrated["stage_id"] == "compositional_syntax"
    assert migrated["curriculum_complete"] is False


def test_completed_v3_curriculum_opens_fresh_productive_track():
    migrated = _migrate_state({
        "schema_version": "aion.native_english_teacher.v3",
        "stage_index": 14,
        "stage_id": "cross_domain_transfer",
        "consecutive_stage_passes": 2,
        "curriculum_complete": True,
        "cycles": 400,
    })

    assert migrated["schema_version"] == "aion.native_english_teacher.v4"
    assert migrated["stage_index"] == 15
    assert migrated["stage_id"] == "productive_semantic_transfer"
    assert migrated["intermediate_curriculum_complete"] is True
    assert migrated["curriculum_complete"] is False


def test_open_advanced_tasks_remain_fresh_across_cycles(tmp_path: Path):
    runtime = _runtime(tmp_path)
    families = (
        "scope_counterfactual_reasoning", "multi_source_evidence_synthesis",
        "paraphrase_revision", "conversation_belief_revision",
        "adversarial_uncertainty", "delayed_open_generalisation",
    )

    for family in families:
        first = runtime.generate_tasks(family=family, limit=12, seed=3, offset=0)
        second = runtime.generate_tasks(family=family, limit=12, seed=3, offset=12)
        assert len(first) == len(second) == 12
        assert not ({task.task_id for task in first} & {task.task_id for task in second})
        outcome = runtime.run_practice_cycle(
            family=family, limit=12, seed=3, offset=0,
            project_family=f"native_english_{family}_v4_test",
        )
        assert outcome["total"] == 12
        assert outcome["free_response"] is True
        assert outcome["expected_withheld"] is True
        assert outcome["model_used"] is False
        assert outcome["source_disjoint"] is True


def test_curriculum_cycle_skips_previously_recorded_task_ids(tmp_path: Path):
    runtime = _runtime(tmp_path)
    first = runtime.run_practice_cycle(
        family="delayed_open_generalisation", limit=8, seed=7, offset=0,
        project_family="native_english_delayed_open_generalisation_v4_test",
        require_unseen_tasks=True,
    )
    second = runtime.run_practice_cycle(
        family="delayed_open_generalisation", limit=8, seed=7, offset=0,
        project_family="native_english_delayed_open_generalisation_v4_test",
        require_unseen_tasks=True,
    )

    assert first["total"] == second["total"] == 8
    assert not ({row["task_id"] for row in first["attempts"]}
                & {row["task_id"] for row in second["attempts"]})


def test_teacher_can_advance_through_sentence_and_discourse_stages(tmp_path: Path):
    runtime = _runtime(tmp_path)
    state_path = tmp_path / "data/aion/native_english_teacher/state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "schema_version": "aion.native_english_teacher.v2",
        "stage_index": 5,
        "stage_id": "sentence_semantics",
        "consecutive_stage_passes": 0,
        "cycles": 0,
    }))

    def teacher(_prompt: str):
        return {
            "model": "qwen-test-local",
            "content": '{"objective":"vary grammar","referenced_lemmas":[]}',
        }

    sentence_outcomes = [
        run_teacher_cycle(
            repo_root=tmp_path, teacher_client=teacher, student=runtime, exam_limit=16,
        ) for _ in range(5)
    ]
    assert sentence_outcomes[-1]["promoted"] is True
    assert sentence_outcomes[-1]["next_stage"] == "discourse_reasoning"

    discourse_outcomes = [
        run_teacher_cycle(
            repo_root=tmp_path, teacher_client=teacher, student=runtime, exam_limit=16,
        ) for _ in range(6)
    ]
    assert discourse_outcomes[-1]["stage_passed"] is True
    assert discourse_outcomes[-1]["promoted"] is True
    assert discourse_outcomes[-1]["next_stage"] == "compositional_syntax"
    assert discourse_outcomes[-1]["curriculum_complete"] is False
    assert runtime.practice_summary(family="discourse_reasoning")["unique_tasks"] >= 80


def test_progressive_english_lesson_uses_native_lexical_authority(
    tmp_path: Path, monkeypatch,
):
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    runtime = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    descriptors = (
        "amber", "birch", "cedar", "dahlia", "elmwood", "fern", "granite", "harbor",
        "island", "juniper", "keystone", "lagoon", "meadow", "nectar", "orchid",
        "pebble", "quartz", "river", "summit", "timber",
    )
    expanded = list(RECORDS) + [
        {
            "lemma": f"concept{index}",
            "definition": f"Verified meaning associated with {descriptor}.",
            "examples": [f"The {descriptor} example is distinct."],
        }
        for index, descriptor in enumerate(descriptors)
    ]
    runtime.ingest_records(expanded, source="sealed_test_lexicon", require_authority=False)

    result = native_english_runner({
        "_repo_root": str(tmp_path),
        "requirement": {"kind": "lesson", "subskills": ["lexical_grounding"]},
    }, [])

    assert result["passed"] is True
    assert result["project_family"] == "native_english_lesson_definition_match_v3_a"
    assert result["evidenced_subskills"] == ["lexical_grounding"]
    assert result["gate"]["source_disjoint_transfer"] is False


def test_progressive_english_retries_when_shared_store_is_busy(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(tmp_path / "native.sqlite3"))

    def busy(*args, **kwargs):
        raise sqlite3.OperationalError("Aion SQLite transaction gate timed out")

    monkeypatch.setattr(NativeLexicalIntelligence, "run_practice_cycle", busy)
    result = native_english_runner({
        "_repo_root": str(tmp_path),
        "requirement": {"kind": "knowledge_test", "subskills": ["lexical_grounding"]},
    }, [])

    assert result["status"] == "learning_store_busy"
    assert result["retryable"] is True
    assert result["passed"] is False
