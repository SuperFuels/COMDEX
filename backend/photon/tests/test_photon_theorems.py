"""
Test: Photon Theorems
---------------------
Check equivalence results against Photon rewriter.
Also regenerates docs/rfc/photon_core_spec.md with:
 - Glyph Axioms Table (philosophical view)
 - Sympy Axioms Table (machine view)
 - Theorem verification results
"""

import pathlib
from backend.photon.theorems import THEOREMS
from backend.photon.axioms import axioms_to_markdown, axioms_to_markdown_sympy


def test_theorem_results():
    """Verify all Photon theorems hold."""
    for name, thm in THEOREMS.items():
        assert thm["result"], f"Theorem {name} failed: {thm['statement']}"

    # --- Auto-generate RFC ---
    lines = [
        "# Photon Core Specification",
        "",
        "## Glyph Axioms (Philosophical View)",
        "",
        axioms_to_markdown(),
        "",
        "## Sympy Axioms (Machine View)",
        "",
        axioms_to_markdown_sympy(),
        "",
        "## Theorem Verification",
        "",
        "| Theorem | Statement | Result |",
        "|---------|-----------|--------|",
    ]

    for name, thm in THEOREMS.items():
        result_str = "✅ Proven" if thm["result"] else "❌ Counterexample"
        lines.append(f"| {name} | {thm['statement']} | {result_str} |")

    path = pathlib.Path("docs/rfc/photon_core_spec.md")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 Photon Core RFC updated → {path}")