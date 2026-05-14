# File: backend/modules/consciousness/situational_engine.py

from datetime import datetime
from collections import deque
import random

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class SituationalEngine:
    """
    Tracks real-world and internal events to maintain situational awareness.
    Analyzes patterns for risk, trends, and environmental/emotional context.
    """

    def __init__(self, max_events=100):
        self.events = deque(maxlen=max_events)  # Bounded memory of recent events
        self.awareness = {}
        self.risk_threshold = 0.3  # Ratio of negative events to trigger high risk

    def log_event(self, description: str, impact: str = "neutral", source: str = "unknown") -> None:
        """
        Logs an event with impact and source metadata.
        Valid impact values: 'positive', 'neutral', 'negative'
        """
        if impact not in {"positive", "neutral", "negative"}:
            print(f"[SITUATION] ⚠️ Invalid impact level: {impact}")
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "description": description,
            "impact": impact,
            "source": source
        }
        self.events.append(event)
        print(f"[SITUATION] Logged event: '{description}' ({impact}) from {source}")

    def log_container_entry(self, container_id: str):
        """
        Shortcut to log a dimension load/entry as a neutral event.
        """
        desc = f"Entered container: {container_id}"
        self.log_event(desc, impact="neutral", source="dimension")

    def analyze_context(self) -> dict:
        """
        Evaluates recent events for risk and trends.
        Returns a dictionary with awareness state.
        """
        if not self.events:
            print("[SITUATION] No events to analyze.")
            return {}

        recent = list(self.events)[-10:]
        summary = {"positive": 0, "neutral": 0, "negative": 0}

        for e in recent:
            if e["impact"] in summary:
                summary[e["impact"]] += 1

        total = sum(summary.values())
        risk_ratio = summary["negative"] / total if total > 0 else 0.0

        self.awareness = {
            "recent_summary": summary,
            "risk_score": round(risk_ratio, 2),
            "current_risk": "high" if risk_ratio >= self.risk_threshold else "low",
            "last_updated": datetime.utcnow().isoformat()
        }

        print(f"[SITUATION] Awareness updated: {self.awareness}")
        return self.awareness

    def get_awareness_state(self) -> dict:
        """
        Returns the current awareness snapshot.
        """
        return self.awareness

    def random_simulate(self) -> None:
        """
        Simulates a random test event.
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