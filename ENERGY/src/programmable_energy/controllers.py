from __future__ import annotations
from dataclasses import dataclass
import json
import hashlib
import numpy as np

from .field import fft_propagate, intensity_from_field, random_walk_phase
PE_CODE_VERSION = "PE01_v0.2"

from .metrics import (
    roi_mask_circle, roi_efficiency, mse, coherence_map, phase_entropy_proxy, div_info_flux
)

@dataclass(frozen=True)
class PEConfig:
    N: int = 256
    steps: int = 60
    seed: int = 1337
    drift_sigma: float = 1e-3
    roi_radius: int = 10
    tups_version: str = "TUPS_V1.2"
    alpha: float = 0.5
    beta: float = 0.2
    chi: float = 1.0

def run_hash_for(config: PEConfig, *, test_id: str, controller_name: str) -> str:
    payload = {"test_id": test_id, "controller": controller_name, "config": config.__dict__, "code_version": PE_CODE_VERSION}
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    return h[:7]

def target_focus_intensity(N: int, sigma: float = 4.0) -> np.ndarray:
    c = N // 2
    yy, xx = np.mgrid[:N, :N]
    r2 = (yy - c) ** 2 + (xx - c) ** 2
    T = np.exp(-0.5 * r2 / (sigma ** 2))
    T = T / np.sum(T)
    return T


def target_split_intensity(N: int, sep: int = 28, sigma: float = 6.0, ratio_left: float = 0.5) -> np.ndarray:
    """
    Two Gaussian lobes (left/right) with adjustable power ratio.
    ratio_left in [0,1] is the fraction of total energy in the left lobe.
    """
    c = N // 2
    yy, xx = np.mgrid[:N, :N]
    xL = c - sep
    xR = c + sep
    r2L = (yy - c) ** 2 + (xx - xL) ** 2
    r2R = (yy - c) ** 2 + (xx - xR) ** 2
    GL = np.exp(-0.5 * r2L / (sigma ** 2))
    GR = np.exp(-0.5 * r2R / (sigma ** 2))
    T = ratio_left * GL + (1.0 - ratio_left) * GR
    T = T / (np.sum(T) + 1e-12)
    return T
class BaseController:
    name = "base"
    def __init__(self, N: int):
        self.N = N
        self.phase_mask = np.zeros((N, N), dtype=np.float64)

    def step(self, U_in: np.ndarray, env_phase: np.ndarray, target_I: np.ndarray, roi_mask: np.ndarray) -> None:
        raise NotImplementedError

class OpenLoopController(BaseController):
    name = "open_loop"
    def step(self, U_in, env_phase, target_I, roi_mask) -> None:
        return

class SPGDController(BaseController):
    name = "spgd_baseline"
    def __init__(self, N: int, rng: np.random.Generator, delta: float = 0.05, lr: float = 0.5):
        super().__init__(N)
        self.rng = rng
        self.delta = delta
        self.lr = lr

    def _score(self, U_in, env_phase, roi_mask) -> float:
        U = U_in * np.exp(1j * (self.phase_mask + env_phase))
        Uf = fft_propagate(U)
        I = intensity_from_field(Uf)
        return roi_efficiency(I, roi_mask)

    def step(self, U_in, env_phase, target_I, roi_mask) -> None:
        perturb = self.rng.choice([-1.0, 1.0], size=(self.N, self.N)) * self.delta

        self.phase_mask += perturb
        s_plus = self._score(U_in, env_phase, roi_mask)

        self.phase_mask -= 2.0 * perturb
        s_minus = self._score(U_in, env_phase, roi_mask)

        self.phase_mask += perturb  # restore

        grad_est = (s_plus - s_minus) / (2.0 * self.delta)
        self.phase_mask += self.lr * grad_est * perturb

