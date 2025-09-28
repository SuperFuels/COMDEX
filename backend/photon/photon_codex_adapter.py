# ============================================
# 📁 backend/modules/photon/photon_codex_adapter.py
# ============================================
"""
Photon ↔ Codex Adapter

Bridges Codex scrolls (CodexLang ASTs) with Photon ASTs
so both systems can share a consistent symbolic execution tree.
"""

from typing import Dict, Any

try:
    from backend.modules.symbolic.codex_ast_types import CodexAST
except ImportError:
    CodexAST = None  # Safe fallback if class not available


# -------------------------------
# Core conversion
# -------------------------------

def codex_to_photon_ast(codex_scroll: Any) -> Dict[str, Any]:
    """
    Convert a Codex scroll (AST from CodexLang parser) into a Photon AST.
    """
    # ✅ Unwrap CodexAST → dict
    if CodexAST and isinstance(codex_scroll, CodexAST):
        codex_scroll = codex_scroll.data

    if not isinstance(codex_scroll, dict):
        raise TypeError(
            f"codex_to_photon_ast expected dict or CodexAST, got {type(codex_scroll)}"
        )

    root = codex_scroll.get("root")
    nodes = codex_scroll.get("nodes", [])
    args = codex_scroll.get("args", [])

    # ✅ Handle CodexLang function AST (root + args)
    if root and not nodes and args:
        nodes = [{"op": root, "args": args}]

    # ✅ Always propagate root explicitly
    return {
        "ast_type": "photon_ast",
        "origin": "codex",
        "root": root or (nodes[0]["op"] if nodes else None),
        "nodes": nodes,
        "metadata": {
            "source": "codex",
            "glyphs": codex_scroll.get("glyphs", []),
            "intents": codex_scroll.get("intents", []),
        },
    }


def photon_to_codex_ast(photon_ast: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a Photon AST back into Codex scroll format."""
    root = photon_ast.get("root")
    nodes = photon_ast.get("nodes", [])
    glyphs = photon_ast.get("metadata", {}).get("glyphs", [])
    intents = photon_ast.get("metadata", {}).get("intents", [])

    codex_ast = {
        "root": root,
        "nodes": nodes,
        "glyphs": glyphs,
        "intents": intents,
    }

    # ✅ Rebuild args from simple single-node ops
    if not codex_ast.get("args") and nodes and len(nodes) == 1:
        op_node = nodes[0]
        if isinstance(op_node, dict) and "op" in op_node and "args" in op_node:
            codex_ast["root"] = op_node["op"]
            codex_ast["args"] = op_node["args"]

    return codex_ast


# -------------------------------
# Tessaris alignment
# -------------------------------

def align_with_tessaris(photon_ast: Dict[str, Any], tessaris) -> Dict[str, Any]:
    """Run Tessaris alignment on a Photon AST to enrich with symbolic intents."""
    glyphs = photon_ast.get("metadata", {}).get("glyphs", [])
    intents = tessaris.extract_intents_from_glyphs(
        glyphs,
        metadata={"origin": "photon"},
    )
    photon_ast["metadata"]["intents"] = intents
    return photon_ast


# -------------------------------
# Debug harness
# -------------------------------
if __name__ == "__main__":
    # Fake Codex scroll for testing
    class DummyCodexAST:
        def __init__(self):
            self.data = {
                "root": "greater_than",
                "args": ["x", "y"],
                "glyphs": ["greater_than", "x", "y"],
                "intents": [],
            }

    codex_ast = DummyCodexAST()
    photon_ast = codex_to_photon_ast(codex_ast)
    print("Photon AST:", photon_ast)

    roundtrip = photon_to_codex_ast(photon_ast)
    print("Roundtrip Codex AST:", roundtrip)