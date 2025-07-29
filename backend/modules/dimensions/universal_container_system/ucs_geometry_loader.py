"""
🌌 UCS Geometry Loader
-----------------------------------------------------
Registers symbolic container geometries for:
    • Visualization (GHX)
    • Runtime orchestration (UCSRuntime)
    • Exotic physics containers (Quantum Orb, Vortex, Black Hole, etc.)
    • Symmetry containers (Tetrahedron, Octahedron, Icosahedron, etc.)
    • Capital containers (e.g., Tesseract Central Command)
    • Legacy compatibility: mirrors classic container geometry usage
"""

import os
import json
from typing import Dict, Any

UCS_TEMPLATE_DIR = "backend/modules/dimensions/universal_container_system/templates/"

class UCSGeometryLoader:
    def __init__(self):
        # Stores registered geometries by name
        self.geometries: Dict[str, Dict[str, Any]] = {}
        self.register_default_geometries()
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
        print(f"🔗 Registered geometry: {name} {symbol}{flag} – {description}")

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
            # Capital designation only for Tesseract
            self.register_geometry(name, symbol, desc, capital=(name == "Tesseract"))

    # ---------------------------------------------------------
    # 🗂 Auto-Detection from Templates
    # ---------------------------------------------------------
    def auto_register_from_templates(self):
        """
        Automatically detect and register container geometries defined in .dc.json templates.
        Supports both generic and capital containers (e.g., Tesseract Central Command).
        """
        if not os.path.exists(UCS_TEMPLATE_DIR):
            print(f"⚠️ No UCS templates directory found at {UCS_TEMPLATE_DIR}")
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
                    print(f"⚠️ Failed to load template {file}: {e}")

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