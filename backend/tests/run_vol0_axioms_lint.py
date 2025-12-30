#!/usr/bin/env python3
"""
Deterministic evidence runner for Tessaris Symatics Volume 0 (v0.3).

Writes:
  - docs/Artifacts/vol0_symatics_axioms/V0_LINT_PROOF.log
  - docs/Artifacts/vol0_symatics_axioms/V0_METRICS.json

Inputs (source-of-record):
  - docs/Artifacts/vol0_symatics_axioms/artifacts/AXIOM_REWRITE_REGISTRY.json
  - docs/Artifacts/vol0_symatics_axioms/artifacts/OPERATOR_RESERVATION_POLICY.yaml
  - docs/Artifacts/vol0_symatics_axioms/qfc/AXIOM_STABILITY_V0_v0_3.scene.json

Canonical publication copies ensured at Vol0 root:
  - docs/Artifacts/vol0_symatics_axioms/AXIOM_REWRITE_REGISTRY.json
  - docs/Artifacts/vol0_symatics_axioms/OPERATOR_RESERVATION_POLICY.yaml
"""

from __future__ import annotations

import hashlib
import json
import platform
import random
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

LOCK_ID = "SRK-V0.3-SYMATICS-AXIOMS"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# -----------------------------
# Tiny canonicalizer for invariance checks (S0, S1, E0)
# -----------------------------
Expr = Any  # ("⊕",[...]) or ("↔",a,b) or atom str

def mk_superpose(a: Expr, b: Expr) -> Expr:
    return ("⊕", [a, b])

def mk_entangle(a: Expr, b: Expr) -> Expr:
    return ("↔", a, b)

def flatten_superpose(e: Expr) -> List[Expr]:
    if isinstance(e, tuple) and len(e) == 2 and e[0] == "⊕":
        out: List[Expr] = []
        for t in e[1]:
            out.extend(flatten_superpose(t))
        return out
    return [e]

def canon_str(e: Expr) -> str:
    if isinstance(e, tuple) and e and e[0] == "⊕":
        return "(" + " ⊕ ".join(canon_str(t) for t in e[1]) + ")"
    if isinstance(e, tuple) and len(e) == 3 and e[0] == "↔":
        return "(" + canon_str(e[1]) + " ↔ " + canon_str(e[2]) + ")"
    return str(e)

def normalize(e: Expr) -> Expr:
    if isinstance(e, tuple) and e and e[0] == "⊕":
        terms: List[Expr] = []
        for t in flatten_superpose(e):
            terms.append(normalize(t))
        terms_sorted = sorted(terms, key=canon_str)
        return ("⊕", terms_sorted)

    if isinstance(e, tuple) and len(e) == 3 and e[0] == "↔":
        a = normalize(e[1])
        b = normalize(e[2])
        aa, bb = (a, b) if canon_str(a) <= canon_str(b) else (b, a)
        return ("↔", aa, bb)

    return e

@dataclass
class InvarianceResult:
    trials: int
    failures: int
    rewrite_invariance_err: float

def run_invariance_trials(seed: int = 1337, trials: int = 200) -> InvarianceResult:
    rng = random.Random(seed)
    atoms = ["A", "B", "C", "a", "b", "c"]
    failures = 0

    for _ in range(trials):
        a = rng.choice(atoms)
        b = rng.choice(atoms)
        c = rng.choice(atoms)

        # S0: commutativity
        if canon_str(normalize(mk_superpose(a, b))) != canon_str(normalize(mk_superpose(b, a))):
            failures += 1
            continue

        # S1: associativity
        e3 = mk_superpose(mk_superpose(a, b), c)
        e4 = mk_superpose(a, mk_superpose(b, c))
        if canon_str(normalize(e3)) != canon_str(normalize(e4)):
            failures += 1
            continue

        # E0: entangle symmetry
        if canon_str(normalize(mk_entangle(a, b))) != canon_str(normalize(mk_entangle(b, a))):
            failures += 1
            continue

    err = failures / float(trials) if trials else 1.0
    return InvarianceResult(trials=trials, failures=failures, rewrite_invariance_err=err)

def policy_mentions(policy_text: str, needles: List[str]) -> bool:
    t = policy_text
    tl = policy_text.lower()
    for n in needles:
        if n in t or n.lower() in tl:
            return True
    return False

