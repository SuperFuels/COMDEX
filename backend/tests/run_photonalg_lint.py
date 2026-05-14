# backend/tests/run_photonalg_lint.py
# Deterministic lint/evidence harness for Photon Algebra v0.3 (Φ + Born normalization + C_+-unitary invariance)

from __future__ import annotations

import json
import os
import sys
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np


SEED = 0

# --- acceptance thresholds (suggested; treat as contract for this runner) ---
EPS_SUM_P = 1e-12
MIN_P_GUARD = -1e-15
EPS_PHI_INVAR = 1e-10

ART_ROOT = "docs/Artifacts/photonalg_v0_3"
LOG_PATH = os.path.join(ART_ROOT, "PHOTONALG_LINT_PROOF.log")
METRICS_PATH = os.path.join(ART_ROOT, "PHOTONALG_METRICS.json")
SAMPLES_PATH = os.path.join(ART_ROOT, "artifacts/PHOTONALG_invariance_samples.json")


def _mkdirp(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------- Photon Algebra v0.3 reference representation ----------------

def _blkdiag3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Block-diagonal with three 2x2 blocks -> 6x6."""
    out = np.zeros((6, 6), dtype=np.complex128)
    out[0:2, 0:2] = a
    out[2:4, 2:4] = b
    out[4:6, 4:6] = c
    return out


def pauli() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    I = np.eye(2, dtype=np.complex128)
    sx = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    sy = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    sz = np.array([[1, 0], [0, -1]], dtype=np.complex128)
    return I, sx, sy, sz


def rho_basis() -> Dict[str, np.ndarray]:
    """ρ(e_i) as in Volume I / Photon Algebra v0.3 doc."""
    I, sx, sy, sz = pauli()
    Z = np.zeros((2, 2), dtype=np.complex128)

    e0 = _blkdiag3(I, I, I)
    e1 = _blkdiag3(sx, Z, Z)
    e2 = _blkdiag3(sy, Z, Z)
    e3 = _blkdiag3(sz, Z, Z)
    e4 = _blkdiag3(I, -I, I)
    e5 = _blkdiag3(I, I, -I)

    return {"e0": e0, "e1": e1, "e2": e2, "e3": e3, "e4": e4, "e5": e5}


def rho_of_coeffs(coeffs: Dict[str, complex], basis: Dict[str, np.ndarray]) -> np.ndarray:
    """ρ(ψ) for ψ = Σ_i a_i e_i."""
    out = np.zeros((6, 6), dtype=np.complex128)
    for k, a in coeffs.items():
        if k not in basis:
            raise KeyError(f"Unknown basis element: {k}")
        out = out + complex(a) * basis[k]
    return out


def C_plus(basis: Dict[str, np.ndarray]) -> np.ndarray:
    """C_+ = (1/3)(e0 + e4 + e5)."""
    return (basis["e0"] + basis["e4"] + basis["e5"]) / 3.0


def Phi(rho_psi: np.ndarray, rho_Cp: np.ndarray) -> float:
    """Φ(ψ) = (1/6) Tr( ρ(ψ)† ρ(C_+) ρ(ψ) ) >= 0."""
    val = (np.trace(rho_psi.conj().T @ rho_Cp @ rho_psi) / 6.0).real
    # numerical guard: tiny negative from fp noise -> clamp
    return float(max(val, -1e-18))


def projector_family() -> List[np.ndarray]:
    """
    Build 6 mutually orthogonal rank-1 projectors that sum to I_6, aligned to block basis.
    (Two per 2x2 block.)
    """
    P = []
    for blk in range(3):
        for j in range(2):
            v = np.zeros((6, 1), dtype=np.complex128)
            v[2 * blk + j, 0] = 1.0
            P.append(v @ v.conj().T)
    # Sanity: sum = I
    S = sum(P)
    if not np.allclose(S, np.eye(6), atol=0, rtol=0):
        raise RuntimeError("Projector family does not sum to identity.")
    return P


def random_coeffs(rng: np.random.Generator) -> Dict[str, complex]:
    # moderate magnitude to avoid underflow/overflow
    keys = ["e0", "e1", "e2", "e3", "e4", "e5"]
    re = rng.normal(0.0, 1.0, size=len(keys))
    im = rng.normal(0.0, 1.0, size=len(keys))
    return {k: complex(re[i], im[i]) for i, k in enumerate(keys)}


def random_block_unitary(rng: np.random.Generator) -> np.ndarray:
    """Generate a deterministic 2x2 unitary via complex QR."""
    A = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
    Q, R = np.linalg.qr(A)
    # normalize phases on diagonal of R
    d = np.diag(R)
    ph = d / np.where(np.abs(d) == 0, 1.0, np.abs(d))
    Q = Q * ph.conj()
    return Q


def declared_Cp_unitaries(rng: np.random.Generator) -> List[np.ndarray]:
    """
    Any block-diagonal U = diag(U1,U2,U3) with Ui unitary satisfies U† C_+ U = C_+
    because C_+ is scalar*I on each block.
    """
    I2, sx, sy, sz = pauli()

    # a small declared set: identity, Pauli flips, phase rotation, and random unitaries per block
    phase = np.exp(1j * 0.37)
    U_phase = phase * I2

    U_list_2x2 = [
        I2,
        sx,
        sy,
        sz,
        U_phase,
        random_block_unitary(rng),
    ]

    U6 = []
    for U1 in U_list_2x2[:4]:
        U6.append(_blkdiag3(U1, I2, I2))
    U6.append(_blkdiag3(U_phase, U_phase, U_phase))
    U6.append(_blkdiag3(random_block_unitary(rng), random_block_unitary(rng), random_block_unitary(rng)))

    return U6


# ---------------- Lint checks ----------------

@dataclass
class LintResult:
    sumP_max_abs_err: float
    minP: float
    max_phi_invar_abs: float
    phi_zero: float
    rho_zero_norm: float
    phi_positive_min: float
    phi_positive_count: int
    samples: Dict[str, object]


def run_lint() -> LintResult:
    rng = np.random.default_rng(SEED)
    basis = rho_basis()
    rho_Cp = C_plus(basis)
    Ps = projector_family()
    Us = declared_Cp_unitaries(rng)

    # Deterministic sample set
    N_SAMPLES = 32

    sumP_errs: List[float] = []
    minPs: List[float] = []
    invar_abs: List[float] = []
    phi_vals: List[float] = []

    sample_dump: List[Dict[str, object]] = []

    # Phi(0) <-> rho(0)=0
    coeffs_zero = {k: 0.0 + 0.0j for k in basis.keys()}
    rho0 = rho_of_coeffs(coeffs_zero, basis)
    phi0 = Phi(rho0, rho_Cp)
    rho0n = float(np.linalg.norm(rho0))

    # Random nonzero ψ checks
    for i in range(N_SAMPLES):
        coeffs = random_coeffs(rng)
        rho_psi = rho_of_coeffs(coeffs, basis)
        phi = Phi(rho_psi, rho_Cp)
        phi_vals.append(phi)

        # Probabilities from orthogonal projectors
        if phi <= 0:
            # extremely unlikely given random coeffs; skip normalization to avoid divide-by-zero
            continue

        probs = []
        for P in Ps:
            phi_i = Phi(P @ rho_psi, rho_Cp)
            probs.append(phi_i / phi)

        probs = np.array(probs, dtype=np.float64)
        sumP = float(probs.sum())
        sumP_errs.append(abs(sumP - 1.0))
        minPs.append(float(probs.min()))

        # C_+-unitary invariance
        max_abs_local = 0.0
        for U in Us:
            # Check declared property (hard assert; should be exact up to fp)
            lhs = U.conj().T @ rho_Cp @ U
            if not np.allclose(lhs, rho_Cp, atol=1e-12, rtol=0):
                raise AssertionError("Declared U is not C_+-unitary within tolerance.")

            phi_u = Phi(U @ rho_psi, rho_Cp)
            max_abs_local = max(max_abs_local, abs(phi_u - phi))
        invar_abs.append(max_abs_local)

        # sample record (small; deterministic)
        sample_dump.append(
            {
                "idx": i,
                "coeffs": {k: [coeffs[k].real, coeffs[k].imag] for k in sorted(coeffs.keys())},
                "Phi": phi,
                "probs": probs.tolist(),
                "sumP": sumP,
                "minP": float(probs.min()),
                "max_abs_phi_invar": max_abs_local,
            }
        )

    sumP_max_abs_err = float(max(sumP_errs) if sumP_errs else 0.0)
    minP = float(min(minPs) if minPs else 0.0)
    max_phi_invar_abs = float(max(invar_abs) if invar_abs else 0.0)

    phi_positive = [v for v in phi_vals if v > 0]
    phi_positive_min = float(min(phi_positive) if phi_positive else 0.0)
    phi_positive_count = int(len(phi_positive))

    samples = {
        "seed": SEED,
        "N_SAMPLES": N_SAMPLES,
        "projectors": {"count": len(Ps), "rank_each": 1, "sum_is_I6": True},
        "declared_U_count": len(Us),
        "records": sample_dump,
    }

    return LintResult(
        sumP_max_abs_err=sumP_max_abs_err,
        minP=minP,
        max_phi_invar_abs=max_phi_invar_abs,
        phi_zero=phi0,
        rho_zero_norm=rho0n,
        phi_positive_min=phi_positive_min,
        phi_positive_count=phi_positive_count,
        samples=samples,
    )


def main() -> int:
    _mkdirp(os.path.dirname(LOG_PATH))
    _mkdirp(os.path.dirname(METRICS_PATH))
    _mkdirp(os.path.dirname(SAMPLES_PATH))

    started = _now_utc_iso()

    try:
        res = run_lint()

        # --- MUST checks ---
        # Probability normalization and non-negativity guard
        if not (res.sumP_max_abs_err < EPS_SUM_P):
            raise AssertionError(f"sum_i P(i) normalization failed: max|sumP-1|={res.sumP_max_abs_err:g}")
        if not (res.minP >= MIN_P_GUARD):
            raise AssertionError(f"P(i) non-negativity guard failed: minP={res.minP:g}")

        # Φ positivity + Φ(0)=0 and "↔" direction in representation (tested as: Φ(0)=0 and ||ρ(0)||=0)
        if not (abs(res.phi_zero) == 0.0 or abs(res.phi_zero) < 1e-18):
            raise AssertionError(f"Phi(0) must be 0: Phi(0)={res.phi_zero:g}")
        if not (res.rho_zero_norm == 0.0):
            raise AssertionError(f"rho(0) must be zero matrix: ||rho(0)||={res.rho_zero_norm:g}")
        # For random nonzero samples, Φ should be > 0 (sanity)
        if not (res.phi_positive_count >= 1 and res.phi_positive_min > 0.0):
            raise AssertionError("Phi positivity sanity failed: no positive Phi samples observed.")

        # C_+-unitary invariance
        if not (res.max_phi_invar_abs < EPS_PHI_INVAR):
            raise AssertionError(f"C_+-unitary invariance failed: max|Phi(Uψ)-Phi(ψ)|={res.max_phi_invar_abs:g}")

        status = "PASS"
        exit_code = 0

    except Exception as e:
        status = "FAIL"
        exit_code = 1
        err = repr(e)

    finished = _now_utc_iso()

    # Write samples artifact (always write if we have it)
    samples_payload = {
        "started_utc": started,
        "finished_utc": finished,
        "status": status,
        "thresholds": {
            "abs(sumP-1) <": EPS_SUM_P,
            "min(P) >=": MIN_P_GUARD,
            "max|Phi(Uψ)-Phi(ψ)| <": EPS_PHI_INVAR,
        },
    }
    if status == "PASS":
        samples_payload["samples"] = res.samples
    else:
        samples_payload["error"] = err

    samples_bytes = json.dumps(samples_payload, indent=2, sort_keys=True).encode("utf-8")
    with open(SAMPLES_PATH, "wb") as f:
        f.write(samples_bytes)

    # Metrics artifact
    metrics = {
        "started_utc": started,
        "finished_utc": finished,
        "status": status,
        "seed": SEED,
        "thresholds": {
            "EPS_SUM_P": EPS_SUM_P,
            "MIN_P_GUARD": MIN_P_GUARD,
            "EPS_PHI_INVAR": EPS_PHI_INVAR,
        },
        "measured": {},
        "digests": {},
        "runner": {
            "relpath": "backend/tests/run_photonalg_lint.py",
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        },
    }

    if status == "PASS":
        metrics["measured"] = {
            "sumP_max_abs_err": res.sumP_max_abs_err,
            "minP": res.minP,
            "max_phi_invar_abs": res.max_phi_invar_abs,
            "phi_zero": res.phi_zero,
            "rho_zero_norm": res.rho_zero_norm,
            "phi_positive_min": res.phi_positive_min,
            "phi_positive_count": res.phi_positive_count,
        }
    else:
        metrics["measured"] = {"error": err}

    # digests (script + artifacts)
    try:
        metrics["digests"]["samples_sha256"] = _sha256_file(SAMPLES_PATH)
    except Exception:
        pass
    try:
        metrics["digests"]["runner_sha256"] = _sha256_file(__file__)
    except Exception:
        pass

    metrics_bytes = json.dumps(metrics, indent=2, sort_keys=True).encode("utf-8")
    with open(METRICS_PATH, "wb") as f:
        f.write(metrics_bytes)

    # Log artifact
    lines = []
    lines.append("PHOTONALG LINT PROOF (Photon Algebra v0.3)")
    lines.append(f"started_utc:  {started}")
    lines.append(f"finished_utc: {finished}")
    lines.append(f"status:       {status}")
    lines.append(f"seed:         {SEED}")
    lines.append("")
    lines.append("THRESHOLDS:")
    lines.append(f"  abs(sumP-1) < {EPS_SUM_P:g}")
    lines.append(f"  min(P) >=     {MIN_P_GUARD:g}")
    lines.append(f"  max|ΔΦ| <     {EPS_PHI_INVAR:g}")
    lines.append("")
    if status == "PASS":
        lines.append("MEASURED:")
        lines.append(f"  max|sumP-1|:          {res.sumP_max_abs_err:.3e}")
        lines.append(f"  min(P):              {res.minP:.3e}")
        lines.append(f"  max|Phi(Uψ)-Phi(ψ)|:  {res.max_phi_invar_abs:.3e}")
        lines.append(f"  Phi(0):              {res.phi_zero:.3e}")
        lines.append(f"  ||rho(0)||:          {res.rho_zero_norm:.3e}")
        lines.append(f"  Phi_positive_min:    {res.phi_positive_min:.3e}")
        lines.append(f"  Phi_positive_count:  {res.phi_positive_count}")
    else:
        lines.append("ERROR:")
        lines.append(f"  {err}")
    lines.append("")
    lines.append("ARTIFACTS:")
    lines.append(f"  log:     {LOG_PATH}")
    lines.append(f"  metrics: {METRICS_PATH}")
    lines.append(f"  samples: {SAMPLES_PATH}")
    lines.append("")
    # sha256s
    try:
        lines.append(f"samples_sha256: {_sha256_file(SAMPLES_PATH)}")
    except Exception:
        pass
    try:
        lines.append(f"metrics_sha256: {_sha256_file(METRICS_PATH)}")
    except Exception:
        pass
    try:
        lines.append(f"runner_sha256:  {_sha256_file(__file__)}")
    except Exception:
        pass

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Exit nonzero on FAIL
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())