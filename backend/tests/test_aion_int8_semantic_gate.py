from backend.scripts.run_aion_int8_semantic_gate import _equivalent, _extract_json


def test_extract_json_from_wrapped_response() -> None:
    assert _extract_json('Result:\n```json\n{"value": 2}\n```') == {"value": 2}


def test_equivalent_is_strict_on_keys_and_tolerant_on_numbers() -> None:
    assert _equivalent({"x": 1.005}, {"x": 1.0})
    assert not _equivalent({"x": 1.0, "extra": 2}, {"x": 1.0})
