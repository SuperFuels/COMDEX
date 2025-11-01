import pandas as pd
import json
from pathlib import Path

LEDGER_PATH = Path("data/ledger/awareness_sessions_summary.jsonl")
OUTPUT_PATH = Path("data/ledger/awareness_latest.json")

def _as_float(val):
    """Convert Timestamp or string -> float safely."""
    import datetime
    if val is None:
        return 0.0
    try:
        if isinstance(val, (float, int)):
            return float(val)
        if hasattr(val, "timestamp"):  # pandas.Timestamp or datetime
            return float(val.timestamp())
        if isinstance(val, str):
            # Try parse as ISO or numeric string
            try:
                return float(val)
            except ValueError:
                try:
                    return datetime.datetime.fromisoformat(val).timestamp()
                except Exception:
                    return 0.0
    except Exception:
        return 0.0

def extract_metadata():
    if not LEDGER_PATH.exists():
        raise FileNotFoundError(f"No ledger found at {LEDGER_PATH}")
    df = pd.read_json(LEDGER_PATH, lines=True)

    # Auto-detect proper Phi column
    phi_col = "Phi" if "Phi" in df.columns else "Φ_mean"

    latest = {
        "Phi": float(df[phi_col].iloc[-1]),
        "R": float(df["resonance_index"].iloc[-1]),
        "S": str(df["closure_state"].iloc[-1]),
        "gain": float(df["gain"].iloc[-1]),
        "timestamp": _as_float(df["timestamp"].iloc[-1]),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2)
    print(f"✅ Awareness metadata extracted -> {OUTPUT_PATH}")

if __name__ == "__main__":
    extract_metadata()