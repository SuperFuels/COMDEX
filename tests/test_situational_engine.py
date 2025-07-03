import unittest
from modules.consciousness.situational_engine import SituationalEngine

class TestSituationalEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SituationalEngine(max_events=5)

    def test_log_event(self):
        self.engine.log_event("test event", impact="positive", source="unittest")
        self.assertEqual(len(self.engine.events), 1)
        self.assertEqual(self.engine.events[0]["description"], "test event")
        self.assertEqual(self.engine.events[0]["impact"], "positive")
        self.assertEqual(self.engine.events[0]["source"], "unittest")

    def test_event_overflow(self):
        for i in range(10):
            self.engine.log_event(f"event {i}", impact="neutral")
        self.assertLessEqual(len(self.engine.events), 5)

    def test_analyze_context_no_events(self):
        engine = SituationalEngine()
        result = engine.analyze_context()
        self.assertEqual(result, {})

    def test_analyze_context_with_mixed_events(self):
        self.engine.log_event("success", impact="positive")
        self.engine.log_event("failure", impact="negative")
        self.engine.log_event("meh", impact="neutral")
        summary = self.engine.analyze_context()
        self.assertIn("risk_score", summary)
        self.assertIn(summary["current_risk"], ["low", "high"])

    def test_get_awareness_state(self):
        self.engine.log_event("something happened", impact="neutral")
        self.engine.analyze_context()
        state = self.engine.get_awareness_state()
        self.assertIn("risk_score", state)

    def test_simulation(self):
        self.engine.random_simulate()
        self.assertGreaterEqual(len(self.engine.events), 1)

if __name__ == "__main__":
    unittest.main()
