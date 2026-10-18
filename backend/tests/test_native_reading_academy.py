from pathlib import Path
import sqlite3

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_reading_academy import NativeReadingAcademy
from backend.modules.aion_cognition.native_semantic_transfer_academy import (
    NativeSemanticTransferAcademy,
)


def _academy(tmp_path: Path) -> NativeReadingAcademy:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "repair", "part_of_speech": "v", "definition": "restore to working order"},
        {"lemma": "robot", "part_of_speech": "n", "definition": "a programmable machine"},
        {"lemma": "laboratory", "part_of_speech": "n", "definition": "a place for experiments"},
        {"lemma": "inspect", "part_of_speech": "v", "definition": "examine carefully"},
    ), source="test", require_authority=False)
    return NativeReadingAcademy(
        repo_root=tmp_path, lexical=lexical,
        retry_delay_seconds=1, retention_delay_seconds=1,
        online_enabled=False,
    )


def test_real_text_is_stored_in_order_with_provenance(tmp_path: Path):
    academy = _academy(tmp_path)
    first = academy.ingest_text(
        title="Workshop Notes", author="Owner", subject="engineering",
        license_name="owner-provided", source_ref="owner:test",
        text=("Yesterday, Leona repaired the robot in the laboratory. "
              "Afterwards, Tavian inspected the machine carefully."),
    )
    duplicate = academy.ingest_text(
        title="Workshop Notes Copy",
        text=("Yesterday, Leona repaired the robot in the laboratory. "
              "Afterwards, Tavian inspected the machine carefully."),
    )

    assert first["status"] == "queued"
    assert first["sentences"] == 2
    assert duplicate["status"] == "already_ingested"
    with sqlite3.connect(academy.database_path) as connection:
        rows = connection.execute(
            "SELECT sentence_index,text FROM native_reading_sentences WHERE source_id=? ORDER BY sentence_index",
            (first["source_id"],),
        ).fetchall()
    assert rows == [
        (0, "Yesterday, Leona repaired the robot in the laboratory."),
        (1, "Afterwards, Tavian inspected the machine carefully."),
    ]


def test_reading_hot_paths_have_bounded_lookup_indexes(tmp_path: Path):
    academy = _academy(tmp_path)
    with sqlite3.connect(academy.database_path) as connection:
        indexes = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }

    assert "native_reading_claim_signature" in indexes
    assert "native_reading_context_signature" in indexes


def test_model_free_reading_creates_experience_claim_and_retention(tmp_path: Path):
    academy = _academy(tmp_path)
    academy.ingest_text(
        title="Repair Log", author="Owner", subject="engineering",
        text="Yesterday, Leona repaired the robot in the laboratory.",
    )

    outcome = academy.run_cycle(limit=1, discover_words=0)
    metrics = academy.metrics()

    assert outcome["model_used_for_reading"] is False
    assert outcome["counts_as_mastery"] is False
    assert outcome["exercises_attempted"] == 1
    assert outcome["exercises_correct"] == 1
    assert outcome["claims_recorded"] == 1
    assert metrics["distinct_words_experienced"] >= 3
    assert metrics["provenanced_claims"] == 1
    assert metrics["retention_scheduled"] == 1


def test_reading_tests_acquired_meaning_in_authentic_context(tmp_path: Path):
    academy = _academy(tmp_path)
    acquired = academy.wordwall.encounter("repair", teacher_lesson_id="test:dictionary")
    assert acquired
    assert academy.wordwall.encounter("robot", teacher_lesson_id="test:dictionary")
    academy.ingest_text(
        title="Context Log", author="Owner", subject="engineering",
        text="Yesterday, Leona repaired the robot in the laboratory.",
    )

    outcome = academy.run_cycle(limit=1, discover_words=0)
    metrics = academy.metrics()

    assert outcome["exercises_attempted"] == 1
    assert outcome["results"][0]["family"] == "contextual_vocabulary"
    assert outcome["results"][0]["correct"] is True
    assert outcome["results"][0]["context_evidence"]["concept_id"] == acquired[0]["concept_id"]
    assert metrics["verified_context_attempts"] == 1
    assert metrics["concepts_verified_in_context"] == 1
    assert metrics["model_used_for_reading"] is False


