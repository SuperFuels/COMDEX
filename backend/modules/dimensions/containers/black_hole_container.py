# ──────────────────────────────────────────────
#  Tessaris • Black Hole Container (Stage 15-B)
#  Specialized ExoticContainer for total compression
#  Simulates gravitational collapse and entropy sink
# ──────────────────────────────────────────────

import math
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from backend.modules.dimensions.containers.exotic_container import ExoticContainer

logger = logging.getLogger(__name__)


class BlackHoleContainer(ExoticContainer):
    """
    ⚫ BlackHoleContainer
    Specialized form of ExoticContainer representing
    high-density symbolic compression (entropy sink).

    Adds:
      • gravitational compression model
      • ψ-κ-T collapse visualization
      • event emission to Morphic / GHX fabric
    """

    def __init__(
        self,
        container_id: Optional[str] = None,
        runtime: Optional[Any] = None,
        horizon_radius: float = 1.0,
    ):
        super().__init__(
            container_id=container_id,
            runtime=runtime,
            geometry="Black Hole Compression Core",
            entropy_mode="sink",
            compression_level="stellar-core",
        )
        self.horizon_radius = horizon_radius
        self.geometry_type = "black_hole"
        logger.info(f"[BlackHoleContainer] Initialized (r={self.horizon_radius})")

    # ──────────────────────────────────────────────
    #  Compression Physics Simulation
    # ──────────────────────────────────────────────
    def apply_gravitational_compression(self, ψ: float, κ: float, T: float) -> Dict[str, float]:
        """
        Simulate gravitational compression of symbolic field.
        Maps ψ-κ-T into entropy collapse + energy emission.
        """
        density = ψ * κ / max(T, 1e-6)
        gravity = 6.674e-11 * density * 1e12  # symbolic scaling
        curvature = math.tanh(gravity)
        collapse_rate = min(1.0, ψ * κ * 1.5)
        logger.debug(f"[BlackHoleContainer] Compression: G={gravity:.4e}, collapse={collapse_rate:.3f}")
        return {
            "gravity": gravity,
            "collapse_rate": collapse_rate,
            "curvature": curvature,
        }

    # ──────────────────────────────────────────────
    #  Override Collapse → full gravitational sink
    # ──────────────────────────────────────────────
    def collapse(self):
        """Override to include gravitational entropy sink visualization."""
        try:
            self.visualize_state("collapsing")
            if self.wave_signature:
                ψ, κ, T = (
                    self.wave_signature.get("ψ", 0.0),
                    self.wave_signature.get("κ", 0.0),
                    self.wave_signature.get("T", 0.0),
                )
                metrics = self.apply_gravitational_compression(ψ, κ, T)
                self._emit_collapse_event(metrics)
            self.compressed_payload = None
            logger.info("[BlackHoleContainer] Collapsed into entropy sink.")
        except Exception as e:
            logger.warning(f"[BlackHoleContainer] Collapse simulation failed: {e}")

    # ──────────────────────────────────────────────
    #  Event emission → Morphic / HUD
    # ──────────────────────────────────────────────
    def _emit_collapse_event(self, metrics: Dict[str, float]):
        try:
            from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
        except Exception:
            def send_codex_ws_event(event_type: str, payload: dict):
                print(f"[Fallback HUD] {event_type} → {payload}")

        payload = {
            "event": "black_hole_collapse",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "container": self.to_dict(),
        }
        import asyncio
        try:
            asyncio.run(send_codex_ws_event("black_hole_collapse", payload))
        except RuntimeError:
            # Event loop already running (e.g., inside HQCE async runtime)
            loop = asyncio.get_event_loop()
            loop.create_task(send_codex_ws_event("black_hole_collapse", payload))
        logger.debug(f"[BlackHoleContainer] Event emitted: {payload}")

    # ──────────────────────────────────────────────
    #  Metadata export
    # ──────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "geometry_type": self.geometry_type,
            "horizon_radius": self.horizon_radius,
        })
        return base