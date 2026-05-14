#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path

LEAN_WORKSPACE = Path("/workspaces/COMDEX/backend/modules/lean/workspace")
BRIDGE_FILE = Path("/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/BridgeTheorem.lean")
OUT_MD = Path("/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/theorem_snapshot.md")

THEOREMS = [
    ("wf_invariant_normStep",
     "∀ e, normalizeWF (normStep e) = normalizeWF e"),
    ("wf_invariant_normalizeFuel",
     "∀ k e, normalizeWF (normalizeFuel k e) = normalizeWF e"),
    ("normalize_bridge",
     "∀ e, normalizeWF (normalize e) = normalizeWF e"),
]

def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr

def detect_axioms(src: str):
    # Very simple, robust enough for this repo style:
    #   axiom NAME ...
    axioms = set(re.findall(r'(?m)^\s*axiom\s+([A-Za-z0-9_]+)\b', src))
    return axioms

def main():
    bridge_src = BRIDGE_FILE.read_text(encoding="utf-8") if BRIDGE_FILE.exists() else ""
    axioms = detect_axioms(bridge_src)

    code, out, err = run(["lake", "build", "PhotonAlgebra.BridgeTheorem"], LEAN_WORKSPACE)
    build_ok = (code == 0)

    lines = []
    lines.append("# PhotonAlgebra Theorem Snapshot")
    lines.append("")
    lines.append("Automated proof snapshot (Lean build).")
    lines.append("")
    lines.append(f"- Module: `PhotonAlgebra.BridgeTheorem`")
    lines.append(f"- Build: {'✅ success' if build_ok else '❌ FAIL'}")
    lines.append(f"- Snapshot source: `{BRIDGE_FILE}`")
    lines.append("")

    lines.append("| Item | Statement | Kind | Build |")
    lines.append("|------|-----------|------|-------|")
    for name, stmt in THEOREMS:
        kind = "AXIOM" if name in axioms else "THEOREM"
        lines.append(f"| `{name}` | `{stmt}` | **{kind}** | {'✅' if build_ok else '❌'} |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if "wf_invariant_normStep" in axioms:
        lines.append("- `wf_invariant_normStep` is currently an **axiom** (assumed, not proved).")
        lines.append("- Therefore `wf_invariant_normalizeFuel` and `normalize_bridge` are theorems **relative to that axiom**.")
    else:
        lines.append("- All items above are proved theorems (no axioms detected for these names).")
    lines.append("")
    lines.append("## Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("cd /workspaces/COMDEX/backend/modules/lean/workspace")
    lines.append("lake build PhotonAlgebra.BridgeTheorem")
    lines.append("```")
    lines.append("")

    if not build_ok:
        lines.append("## Build stderr (first 2000 chars)")
        lines.append("")
        lines.append("```")
        lines.append(err[:2000])
        lines.append("```")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {OUT_MD}")

if __name__ == "__main__":
    main()
