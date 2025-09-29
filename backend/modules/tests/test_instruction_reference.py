import os
import re

import pytest

from docs.CodexLang_Instruction.instruction_reference_builder import build_reference
from backend.modules.codex.collision_resolver import COLLISIONS
from backend.modules.codex.canonical_ops import OP_METADATA


def test_all_ops_in_reference(tmp_path):
    """
    Ensure every canonical op in OP_METADATA appears in the generated reference.
    """
    output = build_reference()

    for key in OP_METADATA.keys():
        assert f"`{key}`" in output, f"Missing {key} in instruction reference"


def test_collision_annotations(tmp_path):
    """
    Ensure every collision listed in COLLISIONS is annotated in the doc with '⚠ Collides With'.
    """
    output = build_reference()

    for symbol, options in COLLISIONS.items():
        if len(options) > 1:
            # Each domain-specific key must show collisions
            for key in options:
                if key in OP_METADATA:  # only check documented ones
                    section_pattern = re.compile(rf"### `{re.escape(key)}`([\s\S]*?)(?=---)", re.MULTILINE)
                    section = section_pattern.search(output)
                    assert section, f"Section for {key} not found in doc"
                    section_text = section.group(1)
                    # Should mention at least one other colliding key
                    others = [o for o in options if o != key]
                    assert any(o in section_text for o in others), (
                        f"Collision note missing in {key} section: expected one of {others}"
                    )


def test_table_of_contents_consistency():
    """
    Ensure all keys appear in the TOC anchors.
    """
    output = build_reference()

    # Collect anchors from TOC
    toc_section = re.search(r"## Table of Contents([\s\S]*?)---", output)
    assert toc_section, "TOC not found in doc"
    toc_text = toc_section.group(1)

    for key in OP_METADATA.keys():
        anchor = key.replace(":", "")
        assert f"#{anchor}" in toc_text, f"Missing TOC entry for {key}"