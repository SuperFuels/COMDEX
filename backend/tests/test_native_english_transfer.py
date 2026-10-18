from pathlib import Path

from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


def _transfer(tmp_path: Path) -> NativeEnglishTransfer:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "calculate", "part_of_speech": "v", "definition": "compute a result"},
        {"lemma": "inspect", "part_of_speech": "v", "definition": "examine carefully"},
        {"lemma": "report", "part_of_speech": "n", "definition": "a written account"},
        {"lemma": "garden", "part_of_speech": "n", "definition": "a cultivated place"},
        {"lemma": "lunch", "part_of_speech": "n", "definition": "a midday meal"},
        {"lemma": "message", "part_of_speech": "n", "definition": "a communication"},
        {"lemma": "robot", "part_of_speech": "n", "definition": "a programmable machine"},
    ), source="test", require_authority=False)
    wordwall = NativeWordwallLearning(repo_root=tmp_path, lexical=lexical)
    wordwall.encounter("calculate")
    return NativeEnglishTransfer(repo_root=tmp_path, lexical=lexical)


def test_arbitrary_sentence_parse_exposes_roles_grounding_and_generated_reason(tmp_path: Path):
    transfer = _transfer(tmp_path)

    result = transfer.answer(
        "Before lunch, Xanthe calculated the report in the garden.",
        "Where did the action happen?",
    )

    assert result["answer"] == "in the garden"
    assert result["parse"]["frame"] == {
        "subject": "Xanthe", "action": "calculate", "action_surface": "calculated",
        "object": "report", "time": "Before lunch", "location": "in the garden",
        "tense": "past", "negated": False,
    }
    assert result["parse"]["grounding"]["acquired"] == 1
    assert "subject=Xanthe" in result["explanation"]
    assert "location=in the garden" in result["explanation"]
    assert result["model_used"] is False


def test_owner_created_challenge_is_first_seen_and_answer_key_is_withheld(tmp_path: Path):
    transfer = _transfer(tmp_path)
    challenge = transfer.create_challenge(
        kind="sentence_qa",
        material="After lunch, Zephyr inspected the robot in the garden.",
        question="Who performed the action?", expected_answer="Zephyr",
        answer_reason="Zephyr occurs before the action and is the subject.",
    )

    result = transfer.attempt(challenge["challenge_id"])

    assert challenge["answer_withheld"] is True
    assert "expected_answer" not in challenge
    assert challenge["first_seen"] is True
    assert result["answer"] == "Zephyr"
    assert result["correct"] is True
    assert result["template_generated"] is False
    assert result["answer_withheld_from_student"] is True
    assert result["learning_update"]["reinforced"] == 0


def test_graded_transfer_updates_acquired_concept_without_instant_mastery(tmp_path: Path):
    transfer = _transfer(tmp_path)
    with transfer.lexical._connect() as connection:
        before = dict(connection.execute(
            "SELECT * FROM acquired_concepts WHERE lemma='calculate'"
        ).fetchone())
    challenge = transfer.create_challenge(
        kind="sentence_qa", material="Xanthe calculated the report.",
        question="What action happened?", expected_answer="calculate",
        answer_reason="Calculated is the past form of calculate.",
    )

    result = transfer.attempt(challenge["challenge_id"])

    assert result["correct"] is True
    assert result["learning_update"]["reinforced"] == 1
    assert result["learning_update"]["counts_as_mastery"] is False
    with transfer.lexical._connect() as connection:
        after = dict(connection.execute(
            "SELECT * FROM acquired_concepts WHERE lemma='calculate'"
        ).fetchone())
    assert after["correct_attempts"] == before["correct_attempts"] + 1
    assert after["stage"] == before["stage"]


def test_ambiguous_noun_order_returns_alternatives_and_lower_confidence(tmp_path: Path):
    transfer = _transfer(tmp_path)

    challenge = transfer.create_challenge(
        kind="word_order", material="robot report inspected",
        expected_answer="The robot inspected the report.",
    )
    result = transfer.attempt(challenge["challenge_id"])

    assert result["status"] == "ambiguous"
    assert len(result["alternatives"]) == 2
    assert result["confidence"] < .6
    assert "subject_object_order_requires_meaning" in result["parse"]["ambiguities"]


def test_transfer_metrics_do_not_mix_template_practice(tmp_path: Path):
    transfer = _transfer(tmp_path)
    challenge = transfer.create_challenge(
        kind="sentence_qa", material="Xanthe calculated the report.",
        question="What action happened?", expected_answer="calculate",
    )
    transfer.attempt(challenge["challenge_id"])

    metrics = transfer.metrics()
    assert metrics["owner_created_challenges"] == 1
    assert metrics["first_seen_challenges"] == 1
    assert metrics["accuracy"] == 1.0
    assert metrics["template_generated"] is False


