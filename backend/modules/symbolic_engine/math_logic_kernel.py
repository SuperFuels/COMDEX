import re
from typing import List, Dict, Any, Optional, Tuple

from backend.quant.qpy.compat_sympy_logic import qand, qor, qnot, qimplies, qequiv
from sympy.logic.boolalg import Boolean
from sympy.core.relational import Relational
from sympy.core.sympify import SympifyError


from backend.modules.symbolic_engine.math_kernel import MathKernel
from backend.modules.symbolic_engine.symbolic_utils import parse_logical_operators
from backend.modules.sqi.sqi_tessaris_bridge import SQITessarisBridge
from backend.modules.sqi.qglyph_utils import generate_qglyph_from_string
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.symbolic.codex_ast_parser import parse_codexlang_to_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph


class MathLogicKernel:
    def __init__(self, container_id: Optional[str] = None):
        self.math_kernel = MathKernel()
        self.container_id = container_id
        self.kg_writer = get_kg_writer()
        self.sqi_bridge = SQITessarisBridge()
        self.rewriter = CodexLangRewriter()

    def prove_theorem(
        self,
        assumptions: List[str],
        conclusion: str,
        raw_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempts to prove a conclusion from a set of assumptions.
        If successful, injects into the KG with type ⟦theorem⟧.
        """
        try:
            parsed_assumptions = [parse_logical_operators(a) for a in assumptions]
            parsed_conclusion = parse_logical_operators(conclusion)

            combined = And(*parsed_assumptions)
            implication = Implies(combined, parsed_conclusion)
            simplified = simplify(implication)

            qglyph = generate_qglyph_from_string(str(implication))
            codexlang, ast, glyphs = self._codex_pipeline(raw_input or conclusion)

            result = {
                "input": str(implication),
                "simplified": str(simplified),
                "qglyph": qglyph,
                "codexlang": codexlang,
                "ast": ast,
                "glyphs": glyphs,
            }

            if simplified is True:
                result["status"] = "✅ Proven"
                self._inject_fact(
                    conclusion,
                    assumptions,
                    kind="⟦theorem⟧",
                    proof=str(implication),
                    extra_meta={"codexlang": codexlang, "ast": ast, "glyphs": glyphs}
                )
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

            if simplified is False:
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

    def assert_axiom(
        self,
        expression: str,
        label: Optional[str] = None,
        raw_input: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Stores an axiom (assumed true) into the KG and container.
        Always preserves the Lean expression in logic/logic_raw.
        """
        try:
            # Preserve original Lean string
            lean_expr = raw_input or expression

            # Parsed is only for validation/debug
            parsed = parse_logical_operators(lean_expr)

            codexlang, ast, glyphs = self._codex_pipeline(lean_expr)

            # 🚨 Debug print before injection
            print("[DEBUG:assert_axiom] Preparing axiom injection")
            print("   lean_expr:", lean_expr)
            print("   parsed:", parsed)
            print("   codexlang:", codexlang)

            self._inject_fact(
                lean_expr,        # ✅ inject Lean string, never parsed SymPy
                [],
                kind="⟦axiom⟧",
                label=label,
                extra_meta={
                    "codexlang": codexlang,
                    "ast": ast,
                    "glyphs": glyphs
                }
            )

            # 🚨 Debug print after injection
            print("[DEBUG:assert_axiom] Axiom injected successfully")

            return {
                "status": "✅ Axiom Stored",
                "expression": lean_expr,
                "parsed": str(parsed)  # keep debug string but don't overwrite logic
            }
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
        label: Optional[str] = None,
        extra_meta: Optional[Dict[str, Any]] = None
    ):
        """
        Sends a glyph-based fact into the Knowledge Graph.
        """
        metadata = {
            "type": kind,
            "sources": sources,
            "container_id": self.container_id,
            "label": label,
        }

        if extra_meta:
            metadata.update(extra_meta)

        entry = {
            "name": label or expression,
            "symbol": kind,
            "logic": expression,        # ✅ Always keep the Lean expression here
            "logic_raw": expression,    # ✅ Preserve raw expression for trace/debug
            "body": "",
            "symbolicProof": proof if proof is not None else "",
        }

        # Merge codexlang/ast/glyphs/etc
        entry.update(metadata)

        # 🚨 Debug: confirm before writing
        import json
        print(f"[DEBUG:_inject_fact] Writing fact into KG:\n{json.dumps(entry, indent=2, ensure_ascii=False)}")

        # Write into KG
        self.kg_writer.write_fact(expression, entry)

    def _log_sqi_event(self, conclusion: str, assumptions: List[str], implication: str, status: str):
        """
        Logs proof attempt to SQI system.
        """
        self.sqi_bridge.log_trace({
            "type": "symbolic_proof_attempt",
            "container": self.container_id,
            "status": status,
            "input": conclusion,
            "assumptions": assumptions,
            "implication": implication
        })

    def _codex_pipeline(self, raw_input: str) -> Tuple[str, Any, Any]:
        """
        Converts raw input into CodexLang, AST, and glyphs.
        Used for deeper knowledge graph registration and glyph injection.

        ✅ Modernized:
        - Uses unified `parse_codexlang_to_ast` (SoulLaw-compliant)
        - Avoids deprecated `parse_raw_input_to_ast`
        - Adds fallback and debug trace for visibility
        """
        try:
            # ✅ Parse using the new symbolic Codex AST parser
            ast = parse_codexlang_to_ast(raw_input)

            # Convert AST -> CodexLang representation
            codexlang = self.rewriter.ast_to_codexlang(ast)

            # Encode CodexAST -> glyph structures for KG injection
            glyphs = encode_codex_ast_to_glyphs(ast)

            return codexlang, ast, glyphs

        except Exception as e:
            import traceback
            print(f"[⚠️ _codex_pipeline] Failed to process CodexLang input '{raw_input}': {e}")
            traceback.print_exc()
            return f"❌ CodexLang Error: {e}", None, None