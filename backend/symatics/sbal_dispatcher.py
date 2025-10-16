"""
Tessaris • SBAL Dispatcher (Substrate Bridge Abstraction Layer)
---------------------------------------------------------------
Routes symbolic or photonic operations to the correct substrate handler:
  • Digital   → CPU/GPU simulation backends
  • Optical   → LightWave engine
  • RF        → Resonance field oscillators
  • Laser     → Quantum coherence amplifiers

Each substrate module registers itself here with a handler callable or class.
QQC and Symatics engines dispatch through this bridge to ensure
cross-phase synchronization consistency.
"""

from typing import Any, Callable, Dict
import logging

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────
# 🔗 Substrate Registry
# ────────────────────────────────────────────────
_SUBSTRATE_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_substrate(name: str, handler: Callable[..., Any]) -> None:
    """
    Register a substrate handler (function or class).

    Args:
        name: Identifier (e.g. "digital", "optical", "rf", "laser").
        handler: Callable that accepts a payload or command dict.
    """
    name = name.lower()
    _SUBSTRATE_REGISTRY[name] = handler
    logger.info(f"[SBAL] Registered substrate → {name}")


def get_substrate(name: str) -> Callable[..., Any] | None:
    """Retrieve a substrate handler by name."""
    return _SUBSTRATE_REGISTRY.get(name.lower())


def dispatch_to_substrate(name: str, payload: Dict[str, Any]) -> Any:
    """
    Route an operation to the selected substrate backend.

    Args:
        name: substrate name ("digital", "optical", etc.)
        payload: operation or event data

    Returns:
        Substrate handler return value, or None if not found.
    """
    handler = get_substrate(name)
    if not handler:
        logger.warning(f"[SBAL] No handler registered for substrate '{name}'")
        return None

    try:
        result = handler(payload)
        logger.debug(f"[SBAL] → Dispatched to {name} substrate successfully.")
        return result
    except Exception as e:
        logger.error(f"[SBAL] ❌ Dispatch failed for {name}: {e}")
        return None


def list_substrates() -> Dict[str, str]:
    """Return available substrate handlers (names + repr)."""
    return {k: repr(v) for k, v in _SUBSTRATE_REGISTRY.items()}


# ────────────────────────────────────────────────
# 🧩 Example Default Handlers (stubs)
# ────────────────────────────────────────────────
def _default_digital_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"[SBAL:DIGITAL] Processing payload → {payload}")
    return {"status": "ok", "backend": "digital"}


def _default_optical_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"[SBAL:OPTICAL] LightWave simulated → {payload}")
    return {"status": "ok", "backend": "optical"}


# Register baseline handlers
register_substrate("digital", _default_digital_handler)
register_substrate("optical", _default_optical_handler)

logger.info("[SBAL] Initialized base substrates (digital, optical).")