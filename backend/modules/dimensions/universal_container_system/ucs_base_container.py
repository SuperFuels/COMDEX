import logging
from typing import Any, Dict, Optional, Tuple

# ✅ Optional hub/link helpers (safe fallbacks)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):  # no-op if helper not present
        pass

logger = logging.getLogger(__name__)

_ucsb_checked = set()
_ucsb_hub_connected = set()


class MicroGrid:
    """3D symbolic micro-grid for container memory and glyph placement."""

    def __init__(self, dimensions: Tuple[int, int, int] = (4, 4, 4)):
        self.dimensions = tuple(int(x) for x in dimensions)
        X, Y, Z = self.dimensions
        self.grid = [[[None for _ in range(Z)] for _ in range(Y)] for _ in range(X)]

    def _in_bounds(self, x: int, y: int, z: int) -> bool:
        X, Y, Z = self.dimensions
        return 0 <= x < X and 0 <= y < Y and 0 <= z < Z

    def place(self, glyph: Any, x: int, y: int, z: int) -> None:
        """Place glyph in grid cell."""
        x, y, z = int(x), int(y), int(z)
        if not self._in_bounds(x, y, z):
            raise IndexError(f"MicroGrid.place out of bounds: {(x, y, z)} dims={self.dimensions}")
        self.grid[x][y][z] = glyph

    def get(self, x: int, y: int, z: int) -> Any:
        """Retrieve glyph from grid cell."""
        x, y, z = int(x), int(y), int(z)
        if not self._in_bounds(x, y, z):
            return None
        return self.grid[x][y][z]

    def serialize(self) -> dict:
        """Convert grid to serializable form."""
        return {
            "dimensions": self.dimensions,
            "cells": [[[cell for cell in plane] for plane in layer] for layer in self.grid],
        }

    def __repr__(self) -> str:
        glyphs = sum(1 for layer in self.grid for plane in layer for cell in plane if cell)
        return f"<MicroGrid dims={self.dimensions} glyphs={glyphs}>"


