from pathlib import Path
import time

from backend.modules.aion_cognition.native_english_practice_gym import NativeEnglishPracticeGym
from backend.modules.aion_cognition.native_language_workshop import FAMILIES, NativeLanguageWorkshop
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


def _workshop(tmp_path: Path) -> NativeLanguageWorkshop:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    records = (
        {"lemma": "calculate", "part_of_speech": "v", "definition": "compute a result"},
        {"lemma": "inspect", "part_of_speech": "v", "definition": "examine carefully"},
        {"lemma": "report", "part_of_speech": "n", "definition": "a written account"},
        {"lemma": "prepared", "part_of_speech": "a", "definition": "made ready"},
        {"lemma": "calmly", "part_of_speech": "r", "definition": "in a calm manner"},
    )
    lexical.ingest_records(records, source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=lexical)
    concept_ids = []
    for row in records:
        concept_ids.append(wall.encounter(row["lemma"])[0]["concept_id"])
    gym = NativeEnglishPracticeGym(repo_root=tmp_path, lexical=lexical)
    with gym._connect() as connection:
        for concept_id in concept_ids:
            for family, correct in (
                ("meaning_discrimination", 2), ("context_completion", 2),
                ("sentence_construction", 2), ("sentence_transformation", 1),
                ("reading_comprehension", 1),
            ):
                connection.execute(
                    """INSERT INTO native_english_practice_progress(
                       concept_id,family,attempts,correct,rewards,corrections,
                       retests_passed,consecutive_passes,last_attempt_epoch,next_due_epoch)
                       VALUES(?,?,?,?,0,0,0,?,0,0)""",
                    (concept_id, family, correct, correct, correct),
                )
    return NativeLanguageWorkshop(repo_root=tmp_path, lexical=lexical,
                                  retry_delay_seconds=.01)


def test_workshop_runs_weighted_connected_language_without_student_model(tmp_path: Path):
    workshop = _workshop(tmp_path)
    results = [workshop.run_cycle(limit=5) for _ in range(4)]
    metrics = workshop.metrics()

    assert sum(result["attempted"] for result in results) == 20
    assert set(metrics["families"]) == set(FAMILIES)
    assert metrics["allocation"] == {
        "clause_inference": .30, "native_generation": .25,
        "paraphrase_transformation": .20, "multi_turn_dialogue": .15,
        "delayed_vocabulary": .10,
    }
    assert all(result["model_used_for_student_answers"] is False for result in results)
    assert all(result["counts_as_mastery"] is False for result in results)
    assert all(row["model_used"] is False for result in results for row in result["results"])


def test_invalid_teacher_material_is_rejected_and_safely_compiled(tmp_path: Path):
    workshop = _workshop(tmp_path)

    def bad_teacher(_prompt: str):
        return {"model": "qwen-test", "content": '{"exercises":[{"concept_id":"wrong"}]}' }

    result = workshop.run_cycle(teacher_client=bad_teacher, limit=1)

    assert result["attempted"] == 1
    assert result["model_used_for_student_answers"] is False
    assert result["results"][0]["teacher_generated"] is False


def test_workshop_drains_correction_backlog_before_new_material(tmp_path: Path):
    workshop = _workshop(tmp_path)
    candidates = workshop._candidates(5)
    with workshop._connect() as connection:
        for index, concept in enumerate(candidates):
            connection.execute(
                """INSERT INTO native_language_workshop_remediation(
                   obligation_id,concept_id,family,expected_answer,answer_reason,
                   status,due_epoch,created_epoch,cleared_epoch,retry_count)
                   VALUES(?,?,?,?,?,'due',?,?,NULL,0)""",
                (f"due-{index}", concept["concept_id"], "clause_inference", "inspect",
                 "verified correction", time.time() - 1, time.time() - 2),
            )

    result = workshop.run_cycle(limit=5)

    assert result["due_before_cycle"] == 5
    assert result["retry_slots"] == 4
    assert result["remedial_retries"] == 4


def test_generation_grade_rejects_wrong_tense_even_with_right_words(tmp_path: Path):
    workshop = _workshop(tmp_path)
    concept = workshop._candidates(1)[0]
    exercise = workshop._compile(concept, "native_generation", 0)
    frame = dict(exercise["frame"])
    frame["tense"] = "future"
    wrong_tense_answer = workshop._realize(frame)

    score, correct = workshop._grade(exercise, wrong_tense_answer, {})

    assert correct is False
    assert score <= .85


def test_dialogue_uses_grounded_acquired_capsule_and_resolves_follow_up(tmp_path: Path):
    workshop = _workshop(tmp_path)
    concept = workshop._candidates(1)[0]
    exercise = workshop._compile(concept, "multi_turn_dialogue", 0)

    answer, evidence = workshop._answer(exercise)

    assert concept["native_gloss"] in answer
    assert evidence["answer_source"] == "acquired_concept_memory"
    assert evidence["dialogue_turns"][1]["resolved_reference"] == concept["lemma"]
    assert evidence["model_used"] is False


def test_delayed_vocabulary_accepts_verified_inflected_surface(tmp_path: Path):
    workshop = _workshop(tmp_path)
    concept = next(row for row in workshop._candidates(10) if row["lemma"] == "calculate")
    exercise = workshop._compile(concept, "delayed_vocabulary", 0)

    score, correct = workshop._grade(exercise, "calculated", {})

    assert correct is True
    assert score == 1.0


def test_clause_inference_questions_the_targets_actual_semantic_role(tmp_path: Path):
    workshop = _workshop(tmp_path)
    concept = next(row for row in workshop._candidates(10) if row["lemma"] == "prepared")
    exercise = workshop._compile(concept, "clause_inference", 0)

    answer, evidence = workshop._answer(exercise)
    score, correct = workshop._grade(exercise, answer, evidence)

    assert "Which property" in exercise["prompt"]
    assert answer == "prepared"
    assert correct is True
    assert score == 1.0


def test_workshop_excludes_closed_class_words_from_content_generation(tmp_path: Path):
    workshop = _workshop(tmp_path)
    concept_ids = [row["concept_id"] for row in workshop._candidates(50)]
    lexical = workshop.lexical
    lexical.ingest_records(
        ({"lemma": "not", "part_of_speech": "r", "definition": "a marker of negation"},),
        source="test", require_authority=False,
    )
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=lexical)
    not_id = wall.encounter("not")[0]["concept_id"]
    gym = NativeEnglishPracticeGym(repo_root=tmp_path, lexical=lexical)
    with gym._connect() as connection:
        for family, correct in (
            ("meaning_discrimination", 2), ("context_completion", 2),
            ("sentence_construction", 2), ("sentence_transformation", 1),
            ("reading_comprehension", 1),
        ):
            connection.execute(
                """INSERT INTO native_english_practice_progress(
                   concept_id,family,attempts,correct,rewards,corrections,
                   retests_passed,consecutive_passes,last_attempt_epoch,next_due_epoch)
                   VALUES(?,?,?,?,0,0,0,?,0,0)""",
                (not_id, family, correct, correct, correct),
            )

    assert not_id not in concept_ids
    assert not_id not in {row["concept_id"] for row in workshop._candidates(100)}
