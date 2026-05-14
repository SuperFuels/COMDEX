#!/usr/bin/env python3
import re
from pathlib import Path
from datetime import datetime

LEAN_FILE = Path("/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/BridgeTheorem.lean")
OUT_FILE  = Path("/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/theorem_snapshot.md")

ITEMS = [
    ("wf_invariant_normStep", "∀ e, normalizeWF (normStep e) = normalizeWF e"),
    ("wf_invariant_normalizeFuel", "∀ k e, normalizeWF (normalizeFuel k e) = normalizeWF e"),
    ("normalize_bridge", "∀ e, normalizeWF (normalize e) = normalizeWF e"),
]

TOPLEVEL_RE = re.compile(r"^(axiom|theorem|lemma|def|abbrev|instance|structure|inductive|opaque|end)\b", re.M)

def find_block(text: str, name: str):
    # Find the toplevel declaration line for name, and slice until next toplevel decl.
    m = re.search(rf"^(axiom|theorem|lemma)\s+{re.escape(name)}\b.*$", text, re.M)
    if not m:
        return None, None, None
    kind = m.group(1)
    start = m.start()
    # Find next toplevel decl after this match
    m2 = TOPLEVEL_RE.search(text, m.end())
    end = m2.start() if m2 else len(text)
    block = text[start:end]
    return kind, block, m.group(0).strip()

def classify(kind: str, block: str):
    if kind == "axiom":
        return "AXIOM"
    # theorem/lemma: check for sorry/admit
    if re.search(r"\bsorry\b", block):
        return "ADMITTED"
    return "THEOREM"

def main():
    if not LEAN_FILE.exists():
        raise SystemExit(f"missing: {LEAN_FILE}")

    text = LEAN_FILE.read_text(encoding="utf-8")

    rows = []
    for name, stmt in ITEMS:
        kind, block, decl_line = find_block(text, name)
        if kind is None:
            rows.append((name, stmt, "MISSING", "❌"))
            continue
        k = classify(kind, block)
        rows.append((name, stmt, f"**{k}**", "✅"))

    now = datetime.now().isoformat(timespec="seconds")
    md = []
    md.append("# PhotonAlgebra Theorem Snapshot\n")
    md.append("Automated proof snapshot (Lean build).\n")
    md.append(f"- Module: `PhotonAlgebra.BridgeTheorem`\n")
    md.append(f"- Snapshot source: `{LEAN_FILE}`\n")
    md.append(f"- Generated: `{now}`\n\n")
    md.append("| Item | Statement | Kind | Build |\n")
    md.append("|------|-----------|------|-------|\n")
    for name, stmt, kind, ok in rows:
        md.append(f"| `{name}` | `{stmt}` | {kind} | {ok} |\n")

    md.append("\n## Interpretation\n\n")
    md.append("- **AXIOM** = assumed (not proved).\n")
    md.append("- **ADMITTED** = theorem uses `sorry` (typechecks, but not proved).\n")
    md.append("- **THEOREM** = no `sorry` detected in its block.\n\n")
    md.append("## Reproduce\n\n")
    md.append("```bash\n")
    md.append("cd /workspaces/COMDEX/backend/modules/lean/workspace\n")
    md.append("lake build PhotonAlgebra.BridgeTheorem\n")
    md.append("python3 /workspaces/COMDEX/backend/photon_algebra/scripts/generate_theorem_snapshot.py\n")
    md.append("```\n")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("".join(md), encoding="utf-8")
    print(f"Wrote: {OUT_FILE}")

if __name__ == "__main__":
    main()