def test_complex_word_order_uses_every_token_and_builds_both_clauses(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "flash", "part_of_speech": "v", "definition": "shine briefly"},
        {"lemma": "complete", "part_of_speech": "v", "definition": "finish"},
        {"lemma": "sensor", "part_of_speech": "n", "definition": "a detecting device"},
        {"lemma": "repair", "part_of_speech": "n", "definition": "an act of fixing"},
        {"lemma": "sunrise", "part_of_speech": "n", "definition": "the rising of the sun"},
        {"lemma": "delicate", "part_of_speech": "a", "definition": "requiring care"},
        {"lemma": "calmly", "part_of_speech": "r", "definition": "in a calm manner"},
        {"lemma": "repeatedly", "part_of_speech": "r", "definition": "again and again"},
    ), source="test", require_authority=False)
    with transfer.lexical._connect() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            (("warning", "warn", "v", "present_participle", "test", 1),
             ("flashed", "flash", "v", "past", "test", 1),
             ("completed", "complete", "v", "past", "test", 1)),
        )

    result = transfer.order_words(
        "although the warning sensor flashed repeatedly Mireya calmly completed "
        "the delicate repair before sunrise"
    )

    assert result["answer"] == (
        "Although the warning sensor flashed repeatedly, Mireya calmly completed "
        "the delicate repair before sunrise."
    )
    assert result["parse"]["used_tokens"] == result["parse"]["total_tokens"] == 14
    assert result["parse"]["unused_tokens"] == []


def test_complex_word_order_treats_past_participle_as_noun_modifier(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "hum", "part_of_speech": "v", "definition": "make a steady sound"},
        {"lemma": "inspect", "part_of_speech": "v", "definition": "examine carefully"},
        {"lemma": "damage", "part_of_speech": "v", "definition": "cause physical harm"},
        {"lemma": "generator", "part_of_speech": "n", "definition": "a machine producing power"},
        {"lemma": "circuit", "part_of_speech": "n", "definition": "an electrical path"},
        {"lemma": "midnight", "part_of_speech": "n", "definition": "twelve at night"},
        {"lemma": "faulty", "part_of_speech": "s", "definition": "not working correctly"},
        {"lemma": "quietly", "part_of_speech": "r", "definition": "with little noise"},
        {"lemma": "carefully", "part_of_speech": "r", "definition": "with care"},
    ), source="test", require_authority=False)
    with transfer.lexical._connect() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            (("hummed", "hum", "v", "past", "test", 1),
             ("inspected", "inspect", "v", "past", "test", 1),
             ("damaged", "damage", "v", "past_participle", "test", 1)),
        )

    result = transfer.order_words(
        "while the faulty generator hummed quietly Tavian carefully inspected "
        "the damaged circuit before midnight"
    )

    assert result["answer"] == (
        "While the faulty generator hummed quietly, Tavian carefully inspected "
        "the damaged circuit before midnight."
    )
    assert result["parse"]["used_tokens"] == result["parse"]["total_tokens"] == 14
    assert result["parse"]["unused_tokens"] == []


def test_word_order_refuses_to_silently_drop_supplied_tokens(tmp_path: Path):
    transfer = _transfer(tmp_path)

    result = transfer.order_words("Xanthe calculated report extra unexplained material")

    assert result["status"] != "answered"
    assert "unplaced_tokens_remain" in result["parse"]["ambiguities"]
    assert result["parse"]["unused_tokens"]


def test_advanced_shuffled_discourse_resolves_passive_negation_and_pronoun(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "route", "part_of_speech": "v", "definition": "send by a particular route"},
        {"lemma": "fail", "part_of_speech": "v", "definition": "stop operating or functioning"},
        {"lemma": "install", "part_of_speech": "v", "definition": "set up for use"},
        {"lemma": "abandon", "part_of_speech": "v", "definition": "give up an activity"},
        {"lemma": "pump", "part_of_speech": "n", "definition": "a mechanical device that moves fluid"},
        {"lemma": "coolant", "part_of_speech": "n", "definition": "a fluid used to transfer heat"},
        {"lemma": "valve", "part_of_speech": "n", "definition": "a device controlling the flow of fluid"},
        {"lemma": "experiment", "part_of_speech": "n", "definition": "a scientific test"},
        {"lemma": "backup", "part_of_speech": "n", "definition": "support available if needed"},
        {"lemma": "auxiliary", "part_of_speech": "s", "definition": "providing additional support"},
        {"lemma": "recently", "part_of_speech": "r", "definition": "at a recent time"},
    ), source="test", require_authority=False)
    with transfer.lexical._connect() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            (("failed", "fail", "v", "past", "test", 1),
             ("installed", "install", "v", "past_participle", "test", 1),
             ("rerouted", "reroute", "v", "past", "test", 1)),
        )

    result = transfer.order_words(
        "rerouted which the experiment an failed Amara recently pump coolant instead "
        "through had she abandon auxiliary not been the after valve backup did installed"
    )

    assert result["answer"] == (
        "After the backup pump, which had been recently installed, failed, Amara did not "
        "abandon the experiment; instead, she rerouted the coolant through an auxiliary valve."
    )
    assert result["parse"]["used_tokens"] == result["parse"]["total_tokens"] == 24
    assert result["parse"]["unused_tokens"] == []
    assert result["parse"]["pronoun_links"][0]["referent"] == "Amara"
    assert result["parse"]["clauses"][1]["negated"] is True


