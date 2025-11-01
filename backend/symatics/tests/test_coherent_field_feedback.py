# -*- coding: utf-8 -*-
"""
Test: SRK-5 Coherent Field Feedback & Diagnostics
Run:  PYTHONPATH=. python backend/symatics/tests/test_coherent_field_feedback.py
"""

import json
import time

from importlib import import_module

def pretty(obj):
    try:
        return json.dumps(obj, indent=2, sort_keys=True)
    except Exception:
        return str(obj)

def find_srk5_extension(kernel):
    """
    Try to locate the SRK-5 extension instance on the kernel.
    Accepts any of:
      - attribute name 'coherent_field' (common binding)
      - extension named containing 'SRK-5'
      - class named 'SRK5CoherentField'
    """
    # direct bind
    if hasattr(kernel, "coherent_field"):
        return getattr(kernel, "coherent_field")

    # scan extensions
    for ext in getattr(kernel, "extensions", []):
        n = getattr(ext, "name", "")
        if "SRK-5" in n or ext.__class__.__name__ == "SRK5CoherentField":
            return ext

    return None

def main():
    # 1) Import kernel
    Kernel = import_module("backend.symatics.core.srk_kernel").SymaticsReasoningKernel

    # 2) Init kernel (loader should include SRK-3 -> SRK-5)
    srk = Kernel()

    # 3) Exercise a small op sequence to produce field activity
    srk.superpose(1.0, 0.7)
    time.sleep(0.05)
    srk.measure(0.5)
    time.sleep(0.05)
    srk.entangle(0.3, 0.9)

    # 4) Manually trigger feedback across all extensions (SRK-3/4/4.1/5)
    for ext in getattr(srk, "extensions", []):
        if hasattr(ext, "feedback"):
            try:
                ext.feedback(srk)
            except Exception as e:
                print(f"[WARN] Feedback error in {getattr(ext, 'name', ext)}: {e}")

    # 5) Pull kernel diagnostics
    diag = srk.diagnostics()
    print("\n=== Kernel Diagnostics (compact) ===")
    wanted_keys = [
        "resonance_feedback",           # SRK-4
        "resonant_entropy_feedback",    # SRK-4.1
        "coherent_field_feedback",      # SRK-5 (expected)
    ]
    for k in wanted_keys:
        print(f"{k}: {pretty(diag.get(k))}")

    # 6) Locate SRK-5 extension and ask it directly for its diagnostics
    srk5 = find_srk5_extension(srk)
    if not srk5:
        print("\n[WARN] SRK-5 extension not found on kernel. "
              "Ensure srk5_coherent_field is in the loader list.")
        return

    try:
        srk5_diag = srk5.diagnostics(srk) if hasattr(srk5, "diagnostics") else {}
    except TypeError:
        # some diag methods don't take args
        srk5_diag = srk5.diagnostics() if hasattr(srk5, "diagnostics") else {}
    except Exception as e:
        print(f"[ERROR] SRK-5 diagnostics failed: {e}")
        srk5_diag = {}

    print("\n=== SRK-5 Coherent Field Diagnostics ===")
    print(pretty(srk5_diag))

    # 7) Friendly checks (don't hard-fail; just report)
    coherent_ok = False
    for key in ("coherent_field_feedback", "coherence_feedback"):
        if isinstance(srk5_diag, dict) and key in srk5_diag:
            coherent_ok = True
            break

    if coherent_ok:
        print("\n[OK] Coherent field feedback present ✅")
    else:
        print("\n[WARN] Coherent field feedback key not found on SRK-5 diagnostics. "
              "Expected 'coherent_field_feedback' (or 'coherence_feedback').")

    # 8) Show any trend arrays if present
    for k in ("coherence_trend", "coherent_trend", "phase_lock_trend"):
        if isinstance(srk5_diag, dict) and k in srk5_diag:
            print(f"\n{k}: {pretty(srk5_diag.get(k))}")

    # 9) Done
    print("\n[Test Completed]\n")


if __name__ == "__main__":
    main()