def test_two_distinct_reading_contexts_release_concept_to_transfer_not_mastery(tmp_path: Path):
    academy = _academy(tmp_path)
    acquired = academy.wordwall.encounter("repair", teacher_lesson_id="test:dictionary")[0]
    NativeSemanticTransferAcademy(
        repo_root=tmp_path, lexical=academy.lexical, transfer=academy.transfer,
    )
    academy.ingest_text(
        title="Repair Journal One", text="Yesterday, Leona repaired the robot carefully.",
    )
    academy.ingest_text(
        title="Repair Journal Two", text="At sunrise, Tavian repaired the machine calmly.",
    )

    academy.run_cycle(limit=1, discover_words=0)
    academy.run_cycle(limit=1, discover_words=0)

    with sqlite3.connect(academy.database_path) as connection:
        stage = connection.execute(
            "SELECT stage FROM acquired_concepts WHERE concept_id=?",
            (acquired["concept_id"],),
        ).fetchone()[0]
        progress = connection.execute(
            """SELECT guided_successes,free_successes,capability_stage
               FROM native_semantic_transfer_concept_progress WHERE concept_id=?""",
            (acquired["concept_id"],),
        ).fetchone()
    assert stage == "recalled"
    assert progress == (2, 0, "recalled")


def test_wrong_answer_gets_reworded_closed_book_retry(tmp_path: Path):
    academy = _academy(tmp_path)
    academy.ingest_text(
        title="Inspection Log", author="Owner", subject="engineering",
        text="Yesterday, Leona inspected the robot in the laboratory.",
    )
    native_answer = academy.transfer.answer
    academy.transfer.answer = lambda material, question: {
        "answer": "Tavian", "confidence": 0.2, "model_used": False,
    }
    failed = academy.run_cycle(limit=1, discover_words=0)
    assert failed["exercises_correct"] == 0
    assert academy.metrics()["corrections_due"] == 1

    with sqlite3.connect(academy.database_path) as connection:
        connection.execute(
            "UPDATE native_reading_exercises SET due_epoch=0 WHERE status='correction_due'"
        )
    academy.transfer.answer = native_answer
    retried = academy.run_cycle(limit=1, discover_words=0)

    assert retried["retests_attempted"] == 1
    assert retried["retests_cleared"] == 1
    assert retried["results"][0]["retest"] is True
    assert retried["results"][0]["correct"] is True
    assert academy.metrics()["corrections_due"] == 0
    assert academy.metrics()["retention_scheduled"] == 1


def test_failed_retries_are_bounded_and_do_not_reproduce_queue_rows(tmp_path: Path):
    academy = _academy(tmp_path)
    academy.wordwall.encounter("inspect", teacher_lesson_id="test:dictionary")
    academy.wordwall.encounter("robot", teacher_lesson_id="test:dictionary")
    academy.ingest_text(
        title="Bounded Retry Log",
        text="Yesterday, Leona inspected the robot in the laboratory.",
    )
    academy.transfer.answer = lambda material, question: {
        "answer": "unsupported", "confidence": 0.1, "model_used": False,
    }
    academy.run_cycle(limit=1, discover_words=0)

    for expected_retry in (1, 2):
        with sqlite3.connect(academy.database_path) as connection:
            connection.execute(
                "UPDATE native_reading_exercises SET due_epoch=0 WHERE status='correction_due'"
            )
        academy.run_cycle(limit=1, discover_words=0)
        with sqlite3.connect(academy.database_path) as connection:
            due_rows, retry_count = connection.execute(
                """SELECT COUNT(*),MAX(retry_count) FROM native_reading_exercises
                   WHERE status='correction_due'"""
            ).fetchone()
        assert due_rows == 1
        assert retry_count == expected_retry

    with sqlite3.connect(academy.database_path) as connection:
        connection.execute(
            "UPDATE native_reading_exercises SET due_epoch=0 WHERE status='correction_due'"
        )
    academy.run_cycle(limit=1, discover_words=0)

    assert academy.metrics()["corrections_due"] == 0
    assert academy.metrics()["diagnostic_parked"] == 1


