from pathlib import Path

from backend.modules.aion_cognition.native_conversation_runtime import NativeConversationRuntime
from backend.modules.aion_cognition.native_discourse_dialogue import NativeDiscourseDialogueEngine
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_open_conversation_academy import (
    NativeOpenConversationAcademy,
)


def _academy(tmp_path: Path, monkeypatch) -> NativeOpenConversationAcademy:
    database = tmp_path / "native.sqlite3"
    monkeypatch.setenv("AION_NATIVE_LEXICON_DB", str(database))
    lexical = NativeLexicalIntelligence(
        database, authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records([
        {"lemma": word, "pos": pos, "definition": definition}
        for word, pos, definition in (
            ("inspect", "v", "examine carefully"), ("repair", "v", "restore"),
            ("test", "v", "evaluate"), ("clean", "v", "remove dirt"),
            ("sensor", "n", "detection device"), ("pump", "n", "fluid device"),
            ("engine", "n", "power machine"), ("lens", "n", "optical component"),
            ("laboratory", "n", "place for experiments"),
            ("workshop", "n", "place for practical work"),
            ("hangar", "n", "building for aircraft"),
            ("observatory", "n", "place for observation"),
        )
    ], source="test", require_authority=False)
    discourse = NativeDiscourseDialogueEngine(repo_root=tmp_path, lexical=lexical)
    runtime = NativeConversationRuntime(repo_root=tmp_path, discourse=discourse)
    return NativeOpenConversationAcademy(repo_root=tmp_path, runtime=runtime)


def test_diverse_selection_caps_each_family_at_four(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)
    contracts = []
    for family in ("entity", "action", "object", "location", "time"):
        for index in range(8):
            contracts.append({"contract_key": f"{family}-{index}", "family": family})

    selected = academy._diverse_contracts(contracts, 20)

    assert len(selected) == 20
    assert all(sum(row["family"] == family for row in selected) == 4
               for family in ("entity", "action", "object", "location", "time"))


def test_source_package_is_replenished_by_reader_passages(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)
    reading = []
    for index in range(8):
        reading.append({
            "source_id": f"reading-{index}",
            "source_family": f"reader-subject-{index % 4}",
            "title": f"Reader source {index}",
            "passage": (
                f"Leona inspected the sensor in the laboratory. "
                f"Tavian repaired the pump in the workshop. "
                f"Mireya tested the engine in the hangar."
            ),
            "source_key": f"temporary-{index}",
        })
    monkeypatch.setattr(academy.discourse, "_reading_passages", lambda _limit: reading)

    sources, signature, contracts = academy._source_package()

    assert signature
    assert any(str(row["source_id"]).startswith("reading-") for row in sources)
    assert len({row["source_family"] for row in sources}) >= 3
    assert len(contracts) >= 20


def test_twenty_turn_exam_is_model_free_and_evidence_backed(tmp_path: Path, monkeypatch):
    academy = _academy(tmp_path, monkeypatch)
    events = [
        ("Leona", "inspected", "inspect", "the damaged sensor", "in the laboratory", "Yesterday"),
        ("Tavian", "repaired", "repair", "the cracked pump", "in the workshop", "On Monday"),
        ("Mireya", "tested", "test", "the quiet engine", "in the hangar", "On Tuesday"),
        ("Owen", "cleaned", "clean", "the telescope lens", "in the observatory", "On Friday"),
    ]
    sources = []
    contracts = []
    for index, (name, surface, action, obj, location, when) in enumerate(events):
        passage = f"{when}, {name} {surface} {obj} {location}."
        sources.append({"source_id": f"source-{index}", "source_family": f"subject-{index}",
                        "passage": passage})
        rows = (
            ("entity", f"Who performed the event involving {obj}?", name),
            ("action", f"What action did {name} perform?", surface),
            ("object", f"What complete object did {name} {action}?", obj),
            ("location", f"Where did the event involving {obj} occur?", location),
            ("time", f"When did the event involving {obj} occur?", when),
        )
        for family, question, expected in rows:
            contracts.append({"contract_key": f"{family}-{index}", "source_key": f"source-{index}",
                              "family": family, "question": question,
                              "expected_answer": expected, "answer_reason": "The passage states it."})
    monkeypatch.setattr(academy, "_source_package", lambda: (sources, "unique-package", contracts))

    result = academy.run_cycle(limit=1)

    assert result["attempted"] == 1
    assert result["results"][0]["turns"] == 20
    assert result["results"][0]["student_model_used"] is False
    assert result["qwen_used_for_student_answers"] is False
    assert academy.metrics()["turns"] == 20
