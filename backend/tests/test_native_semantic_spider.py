from pathlib import Path
import sqlite3
import time

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_semantic_spider import NativeSemanticSpider


def _spider(tmp_path: Path, monkeypatch) -> NativeSemanticSpider:
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "language", "part_of_speech": "n",
         "definition": "a system of communication using meaning and context",
         "synonyms": ["communication"]},
        {"lemma": "communication", "part_of_speech": "n",
         "definition": "the exchange of meaning between people", "synonyms": ["language"]},
        {"lemma": "meaning", "part_of_speech": "n",
         "definition": "an idea communicated by language", "synonyms": ["sense"]},
        {"lemma": "context", "part_of_speech": "n",
         "definition": "surrounding information that clarifies meaning"},
        {"lemma": "system", "part_of_speech": "n",
         "definition": "connected parts forming a whole"},
        {"lemma": "sense", "part_of_speech": "n",
         "definition": "a meaning conveyed by expression"},
        {"lemma": "exchange", "part_of_speech": "n",
         "definition": "an act of giving and receiving"},
        {"lemma": "idea", "part_of_speech": "n",
         "definition": "a concept or thought"},
    ), source="test", require_authority=False)
    return NativeSemanticSpider(
        repo_root=tmp_path, lexical=lexical, wikipedia_enabled=False,
        macos_dictionary_enabled=False,
        words_per_page=2, max_open_pages=2, max_discoveries_per_page=4, max_frontier=6,
    )


def test_semantic_spider_caps_frontier_persists_pages_and_tests_closed_book(tmp_path, monkeypatch):
    spider = _spider(tmp_path, monkeypatch)
    started = spider.start("language")

    first = spider.step()
    second = spider.step()

    assert started["running"] is True
    assert first["status"] == "word_read"
    assert second["status"] == "page_completed"
    assert second["pages_completed"] == 1
    assert second["frontier_queued"] <= second["caps"]["max_frontier"] == 6
    assert second["pages"][0]["status"] == "tested"
    assert second["pages"][0]["test"]["model_used"] is False
    assert second["pages"][0]["test"]["page_certified"] is True
    assert second["pages"][0]["test"]["coverage_count"] == 2
    assert second["pages"][0]["test"]["coverage_total"] == 2
    assert set(second["pages"][0]["test"]["tested_lemmas"]) == {
        word["lemma"] for word in second["pages"][0]["words"]
    }
    assert second["model_used_for_tests"] is False
    assert second["words_read"] == 2


def test_semantic_spider_pause_prevents_automatic_step(tmp_path, monkeypatch):
    spider = _spider(tmp_path, monkeypatch)
    spider.start("language")
    paused = spider.pause()
    result = spider.step()

    assert paused["running"] is False
    assert result["status"] == "paused"
    assert result["words_read"] == 0


def test_semantic_spider_lease_prevents_overlapping_callers(tmp_path, monkeypatch):
    spider = _spider(tmp_path, monkeypatch)
    spider.start("language")
    with sqlite3.connect(spider.database_path) as connection:
        connection.execute(
            "UPDATE semantic_spider_state SET busy=1,lease_epoch=? WHERE singleton=1",
            (time.time(),),
        )

    result = spider.step()

    assert result["status"] == "busy"
    assert result["words_read"] == 0
