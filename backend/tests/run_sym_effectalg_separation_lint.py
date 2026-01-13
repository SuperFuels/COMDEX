#!/usr/bin/env python3
"""
(C) Effect-algebra / quantum-logic representation failure (phase irreducibility)

Goal:
  Support theorem: no homomorphism preserving φ-indexed interference into an
  effect-algebra / OML-style φ-free structure, by locking a minimal failed attempt.

MUST emit:
  docs/Artifacts/sym_compare_v1/EFFECTALG_COUNTEREXAMPLE.json
  docs/Artifacts/sym_compare_v1/EFFECTALG_LINT_PROOF.log
  docs/Artifacts/sym_compare_v1/EFFECTALG_METRICS.json

Determinism:
  SEED=0 required; recorded in log + metrics.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np


# -------------------------
# Paths / constants
# -------------------------

ART_ROOT = pathlib.Path("docs/Artifacts/sym_compare_v1")
COUNTEREX = ART_ROOT / "EFFECTALG_COUNTEREXAMPLE.json"
LOG_PATH = ART_ROOT / "EFFECTALG_LINT_PROOF.log"
METRICS = ART_ROOT / "EFFECTALG_METRICS.json"
THRESH_YAML = ART_ROOT / "SYM_COMPARE_ACCEPTANCE_THRESHOLDS.yaml"
LOCK_SURFACE = ART_ROOT / "SYM_COMPARE_LOCK_SURFACE.json"

LOCK_ID = "EFFECTALG_SEPARATION_LINT_v1"
PY_REL = "backend/tests/run_sym_effectalg_separation_lint.py"


# -------------------------
# Utilities
# -------------------------

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def now_utc_iso() -> str:
    # Keep simple + stable; caller may swap to datetime.now(timezone.utc).isoformat()
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def load_thresholds_yaml(path: pathlib.Path) -> Dict[str, Any]:
    # Avoid non-stdlib deps in test runners; parse the tiny YAML we control.
    # This parser supports the exact shape used above.
    data: Dict[str, Any] = {}
    stack: list[Tuple[int, Dict[str, Any]]] = [(0, data)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, val = [x.strip() for x in line.strip().split(":", 1)]
        while stack and indent < stack[-1][0]:
            stack.pop()
        cur = stack[-1][1]
        if val == "":
            cur[key] = {}
            stack.append((indent + 2, cur[key]))
        else:
            # number / string
            v: Any
            if val.lower() in ("true", "false"):
                v = (val.lower() == "true")
            else:
                try:
                    v = float(val) if ("." in val or "e" in val.lower()) else int(val)
                except Exception:
                    v = val
            cur[key] = v
    return data

def write_json(path: pathlib.Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# -------------------------
# Symatics hooks (YOU wire these)
# -------------------------

def sym_interf(phi: float, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Replace this with Symatics interference primitive:
      return Symatics.Interf(phi, A, B) in your canonical representation.

    This stub is *only* to make the runner executable in isolation:
      Interf_phi(A,B) := A + exp(i*phi) B
    """
    return A + np.exp(1j * phi) * B

def sym_distance(X: np.ndarray, Y: np.ndarray) -> float:
    """
    Replace with your canonical Symatics distance (metric) if one exists.
    """
    return float(np.linalg.norm(X - Y))


# -------------------------
# Candidate “effect algebra” (φ-free) representation attempt
# -------------------------

@dataclass(frozen=True)
class UnitIntervalEffect:
    """Minimal effect algebra: E=[0,1], partial sum defined when a+b<=1."""
    x: float

def effect_add(a: UnitIntervalEffect, b: UnitIntervalEffect) -> UnitIntervalEffect:
    s = a.x + b.x
    if s > 1.0 + 1e-15:
        raise ValueError("partial sum undefined (a+b>1)")
    return UnitIntervalEffect(float(s))

