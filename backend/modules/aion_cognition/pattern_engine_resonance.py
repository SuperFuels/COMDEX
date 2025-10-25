"""
⚙️  Pattern Engine ↔ QQC Resonance Coupling  (Phase 46B)
────────────────────────────────────────────────────────
Bridges Aion’s pattern subsystem to the QQC resonance field.

Responsibilities:
 • Translate QQC coherence/drift values into pattern SQI adjustments
 • Maintain QuantumPatternMap (Ψ-field ↔ symbolic pattern)
 • Export patternfield.qdata.json for CodexMetrics overlay
"""

import json, logging, time
from pathlib import Path
from typing import Dict, Any
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/telemetry/patternfield.qdata.json")

#───────────────────────────────────────────────
# Core cycle
#───────────────────────────────────────────────
def pattern_cycle(aion_state: Dict[str, Any], qqc_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies QQC resonance metrics to Aion pattern engine.
    Returns patternfield summary.
    """
    engine = SymbolicPatternEngine()
    coherence = qqc_result.get("coherence", 0.0)
    entanglement = qqc_result.get("entanglement", 0.0)
    drift = qqc_result.get("drift", {})

    logger.info(
        f"[PatternEngine] Applying resonance field → coherence={coherence}, entanglement={entanglement}, drift={len(drift)}"
    )

    # Adjust all known patterns’ SQI values proportionally to coherence & entanglement
    pattern_summary = []
    try:
        for pattern in engine.registry.get_all_patterns():
            base = pattern.sqi_score or 0.3
            adj = base * (1 + (coherence * 0.2)) * (1 + (entanglement * 0.1))
            pattern.sqi_score = round(adj, 4)
            pattern.metadata["resonance_update"] = {
                "coherence": coherence,
                "entanglement": entanglement,
                "timestamp": time.time(),
            }
            pattern_summary.append(
                {"pattern_id": pattern.pattern_id, "name": pattern.name, "sqi": pattern.sqi_score}
            )
        # Save updated pattern registry state
        engine.registry.save()
        logger.info(f"[PatternEngine] Computed {len(pattern_summary)} resonance-matched weights")
    except Exception as e:
        logger.warning(f"[PatternEngine] Resonance update failed: {e}")

    # Export patternfield data
    field_data = {
        "timestamp": time.time(),
        "patterns": pattern_summary,
        "Ψ_field": {
            "ρ": coherence,
            "Ī": entanglement,
            "φ": drift,
        },
        "schema": "PatternField.v1",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(field_data, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[PatternEngine] Exported pattern field → {OUT_PATH}")

    return field_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dummy_state = {"resonance": {"ρ": 0.3, "I": 0.25, "SQI": 0.4}}
    dummy_qqc = {"coherence": 0.38, "entanglement": 0.27, "drift": {"resonance": 0.0038}}
    result = pattern_cycle(dummy_state, dummy_qqc)
    print(json.dumps(result, indent=2))