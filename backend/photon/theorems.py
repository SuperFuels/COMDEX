"""
Photon Theorems
---------------
Derived theorems from Photon axioms.
These are auto-checked with the Photon rewriter.
"""

from backend.photon.rewriter import rewriter


THEOREMS = {
    "T1_comm_add": {
        "statement": "(a ⊕ b) ≡ (b ⊕ a)",
        "result": rewriter.equivalent("a ⊕ b", "b ⊕ a"),
    },
    "T2_assoc_add": {
        "statement": "((a ⊕ b) ⊕ c) ≡ (a ⊕ (b ⊕ c))",
        "result": rewriter.equivalent("(a ⊕ b) ⊕ c", "a ⊕ (b ⊕ c)"),
    },
    "T3_grad_add": {
        "statement": "∇(a ⊕ b) ≡ (∇a ⊕ ∇b)",
        "result": rewriter.equivalent("∇(a ⊕ b)", "∇a ⊕ ∇b"),
    },
    "T4_grad_mul": {
        "statement": "∇(a ⊗ b) ≡ (∇a ⊗ b) ⊕ (a ⊗ ∇b)",
        "result": rewriter.equivalent(
            "∇(a ⊗ b)", "(∇a ⊗ b) ⊕ (a ⊗ ∇b)"
        ),
    },
    "T5_sym_eq": {
        "statement": "(a ↔ b) ≡ (b ↔ a)",
        "result": rewriter.equivalent("a ↔ b", "b ↔ a"),
    },
    "T6_grad_nested": {
        "statement": "∇((a ⊕ b) ⊗ c) ≡ ((∇a ⊕ ∇b) ⊗ c) ⊕ ((a ⊕ b) ⊗ ∇c)",
        "result": rewriter.equivalent(
            "∇((a ⊕ b) ⊗ c)",
            "((∇a ⊕ ∇b) ⊗ c) ⊕ ((a ⊕ b) ⊗ ∇c)",
        ),
    },
}


def export_results_md(path: str = "docs/rfc/photon_results.md"):
    """Export theorem results to Markdown table."""
    lines = [
        "# Photon Theorems Results",
        "",
        "Automated proof snapshot.",
        "",
        "| Theorem | Statement | Result |",
        "|---------|-----------|--------|",
    ]
    for name, thm in THEOREMS.items():
        result_str = "✅ Proven" if thm["result"] else "❌ Counterexample"
        lines.append(f"| {name} | {thm['statement']} | {result_str} |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    export_results_md()
    print("📄 Photon theorem results exported -> docs/rfc/photon_results.md")