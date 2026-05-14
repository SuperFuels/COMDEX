import os
import json
import time
from typing import Optional, Dict, Any

# Root output directory for collapse timelines
TIMELINE_ROOT = "logs/collapse_timeline"
os.makedirs(TIMELINE_ROOT, exist_ok=True)

# 🧪 Fallback path used in testing if no container_id provided
COLLAPSE_LOG_PATH = os.path.join(os.getcwd(), "collapse_log.json")


def log_collapse_event(
    beam,
    tick_num: int,
    container_id: Optional[str] = None,
    tick_start_time: Optional[float] = None,
    profile_data: Optional[Dict[str, Any]] = None,
):
    """
    Logs a single collapse event into the container's timeline log.

    Parameters:
    - beam: The Beam object
    - tick_num: Current tick index
    - container_id: If provided, logs to `logs/collapse_timeline/{container_id}.timeline.jsonl`
    - tick_start_time: If provided, duration for tick will be calculated
    - profile_data: Optional dict of additional metrics (e.g., tick_duration, mutation_time, etc.)

    Falls back to `collapse_log.json` if container_id is missing.
    """

    timestamp = time.time()
    tick_duration_ms = None

    if tick_start_time:
        tick_duration_ms = round((timestamp - tick_start_time) * 1000, 3)

    if container_id:
        filename = f"{container_id}.timeline.jsonl"
        path = os.path.join(TIMELINE_ROOT, filename)
    else:
        path = COLLAPSE_LOG_PATH

    event = {
        "tick": tick_num,
        "timestamp": timestamp,
        "container_id": container_id,
        "beam_id": beam.id,
        "coherence": round(beam.coherence, 6),
        "phase": round(beam.phase, 6),
        "amplitude": round(beam.amplitude, 6),
        "sqi_score": round(getattr(beam, "sqi_score", 0.0), 6),
        "status": beam.status,
        "decoherence_rate": round(getattr(beam, "decoherence_rate", 0.0), 6),
        "collapse_type": getattr(beam, "collapse_type", "unknown"),
    }

    # Include profiling data if available
    if tick_duration_ms is not None:
        event["tick_duration_ms"] = tick_duration_ms
    if profile_data:
        event.update(profile_data)

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[Timeline] ⚠️ Failed to write collapse event for beam {beam.id}: {e}")

def log_collapse_tick(wave_state, profile_data: Optional[Dict[str, Any]] = None):
    """
    Adapter function used by BeamController to log the current collapse tick
    based on wave state. It wraps log_collapse_event for each beam.
    """
    tick_num = profile_data.get("tick_index", 0) if profile_data else 0
    tick_start_time = None

    if profile_data and "tick_duration_ms" in profile_data:
        tick_start_time = time.time() - (profile_data["tick_duration_ms"] / 1000.0)

    container_id = getattr(wave_state, "container_id", None)

    for beam in getattr(wave_state, "beams", []):
        log_collapse_event(
            beam=beam,
            tick_num=tick_num,
            container_id=container_id,
            tick_start_time=tick_start_time,
            profile_data=profile_data
        )