# 📁 backend/modules/symbolic_spreadsheet/wavescope_v2_adapter.py
"""
🌊 WaveScope v2 Adapter
Deferred import for GlyphCell to avoid circular dependencies.
Bridges AtomSheet runtime with QCompilerCore simulate().
"""

from __future__ import annotations
import logging
from backend.quant.qcompiler.qcompiler_core import QCompilerCore
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
from backend.quant.ghx.ghx_feedback_bridge import GHXFeedbackBridge

logger = logging.getLogger(__name__)

class WaveScopeV2:
    def __init__(self):
        self.compiler = QCompilerCore()
        self.telemetry = ResonanceTelemetry()
        self.ghx = GHXFeedbackBridge()

    def execute_cell(self, expr: str):
        try:
            graph = self.compiler.compile_expr(expr)
            ψ1 = ψ2 = None  # cells may supply actual tensors later
            result = self.compiler.simulate({"ψ1": ψ1, "ψ2": ψ2}, expr=expr)
            telem = self.telemetry.emit()
            packet = {"expr": expr, "result": result, "telemetry": telem}
            self.ghx.push(packet)
            logger.info(f"🌊 WaveScopeV2 executed: {expr}")
            return packet
        except Exception as e:
            logger.exception(f"[WaveScopeV2] Execution failed: {e}")
            return {"error": str(e)}