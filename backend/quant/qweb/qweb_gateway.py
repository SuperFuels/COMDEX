# ===============================
# 📁 backend/quant/qweb/qweb_gateway.py
# ===============================
"""
🌐 QWeb Gateway — Resonant API Layer for Q-Series
-------------------------------------------------
Provides a symbolic API bridge between Tessaris core and external clients.

Capabilities:
    • Accept JSON/Photon-language requests
    • Parse QLang or symbolic expressions
    • Execute via QCompilerCore + QTensor
    • Stream symbolic/numeric results to AION or QQC dashboards

All handlers are designed to be embeddable in FastAPI, Flask,
or local notebook contexts.
"""

from __future__ import annotations
import json
import numpy as np
from typing import Dict, Any, Union, Optional

from backend.quant.qlang.qlang_parser import QLangParser
from backend.quant.qtensor.qtensor_field import QTensorField, random_field
from backend.quant.qcompiler.qcompiler_core import QCompilerCore


# ----------------------------------------------------------------------
# Core Gateway
# ----------------------------------------------------------------------
class QWebGateway:
    """Symbolic execution interface over HTTP-like endpoints."""

    def __init__(self):
        self.parser = QLangParser()
        self.compiler = QCompilerCore()

    # --------------------------------------------------------------
    def execute_symbolic(self, payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Accepts symbolic QLang/Photon expression and executes it.

        Args:
            payload: either a raw QLang string or a JSON dict
        Returns:
            Dict[str, Any]: execution output
        """
        if isinstance(payload, str):
            expr = payload
        else:
            expr = payload.get("expression") or payload.get("qlang") or ""

        if not expr.strip():
            return {"error": "Empty expression"}

        # compile and simulate
        graph = self.compiler.compile_expr(expr)
        ψ1, ψ2 = random_field((8, 8)), random_field((8, 8))
        sim = self.compiler.simulate({"ψ1": ψ1, "ψ2": ψ2})
        return {
            "status": "ok",
            "compiled_nodes": len(graph.nodes),
            "simulation": sim,
        }

    # --------------------------------------------------------------
    def handle_request(self, data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Dispatch handler for QWeb JSON protocol.

        Example payloads:
        -----------------
        {"op": "run", "expression": "ψ1 ⊕ ψ2"}
        {"op": "compile", "expression": "ψ1 ↔ ψ2"}
        {"op": "simulate", "tensor_shape": [4,4]}
        """
        try:
            if isinstance(data, str):
                data = json.loads(data)
        except Exception:
            return {"error": "Invalid JSON"}

        op = data.get("op", "run").lower()
        if op == "run":
            return self.execute_symbolic(data)
        elif op == "compile":
            expr = data.get("expression", "")
            g = self.compiler.compile_expr(expr)
            return {"compiled": g.to_dict()}
        elif op == "simulate":
            shape = tuple(data.get("tensor_shape", [4, 4]))
            ψ = random_field(shape)
            ref = random_field(shape)
            res = ψ.interact(ref)
            return {"measurement": res["measurement"], "correlation": res["correlation"]}
        else:
            return {"error": f"Unknown op: {op}"}

    # --------------------------------------------------------------
    def export_result(self, result: Dict[str, Any], path: Optional[str] = None) -> str:
        """
        Save result as .qweb.json for later replay or telemetry logs.
        """
        out = json.dumps(result, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
        return out

    # --------------------------------------------------------------
    def run_test(self) -> Dict[str, Any]:
        """
        Self-test endpoint simulation.
        """
        req = {"op": "run", "expression": "ψ1 ⊕ ψ2 ∇ μ"}
        result = self.handle_request(req)
        return {
            "status": result.get("status"),
            "compiled_nodes": result.get("compiled_nodes"),
            "measurement": result.get("simulation", {}).get("measurement"),
        }


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    qweb = QWebGateway()
    res = qweb.run_test()
    from pprint import pprint
    pprint(res)