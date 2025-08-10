"""
Telemetry stub for GlyphWave (hook into existing HUD later).
"""
from typing import Dict, Any, List

class WaveScope:
    def __init__(self):
        self._lines: List[Dict[str, Any]] = []

    def log(self, event: str, **kv: Any) -> None:
        self._lines.append({"event": event, **kv})
        # TODO: stream to WebSocket HUD / GHX trace

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._lines[-limit:]