class TessarisGSController(BaseController):
    """
    Tessaris controller (practical/credible version):
      - ROI-weighted Gerchberg–Saxton phase update to push energy into ROI
      - Re-apply each step to lock under drift
      - Limit phase step for stability
    """
    name = "tessaris_gs"
    def __init__(self, N: int, max_phase_step: float = 0.5, inner_iters: int = 3, roi_weight: float = 0.85):
        super().__init__(N)
        self.max_phase_step = float(max_phase_step)
        self.inner_iters = int(inner_iters)
        self.roi_weight = float(roi_weight)

    def step(self, U_in, env_phase, target_I, roi_mask) -> None:
        target_amp = np.sqrt(np.maximum(target_I, 0.0))
        w = self.roi_weight * roi_mask.astype(np.float64)

        for _ in range(self.inner_iters):
            # Forward to focal plane
            U_ap = U_in * np.exp(1j * (self.phase_mask + env_phase))
            U_f = fft_propagate(U_ap)

            cur_amp = np.abs(U_f)
            cur_ph = np.angle(U_f)

            # Scale target amplitude to match current ROI energy (in amp^2)
            eps = 1e-12
            cur_roi = float(np.sum(cur_amp[roi_mask] ** 2)) + eps
            tgt_roi = float(np.sum(target_amp[roi_mask] ** 2)) + eps
            scale = (cur_roi / tgt_roi) ** 0.5
            tgt_amp = target_amp * scale

            # Blend amplitude only in ROI (outside ROI stays as-is)
            mixed_amp = cur_amp + w * (tgt_amp - cur_amp)

            U_f_new = mixed_amp * np.exp(1j * cur_ph)

            # Backprop to aperture plane (inverse of fft_propagate)
            U_ap_new = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(U_f_new)))

            # Enforce known aperture amplitude (classic GS constraint)
            U_ap_new = np.abs(U_in) * np.exp(1j * np.angle(U_ap_new))

            # Desired mask (input is plane wave; drift is env_phase)
            desired_mask = np.angle(U_ap_new) - env_phase

            # Step-limited wrapped phase update
            delta = np.angle(np.exp(1j * (desired_mask - self.phase_mask)))
            delta = np.clip(delta, -self.max_phase_step, self.max_phase_step)
            self.phase_mask = self.phase_mask + delta

        # Keep mask wrapped for numerical hygiene
        self.phase_mask = np.angle(np.exp(1j * self.phase_mask))

def simulate_pe(
    *,
    test_id: str,
    controller: BaseController,
    config: PEConfig,
    U_in: np.ndarray,
    target_I: np.ndarray,
) -> dict:
    rng = np.random.default_rng(config.seed)
    roi_mask = roi_mask_circle(config.N, config.roi_radius)
    env_phase = np.zeros((config.N, config.N), dtype=np.float64)

    rows = []
    prev_S = None
    I = None

    for t in range(config.steps):
        env_phase = env_phase + random_walk_phase(config.N, rng, config.drift_sigma)
        controller.step(U_in, env_phase, target_I, roi_mask)

        U_ap = U_in * np.exp(1j * (controller.phase_mask + env_phase))
        U_f = fft_propagate(U_ap)
        I = intensity_from_field(U_f)

        # Disturbance model (credible toy): focal-plane pointing jitter as a *random walk*.
        # drift_sigma is std-dev of per-step jitter increment in pixels (trackable, not teleporting).
        if t == 0:
            jx = 0
            jy = 0
        else:
            jx = rows[-1].get("_jx", 0)
            jy = rows[-1].get("_jy", 0)

        jx += int(np.round(rng.normal(0.0, config.drift_sigma)))
        jy += int(np.round(rng.normal(0.0, config.drift_sigma)))

        if jx != 0:
            I = np.roll(I, jx, axis=1)
        if jy != 0:
            I = np.roll(I, jy, axis=0)


        eta = roi_efficiency(I, roi_mask)
        m = mse(I, target_I)

        phase_f = np.angle(U_f)
        Cmap = coherence_map(phase_f, win=7)
        C = float(np.mean(Cmap))
        S = phase_entropy_proxy(phase_f)

        divJ = div_info_flux(Cmap, k=1.0)
        dS = 0.0 if prev_S is None else (S - prev_S)
        prev_S = S
        r = divJ + dS
        r_norm = float(np.sqrt(np.mean(r ** 2)))

        rows.append({"step": t, "eta": eta, "mse": m, "coherence": C, "S": S, "r_norm": r_norm, "_jx": jx, "_jy": jy})

    out = {
        "test_id": test_id,
        "controller": controller.name,
        "config": config.__dict__,
        "run_hash": run_hash_for(config, test_id=test_id, controller_name=controller.name),
        "final_phase": controller.phase_mask.astype(np.float32),
        "final_intensity": I.astype(np.float32),
        "target_intensity": target_I.astype(np.float32),
        "metrics": rows,
    }
    return out


def target_tophat_intensity(N: int, radius: int = 18) -> np.ndarray:
    """
    Flat disk (top-hat) target intensity, normalized to sum=1.
    """
    c = N // 2
    yy, xx = np.mgrid[:N, :N]
    mask = (yy - c) ** 2 + (xx - c) ** 2 <= radius ** 2
    T = np.zeros((N, N), dtype=np.float64)
    T[mask] = 1.0
    T = T / (np.sum(T) + 1e-12)
    return T
