# -*- coding: utf-8 -*-
"""
Tessaris Symatics–Lean Bridge (v1.0)
------------------------------------
Unifies parser, exporter, proof verifier, and CodexLang translator.

Acts as the orchestration layer between:
    - lean_parser / lean_proofverifier / lean_exporter
    - convert_lean_to_codexlang
    - CodexTrace / SRK-8 Proof Kernel

Provides two APIs:
    • LeanBridge class — full interactive API
    • run_lean_proofs() — one-shot batch function used by SRK-8
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

# ───────────────────────────────────────────────────────────────
# Module resolution hierarchy
#   1. backend.modules.lean.* → preferred location
#   2. backend.symatics.*      → fallback (legacy support)
# ───────────────────────────────────────────────────────────────

# --- Parser ---
try:
    from backend.modules.lean.lean_parser import parse_lean_file, parse_proof_dir
    print("[LeanBridge] ✅ Using backend.modules.lean.lean_parser")
except Exception as e:
    print(f"[LeanBridge] ⚠️ modules.lean.lean_parser not found: {e}")
    parse_lean_file = None
    parse_proof_dir = None

# --- Proof Verifier ---
try:
    from backend.modules.lean.lean_proofverifier import verify_proofs
    print("[LeanBridge] ✅ Using backend.modules.lean.lean_proofverifier")
except Exception as e:
    print(f"[LeanBridge] ⚠️ modules.lean.lean_proofverifier not found: {e}")
    verify_proofs = None

# --- CodexLang Exporter ---
try:
    from backend.modules.lean.convert_lean_to_codexlang import (
        convert_lean_expr,
        export_theorems_to_ledger,
    )
    print("[LeanBridge] ✅ Using backend.modules.lean.convert_lean_to_codexlang")
except Exception as e:
    print(f"[LeanBridge] ⚠️ modules.lean.convert_lean_to_codexlang not found: {e}")
    convert_lean_expr = None
    export_theorems_to_ledger = None

# --- Optional Exporter / Normalizer ---
try:
    from backend.modules.lean.lean_exporter import export_axioms_to_lean, normalize_theorem
    print("[LeanBridge] ✅ Using backend.modules.lean.lean_exporter")
except Exception as e:
    print(f"[LeanBridge] ⚠️ modules.lean.lean_exporter not found: {e}")
    export_axioms_to_lean = None
    normalize_theorem = None

# --- Optional Watcher ---
try:
    from backend.modules.lean.lean_watch import watch_lean_session
    print("[LeanBridge] ✅ Using backend.modules.lean.lean_watch")
except Exception as e:
    print(f"[LeanBridge] ⚠️ modules.lean.lean_watch not found: {e}")
    watch_lean_session = None


# ───────────────────────────────────────────────────────────────
# Utility: generate deterministic Lean hash placeholder
# ───────────────────────────────────────────────────────────────
def _fake_lean_hash() -> str:
    """Return a reproducible Lean build hash surrogate (UTC timestamp)."""
    return "lean4-stub-hash:" + datetime.utcnow().strftime("%Y%m%dT%H%M%S")


# ───────────────────────────────────────────────────────────────
# Unified LeanBridge class (interactive + composable)
# ───────────────────────────────────────────────────────────────
class LeanBridge:
    """Unified bridge between Symatics Algebra and Lean formal proof system."""

    def __init__(self):
        self.last_export = None
        self.last_verification = None
        self.last_conversion = None
        self.last_summary = None

    # ---------------------------------------
    # Export axioms
    # ---------------------------------------
    def export_axioms(self, axioms, out_path="exported_axioms.lean"):
        if export_axioms_to_lean is None:
            raise RuntimeError("export_axioms_to_lean not available")
        self.last_export = export_axioms_to_lean(axioms, out_path)
        return self.last_export

    # ---------------------------------------
    # Verify one proof file
    # ---------------------------------------
    def verify(self, lean_file: str):
        if verify_lean_proof is None:
            raise RuntimeError("verify_lean_proof not available")
        self.last_verification = verify_lean_proof(lean_file)
        return self.last_verification

    # ---------------------------------------
    # Convert Lean expression → CodexLang
    # ---------------------------------------
    def convert_to_codex(self, lean_expr: str):
        if convert_lean_expr is None:
            raise RuntimeError("convert_lean_expr not available")
        self.last_conversion = convert_lean_expr(lean_expr)
        return self.last_conversion

    # ---------------------------------------
    # Parse Lean source
    # ---------------------------------------
    def parse(self, lean_file: str):
        if parse_lean_file is None:
            raise RuntimeError("parse_lean_file not available")
        return parse_lean_file(lean_file)

    # ---------------------------------------
    # Watch Lean workspace for updates
    # ---------------------------------------
    def watch(self, path="lean_projects/", callback=None):
        if watch_lean_session is None:
            raise RuntimeError("watch_lean_session not available")
        return watch_lean_session(path, callback=callback)

    # ---------------------------------------
    # Run full verification pass
    # ---------------------------------------
    def run_batch(self, proofs_dir: str, update_codex=True, ledger_path="docs/rfc/theorem_ledger.jsonl"):
        self.last_summary = run_lean_proofs(proofs_dir, update_codex, ledger_path)
        return self.last_summary


# ───────────────────────────────────────────────────────────────
# Batch-style entrypoint for SRK-8
# ───────────────────────────────────────────────────────────────
def run_lean_proofs(
    proofs_dir: str = "backend/symatics/proofs",
    update_codex: bool = True,
    ledger_path: str = "docs/rfc/theorem_ledger.jsonl",
) -> dict:
    """
    Parse Lean-style files, verify invariants with your Python verifier,
    and (optionally) export a JSONL ledger for Codex/SRK consumption.
    Automatically scans alternate locations if the proofs_dir is empty.
    """

    # ───────────────────────────────────────────────
    # Step 0 — Locate Lean proofs directory
    # ───────────────────────────────────────────────
    search_paths = [
        Path(proofs_dir),
        Path("backend/symatics"),             # where your real Lean files live
        Path("backend/symatics/lean"),        # optional subdir variant
        Path("backend/symatics/theorems"),    # optional structured path
    ]

    found_dir = None
    for candidate in search_paths:
        if candidate.exists() and any(f.suffix == ".lean" for f in candidate.iterdir()):
            found_dir = candidate
            break

    if found_dir is None:
        return {
            "ok": False,
            "error": f"No .lean proofs found in search paths: {[str(p) for p in search_paths]}",
            "verified": [],
            "failed": [],
            "count": 0,
            "lean_hash": _fake_lean_hash(),
            "ledger_path": None,
        }

    # ───────────────────────────────────────────────
    # Step 1 — Parse
    # ───────────────────────────────────────────────
    parsed = []
    if parse_proof_dir:
        try:
            parsed = parse_proof_dir(str(found_dir))
        except Exception as e:
            parsed = []
            print(f"[LeanBridge] parse_proof_dir failed: {e}")

    # ───────────────────────────────────────────────
    # Step 2 — Verify
    # ───────────────────────────────────────────────
    verified, failed = [], []
    if verify_proofs:
        try:
            result = verify_proofs(parsed)
            verified = result.get("verified", [])
            failed = result.get("failed", [])
        except Exception as e:
            print(f"[LeanBridge] verify_proofs failed: {e}")
            failed = [t.get("name", "unknown") for t in parsed]
    else:
        failed = [t.get("name", "unknown") for t in parsed]

    # ───────────────────────────────────────────────
    # Step 3 — Export to Codex ledger
    # ───────────────────────────────────────────────
    if update_codex and export_theorems_to_ledger:
        try:
            os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
            export_theorems_to_ledger(verified, ledger_path)
        except Exception as e:
            print(f"[LeanBridge] export_theorems_to_ledger failed: {e}")

    # ───────────────────────────────────────────────
    # Step 4 — Summarize
    # ───────────────────────────────────────────────
    summary = {
        "ok": len(failed) == 0,
        "lean_hash": _fake_lean_hash(),
        "verified": [t["name"] if isinstance(t, dict) else str(t) for t in verified],
        "failed": [t["name"] if isinstance(t, dict) else str(t) for t in failed],
        "count": len(parsed),
        "ledger_path": ledger_path if update_codex else None,
        "source_dir": str(found_dir),
    }

    return summary


# ───────────────────────────────────────────────────────────────
# Stand-alone CLI
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    proofs_dir = sys.argv[1] if len(sys.argv) > 1 else "backend/symatics/proofs"
    summary = run_lean_proofs(proofs_dir)
    print(json.dumps(summary, indent=2))