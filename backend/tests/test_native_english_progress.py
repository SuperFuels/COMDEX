import json
from pathlib import Path

from backend.api.aion_english_intelligence_router import panel
from backend.modules.aion_cognition.native_english_progress import (
    _recent_cycles, collect_native_english_progress,
)
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def test_progress_panel_reports_native_exam_and_storage_health(tmp_path: Path, monkeypatch):
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    learner = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    learner.ingest_records([
        {"lemma": "clear", "definition": "Easy to understand.", "synonyms": ["plain"]},
        {"lemma": "plain", "definition": "Simple and readily understood.", "synonyms": ["clear"]},
        {"lemma": "opaque", "definition": "Difficult to understand.", "antonyms": ["clear"]},
        {"lemma": "simple", "definition": "Not complicated.", "synonyms": ["plain"]},
    ], source="test", require_authority=False)
    learner.run_practice_cycle(family="definition_match", limit=4, project_family="test")
    state_dir = tmp_path / "data/aion/native_english_teacher"
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text(json.dumps({
        "stage_index": 0, "stage_id": "lexical_foundations", "cycles": 1,
        "consecutive_stage_passes": 1, "last_cycle_epoch": 99999999999,
        "last_teacher_model": "qwen-test", "last_teacher_error": None,
        "last_exam": {"score": 1.0, "correct": 4, "total": 4, "passed": True,
                      "model_used": False, "cloud_used": False, "expected_withheld": True},
    }), encoding="utf-8")
    results = tmp_path / "results"
    results.mkdir()
    (results / "aion_mastery_curriculum_service_status.json").write_text(json.dumps({
        "native_english_teacher": {"status": "completed", "enabled": True,
                                    "running": False, "interval_seconds": 300},
    }), encoding="utf-8")

    progress = collect_native_english_progress(tmp_path)

    assert progress["health"] == "degraded"  # test DB is intentionally not on the SD volume
    assert progress["exam"]["separation_verified"] is True
    assert progress["memory"]["lexemes"] == 4
    assert progress["stage"]["id"] == "lexical_foundations"
    assert "sd_native_english_store_not_mounted" in progress["blockers"]


def test_panel_is_a_live_read_only_progress_surface():
    response = panel()
    body = response.body.decode("utf-8")
    assert "English Intelligence Progress" in body
    assert "/api/aion/english-intelligence/progress" in body
    assert "Qwen may teach" in body
    assert "Unseen Transfer Lab" in body
    assert "English Coverage Ledger" in body
    assert "Guided English practice — scaffolded" in body
    assert "Aion Semantic Spider" in body
    assert "semantic-spider/${action}" in body
    assert 'class="leg"' in body


def test_recent_cycles_reads_only_the_tail_records(tmp_path: Path):
    ledger = tmp_path / "cycles.jsonl"
    rows = [
        {"status": "completed", "stage": {"id": f"stage-{index}"},
         "closed_book_exam": {"score": 1.0}}
        for index in range(30)
    ]
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    recent = _recent_cycles(ledger, limit=3)

    assert [row["stage_id"] for row in recent] == ["stage-27", "stage-28", "stage-29"]
