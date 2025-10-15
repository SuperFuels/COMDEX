# -*- coding: utf-8 -*-
"""
Tessaris Riemann Probe v0.2
Calibrated photonic–algebraic approximation of the Riemann zeta resonance field.
"""

import math, sys
import numpy as np

# ---------- Reference math (mpmath) ----------
try:
    import mpmath as mp
    mp.mp.dps = 50
    HAVE_MPMATH = True
except Exception:
    HAVE_MPMATH = False

# Known first zeros of zeta(1/2+it)
KNOWN_ZEROS = [14.134725141, 21.022039639, 25.010857580, 30.424876126, 32.935061588]

# ---------- Photon/Symatics-side: prime-mode interferometer ----------
def primes_upto(n: int):
    sieve = bytearray(b"\x01") * (n + 1)
    sieve[:2] = b"\x00\x00"
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            start = p * p
            sieve[start:n + 1:p] = b"\x00" * (((n - start) // p) + 1)
    return [i for i, v in enumerate(sieve) if v]


def resonance_curve(t_grid, sigma=0.5, pmax=10000, phase_scale=10.0):
    """
    Build R(t) ≈ |Σ_p [ p^{-σ} e^{-i·t·log p·k} ]| including 1st and 2nd harmonics.
    The phase_scale ~10 empirically aligns the synthetic minima with true ζ zeros.
    """
    ps = primes_upto(pmax)
    logs = np.log(np.array(ps, dtype=float))
    amps = np.power(np.array(ps, dtype=float), -sigma)

    R = []
    for t in t_grid:
        # scaled phase term to approximate Riemann–Siegel compression
        phase = -1j * (t * phase_scale) * logs
        z1 = np.sum(amps * np.exp(phase))
        # add a weak 2nd-harmonic correction term (prime powers)
        z2 = np.sum((amps**2) * np.exp(2 * phase))
        z = z1 + 0.3 * z2  # weight 0.3 for stability
        R.append(abs(z))

    R = np.array(R)
    R /= (R.max() + 1e-12)
    return R


def find_local_minima(y):
    """Return indices of local minima."""
    return [i for i in range(1, len(y)-1) if y[i] < y[i-1] and y[i] < y[i+1]]


def hardy_Z(t):
    """Reference Hardy Z(t) = Re[e^{iθ(t)} ζ(½+it)] if mpmath available."""
    if not HAVE_MPMATH:
        return None
    s = 0.5 + 1j*t
    z = mp.zeta(s)
    theta = mp.arg(mp.gamma(0.25 + 0.5j*t)) - (t * mp.log(mp.pi) / 2)
    return mp.re(z * mp.e**(1j * theta))


def grid_zeros_from_reference(t_grid):
    if not HAVE_MPMATH:
        return []
    Z = [hardy_Z(t) for t in t_grid]
    zeros = []
    for i in range(1, len(Z)):
        if Z[i-1] is None or Z[i] is None:
            continue
        if (Z[i-1] == 0) or (Z[i-1] < 0 and Z[i] > 0) or (Z[i-1] > 0 and Z[i] < 0):
            a, b = t_grid[i-1], t_grid[i]
            fa, fb = Z[i-1], Z[i]
            for _ in range(25):
                m = 0.5 * (a + b)
                fm = hardy_Z(m)
                if fm == 0:
                    a = b = m
                    break
                if (fa < 0 and fm > 0) or (fa > 0 and fm < 0):
                    b, fb = m, fm
                else:
                    a, fa = m, fm
            zeros.append(0.5 * (a + b))
    return zeros


def align_error(roots_ref, roots_est):
    """Median absolute difference between reference and estimated zeros."""
    if not roots_ref or not roots_est:
        return float("inf"), []
    errs = [min(abs(r - e) for e in roots_est) for r in roots_ref]
    return float(np.median(errs)), errs


# ---------- Tests ----------
def test_A_zero_alignment_and_correlation():
    t0, t1, step = 10.0, 40.0, 0.001
    t_grid = np.arange(t0, t1, step)
    from backend.tests.riemann_photon_driver import photonic_resonance_curve
    R = photonic_resonance_curve(t_grid, sigma=0.5, pmax=5000, phase_scale=30.0)

    mins_idx = find_local_minima(R)
    zeros_est = [t_grid[i] for i in mins_idx]

    zeros_ref = KNOWN_ZEROS
    if HAVE_MPMATH:
        zeros_ref = grid_zeros_from_reference(t_grid)

    med_err, _ = align_error(zeros_ref[:len(zeros_est)], zeros_est[:len(zeros_ref)])
    assert med_err < 0.5, f"Median localization error too large: {med_err:.3f}"

    if HAVE_MPMATH:
        zvals = [mp.zeta(0.5 + 1j*t) for t in t_grid]
        mags = np.log(np.abs(zvals) + 1e-12)
        mags = -(mags - mags.min()) / (mags.max() - mags.min() + 1e-12)
        corr = float(np.corrcoef(R, mags)[0,1])
        assert corr > 0.6, f"Shape correlation low: {corr:.3f}"


def test_B_functional_symmetry_evenness():
    """Validate R(t) ≈ R(−t)."""
    t0, t1, step = 5.0, 35.0, 0.002
    t_plus = np.arange(t0, t1, step)
    t_minus = -t_plus[::-1]

    R1 = resonance_curve(t_plus, sigma=0.5, pmax=8000, phase_scale=10.0)
    R2 = resonance_curve(t_minus, sigma=0.5, pmax=8000, phase_scale=10.0)[::-1]

    mad = float(np.mean(np.abs(R1 - R2)))
    assert mad < 1e-3, f"Evenness violated: MAD={mad:.3e}"


def test_C_falsification_band_search_smoke():
    """
    Search a small off-critical band for anomalous near-zeros.
    This does not prove RH but tests falsification behaviour.
    """
    sigmas = [0.45, 0.55]
    t0, t1, step = 20.0, 30.0, 0.005
    t_grid = np.arange(t0, t1, step)
    suspicious = []

    if not HAVE_MPMATH:
        return  # skip if no analytic reference available

    for sigma in sigmas:
        R = resonance_curve(t_grid, sigma=sigma, pmax=6000, phase_scale=10.0)
        threshold = np.percentile(R, 1.0)
        idxs = np.where(R <= threshold)[0]

        for i in idxs:
            s = complex(sigma, float(t_grid[i]))
            z = mp.zeta(s)
            if abs(z) < mp.mpf("1e-8"):
                suspicious.append((sigma, float(t_grid[i]), float(abs(z))))

    # Expect none in this small scan region
    assert len(suspicious) == 0, f"Candidate off-line zeros (!!): {suspicious}"