from __future__ import annotations

from backend.modules.aion_fabric.education import EducationLearningCentre


def test_learning_session_hides_answer_and_awards_persistent_stars(tmp_path):
    centre = EducationLearningCentre(tmp_path)
    started = centre.start("explorer_a")
    lesson = started["session"]
    assert lesson["phase"] == "question"
    assert "correct_index" not in lesson
    assert started["privacy"]["open_web"] is False

    internal = centre._load()["session"]
    result = centre.answer(int(internal["correct_index"]))
    assert result["session"]["was_correct"] is True
    assert result["session"]["correct_in_session"] == 1
    assert result["session"]["answered_in_session"] == 1
    assert result["session"]["lesson_total"] == 50
    assert result["session"]["feedback"].startswith("✅ Correct!")
    assert result["profiles"]["explorer_a"]["stars"] == 2
    assert EducationLearningCentre(tmp_path).snapshot()["profiles"]["explorer_a"]["stars"] == 2


def test_learning_profiles_are_separate_and_conversation_round_arrives(tmp_path):
    centre = EducationLearningCentre(tmp_path)
    centre.start("explorer_a")
    centre.answer(int(centre._load()["session"]["correct_index"]))
    centre.start("explorer_b")
    assert centre.snapshot()["profiles"]["explorer_b"]["stars"] == 0
    for _ in range(3):
        session = centre._load()["session"]
        if session["phase"] == "question":
            centre.answer(int(session["correct_index"]))
        centre.next_round()
    assert centre.snapshot()["session"]["round_kind"] == "conversation"


def test_age_difficulty_subjects_and_original_illustrations_are_local(tmp_path):
    centre = EducationLearningCentre(tmp_path)
    maths = centre.start("explorer_a", age_band="8-9", difficulty="developing", subject="mathematics")
    assert maths["session"]["round_kind"] == "mathematics"
    assert maths["session"]["illustration_uri"].startswith("data:image/svg+xml,")
    assert maths["profiles"]["explorer_a"]["subject"] == "mathematics"
    assert maths["curriculum"]["paid_ai_required"] is False
    science = centre.start("explorer_b", age_band="10-12", difficulty="challenge", subject="science")
    assert science["session"]["round_kind"] == "science"
    assert science["privacy"]["advertising_profiles_created"] is False


def test_pronunciation_discards_raw_voice_and_transcript(tmp_path):
    centre = EducationLearningCentre(tmp_path)
    started = centre.start("explorer_a")
    expected = started["session"]["speak_text"]
    result = centre.assess_pronunciation(expected)
    assert result["assessment"]["score"] >= 99
    assert result["assessment"]["raw_audio_retained"] is False
    assert result["assessment"]["raw_transcript_retained"] is False
    persisted = centre.path.read_text(encoding="utf-8")
    assert "recognised_text" not in persisted
    assert centre.snapshot()["profiles"]["explorer_a"]["pronunciation_attempts"] == 1


def test_parent_report_and_corrections_require_guardian_identity(tmp_path):
    centre = EducationLearningCentre(tmp_path)
    centre.start("explorer_a")
    try:
        centre.parent_report("explorer_a", guardian_persona_id="")
    except PermissionError:
        pass
    else:
        raise AssertionError("guardian boundary was not enforced")
    centre.record_parent_correction(
        "explorer_a", guardian_persona_id="parent_private", card_id="hello", note="Practise this again tomorrow."
    )
    report = centre.parent_report("explorer_a", guardian_persona_id="parent_private")
    assert len(report["guardian_corrections"]) == 1
    assert report["child_raw_voice_available"] is False
    assert "parent_private" not in centre.path.read_text(encoding="utf-8")
