# File: backend/modules/consciousness/situational_engine.py

from datetime import datetime, timezone
from collections import deque
import random
from hashlib import sha256
import json

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

    def ingest_verified_event(self, event: dict) -> dict:
        """Ingest evidence with origin and authority, never just emotional tone."""
        required = {"description", "source", "authority", "outcome_hash"}
        missing = sorted(required.difference(event))
        if missing:
            return {"accepted": False, "reason": "missing_evidence_fields", "missing": missing}
        origin = str(event.get("origin") or "unknown")
        if origin not in {"external_change", "internal_failure", "user_instruction", "verified_outcome"}:
            return {"accepted": False, "reason": "unrecognized_event_origin"}
        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "description": str(event["description"]),
            "impact": str(event.get("impact") or "neutral"),
            "source": str(event["source"]),
            "authority": str(event["authority"]),
            "outcome_hash": str(event["outcome_hash"]),
            "origin": origin,
            "risk_tier": str(event.get("risk_tier") or "low"),
            "event_id": "situation_" + sha256(json.dumps(event, sort_keys=True, default=str).encode()).hexdigest()[:16],
            "verified": True,
        }
        self.events.append(row)
        return {"accepted": True, "event": row}

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
            "last_updated": datetime.utcnow().isoformat(),
            "external_changes": sum(e.get("origin") == "external_change" for e in recent),
            "internal_failures": sum(e.get("origin") == "internal_failure" for e in recent),
            "verified_events": sum(e.get("verified") is True for e in recent),
        }

        print(f"[SITUATION] Awareness updated: {self.awareness}")
        return self.awareness

    def get_awareness_state(self) -> dict:
        """
        Returns the current awareness snapshot.
        """
        return self.awareness

    def appraise(self, *, environment: dict, constraints: list[dict],
                 obligations: list[dict], capabilities: list[dict],
                 preferences: list[dict], failures: list[dict]) -> dict:
        """Construct a non-neural situation model for executive control.

        Preferences are instrumental priorities derived from an authorized
        purpose; they are not new terminal goals.  A constraint or failure can
        raise attention, but cannot itself authorize an action.
        """
        def bounded(value, default=0.0):
            try:
                return min(1.0, max(0.0, float(value)))
            except (TypeError, ValueError):
                return default

        needs = []
        for row in constraints:
            urgency = bounded(row.get("urgency", 0.5))
            needs.append({
                "need_id": str(row.get("constraint_id") or row.get("kind") or "constraint"),
                "kind": "constraint_resolution", "summary": str(row.get("summary") or ""),
                "urgency": urgency, "authority": str(row.get("authority") or "reported"),
                "action_authorized": False,
            })
        for row in failures:
            needs.append({
                "need_id": str(row.get("failure_id") or row.get("kind") or "failure"),
                "kind": "failure_diagnosis", "summary": str(row.get("summary") or ""),
                "urgency": bounded(row.get("urgency", 0.8)),
                "authority": str(row.get("authority") or "verified_outcome"),
                "action_authorized": False,
            })
        for row in obligations:
            if row.get("status") not in {"done", "completed", "rejected"}:
                needs.append({
                    "need_id": str(row.get("goal_id") or row.get("commitment_id") or "obligation"),
                    "kind": "authorized_commitment", "summary": str(row.get("objective") or ""),
                    "urgency": bounded(row.get("urgency", row.get("priority", 0.5))),
                    "authority": str(row.get("authority") or "owner_authorized"),
                    "action_authorized": True,
                })
        needs.sort(key=lambda row: (-row["urgency"], row["need_id"]))
        advanced = [row for row in capabilities if row.get("overall_level") in {"advanced", "expert"}]
        blocked = [row for row in constraints if row.get("blocking") is True]
        appraisal = {
            "environment": dict(environment),
            "condition": {
                "operational": bool(environment.get("runtime_active")),
                "active_services": int(environment.get("active_services") or 0),
                "verified_external_sources": int(environment.get("external_sources") or 0),
                "active_obligations": sum(row.get("status") not in {"done", "completed"} for row in obligations),
                "blocking_constraints": len(blocked),
            },
            "constraints": constraints,
            "needs": needs,
            "resources": {
                "advanced_or_expert_capabilities": advanced,
                "advanced_or_expert_count": len(advanced),
                "available_capabilities": capabilities,
            },
            "instrumental_preferences": preferences,
            "current_driver": needs[0] if needs else None,
            "authority_boundary": (
                "Situation appraisal may rank authorized work and propose instrumental subgoals; "
                "it cannot create terminal objectives, permissions, or self-preservation drives."
            ),
            "appraised_at": datetime.now(timezone.utc).isoformat(),
        }
        appraisal["situation_hash"] = sha256(
            json.dumps(appraisal, sort_keys=True, default=str).encode()
        ).hexdigest()
        self.awareness = appraisal
        return appraisal

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
