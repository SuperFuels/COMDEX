"""
🧩  Resonant Reasoner — Phase 47 Integration
--------------------------------------------
Ingests LexMemory, patternfield, and motivfield data to bias reasoning
depth, exploration, and tone dynamically during cognitive cycles.

Inputs :
    - data/memory/lex_memory.json
    - data/telemetry/patternfield.qdata.json
    - data/telemetry/motivfield.qdata.json
Outputs:
    - data/telemetry/reasonfield.qdata.json
"""

import json, time, math, logging, statistics
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

#───────────────────────────────────────────────
# 📂 Paths
#───────────────────────────────────────────────
MEM_PATH    = Path("data/memory/lex_memory.json")
PATTERN     = Path("data/telemetry/patternfield.qdata.json")
MOTIVFIELD  = Path("data/telemetry/motivfield.qdata.json")
REASONFIELD = Path("data/telemetry/reasonfield.qdata.json")


#───────────────────────────────────────────────
# 🧩 Utility
#───────────────────────────────────────────────
def _extract_numeric(val: Any, default: float = 0.0) -> float:
    """Safely extract a numeric value from potentially nested dicts."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        for k in ("value", "amplitude", "depth", "exploration"):
            if k in val and isinstance(val[k], (int, float)):
                return float(val[k])
    if isinstance(val, list) and len(val) > 0:
        return _extract_numeric(val[0], default)
    return default


#───────────────────────────────────────────────
# 🔬 Resonant Reasoning Core
#───────────────────────────────────────────────
def compute_reasoning_bias(
    lex_data: Dict[str, Any],
    pattern_data: Dict[str, Any],
    motiv_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine symbolic (LexMemory), affective (Motivator), and structural (PatternEngine)
    fields to derive reasoning bias tensors.
    """
    # --- Motivator fields ---
    tone_amp = _extract_numeric(motiv_data.get("tone", 0.0))
    depth    = _extract_numeric(motiv_data.get("bias", {}).get("depth", 1.0))
    explore  = _extract_numeric(motiv_data.get("bias", {}).get("exploration", 0.1))

    # --- Lexical field averages ---
    if isinstance(lex_data, dict) and len(lex_data) > 0:
        weights = [v.get("SQI", 0.3) for v in lex_data.values() if isinstance(v, dict)]
    else:
        weights = [0.3]
    mean_SQI = statistics.mean(weights)

    # --- Pattern coherence estimation ---
    coherence = pattern_data.get("entries", 1) / max(len(lex_data) or 1, 1)

    # --- Reasoning bias computations ---
    reasoning_depth = round(depth * (1 + mean_SQI * 0.5), 3)
    exploration_rate = round(explore * (1 - mean_SQI * 0.3), 3)
    tone_weight = round(tone_amp * (0.8 + mean_SQI * 0.2), 3)

    field = {
        "timestamp": time.time(),
        "schema": "ReasonField.v1",
        "bias": {
            "depth": reasoning_depth,
            "exploration": exploration_rate
        },
        "tone": tone_weight,
        "meta": {
            "mean_SQI": mean_SQI,
            "coherence": coherence,
            "lexical_count": len(lex_data)
        }
    }

    logger.info(
        f"[ResonantReasoner] depth={reasoning_depth}, exploration={exploration_rate}, tone={tone_weight}"
    )
    logger.info(
        f"[ResonantReasoner] SQĪ={mean_SQI}, coherence={coherence}, lex_count={len(lex_data)}"
    )
    return field


#───────────────────────────────────────────────
# 💾  Persistence Cycle
#───────────────────────────────────────────────
def reasoner_cycle() -> Dict[str, Any]:
    """Load all telemetry sources and compute the composite reasonfield."""
    if not (MEM_PATH.exists() and PATTERN.exists() and MOTIVFIELD.exists()):
        raise FileNotFoundError("Required telemetry files missing for ResonantReasoner.")

    with open(MEM_PATH, "r", encoding="utf-8") as f:
        lex_data = json.load(f)
    with open(PATTERN, "r", encoding="utf-8") as f:
        pattern = json.load(f)
    with open(MOTIVFIELD, "r", encoding="utf-8") as f:
        motiv = json.load(f)

    reasonfield = compute_reasoning_bias(lex_data, pattern, motiv)

    REASONFIELD.parent.mkdir(parents=True, exist_ok=True)
    with open(REASONFIELD, "w", encoding="utf-8") as f:
        json.dump(reasonfield, f, indent=2)

    logger.info(f"[ResonantReasoner] Exported reasonfield → {REASONFIELD}")
    return reasonfield


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reasoner_cycle()