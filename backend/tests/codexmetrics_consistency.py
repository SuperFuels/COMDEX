# ================================================================
# 🧩 CodexMetrics Consistency Validation — GHX ↔ Habit ↔ Codex
# ================================================================
"""
Ensures that CodexMetrics overlay matches GHX summary
values (ρ, I) within tolerance.

Checks:
  • codexmetrics_overlay.json and ghx_stream.json exist
  • avg_ρ and avg_I differ ≤ 5%
  • Logs result → data/telemetry/codexmetrics_consistency.json
"""

import json, math, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GHX_PATH = Path("data/telemetry/ghx_stream.json")
CODEX_PATH = Path("data/telemetry/codexmetrics_overlay.json")
OUT_PATH = Path("data/telemetry/codexmetrics_consistency.json")

def run_validation():
    if not (GHX_PATH.exists() and CODEX_PATH.exists()):
        logger.error("[CodexConsistency] Missing required telemetry files.")
        return

    ghx = json.load(open(GHX_PATH))
    codex = json.load(open(CODEX_PATH))

    g_ops = ghx.get("stream", ghx.get("instructions", []))
    if not g_ops:
        logger.warning("[CodexConsistency] No GHX stream data found.")
        return

    ghx_rho = sum(op.get("ρ", 0) for op in g_ops) / len(g_ops)
    ghx_I = sum(op.get("I", 0) for op in g_ops) / len(g_ops)

    c_rho = codex.get("avg_ρ", codex.get("avg_rho"))
    c_I = codex.get("avg_I", codex.get("avg_i"))

    rho_diff = abs((c_rho or 0) - ghx_rho)
    I_diff = abs((c_I or 0) - ghx_I)
    consistent = rho_diff <= 0.05 and I_diff <= 0.05

    summary = {
        "timestamp": time.time(),
        "ghx_avg_ρ": round(ghx_rho, 3),
        "ghx_avg_I": round(ghx_I, 3),
        "codex_avg_ρ": c_rho,
        "codex_avg_I": c_I,
        "rho_diff": round(rho_diff, 3),
        "I_diff": round(I_diff, 3),
        "consistent": consistent,
        "schema": "CodexMetricsConsistency.v1",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[CodexConsistency] Summary → {OUT_PATH}")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    run_validation()
    print("✅ CodexMetrics consistency validation complete.")