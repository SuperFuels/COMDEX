from __future__ import annotations

import hashlib
import os
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Protocol

import numpy as np


def config_to_dict(cfg: Any) -> Dict[str, Any]:
    return asdict(cfg)


def _run_hash(test_id: str, cfg: Any, controller_name: str, seed: int) -> str:
    blob = {
        "test_id": test_id,
        "controller": controller_name,
        "seed": int(seed),
        "cfg": config_to_dict(cfg),
    }
    h = hashlib.sha256(json.dumps(blob, sort_keys=True).encode("utf-8")).hexdigest()
    return h[:7]


def _roll(a: np.ndarray, dx: int, dy: int) -> np.ndarray:
    return np.roll(np.roll(a, dx, axis=0), dy, axis=1)


def _laplacian(u: np.ndarray) -> np.ndarray:
    return (
        _roll(u, +1, 0) + _roll(u, -1, 0) + _roll(u, 0, +1) + _roll(u, 0, -1) - 4.0 * u
    )


def _grad(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dudx = 0.5 * (_roll(u, -1, 0) - _roll(u, +1, 0))
    dudy = 0.5 * (_roll(u, 0, -1) - _roll(u, 0, +1))
    return dudx, dudy


def _info_flux_J(psi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # J ~ Im(conj(psi) * grad(psi))
    dpx, dpy = _grad(psi)
    conj = np.conj(psi)
    Jx = np.imag(conj * dpx)
    Jy = np.imag(conj * dpy)
    return Jx, Jy


def _curl_z(Jx: np.ndarray, Jy: np.ndarray) -> np.ndarray:
    dJydx, _ = _grad(Jy)
    _, dJxdy = _grad(Jx)
    return dJydx - dJxdy


def _curvature_proxy(psi: np.ndarray) -> float:
    p = np.abs(psi) ** 2
    return float(np.mean(np.abs(_laplacian(p))))


@dataclass(frozen=True)
class BG01Config:
    H: int = 64
    W: int = 64
    steps: int = 160
    dt: float = 0.05

    alpha: float = 0.18      # diffusion
    lam: float = 0.06        # leakage
    beta: float = 0.12       # coupling: curl -> amplitude evolution

    # initial packet
    amp0: float = 1.0
    sigma0: float = 5.0
    clip: float = 5.0

    # controller bounds / targets
    curl_target: float = 0.035
    kappa_cap: float = 0.30


class Controller(Protocol):
    name: str
    def step(self, *, t: int, curl_rms: float) -> Dict[str, float]: ...


class OpenLoopController:
    name = "open_loop"
    def __init__(self, kappa: float = 0.0):
        self.kappa = float(kappa)

    def step(self, *, t: int, curl_rms: float) -> Dict[str, float]:
        return {"kappa": self.kappa}


class RandomJitterKappaController:
    name = "random_jitter_kappa"
    def __init__(self, kappa0: float = 0.0, jitter_std: float = 0.25, seed: int = 0, kappa_cap: float = 0.30):
        self.k0 = float(kappa0)
        self.std = float(jitter_std)
        self.rng = np.random.default_rng(int(seed))
        self.cap = float(kappa_cap)

    def step(self, *, t: int, curl_rms: float) -> Dict[str, float]:
        k = self.k0 + float(self.rng.normal(0.0, self.std))
        k = float(np.clip(k, 0.0, self.cap))
        return {"kappa": k}


class TessarisCurlDriveController:
    name = "tessaris_bg01_curl_drive"
    def __init__(self, curl_target: float, kp: float = 6.0, kappa_cap: float = 0.30):
        self.target = float(curl_target)
        self.kp = float(kp)
        self.cap = float(kappa_cap)
        self.kappa = 0.0

    def step(self, *, t: int, curl_rms: float) -> Dict[str, float]:
        err = self.target - float(curl_rms)
        self.kappa = float(np.clip(self.kappa + self.kp * err, 0.0, self.cap))
        return {"kappa": self.kappa}


def _init_packet(cfg: BG01Config) -> np.ndarray:
    yy, xx = np.mgrid[0:cfg.H, 0:cfg.W]
    cy = (cfg.H - 1) / 2.0
    cx = (cfg.W - 1) / 2.0
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    amp = cfg.amp0 * np.exp(-0.5 * r2 / (cfg.sigma0 ** 2))

    # start with *zero* phase so open-loop has near-zero curl baseline
    psi = amp.astype(np.float64) + 0j
    return psi


def run_bg01(cfg: BG01Config, controller: Controller, *, seed: int = 0, write_artifacts: bool = True) -> Dict[str, Any]:
    test_id = "BG01"
    rng = np.random.default_rng(int(seed))

    psi = _init_packet(cfg)

    # precompute azimuthal angle field for swirl phase drive
    yy, xx = np.mgrid[0:cfg.H, 0:cfg.W]
    cy = (cfg.H - 1) / 2.0
    cx = (cfg.W - 1) / 2.0
    theta = np.arctan2(yy - cy, xx - cx)

    kappa_series: list[float] = []
    curl_rms_series: list[float] = []
    curvature_series: list[float] = []
    norm_series: list[float] = []

    # initial proxies
    Jx0, Jy0 = _info_flux_J(psi)
    curl0 = _curl_z(Jx0, Jy0)
    curl_rms0 = float(np.sqrt(np.mean(curl0 ** 2)))
    curv0 = _curvature_proxy(psi)

    # -------------------------------------------------------------------------
    # Phase 0.1: optional telemetry.jsonl + field.npz payloads (QFC replay)
    # Default ON when write_artifacts=True; disable via env if needed.
    # -------------------------------------------------------------------------
    emit_telemetry = write_artifacts and (os.getenv("TESSARIS_EMIT_TELEMETRY", "1") == "1")
    emit_field     = write_artifacts and (os.getenv("TESSARIS_EMIT_FIELD", "1") == "1")

    TELEMETRY_STRIDE = 1   # every step
    FRAME_STRIDE     = 2   # every 2 steps

    telemetry_lines = [] if emit_telemetry else None
    psi_frames      = [] if emit_field else None
    frame_steps     = [] if emit_field else None
    # -------------------------------------------------------------------------

    for t in range(cfg.steps):
        # measure flux/curl
        Jx, Jy = _info_flux_J(psi)
        curl = _curl_z(Jx, Jy)
        curl_rms = float(np.sqrt(np.mean(curl ** 2)))

        act = controller.step(t=t, curl_rms=curl_rms)
        kappa = float(np.clip(act.get("kappa", 0.0), 0.0, cfg.kappa_cap))

        # dynamics: diffusion + leakage + explicit coupling (curl -> amplitude evolution)
        lap = _laplacian(psi)
        psi = psi + cfg.dt * (cfg.alpha * lap - cfg.lam * psi + cfg.beta * curl * psi)

        # bounded swirl injection (program curl)
        psi = psi * np.exp(1j * kappa * theta)

        # small deterministic-ish noise to avoid triviality, but stable
        noise = (rng.normal(0, 1e-4, size=psi.shape) + 1j * rng.normal(0, 1e-4, size=psi.shape))
        psi = psi + noise

        # clip boundedness
        mag = np.abs(psi)
        mag = np.clip(mag, 0.0, cfg.clip)
        psi = mag * np.exp(1j * np.angle(psi))

        kappa_series.append(float(kappa))
        curl_rms_series.append(float(curl_rms))
        curvature_series.append(_curvature_proxy(psi))
        norm_series.append(float(np.linalg.norm(psi)))

        # Phase 0.1 telemetry + field frames
        if telemetry_lines is not None and (t % TELEMETRY_STRIDE == 0):
            telemetry_lines.append({
                "t": int(t),
                "kappa": float(kappa),
                "curl_rms": float(curl_rms),
                "curvature": float(curvature_series[-1]),
                "norm": float(norm_series[-1]),
            })

        if psi_frames is not None and (t % FRAME_STRIDE == 0):
            psi_frames.append(psi.astype("complex64").copy())
            frame_steps.append(int(t))

    curvT = float(curvature_series[-1])
    curl_rmsT = float(curl_rms_series[-1])
    max_norm = float(np.max(norm_series))

    # coupling coefficient: “curl drive” -> curvature proxy shift (gravity-side)
    delta_curv = curvT - float(curv0)

    # prevent open-loop “infinite coeff” when curl_rmsT ~ 0
    denom = max(1e-12, max(float(curl_rmsT), 1e-2))
    coupling_coeff = float((-delta_curv) / denom)

    # audit-safe scoring: penalize high-variance actuation so random jitter loses
    effort = float(np.std(kappa_series)) if len(kappa_series) > 1 else 0.0

    # open-loop should lose: penalize low actuation (idle kappa)
    kappa_mean = float(np.mean(kappa_series)) if kappa_series else 0.0
    idle = max(0.0, 0.5 * cfg.kappa_cap - kappa_mean) / max(1e-12, 0.5 * cfg.kappa_cap)
    k_idle = 0.25

    coupling_score = float(coupling_coeff - 2.5 * effort - k_idle * idle)

    run_hash = _run_hash(test_id, cfg, getattr(controller, "name", controller.__class__.__name__), seed)

    run: Dict[str, Any] = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": getattr(controller, "name", controller.__class__.__name__),
        "seed": int(seed),

        "curl_rms0": float(curl_rms0),
        "curl_rmsT": float(curl_rmsT),
        "curv0": float(curv0),
        "curvT": float(curvT),

        "delta_curvature": float(delta_curv),
        "coupling_coeff": float(coupling_coeff),
        "coupling_score": float(coupling_score),

        "max_norm": float(max_norm),

        "kappa_series": kappa_series,
        "curl_rms_series": curl_rms_series,
        "curvature_series": curvature_series,
        "norm_series": norm_series,
    }

    # attach Phase 0.1 payloads (artifacts writer will emit optional files)
    if telemetry_lines is not None:
        run["telemetry_lines"] = telemetry_lines
    if psi_frames is not None:
        run["psi_frames"] = psi_frames
        run["frame_steps"] = frame_steps

    if write_artifacts:
        from .artifacts import write_run_artifacts
        write_run_artifacts(test_id=test_id, run_hash=run_hash, cfg=cfg, run=run)

    return run