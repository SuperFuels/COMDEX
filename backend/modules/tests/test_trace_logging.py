import pytest
from backend.modules.glyphos.codexlang_translator import (
    parse_action_expr,
    translate_node,
    translate_to_instruction,
)
from backend.modules.glyphos.glyph_instruction_set import register_instruction


# --- Dummy instruction for testing ---
class DummyInstr:
    def __init__(self, op_name):
        self.op_name = op_name

    def execute(self, *args, **kwargs):
        # Always return something non-None
        return (self.op_name, list(args))


@pytest.fixture(autouse=True)
def register_dummy_instructions():
    # Register dummy handlers for canonical ops used in tests
    register_instruction("logic:⊕", DummyInstr("logic:⊕"))
    register_instruction("logic:↔", DummyInstr("logic:↔"))
    yield
    # no teardown needed - safe to persist


# --- Tests ---
def test_trace_log_collects_execution_steps():
    expr = "⊕(A, B)"  # simple binary op
    parsed = parse_action_expr(expr)
    parsed = translate_node(parsed)
    parsed_glyph = {"action": parsed}  # ✅ wrap into dict

    trace_log = []
    result = translate_to_instruction(parsed_glyph, trace_log=trace_log)

    # Result should not be an error
    assert result is not None

    # Trace log should have entries
    assert isinstance(trace_log, list)
    assert len(trace_log) >= 1

    # Each entry should have expected keys
    for entry in trace_log:
        assert "stage" in entry
        assert "op" in entry
        assert "result" in entry


def test_trace_log_with_nested_expression():
    expr = "⊕(A, ↔(B, C))"
    parsed = parse_action_expr(expr)
    parsed = translate_node(parsed)
    parsed_glyph = {"action": parsed}  # ✅ wrap into dict

    trace_log = []
    result = translate_to_instruction(parsed_glyph, trace_log=trace_log)

    # Should produce a valid output
    assert result is not None

    # Ensure nested ops are traced
    ops = [entry["op"] for entry in trace_log]
    assert any("⊕" in op for op in ops)
    assert any("↔" in op for op in ops)


def test_trace_log_skips_when_not_provided():
    expr = "⊕(A, B)"
    parsed = parse_action_expr(expr)
    parsed = translate_node(parsed)
    parsed_glyph = {"action": parsed}  # ✅ wrap into dict

    # No trace_log provided
    result = translate_to_instruction(parsed_glyph)
    assert result is not None  # still works