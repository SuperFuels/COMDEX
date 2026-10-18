from pathlib import Path
import time

from backend.modules.aion_cognition.native_communication_academy import (
    NativeCommunicationAcademy,
)
from backend.modules.aion_cognition.native_discourse_dialogue import (
    NativeDiscourseDialogueEngine,
)
from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence,
)


def _academy(tmp_path: Path, monkeypatch) -> NativeCommunicationAcademy:
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records([
        {"lemma": "inspect", "pos": "v", "definition": "examine carefully"},
        {"lemma": "replace", "pos": "v", "definition": "put something new in place"},
        {"lemma": "fail", "pos": "v", "definition": "stop working"},
        {"lemma": "sensor", "pos": "n", "definition": "a detection device"},
        {"lemma": "cable", "pos": "n", "definition": "an insulated wire"},
    ], source="test", require_authority=False)
    discourse = NativeDiscourseDialogueEngine(repo_root=tmp_path, lexical=lexical)
    academy = NativeCommunicationAcademy(repo_root=tmp_path, discourse=discourse)
    now = time.time()
    with academy._connect() as connection:
        connection.executescript("""
            CREATE TABLE native_reading_sources(
                source_id TEXT PRIMARY KEY,title TEXT,author TEXT,subject TEXT,license TEXT,
                source_ref TEXT,content_hash TEXT,status TEXT,paragraph_count INTEGER,
                sentence_count INTEGER,next_sentence_index INTEGER,created_epoch REAL,updated_epoch REAL
            );
            CREATE TABLE native_reading_sentences(
                sentence_id TEXT PRIMARY KEY,source_id TEXT,sentence_index INTEGER,
                paragraph_index INTEGER,text TEXT,status TEXT,parse_json TEXT,
                acquired_concepts_json TEXT,reference_words_json TEXT,unknown_words_json TEXT,
                summary_text TEXT,processed_epoch REAL,created_epoch REAL
            );
        """)
        passages = {
            "book-a": [
                "Leona inspected the damaged sensor in the laboratory.",
                "She replaced the loose cable because the warning light had failed.",
                "The repaired sensor then worked normally during the inspection.",
            ],
            "book-b": [
                "Tavian inspected the damaged pump in the workshop.",
                "He replaced the cracked seal because the old part had failed.",
                "The repaired pump then worked normally during the test.",
            ],
        }
        for source_offset, (source_id, sentences) in enumerate(passages.items()):
            connection.execute(
                "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (source_id, source_id, "Owner", "engineering", "test", "test", source_id,
                 "completed", 1, 3, 3, now + source_offset, now + source_offset),
            )
            for index, text in enumerate(sentences):
                connection.execute(
                    "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                    (f"{source_id}-{index}", source_id, index, 0, text,
                     now + source_offset + index / 10, now),
                )
    return academy


def test_academy_runs_sealed_model_free_session_and_schedules_retention(
    tmp_path: Path, monkeypatch,
):
    academy = _academy(tmp_path, monkeypatch)

    result = academy.run_cycle(limit=1)

    assert result["status"] == "completed"
    assert result["attempted"] == 1
    assert result["results"][0]["passed"] is True
    assert result["results"][0]["student_model_used"] is False
    assert result["qwen_used_for_student_answers"] is False
    metrics = academy.metrics()
    assert metrics["dialogue_turns"] == 1
    assert metrics["retests_pending"] == 1


def test_stage_requires_two_distinct_sources_before_progression(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)

    first = academy.run_cycle(limit=1)
    second = academy.run_cycle(limit=1)

    assert first["results"][0]["academy_session_id"] != second["results"][0]["academy_session_id"]
    assert academy.metrics()["current_stage"]["id"] == "connected_explanation"


def test_due_retest_remains_native_and_advances_retention(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)
    academy.run_cycle(limit=1)
    with academy._connect() as connection:
        connection.execute(
            "UPDATE native_communication_retests SET due_epoch=?", (time.time() - 1,),
        )

    outcomes = academy._run_due_retests(2)

    assert outcomes
    assert outcomes[0]["correct"] is True
    assert outcomes[0]["model_used"] is False


def test_dialogue_contract_selection_caps_repeated_families(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)
    contracts = [
        {"contract_key": f"object-{index}", "family": "object",
         "question": f"What object was affected in event {index}?",
         "expected_answer": "sensor", "answer_reason": "The event names it."}
        for index in range(6)
    ] + [
        {"contract_key": "entity-1", "family": "entity",
         "question": "Who acted?", "expected_answer": "Leona",
         "answer_reason": "The passage names her."}
    ]

    _, selected, _ = academy._select_contracts(contracts, 6, None, {"id": "test"})

    assert sum(row["family"] == "object" for row in selected) == 2
    assert sum(row["family"] == "entity" for row in selected) == 1
