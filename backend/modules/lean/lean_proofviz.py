# backend/modules/lean/lean_proofviz.py
# ---------------------------------------------------------------------
# Lean / container proof visualization utilities + back-compat shims.
# - CLI helpers for ASCII / Mermaid / PNG / DOT
# - Exports ascii_print, write_mermaid, write_png used by lean_inject_cli
# - Delegates all graph logic to lean_proofviz_utils
# ---------------------------------------------------------------------

from __future__ import annotations

import json
import argparse
from typing import Any, Dict, List, Optional, TextIO

# Canonical visualization helpers (single source of truth)
from backend.modules.lean.lean_proofviz_utils import (
    mermaid_for_dependencies,
    png_for_dependencies,
    dot_for_dependencies,
)

# ----------------------------
# Core container parsing utils
# ----------------------------
def _logic_nodes(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect theorem/logic entries from all known fields."""
    nodes: List[Dict[str, Any]] = []
    for fld in (
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ):
        if fld in container and container[fld]:
            nodes.extend(container[fld])
    return nodes

# ----------------------------
# Renderers
# ----------------------------
def ascii_tree_for_theorem(entry: Dict[str, Any]) -> str:
    """Render a single entry's glyph_tree as ASCII."""
    name = entry.get("name", "?")
    lines = [f"{name} [{entry.get('symbol','⟦ ? ⟧')}] : {entry.get('logic','?')}"]

    def walk(node: Dict[str, Any], prefix: str = ""):
        if not isinstance(node, dict):
            lines.append(f"{prefix}└─ {node}")
            return
        t = node.get("type", "?")
        n = node.get("name", "?")
        logic = node.get("logic", "?")
        op = node.get("operator", "")
        lines.append(f"{prefix}├─ {t}:{n}  {op}  {logic}")
        for i, a in enumerate(node.get("args", [])):
            is_last = i == len(node["args"]) - 1
            branch = "└─" if is_last else "├─"
            subprefix = prefix + ("   " if is_last else "│  ")
            if isinstance(a, dict):
                walk(a, subprefix)
            else:
                lines.append(f"{subprefix}{branch} arg: {a}")

    walk(entry.get("glyph_tree") or {}, "")
    return "\n".join(lines)

# ----------------------------
# Composite helpers
# ----------------------------
def mermaidify(container: Dict[str, Any]) -> str:
    """
    Return a Mermaid diagram string for the container.
    Currently wraps mermaid_for_dependencies, but extendable to AST graphs.
    """
    return mermaid_for_dependencies(container)


def attach_visualizations(container: dict, *, png_path: str | None = None) -> dict:
    """Generate and embed visualization artifacts into container['viz']."""
    viz = {"mermaid": mermaidify(container)}
    if png_path:
        ok, msg = png_for_dependencies(container, png_path)
        viz["png_path" if ok else "png_fallback"] = png_path if ok else msg
    container["viz"] = viz
    return container

# ----------------------------
# Back-compat API
# ----------------------------
def ascii_print(proof: Any, file: Optional[TextIO] = None) -> str:
    out_lines: List[str] = []
    if isinstance(proof, str):
        out_lines.append(proof)
    elif isinstance(proof, dict):
        entries = _logic_nodes(proof)
        if not entries and "glyph_tree" in proof:
            entries = [proof]
        for e in entries:
            out_lines.append("\n" + "=" * 60)
            out_lines.append(ascii_tree_for_theorem(e))
    elif isinstance(proof, list) and all(isinstance(x, dict) for x in proof):
        for e in proof:
            out_lines.append("\n" + "=" * 60)
            out_lines.append(ascii_tree_for_theorem(e))
    else:
        out_lines.append(json.dumps(proof, default=str, indent=2)[:8000])

    rendered = "\n".join(out_lines)
    if file:
        file.write(rendered + "\n")
    return rendered


def write_mermaid(proof_or_container: Any, out_path: Optional[str] = None) -> str:
    if isinstance(proof_or_container, str) and proof_or_container.lstrip().startswith(
        ("graph", "flowchart", "```mermaid")
    ):
        mermaid = proof_or_container
    elif isinstance(proof_or_container, dict):
        mermaid = mermaidify(proof_or_container)
    else:
        dumped = json.dumps(proof_or_container, default=str)[:8000]
        mermaid = "```mermaid\n%% Unable to infer structure\n%% " + dumped + "\n```"
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(mermaid)
    return mermaid


def write_png(proof_or_container: Any, out_path: str) -> str:
    if isinstance(proof_or_container, dict):
        ok, msg = png_for_dependencies(proof_or_container, out_path)
        if ok:
            return out_path if out_path.endswith(".png") else out_path + ".png"
        # fallback to .mmd
        alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
        with open(alt_path, "w", encoding="utf-8") as f:
            f.write(mermaidify(proof_or_container))
        return alt_path

    alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
    with open(alt_path, "w", encoding="utf-8") as f:
        f.write("```mermaid\n%% Non-container input\n```")
    return alt_path

# ----------------------------
# Basic file IO helpers
# ----------------------------
def load_json(p: str) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def save_text(p: str, s: str) -> None:
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

# ----------------------------
# CLI
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="Lean proof viz tools")
    ap.add_argument("container", help="path to container json")
    ap.add_argument("--ascii", action="store_true", help="print ASCII trees")
    ap.add_argument("--mermaid-out", help="write Mermaid dependency graph to file.md")
    ap.add_argument("--png-out", help="write dependency graph PNG")
    ap.add_argument("--dot-out", help="write dependency graph DOT")
    args = ap.parse_args()

    c = load_json(args.container)
    entries = _logic_nodes(c)

    if args.ascii:
        for e in entries:
            print("\n" + "=" * 60)
            print(ascii_tree_for_theorem(e))

    if args.mermaid_out:
        save_text(args.mermaid_out, mermaidify(c))
        print(f"[🧭] wrote mermaid → {args.mermaid_out}")

    if args.dot_out:
        ok, msg = dot_for_dependencies(c, args.dot_out)
        print(("[✅] " + msg) if ok else ("[⚠️] " + msg))

    if args.png_out:
        ok, msg = png_for_dependencies(c, args.png_out)
        print(("[✅] " + msg) if ok else ("[⚠️] " + msg))

if __name__ == "__main__":
    main()

# Public API
__all__ = [
    "ascii_tree_for_theorem",
    "mermaidify",
    "mermaid_for_dependencies",
    "png_for_dependencies",
    "dot_for_dependencies",
    "ascii_print",
    "write_mermaid",
    "write_png",
    "attach_visualizations",
    "load_json",
    "save_text",
]