class UCSBaseContainer:
    """
    🧩 UCSBaseContainer
    -----------------------------------------------------
    Shared mechanics for all Universal Container System geometries:
        * Micro-grid layout (spatial symbolic memory)
        * Time dilation per container
        * Glyph storage abstraction
        * SoulLaw enforcement
        * GHX visualization hooks
        * SQI runtime event integration
        * DNA Switch-like feature management (gravity, micro-grid toggling, etc.)
    """

    global_features = {
        "micro_grid": True,
        "time_dilation": True,
        "glyph_storage": "Cube",
        "gravity": False,
    }

    def __init__(self, name, geometry, runtime, features=None, container_type=None):
        self.name = name
        self.geometry = geometry
        self.runtime = runtime
        self.container_type = container_type

        self.features = {**UCSBaseContainer.global_features, **(features or {})}

        # ✅ Initialize core state
        self.micro_grid = MicroGrid() if self.features.get("micro_grid", True) else None
        self.glyph_storage = []
        self.state = "idle"
        self.metadata: Dict[str, Any] = {}

        # ✅ Ensure time dilation & gravity are always initialized
        self.time_dilation = 1.0 if self.features.get("time_dilation", True) else None
        self.time_factor = self.time_dilation or 1.0
        self.gravity_force = 0

        print(
            f"🔧 UCSBaseContainer initialized: {self.name} ({self.geometry}) | "
            f"Time Dilation: {self.time_dilation}, Micro-grid: {bool(self.micro_grid)}"
        )

        # ✅ idempotently connect every base container to hub
        try:
            self._connect_to_hub()
        except Exception:
            pass

    # ---------------------------------------------------------
    # 🧩 DNA Switch-like Feature Management
    # ---------------------------------------------------------
    def enable_feature(self, feature):
        self.features[feature] = True
        print(f"✅ Feature enabled: {feature} for {self.name}")

    def disable_feature(self, feature):
        self.features[feature] = False
        print(f"🚫 Feature disabled: {feature} for {self.name}")

    @classmethod
    def set_global_feature(cls, feature, value):
        cls.global_features[feature] = value
        print(f"🌐 Global feature updated: {feature} = {value}")

    # ---------------------------------------------------------
    # 🧠 Micro-Grid Logic
    # ---------------------------------------------------------
    def init_micro_grid(self, dimensions=(4, 4, 4)):
        """Initialize symbolic micro-grid (3D memory lattice)."""
        if not self.features.get("micro_grid", True):
            return
        self.micro_grid = MicroGrid(dimensions)
        print(f"🧠 Micro-grid initialized in {self.name}: {dimensions}")

    def place_glyph(self, glyph, x, y, z):
        """Place a glyph into a micro-grid cell."""
        if not self.micro_grid:
            raise RuntimeError(f"❌ Micro-grid not initialized in {self.name}")
        self.micro_grid.place(glyph, x, y, z)
        print(f"📦 Glyph placed at ({x},{y},{z}) in {self.name}")

        # --- Optional: Microgrid HUD registration (best-effort; no impact on core flow)
        try:
            from backend.modules.glyphos.microgrid_index import MicrogridIndex
            MG = getattr(MicrogridIndex, "_GLOBAL", None) or MicrogridIndex()
            MicrogridIndex._GLOBAL = MG
            MG.register_glyph(
                int(x) % 16, int(y) % 16, int(z) % 16,
                glyph=str(glyph),
                metadata={
                    "type": "glyph",
                    "container": getattr(self, "id", None) or self.name,
                    "tags": ["ucs_base", "place_glyph"],
                    "energy": 1.0,
                },
            )
        except Exception:
            pass

    # ---------------------------------------------------------
    # ⏳ Time Dilation
    # ---------------------------------------------------------
    def apply_time_dilation(self, factor):
        """Adjust per-container tick speed."""
        if self.features.get("time_dilation", True):
            self.time_dilation = max(0.1, float(factor))
            self.time_factor = self.time_dilation
            print(f"⏱ Time dilation applied in {self.name}: x{self.time_dilation}")

    # ---------------------------------------------------------
    # 🌀 Gravity Simulation
    # ---------------------------------------------------------
    def apply_gravity(self, force):
        """Enable simulated gravity force in container."""
        if self.features.get("gravity", False):
            self.gravity_force = force
            print(f"🌀 Gravity applied in {self.name}: {force}N symbolic")

    # ---------------------------------------------------------
    # 🔒 SoulLaw Enforcement
    # ---------------------------------------------------------
    def enforce_soullaw(self):
        """Enforce SoulLaw validation before execution (only once per container id/name)."""
        key = getattr(self, "id", None) or self.name
        if key in _ucsb_checked:
            return

        # runtime might not have soul_law in tests/CLI
        try:
            soul = getattr(self.runtime, "soul_law", None)
            if soul and hasattr(soul, "validate_access"):
                soul.validate_access({"id": key, "name": self.name, "geometry": self.geometry})
        except Exception as e:
            logger.warning(f"[UCSBaseContainer] SoulLaw validate failed for {key}: {e}")
            raise

        _ucsb_checked.add(key)
        print(f"🔒 SoulLaw validated once for {key}")

    # ---------------------------------------------------------
    # 🎨 GHX Visualization
    # ---------------------------------------------------------
    def visualize_state(self, state):
        """Highlight container state in GHXVisualizer."""
        self.state = state
        if hasattr(self.runtime, "visualizer"):
            try:
                self.runtime.visualizer.highlight(self.name)
            except Exception:
                pass
        print(f"🎨 GHX Visualizer: {self.name} now {state}")

    # ---------------------------------------------------------
    # ⚡ SQI Hooks (Pi GPIO)
    # ---------------------------------------------------------
    def emit_sqi_event(self, event):
        """Emit SQI runtime event tied to container."""
        try:
            sqi = getattr(self.runtime, "sqi", None)
            if sqi and hasattr(sqi, "emit"):
                sqi.emit(event, payload={"container": self.name, "state": self.state})
        except Exception:
            pass
        print(f"⚡ SQI Event Emitted: {event} for {self.name}")

    # ---------------------------------------------------------
    # 🚀 Execute Container
    # ---------------------------------------------------------
    def execute(self):
        """Enforce SoulLaw and trigger visualization/state transitions."""
        self.enforce_soullaw()
        self.visualize_state("running")
        print(f"🚀 Executing {self.name} ({self.geometry})")

    # ---------------------------------------------------------
    # 🧭 Hub hookup (idempotent)
    # ---------------------------------------------------------
    def _connect_to_hub(self, hub_id: str = "tesseract_hq") -> None:
        """
        Register/connect this container into the HQ graph. Safe to call many times.
        """
        container_id = getattr(self, "id", None) or self.name
        if container_id in _ucsb_hub_connected:
            return

        doc: Dict[str, Any] = {
            "id": container_id,
            "name": self.name,
            "geometry": self.geometry,
            "type": self.container_type or "container",
            "meta": {"address": f"ucs://local/{container_id}#container"},
        }
        connect_container_to_hub(doc, hub_id=hub_id)
        _ucsb_hub_connected.add(container_id)

    # ---------------------------------------------------------
    # ✅ Dict Export for Runtime Injection / Registry
    # ---------------------------------------------------------
    def to_dict(self) -> dict:
        """Export container to dict for runtime registration."""
        container_id = getattr(self, "id", None) or self.name
        return {
            "id": container_id,
            "name": self.name,
            "type": self.container_type or "container",
            "geometry": self.geometry,
            "meta": {"address": f"ucs://local/{container_id}#container"},
            "atoms": getattr(self, "atoms", {}),
            "features": self.features,
            "runtime": {
                "time_dilation": self.time_dilation,
                "micro_grid": self.micro_grid.serialize() if self.micro_grid else None,
            },
            "state": self.state,
        }