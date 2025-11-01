# -*- coding: utf-8 -*-
"""
Tessaris Lean Bridge Integration Test
-------------------------------------
Validates the orchestration of:
  * parsing Lean proof files
  * verifying proofs
  * exporting Codex theorem ledger
  * generating runtime summary for SRK-8
"""

import json
import os
from pathlib import Path
from pprint import pprint

# Import the bridge function directly
from backend.symatics.lean_bridge import run_lean_proofs, LeanBridge


def setup_fake_proofs(tmpdir: str):
    """
    Create a small dummy proof directory with minimal .lean files
    that the bridge can parse.
    """
    os.makedirs(tmpdir, exist_ok=True)

    # --- Fake proof file 1 ---
    lean1 = Path(tmpdir) / "energy_entropy_duality.lean"
    lean1.write_text(
        """
        theorem energy_entropy_duality : ∀ λ ψ, ΔE λ ψ = ΔS λ ψ := by
          simp
        """
    )

    # --- Fake proof file 2 ---
    lean2 = Path(tmpdir) / "lambda_psi_stable.lean"
    lean2.write_text(
        """
        theorem lambda_psi_stable : ∀ λ ψ, ‖λ ⊗ ψ‖ = ‖λ‖ * ‖ψ‖ := by
          simp
        """
    )

    return tmpdir


def test_run_lean_proofs():
    tmpdir = "tests/tmp_proofs"
    setup_fake_proofs(tmpdir)

    print("=== Running run_lean_proofs() ===")
    summary = run_lean_proofs(tmpdir, update_codex=True, ledger_path="docs/rfc/theorem_ledger.jsonl")

    print("\n--- Summary ---")
    pprint(summary)

    # Basic structure validation
    assert isinstance(summary, dict)
    assert "lean_hash" in summary
    assert "verified" in summary
    assert "failed" in summary
    assert "ok" in summary

    # Ledger should exist
    if summary.get("ledger_path"):
        assert os.path.exists(summary["ledger_path"])
        print(f"Ledger created: {summary['ledger_path']}")

    print("✅ run_lean_proofs() executed successfully.")


def test_bridge_class():
    tmpdir = "tests/tmp_proofs"
    setup_fake_proofs(tmpdir)

    bridge = LeanBridge()
    print("\n=== Running LeanBridge.run_batch() ===")
    summary = bridge.run_batch(tmpdir)

    print("\n--- LeanBridge Summary ---")
    pprint(summary)

    assert "verified" in summary
    assert "lean_hash" in summary
    print("✅ LeanBridge class operational.")


if __name__ == "__main__":
    # ensure target directories exist
    os.makedirs("docs/rfc", exist_ok=True)
    os.makedirs("tests/tmp_proofs", exist_ok=True)

    print("=== Tessaris Lean Bridge Test Suite ===")
    test_run_lean_proofs()
    test_bridge_class()
    print("\n🎯 All tests completed successfully.")