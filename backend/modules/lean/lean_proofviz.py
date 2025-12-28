# backend/modules/lean/lean_proofviz.py
# ---------------------------------------------------------------------
# Lean / container proof visualization utilities + back-compat shims.
# - CLI helpers for ASCII / Mermaid / PNG / DOT
# - Exports ascii_print, write_mermaid, write_png used by lean_inject_cli
# ---------------------------------------------------------------------

from __future__ import annotations

import subprocess
import shutil
import tempfile
from pathlib import Path
import json
import argparse
from typing import Any, Dict, List, Optional, TextIO, Tuple


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
        val = container.get(fld)
        if isinstance(val, list) and val:
            nodes.extend(val)
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

    def walk(node: Any, prefix: str = ""):
        if not isinstance(node, dict):
            lines.append(f"{prefix}└─ {node}")
            return

        t = node.get("type", "?")
        n = node.get("name", "?")
        logic = node.get("logic", "?")
        op = node.get("operator", "")
        lines.append(f"{prefix}├─ {t}:{n}  {op}  {logic}")

        # ✅ hardened args handling (no KeyError, supports non-list)
        args_list = node.get("args") or []
        if not isinstance(args_list, list):
            args_list = [args_list]

        for i, a in enumerate(args_list):
            is_last = i == len(args_list) - 1
            branch = "└─" if is_last else "├─"
            subprefix = prefix + ("   " if is_last else "│  ")

            if isinstance(a, dict):
                lines.append(f"{subprefix}{branch} arg:")
                walk(a, subprefix + ("   " if is_last else "│  "))
            else:
                lines.append(f"{subprefix}{branch} arg: {a}")

    gt = entry.get("glyph_tree") or {}
    walk(gt, "")
    return "\n".join(lines)


# ----------------------------
# Composite helpers
# ----------------------------
def attach_visualizations(container: dict, *, png_path: str | None = None) -> dict:
    """
    Generate and embed visualization artifacts into container['viz'].
    """
    viz: Dict[str, Any] = {}
    viz["mermaid"] = mermaid_for_dependencies(container)

    if png_path:
        ok, msg = png_for_dependencies(container, png_path)
        if ok:
            viz["png_path"] = png_path
        else:
            viz["png_fallback"] = msg

    container["viz"] = viz
    return container


# ----------------------------
# Back-compat API (used elsewhere)
# ----------------------------
def ascii_print(proof: Any, file: Optional[TextIO] = None) -> str:
    out_lines: List[str] = []
    if isinstance(proof, str):
        out_lines.append(proof)
    elif isinstance(proof, dict):
        entries = _logic_nodes(proof)
        if not entries and "glyph_tree" in proof:
            entries = [proof]  # treat as single entry
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
        mermaid = mermaid_for_dependencies(proof_or_container)
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
        alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
        mmd = mermaid_for_dependencies(proof_or_container)
        with open(alt_path, "w", encoding="utf-8") as f:
            f.write(mmd)
        return alt_path

    alt_path = out_path.rsplit(".", 1)[0] + ".mmd"
    with open(alt_path, "w", encoding="utf-8") as f:
        f.write(
            "```mermaid\n%% Non-container input; PNG not generated. See JSON below.\n%% "
            + json.dumps(proof_or_container, default=str)[:8000]
            + "\n```"
        )
    return alt_path


