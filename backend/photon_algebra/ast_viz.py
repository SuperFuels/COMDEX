"""
Photon AST Visualization
------------------------

Exports normalized expressions to Graphviz DOT or Mermaid syntax
for teaching/debugging purposes.

Usage:
    from backend.photon_algebra.rewriter import normalize
    from backend.photon_algebra.ast_viz import to_dot, to_mermaid

    expr = {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["b", "c"]}]}
    norm = normalize(expr)

    print(to_dot(norm))
    print(to_mermaid(norm))
"""

from typing import Any, Dict, Union
import itertools

PhotonState = Union[str, Dict[str, Any]]


# -------------------------------
# Graphviz Export
# -------------------------------

def to_dot(expr: PhotonState) -> str:
    """Export Photon AST to Graphviz DOT string."""
    lines = ["digraph PhotonAST {", "    node [shape=ellipse, fontname=Helvetica];"]

    counter = itertools.count()

    def add_node(e: PhotonState, parent: str = None) -> str:
        node_id = f"n{next(counter)}"
        if isinstance(e, str):
            label = e
        else:
            label = e.get("op", "?")
        lines.append(f'    {node_id} [label="{label}"];')
        if parent:
            lines.append(f"    {parent} -> {node_id};")

        if isinstance(e, dict):
            for child in e.get("states", []):
                add_node(child, node_id)
            if "state" in e:
                add_node(e["state"], node_id)
        return node_id

    add_node(expr)
    lines.append("}")
    return "\n".join(lines)


# -------------------------------
# Mermaid Export
# -------------------------------

def to_mermaid(expr: PhotonState) -> str:
    """Export Photon AST to Mermaid (flowchart) string."""
    lines = ["flowchart TD"]

    counter = itertools.count()

    def add_node(e: PhotonState, parent: str = None) -> str:
        node_id = f"n{next(counter)}"
        if isinstance(e, str):
            label = e
        else:
            label = e.get("op", "?")
        lines.append(f'    {node_id}["{label}"]')
        if parent:
            lines.append(f"    {parent} --> {node_id}")

        if isinstance(e, dict):
            for child in e.get("states", []):
                add_node(child, node_id)
            if "state" in e:
                add_node(e["state"], node_id)
        return node_id

    add_node(expr)
    return "\n".join(lines)


# -------------------------------
# Debug Harness
# -------------------------------

if __name__ == "__main__":
    from backend.photon_algebra.core import superpose, fuse
    from backend.photon_algebra.rewriter import normalize

    expr = superpose("a", fuse("b", "c"))
    norm = normalize(expr)

    print("DOT:\n", to_dot(norm))
    print("\nMermaid:\n", to_mermaid(norm))