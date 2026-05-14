#!/usr/bin/env python3
"""
PHOTONALG STRUCTURE LINT (Photon Algebra v0.3)

Purpose:
- Verify the rho-representation basis is well-formed (rank, Hermitian basis)
- Verify closure in the span via reconstruction residual (pinv projection)
- Verify commutation of declared central elements with Pauli sector
- Verify associativity and *-law for the induced coefficient product

Artifacts (MUST emit):
- docs/Artifacts/photonalg_v0_3/PHOTONALG_STRUCTURE_LINT_PROOF.log
- docs/Artifacts/photonalg_v0_3/PHOTONALG_STRUCTURE_METRICS.json
- docs/Artifacts/photonalg_v0_3/artifacts/PHOTONALG_structure_samples.json

Lock footer format:
Lock ID: <...>
Status: <...>
Maintainer: Tessaris AI
Author: Kevin Robinson.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np


# -----------------------------
# Deterministic config
# -----------------------------
SEED = 0
N_SAMPLES = 32

# Thresholds (tight; should pass at ~1e-15 if consistent)
RANK_TOL = 1e-12
EPS_BASIS_HERM = 1e-12
EPS_HOM = 1e-12          # closure residual on basis products
EPS_COMM = 1e-12
EPS_ASSOC = 1e-12
EPS_STAR = 1e-12

# Artifact paths
ART_ROOT = os.path.join("docs", "Artifacts", "photonalg_v0_3")
ART_DIR = os.path.join(ART_ROOT, "artifacts")
LOG_PATH = os.path.join(ART_ROOT, "PHOTONALG_STRUCTURE_LINT_PROOF.log")
METRICS_PATH = os.path.join(ART_ROOT, "PHOTONALG_STRUCTURE_METRICS.json")
SAMPLES_PATH = os.path.join(ART_DIR, "PHOTONALG_structure_samples.json")


# -----------------------------
# Helpers
# -----------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def ensure_dirs() -> None:
    os.makedirs(ART_DIR, exist_ok=True)
    os.makedirs(ART_ROOT, exist_ok=True)

def repo_root_from_file(pyfile: str) -> str:
    # backend/tests/<file> -> go up 3 levels to repo root
    return os.path.abspath(os.path.join(os.path.dirname(pyfile), "../../.."))

def relpath_from_root(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except Exception:
        return path

def block_diag3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    z = np.zeros((6, 6), dtype=np.complex128)
    z[0:2, 0:2] = a
    z[2:4, 2:4] = b
    z[4:6, 4:6] = c
    return z

def fro_norm(m: np.ndarray) -> float:
    return float(np.linalg.norm(m, ord="fro"))

def l2_norm(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))

def to_pairs6(coeffs: np.ndarray) -> List[List[float]]:
    # coeffs complex length-6 -> [[re, im], ...]
    out: List[List[float]] = []
    for x in coeffs:
        out.append([float(np.real(x)), float(np.imag(x))])
    return out


# -----------------------------
# Basis + rho + induced product
# -----------------------------
@dataclass(frozen=True)
class RhoAlgebra:
    basis: List[np.ndarray]          # 6 matrices, 6x6
    B: np.ndarray                    # 36x6 column-stacked basis vectors
    pinvB: np.ndarray                # 6x36 left-inverse

    def rho(self, c: np.ndarray) -> np.ndarray:
        # c shape (6,) complex
        # sum_i c_i * basis_i
        m = np.zeros((6, 6), dtype=np.complex128)
        for i in range(6):
            m += c[i] * self.basis[i]
        return m

    def coeffs_of(self, m: np.ndarray) -> np.ndarray:
        # project m onto span(basis) using pinv
        v = m.reshape(-1)
        return (self.pinvB @ v).astype(np.complex128)

    def project(self, m: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        # returns (coeffs, reconstructed_matrix, residual_fro)
        c = self.coeffs_of(m)
        m2 = (self.B @ c).reshape(6, 6)
        resid = fro_norm(m - m2)
        return c, m2, resid

    def mul(self, a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, float]:
        # induced coefficient product: a ⊙ b := coeffs_of(rho(a)rho(b))
        m = self.rho(a) @ self.rho(b)
        c, _, resid = self.project(m)
        return c, resid

    def star(self, a: np.ndarray) -> np.ndarray:
        # Hermitian basis => * is coefficient-wise conjugation
        return np.conj(a)


def build_rho_algebra() -> RhoAlgebra:
    I2 = np.eye(2, dtype=np.complex128)
    O2 = np.zeros((2, 2), dtype=np.complex128)

    sx = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    sy = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    sz = np.array([[1, 0], [0, -1]], dtype=np.complex128)

    # Basis: e0..e5
    e0 = block_diag3(I2, I2, I2)
    e1 = block_diag3(sx, O2, O2)
    e2 = block_diag3(sy, O2, O2)
    e3 = block_diag3(sz, O2, O2)
    e4 = block_diag3(I2, -I2, I2)
    e5 = block_diag3(I2, I2, -I2)

    basis = [e0, e1, e2, e3, e4, e5]

    # Build column-stacked basis vectors B (36x6), compute left inverse
    B = np.column_stack([m.reshape(-1) for m in basis]).astype(np.complex128)

    # full rank check later; pinv is stable for evidence harness
    pinvB = np.linalg.pinv(B, rcond=1e-15).astype(np.complex128)

    return RhoAlgebra(basis=basis, B=B, pinvB=pinvB)


# -----------------------------
# Main runner
# -----------------------------
def main() -> int:
    ensure_dirs()
    started = utc_now()

    rng = np.random.default_rng(SEED)
    A = build_rho_algebra()
    basis = A.basis

    # Basis rank (over C): use real+imag stacked to compute rank robustly
    Bc = np.column_stack([m.reshape(-1) for m in basis])  # 36x6 complex
    Breal = np.vstack([np.real(Bc), np.imag(Bc)])         # 72x6 real
    basis_rank = int(np.linalg.matrix_rank(Breal, tol=RANK_TOL))

    # Hermitian basis check
    max_basis_herm_fro = 0.0
    for m in basis:
        max_basis_herm_fro = max(max_basis_herm_fro, fro_norm(m - m.conj().T))

    # Closure residual on basis products (this is what homomorphism reduces to here)
    # For each basis pair, compute residual of projecting product back into span.
    max_hom_fro = 0.0
    for i in range(6):
        for j in range(6):
            prod = basis[i] @ basis[j]
            _, _, resid = A.project(prod)
            max_hom_fro = max(max_hom_fro, resid)

    # Commutation for central candidates (e4,e5) vs Pauli sector (e1..e3)
    max_comm_fro = 0.0
    for central_idx in (4, 5):
        for pauli_idx in (1, 2, 3):
            c = basis[central_idx]
            p = basis[pauli_idx]
            comm = c @ p - p @ c
            max_comm_fro = max(max_comm_fro, fro_norm(comm))

    # Random samples: associativity and star law under induced product
    max_assoc_l2 = 0.0
    max_star_l2 = 0.0
    records: List[Dict] = []

    def rand_coeffs() -> np.ndarray:
        re = rng.normal(size=6)
        im = rng.normal(size=6)
        return (re + 1j * im).astype(np.complex128)

    for idx in range(N_SAMPLES):
        a = rand_coeffs()
        b = rand_coeffs()
        c = rand_coeffs()

        ab, resid_ab = A.mul(a, b)
        bc, resid_bc = A.mul(b, c)

        left, resid_left = A.mul(ab, c)
        right, resid_right = A.mul(a, bc)

        assoc_l2 = l2_norm(left - right)
        max_assoc_l2 = max(max_assoc_l2, assoc_l2)

        # Star law: (ab)^* == b^* a^*
        lhs = A.star(ab)
        rhs, resid_rhs = A.mul(A.star(b), A.star(a))
        star_l2 = l2_norm(lhs - rhs)
        max_star_l2 = max(max_star_l2, star_l2)

        records.append(
            {
                "idx": idx,
                "coeffs_a": to_pairs6(a),
                "coeffs_b": to_pairs6(b),
                "coeffs_c": to_pairs6(c),
                "assoc_l2": assoc_l2,
                "star_l2": star_l2,
                "resid_ab_fro": resid_ab,
                "resid_bc_fro": resid_bc,
                "resid_left_fro": resid_left,
                "resid_right_fro": resid_right,
                "resid_star_rhs_fro": resid_rhs,
            }
        )

    # Build results
    thresholds = {
        "RANK_TOL": RANK_TOL,
        "EPS_BASIS_HERM": EPS_BASIS_HERM,
        "EPS_HOM": EPS_HOM,
        "EPS_COMM": EPS_COMM,
        "EPS_ASSOC": EPS_ASSOC,
        "EPS_STAR": EPS_STAR,
    }

    measured = {
        "basis_rank": basis_rank,
        "max_basis_herm_fro": max_basis_herm_fro,
        "max_hom_fro": max_hom_fro,
        "max_comm_fro": max_comm_fro,
        "max_assoc_l2": max_assoc_l2,
        "max_star_l2": max_star_l2,
    }

    failures: List[str] = []
    if basis_rank != 6:
        failures.append(f"basis_rank={basis_rank} != 6")
    if max_basis_herm_fro > EPS_BASIS_HERM:
        failures.append(f"max_basis_herm_fro={max_basis_herm_fro:.3e} > {EPS_BASIS_HERM:.3e}")
    if max_hom_fro > EPS_HOM:
        failures.append(f"max_hom_fro={max_hom_fro:.3e} > {EPS_HOM:.3e}")
    if max_comm_fro > EPS_COMM:
        failures.append(f"max_comm_fro={max_comm_fro:.3e} > {EPS_COMM:.3e}")
    if max_assoc_l2 > EPS_ASSOC:
        failures.append(f"max_assoc_l2={max_assoc_l2:.3e} > {EPS_ASSOC:.3e}")
    if max_star_l2 > EPS_STAR:
        failures.append(f"max_star_l2={max_star_l2:.3e} > {EPS_STAR:.3e}")

    status = "PASS" if not failures else "FAIL"
    finished = utc_now()

    # Write samples first
    samples_payload = {
        "started_utc": started,
        "finished_utc": finished,
        "status": status,
        "seed": SEED,
        "thresholds": thresholds,
        "measured": measured,
        "samples": {"N_SAMPLES": N_SAMPLES, "records": records},
        "failures": failures,
    }
    with open(SAMPLES_PATH, "w", encoding="utf-8") as f:
        json.dump(samples_payload, f, indent=2, sort_keys=True)

    # Digests
    runner_path = os.path.abspath(__file__)
    with open(runner_path, "rb") as f:
        runner_bytes = f.read()
    runner_sha = sha256_bytes(runner_bytes)
    samples_sha = sha256_file(SAMPLES_PATH)

    repo_root = repo_root_from_file(__file__)
    relpath = relpath_from_root(runner_path, repo_root)

    metrics_payload = {
        "started_utc": started,
        "finished_utc": finished,
        "status": status,
        "seed": SEED,
        "thresholds": thresholds,
        "measured": measured,
        "failures": failures,
        "runner": {
            "relpath": relpath,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
        "digests": {
            "runner_sha256": runner_sha,
            "samples_sha256": samples_sha,
        },
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2, sort_keys=True)

    metrics_sha = sha256_file(METRICS_PATH)

    # Write log
    lines: List[str] = []
    lines.append("PHOTONALG STRUCTURE LINT PROOF (Photon Algebra v0.3)")
    lines.append(f"started_utc:  {started}")
    lines.append(f"finished_utc: {finished}")
    lines.append(f"status:       {status}")
    lines.append(f"seed:         {SEED}")
    lines.append("")
    lines.append("THRESHOLDS:")
    lines.append("  basis_rank == 6")
    lines.append(f"  max_basis_herm_fro <= {EPS_BASIS_HERM:g}")
    lines.append(f"  max_hom_fro <=       {EPS_HOM:g}    (closure residual)")
    lines.append(f"  max_comm_fro <=      {EPS_COMM:g}")
    lines.append(f"  max_assoc_l2 <=      {EPS_ASSOC:g}")
    lines.append(f"  max_star_l2 <=       {EPS_STAR:g}")
    lines.append("")
    lines.append("MEASURED:")
    lines.append(f"  basis_rank:          {basis_rank}")
    lines.append(f"  max_basis_herm_fro:  {max_basis_herm_fro:.3e}")
    lines.append(f"  max_hom_fro:         {max_hom_fro:.3e}")
    lines.append(f"  max_comm_fro:        {max_comm_fro:.3e}")
    lines.append(f"  max_assoc_l2:        {max_assoc_l2:.3e}")
    lines.append(f"  max_star_l2:         {max_star_l2:.3e}")
    lines.append("")
    lines.append("ARTIFACTS:")
    lines.append(f"  log:     {LOG_PATH}")
    lines.append(f"  metrics: {METRICS_PATH}")
    lines.append(f"  samples: {SAMPLES_PATH}")
    lines.append("")
    lines.append(f"samples_sha256: {samples_sha}")
    lines.append(f"metrics_sha256: {metrics_sha}")
    lines.append(f"runner_sha256:  {runner_sha}")
    lines.append("")

    if failures:
        lines.append("FAILURES:")
        for s in failures:
            lines.append(f"  - {s}")
        lines.append("")

    # Lock footer (stable text)
    lines.append("Lock ID: PHOTONALG_STRUCTURE_LINT_v0_3")
    lines.append(f"Status: {status}")
    lines.append("Maintainer: Tessaris AI")
    lines.append("Author: Kevin Robinson.")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
