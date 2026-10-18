from pathlib import Path
import json
import time

from backend.modules.aion_cognition.native_discourse_dialogue import NativeDiscourseDialogueEngine
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def _engine(tmp_path: Path, monkeypatch) -> NativeDiscourseDialogueEngine:
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records([
        {"lemma": "inspect", "pos": "v", "definition": "examine carefully"},
        {"lemma": "replace", "pos": "v", "definition": "put something new in place"},
        {"lemma": "fail", "pos": "v", "definition": "stop working"},
        {"lemma": "work", "pos": "v", "definition": "operate correctly"},
        {"lemma": "contradict", "pos": "v", "definition": "conflict with a claim"},
        {"lemma": "reject", "pos": "v", "definition": "refuse or dismiss"},
        {"lemma": "result", "pos": "n", "definition": "an outcome"},
        {"lemma": "claim", "pos": "n", "definition": "an assertion"},
        {"lemma": "assumption", "pos": "n", "definition": "a proposition taken as true"},
        {"lemma": "revise", "pos": "v", "definition": "change after review"},
        {"lemma": "diagnosis", "pos": "n", "definition": "identification of a condition"},
        {"lemma": "evidence", "pos": "n", "definition": "facts supporting a conclusion"},
        {"lemma": "sensor", "pos": "n", "definition": "a detection device"},
        {"lemma": "cable", "pos": "n", "definition": "an insulated wire"},
        {"lemma": "laboratory", "pos": "n", "definition": "a place for experiments"},
    ], source="test", require_authority=False)
    return NativeDiscourseDialogueEngine(repo_root=tmp_path, lexical=lexical)


