# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.1 — Continuous Wave Calculus + Δ-Telemetry
# Unified differential–integral engine with CodexTrace and internal telemetry
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.1.0 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict
import numpy as np
import time

# ──────────────────────────────────────────────────────────────
# Telemetry Integration Layer
# ──────────────────────────────────────────────────────────────
try:
    from backend.modules.codex.codex_trace import record_event
    TELEMETRY_MODE = "CodexTrace"
except ImportError:
    try:
        from backend.symatics.core.telemetry_channel import record_event
        TELEMETRY_MODE = "SymaticsChannel"
    except ImportError:
        def record_event(event_type: str, **fields):
            """Fallback no-op if telemetry unavailable."""
            return None
        TELEMETRY_MODE = "None"


# ──────────────────────────────────────────────────────────────
# Fundamental Differential Operators (Wave Form)
# ──────────────────────────────────────────────────────────────
def d_dt(field_t: np.ndarray, field_t1: np.ndarray, dt: float = 1.0) -> np.ndarray:
    """Temporal derivative ∂ψ/∂t."""
    dfield = (field_t1 - field_t) / dt
    try:
        record_event("d_dt", mean=float(np.mean(dfield)), telemetry_mode=TELEMETRY_MODE)
    except Exception:
        pass
    return dfield


def laplacian(field: np.ndarray) -> np.ndarray:
    """∇²ψ — discrete Laplacian operator.
    Handles both 1D and 2D fields automatically.
    """
    grads = np.gradient(field)

    # Handle 1D and 2D cases dynamically
    if isinstance(grads, (list, tuple)):
        if len(grads) == 1:
            # 1D case: ∇²ψ = ∂²ψ/∂x²
            gx = grads[0]
            lap = np.gradient(gx)
        elif len(grads) == 2:
            # 2D case: ∇²ψ = ∂²ψ/∂x² + ∂²ψ/∂y²
            gx, gy = grads
            gxx = np.gradient(gx, axis=0)
            gyy = np.gradient(gy, axis=1)
            lap = gxx + gyy
        else:
            raise ValueError(f"Unsupported gradient dimensionality: {len(grads)}")
    else:
        # Fallback: treat as 1D
        gx = grads
        lap = np.gradient(gx)

    # Optional: flatten nested gradients for consistency
    lap = np.array(lap)

    # Telemetry emission
    try:
        record_event("laplacian", mean=float(np.mean(lap)), telemetry_mode=TELEMETRY_MODE)
    except Exception:
        pass

    return lap


def integrate_wave(field: np.ndarray, dx: float = 1.0, dy: float = 1.0) -> float:
    """∫ψ dψ — symbolic area integral (approximated)."""
    integral = np.sum(field) * dx * dy
    try:
        record_event("integrate_wave", value=float(integral), telemetry_mode=TELEMETRY_MODE)
    except Exception:
        pass
    return float(integral)


# ──────────────────────────────────────────────────────────────
# Resonant Differential Dynamics
# ──────────────────────────────────────────────────────────────
def evolve_wavefield(ψ_t: np.ndarray, λ_t: np.ndarray, dt: float = 1.0, damping: float = 0.01) -> np.ndarray:
    """
    Time-step evolution of ψ-field under λ influence:
        ∂ψ/∂t = λ ∇²ψ − γ ψ
    Returns ψ_{t+Δt}.
    """
    lap = laplacian(ψ_t)
    dψ = λ_t * lap - damping * ψ_t
    ψ_next = ψ_t + dt * dψ
    try:
        record_event(
            "evolve_wavefield",
            mean=float(np.mean(ψ_next)),
            damping=damping,
            telemetry_mode=TELEMETRY_MODE,
        )
    except Exception:
        pass
    return ψ_next


# ──────────────────────────────────────────────────────────────
# High-Level Wave Calculus Engine
# ──────────────────────────────────────────────────────────────
class WaveDiffEngine:
    """
    Continuous symbolic calculus engine for ψ and λ fields.
    Evolves wavefields, computes derivatives, and evaluates continuity.
    """

    def __init__(self):
        self.fields: Dict[str, np.ndarray] = {}
        self.energy_log = []
        self.last_time = time.time()

    def register_field(self, name: str, field: np.ndarray):
        """Register a symbolic ψ or λ field."""
        self.fields[name] = field

    def step(self, ψ_name: str, λ_name: str, dt: float = 1.0, damping: float = 0.01) -> np.ndarray:
        """Advance ψ_name using λ_name over one Δt step."""
        ψ = self.fields[ψ_name]
        λ = self.fields[λ_name]
        ψ_next = evolve_wavefield(ψ, λ, dt=dt, damping=damping)
        self.fields[ψ_name] = ψ_next

        # Energy and coherence telemetry
        energy = self.measure_energy(ψ_name)
        coherence = self.coherence_index(ψ_name)
        now = time.time()
        dE_dt = (energy - self.energy_log[-1]) / (now - self.last_time) if self.energy_log else 0.0
        self.energy_log.append(energy)
        self.last_time = now

        try:
            record_event(
                "wave_step",
                energy=energy,
                dE_dt=dE_dt,
                coherence=coherence,
                lambda_mean=float(np.mean(λ)),
                telemetry_mode=TELEMETRY_MODE,
                tags=[ψ_name],
            )
        except Exception:
            pass

        return ψ_next

    def measure_energy(self, ψ_name: str) -> float:
        ψ = self.fields[ψ_name]
        energy = float(np.sum(ψ ** 2))
        try:
            record_event("wave_energy", value=energy, telemetry_mode=TELEMETRY_MODE)
        except Exception:
            pass
        return energy

    def coherence_index(self, ψ_name: str) -> float:
        """Compute coherence index C = exp(-||∇ψ||).
        Handles both 1D and 2D ψ fields.
        """
        ψ = self.fields[ψ_name]
        grads = np.gradient(ψ)

        # Handle 1D or 2D cases automatically
        if isinstance(grads, (list, tuple)):
            if len(grads) == 1:
                grad_mag = np.linalg.norm(grads[0])
            elif len(grads) == 2:
                gx, gy = grads
                grad_mag = np.sqrt(np.sum(gx**2 + gy**2))
            else:
                raise ValueError(f"Unsupported ψ dimensionality: {len(grads)}")
        else:
            grad_mag = np.linalg.norm(grads)

        # Coherence index bounded in [0,1]
        coherence = float(np.exp(-grad_mag))
        coherence = max(0.0, min(coherence, 1.0))

        # Telemetry emission (if available)
        try:
            record_event(
                "coherence_index",
                value=coherence,
                grad_magnitude=float(grad_mag),
                telemetry_mode=TELEMETRY_MODE,
            )
        except Exception:
            pass

        return coherence


# ──────────────────────────────────────────────────────────────
# Self-Test Diagnostic
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[Telemetry mode: {TELEMETRY_MODE}]")
    engine = WaveDiffEngine()
    ψ = np.outer(np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    λ = np.ones_like(ψ) * 0.5
    engine.register_field("ψ", ψ)
    engine.register_field("λ", λ)
    for _ in range(3):
        ψ = engine.step("ψ", "λ", dt=0.1)
        print(f"Energy={engine.measure_energy('ψ'):.4f}, Coherence={engine.coherence_index('ψ'):.4f}")