def test_acquired_meaning_transfers_into_unseen_clause_inference_with_receipt(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "bailiwick", "part_of_speech": "n", "definition": "a branch of knowledge",
         "synonyms": ["field", "subject area"]},
        {"lemma": "allot", "part_of_speech": "v", "definition": "give out as a share"},
        {"lemma": "bankrupt", "part_of_speech": "s", "definition": "financially ruined"},
        {"lemma": "finance", "part_of_speech": "n", "definition": "management of money"},
        {"lemma": "fund", "part_of_speech": "n", "definition": "a supply of money"},
        {"lemma": "emergency", "part_of_speech": "n", "definition": "an urgent situation"},
        {"lemma": "supplier", "part_of_speech": "n", "definition": "a person who supplies goods"},
        {"lemma": "area", "part_of_speech": "n", "definition": "a subject of study",
         "synonyms": ["field"]},
        {"lemma": "expertise", "part_of_speech": "n",
         "definition": "special knowledge and skill"},
    ), source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=transfer.lexical)
    for lemma in ("bailiwick", "allot", "bankrupt"):
        wall.encounter(lemma)
    with transfer.lexical._connect() as connection:
        connection.execute(
            "UPDATE acquired_concepts SET stage='retention_1d' "
            "WHERE lemma IN ('bailiwick','allot','bankrupt')"
        )
        connection.execute(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            ("allotted", "allot", "v", "past", "test", 1),
        )

    challenge = transfer.create_challenge(
        kind="sentence_qa",
        material=("Although finance is not her bailiwick, Mara allotted the emergency "
                  "funds to a bankrupt supplier."),
        question="Which activity is outside Mara's area of expertise?",
        expected_answer="finance",
        answer_reason=("Bailiwick means a field of knowledge; the negated clause says "
                       "finance is outside Mara's field."),
    )
    result = transfer.attempt(challenge["challenge_id"])

    assert result["answer"] == "finance"
    assert result["correct"] is True
    assert result["parse"]["frame"]["subject"] == "Mara"
    assert result["parse"]["frame"]["object"] == "emergency funds"
    assert result["parse"]["frame"]["negated"] is False
    assert result["parse"]["clauses"][0]["subject"] == "finance"
    assert result["parse"]["clauses"][0]["negated"] is True
    assert result["parse"]["clauses"][0]["possessor"] == "Mara"
    receipt = result["semantic_evidence"]
    assert receipt["target_lemma"] == "bailiwick"
    assert receipt["target_concept_id"].startswith("aion_concept_")
    assert receipt["target_stage"] == "retention_1d"
    assert receipt["target_reference_fallback"] is False
    assert receipt["model_used"] is False


def test_acquired_inflected_action_meaning_identifies_affected_object(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "vindicate", "part_of_speech": "v",
         "definition": "clear of accusation blame or suspicion"},
        {"lemma": "vindicated", "part_of_speech": "s",
         "definition": "freed from any question of guilt",
         "synonyms": ["cleared", "exonerated"]},
        {"lemma": "panel", "part_of_speech": "n", "definition": "a group of people"},
    ), source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=transfer.lexical)
    wall.encounter("vindicated")
    with transfer.lexical._connect() as connection:
        connection.execute(
            "UPDATE acquired_concepts SET stage='retention_1d' WHERE lemma='vindicated'"
        )
        connection.execute(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            ("vindicated", "vindicate", "v", "past", "test", 1),
        )

    challenge = transfer.create_challenge(
        kind="sentence_qa", material="The panel vindicated Leona.",
        question="Who was cleared of blame?", expected_answer="Leona",
        answer_reason=("Vindicated means cleared or freed from blame; Leona is the "
                       "person affected by the panel's action."),
    )
    result = transfer.attempt(challenge["challenge_id"])

    assert result["answer"] == "Leona"
    assert result["correct"] is True
    assert result["parse"]["frame"]["subject"] == "panel"
    assert result["parse"]["frame"]["action"] == "vindicate"
    assert result["parse"]["frame"]["object"] == "Leona"
    assert result["parse"]["frame"]["tense"] == "past"
    receipt = result["semantic_evidence"]
    assert receipt["intent"] == "semantic_action_patient_inference"
    assert receipt["target_lemma"] == "vindicated"
    assert receipt["action_lemma"] == "vindicate"
    assert receipt["target_reference_fallback"] is False
    assert receipt["model_used"] is False


