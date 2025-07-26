import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

EXPORT_PATH = "data/logs/collapse_trace_log.dc.json"  # Customize as needed
logger = logging.getLogger(__name__)

def export_collapse_trace(
    expression: str,
    output: str,
    adapter_name: str,
    identity: Optional[str] = None,
    timestamp: Optional[float] = None,
    extra: Optional[Dict] = None
) -> None:
    """
    Export a symbolic collapse trace for replay, GHX holograms, or debugging.
    Saves in `.dc.json` format.

    Args:
        expression: symbolic input expression, e.g. ⟦ Key : ... ⟧
        output: collapse result (hex, key, string, etc.)
        adapter_name: name of adapter used ("CodexCore", "DummyAdapter", etc.)
        identity: optional linked identity or avatar
        timestamp: optional Unix time
        extra: any additional fields to include (e.g., ghx_data, trigger metadata)
    """
    try:
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()

        trace = {
            "type": "collapse_trace",
            "expression": expression,
            "output": output,
            "adapter": adapter_name,
            "identity": identity,
            "timestamp": timestamp,
            "hologram": {
                "ghx_data": extra.get("ghx_data") if extra and "ghx_data" in extra else None,
                "trigger_metadata": extra.get("trigger_metadata") if extra and "trigger_metadata" in extra else None,
            }
        }

        # Merge any other extra fields outside of 'hologram'
        if extra:
            for key, value in extra.items():
                if key not in ("ghx_data", "trigger_metadata"):
                    trace[key] = value

        # Ensure directory exists
        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)

        # Append to file
        with open(EXPORT_PATH, "a", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False)
            f.write("\n")

        logger.info(f"[CollapseTraceExporter] Exported trace for {expression} → {output}")

    except Exception as e:
        logger.error(f"[CollapseTraceExporter] Failed to export collapse trace: {e}")