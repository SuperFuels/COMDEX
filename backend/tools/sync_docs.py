# backend/tools/sync_docs.py
# -*- coding: utf-8 -*-
"""
Unified Doc/YAML Sync Entrypoint
- Step 1: Merge Photon ops into docs/CodexLang_Instruction/instruction_registry.yaml
- Step 2: Run backend/photon_algebra/docgen.py
- Step 3: Rebuild docs/CodexLang_Instruction/instruction_reference.md
"""

import os
import sys
import subprocess
from pathlib import Path

# ── Resolve repo ROOT robustly no matter where this script lives ─────────────
HERE = Path(__file__).resolve()
CANDIDATES = list(HERE.parents)
ROOT = None
for p in CANDIDATES:
    if (p / "backend").is_dir() and (p / "docs").is_dir():
        ROOT = p
        break
if ROOT is None:
    print("❌ Could not locate repo root (expected 'backend' and 'docs' dirs).")
    sys.exit(1)

# Ensure ROOT on sys.path for intra-repo imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docs.CodexLang_Instruction.yamlsync import sync_yaml
from docs.CodexLang_Instruction.instruction_reference_builder import build_reference

OUT_INSTR_MD = ROOT / "docs" / "CodexLang_Instruction" / "instruction_reference.md"
DOCGEN_SCRIPT = ROOT / "backend" / "photon_algebra" / "docgen.py"

def run_docgen():
    """Run backend/photon_algebra/docgen.py as a separate process."""
    env = os.environ.copy()
    # prepend repo root to PYTHONPATH
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH','')}"
    cmd = [sys.executable, str(DOCGEN_SCRIPT)]
    subprocess.check_call(cmd, cwd=str(ROOT), env=env)

def main():
    print("🔧 Step 1/3: Merging Photon ops into instruction_registry.yaml …")
    sync_yaml()
    print("✅ YAML sync complete.\n")

    print("🔧 Step 2/3: Generating Photon docs via backend/photon_algebra/docgen.py …")
    try:
        run_docgen()
        print("✅ Photon docgen complete.\n")
    except subprocess.CalledProcessError as e:
        print("❌ docgen.py failed:", e)
        sys.exit(e.returncode)

    print("🔧 Step 3/3: Rebuilding CodexLang instruction reference …")
    md = build_reference()
    OUT_INSTR_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_INSTR_MD.write_text(md, encoding="utf-8")
    print(f"✅ Instruction reference regenerated at {OUT_INSTR_MD}\n")

    print("🎉 All docs synced.")

if __name__ == "__main__":
    main()