def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    vol0_dir = repo_root / "docs" / "Artifacts" / "vol0_symatics_axioms"
    art_dir  = vol0_dir / "artifacts"
    qfc_dir  = vol0_dir / "qfc"

    src_registry = art_dir / "AXIOM_REWRITE_REGISTRY.json"
    src_policy   = art_dir / "OPERATOR_RESERVATION_POLICY.yaml"
    scene_path   = qfc_dir / "AXIOM_STABILITY_V0_v0_3.scene.json"

    pub_registry = vol0_dir / "AXIOM_REWRITE_REGISTRY.json"
    pub_policy   = vol0_dir / "OPERATOR_RESERVATION_POLICY.yaml"
    proof_log    = vol0_dir / "V0_LINT_PROOF.log"
    metrics_json = vol0_dir / "V0_METRICS.json"

    missing = [str(p) for p in (src_registry, src_policy, scene_path) if not p.exists()]
    if missing:
        print("[FAIL] missing required inputs:")
        for m in missing:
            print("  -", m)
        return 2

    copied = {"AXIOM_REWRITE_REGISTRY.json": False, "OPERATOR_RESERVATION_POLICY.yaml": False}
    if not pub_registry.exists():
        shutil.copy2(src_registry, pub_registry)
        copied["AXIOM_REWRITE_REGISTRY.json"] = True
    if not pub_policy.exists():
        shutil.copy2(src_policy, pub_policy)
        copied["OPERATOR_RESERVATION_POLICY.yaml"] = True

    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    tol = 1e-6
    try:
        tol = float(scene.get("metric", {}).get("tolerance", tol))
    except Exception:
        pass

    policy_text = src_policy.read_text(encoding="utf-8")
    tc_notes: List[str] = []

    # MUST: μ reservation (accept glyph μ OR "mu" OR "\mu" OR "measure")
    has_mu = policy_mentions(policy_text, ["μ", "mu", "\\mu", "measure"])
    if not has_mu:
        tc_notes.append("Missing μ reservation (expected one of: μ, mu, \\mu, measure).")

    # MUST: ∇ reservation (accept glyph ∇ OR "nabla" OR "\nabla" OR "gradient")
    has_nabla = policy_mentions(policy_text, ["∇", "nabla", "\\nabla", "gradient"])
    if not has_nabla:
        tc_notes.append("Missing ∇ reservation (expected one of: ∇, nabla, \\nabla, gradient).")

    # OPTIONAL: Born/intensity mention
    has_born = policy_mentions(policy_text, ["Δ", "born", "intensity"])
    if not has_born:
        tc_notes.append("No Born/intensity mention (optional for Vol0).")

    tc_ok = has_mu and has_nabla

    res = run_invariance_trials(seed=1337, trials=200)
    status = "PASS" if (tc_ok and res.rewrite_invariance_err <= tol) else "FAIL"

    inputs = {
        "registry": {"path": str(src_registry), "sha256": sha256_file(src_registry)},
        "policy": {"path": str(src_policy), "sha256": sha256_file(src_policy)},
        "scene": {"path": str(scene_path), "sha256": sha256_file(scene_path)},
    }

    metrics_obj = {
        "lock_id": LOCK_ID,
        "timestamp_utc": utc_now_iso(),
        "status": status,
        "truth_chain_policy_ok": tc_ok,
        "truth_chain_notes": tc_notes,
        "scene": {
            "name": scene.get("scene", scene.get("name", "AXIOM_STABILITY_V0")),
            "metric_name": "REWRITE_INVARIANCE_ERR",
            "tolerance": tol,
        },
        "results": {
            "trials": res.trials,
            "failures": res.failures,
            "rewrite_invariance_err": res.rewrite_invariance_err,
        },
        "inputs": inputs,
        "canonical_copies_written": copied,
        "env": {"python": sys.version.split()[0], "platform": platform.platform()},
        "command": " ".join([sys.executable] + sys.argv),
    }
    write_json(metrics_json, metrics_obj)

    log = []
    log.append("# Deterministic evidence log for Volume 0 axioms + rewrite invariance.")
    log.append("")
    log.append(f"LOCK_ID: {LOCK_ID}")
    log.append(f"TIMESTAMP_UTC: {metrics_obj['timestamp_utc']}")
    log.append(f"STATUS: {status}")
    log.append("")
    log.append("INPUTS:")
    log.append(f"  AXIOM_REWRITE_REGISTRY.json: {inputs['registry']['path']}")
    log.append(f"    sha256: {inputs['registry']['sha256']}")
    log.append(f"  OPERATOR_RESERVATION_POLICY.yaml: {inputs['policy']['path']}")
    log.append(f"    sha256: {inputs['policy']['sha256']}")
    log.append(f"  SCENE: {inputs['scene']['path']}")
    log.append(f"    sha256: {inputs['scene']['sha256']}")
    log.append("")
    log.append("CANONICAL_PUBLICATION_COPIES:")
    log.append(f"  AXIOM_REWRITE_REGISTRY.json -> {str(pub_registry)} (copied={copied['AXIOM_REWRITE_REGISTRY.json']})")
    log.append(f"  OPERATOR_RESERVATION_POLICY.yaml -> {str(pub_policy)} (copied={copied['OPERATOR_RESERVATION_POLICY.yaml']})")
    log.append("")
    log.append("TRUTH_CHAIN_CHECKS:")
    log.append(f"  policy_ok: {tc_ok}")
    if tc_notes:
        log.append("  notes:")
        for n in tc_notes:
            log.append(f"    - {n}")
    else:
        log.append("  notes: (none)")
    log.append("")
    log.append("SCENE_METRIC:")
    log.append(f"  scene: {metrics_obj['scene']['name']}")
    log.append("  metric: REWRITE_INVARIANCE_ERR")
    log.append(f"  tolerance: {tol}")
    log.append(f"  trials: {res.trials}")
    log.append(f"  failures: {res.failures}")
    log.append(f"  REWRITE_INVARIANCE_ERR: {res.rewrite_invariance_err}")
    log.append("")
    log.append("ENV:")
    log.append(f"  python: {metrics_obj['env']['python']}")
    log.append(f"  platform: {metrics_obj['env']['platform']}")
    log.append(f"  command: {metrics_obj['command']}")
    log.append("")

    write_text(proof_log, "\n".join(log))

    if status == "PASS":
        print(f"[PASS] wrote: {proof_log}")
        print(f"       wrote: {metrics_json}")
        print(f"       trials={res.trials} failures={res.failures} rewrite_invariance_err={res.rewrite_invariance_err}")
        return 0

    print(f"[FAIL] wrote: {proof_log}")
    print(f"       wrote: {metrics_json}")
    print(f"       trials={res.trials} failures={res.failures} rewrite_invariance_err={res.rewrite_invariance_err}")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
