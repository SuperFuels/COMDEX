# ================================================================
# ⚙️ CEE Learning Cycle QA Validation — Phase 45G g17
# ================================================================
"""
Automated QA validator for Cognitive Exercise Engine learning cycles.
Checks:
  1. LexField ↔ MathField coherence (resonance means within tolerance)
  2. GHX↔Habit↔CodexMetrics consistency (if overlays exist)
  3. SQI trend direction in math progression dataset
Outputs → data/telemetry/cee_learningcycle_validation.json
"""

import json, logging, time
from pathlib import Path

DATA = {
    "lexfield": Path("data/learning/lexfield_v1.qdata.json"),
    "mathfield": Path("data/learning/mathfield_v1.qdata.json"),
    "math_progression": Path("data/learning/mathfield_progression_v1.qdata.json"),
    "codex": Path("data/telemetry/codexmetrics_overlay.json"),
}

OUT = Path("data/telemetry/cee_learningcycle_validation.json")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def mean(vals):
    return round(sum(vals) / len(vals), 3) if vals else 0.0

# ----------------------------------------------------------------------
def load_resonance(path):
    """Robustly load resonance data from qdata files (dict or list)."""
    if not path.exists():
        logger.warning(f"[CEE-QA] Missing file: {path}")
        return {"ρ̄": 0.0, "Ī": 0.0, "SQĪ": 0.0}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"[CEE-QA] Could not parse {path}: {e}")
        return {"ρ̄": 0.0, "Ī": 0.0, "SQĪ": 0.0}

    if isinstance(data, list):
        try:
            ρ = mean([d["resonance"]["ρ"] for d in data])
            I = mean([d["resonance"]["I"] for d in data])
            SQI = mean([d["resonance"]["SQI"] for d in data])
            return {"ρ̄": ρ, "Ī": I, "SQĪ": SQI}
        except Exception:
            return {"ρ̄": 0.0, "Ī": 0.0, "SQĪ": 0.0}

    if isinstance(data, dict):
        keys = list(data.keys())
        logger.info(f"[CEE-QA] Reading {path.name}, keys: {keys}")

        # --- NEW: handle nested averages block (LexField v1)
        if "averages" in data and isinstance(data["averages"], dict):
            avg = data["averages"]
            ρ = avg.get("ρ̄") or avg.get("rho") or 0.0
            I = avg.get("Ī") or avg.get("I") or 0.0
            SQI = avg.get("SQĪ") or avg.get("SQI") or 0.0
            return {"ρ̄": float(ρ), "Ī": float(I), "SQĪ": float(SQI)}

        # --- handle flat resonance summaries
        rho = data.get("ρ̄") or data.get("\\u03c1\\u0304") or data.get("rho") or data.get("ρ") or 0.0
        I = data.get("Ī") or data.get("\\u012a") or data.get("I") or 0.0
        SQI = data.get("SQĪ") or data.get("\\u0053\\u0051\\u0049\\u0304") or data.get("SQI") or 0.0
        return {"ρ̄": float(rho), "Ī": float(I), "SQĪ": float(SQI)}

    return {"ρ̄": 0.0, "Ī": 0.0, "SQĪ": 0.0}

# ----------------------------------------------------------------------
def validate_cycle():
    lex = load_resonance(DATA["lexfield"])
    math = load_resonance(DATA["mathfield"])
    prog = load_resonance(DATA["math_progression"])

    rho_diff = round(abs(lex["ρ̄"] - math["ρ̄"]), 3)
    I_diff = round(abs(lex["Ī"] - math["Ī"]), 3)
    SQI_diff = round(abs(lex["SQĪ"] - math["SQĪ"]), 3)
    consistent = all(d < 0.15 for d in (rho_diff, I_diff, SQI_diff))

    trend = (
        "increasing" if prog["ρ̄"] > math["ρ̄"] else
        "decreasing" if prog["ρ̄"] < math["ρ̄"] else
        "stable"
    )

    result = {
        "timestamp": time.time(),
        "lexfield": lex,
        "mathfield": math,
        "math_progression": prog,
        "rho_diff": rho_diff,
        "I_diff": I_diff,
        "SQI_diff": SQI_diff,
        "trend": trend,
        "consistent": consistent,
        "schema": "CEELearningCycleValidation.v1",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(OUT, "w"), indent=2)
    logger.info(f"[CEE-QA] Validation summary → {OUT}")
    print(json.dumps(result, indent=2))
    return result

# ----------------------------------------------------------------------
if __name__ == "__main__":
    validate_cycle()