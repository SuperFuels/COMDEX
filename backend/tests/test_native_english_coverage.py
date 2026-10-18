from pathlib import Path

from backend.modules.aion_cognition.native_english_coverage import NativeEnglishCoverage
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def _foundation(tmp_path: Path, monkeypatch):
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "repair", "part_of_speech": "n", "definition": "the act of fixing"},
        {"lemma": "repair", "part_of_speech": "v", "definition": "restore to working order"},
        {"lemma": "go", "part_of_speech": "v", "definition": "move from one place to another"},
        {"lemma": "get", "part_of_speech": "v", "definition": "come to possess"},
        {"lemma": "fuel", "part_of_speech": "n", "definition": "material used for energy"},
        {"lemma": "price", "part_of_speech": "n", "definition": "the amount paid"},
        {"lemma": "gallon", "part_of_speech": "n", "definition": "a unit of volume"},
        {"lemma": "garage", "part_of_speech": "n", "definition": "a building for vehicles"},
        {"lemma": "robot", "part_of_speech": "n", "definition": "a programmable machine"},
        {"lemma": "laboratory", "part_of_speech": "n", "definition": "a place for experiments"},
        {"lemma": "polish", "part_of_speech": "v", "definition": "make a surface smooth and bright"},
        {"lemma": "telescope", "part_of_speech": "n", "definition": "an instrument for distant objects"},
        {"lemma": "observatory", "part_of_speech": "n", "definition": "a place for astronomical observation"},
    ), source="test", require_authority=False)
    with lexical._connect() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            (("went", "go", "v", "irregular", "test", 1),
             ("repaired", "repair", "v", "past", "test", 1),
             ("polished", "polish", "v", "past", "test", 1)),
        )
    return lexical, NativeEnglishTransfer(repo_root=tmp_path, lexical=lexical)


def test_sense_inventory_keeps_multiple_parts_of_speech(tmp_path: Path, monkeypatch):
    lexical, _ = _foundation(tmp_path, monkeypatch)

    senses = lexical.lookup_senses("repair")

    assert {sense["part_of_speech"] for sense in senses} == {"n", "v"}
    assert lexical.resolve_form("went", part_of_speech="v")[0]["lemma"] == "go"


def test_owner_fuel_example_parses_spelling_morphology_and_currency(tmp_path: Path, monkeypatch):
    _, transfer = _foundation(tmp_path, monkeypatch)

    result = transfer.answer(
        "wehn i went to the garage to get some fuel the price per gallon was £8",
        "how much was a gallon of fuel",
    )

    assert result["answer"] == "£8"
    assert result["parse"]["frame"]["action"] == "go"
    assert result["parse"]["frame"]["tense"] == "past"
    assert result["parse"]["quantities"][0] == {
        "value": 8.0, "currency": "GBP", "symbol": "£", "unit": "gallon",
        "property": "price", "item": "fuel", "surface": "£8",
    }
    assert result["parse"]["spelling_hypotheses"][0]["candidate"] == "when"
    assert result["model_used"] is False


def test_owner_kellan_example_requires_a_complete_semantic_frame(tmp_path: Path, monkeypatch):
    _, transfer = _foundation(tmp_path, monkeypatch)

    result = transfer.answer(
        "Yesterday, Kellan repaired the robot in the laboratory.",
        "Who performed the action?",
    )

    assert result["answer"] == "Kellan"
    assert result["parse"]["frame"] == {
        "subject": "Kellan", "action": "repair", "action_surface": "repaired",
        "object": "robot", "time": "Yesterday", "location": "in the laboratory",
        "tense": "past", "negated": False,
    }


def test_calendar_phrase_does_not_become_the_subject(tmp_path: Path, monkeypatch):
    _, transfer = _foundation(tmp_path, monkeypatch)

    result = transfer.answer(
        "Last Thursday, Mireya polished the telescope in the observatory.",
        "Who polished the telescope?",
    )

    assert result["answer"] == "Mireya"
    assert result["parse"]["frame"]["subject"] == "Mireya"
    assert result["parse"]["frame"]["time"] == "Last Thursday"


def test_coverage_ledger_records_only_cases_actually_run(tmp_path: Path, monkeypatch):
    _foundation(tmp_path, monkeypatch)
    coverage = NativeEnglishCoverage(repo_root=tmp_path)
    cases = ({"category": "currency_quantity", "sentence": "The price per gallon was £8.",
              "question": "How much was a gallon?", "expected": "£8"},)

    run = coverage.run(cases)
    metrics = coverage.metrics()

    assert run["tested"] == run["passed"] == 1
    assert run["model_used"] is False
    assert metrics["latest_categories"]["currency_quantity"]["tested"] == 1
    assert metrics["claim_boundary"].startswith("Coverage is reported per tested category")