def test_watched_library_imports_supported_local_files(tmp_path: Path):
    academy = _academy(tmp_path)
    library = tmp_path / "data/aion/reading_library"
    source = library / "science-notes.txt"
    source.write_text(
        "Mira inspected the sample in the laboratory. The result confirmed the earlier report.",
        encoding="utf-8",
    )

    imported = academy.scan_library()

    assert len(imported) == 1
    assert imported[0]["title"] == "science-notes"
    assert academy.metrics()["sources"] == 1


def test_cycle_lease_prevents_two_readers_claiming_the_same_sentence(tmp_path: Path):
    academy = _academy(tmp_path)
    academy.ingest_text(
        title="Lease Test", text="Leona repaired the robot in the laboratory.",
    )
    assert academy._acquire_cycle_lease() is True
    try:
        outcome = academy.run_cycle(limit=1, discover_words=0)
    finally:
        academy._release_cycle_lease()

    assert outcome["status"] == "busy"
    assert academy.metrics()["sentences_processed"] == 0


def test_cycle_lease_recovers_immediately_when_owner_process_is_gone(tmp_path: Path):
    academy = _academy(tmp_path)
    with sqlite3.connect(academy.database_path) as connection:
        connection.execute(
            """UPDATE native_reading_runtime
               SET busy=1,lease_epoch=strftime('%s','now'),owner_pid=99999999
               WHERE singleton=1"""
        )

    assert academy._acquire_cycle_lease() is True
    academy._release_cycle_lease()


def test_chapter_titles_are_preserved_as_sentence_structure(tmp_path: Path):
    academy = _academy(tmp_path)
    source = academy.ingest_text(
        title="Structured Book",
        text=("CHAPTER ONE\n\nLeona repaired the robot in the laboratory.\n\n"
              "CHAPTER TWO\n\nTavian inspected the machine after sunrise."),
    )

    with sqlite3.connect(academy.database_path) as connection:
        rows = connection.execute(
            """SELECT section_index,section_title,text FROM native_reading_sentences
               WHERE source_id=? ORDER BY sentence_index""", (source["source_id"],),
        ).fetchall()

    assert rows == [
        (1, "CHAPTER ONE", "Leona repaired the robot in the laboratory."),
        (2, "CHAPTER TWO", "Tavian inspected the machine after sunrise."),
    ]


def test_long_sources_use_fast_exposure_and_selective_deep_tests(tmp_path: Path):
    academy = _academy(tmp_path)
    sentences = [
        f"Yesterday, Leona repaired robot {index} in the laboratory."
        for index in range(30)
    ]
    source = academy.ingest_text(title="Long Workshop Log", text=" ".join(sentences))

    outcome = academy.run_cycle(limit=200, discover_words=0)
    metrics = academy.metrics()

    # The bundled 13-sentence public-domain starter and 72-sentence
    # cross-subject conversation curriculum are also seeded and fully examined.
    assert outcome["sentences_read"] == 115
    assert 78 <= outcome["deep_tests_selected"] <= 84
    assert outcome["deep_tests_selected"] + outcome["exposure_only"] == 115
    assert outcome["sentences_per_second"] > 0
    assert metrics["sentences_processed"] == 115
    assert metrics["sentences_exposure_only"] == outcome["exposure_only"]
    assert metrics["sentence_characters_compacted"] > 0
    with sqlite3.connect(academy.database_path) as connection:
        long_source_characters = connection.execute(
            "SELECT COALESCE(SUM(length(text)),0) FROM native_reading_sentences WHERE source_id=?",
            (source["source_id"],),
        ).fetchone()[0]
    assert long_source_characters < len(" ".join(sentences))
    assert metrics["configured_batch_size"] == 40
