import time
from collections import Counter
from pathlib import Path

from backend.modules.aion_cognition.native_english_practice_gym import (
    FAMILIES, NativeEnglishPracticeGym,
)
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


def _gym(tmp_path: Path, *, retry_delay: float = .01) -> NativeEnglishPracticeGym:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    records = (
        {"lemma": "calculate", "part_of_speech": "v", "definition": "compute a numerical result"},
        {"lemma": "inspect", "part_of_speech": "v", "definition": "examine carefully"},
        {"lemma": "report", "part_of_speech": "n", "definition": "a written account"},
        {"lemma": "sensor", "part_of_speech": "n", "definition": "a device that detects change"},
        {"lemma": "prepared", "part_of_speech": "a", "definition": "made ready in advance"},
        {"lemma": "unprepared", "part_of_speech": "a", "definition": "not made ready in advance"},
        {"lemma": "calmly", "part_of_speech": "r", "definition": "in a calm manner"},
        {"lemma": "semiannual", "part_of_speech": "a", "definition": "occurring twice each year"},
        {"lemma": "forward-looking", "part_of_speech": "s", "definition": "concerned with the future"},
        {"lemma": "proportionately", "part_of_speech": "r", "definition": "in proportion"},
        {"lemma": "comprehensively", "part_of_speech": "r", "definition": "in an all-inclusive manner"},
        {"lemma": "heave", "part_of_speech": "n", "definition": "an upward movement made with effort"},
        {"lemma": "fine-tune", "part_of_speech": "v", "definition": "make small adjustments to improve performance"},
        {"lemma": "custom-make", "part_of_speech": "v", "definition": "make for a particular customer"},
    )
    lexical.ingest_records(records, source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=lexical)
    for row in records:
        wall.encounter(row["lemma"])
    return NativeEnglishPracticeGym(
        repo_root=tmp_path, lexical=lexical, retry_delay_seconds=retry_delay,
    )


def test_practice_cycle_covers_all_learning_layers_without_awarding_mastery(tmp_path: Path):
    gym = _gym(tmp_path)
    result = gym.run_cycle(limit=20)

    assert result["attempted"] == 20
    assert set(result["families"]) == set(FAMILIES)
    assert result["model_used_for_student_answers"] is False
    assert result["counts_as_mastery"] is False
    assert all(row["counts_as_mastery"] is False for row in result["results"])
    assert all(row["model_used"] is False for row in result["results"])


