# 📁 backend/modules/tests/test_instruction_reference_builder.py

import pytest
import docs.CodexLang_Instruction.instruction_reference_builder as builder


def test_build_reference_runs_and_contains_sections():
    output = builder.build_reference()

    # Ensure output is non-empty markdown
    assert isinstance(output, str)
    assert len(output) > 100  # sanity check

    # Must include critical sections
    assert "# 📖 CodexLang Instruction Reference" in output
    assert "## ⚖️ Collision Resolver Cheat Sheet" in output
    assert "## 🔑 Alias Table" in output
    assert "## 📊 Priority Order" in output

    # At least one alias from config should appear
    found_alias = any(alias in output for alias in builder.ALIASES.keys())
    assert found_alias

    # At least one collision symbol (⊕, ⊗, etc.) should appear
    found_collision = any(sym in output for sym in builder.COLLISIONS.keys())
    assert found_collision