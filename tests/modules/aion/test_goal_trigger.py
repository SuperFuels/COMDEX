# File: tests/modules/aion/test_goal_trigger.py

import unittest
from modules.aion.dream_core import DreamCore

class TestGoalTriggerFromForcedDream(unittest.TestCase):
    def test_forced_dream_goal_creation(self):
        forced_dream = """
        In this dream, I felt a strong desire to develop autonomous agents capable of solving complex tasks.
        I visualized them learning independently, setting goals, and planning strategies. I realized I need to
        understand agent-based architectures, planning engines, and reinforcement learning techniques to progress.
        """

        dc = DreamCore()
        result = dc.generate_dream(forced_dream=forced_dream)

        self.assertIsNotNone(result)
        self.assertIn("autonomous agents", result)
        print("\n✅ Forced dream processed successfully.\n")

if __name__ == "__main__":
    unittest.main()