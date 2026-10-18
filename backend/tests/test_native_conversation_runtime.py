from pathlib import Path

from backend.modules.aion_cognition.native_conversation_runtime import NativeConversationRuntime
from backend.modules.aion_cognition.native_discourse_dialogue import NativeDiscourseDialogueEngine
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def _runtime(tmp_path: Path, monkeypatch) -> NativeConversationRuntime:
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records([
        {"lemma": "inspect", "pos": "v", "definition": "examine carefully"},
        {"lemma": "repair", "pos": "v", "definition": "restore to working condition"},
        {"lemma": "replace", "pos": "v", "definition": "put something new in place"},
        {"lemma": "sensor", "pos": "n", "definition": "a detection device"},
        {"lemma": "pump", "pos": "n", "definition": "a device that moves fluid"},
        {"lemma": "cable", "pos": "n", "definition": "an insulated wire"},
    ], source="test", require_authority=False)
    discourse = NativeDiscourseDialogueEngine(repo_root=tmp_path, lexical=lexical)
    return NativeConversationRuntime(repo_root=tmp_path, discourse=discourse)


def test_runtime_answers_from_persistent_situation_without_model(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)
    context = (
        "Leona inspected the damaged sensor in the laboratory. "
        "She repaired the loose cable. The sensor worked normally."
    )

    result = runtime.respond(
        "Who inspected the sensor?", session_id="owner", context=context,
    )

    assert result["status"] == "answered"
    assert result["response"].startswith("Leona")
    assert result["checks"]["evidence_supported"] is True
    assert result["generation"]["model_used"] is False
    assert runtime.session_state("owner")["active_propositions"] >= 2


def test_runtime_detects_ambiguous_same_surface_references(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)
    context = (
        "Leona inspected the sensor. She repaired it. "
        "Tavian inspected the pump. He replaced it."
    )
    runtime.ingest_context(session_id="references", text=context)

    ambiguous = runtime.respond("What does 'it' refer to?", session_id="references")
    specific = runtime.respond(
        "In sentence 2, what does 'it' refer to?", session_id="references",
    )

    assert ambiguous["status"] == "clarification_required"
    assert ambiguous["ambiguities"][0]["kind"] == "multiple_references"
    assert specific["status"] == "answered"
    assert "sensor" in specific["response"].lower()


def test_runtime_remembers_assertion_and_records_correction(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)

    remembered = runtime.respond(
        "Remember that Leona repaired the cable.", session_id="memory",
    )
    answer = runtime.respond("Who repaired the cable?", session_id="memory")
    correction = runtime.correct(
        turn_id=answer["turn_id"], corrected_fact="Tavian repaired the pump.",
        explanation="The owner supplied the corrected event.", source_ref="owner-test",
    )

    assert remembered["status"] == "answered"
    assert answer["status"] == "answered"
    assert "Leona" in answer["response"]
    assert correction["stored"] is True
    assert correction["model_used"] is False
    assert runtime.metrics()["corrections"] == 1


def test_runtime_requests_context_for_open_unsupported_question(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch)

    result = runtime.respond(
        "Why did the engineer change the design?", session_id="empty",
    )

    assert result["status"] == "clarification_required"
    assert result["checks"]["unsupported_claims"] is False
    assert result["generation"]["qwen_used"] is False


def test_runtime_does_not_answer_embedded_unknown_as_direct_who_question(
    tmp_path: Path, monkeypatch,
):
    runtime = _runtime(tmp_path, monkeypatch)
    result = runtime.respond(
        "What would you need before saying who manufactured the sensor?",
        session_id="requirements",
        context="Leona inspected the damaged sensor.",
    )

    assert result["status"] == "clarification_required"
    assert "supported evidence" in result["response"]
    assert "does not provide" in result["response"]
    assert "Leona" not in result["response"]


def test_runtime_answers_anchored_sequence_question_instead_of_echoing_it(
    tmp_path: Path, monkeypatch,
):
    runtime = _runtime(tmp_path, monkeypatch)
    context = (
        "Leona inspected the sensor. "
        "Tavian repaired the pump. "
        "Mireya replaced the cable."
    )
    question = "According to passage order, what happened first? Use sentence 1."

    result = runtime.respond(question, session_id="sequence", context=context)

    assert result["request_frame"]["speech_act"] == "question"
    assert result["status"] == "answered"
    assert result["response"] != question
    assert "Leona" in result["response"]
    assert "inspect" in result["response"].lower()
