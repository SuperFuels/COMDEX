import datetime
from typing import List, Dict, Optional, Any
from backend.modules.state_manager import get_active_container


class GlyphReplayRenderer:
    def __init__(self):
        self.container = get_active_container()
        self.grid = self.container.get("glyph_grid", [])

    def render_replay_sequence(
        self,
        glyph_types: Optional[List[str]] = None,
        include_metadata: bool = True,
        include_trace: bool = True,
        sort_by_time: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return a structured list of glyph replay entries.

        Args:
            glyph_types: Optional list of glyph types to include (e.g., ["dream", "emotion"])
            include_metadata: If True, includes metadata field
            include_trace: If True, includes trace_ref field if present
            sort_by_time: Whether to sort the replay by timestamp ascending
            limit: Optional limit to number of entries returned

        Returns:
            List of replay dictionary entries.
        """
        result = []
        for glyph in self.grid:
            if glyph_types and glyph.get("type") not in glyph_types:
                continue

            entry = {
                "id": glyph.get("id"),
                "type": glyph.get("type"),
                "content": glyph.get("content"),
                "timestamp": glyph.get("timestamp"),
            }

            if include_metadata:
                entry["metadata"] = glyph.get("metadata", {})

            if include_trace and "trace_ref" in glyph:
                entry["trace_ref"] = glyph["trace_ref"]

            if "prediction" in glyph:
                entry["prediction"] = glyph["prediction"]

            if "coordinates" in glyph:
                entry["coordinates"] = glyph["coordinates"]

            if "region" in glyph:
                entry["region"] = glyph["region"]

            if "source_plugin" in glyph:
                entry["source_plugin"] = glyph["source_plugin"]

            result.append(entry)

        if sort_by_time:
            result.sort(key=lambda g: g.get("timestamp", ""))

        if limit:
            result = result[:limit]

        return result

    def get_replay_as_trace(self, glyph_type: str = "dream") -> str:
        """
        Flatten replay into a simple text trace.

        Args:
            glyph_type: Type of glyphs to include in trace (e.g., "dream")

        Returns:
            Stringified trace of glyph content ordered by time.
        """
        replay = self.render_replay_sequence(glyph_types=[glyph_type])
        trace_lines = [f"[{g['timestamp']}] {g['content']}" for g in replay]
        return "\n".join(trace_lines)

    def get_replay_stats(self) -> Dict[str, int]:
        """
        Return a summary count of glyph types in the container.
        """
        counts = {}
        for glyph in self.grid:
            gtype = glyph.get("type", "unknown")
            counts[gtype] = counts.get(gtype, 0) + 1
        return counts