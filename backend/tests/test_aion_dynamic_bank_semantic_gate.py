from backend.scripts.run_aion_int8_semantic_mcq_gate import _choice


def test_semantic_choice_parser_rejects_missing_choice() -> None:
    assert _choice("The result is B.") == "B"
    assert _choice("no selection") is None
