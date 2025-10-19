# ===============================
# 📁 backend/quant/qvision/qvision_engine.py
# ===============================
"""
👁️  QVision Engine — Symbolic Vision Bridge
--------------------------------------------
Detects and interprets glyphs, photon traces, and field patterns,
then translates them into QLang / QTensor symbolic structures.

Purpose:
    • Bridge visual inputs → symbolic algebra (QLang)
    • Map photon interference / field patterns → wave operators
    • Provide introspection layer for GHX HUD or AION observers
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any, List, Optional

from backend.quant.qlang.qlang_parser import QLangParser
from backend.quant.qtensor.qtensor_field import QTensorField, random_field


# ----------------------------------------------------------------------
# Core Detection & Mapping
# ----------------------------------------------------------------------
class QVisionEngine:
    """
    Visual-to-symbolic interpreter for wave patterns and glyph fields.
    """

    def __init__(self):
        self.parser = QLangParser()

    # --------------------------------------------------------------
    def detect_glyphs(self, frame: np.ndarray, threshold: float = 0.7) -> List[str]:
        """
        Detect simple symbolic glyphs from 2D intensity field.

        Args:
            frame: 2D numpy array (optical intensity)
            threshold: detection cutoff (relative)
        Returns:
            List[str]: recognized glyphs (⊕, ↔, ⟲, ∇, μ, π)
        """
        mean_intensity = np.mean(frame)
        glyphs: List[str] = []

        # crude heuristic: high-energy clusters imply certain operators
        if mean_intensity > threshold * 0.8:
            glyphs.append("⊕")
        if np.std(frame) > threshold * 0.4:
            glyphs.append("↔")
        if np.max(frame) > threshold:
            glyphs.append("⟲")
        if np.median(frame) < 0.2 * threshold:
            glyphs.append("∇")

        # always include measurement for baseline
        glyphs.append("μ")
        return glyphs

    # --------------------------------------------------------------
    def glyphs_to_qlang(self, glyphs: List[str]) -> str:
        """
        Convert a detected glyph list into a QLang expression.
        """
        if not glyphs:
            return "μ"
        expr = " ψ ".join(glyphs)
        return f"ψ0 {expr}"

    # --------------------------------------------------------------
    def interpret_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Full visual → symbolic interpretation pipeline.
        """
        glyphs = self.detect_glyphs(frame)
        qlang_expr = self.glyphs_to_qlang(glyphs)
        compiled = self.parser.compiler.compile_expr(qlang_expr)
        simulation = self._simulate_from_frame(frame)
        return {
            "glyphs": glyphs,
            "qlang_expr": qlang_expr,
            "compiled_nodes": len(compiled.nodes),
            "simulation": simulation,
        }

    # --------------------------------------------------------------
    def _simulate_from_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Convert frame → QTensorField → symbolic simulation.
        """
        ψ = QTensorField(frame + 0j)
        ref = random_field(frame.shape)
        result = ψ.interact(ref)
        return {
            "correlation": result["correlation"],
            "measurement": result["measurement"],
        }

    # --------------------------------------------------------------
    def run_test(self) -> Dict[str, Any]:
        """Self-test: create synthetic frame → run detection & simulation."""
        frame = np.random.rand(8, 8)
        out = self.interpret_frame(frame)
        return {
            "detected": out["glyphs"],
            "qlang_expr": out["qlang_expr"],
            "corr": out["simulation"]["correlation"],
        }


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    qv = QVisionEngine()
    result = qv.run_test()
    from pprint import pprint
    pprint(result)