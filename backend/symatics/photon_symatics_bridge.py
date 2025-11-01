# =========================================================
# 📁 backend/symatics/photon_symatics_bridge.py
# =========================================================
"""
⚛ Photon-Symatics Bridge - SRK-15
Bidirectional interface between Symatics Algebra and Photon Algebra Runtime.

Executes symbolic operators (⊕, ↔, ⟲, ∇, μ) in the photonic domain while keeping
a structured trace suitable for front-end visualization.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List

from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime
from backend.symatics.operators import OPS


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

OP_SYMBOL_TO_NAME = {
    "⊕": "superpose",
    "↔": "entangle",
    "⟲": "resonate",
    "∇": "collapse",
    "μ": "measure",
}

def op_color(op_symbol: str) -> str:
    return {
        "⊕": "#06B6D4",  # cyan
        "↔": "#D946EF",  # fuchsia
        "⟲": "#EAB308",  # yellow
        "∇": "#EF4444",  # red
        "μ": "#FFFFFF",  # white
    }.get(op_symbol, "#8B5CF6")  # fallback indigo


class _SymaticOperatorProxy:
    """
    Adapter to expose Symatics OPS via .apply() interface if needed.
    """
    def __init__(self, ops_dict):
        self.ops = ops_dict

    def apply(self, op_symbol: str, *args, **kwargs):
        op = self.ops.get(op_symbol)
        if not op:
            raise ValueError(f"Unknown symbolic operator: {op_symbol}")
        if hasattr(op, "impl"):
            return op.impl(*args, **kwargs)
        elif callable(op):
            return op(*args, **kwargs)
        raise TypeError(f"Operator {op_symbol} is not callable")


# ────────────────────────────────────────────────────────────────
# Bridge
# ────────────────────────────────────────────────────────────────

class PhotonSymaticsBridge:
    """
    Routes glyph-plane operations to Photon runtime, and everything else to Symatics.
    Produces UI-friendly traces for the PhotonLens overlay.
    """

    def __init__(self):
        self.photon_runtime = PhotonAlgebraRuntime()

    # ---------- Domain routing ----------
    def resolve_operator(self, op_symbol: str):
        if op_symbol in OP_SYMBOL_TO_NAME:
            return self.photon_runtime  # photonic
        return _SymaticOperatorProxy(OPS)  # symatic fallback

    # ---------- Parsing raw glyph lines ----------
    def parse_raw_photon_line(self, src: str) -> Dict[str, Any]:
        """
        Accepts a single glyph line like: '💡 = 🌊 ⊕ 🌀'
        Returns a small descriptor for trace (no Photon runtime schema here).
        """
        src = (src or "").strip()
        if not src:
            return {"type": "empty", "line": src}

        left, right = None, src
        if "=" in src:
            left, right = [s.strip() for s in src.split("=", 1)]

        # find first supported operator
        op_symbol = next((s for s in OP_SYMBOL_TO_NAME.keys() if s in right), None)

        if op_symbol:
            parts = [p.strip() for p in re.split(rf"\s*{re.escape(op_symbol)}\s*", right) if p.strip()]
            return {
                "type": "operation",
                "assign": left,
                "op_symbol": op_symbol,
                "op_name": OP_SYMBOL_TO_NAME[op_symbol],
                "args": parts,
                "raw": src,
            }

        return {"type": "literal", "assign": left, "value": right, "raw": src}

    # ---------- Build a valid Photon capsule ----------
    def _build_capsule_from_line(self, line: str) -> Dict[str, Any]:
        """
        Photon runtime expects a capsule schema. Keep it minimal & valid.
        """
        return {
            "name": "bridge_inline",
            "glyphs": [line],   # hand the exact glyph line to the runtime
            # add more fields if your runtime supports them (metadata, seed, etc.)
        }

    # ---------- Public: execute a multi-line glyph block ----------
    async def execute_raw(self, source: str) -> Dict[str, Any]:
        """
        Execute raw glyph-plane Photon code through the bridge pipeline.

        - Parses each non-empty line
        - For lines containing supported ops (⊕, ↔, ⟲, ∇, μ), builds a valid capsule
          and calls PhotonAlgebraRuntime.execute(capsule)
        - Returns a visualization-friendly trace with op + color fields
        """
        lines = [l.strip() for l in (source or "").splitlines() if l.strip()]
        results: List[Dict[str, Any]] = []

        for line in lines:
            desc = self.parse_raw_photon_line(line)

            if desc.get("type") != "operation":
                # Non-operational lines are skipped (could be assignments with no op)
                results.append({
                    "input": line,
                    "status": "skipped",
                    "note": "no supported operator found",
                })
                continue

            op_symbol = desc["op_symbol"]
            color = op_color(op_symbol)
            target = self.resolve_operator(op_symbol)

            try:
                # ✅ Build a Photon capsule the runtime accepts
                capsule = self._build_capsule_from_line(line)
                # Execute in photonic domain
                exec_result = await target.execute(capsule)

                results.append({
                    "input": line,
                    "op": op_symbol,
                    "color": color,
                    "status": "ok",
                    "result": exec_result,
                })
            except Exception as e:
                results.append({
                    "input": line,
                    "op": op_symbol,
                    "color": "#DC2626",
                    "status": "error",
                    "error": str(e),
                })

        return {"ok": True, "count": len(results), "results": results}