def dot_for_dependencies(container: Dict[str, Any], out_dot: str) -> Tuple[bool, str]:
    """
    Write a Graphviz DOT file for the dependency graph.
    Returns (ok, message). Produces a standalone .dot file that can be
    rendered with Graphviz tools (`dot -Tpng file.dot -o out.png`).
    """
    try:
        entries = _logic_nodes(container)
        if not entries:
            return False, "no entries to render"

        idmap = {e.get("name", f"?{i}"): f"n{i}" for i, e in enumerate(entries)}
        lines: List[str] = [
            "digraph G {",
            "  rankdir=LR;",
            '  node [shape=box, fontsize=10, style="rounded"];',
        ]

        # Nodes
        for e in entries:
            nm = e.get("name", "?")
            logic = str(e.get("logic", "")).replace('"', "'").replace("\n", " ")
            label = f"{nm}\\n{logic}" if logic else nm
            lines.append(f'  {idmap[nm]} [label="{label}"];')

        # Edges (dep -> theorem)
        for e in entries:
            nm = e.get("name", "?")
            for d in e.get("depends_on") or []:
                if d in idmap:
                    lines.append(f"  {idmap[d]} -> {idmap[nm]};")

        lines.append("}")
        with open(out_dot, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True, f"wrote {out_dot}"
    except Exception as e:
        return False, f"DOT generation failed: {e}"


def mermaid_for_dependencies(container: dict) -> str:
    """
    Build Mermaid dependency graph.
    Prefer backend.modules.lean.lean_proofviz_utils.mermaid_for_dependencies if available.
    """
    try:
        from backend.modules.lean.lean_proofviz_utils import mermaid_for_dependencies as _m
        return _m(container)
    except Exception:
        # Simple fallback: name -> depends_on edges
        entries = _logic_nodes(container)
        lines = ["```mermaid", "graph TD"]
        by_name = {e.get("name") for e in entries if e.get("name")}
        _ = by_name  # keep lint quiet; externals are still shown
        for e in entries:
            src = e.get("name")
            if not src:
                continue
            deps = e.get("depends_on") or []
            for d in deps:
                if not d:
                    continue
                lines.append(f"  {src} --> {d}")
        lines.append("```")
        return "\n".join(lines)


def png_for_dependencies(container: dict, out_path: str) -> Tuple[bool, str]:
    """
    Try to render container dependency graph to PNG using mermaid-cli (mmdc).
    Fallback: save Mermaid .mmd file instead.

    Returns:
        (ok, msg) where ok=True if PNG generated, else fallback with reason/path.
    """
    mermaid = mermaid_for_dependencies(container)
    out_path_p = Path(out_path)
    out_path_p.parent.mkdir(parents=True, exist_ok=True)

    # Check for mermaid-cli (mmdc)
    mmdc = shutil.which("mmdc")
    if mmdc:
        tmp_mmd = tempfile.NamedTemporaryFile(delete=False, suffix=".mmd")
        Path(tmp_mmd.name).write_text(mermaid, encoding="utf-8")
        try:
            subprocess.run(
                [mmdc, "-i", tmp_mmd.name, "-o", str(out_path_p)],
                check=True,
                capture_output=True,
            )
            return True, f"PNG written -> {out_path_p}"
        except subprocess.CalledProcessError as e:
            stderr = ""
            try:
                stderr = (e.stderr or b"").decode(errors="ignore")
            except Exception:
                stderr = str(e)
            return False, f"mmdc failed: {stderr.strip() or str(e)}"
        finally:
            try:
                Path(tmp_mmd.name).unlink(missing_ok=True)
            except Exception:
                pass

    # Fallback: dump Mermaid text to .mmd
    alt_path = out_path_p.with_suffix(".mmd")
    alt_path.write_text(mermaid, encoding="utf-8")
    return False, f"mmdc not found. Mermaid text written -> {alt_path}"


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
    ap.add_argument("--ascii", action="store_true", help="print ASCII trees for each theorem")
    ap.add_argument("--mermaid-out", help="write Mermaid dependency graph to file.md")
    ap.add_argument("--png-out", help="write dependency graph PNG (no graphviz needed)")
    ap.add_argument("--dot-out", help="write dependency graph DOT")
    args = ap.parse_args()

    c = load_json(args.container)

    if args.ascii:
        for e in _logic_nodes(c):
            print("\n" + "=" * 60)
            print(ascii_tree_for_theorem(e))

    if args.mermaid_out:
        save_text(args.mermaid_out, mermaid_for_dependencies(c))
        print(f"[🧭] wrote mermaid -> {args.mermaid_out}")

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
    "ascii_print",
    "write_mermaid",
    "write_png",
    "attach_visualizations",
    "load_json",
    "save_text",
    "mermaid_for_dependencies",
    "png_for_dependencies",
    "dot_for_dependencies",
]