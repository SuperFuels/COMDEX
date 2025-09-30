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

# ── Resolve repo ROOT robustly ────────────────────────────────────────────────
HERE = Path(__file__).resolve()
ROOT = None
for p in HERE.parents:
    if (p / "backend").is_dir() and (p / "docs").is_dir():
        ROOT = p
        break
if ROOT is None:
    print("❌ Could not locate repo root (expected 'backend' and 'docs' dirs).")
    sys.exit(1)

# Ensure ROOT on sys.path for intra-repo imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Paths
DOCS_DIR = ROOT / "docs" / "CodexLang_Instruction"
OUT_INSTR_MD = DOCS_DIR / "instruction_reference.md"
DOCGEN_SCRIPT = ROOT / "backend" / "photon_algebra" / "docgen.py"
BUILDER_PATH = DOCS_DIR / "instruction_reference_builder.py"

# Imports (after sys.path set)
from docs.CodexLang_Instruction.yamlsync import sync_yaml

def run_docgen():
    """Run backend/photon_algebra/docgen.py as a separate process."""
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH','')}"
    subprocess.check_call([sys.executable, str(DOCGEN_SCRIPT)], cwd=str(ROOT), env=env)

def run_builder():
    """
    Execute the YAML-first builder.
    Supports both variants:
      - build_reference() returns str (we write it)
      - build_reference() returns None (it writes the file itself)
    """
    # Import at runtime to reflect latest file edits
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "instruction_reference_builder", str(BUILDER_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore

    if not hasattr(mod, "build_reference"):
        raise RuntimeError("instruction_reference_builder.py missing build_reference()")

    md = mod.build_reference()
    if isinstance(md, str):
        OUT_INSTR_MD.parent.mkdir(parents=True, exist_ok=True)
        OUT_INSTR_MD.write_text(md, encoding="utf-8")
        print(f"✅ Instruction reference regenerated at {OUT_INSTR_MD}")
    # If md is None (or not a str), assume the builder wrote the file and printed already.

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
    try:
        run_builder()
        print()  # spacing
    except Exception as e:
        print("❌ instruction_reference_builder failed:", e)
        sys.exit(1)

    print("🎉 All docs synced.")

if __name__ == "__main__":
    main()