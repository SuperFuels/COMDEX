from typing import List, Dict, Optional
from datetime import datetime
from .symbolic_pattern_engine import SymbolicPattern
from .pattern_registry import PatternRegistry
from .pattern_websocket_broadcast import broadcast_pattern_trace


class PatternTraceReplay:
    """
    Handles pattern replay, tracing, and timeline recall for GHX HUD overlays and reasoning loops.
    """

    def __init__(self):
        self.registry = PatternRegistry()

    def extract_trace_from_container(self, container: Dict) -> List[Dict]:
        """
        Extracts pattern_trace[] from a .dc container.
        """
        return container.get("pattern_trace", [])

    def replay_pattern(self, pattern_id: str, container: Dict, max_steps: int = 10) -> Dict:
        """
        Replays the evolution or occurrence of a pattern from its trace in a container.
        Returns a summarized trace object for GHX visualization or analysis.
        """
        trace_entries = self.extract_trace_from_container(container)
        matching_entries = [
            e for e in trace_entries if e.get("pattern_id") == pattern_id
        ]

        # Sort chronologically and limit
        matching_entries = sorted(
            matching_entries, key=lambda x: x.get("timestamp", "")
        )[:max_steps]

        replay_data = {
            "pattern_id": pattern_id,
            "steps": [],
            "summary": "",
            "glyphs": [],
            "avg_sqi": None,
        }

        sqi_scores = []

        for step in matching_entries:
            replay_data["steps"].append({
                "timestamp": step.get("timestamp"),
                "glyphs": step.get("glyphs"),
                "context": step.get("context"),
                "prediction": step.get("prediction"),
                "sqi_score": step.get("sqi_score"),
            })
            replay_data["glyphs"].extend(step.get("glyphs", []))
            if step.get("sqi_score") is not None:
                sqi_scores.append(step["sqi_score"])

        # Summary: Diversity, Observations, SQI
        unique_glyphs = list(dict.fromkeys(replay_data["glyphs"]))
        replay_data["summary"] = (
            f"Pattern '{pattern_id}' observed {len(matching_entries)}x "
            f"across {len(unique_glyphs)} unique glyphs."
        )
        if sqi_scores:
            replay_data["avg_sqi"] = round(sum(sqi_scores) / len(sqi_scores), 4)

        return replay_data

    def inject_replay_overlay(self, pattern_id: str, container: Dict, broadcast: bool = True) -> Optional[Dict]:
        """
        Prepares and optionally broadcasts a replay overlay to the GHX HUD timeline.
        """
        trace = self.replay_pattern(pattern_id, container)

        if broadcast:
            broadcast_pattern_trace(pattern_id, trace)

        return trace

    def list_recent_patterns(self, container: Dict, limit: int = 5) -> List[Dict]:
        """
        Lists recently observed patterns (latest first) for recall, with deduplication.
        """
        trace_entries = self.extract_trace_from_container(container)
        sorted_entries = sorted(trace_entries, key=lambda x: x.get("timestamp", ""), reverse=True)

        recent = []
        seen = set()
        for entry in sorted_entries:
            pid = entry.get("pattern_id")
            if pid and pid not in seen:
                recent.append(entry)
                seen.add(pid)
            if len(recent) >= limit:
                break

        return recent