def test_sealed_target_selects_exact_surface_instead_of_modifier_or_competing_concept(
    tmp_path: Path,
):
    transfer = _transfer(tmp_path)
    records = (
        {"lemma": "reason", "part_of_speech": "n",
         "definition": "capacity for rational thought and inference"},
        {"lemma": "revise", "part_of_speech": "v",
         "definition": "review and rewrite"},
        {"lemma": "unprepared", "part_of_speech": "a",
         "definition": "not ready in advance"},
    )
    transfer.lexical.ingest_records(records, source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=transfer.lexical)
    concepts = {}
    for row in records:
        wall.encounter(row["lemma"])
        concepts[row["lemma"]] = transfer._acquired(row["lemma"])

    cases = (
        ("reason", "Lila inspected the clear reason.",
         "Which word refers to rational thought and inference?", "reason"),
        ("revise", "Lila will revise the manuscript.",
         "Which action is associated with review and rewrite?", "revise"),
        ("unprepared", "The team was unprepared.",
         "Which word indicates that the team was not ready in advance?", "unprepared"),
    )
    for lemma, material, question, expected in cases:
        challenge = transfer.create_challenge(
            kind="sentence_qa", material=material, question=question,
            expected_answer=expected, answer_reason="Meaning-grounded target surface.",
            source="test_teacher_sealed",
            learning_target_concept_id=concepts[lemma]["concept_id"],
        )
        result = transfer.attempt(challenge["challenge_id"])
        assert result["answer"] == expected
        assert result["correct"] is True
        assert result["semantic_evidence"]["target_concept_id"] == concepts[lemma]["concept_id"]


def test_temporal_adjunct_does_not_replace_vindication_main_clause(tmp_path: Path):
    transfer = _transfer(tmp_path)
    transfer.lexical.ingest_records((
        {"lemma": "review", "part_of_speech": "v", "definition": "examine again"},
        {"lemma": "vindicate", "part_of_speech": "v",
         "definition": "clear of accusation blame or suspicion"},
        {"lemma": "vindicated", "part_of_speech": "s",
         "definition": "freed from any question of guilt", "synonyms": ["cleared"]},
        {"lemma": "panel", "part_of_speech": "n", "definition": "a group of people"},
        {"lemma": "evidence", "part_of_speech": "n", "definition": "supporting facts"},
        {"lemma": "colleague", "part_of_speech": "n", "definition": "a coworker"},
        {"lemma": "suspicion", "part_of_speech": "n", "definition": "a feeling of doubt"},
        {"lemma": "remain", "part_of_speech": "v", "definition": "continue in a state"},
    ), source="test", require_authority=False)
    wall = NativeWordwallLearning(repo_root=tmp_path, lexical=transfer.lexical)
    wall.encounter("vindicated")
    with transfer.lexical._connect() as connection:
        connection.execute(
            "UPDATE acquired_concepts SET stage='retention_1d' WHERE lemma='vindicated'"
        )
        connection.executemany(
            "INSERT OR REPLACE INTO morphology_forms VALUES(?,?,?,?,?,?)",
            (("reviewing", "review", "v", "present_participle", "test", 1),
             ("vindicated", "vindicate", "v", "past", "test", 1),
             ("remained", "remain", "v", "past", "test", 1)),
        )

    result = transfer.answer(
        "After reviewing the new evidence, the panel vindicated Leona, "
        "although her colleague remained under suspicion.",
        "Who was cleared of blame?",
    )

    assert result["answer"] == "Leona"
    assert result["parse"]["frame"]["subject"] == "panel"
    assert result["parse"]["frame"]["action"] == "vindicate"
    assert result["parse"]["frame"]["object"] == "Leona"
    assert result["parse"]["frame"]["location"] is None
    assert result["parse"]["clauses"][0]["subordinate"] is True
    assert result["parse"]["clauses"][2]["location"] == "under suspicion"
