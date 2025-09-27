# ============================================
# 📁 backend/modules/photon/photon_codex_adapter.py
# ============================================
"""
Photon ↔ Codex Adapter

Bridges Codex scrolls (CodexLang ASTs) with Photon ASTs
so both systems can share a consistent symbolic execution tree.

Contracts:
  - Input: Codex scroll (from codex_scroll_builder / codexlang_parser)
  - Output: Photon-compatible AST (dict-based JSON)
  - Reverse: Photon AST → Codex AST

Downstream:
  - BeamEvents and CollapseTraces must remain aligned
  - Tessaris intent alignment (metadata={"origin":"photon"})
"""

from typing import Dict, Any


# -------------------------------
# Core conversion
# -------------------------------

def codex_to_photon_ast(codex_scroll: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Codex scroll (AST from CodexLang parser) into a Photon AST.

    Args:
        codex_scroll (dict): Parsed Codex AST

    Returns:
        dict: Photon AST, JSON-compatible
    """
    return {
        "ast_type": "photon_ast",
        "origin": "codex",
        "root": codex_scroll.get("root"),
        "nodes": codex_scroll.get("nodes", []),
        "metadata": {
            "source": "codex",
            "glyphs": codex_scroll.get("glyphs", []),
            "intents": codex_scroll.get("intents", []),
        }
    }


def photon_to_codex_ast(photon_ast: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Photon AST back into Codex scroll format.

    Args:
        photon_ast (dict): Photon AST

    Returns:
        dict: Codex scroll-compatible structure
    """
    return {
        "root": photon_ast.get("root"),
        "nodes": photon_ast.get("nodes", []),
        "glyphs": photon_ast.get("metadata", {}).get("glyphs", []),
        "intents": photon_ast.get("metadata", {}).get("intents", []),
    }


# -------------------------------
# Tessaris alignment
# -------------------------------

def align_with_tessaris(photon_ast: Dict[str, Any], tessaris) -> Dict[str, Any]:
    """
    Run Tessaris alignment on a Photon AST to enrich with symbolic intents.

    Args:
        photon_ast (dict): Photon AST
        tessaris: Tessaris engine instance (must expose extract_intents_from_glyphs)

    Returns:
        dict: Updated Photon AST with Tessaris intents
    """
    glyphs = photon_ast.get("metadata", {}).get("glyphs", [])
    intents = tessaris.extract_intents_from_glyphs(
        glyphs,
        metadata={"origin": "photon"}
    )
    photon_ast["metadata"]["intents"] = intents
    return photon_ast


# -------------------------------
# Debug harness
# -------------------------------
if __name__ == "__main__":
    # Fake Codex scroll for testing
    codex_scroll = {
        "root": "⊗",
        "nodes": [
            {"id": "n1", "op": "⊗", "args": ["R1", "R2"]}
        ],
        "glyphs": ["⊗", "R1", "R2"],
        "intents": []
    }

    photon_ast = codex_to_photon_ast(codex_scroll)
    print("Photon AST:", photon_ast)

    roundtrip = photon_to_codex_ast(photon_ast)
    print("Roundtrip Codex AST:", roundtrip)