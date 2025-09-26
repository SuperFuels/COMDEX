"""
Photon Core Spec Export
-----------------------
Generates docs/rfc/photon_core_spec.md with both glyph and sympy-safe axiom tables.
"""

from pathlib import Path
from backend.photon.axioms import axioms_to_markdown, axioms_to_markdown_sympy

DOC_PATH = Path("docs/rfc/photon_core_spec.md")

def export_core_spec():
    content = [
        "# Photon Core Specification",
        "",
        "## Glyph Axioms",
        axioms_to_markdown(),
        "",
        "## Sympy-Safe Axioms",
        axioms_to_markdown_sympy(),
    ]
    DOC_PATH.write_text("\n".join(content), encoding="utf-8")
    print(f"📄 Photon Core Spec written to {DOC_PATH}")

if __name__ == "__main__":
    export_core_spec()