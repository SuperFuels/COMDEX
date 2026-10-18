import json
from pathlib import Path
import time

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning
from backend.modules.aion_cognition.native_semantic_transfer_academy import (
    NativeSemanticTransferAcademy, _json_object,
)


def _academy(tmp_path: Path) -> NativeSemanticTransferAcademy:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "calculate", "part_of_speech": "v", "definition": "compute a numerical result"},
        {"lemma": "report", "part_of_speech": "n", "definition": "a written account"},
    ), source="test", require_authority=False)
    wordwall = NativeWordwallLearning(repo_root=tmp_path, lexical=lexical)
    encountered = wordwall.encounter("calculate")
    concept = encountered[0]
    with lexical._connect() as connection:
        connection.execute(
            "UPDATE acquired_concepts SET stage='productive' WHERE concept_id=?",
            (concept["concept_id"],),
        )
    return NativeSemanticTransferAcademy(repo_root=tmp_path, lexical=lexical)


def test_academy_uses_acquired_concept_and_keeps_qwen_out_of_student_answer(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]

    def teacher(_prompt: str):
        return {"model": "qwen-test", "content": json.dumps({"challenges": [{
            "concept_id": concept["concept_id"], "lemma": "calculate",
            "family": "semantic_patient",
            "material": "Yesterday, Xanthe calculated the report.",
            "question": "Which item was affected by the compute action?",
            "expected_answer": "report",
            "answer_reason": "Calculate means compute a result.",
        }]})}

    result = academy.run_cycle(teacher_client=teacher, limit=1)

    assert result["attempted"] == 1
    assert result["correct"] == 1
    assert result["reinforced"] == 1
    assert result["model_used_for_student_answers"] is False
    assert result["teacher_saw_student_answer"] is False
    assert academy.metrics()["cycles"] == 1


def test_academy_never_uses_bad_teacher_key_and_compiles_safe_foundation(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]

    def teacher(_prompt: str):
        return {"model": "qwen-test", "content": json.dumps({"challenges": [{
            "concept_id": concept["concept_id"], "lemma": "calculate",
            "family": "semantic_patient",
            "material": "Yesterday, Xanthe calculated the report.",
            "question": "Who did the work?", "expected_answer": "Mireya",
            "answer_reason": "Calculate means compute a result.",
        }]})}

    result = academy.run_cycle(teacher_client=teacher, limit=1)

    assert result["attempted"] == 1
    assert result["correct"] == 1
    assert result["concepts"][0]["foundation_compiled"] is True


def test_teacher_json_repairs_a_missing_line_comma():
    decoded = _json_object('''{"challenges":[{
      "concept_id":"a"
      "lemma":"calm",
      "family":"semantic_entity"
    }]}''')

    assert decoded["challenges"][0]["lemma"] == "calm"


def test_academy_promotes_only_after_varied_contextual_and_productive_evidence(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]
    concept_id = concept["concept_id"]
    with academy._connect() as connection:
        connection.execute(
            "UPDATE acquired_concepts SET stage='grounded' WHERE concept_id=?", (concept_id,),
        )
    now = time.time()

    first = academy._record_progress(
        concept_id=concept_id, evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now,
    )
    recalled = academy._record_progress(
        concept_id=concept_id, evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now + 1,
    )
    assert first["promoted"] is False
    assert recalled["stage_after"] == "recalled"

    academy._record_progress(
        concept_id=concept_id, evidence_tier="free_transfer",
        family="semantic_patient", correct=True, now=now + 2,
    )
    contextual = academy._record_progress(
        concept_id=concept_id, evidence_tier="free_transfer",
        family="cause_inference", correct=True, now=now + 3,
    )
    assert contextual["stage_after"] == "contextual"

    academy._record_progress(
        concept_id=concept_id, evidence_tier="free_transfer",
        family="paraphrase", correct=True, now=now + 4,
    )
    productive = academy._record_progress(
        concept_id=concept_id, evidence_tier="free_transfer",
        family="comparison", correct=True, now=now + 5,
    )
    assert productive["stage_after"] == "productive"
    assert productive["distinct_free_families"] == 4


def test_failed_concept_cools_down_and_rotates_out_of_immediate_selection(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]
    result = academy._record_progress(
        concept_id=concept["concept_id"], evidence_tier="free_transfer",
        family="comparison", correct=False, now=time.time(),
    )

    assert result["failure_streak"] == 1
    assert result["cooldown_until"] > time.time()
    assert all(
        row["concept_id"] != concept["concept_id"] for row in academy._candidates(12)
    )


def test_advanced_repair_requires_novel_transfer_not_foundation_fallback(tmp_path: Path):
    academy = _academy(tmp_path)
    candidate = academy._candidates(1)[0]
    candidate.update({
        "needs_scaffold": False,
        "free_families": ["semantic_patient"],
        "recent_materials": ["Mireya calculated the report."],
    })

    prompt = academy._repair_prompt(
        candidate, {"family": "cause_inference"}, ["repeated_material"],
    )

    assert "genuinely new advanced transfer challenge" in prompt
    assert "Required transfer family: cause_inference" in prompt
    assert "compile the final sentence, question, answer span and explanation" in prompt
    assert "material" not in prompt.split("Return only JSON:", 1)[1]