def test_wrong_answer_stores_explanation_then_varied_closed_book_retest_clears_it(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("unprepared")
    first = gym._store_exercise(gym._build(concept, "context_completion", 0))
    original_student = gym._student_answer
    gym._student_answer = lambda _exercise: "prepared"
    failed = gym._attempt(first)
    gym._student_answer = original_student

    assert failed["correct"] is False
    assert failed["correction_revealed_after_answer"] is True
    assert "verified answer" in failed["feedback"]
    time.sleep(.02)
    retry_cycle = gym.run_cycle(limit=1)
    retry = retry_cycle["results"][0]

    assert retry["remedial_retry"] is True
    assert retry["exercise_id"] != first["exercise_id"]
    assert retry["correct"] is True
    assert retry["reward"] == 2
    assert gym.metrics()["corrections_cleared"] == 1


def test_native_sentence_production_is_graded_by_rubric_not_exact_string(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("calculate")
    exercise = gym._build(concept, "sentence_construction", 0)

    score, correct = gym._grade(exercise, "Mireya calculated the result clearly.")

    assert correct is True
    assert score >= .8


def test_event_noun_rejects_semantically_awkward_inspection_template(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("heave")
    exercise = gym._build(concept, "sentence_construction", 0)

    bad_score, bad = gym._grade(exercise, "Amara inspected the heave.")
    good_score, good = gym._grade(exercise, "Amara observed the heave.")

    assert "observed the heave" in exercise["answer_key"]
    assert bad is False
    assert bad_score < .8
    assert good is True
    assert good_score >= .8


def test_practice_concentrates_on_cohorts_and_releases_transfer_ready_concepts(tmp_path: Path):
    gym = _gym(tmp_path)

    result = gym.run_cycle(limit=20)
    concept_ids = {row["concept_id"] for row in result["results"]}
    metrics = gym.metrics()

    assert len(concept_ids) == 2
    assert metrics["transfer_ready_concepts"] == 2
    assert metrics["nearly_transfer_ready_concepts"] == 0
    for concept_id in concept_ids:
        readiness = gym._readiness(concept_id)
        assert readiness["ready"] is True
        assert readiness["components_passed"] == readiness["components_required"]


def test_failed_family_is_bounded_per_cycle_instead_of_hammered(tmp_path: Path):
    gym = _gym(tmp_path)
    original_student = gym._student_answer

    def fail_reading(exercise):
        if exercise["family"] == "reading_comprehension":
            return "deliberately wrong"
        return original_student(exercise)

    gym._student_answer = fail_reading
    result = gym.run_cycle(limit=20)
    counts = Counter((row["concept_id"], row["family"]) for row in result["results"])

    assert max(count for (_, family), count in counts.items()
               if family == "reading_comprehension") == 1
    assert len({row["concept_id"] for row in result["results"]}) >= 2


def test_hyphenated_concept_keeps_its_identity_and_grammatical_role(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("forward-looking")
    exercise = gym._store_exercise(
        gym._build(concept, "sentence_construction", 0),
    )

    result = gym._attempt(exercise)

    assert result["correct"] is True
    assert "was forward-looking" in result["answer"]


def test_semantic_matching_ignores_generic_prompt_scaffolding(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("proportionately")
    exercise = gym._build(concept, "context_completion", 0)
    view = {key: exercise[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}

    assert gym._student_answer(view) == "proportionately"


def test_reading_comprehension_asks_for_and_recovers_adverbial_manner(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("calmly")
    exercise = gym._build(concept, "reading_comprehension", 3)
    view = {key: exercise[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}

    assert "How did" in exercise["prompt"]
    assert gym._student_answer(view) == "calmly"


def test_reading_comprehension_recovers_explicit_copular_property_when_parse_index_lags(
    tmp_path: Path,
):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("prepared")
    exercise = gym._build(concept, "reading_comprehension", 2)
    view = {key: exercise[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}
    gym.transfer.parse = lambda _text: {"frame": {}, "tokens": [], "clauses": []}

    assert gym._student_answer(view) == "prepared"


def test_transformation_disambiguates_surface_from_acquired_meaning_and_accepts_variant(
    tmp_path: Path,
):
    gym = _gym(tmp_path)
    records = (
        {"lemma": "barde", "part_of_speech": "v", "definition": "put caparison on a horse"},
        {"lemma": "bard", "part_of_speech": "v", "definition": "cover meat with fat before roasting"},
        {"lemma": "lambaste", "part_of_speech": "v", "definition": "criticize severely"},
        {"lemma": "lambast", "part_of_speech": "v", "definition": "criticize severely"},
    )
    gym.lexical.ingest_records(records, source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=gym.lexical)
    for row in records:
        wall.encounter(row["lemma"])
    barde = gym._concept_by_lemma("barde")
    barde_exercise = gym._build(barde, "sentence_transformation", 0)
    barde_view = {key: barde_exercise[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}
    assert "did not barde" in gym._student_answer(barde_view)

    lambaste = gym._concept_by_lemma("lambaste")
    variant_exercise = gym._build(lambaste, "sentence_transformation", 0)
    variant_answer = variant_exercise["answer_key"].replace("lambaste", "lambast")
    score, correct = gym._grade(variant_exercise, variant_answer)
    assert correct is True
    assert score == 1.0

    reading = gym._build(barde, "reading_comprehension", 0)
    reading_view = {key: reading[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}
    assert gym._student_answer(reading_view) == "barde"


def test_hyphenated_verb_transformation_uses_acquired_lemma_and_returns_answer(
    tmp_path: Path,
):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("fine-tune")
    exercise = gym._build(concept, "sentence_transformation", 0)
    view = {key: exercise[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}

    answer = gym._student_answer(view)

    assert answer == exercise["answer_key"]
    assert "did not fine-tune" in answer

    irregular = gym._build(
        gym._concept_by_lemma("custom-make"), "sentence_transformation", 0,
    )
    irregular_view = {key: irregular[key] for key in (
        "concept_id", "lemma", "family", "activity_mode", "variant", "prompt",
        "choices", "metadata",
    )}
    assert "custom-made" in irregular["prompt"]
    assert gym._student_answer(irregular_view) == irregular["answer_key"]


def test_failed_concept_cools_until_its_sealed_retry_is_due(tmp_path: Path):
    gym = _gym(tmp_path, retry_delay=60)
    concept = gym._concept_by_lemma("unprepared")
    exercise = gym._store_exercise(gym._build(concept, "context_completion", 0))
    original_student = gym._student_answer
    gym._student_answer = lambda _exercise: "prepared"
    gym._attempt(exercise)
    gym._student_answer = original_student

    candidates = gym._cohort_candidates(100, exclude=set())

    assert concept["concept_id"] not in {row["concept_id"] for row in candidates}


def test_choices_do_not_reveal_answer_through_a_fixed_first_position(tmp_path: Path):
    gym = _gym(tmp_path)
    concept = gym._concept_by_lemma("calculate")
    exercise = gym._build(concept, "context_completion", 1)

    assert exercise["choices"][0] != "calculate"


def test_dictionary_punctuation_artifacts_are_not_used_as_practice_concepts(tmp_path: Path):
    gym = _gym(tmp_path)
    assert gym._usable_concept({"lemma": "o.k.", "part_of_speech": "a"}) is False
    assert gym._usable_concept({"lemma": "'tween", "part_of_speech": "r"}) is False
    assert gym._usable_concept({"lemma": "forward-looking", "part_of_speech": "s"}) is True