def test_discourse_tracks_entities_events_and_references(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    passage = (
        "Leona inspected the damaged sensor in the laboratory. "
        "She replaced the loose cable because the warning light had failed. "
        "The sensor then worked normally."
    )

    first = engine.ask("Who inspected the sensor?", session_id="s1", passage=passage)
    reference = engine.ask("Who does she refer to?", session_id="s1")
    cause = engine.ask("Why did she replace the cable?", session_id="s1")
    summary = engine.ask("Summarise what happened.", session_id="s1")
    location = engine.ask("Where did the inspection happen?", session_id="s1")
    first_event = engine.ask("What happened first?", session_id="s1")
    action = engine.ask("What did Leona do?", session_id="s1")

    assert first["answer"] == "Leona."
    assert reference["answer"] == "Leona."
    assert "warning light" in cause["answer"].lower()
    assert "inspected" in summary["answer"].lower()
    assert location["answer"] == "In the laboratory."
    assert "inspected" in first_event["answer"].lower()
    assert "inspected" in action["answer"].lower()
    assert first["generation"]["model_used"] is False
    assert first["evidence"][0]["source_id"] == "owner_dialogue"
    assert engine.metrics()["dialogue_turns"] == 7


def test_sequence_contract_rejects_connective_and_copular_fragments(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    passage = (
        "Leona inspected the sensor in the laboratory. "
        "Tavian repaired the pump in the workshop."
    )

    assert engine._exam_contract_valid(
        passage, "sequence_first", "Leona inspected the sensor",
    )
    assert not engine._exam_contract_valid(passage, "sequence_first", "And was")
    assert not engine._exam_contract_valid(passage, "sequence_next", "For needed")
    assert not engine._exam_contract_valid(passage, "sequence_next", "Publique is Free")


def test_sequence_contracts_require_two_distinct_sentence_events(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    source = {
        "source_id": "sequence-source",
        "source_key": "sequence-source",
        "source_family": "engineering",
        "passage": (
            "Leona inspected the sensor in the laboratory. "
            "Tavian repaired the cable in the laboratory. "
            "Mireya revised the diagnosis after the inspection."
        ),
    }

    contracts = engine._contract_candidates([source])
    sequence = [row for row in contracts if row["family"].startswith("sequence_")]

    assert {row["family"] for row in sequence} == {"sequence_first", "sequence_next"}
    assert sequence[0]["expected_answer"] != sequence[1]["expected_answer"]


def test_person_pronoun_prefers_previous_event_agent_over_sentence_opener(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    passage = (
        "Tavian wanted to prove that no largest even integer exists. "
        "He temporarily assumed that a largest even integer named n did exist."
    )
    model = engine.build_situation_model(
        passage, session_id="pronoun-regression", persist=False,
    )

    relation = next(row for row in model["relations"]
                    if row.get("type") == "coreference" and row.get("surface") == "He")
    assert relation["target"] == "Tavian"


def test_sentence_anchored_cause_can_retrieve_prior_sentence_event(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    passage = (
        "The result contradicted the original claim. "
        "Tavian therefore rejected the temporary assumption."
    )
    result = engine.ask(
        "Why did Tavian reject the assumption? Use sentence 2.",
        session_id="anchored-cause", passage=passage,
    )

    assert result["status"] == "answered"
    assert "contradicted" in result["answer"].lower()


def test_cause_question_prefers_main_event_over_same_sentence_subordinate(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    passage = "Because the new evidence contradicted her explanation, Amara revised the diagnosis."
    result = engine.ask(
        "Why did the event involving diagnosis happen? Use sentence 1.",
        session_id="same-sentence-cause", passage=passage,
    )

    assert result["status"] == "answered"
    assert "contradicted" in result["answer"].lower()


def test_dialogue_requests_clarification_and_records_verified_correction(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    missing = engine.ask("Why did it happen?", session_id="empty")
    assert missing["status"] == "clarification_required"
    assert missing["checks"]["unsupported_claims"] is True

    passage = "Leona inspected the sensor."
    turn = engine.ask("Who inspected it?", session_id="s2", passage=passage)
    correction = engine.correct(
        turn_id=turn["turn_id"], verified_answer="Leona",
        explanation="Leona is the stated agent.", source_ref="owner-test",
    )
    assert correction["stored"] is True
    assert engine.metrics()["corrections"]["due"] == 1


def test_contradiction_check_uses_clause_negation(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    passage = "Leona inspected the sensor. Leona did not inspect the sensor."
    result = engine.ask("Do these statements contradict each other?", session_id="s3",
                        passage=passage)
    assert result["status"] == "answered"
    assert result["answer"].startswith("Yes")
    assert result["generation"]["qwen_used"] is False


def test_sealed_teacher_contract_is_authored_before_model_free_exam(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    sentences = [
        "Leona inspected the sensor in the laboratory.",
        "She replaced the loose cable because the warning light had failed.",
        "The sensor then worked normally.",
    ]
    with engine._connect() as connection:
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
        connection.execute(
            "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("book-1", "Test Book", "Owner", "engineering", "test", "test", "hash",
             "completed", 1, 3, 3, now, now),
        )
        for index, text in enumerate(sentences):
            connection.execute(
                "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                (f"sentence-{index}", "book-1", index, 0, text, now, now),
            )

    def teacher(_prompt: str):
        return {"model": "qwen-test", "content": json.dumps({"challenges": [{
            "source_key": "source-1", "family": "coreference",
            "question": "Who does she refer to?", "expected_answer": "Leona",
            "answer_reason": "Leona is the previously introduced person.",
        }]})}

    result = engine.run_cycle(teacher_client=teacher, limit=1)
    assert result["attempted"] == 1
    assert result["correct"] == 1
    assert result["results"][0]["expected_withheld"] is True
    assert result["qwen_used_for_student_answers"] is False
    assert engine.metrics()["exams"] == 1


def test_explicit_weekday_time_survives_reported_speech(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    passage = (
        '"That will be next Monday," said Rowan. '
        'Mira recorded the appointment in her notebook. '
        'She checked the date before leaving.'
    )
    model = engine.build_situation_model(
        passage, session_id="time", source_id="book", persist=False,
    )
    answer = engine._plan(
        model, "What day was mentioned as the next day for the event?",
    )
    assert answer["intent"] == "time"
    assert answer["answer"] == "Next Monday."
    assert answer["evidence"]

    byline = engine.build_situation_model(
        "Pride and Prejudice by Jane Austen.", session_id="byline",
        source_id="book", persist=False,
    )
    assert all(not event["time"] for event in byline["events"])


def test_invalid_teacher_draft_falls_back_to_compiled_contract(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    sentences = [
        "Leona inspected the damaged sensor in the laboratory.",
        "She replaced the loose cable because the warning light had failed.",
        "The repaired sensor then worked normally during the final inspection.",
    ]
    with engine._connect() as connection:
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
        connection.execute(
            "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("book-1", "Test Book", "Owner", "engineering", "test", "test", "hash",
             "completed", 1, 3, 3, now, now),
        )
        for index, text in enumerate(sentences):
            connection.execute(
                "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                (f"sentence-{index}", "book-1", index, 0, text, now, now),
            )

    def invalid_teacher(_prompt: str):
        return {"model": "qwen-test", "content": json.dumps({"challenges": [{
            "source_key": "missing", "family": "object", "question": "Invent a fact",
            "expected_answer": "unsupported", "answer_reason": "not in source",
        }]})}

    result = engine.run_cycle(teacher_client=invalid_teacher, limit=1)
    assert result["attempted"] == 1
    assert result["compiled_fallbacks"] == 1
    assert result["rejected"] == 1
    assert result["qwen_used_for_student_answers"] is False


def test_compiled_contract_runs_without_waiting_for_teacher(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    sentences = [
        "Leona inspected the damaged sensor in the laboratory.",
        "She replaced the loose cable because the warning light had failed.",
        "The repaired sensor then worked normally during the final inspection.",
    ]
    with engine._connect() as connection:
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
        connection.execute(
            "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("book-1", "Test Book", "Owner", "engineering", "test", "test", "hash",
             "completed", 1, 3, 3, now, now),
        )
        for index, text in enumerate(sentences):
            connection.execute(
                "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                (f"sentence-{index}", "book-1", index, 0, text, now, now),
            )

    result = engine.run_cycle(teacher_client=None, limit=1)

    assert result["attempted"] == 1
    assert result["compiled_fallbacks"] == 1
    assert result["teacher_model"] == "compiled-native-contracts"
    assert result["qwen_used_for_student_answers"] is False


def test_same_book_supplies_new_passage_contracts_and_sequence_exams(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    sentences = [
        "Leona inspected the damaged sensor in the laboratory.",
        "She replaced the loose cable because the warning light had failed.",
        "The repaired sensor then worked normally during the final inspection.",
        "Tavian examined the cracked housing in the workshop.",
        "He ordered a replacement after the engineer confirmed the damage.",
        "The new housing arrived before the maintenance shift ended.",
    ]
    with engine._connect() as connection:
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
        connection.execute(
            "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("book-1", "Test Book", "Owner", "engineering", "test", "test", "hash",
             "completed", 2, 6, 6, now, now),
        )
        for index, text in enumerate(sentences):
            connection.execute(
                "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                (f"sentence-{index}", "book-1", index, index // 3, text, now + index, now),
            )

    passages = engine._reading_passages(8)
    contracts = engine._contract_candidates(passages)
    assert {row["family"] for row in contracts} >= {"sequence_first", "sequence_next"}

    first = engine.run_cycle(teacher_client=None, limit=1)
    second = engine.run_cycle(teacher_client=None, limit=1)

    assert first["attempted"] == 1
    assert second["attempted"] == 1
    assert engine.metrics()["exams"] == 2


def test_discourse_passages_exclude_reference_books_and_balance_sources(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    with engine._connect() as connection:
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
        sources = (
            ("dictionary", "Example Dictionary", "reference"),
            ("novel-a", "First Novel", "literature"),
            ("novel-b", "Second Novel", "literature"),
        )
        for source_id, title, subject in sources:
            connection.execute(
                "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (source_id, title, "Owner", subject, "test", "test", source_id,
                 "completed", 1, 3, 3, now, now),
            )
            for index in range(3):
                text = f"Leona inspected the damaged sensor in laboratory {index}."
                connection.execute(
                    "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                    (f"{source_id}-{index}", source_id, index, 0, text,
                     now + (1000 if source_id == 'dictionary' else index), now),
                )

    passages = engine._reading_passages(8)

    assert {row["source_id"] for row in passages} == {"novel-a", "novel-b"}


def test_compiled_selection_prioritises_connected_sequence_over_repeated_entity_drills(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    now = time.time()
    sentences = [
        "Leona inspected the damaged sensor in the laboratory.",
        "She replaced the loose cable because the warning light had failed.",
        "The repaired sensor then worked normally during the final inspection.",
    ]
    with engine._connect() as connection:
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
        connection.execute(
            "INSERT INTO native_reading_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("book-1", "Test Novel", "Owner", "literature", "test", "test", "hash",
             "completed", 1, 3, 3, now, now),
        )
        for index, text in enumerate(sentences):
            connection.execute(
                "INSERT INTO native_reading_sentences VALUES(?,?,?,?,?,'exposure_only','{}','[]','[]','[]','',?,?)",
                (f"sentence-{index}", "book-1", index, 0, text, now + index, now),
            )

    result = engine.run_cycle(teacher_client=None, limit=1)

    assert result["attempted"] == 1
    assert result["results"][0]["family"] == "sequence_first"


def test_sequence_contract_rejects_sentence_initial_common_word_as_fake_entity(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    source = {
        "source_key": "source-1", "source_id": "book-1", "title": "Novel",
        "source_family": "literature",
        "passage": (
            "Our lunch awaited us on the table. "
            "Every guest sensed the tension in the room. "
            "Leona inspected the damaged sensor in the laboratory."
        ),
    }

    contracts = engine._contract_candidates([source])
    sequence_answers = {
        row["expected_answer"] for row in contracts
        if row["family"] in {"sequence_first", "sequence_next"}
    }

    assert all(not answer.startswith(("Our ", "Every ")) for answer in sequence_answers)


def test_contract_quality_rejects_pronoun_objects_and_non_place_locations(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)

    assert engine._object_answer_safe("it") is False
    assert engine._object_answer_safe("the damaged sensor") is True
    assert engine._location_answer_safe("in the laboratory") is True
    assert engine._location_answer_safe("in a family so deranged") is False
    assert engine._location_answer_safe("at the crowds") is False


def test_exam_contract_filter_rejects_indexes_and_particle_objects(
    tmp_path: Path, monkeypatch,
):
    engine = _engine(tmp_path, monkeypatch)
    index = (
        "Of the Monstrous Pictures of Whales. Of Whales in Paint; in Teeth; "
        "in Wood; in Stone; in Mountains; in Stars."
    )
    prose = (
        "I started from my sleep with horror; a cold dew covered my forehead, "
        "my teeth chattered, and every limb became convulsed; when the light "
        "crossed the room, I saw the figure beside the bed."
    )

    assert engine._passage_is_prose(index) is False
    assert engine._passage_is_prose(prose) is True
    assert engine._exam_contract_valid(prose, "object", "up the curtain") is False
    assert engine._exam_contract_valid(prose, "action", "started") is True


def test_object_contract_requires_complete_grounded_noun_phrase(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    prose = (
        "Leona inspected the damaged sensor in the laboratory. "
        "She replaced the loose cable after the alarm sounded. "
        "The repaired sensor then worked normally."
    )

    assert engine._object_answer_safe("the damaged sensor") is True
    assert engine._object_answer_safe("the loose cable") is True
    assert engine._object_answer_safe("me") is False
    assert engine._object_answer_safe("the fact that only") is False
    assert engine._object_answer_safe("up the curtain") is False
    assert engine._exam_contract_valid(prose, "object", "the damaged sensor") is True


def test_passage_filter_rejects_catalogue_fragments(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)
    catalogue = (
        "MISCELLANEOUS. Table 12 Basalt Formations; Fig. 18 Coastal Deposits; "
        "Section IV Mineral Records; Appendix IX Regional Notes."
    )

    assert engine._passage_is_prose(catalogue) is False


def test_literary_interjections_are_not_treated_as_named_agents(tmp_path: Path, monkeypatch):
    engine = _engine(tmp_path, monkeypatch)

    assert engine._grounded_named_entity("O") is False
    assert engine._grounded_named_entity("Tis") is False