def h_map_to_effect(A: np.ndarray) -> UnitIntervalEffect:
    """
    Candidate mapping h: Symatics element -> effect element.

    IMPORTANT: The *failure* we lock is not “this particular h is bad”;
    it is that any φ-free target operation must compute Interf’s image
    from h(A), h(B) using fixed operations, hence cannot depend on φ.

    We keep h deterministic + small so ⊕ is defined.
    """
    # Deterministic “size” proxy; bounded so that h(A)⊕h(B) exists.
    n2 = float(np.vdot(A, A).real)
    # scale into [0,0.49]
    v = min(0.49, n2 / (1.0 + n2) * 0.49)
    return UnitIntervalEffect(v)

def image_of_interf_under_candidate(hA: UnitIntervalEffect, hB: UnitIntervalEffect) -> UnitIntervalEffect:
    """
    The φ-free collapse rule:
      image(Interf_phi(A,B)) := h(A) ⊕ h(B)
    independent of φ (this is the point).
    """
    return effect_add(hA, hB)


# -------------------------
# Lock-surface updater
# -------------------------

def update_lock_surface(counterexample_paths: Dict[str, str]) -> None:
    payload: Dict[str, Any] = {}
    if LOCK_SURFACE.exists():
        try:
            payload = json.loads(LOCK_SURFACE.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    payload.setdefault("version", 1)
    payload.setdefault("sym_compare_v1", {})
    payload["sym_compare_v1"].setdefault("artifact_roots", [])
    if str(ART_ROOT) not in payload["sym_compare_v1"]["artifact_roots"]:
        payload["sym_compare_v1"]["artifact_roots"].append(str(ART_ROOT))

    payload["sym_compare_v1"].setdefault("runners", {})
    payload["sym_compare_v1"]["runners"]["effectalg"] = {
        "relpath": PY_REL,
        "command": f"SEED=0 python {PY_REL}",
        "artifacts": {
            "counterexample_json": str(COUNTEREX),
            "metrics_json": str(METRICS),
            "log": str(LOG_PATH),
        },
    }

    payload["sym_compare_v1"].setdefault("counterexample_sha256", {})
    for k, p in counterexample_paths.items():
        pp = pathlib.Path(p)
        payload["sym_compare_v1"]["counterexample_sha256"][k] = sha256_file(pp)

    write_json(LOCK_SURFACE, payload)


# -------------------------
# Main
# -------------------------

def main() -> int:
    ensure_dir(ART_ROOT)

    started = now_utc_iso()

    # Deterministic seed enforcement
    seed_env = os.environ.get("SEED", "0")
    try:
        seed = int(seed_env)
    except Exception:
        seed = 0
    if seed != 0:
        raise RuntimeError("Determinism required: run with SEED=0")

    # Load shared thresholds + canonical phis
    thr = load_thresholds_yaml(THRESH_YAML)
    phi1 = float(thr["phi"]["phi1"])
    phi2 = float(thr["phi"]["phi2"])
    t_sym_min = float(thr["thresholds"]["effectalg"]["distance_sym_min"])
    t_cand_max = float(thr["thresholds"]["effectalg"]["distance_candidate_max"])

    # Lock explicit A,B (same for both φ)
    # NOTE: adjust dimensionality to your canonical Symatics element basis if needed.
    A = np.array([0.21 + 0.05j, -0.13 + 0.17j, 0.08 - 0.02j, 0.11 + 0.09j], dtype=np.complex128)
    B = np.array([-0.07 + 0.04j, 0.19 - 0.06j, -0.05 + 0.12j, 0.03 - 0.15j], dtype=np.complex128)

    # Symatics interference differs across φ
    S1 = sym_interf(phi1, A, B)
    S2 = sym_interf(phi2, A, B)
    dist_sym = sym_distance(S1, S2)

    # Candidate φ-free image is forced invariant
    hA = h_map_to_effect(A)
    hB = h_map_to_effect(B)
    C1 = image_of_interf_under_candidate(hA, hB)
    C2 = image_of_interf_under_candidate(hA, hB)
    dist_cand = abs(C1.x - C2.x)

    failures = []
    if not (dist_sym > t_sym_min):
        failures.append(f"distance_sym={dist_sym:.6e} <= {t_sym_min:.1e}")
    if not (dist_cand < t_cand_max):
        failures.append(f"distance_candidate={dist_cand:.6e} >= {t_cand_max:.1e}")

    status = "PASS" if not failures else "FAIL"
    finished = now_utc_iso()

    # Counterexample JSON (witness)
    counter = {
        "lock_id": LOCK_ID,
        "status": status,
        "seed": seed,
        "phi": {"phi1": phi1, "phi2": phi2},
        "A": {"re": A.real.tolist(), "im": A.imag.tolist()},
        "B": {"re": B.real.tolist(), "im": B.imag.tolist()},
        "sym": {
            "interf_phi1": {"re": S1.real.tolist(), "im": S1.imag.tolist()},
            "interf_phi2": {"re": S2.real.tolist(), "im": S2.imag.tolist()},
            "distance_sym": dist_sym,
        },
        "candidate_effectalg": {
            "hA": hA.x,
            "hB": hB.x,
            "image_phi1": C1.x,
            "image_phi2": C2.x,
            "distance_candidate": dist_cand,
            "rule": "image(Interf_phi(A,B)) := h(A) ⊕ h(B)  (φ-free)",
        },
        "thresholds": {
            "distance_sym_min": t_sym_min,
            "distance_candidate_max": t_cand_max,
        },
        "failures": failures,
        "started_utc": started,
        "finished_utc": finished,
    }
    write_json(COUNTEREX, counter)

    # Metrics JSON (runner metadata + digests)
    runner_sha = sha256_file(pathlib.Path(PY_REL))
    metrics = {
        "digests": {
            "runner_sha256": runner_sha,
            "counterexample_sha256": sha256_file(COUNTEREX),
        },
        "runner": {
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "numpy": np.__version__,
            "relpath": PY_REL,
        },
        "seed": seed,
        "phi": {"phi1": phi1, "phi2": phi2},
        "thresholds": {
            "distance_sym_min": t_sym_min,
            "distance_candidate_max": t_cand_max,
        },
        "measured": {
            "distance_sym": dist_sym,
            "distance_candidate": dist_cand,
        },
        "failures": failures,
        "started_utc": started,
        "finished_utc": finished,
        "status": status,
    }
    write_json(METRICS, metrics)

    # Log (human readable + required footer style)
    log_lines = []
    log_lines.append("EFFECTALG SEPARATION LINT PROOF (sym_compare_v1)")
    log_lines.append(f"started_utc:  {started}")
    log_lines.append(f"finished_utc: {finished}")
    log_lines.append(f"status:       {status}")
    log_lines.append(f"seed:         {seed}")
    log_lines.append("")
    log_lines.append("CANONICAL PHI:")
    log_lines.append(f"  phi1 = {phi1}  (pi/3)")
    log_lines.append(f"  phi2 = {phi2}  (pi/2)")
    log_lines.append("")
    log_lines.append("THRESHOLDS:")
    log_lines.append(f"  distance_sym(phi1,phi2) >  {t_sym_min:.1e}")
    log_lines.append(f"  distance_candidate      <  {t_cand_max:.1e}")
    log_lines.append("")
    log_lines.append("MEASURED:")
    log_lines.append(f"  distance_sym:      {dist_sym:.6e}")
    log_lines.append(f"  distance_candidate:{dist_cand:.6e}")
    log_lines.append("")
    log_lines.append("ARTIFACTS:")
    log_lines.append(f"  counterexample: {COUNTEREX}")
    log_lines.append(f"  metrics:        {METRICS}")
    log_lines.append(f"  log:            {LOG_PATH}")
    log_lines.append("")
    if failures:
        log_lines.append("FAILURES:")
        for f in failures:
            log_lines.append(f"  - {f}")
        log_lines.append("")
    log_lines.append(f"Lock ID: {LOCK_ID}")
    log_lines.append(f"Status: {status}")
    log_lines.append("Maintainer: Tessaris AI")
    log_lines.append("Author: Kevin Robinson.")
    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    # Update lock surface with counterexample sha
    update_lock_surface({"effectalg": str(COUNTEREX)})

    # Exit nonzero if FAIL (lint semantics)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())