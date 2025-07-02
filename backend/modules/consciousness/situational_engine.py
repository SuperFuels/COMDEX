from datetime import datetime
from collections import deque
import random

class SituationalEngine:
    """
    Tracks real-world and internal events to maintain situational awareness.
    Analyzes patterns for risk, trends, and emotional/environmental awareness.
    """

    def __init__(self, max_events=100):
        self.events = deque(maxlen=max_events)  # bounded memory of recent events
        self.awareness = {}
        self.risk_threshold = 3  # # of negative events in recent history to trigger high risk

    def log_event(self, description: str, impact: str = "neutral", source: str = "unknown"):
        """
        Logs an event with impact and source metadata.
        """
        timestamp = datetime.utcnow().isoformat()
        event = {
            "timestamp": timestamp,
            "description": description,
            "impact": impact,
            "source": source
        }
        self.events.append(event)
        print(f"[SITUATION] Logged event: '{description}' ({impact}) from {source}")

    def analyze_context(self):
        """
        Evaluates recent events for situational risk and pattern trends.
        """
        if not self.events:
            print("[SITUATION] No events to analyze.")
            return {}

        recent_events = list(self.events)[-10:]
        impact_summary = {"positive": 0, "neutral": 0, "negative": 0}
        for event in recent_events:
            impact_summary[event["impact"]] += 1

        total = sum(impact_summary.values())
        risk_score = impact_summary["negative"] / total if total > 0 else 0

        self.awareness = {
            "recent_summary": impact_summary,
            "risk_score": round(risk_score, 2),
            "current_risk": "high" if risk_score >= 0.3 else "low",
            "last_updated": datetime.utcnow().isoformat()
        }

        print(f"[SITUATION] Awareness updated: {self.awareness}")
        return self.awareness

    def get_awareness_state(self):
        """
        Returns current awareness snapshot.
        """
        return self.awareness

    def random_simulate(self):
        """
        Optional: Simulates a random event to test reactivity.
        """
        samples = [
            ("new goal assigned", "positive"),
            ("task failure", "negative"),
            ("data synced", "neutral"),
            ("resource depleted", "negative"),
            ("milestone achieved", "positive"),
            ("conflict detected", "negative")
        ]
        desc, impact = random.choice(samples)
        self.log_event(desc, impact, source="simulation")