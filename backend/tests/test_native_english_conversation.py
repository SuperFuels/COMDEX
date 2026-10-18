from pathlib import Path

from backend.modules.aion_cognition.native_english_conversation import NativeEnglishConversation
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


def _conversation(tmp_path: Path) -> NativeEnglishConversation:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records(({
        "lemma": "calm", "definition": "a peaceful state without agitation",
        "examples": ["The room remained calm."], "synonyms": ["peaceful"],
        "antonyms": ["agitated"],
    }, {
        "lemma": "peaceful", "definition": "free from disturbance",
        "examples": ["The garden was peaceful."], "synonyms": ["calm"],
    }), source="verified_test_lexicon", require_authority=False)
    return NativeEnglishConversation(repo_root=tmp_path, lexical=lexical)


def _activate(conversation: NativeEnglishConversation, lemma: str) -> None:
    concepts = conversation.wordwall.encounter(lemma)
    concept_id = concepts[0]["concept_id"]
    for _ in range(8):
        current = next(row for row in conversation.wordwall.acquired(lemma)
                       if row["concept_id"] == concept_id)
        conversation.wordwall.practise(current)


def test_native_answer_is_planned_from_meaning_without_a_model(tmp_path: Path):
    conversation = _conversation(tmp_path)
    _activate(conversation, "calm")

    result = conversation.ask("What does calm mean?")

    assert result["status"] == "answered"
    assert result["knowledge_status"] == "acquired"
    assert result["acquisition_stage"] == "retention_1d"
    assert "calm is a concept associated with" in result["answer"].lower()
    assert result["evidence"][0]["kind"] == "acquired_concept"
    assert result["checks"]["has_evidence"] is True
    assert result["generation"] == {
        "method": "symbolic_meaning_plan_and_rule_grammar",
        "aion_generated": True,
        "next_token_prediction": False,
        "qwen_used": False,
        "model_used": False,
        "cloud_used": False,
        "external_polisher_used": False,
    }


def test_native_conversation_abstains_without_verified_knowledge(tmp_path: Path):
    conversation = _conversation(tmp_path)

    result = conversation.ask("Why did the orbital project finish late?")

    assert result["status"] == "unknown"
    assert result["confidence"] == 0.0
    assert result["evidence"] == []
    assert "do not have enough verified knowledge" in result["answer"]
    assert conversation.metrics()["open_failures"] == 1


def test_dictionary_entry_is_not_claimed_as_learned(tmp_path: Path):
    conversation = _conversation(tmp_path)

    result = conversation.ask("What does calm mean?")

    assert result["status"] == "reference_only"
    assert result["knowledge_status"] == "reference_only"
    assert "not yet completed learning" in result["answer"]
    assert result["evidence"][0]["kind"] == "reference_lexeme_not_learned"
    assert conversation.metrics()["open_failures"] == 0


def test_native_conversation_resolves_a_reference_from_its_own_session(tmp_path: Path):
    conversation = _conversation(tmp_path)
    _activate(conversation, "calm")
    first = conversation.ask("Define calm", session_id="reference-test")
    second = conversation.ask("What does it mean?", session_id="reference-test")

    assert first["status"] == "answered"
    assert second["status"] == "answered"
    assert second["parse"]["slots"]["term"] == "calm"
    assert second["parse"]["context"]["used"] is True
    assert second["answer"] == first["answer"]


def test_verified_fact_can_be_retrieved_and_realised_as_english(tmp_path: Path):
    conversation = _conversation(tmp_path)
    stored = conversation.remember_fact(
        subject="aion", predicate="uses", object_value="verified local memory",
        qualifiers={"place": "the SD card"}, source="test_verified_record",
    )

    result = conversation.ask("What does Aion use?")

    assert stored["stored"] is True
    assert result["status"] == "answered"
    assert result["answer"] == "Aion uses verified local memory."
    assert result["evidence"][0]["kind"] == "verified_fact"


def test_self_improvement_uses_verified_paraphrase_consistency(tmp_path: Path):
    conversation = _conversation(tmp_path)
    _activate(conversation, "calm")
    _activate(conversation, "peaceful")
    conversation.ask("What is the purpose of an unknown flux lattice?")

    result = conversation.self_improvement_cycle(limit=4)

    assert result["status"] == "completed"
    assert result["consistency_checks"] == 2
    assert result["consistency_passed"] == 2
    assert result["model_used"] is False
    assert result["cloud_used"] is False
    assert result["next_token_prediction"] is False


def test_verified_owner_correction_enters_remedial_learning_not_instant_mastery(tmp_path: Path):
    conversation = _conversation(tmp_path)
    turn = conversation.ask("What does calm mean?")

    feedback = conversation.correct(
        turn_id=turn["turn_id"],
        proposed_answer="Calm is a peaceful state without agitation.",
        reason="This expresses the stored semantic features.",
    )

    assert feedback["verified"] is True
    assert feedback["immediate_answer_overwrite"] is False
    assert feedback["counts_as_mastery"] is False
    assert feedback["remedial_action"] == "concept_grounded_or_requeued_for_closed_book_practice"
    assert conversation.wordwall.acquired("calm")[0]["stage"] == "grounded"


def test_unverifiable_open_correction_is_held_not_learned(tmp_path: Path):
    conversation = _conversation(tmp_path)
    turn = conversation.ask("Why did the orbital project finish late?")

    feedback = conversation.correct(
        turn_id=turn["turn_id"], proposed_answer="Because the engine failed.",
        reason="I say so.",
    )

    assert feedback["verified"] is False
    assert feedback["status"] == "pending_evidence"
    assert feedback["remedial_action"] == "held_for_review_not_learned"
    assert conversation.metrics()["pending_feedback"] == 1
