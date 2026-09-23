from __future__ import annotations

from backend.modules.aion_inference.trajectory_verification_ladder import (
    deterministic_entailment_answer,
    derive_simple_entailments,
    earliest_failure,
    verify_candidate,
)


def test_repeated_phrase_escalates_before_completion() -> None:
    tokens = [1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 7, 8, 10, 11, 12, 13, 14, 30]
    failure = earliest_failure(tokens)
    assert failure is not None
    assert failure.kind == "repeated_ngram"
    assert failure.first_detected_token < len(tokens)


def test_repeated_single_token_escalates() -> None:
    failure = earliest_failure([1, 2, 3, 4, 5, 8, 8, 8, 8, 8, 9])
    assert failure is not None
    assert failure.kind == "repeated_token_run"


def test_repeated_control_token_escalates_immediately() -> None:
    failure = earliest_failure([200005, 200005, 35644, 200008])
    assert failure is not None
    assert failure.kind == "repeated_control_token"
    assert failure.first_detected_token == 2


def test_unseen_one_hop_entailment_is_derived_and_accepted() -> None:
    prompt = "Every green parcel is insured. This parcel is green. What follows?"
    assert derive_simple_entailments(prompt) == ("this parcel is insured",)
    decision = verify_candidate(prompt, "Therefore, this parcel is insured.", range(30))
    assert decision.decision == "ACCEPT"
    assert deterministic_entailment_answer(prompt) == "This parcel is insured."


def test_two_hop_entailment_is_supported() -> None:
    prompt = "Every bronze item is metal. Every metal item is heavy. This item is bronze."
    conclusions = derive_simple_entailments(prompt)
    assert conclusions == ("this item is heavy", "this item is metal")


def test_missing_required_conclusion_escalates() -> None:
    prompt = "Every green parcel is insured. This parcel is green. What follows?"
    decision = verify_candidate(prompt, "The parcel is green.", range(30))
    assert decision.decision == "ESCALATE"


def test_open_ended_clean_answer_requires_critic() -> None:
    decision = verify_candidate(
        "Explain why rain falls.",
        "Water droplets grow until gravity pulls them down.",
        range(30),
    )
    assert decision.decision == "REQUIRE_CRITIC"
    assert deterministic_entailment_answer("Explain why rain falls.") is None


def test_no_false_loop_on_ordinary_repetition() -> None:
    tokens = [1, 2, 3, 1, 2, 4, 5, 6, 7, 5, 6, 8, 9, 10, 11, 12, 13, 14]
    assert earliest_failure(tokens) is None


def test_question_restatement_does_not_trip_short_ngram_rule() -> None:
    tokens = [
        200005, 35644, 200008, 2167, 1309, 316, 13424, 36161, 2086, 326,
        3609, 13, 51441, 8205, 483, 36161, 11733, 326, 3609, 13, 200007,
    ]
    assert earliest_failure(tokens) is None
