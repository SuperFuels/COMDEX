# File: backend/lean/tests/test_glyph_roundtrip.py
"""
Round-Trip Translator Test
──────────────────────────────────────────────
Ensures that Lean -> Glyph -> Lean translation preserves
operator semantics via glyph_bindings.

Flow:
    1.  Convert Lean file -> CodexLang container  (lean_to_glyph)
    2.  Convert container -> Lean file           (glyph_to_lean)
    3.  Re-parse Lean output -> container again
    4.  Compare logic fields and operator counts
"""

import os
import json
import tempfile
from backend.modules.lean.lean_to_glyph import lean_to_dc_container
from backend.modules.lean.glyph_to_lean import build_lean_from_codex
from backend.modules.lean.imports.glyph_bindings import GLYPH_TO_LEAN


def _glyph_count(expr: str) -> int:
    """Utility: count how many glyphs appear in expression."""
    return sum(expr.count(k) for k in GLYPH_TO_LEAN.keys())


def test_roundtrip_minimal():
    """
    1️⃣  Create temporary Lean input.
    2️⃣  Convert -> container.
    3️⃣  Convert back -> Lean.
    4️⃣  Compare symbolic content.
    """

    # --- Create a temporary minimal Lean axiom ---
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as tmp:
        tmp.write(
            "axiom collapse_axiom : ∀ ψ : Wave, measure (resonate ψ) = project ψ\n"
        )
        lean_path = tmp.name

    try:
        # Step 1: Lean -> container
        container = lean_to_dc_container(lean_path)
        assert "symbolic_logic" in container, "Missing symbolic_logic field"
        entry = container["symbolic_logic"][0]
        logic = entry["logic"]

        # Step 2: Container -> Lean
        with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as tmp_out:
            lean_out = tmp_out.name
        build_lean_from_codex(container, lean_out)

        # Step 3: Re-parse Lean -> new container
        container2 = lean_to_dc_container(lean_out)
        logic2 = container2["symbolic_logic"][0]["logic"]

        # Step 4: Compare glyph counts and content
        g1 = _glyph_count(logic)
        g2 = _glyph_count(logic2)

        print(f"\n[Roundtrip] Logic1 = {logic}")
        print(f"[Roundtrip] Logic2 = {logic2}")
        print(f"[Glyph count] before={g1}, after={g2}")

        assert logic.strip() == logic2.strip() or g1 == g2, \
            "Round-trip glyph translation mismatch"

        print("\n✅ Round-trip translator test passed.")

    finally:
        # Clean up temporary files
        try:
            os.remove(lean_path)
        except OSError:
            pass


if __name__ == "__main__":
    test_roundtrip_minimal()