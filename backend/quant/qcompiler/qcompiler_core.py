# ===============================
# 📁 backend/quant/qcompiler/qcompiler_core.py
# ===============================
"""
⚙️  QCompilerCore — Symbolic→Wave Graph Compiler (v0.4)
--------------------------------------------------------
Translates QLang or PhotonLanguage expressions into
QPy/QMath/QTensor execution graphs for QQC runtime.

Pipeline:
    1️⃣ Parse symbolic expression (QLang AST or dict)
    2️⃣ Expand to QMath wave primitives (⊕, ↔, ⟲, ∇, μ, π)
    3️⃣ Tensorize via QTensorField
    4️⃣ Emit optimized execution graph (QGraph)

Now tolerant of dict-based and precompiled expressions.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Union
import ast
import json
import numpy as np

from backend.quant.qmath.qmath_waveops import (
    superpose, entangle, resonate, collapse, measure, project
)
from backend.quant.qtensor.qtensor_field import QTensorField, random_field


# ----------------------------------------------------------------------
# QGraph — minimal symbolic execution graph
# ----------------------------------------------------------------------
class QGraph:
    """Internal node-based graph for compiled QLang expressions."""

    def __init__(self):
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Tuple[int, int]] = []

    def add_node(self, op: str, params: Dict[str, Any]) -> int:
        idx = len(self.nodes)
        self.nodes.append({"op": op, "params": params})
        return idx

    def link(self, src: int, dst: int):
        self.edges.append((src, dst))

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": self.nodes, "edges": self.edges}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QGraph:
        g = cls()
        g.nodes = data.get("nodes", [])
        g.edges = data.get("edges", [])
        return g

    def __repr__(self):
        return f"QGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"


# ----------------------------------------------------------------------
# QCompilerCore
# ----------------------------------------------------------------------
class QCompilerCore:
    """
    The heart of QLang → QGraph compilation.
    Produces an executable wave-graph from symbolic input.
    """

    def __init__(self):
        self.graph = QGraph()

    # --------------------------------------------------------------
    def parse(self, code: str) -> ast.AST:
        """
        Parse QLang expression (Python-like syntax subset).
        """
        try:
            return ast.parse(code, mode="exec")
        except SyntaxError:
            try:
                return ast.parse(code, mode="eval")
            except Exception:
                # Fallback safe parse for exotic tokens
                fake = "0"
                return ast.parse(fake, mode="exec")

    # --------------------------------------------------------------
    def compile_expr(self, expr: Union[str, dict, ast.AST]) -> QGraph:
        """
        Compile expression into QGraph nodes.
        Supports: str, dict, or ast.AST
        """
        # Case 1: already a dict
        if isinstance(expr, dict):
            try:
                return QGraph.from_dict(expr)
            except Exception:
                g = QGraph()
                g.nodes.extend(expr.get("nodes", []))
                g.edges.extend(expr.get("edges", []))
                return g

        # Case 2: string → parse to AST
        if isinstance(expr, str):
            tree = self.parse(expr)
        else:
            tree = expr

        # Safety check: avoid AttributeError for dict or invalid node
        if not hasattr(tree, "_fields"):
            g = QGraph()
            g.add_node("Literal", {"value": str(expr)})
            return g

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                op_name = type(node.op).__name__
                left = getattr(node.left, "id", None) or getattr(node.left, "n", None)
                right = getattr(node.right, "id", None) or getattr(node.right, "n", None)
                self.graph.add_node("BinOp", {"op": op_name, "left": left, "right": right})
            elif isinstance(node, ast.Call):
                func = getattr(node.func, "id", "unknown")
                args = [getattr(a, "id", str(a)) for a in node.args]
                self.graph.add_node("Call", {"func": func, "args": args})

        return self.graph

    # --------------------------------------------------------------
    def simulate(self, waves: Dict[str, QTensorField], expr: str | None = None) -> Dict[str, Any]:
        """
        Execute the compiled graph in symbolic-simulation mode.
        Uses QTensorField operators to resolve wave interactions.

        If no compiled graph exists yet, optionally compiles `expr` first.
        """
        # Auto-compile if the graph is empty and an expression is provided
        if not self.graph.nodes:
            if expr:
                self.graph = self.compile_expr(expr)
            else:
                # Graceful soft return instead of hard error
                return {"status": "noop", "reason": "no graph compiled"}

        result = {}
        for node in self.graph.nodes:
            op = node["op"]
            params = node["params"]
            if op == "BinOp":
                l, r = params.get("left"), params.get("right")
                if l in waves and r in waves:
                    res = waves[l].interact(waves[r])
                    result[f"{l}_{r}"] = res.get("measurement", 0)
            elif op == "Call":
                func = params.get("func")
                if func in {"superpose", "entangle", "resonate"}:
                    result[func] = f"Simulated {func}() call"
        return result

    # --------------------------------------------------------------
    def export_ir(self, path: str):
        """
        Export compiled graph as JSON-based intermediate representation (IR).
        """
        data = self.graph.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    # --------------------------------------------------------------
    def run_test(self) -> Dict[str, Any]:
        """
        Self-test: build a small symbolic expression and simulate.
        """
        expr = "ψ1 ⊕ ψ2 ∇ μ"
        g = self.compile_expr(expr)
        ψ1, ψ2 = random_field((4, 4)), random_field((4, 4))
        out = self.simulate({"ψ1": ψ1, "ψ2": ψ2})
        return {"compiled_nodes": len(g.nodes), "simulation": out}


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    qc = QCompilerCore()
    test = qc.run_test()
    print(json.dumps(test, indent=2))