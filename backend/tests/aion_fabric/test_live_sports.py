from __future__ import annotations

from backend.modules.aion_fabric.sports import LiveSportsInterpreter
from backend.modules.aion_fabric.voice import parse_voice_intent


def test_live_sports_reads_captured_score_and_names_leader(tmp_path):
    service = LiveSportsInterpreter(tmp_path)
    result = service.interpret(
        live_context={"context_hash": "a" * 64, "recent_transcripts": []},
        screen_understanding={
            "scoreboard": {
                "detected": True,
                "score_text": "REAL MADRID 2 - 1 BARCELONA",
                "clock": "78:42",
                "confidence": 0.92,
            }
        },
        question_kind="leader",
        question="who is winning",
    )

    assert "REAL MADRID are ahead" in result["answer"]
    assert result["scoreboard"]["structured"]["left_score"] == 2
    assert result["scoreboard"]["clock"] == "78:42"
    assert result["evidence_boundary"]["player_identity_inferred"] is False
    assert result["presentation"]["playback_preserved"] is True
    assert service.latest()["interpretation_id"] == result["interpretation_id"]


def test_live_sports_explains_rule_without_claiming_decision_was_correct(tmp_path):
    result = LiveSportsInterpreter(tmp_path).interpret(
        live_context={
            "context_hash": "b" * 64,
            "recent_transcripts": ["The assistant referee has flagged for offside."],
        },
        screen_understanding=None,
        question_kind="decision",
        question="why was that offside",
    )

    assert result["rule_key"] == "offside"
    assert "second-last opponent" in result["rule_explanation"]
    assert result["observed_incident_cue"] is True
    assert result["evidence_boundary"]["referee_decision_verified"] is False
    assert "cannot verify" in result["limitation"]


def test_live_sports_refuses_unseen_incident(tmp_path):
    result = LiveSportsInterpreter(tmp_path).interpret(
        live_context={"context_hash": "c" * 64, "recent_transcripts": []},
        screen_understanding=None,
        question_kind="decision",
        question="explain that referee decision",
    )

    assert result["confidence"] == 0
    assert "did not capture enough evidence" in result["answer"]
    assert result["internet_used"] is False
    assert result["paid_ai_used"] is False


def test_live_sports_voice_intents_are_contextual():
    score = parse_voice_intent("Pilot what is the score")
    assert score.action == "live_event"
    assert score.arguments["kind"] == "score"
    decision = parse_voice_intent("Pilot explain that referee decision")
    assert decision.action == "live_sports"
    assert decision.arguments["kind"] == "decision"