def test_constrained_transfer_builder_owns_answer_role_and_ignores_unsafe_teacher_fields(
    tmp_path: Path,
):
    academy = _academy(tmp_path)
    candidate = academy._candidates(1)[0]
    candidate.update({
        "needs_scaffold": False,
        "required_transfer_family": "cause_inference",
        "features": ["compute"],
        "recent_materials": [],
    })

    item = academy._compile_transfer_contract(candidate, {
        "name": "Leona", "patient": "sensor", "context": "During the audit",
        "material": "Wrong material.", "expected_answer": "wrong answer",
    }, 7)
    verified, problems = academy._verify(item, candidate)

    assert item["material"] != "Wrong material."
    assert item["expected_answer"] != "wrong answer"
    assert item["expected_answer"] in item["material"]
    assert item["family"] == "cause_inference"
    assert verified is True
    assert problems == []


def test_malformed_teacher_slots_fall_back_without_blocking_advanced_exam(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]
    now = time.time()
    academy._record_progress(
        concept_id=concept["concept_id"], evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now,
    )
    academy._record_progress(
        concept_id=concept["concept_id"], evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now + 1,
    )

    def malformed_teacher(_prompt: str):
        return {"model": "qwen-test", "content": "not-json"}

    result = academy.run_cycle(teacher_client=malformed_teacher, limit=1)

    assert result["attempted"] == 1
    assert result["rejected"] == 0
    assert result["compiled_transfer_contracts"] == 1
    assert result["teacher_slot_fallbacks"] == 1
    assert result["model_used_for_student_answers"] is False


def test_advanced_validator_rejects_metalinguistic_and_wrong_pos_family(tmp_path: Path):
    academy = _academy(tmp_path)
    candidate = academy._candidates(1)[0]
    candidate.update({
        "needs_scaffold": False,
        "required_transfer_family": "semantic_patient",
        "features": ["compute"],
    })
    item = {
        "concept_id": candidate["concept_id"], "lemma": "calculate",
        "family": "property_inference",
        "material": "Yesterday, Xanthe calculated the report.",
        "question": "Which word in the material means compute?",
        "expected_answer": "calculated",
        "answer_reason": "Calculate means compute a result.",
    }

    verified, problems = academy._verify(item, candidate)

    assert verified is False
    assert "advanced_family_mismatch" in problems
    assert "part_of_speech_family_mismatch" in problems
    assert "metalinguistic_question" in problems


def test_focused_cohort_keeps_recalled_concept_in_advanced_queue(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]
    now = time.time()
    academy._record_progress(
        concept_id=concept["concept_id"], evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now,
    )
    academy._record_progress(
        concept_id=concept["concept_id"], evidence_tier="guided_foundation",
        family="semantic_patient", correct=True, now=now + 1,
    )

    advanced = academy._candidates(1, prefer_advanced=True)[0]
    metrics = academy.metrics()

    assert advanced["concept_id"] == concept["concept_id"]
    assert advanced["focused_cohort"] == 1
    assert metrics["focused_cohort_active"] == 1
    assert metrics["advanced_transfer_share"] == 0.75


def test_noun_and_property_rotation_never_emits_one_item_comparison(tmp_path: Path):
    academy = _academy(tmp_path)

    for part_of_speech in ("n", "a", "s"):
        candidate = {"part_of_speech": part_of_speech, "free_families": []}
        observed = {
            academy._next_transfer_family(candidate, cycle) for cycle in range(12)
        }
        assert "comparison" not in observed
        assert len(observed) >= 4


def test_contextual_metric_counts_concepts_that_advanced_to_productive(tmp_path: Path):
    academy = _academy(tmp_path)
    concept = academy._candidates(1)[0]
    now = time.time()
    for index, family in enumerate((
        "semantic_patient", "cause_inference", "paraphrase", "negation_scope",
    )):
        academy._record_progress(
            concept_id=concept["concept_id"], evidence_tier="free_transfer",
            family=family, correct=True, now=now + index,
        )

    metrics = academy.metrics()
    assert metrics["productive_use_concepts"] == 1
    assert metrics["currently_contextual_use_concepts"] == 0
    assert metrics["contextual_use_concepts"] == 1


def test_next_transfer_family_prefers_unseen_family_for_pos():
    candidate = {
        "part_of_speech": "v",
        "free_families": ["semantic_patient", "cause_inference"],
    }

    selected = NativeSemanticTransferAcademy._next_transfer_family(candidate, 0)

    assert selected in {"contextual_meaning", "paraphrase", "negation_scope"}


def test_advanced_validator_rejects_target_used_as_wrong_part_of_speech(tmp_path: Path):
    academy = _academy(tmp_path)
    candidate = academy._candidates(1)[0]
    candidate.update({
        "needs_scaffold": False,
        "part_of_speech": "n",
        "required_transfer_family": "semantic_entity",
        "features": ["compute"],
    })
    item = {
        "concept_id": candidate["concept_id"], "lemma": "calculate",
        "family": "semantic_entity",
        "material": "Xanthe will calculate the report tomorrow.",
        "question": "What action will Xanthe perform that is associated with compute?",
        "expected_answer": "calculate",
        "answer_reason": "Calculate is associated with compute.",
    }

    verified, problems = academy._verify(item, candidate)

    assert verified is False
    assert "target_part_of_speech_mismatch" in problems


def test_advanced_validator_accepts_meaning_grounded_parseable_transfer(tmp_path: Path):
    academy = _academy(tmp_path)
    candidate = academy._candidates(1)[0]
    candidate.update({
        "needs_scaffold": False,
        "required_transfer_family": "semantic_patient",
        "features": ["compute"],
    })
    item = {
        "concept_id": candidate["concept_id"], "lemma": "calculate",
        "family": "semantic_patient",
        "material": "Yesterday, Xanthe calculated the report.",
        "question": "What did Xanthe affect through the act of compute?",
        "expected_answer": "report",
        "answer_reason": "Calculate means compute; report is its direct object.",
    }

    verified, problems = academy._verify(item, candidate)

    assert verified is True
    assert problems == []
