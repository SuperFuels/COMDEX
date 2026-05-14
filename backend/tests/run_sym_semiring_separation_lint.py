#!/usr/bin/env python3
"""
SEMIRING SEPARATION LINT (sym_compare_v1) — STRONG N2 (distributivity witness)

Goal:
  Lock a minimal distributivity failure for a semiring-style candidate, using:
    add := canon(Interf_phi(A,B))  where Interf_phi(A,B) = A + exp(i*phi) B
    mul := Hadamard (componentwise complex multiplication)

Why canon():
  If add is purely linear and mul is Hadamard, distributivity holds identically.
  Symatics-style canonicalization/normalization is a plausible primitive that makes add nonlinear,
  and then distributivity fails for non-boundary phases.

We lock:
  LHS = mul(add(A,B), C)
  RHS = add(mul(A,C), mul(B,C))
  distance_distrib = ||LHS - RHS||_2  > threshold

Artifacts (MUST emit):
  docs/Artifacts/sym_compare_v1/SEMIRING_COUNTEREXAMPLE.json
  docs/Artifacts/sym_compare_v1/SEMIRING_LINT_PROOF.log
  docs/Artifacts/sym_compare_v1/SEMIRING_METRICS.json

Seed:
  SEED=0 (recorded everywhere)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
from typing import Any, Dict

import numpy as np
import yaml


LOCK_ID = "SEMIRING_SEPARATION_LINT_v1"

ART_ROOT = pathlib.Path("docs/Artifacts/sym_compare_v1")
THRESH_YAML = ART_ROOT / "SYM_COMPARE_ACCEPTANCE_THRESHOLDS.yaml"

OUT_COUNTEREX = ART_ROOT / "SEMIRING_COUNTEREXAMPLE.json"
OUT_METRICS = ART_ROOT / "SEMIRING_METRICS.json"
OUT_LOG = ART_ROOT / "SEMIRING_LINT_PROOF.log"


def _utcnow() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: pathlib.Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _ensure_dir(p: pathlib.Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _load_thresholds() -> Dict[str, Any]:
    data = yaml.safe_load(THRESH_YAML.read_text(encoding="utf-8"))
    assert int(data["version"]) == 1
    return data


def _seed_from_env_or_yaml(th: Dict[str, Any]) -> int:
    if "SEED" in os.environ:
        return int(os.environ["SEED"])
    return int(th["seed"])


def _vec_from_parts(re: list[float], im: list[float]) -> np.ndarray:
    return np.array(re, dtype=float) + 1j * np.array(im, dtype=float)


# --- Symatics-side primitives (minimal, deterministic, auditable) ---

def sym_interf(phi: float, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # Must match the placeholder used by run_sym_effectalg_separation_lint.py
    return A + np.exp(1j * phi) * B


def canon(v: np.ndarray) -> np.ndarray:
    # Minimal canonicalization: L2 normalization (nonlinear; breaks distributivity).
    n = float(np.linalg.norm(v))
    if n == 0.0:
        return v.copy()
    return v / n


def sym_add(phi: float, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # add := canon(Interf_phi(A,B))
    return canon(sym_interf(phi, A, B))


def sym_mul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # mul := Hadamard (componentwise complex multiply)
    return A * B


def _distance(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.linalg.norm(x - y))


def main() -> int:
    _ensure_dir(OUT_COUNTEREX)
    _ensure_dir(OUT_METRICS)
    _ensure_dir(OUT_LOG)

    th = _load_thresholds()
    seed = _seed_from_env_or_yaml(th)

    # We fix the semiring-add phase to canonical phi1 (= pi/3)
    phi = float(th["phi"]["phi1"])

    # Thresholds (backward-compatible keying)
    sem = th["thresholds"]["semiring"]
    dist_min = float(sem.get("distrib_distance_min", sem.get("distance_min", 1.0e-6)))

    started = _utcnow()

    # Deterministic witness A,B (reuse effectalg A,B for tight narrative)
    reA = [0.21, -0.13, 0.08, 0.11]
    imA = [0.05, 0.17, -0.02, 0.09]
    reB = [-0.07, 0.19, -0.05, 0.03]
    imB = [0.04, -0.06, 0.12, -0.15]

    # Deterministic C (fixed; small nonzero phasors)
    reC = [0.07, -0.02, 0.05, -0.08]
    imC = [-0.03, 0.11, 0.09, 0.04]

    A = _vec_from_parts(reA, imA)
    B = _vec_from_parts(reB, imB)
    C = _vec_from_parts(reC, imC)

    # Distributivity witness:
    # LHS = (A ⊕ B) ⊗ C
    # RHS = (A ⊗ C) ⊕ (B ⊗ C)
    addAB = sym_add(phi, A, B)
    lhs = sym_mul(addAB, C)
    rhs = sym_add(phi, sym_mul(A, C), sym_mul(B, C))
    dist_distrib = _distance(lhs, rhs)

    status = "PASS"
    failures: list[str] = []
    if not (dist_distrib > dist_min):
        status = "FAIL"
        failures.append(f"distance_distrib <= threshold ({dist_distrib} <= {dist_min})")

    finished = _utcnow()

    counterex: Dict[str, Any] = {
        "lock_id": LOCK_ID,
        "status": status,
        "failures": failures,
        "seed": seed,
        "started_utc": started,
        "finished_utc": finished,
        "phi": {"phi": phi},
        "A": {"re": reA, "im": imA},
        "B": {"re": reB, "im": imB},
        "C": {"re": reC, "im": imC},
        "ops": {
            "add": "canon(Interf_phi(X,Y)) where Interf_phi(X,Y)=X+exp(i*phi)Y",
            "mul": "Hadamard(X,Y) (componentwise complex multiplication)",
            "canon": "L2-normalize (v / ||v||) with 0-guard",
        },
        "witness": {
            "lhs": {"re": [float(x.real) for x in lhs], "im": [float(x.imag) for x in lhs]},
            "rhs": {"re": [float(x.real) for x in rhs], "im": [float(x.imag) for x in rhs]},
            "distance_distrib": dist_distrib,
        },
        "thresholds": {"distrib_distance_min": dist_min},
    }
    OUT_COUNTEREX.write_text(json.dumps(counterex, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    runner_sha = _sha256_file(pathlib.Path(__file__))
    counter_sha = _sha256_file(OUT_COUNTEREX)

    metrics: Dict[str, Any] = {
        "digests": {"runner_sha256": runner_sha, "counterexample_sha256": counter_sha},
        "status": status,
        "failures": failures,
        "seed": seed,
        "started_utc": started,
        "finished_utc": finished,
        "phi": {"phi": phi},
        "measured": {"distance_distrib": dist_distrib},
        "thresholds": {"distrib_distance_min": dist_min},
        "runner": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "relpath": "backend/tests/run_sym_semiring_separation_lint.py",
        },
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("SEMIRING SEPARATION LINT PROOF (sym_compare_v1) — STRONG N2 (distributivity witness)")
    lines.append(f"started_utc:  {started}")
    lines.append(f"finished_utc: {finished}")
    lines.append(f"status:       {status}")
    lines.append(f"seed:         {seed}")
    lines.append("")
    lines.append("CANONICAL PHASE (for add):")
    lines.append(f"  phi = {phi}  (phi1 = pi/3)")
    lines.append("")
    lines.append("THRESHOLDS:")
    lines.append(f"  distance_distrib(LHS,RHS) >  {dist_min:.1e}")
    lines.append("")
    lines.append("MEASURED:")
    lines.append(f"  distance_distrib: {dist_distrib:.6e}")
    lines.append("")
    lines.append("ARTIFACTS:")
    lines.append(f"  counterexample: {OUT_COUNTEREX.as_posix()}")
    lines.append(f"  metrics:        {OUT_METRICS.as_posix()}")
    lines.append(f"  log:            {OUT_LOG.as_posix()}")
    lines.append("")
    lines.append(f"counterexample_sha256: {counter_sha}")
    lines.append(f"runner_sha256:         {runner_sha}")
    lines.append("")
    lines.append(f"Lock ID: {LOCK_ID}")
    lines.append(f"Status: {status}")
    lines.append("Maintainer: Tessaris AI")
    lines.append("Author: Kevin Robinson.")
    OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())