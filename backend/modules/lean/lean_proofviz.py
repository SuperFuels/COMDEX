# backend/modules/lean/lean_proofviz.py
# ---------------------------------------------------------------------
# Lean / container proof visualization utilities + back-compat shims.
# - CLI helpers for ASCII / Mermaid / PNG
# - Exports ascii_print, write_mermaid, write_png used by lean_inject_cli
# ---------------------------------------------------------------------

from __future__ import annotations

import json
import argparse
from typing import Any, Dict, List, Tuple, Optional, TextIO

# Optional deps for PNG rendering (no graphviz binary required)
try:
    import networkx as nx  # type: ignore
    import matplotlib.pyplot as plt  # type: ignore

    _HAS_PNG = True
except Exception:
    _HAS_PNG = False

from backend.modules.lean.lean_proofviz_utils import mermaid_for_dependencies, png_for_dependencies

def attach_visualizations(container: dict, *, png_path: str | None = None) -> dict:
    """
    Generate and embed visualization artifacts into container['viz'].
    """
    viz = {}

    # Mermaid text
    viz["mermaid"] = mermaid_for_dependencies(container)

    # Optional PNG file
    if png_path:
        ok, msg = png_for_dependencies(container, png_path)
        if ok:
            viz["png_path"] = png_path
        else:
            viz["png_fallback"] = msg

    container["viz"] = viz
    return container

# ----------------------------
# Core container parsing utils
# ----------------------------
def _logic_nodes(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect theorem/logic entries from all known fields.
    Returns a flattened list.
    """
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
    """
    Render a single entry's glyph_tree as a lightweight ASCII block.
    Recursively walks nested args.
    """
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

        args = node.get("args", [])
        for i, a in enumerate(args):
            is_last = i == len(args) - 1
            branch = "└─" if is_last else "├─"
            subprefix = prefix + ("   " if is_last else "│  ")
            if isinstance(a, dict):
                walk(a, subprefix)
            else:
                lines.append(f"{subprefix}{branch} arg: {a}")

    gt = entry.get("glyph_tree") or {}
    walk(gt, "")
    return "\n".join(lines)


def mermaid_for_dependencies(container: Dict[str, Any]) -> str:
    """
    Build a Mermaid graph for the dependency structure:
      nodes: theorem names
      edges: depends_on -> name
    """
    entries = _logic_nodes(container)
    idmap = {e.get("name"): f"n{i}" for i, e in enumerate(entries)}
    lines = ["```mermaid", "graph TD"]
    # nodes
    for e in entries:
        nm = e.get("name", "?")
        logic = str(e.get("logic", "")).replace('"', "'")
        lines.append(f'  {idmap[nm]}["{nm}\\n{logic}"]')
    # edges
    for e in entries:
        nm = e.get("name", "?")
        for d in e.get("depends_on") or []:
            if d in idmap:
                lines.append(f"  {idmap[d]} --> {idmap[nm]}")
    lines.append("```")
    return "\n".join(lines)


def png_for_dependencies(container: Dict[str, Any], out_png: str) -> Tuple[bool, str]:
    """
    Try to draw dependency graph to PNG using networkx + matplotlib.
    Returns (ok, message). If PNG deps missing, returns (False, hint).
    """
    if not _HAS_PNG:
        return (
            False,
            "PNG renderer requires networkx + matplotlib. Install them or use mermaid/ascii.",
        )

    G = nx.DiGraph()
    entries = _logic_nodes(container)
    for e in entries:
        nm = e.get("name", "?")
        G.add_node(nm)
    for e in entries:
        nm = e.get("name", "?")
        for d in e.get("depends_on") or []:
            if any(x.get("name") == d for x in entries):
                G.add_edge(d, nm)

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(G, seed=1)
    nx.draw(G, pos, with_labels=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return True, f"wrote {out_png}"


# ----------------------------
# Back-compat API (used elsewhere)
# ----------------------------
def ascii_print(proof: Any, file: Optional[TextIO] = None) -> str:
    """
    Back-compat wrapper. Accepts:
      - container dict -> prints all entries' ASCII
      - list[entry]    -> prints each entry
      - str            -> returns as-is
    Returns the rendered string (also writes to file if provided).
    """
    out_lines: List[str] = []
    if isinstance(proof, str):
        out_lines.append(proof)
    elif isinstance(proof, dict):
        entries = _logic_nodes(proof)
        if not entries and "glyph_tree" in proof:
            # treat as single entry
            entries = [proof]  # type: ignore[assignment]
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
    """
    Back-compat wrapper. If given a container dict, produce full dependency Mermaid.
    If given a string that already looks like Mermaid, pass it through.
    """
    if isinstance(proof_or_container, str) and proof_or_container.lstrip().startswith(
        ("graph", "flowchart", "```mermaid")
    ):
        mermaid = proof_or_container
    elif isinstance(proof_or_container, dict):
        mermaid = mermaid_for_dependencies(proof_or_container)
    else:
        # Fallback: embed as a Mermaid comment block
        dumped = json.dumps(proof_or_container, default=str)[:8000]
        mermaid = "```mermaid\n%% Unable to infer structure\n%% " + dumped + "\n```"

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(mermaid)
    return mermaid


def write_png(proof_or_container: Any, out_path: str) -> str:
    """
    Back-compat wrapper to write a PNG of dependencies. If PNG deps are missing,
    writes a Mermaid `.mmd` next to the requested path and returns that path instead.
    """
    if isinstance(proof_or_container, dict):
        ok, msg = png_for_dependencies(proof_or_container, out_path)
        if ok:
            return out_path if out_path.endswith(".png") else out_path + ".png"
        # Fallback: write Mermaid text
        alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
        mmd = mermaid_for_dependencies(proof_or_container)
        with open(alt_path, "w", encoding="utf-8") as f:
            f.write(mmd)
        return alt_path

    # Non-container input: store Mermaid fallback
    alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
    with open(alt_path, "w", encoding="utf-8") as f:
        f.write(
            "```mermaid\n%% Non-container input; PNG not generated. See JSON below.\n%% "
            + json.dumps(proof_or_container, default=str)[:8000]
            + "\n```"
        )
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
    ap.add_argument(
        "--ascii", action="store_true", help="print ASCII trees for each theorem"
    )
    ap.add_argument(
        "--mermaid-out", help="write Mermaid dependency graph to file.md"
    )
    ap.add_argument(
        "--png-out", help="write dependency graph PNG (no graphviz needed)"
    )
    args = ap.parse_args()

    c = load_json(args.container)
    entries = _logic_nodes(c)

    if args.ascii:
        for e in entries:
            print("\n" + "=" * 60)
            print(ascii_tree_for_theorem(e))

    if args.mermaid_out:
        save_text(args.mermaid_out, mermaid_for_dependencies(c))
        print(f"[🧭] wrote mermaid → {args.mermaid_out}")

    if args.png_out:
        ok, msg = png_for_dependencies(c, args.png_out)
        print(("[✅] " + msg) if ok else ("[⚠️] " + msg))


if __name__ == "__main__":
    main()


# Public API for imports
__all__ = [
    "ascii_tree_for_theorem",
    "mermaid_for_dependencies",
    "png_for_dependencies",
    "ascii_print",
    "write_mermaid",
    "write_png",
    "load_json",
    "save_text",
]