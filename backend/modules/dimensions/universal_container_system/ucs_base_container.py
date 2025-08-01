class MicroGrid:
    """3D symbolic micro-grid for container memory and glyph placement."""

    def __init__(self, dimensions=(4, 4, 4)):
        self.dimensions = dimensions
        self.grid = [[[None for _ in range(dimensions[2])]
                      for _ in range(dimensions[1])]
                      for _ in range(dimensions[0])]

    def place(self, glyph, x, y, z):
        """Place glyph in grid cell."""
        self.grid[x][y][z] = glyph

    def get(self, x, y, z):
        """Retrieve glyph from grid cell."""
        return self.grid[x][y][z]

    def serialize(self):
        """Convert grid to serializable form."""
        return {
            "dimensions": self.dimensions,
            "cells": [[[cell for cell in plane] for plane in layer] for layer in self.grid],
        }

    def __repr__(self):
        glyphs = sum(1 for layer in self.grid for plane in layer for cell in plane if cell)
        return f"<MicroGrid dims={self.dimensions} glyphs={glyphs}>"


class UCSBaseContainer:
    """
    🧩 UCSBaseContainer
    -----------------------------------------------------
    Shared mechanics for all Universal Container System geometries:
        • Micro-grid layout (spatial symbolic memory)
        • Time dilation per container
        • Glyph storage abstraction
        • SoulLaw enforcement
        • GHX visualization hooks
        • SQI runtime event integration
        • DNA Switch-like feature management (gravity, micro-grid toggling, etc.)
    """

    # 🌐 Global DNA-Switch-Like Features (applies to all containers unless overridden)
    global_features = {
        "micro_grid": True,
        "time_dilation": True,
        "glyph_storage": "Cube",
        "gravity": False,
    }

    def __init__(self, name, geometry, runtime, features=None):
        self.name = name
        self.geometry = geometry
        self.runtime = runtime
        self.features = {**UCSBaseContainer.global_features, **(features or {})}

        # ✅ Initialize core state
        self.micro_grid = MicroGrid() if self.features.get("micro_grid", True) else None
        self.glyph_storage = []  # Glyph storage abstraction (default: Cube)
        self.state = "idle"

        # ✅ Ensure time dilation & gravity are always initialized
        self.time_dilation = 1.0 if self.features.get("time_dilation", True) else None
        self.time_factor = self.time_dilation or 1.0
        self.gravity_force = 0

        print(f"🔧 UCSBaseContainer initialized: {self.name} ({self.geometry}) | Time Dilation: {self.time_dilation}, Micro-grid: {bool(self.micro_grid)}")

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
        if not self.features["micro_grid"]:
            return
        self.micro_grid = MicroGrid(dimensions)
        print(f"🧠 Micro-grid initialized in {self.name}: {dimensions}")

    def place_glyph(self, glyph, x, y, z):
        """Place a glyph into a micro-grid cell."""
        if not self.micro_grid:
            raise RuntimeError(f"❌ Micro-grid not initialized in {self.name}")
        self.micro_grid.place(glyph, x, y, z)
        print(f"📦 Glyph placed at ({x},{y},{z}) in {self.name}")

    # ---------------------------------------------------------
    # ⏳ Time Dilation
    # ---------------------------------------------------------
    def apply_time_dilation(self, factor):
        """Adjust per-container tick speed."""
        if self.features["time_dilation"]:
            self.time_dilation = max(0.1, factor)
            self.time_factor = self.time_dilation
            print(f"⏱ Time dilation applied in {self.name}: x{self.time_dilation}")

    # ---------------------------------------------------------
    # 🌀 Gravity Simulation
    # ---------------------------------------------------------
    def apply_gravity(self, force):
        """Enable simulated gravity force in container."""
        if self.features["gravity"]:
            self.gravity_force = force
            print(f"🌀 Gravity applied in {self.name}: {force}N symbolic")

    # ---------------------------------------------------------
    # 🔒 SoulLaw Enforcement
    # ---------------------------------------------------------
    def enforce_soullaw(self):
        """Enforce SoulLaw validation before execution."""
        self.runtime.soul_law.validate_access({"name": self.name, "geometry": self.geometry})
        print(f"🔒 SoulLaw validated for {self.name}")

    # ---------------------------------------------------------
    # 🎨 GHX Visualization
    # ---------------------------------------------------------
    def visualize_state(self, state):
        """Highlight container state in GHXVisualizer."""
        self.state = state
        if hasattr(self.runtime, "visualizer"):
            self.runtime.visualizer.highlight(self.name)
        print(f"🎨 GHX Visualizer: {self.name} now {state}")

    # ---------------------------------------------------------
    # ⚡ SQI Hooks (Pi GPIO)
    # ---------------------------------------------------------
    def emit_sqi_event(self, event):
        """Emit SQI runtime event tied to container."""
        if hasattr(self.runtime, "sqi"):
            self.runtime.sqi.emit(event, payload={"container": self.name, "state": self.state})
        print(f"⚡ SQI Event Emitted: {event} for {self.name}")

    # ---------------------------------------------------------
    # 🚀 Execute Container
    # ---------------------------------------------------------
    def execute(self):
        """Enforce SoulLaw and trigger visualization/state transitions."""
        self.enforce_soullaw()
        self.visualize_state("running")
        print(f"🚀 Executing {self.name} ({self.geometry})")