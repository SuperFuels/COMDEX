# 🧪 tests/test_codexlang_rewriter.py

import unittest
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter, suggest_rewrite_candidates


class TestCodexLangRewriter(unittest.TestCase):

    def test_simplify_soft_mode(self):
        expr = "x + 0"
        simplified = CodexLangRewriter.simplify(expr, mode="soft")
        self.assertEqual(simplified, "x")

    def test_simplify_aggressive_mode(self):
        expr = "  0 +   y  "
        simplified = CodexLangRewriter.simplify(expr, mode="aggressive")
        self.assertEqual(simplified, "y")   # canonical form retained

    def test_render_ast_forall(self):
        ast = {"type": "forall", "var": "x", "body": {"type": "predicate", "name": "P", "arg": "x"}}
        output = CodexLangRewriter.ast_to_codexlang(ast)
        self.assertEqual(output, "∀x. P(x)")

    def test_render_ast_and(self):
        ast = {"type": "and", "terms": ["P", "Q", "R"]}
        output = CodexLangRewriter.ast_to_codexlang(ast)
        self.assertEqual(output, "P ∧ Q ∧ R")

    def test_render_ast_nested(self):
        ast = {
            "type": "implies",
            "left": {
                "type": "and",
                "terms": [
                    {"type": "predicate", "name": "P", "arg": "x"},
                    {"type": "predicate", "name": "Q", "arg": "x"}
                ]
            },
            "right": {"type": "predicate", "name": "R", "arg": "x"}
        }
        output = CodexLangRewriter.ast_to_codexlang(ast)
        self.assertEqual(output, "P(x) ∧ Q(x) -> R(x)")

    def test_suggest_double_negation(self):
        ast = {
            "type": "not",
            "term": {
                "type": "not",
                "term": {"type": "predicate", "name": "P", "arg": "x"}
            }
        }
        suggestions = suggest_rewrite_candidates(ast)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["reason"], "Double negation")

    def test_suggest_identity_and_true(self):
        ast = {
            "type": "and",
            "terms": [
                "P",
                {"type": "constant", "value": "True"},
                "Q"
            ]
        }
        suggestions = suggest_rewrite_candidates(ast)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["reason"], "Identity: P ∧ True -> P")
        self.assertIn("rewrite", suggestions[0])


if __name__ == "__main__":
    unittest.main()