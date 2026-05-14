"""
Photon Axioms Exporter
----------------------
Generates RFC documentation tables from axioms.py
"""

from pathlib import Path
from backend.photon.axioms import axioms_to_markdown

DOC_PATH = Path("docs/rfc/photon_core_spec.md")

def export_axioms():
    md = "# Photon Core Specification\n\n"
    md += "## Axioms\n\n"
    md += axioms_to_markdown()
    DOC_PATH.write_text(md, encoding="utf-8")
    print(f"✅ Photon axioms exported to {DOC_PATH}")

if __name__ == "__main__":
    export_axioms()