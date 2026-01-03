# backend/modules/sim/qfc_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional
import numpy as np

EPS = 1e-12

def clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def l2_norm(a: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.abs(a) ** 2) + EPS))

def window(a: np.ndarray, cx: int, cy: int, r: int = 1) -> np.ndarray:
    h, w = a.shape
    ys = [(cy + dy) % h for dy in range(-r, r + 1)]
    xs = [(cx + dx) % w for dx in range(-r, r + 1)]
    return a[np.ix_(ys, xs)]

def corr_complex(a: np.ndarray, b: np.ndarray) -> float:
    na = l2_norm(a); nb = l2_norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    inner = np.vdot(a, b)
    return float(np.abs(inner) / (na * nb + EPS))

def apply_throat_coupling(
    psi: np.ndarray, *, a: Tuple[int, int], b: Tuple[int, int], eta: float, sigma: float, dt: float
) -> None:
    eta = clip01(eta); sigma = clip01(sigma)
    x1, y1 = a; x2, y2 = b
    p1 = psi[y1, x1]; p2 = psi[y2, x2]
    k = sigma * eta
    d12 = (p2 - p1)
    psi[y1, x1] = p1 + dt * k * d12
    psi[y2, x2] = p2 - dt * k * d12

def phase_vorticity_rms(psi: np.ndarray) -> float:
    # vorticity of phase gradient (cheap “curl” proxy)
    ph = np.angle(psi)
    dph_dx = np.angle(np.exp(1j * (np.roll(ph, -1, axis=1) - np.roll(ph, 1, axis=1)))) * 0.5
    dph_dy = np.angle(np.exp(1j * (np.roll(ph, -1, axis=0) - np.roll(ph, 1, axis=0)))) * 0.5
    vort = (np.roll(dph_dy, -1, axis=1) - np.roll(dph_dy, 1, axis=1)) * 0.5 - \
           (np.roll(dph_dx, -1, axis=0) - np.roll(dph_dx, 1, axis=0)) * 0.5
    return float(np.sqrt(np.mean(vort * vort) + EPS))

@dataclass
class QFCConfig:
    H: int = 64
    W: int = 64
    nu: float = 0.08
    damp: float = 0.01
    eta: float = 0.98
    src_xy: Tuple[int, int] = (10, 10)
    dst_xy: Tuple[int, int] = (50, 50)
    corr_r: int = 2
    seed: int = 1337

class QFCEngine:
    """
    Stateful lattice sim producing the exact QFC HUD keys:
      kappa, chi, sigma, alpha, curv, curl_rms, coupling_score, max_norm
    """

    def __init__(self, cfg: Optional[QFCConfig] = None) -> None:
        self.cfg = cfg or QFCConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.psi = np.zeros((self.cfg.H, self.cfg.W), dtype=np.complex128)
        x0, y0 = self.cfg.src_xy
        self.psi[y0, x0] = 1.0 + 0.0j
        self._prev_norm = l2_norm(self.psi)
        self._sigma = 0.0

    def set_sigma(self, sigma: float) -> None:
        self._sigma = clip01(float(sigma))

    def step(self, dt: float) -> Dict[str, float]:
        dt = float(max(0.0, dt))

        # base dynamics: diffusion + damping (stable)
        lap = (
            np.roll(self.psi, 1, axis=0) + np.roll(self.psi, -1, axis=0) +
            np.roll(self.psi, 1, axis=1) + np.roll(self.psi, -1, axis=1) -
            4.0 * self.psi
        )
        self.psi = self.psi + dt * (self.cfg.nu * lap - self.cfg.damp * self.psi)

        # coupling after base dynamics
        if self._sigma > 0.0:
            apply_throat_coupling(self.psi, a=self.cfg.src_xy, b=self.cfg.dst_xy,
                                 eta=self.cfg.eta, sigma=self._sigma, dt=dt)

        # tiny deterministic phase noise
        self.psi *= np.exp(1j * (1e-6 * self.rng.normal()))

        # --- metrics ---
        x0, y0 = self.cfg.src_xy
        x1, y1 = self.cfg.dst_xy
        src_w = window(self.psi, x0, y0, r=self.cfg.corr_r)
        dst_w = window(self.psi, x1, y1, r=self.cfg.corr_r)
        chi = clip01(corr_complex(dst_w, src_w))          # correlation “arrival”
        sigma = float(self._sigma)                        # controller gate
        max_norm = float(np.max(np.abs(self.psi)))

        norm = l2_norm(self.psi)
        # alpha: “stability” proxy (1 = stable)
        dnorm = abs(norm - self._prev_norm)
        self._prev_norm = norm
        alpha = clip01(1.0 - min(1.0, dnorm / (norm + EPS)))

        # curv: laplacian energy proxy
        curv = clip01(float(np.mean(np.abs(lap))) * 0.75)

        # curl_rms: vorticity of phase gradient
        curl_rms = float(max(0.0, phase_vorticity_rms(self.psi)))

        # kappa: amplitude coherence proxy
        kappa = clip01(float(np.mean(np.abs(self.psi))) * 1.5)

        # coupling_score: what the HUD expects (tie it to actual coupling)
        coupling_score = clip01(chi * sigma * self.cfg.eta)

        return {
            "kappa": kappa,
            "chi": chi,
            "sigma": clip01(sigma),
            "alpha": alpha,
            "curv": curv,
            "curl_rms": curl_rms,
            "coupling_score": coupling_score,
            "max_norm": max_norm,
        }