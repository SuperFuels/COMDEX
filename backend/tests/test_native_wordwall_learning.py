from pathlib import Path

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


def _engine(tmp_path: Path) -> NativeWordwallLearning:
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
    return NativeWordwallLearning(
        repo_root=tmp_path, lexical=lexical,
        retention_seconds={
            "retention_1d": 0, "retention_7d": 0,
            "retention_30d": 0, "retention_90d": 0,
        },
    )


def _practise_twice(engine: NativeWordwallLearning, lemma: str) -> dict:
    result = {}
    for _ in range(2):
        concept = engine.acquired(lemma)[0]
        result = engine.practise(concept)
    return result


def test_reference_entries_are_separate_from_learned_vocabulary(tmp_path: Path):
    engine = _engine(tmp_path)

    before = engine.metrics()
    engine.encounter("calm", teacher_lesson_id="lesson-1")
    after = engine.metrics()

    assert before["reference_entries"] == 2
    assert before["encountered_words"] == 0
    assert after["encountered_words"] == 1
    assert after["active_vocabulary"] == 0
    assert after["mastered_words"] == 0
    assert after["claim_boundary"] == "Reference entries are not learned vocabulary."


def test_closed_book_stages_gate_active_and_mastered_vocabulary(tmp_path: Path):
    engine = _engine(tmp_path)
    engine.encounter("calm")

    for expected_stage in ("recalled", "contextual", "productive", "retention_1d"):
        result = _practise_twice(engine, "calm")
        assert result["stage_after"] == expected_stage
        assert result["expected_withheld"] is True
        assert result["model_used"] is False

    assert engine.metrics()["active_vocabulary"] == 1
    assert engine.metrics()["mastered_words"] == 0

    for expected_stage in ("retention_7d", "retention_30d", "retention_90d", "mastered"):
        result = _practise_twice(engine, "calm")
        assert result["stage_after"] == expected_stage

    metrics = engine.metrics()
    assert metrics["active_vocabulary"] == 1
    assert metrics["mastered_words"] == 1
    assert metrics["practice_attempts"] == 16


def test_wordwall_cycle_has_no_model_or_answer_leakage(tmp_path: Path):
    engine = _engine(tmp_path)

    result = engine.run_cycle(limit=2, preferred_lemmas=("calm", "peaceful"))

    assert result["status"] == "completed"
    assert result["model_used"] is False
    assert result["cloud_used"] is False
    assert result["next_token_prediction"] is False
    assert result["expected_withheld"] is True
    assert all("expected_answer" in row for row in result["attempts"])
    assert all(row["expected_withheld"] for row in result["attempts"])


def test_exact_cycle_tests_only_requested_page_words_despite_due_backlog(tmp_path: Path):
    engine = _engine(tmp_path)
    engine.encounter("calm", teacher_lesson_id="older-due-work")

    result = engine.run_exact_cycle(
        lemmas=("peaceful",), teacher_lesson_id="semantic_spider:page-1",
    )

    assert result["status"] == "completed"
    assert result["requested_lemmas"] == ["peaceful"]
    assert result["tested_lemmas"] == ["peaceful"]
    assert result["coverage_count"] == result["coverage_total"] == 1
    assert result["coverage_ratio"] == 1.0
    assert result["page_certified"] is True
    assert result["expected_withheld"] is True
    assert result["model_used"] is False
