# backend/tests/test_dimension_thought_runner.py

import unittest
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.tessaris.tessaris_store import TESSARIS_STORE
from backend.modules.tessaris.thought_branch import ThoughtBranch

class TestTessarisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TessarisEngine(container_id="test_container")

    def test_seed_and_expand(self):
        glyph = "⟦ Goal | Test -> Reflect ⟧"
        thought_id, root = self.engine.seed_thought(glyph, source="test_case")
        self.assertIsNotNone(thought_id)
        self.assertEqual(root.symbol, glyph)

        expanded = self.engine.expand_thought(thought_id, depth=2)
        self.assertTrue(len(expanded.children) > 0)

    def test_execute_branch(self):
        glyph = "⟦ Goal | Test -> Reflect ⟧"
        thought_id, root = self.engine.seed_thought(glyph, source="test_exec")
        self.engine.expand_thought(thought_id, depth=1)
        branch = ThoughtBranch.from_root(root, origin_id=thought_id)

        result = self.engine.execute_branch(branch)
        self.assertTrue(result)

    def test_extract_intents(self):
        glyphs = ["⟦ Goal | Learn -> Reflect ⟧", "⟦ Skill | Remember -> Boot ⟧"]
        self.engine.extract_intents_from_glyphs(glyphs)

if __name__ == '__main__':
    unittest.main()