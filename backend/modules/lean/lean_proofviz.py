import json
import argparse
from typing import Any, Dict, List, Tuple

# Optional deps for PNG rendering (no graphviz binary required)
try:
    import networkx as nx  # type: ignore
    import matplotlib.pyplot as plt  # type: ignore
    _HAS_PNG = True
except Exception:
    _HAS_PNG = False

def _logic_nodes(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    for fld in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
        if fld in container:
            return container[fld]
    return []

def ascii_tree_for_theorem(entry: Dict[str, Any]) -> str:
    """Render glyph_tree as ASCII."""
    name = entry.get("name","?")
    gt = entry.get("glyph_tree") or {}
    lines = [f"{name} [{entry.get('symbol','⟦ ? ⟧')}] : {entry.get('logic','?')}"]
    def walk(node: Dict[str, Any], prefix: str = ""):
        t = node.get("type","?")
        n = node.get("name","?")
        logic = node.get("logic","?")
        op = node.get("operator","")
        lines.append(f"{prefix}├─ {t}:{n}  {op}  {logic}")
        args = node.get("args",[])
        for i, a in enumerate(args):
            is_last = (i == len(args)-1)
            pre2 = prefix + ("│  " if not is_last else "   ")
            if isinstance(a, dict):
                # arg node
                k = a.get("type","node")
                v = a.get("value", a.get("logic",""))
                lines.append(f"{prefix}│  ├─ arg[{k}]: {v}")
            else:
                lines.append(f"{prefix}│  ├─ arg: {a}")
        # no deeper child nesting in current schema; glyph_tree is one level with args payloads
    walk(gt, "")
    return "\n".join(lines)

def mermaid_for_dependencies(container: Dict[str, Any]) -> str:
    entries = _logic_nodes(container)
    idmap = {e.get("name"): f"n{i}" for i,e in enumerate(entries)}
    lines = ["```mermaid","graph TD"]
    # nodes
    for e in entries:
        nm = e.get("name","?")
        logic = e.get("logic","").replace('"',"'")
        lines.append(f'  {idmap[nm]}["{nm}\\n{logic}"]')
    # edges
    for e in entries:
        nm = e.get("name","?")
        deps = e.get("depends_on") or []
        for d in deps:
            if d in idmap:
                lines.append(f"  {idmap[d]} --> {idmap[nm]}")
    lines.append("```")
    return "\n".join(lines)

def png_for_dependencies(container: Dict[str, Any], out_png: str) -> Tuple[bool,str]:
    if not _HAS_PNG:
        return False, "PNG renderer requires networkx + matplotlib. Install them or use mermaid/ascii."
    G = nx.DiGraph()
    entries = _logic_nodes(container)
    for e in entries:
        nm = e.get("name","?")
        G.add_node(nm)
    for e in entries:
        nm = e.get("name","?")
        for d in e.get("depends_on") or []:
            if any(x.get("name")==d for x in entries):
                G.add_edge(d, nm)
    plt.figure(figsize=(8,6))
    pos = nx.spring_layout(G, seed=1)
    nx.draw(G, pos, with_labels=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return True, f"wrote {out_png}"

def load_json(p: str) -> Dict[str, Any]:
    with open(p,"r",encoding="utf-8") as f:
        return json.load(f)

def save_text(p: str, s: str) -> None:
    with open(p,"w",encoding="utf-8") as f:
        f.write(s)

def main():
    ap = argparse.ArgumentParser(description="Lean proof viz tools")
    ap.add_argument("container", help="path to container json")
    ap.add_argument("--ascii", action="store_true", help="print ASCII trees for each theorem")
    ap.add_argument("--mermaid-out", help="write Mermaid dependency graph to file.md")
    ap.add_argument("--png-out", help="write dependency graph PNG (no graphviz needed)")
    args = ap.parse_args()

    c = load_json(args.container)
    entries = _logic_nodes(c)

    if args.ascii:
        for e in entries:
            print("\n" + "="*60)
            print(ascii_tree_for_theorem(e))

    if args.mermaid_out:
        save_text(args.mermaid_out, mermaid_for_dependencies(c))
        print(f"[🧭] wrote mermaid → {args.mermaid_out}")

    if args.png_out:
        ok, msg = png_for_dependencies(c, args.png_out)
        print(("[✅] "+msg) if ok else ("[⚠️] "+msg))

if __name__ == "__main__":
    main()