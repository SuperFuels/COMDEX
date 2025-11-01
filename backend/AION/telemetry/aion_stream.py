"""
AION Telemetry Stream Bridge
────────────────────────────
Lightweight async telemetry interface used by QQC and AION diagnostics.
Writes incoming metrics to local JSONL logs (can later be extended to
send over WebSocket or MessageBus).
"""

import json
from pathlib import Path
from datetime import datetime, timezone

LOG_PATH = Path("backend/logs/telemetry/aion_stream.jsonl")


async def post_metric(name: str, payload: dict):
    """Append a metric event to the AION telemetry stream."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "metric": name,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[AION::Telemetry] {name} logged -> {payload}")
    return True