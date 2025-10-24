# ================================================================
# 📊 CodexMetrics Hook
# ================================================================
import json, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)
METRICS_PATH = Path("data/telemetry/codexmetrics.json")

def log_resonance(expr, rho, phi, intensity):
    payload = {
        "timestamp": time.time(),
        "expr": str(expr),
        "ρ": rho,
        "φ": phi,
        "I": intensity,
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = []
    if METRICS_PATH.exists():
        try:
            data = json.load(open(METRICS_PATH))
        except Exception:
            data = []
    data.append(payload)
    json.dump(data[-200:], open(METRICS_PATH, "w"), indent=2)
    logger.info(f"[CodexMetrics] Logged resonance for {expr}")