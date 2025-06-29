from datetime import datetime

class SituationalEngine:
    def __init__(self):
        self.events = []
        self.awareness = {}

    def log_event(self, description: str, impact: str = "neutral"):
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "description": description,
            "impact": impact
        }
        self.events.append(event)
        print(f"[SITUATION] Logged event: {description} ({impact})")

    def analyze_context(self):
        if not self.events:
            print("[SITUATION] No context to analyze.")
            return {}

        recent_events = self.events[-5:]
        impact_summary = {"positive": 0, "neutral": 0, "negative": 0}
        for event in recent_events:
            impact_summary[event["impact"]] += 1

        self.awareness = {
            "recent_summary": impact_summary,
            "current_risk": "high" if impact_summary["negative"] >= 3 else "low"
        }

        print(f"[SITUATION] Context awareness updated: {self.awareness}")
        return self.awareness

    def get_awareness_state(self):
        return self.awareness
