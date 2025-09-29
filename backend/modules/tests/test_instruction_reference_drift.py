# 📁 backend/modules/tests/test_instruction_reference_drift.py

import os
import pytest

from docs.CodexLang_Instruction import instruction_reference_builder as builder


DOC_PATH = os.path.join("docs", "CodexLang_Instruction", "instruction_reference.md")


def test_instruction_reference_up_to_date():
    """Ensure the generated instruction_reference.md matches the builder output."""
    # Generate fresh content
    generated = builder.build_reference()

    # Read existing file
    assert os.path.exists(DOC_PATH), f"Expected {DOC_PATH} to exist. Run the builder once."
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        existing = f.read()

    # Compare
    if generated.strip() != existing.strip():
        # Show diff in pytest output
        diff_msg = (
            f"instruction_reference.md is outdated!\n"
            f"Run: python docs/CodexLang_Instruction/instruction_reference_builder.py\n"
        )
        assert generated.strip() == existing.strip(), diff_msg