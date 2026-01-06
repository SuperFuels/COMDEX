"""
🌌 UCS Geometry Loader
-----------------------------------------------------
Registers symbolic container geometries for:
    * Visualization (GHX)
    * Runtime orchestration (UCSRuntime)
    * Exotic physics containers (Quantum Orb, Vortex, Black Hole, etc.)
    * Symmetry containers (Tetrahedron, Octahedron, Icosahedron, etc.)
    * Capital containers (e.g., Tesseract Central Command)
    * Engine-specific geometries (Field Resonance, Compression Core, Exhaust Nozzle)
"""

import os
import json
from typing import Dict, Any

UCS_TEMPLATE_DIR = "backend/modules/dimensions/universal_container_system/templates/"


# ────────────────────────────────────────────────
# Quiet gate (tests/imports)
# ────────────────────────────────────────────────
_QUIET = os.getenv("TESSARIS_TEST_QUIET", "") == "1"

try:
    # Prefer shared helper if present (optional).
    from backend.utils.quiet import qprint as _qprint  # type: ignore
except Exception:  # pragma: no cover
    _qprint = None  # type: ignore


def _emit(msg: str) -> None:
    if _QUIET:
        return
    if _qprint is not None:
        _qprint(msg)
    else:
        print(msg)


class UCSGeometryLoader:
    def __init__(self):
        # Stores registered geometries by name
        self.geometries: Dict[str, Dict[str, Any]] = {}
        self.register_default_geometries()
        self.register_engine_geometries()  # ✅ Added for QWave Engine stages
        self.auto_register_from_templates()

    # ---------------------------------------------------------
    # 🔑 Geometry Registration
    # ---------------------------------------------------------
    def register_geometry(self, name: str, symbol: str, description: str, capital: bool = False):
        """
        Register a single container geometry into UCS.
        :param name: The container's name (e.g., "Tesseract").
        :param symbol: Unicode glyph or icon associated with geometry.
        :param description: Human-readable explanation of its role.
        :param capital: Boolean indicating if this is a capital (central command) container.
        """
        self.geometries[name] = {
            "symbol": symbol,
            "description": description,
            "capital": capital
        }
        flag = " (CAPITAL)" if capital else ""
        _emit(f"🔗 Registered geometry: {name} {symbol}{flag} - {description}")

    def register_default_geometries(self):
        """
        Registers all core UCS container geometries (Symmetry, Exotic, and Capitals).
        """
        geometries = [
            ("Tetrahedron", "🔻", "Foundational logic unit"),
            ("Octahedron", "🟣", "Duality bridge / logic resolver"),
            ("Icosahedron", "🔶", "Dream state container"),
            ("Dodecahedron", "🔷", "Higher-order mind core"),
            ("Tesseract", "🧮", "Entangled futures container"),
            ("Quantum Orb", "⚛️", "Probabilistic glyph states"),
            ("Vortex", "🌪️", "Chaos/order transformation"),
            ("Black Hole", "🪐", "Compression and entropy sink"),
            ("Torus", "🧿", "Symbolic memory loop"),
            ("DNA Spiral", "🧬", "Mutation lineage growth"),
            ("Fractal Crystal", "🧊", "Infinite zoom fractal logic"),
            ("Memory Pearl", "🧿", "Sequential memory chain"),
            ("Mirror Container", "🪞", "Self-reference and reflection triggers")
        ]
        for name, symbol, desc in geometries:
            self.register_geometry(name, symbol, desc, capital=(name == "Tesseract"))

    # ---------------------------------------------------------
    # 🚀 Engine-Specific Geometries (QWave Stages)
    # ---------------------------------------------------------
    def register_engine_geometries(self):
        """
        Registers specialized geometries required for QWave Engine staging.
        """
        engine_geometries = [
            ("Field Resonance Chamber", "🎛️", "SQI resonance field harmonization for wave stability"),
            ("Compression Core", "🌀", "Extreme density collapse stage for peak energy focusing"),
            ("Plasma Exciter", "🔥", "Plasma agitation and proton spin-up zone"),
            ("Vortex Chamber", "🌪️", "Controlled turbulence and chaos for energy buildup"),
            ("Torus Recycler", "♾️", "Feedback memory loop stabilization stage"),
            ("Wave Exhaust Nozzle", "💨", "Final exhaust stage for wave emission"),
        ]
        for name, symbol, desc in engine_geometries:
            self.register_geometry(name, symbol, desc)

    # ---------------------------------------------------------
    # 🗂 Auto-Detection from Templates
    # ---------------------------------------------------------
    def auto_register_from_templates(self):
        """
        Automatically detect and register container geometries defined in .dc.json templates.
        Supports both generic and capital containers (e.g., Tesseract Central Command).
        """
        if not os.path.exists(UCS_TEMPLATE_DIR):
            _emit(f"⚠️ No UCS templates directory found at {UCS_TEMPLATE_DIR}")
            return

        for file in os.listdir(UCS_TEMPLATE_DIR):
            if file.endswith(".dc.json"):
                path = os.path.join(UCS_TEMPLATE_DIR, file)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    name = data.get("name", file.replace(".dc.json", ""))
                    symbol = data.get("symbol", "❔")
                    desc = data.get("description", "No description provided.")
                    capital = data.get("capital", False)
                    self.register_geometry(name, symbol, desc, capital=capital)
                except Exception as e:
                    _emit(f"⚠️ Failed to load template {file}: {e}")

    # ---------------------------------------------------------
    # 🔍 Geometry Lookup
    # ---------------------------------------------------------
    def get_geometry(self, name: str) -> Dict[str, Any]:
        """
        Retrieve geometry metadata (symbol + description) by container name.
        Falls back to default entry if missing.
        """
        return self.geometries.get(
            name,
            {"symbol": "❔", "description": f"No geometry metadata registered for {name}"}
        )

    def list_geometries(self):
        """Return a dict of all registered geometries."""
        return self.geometries

    # ---------------------------------------------------------
    # 🔄 Runtime Sync Hook
    # ---------------------------------------------------------
    def sync_to_visualizer(self, visualizer):
        """
        Push all registered geometries into GHXVisualizer.
        :param visualizer: An active GHXVisualizer instance.
        """
        for name, meta in self.geometries.items():
            visualizer.register_geometry(
                name,
                meta["symbol"],
                meta["description"]
            )