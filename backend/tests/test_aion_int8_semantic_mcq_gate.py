from backend.scripts.run_aion_int8_semantic_mcq_gate import _choice


def test_choice_extracts_standalone_letter_only() -> None:
    assert _choice("B") == "B"
    assert _choice("Answer: c.") == "C"
    assert _choice("because") is None
