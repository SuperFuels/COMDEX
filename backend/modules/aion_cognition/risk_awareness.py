import json, os, time
from pathlib import Path
from typing import Any, Dict, Optional

def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))

RISK_LOG_PATH = _data_root() / "telemetry" / "risk_awareness_log.jsonl"

def _clamp01(x: float) -> float:
    if x < 0.0: return 0.0
    if x > 1.0: return 1.0
    return x

def append_risk_awareness(
    *,
    ts: float,
    session: str,
    goal: str,
    topic: str,
    risk: float,
    confidence: float,
    S: Optional[float],
    H: Optional[float],
    cause: str = "risk_awareness",
) -> None:
    rec = {
        "ts": float(ts),
        "session": str(session),
        "goal": str(goal),
        "topic": str(topic),
        "risk": float(risk),
        "confidence": float(confidence),
        "S": None if S is None else float(S),
        "H": None if H is None else float(H),
        "cause": str(cause),
        "schema": "AION.RiskAwareness.v1",
    }
    RISK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RISK_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def compute_risk_from_cau(cau_snap: Dict[str, Any], confidence: float) -> float:
    # deterministic stub: higher H and lower S => higher risk
    try:
        S = cau_snap.get("S")
        H = cau_snap.get("H")
        if S is None or H is None:
            return 0.5
        Sf = float(S)
        Hf = float(H)
        return _clamp01(0.5 * (1.0 - Sf) + 0.5 * Hf)
    except Exception:
        return 0.5