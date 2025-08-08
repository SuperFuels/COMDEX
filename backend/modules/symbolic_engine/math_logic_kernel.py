# 📁 backend/modules/symbolic_engine/math_logic_kernel.py

import re
from typing import List, Dict, Any, Optional, Tuple

from sympy import Symbol, sympify, Eq, simplify, And, Or, Not, Implies, Equivalent
from sympy.logic.boolalg import Boolean
from sympy.core.relational import Relational
from sympy.core.sympify import SympifyError

from backend.modules.symbolic_engine.math_kernel import MathKernel
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.symbolic_engine.symbolic_utils import parse_logical_operators
from backend.modules.sqi.sqi_tessaris_bridge import SQIBridge
from backend.modules.sqi.qglyph_generator import generate_qglyph_from_string


class MathLogicKernel:
    def __init__(self, container_id: Optional[str] = None):
        self.math_kernel = MathKernel()
        self.kg_writer = KnowledgeGraphWriter()
        self.sqi_bridge = SQIBridge()
        self.container_id = container_id or "math_kernel_default"

    def prove_theorem(self, assumptions: List[str], conclusion: str) -> Dict[str, Any]:
        """
        Attempts to prove a conclusion from a set of assumptions.
        If successful, injects into the KG with type ⟦theorem⟧.
        """
        try:
            parsed_assumptions = [parse_logical_operators(a) for a in assumptions]
            parsed_conclusion = parse_logical_operators(conclusion)

            # Combine assumptions logically
            combined = And(*parsed_assumptions)
            implication = Implies(combined, parsed_conclusion)

            simplified = simplify(implication)
            qglyph = generate_qglyph_from_string(str(implication))

            result = {
                "input": str(implication),
                "simplified": str(simplified),
                "qglyph": qglyph
            }

            if simplified == True:
                result["status"] = "✅ Proven"
                self._inject_fact(conclusion, assumptions, kind="⟦theorem⟧", proof=str(implication))
            else:
                result["status"] = "❌ Unproven"

            self._log_sqi_event(conclusion, assumptions, str(implication), result["status"])
            return result
        except Exception as e:
            return {"status": "❌ Error", "error": str(e)}

    def detect_contradiction(self, statements: List[str]) -> Dict[str, Any]:
        """
        Detects if a set of logical statements leads to contradiction.
        """
        try:
            expressions = [parse_logical_operators(s) for s in statements]
            combined = And(*expressions)
            simplified = simplify(combined)

            if simplified == False:
                self._inject_fact("⊥", statements, kind="⟦contradiction⟧")
                return {
                    "status": "❌ Contradiction Detected",
                    "combined": str(combined),
                    "simplified": str(simplified)
                }
            return {
                "status": "✅ No Contradiction",
                "combined": str(combined),
                "simplified": str(simplified)
            }
        except Exception as e:
            return {"status": "❌ Error", "error": str(e)}

    def assert_axiom(self, expression: str, label: Optional[str] = None) -> Dict[str, str]:
        """
        Stores an axiom (assumed true) into the KG and container.
        """
        try:
            parsed = parse_logical_operators(expression)
            self._inject_fact(expression, [], kind="⟦axiom⟧", label=label)
            return {"status": "✅ Axiom Stored", "expression": str(parsed)}
        except Exception as e:
            return {"status": "❌ Failed", "error": str(e)}

    def rewrite_equivalence(self, expr1: str, expr2: str) -> Dict[str, str]:
        """
        Checks if expr1 and expr2 are logically equivalent.
        """
        try:
            p1 = parse_logical_operators(expr1)
            p2 = parse_logical_operators(expr2)
            equivalence = Equivalent(p1, p2)
            simplified = simplify(equivalence)
            return {
                "expr1": str(p1),
                "expr2": str(p2),
                "equivalent": str(simplified),
                "status": "✅ Equivalent" if simplified else "❌ Not Equivalent"
            }
        except Exception as e:
            return {"status": "❌ Error", "error": str(e)}

    def _inject_fact(
        self,
        expression: str,
        sources: List[str],
        kind: str = "⟦fact⟧",
        proof: Optional[str] = None,
        label: Optional[str] = None
    ):
        """
        Sends a glyph-based fact into the Knowledge Graph.
        """
        metadata = {
            "type": kind,
            "sources": sources,
            "container_id": self.container_id,
            "proof": proof,
            "label": label
        }
        self.kg_writer.write_fact(expression, metadata)

    def _log_sqi_event(self, conclusion: str, assumptions: List[str], implication: str, status: str):
        self.sqi_bridge.log_trace({
            "type": "symbolic_proof_attempt",
            "container": self.container_id,
            "status": status,
            "input": conclusion,
            "assumptions": assumptions,
            "implication": implication
        })