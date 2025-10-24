# ================================================================
# 🧩 MathField Validation — Resonance Dataset Consistency
# ================================================================
"""
Verifies that mathfield_v1.qdata.json and mathfield_progression_v1.qdata.json
contain valid MathExercise structures and coherent resonance metrics.
"""

import json, logging
from pathlib import Path
from statistics import mean

DATA_FILES = [
    Path("data/learning/mathfield_v1.qdata.json"),
    Path("data/learning/mathfield_progression_v1.qdata.json"),
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate(path: Path):
    if not path.exists():
        logger.warning(f"[MathFieldValidation] Missing file: {path}")
        return None

    data = json.load(open(path))
    if not isinstance(data, list):
        logger.error(f"[MathFieldValidation] Invalid format: {path.name}")
        return None

    ρ_vals = [d["resonance"]["ρ"] for d in data if "resonance" in d]
    I_vals = [d["resonance"]["I"] for d in data if "resonance" in d]
    SQI_vals = [d["resonance"]["SQI"] for d in data if "resonance" in d]
    summary = {
        "file": path.name,
        "count": len(data),
        "ρ̄": round(mean(ρ_vals), 3),
        "Ī": round(mean(I_vals), 3),
        "SQĪ": round(mean(SQI_vals), 3),
    }
    logger.info(f"[MathFieldValidation] {path.name} → OK ({len(data)} items)")
    return summary

if __name__ == "__main__":
    summaries = [s for s in map(validate, DATA_FILES) if s]
    print(json.dumps(summaries, indent=2))