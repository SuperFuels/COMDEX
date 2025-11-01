# 📁 backend/symatics/theorem_ledger_writer.py
# ------------------------------------------------
# Symatics Theorem Ledger Writer (v0.2)
# Persists all "law_check" / theorem trace events into
# docs/rfc/theorem_ledger.jsonl for long-term verification.
# ------------------------------------------------

import os
import json
import time
from typing import Dict, Any

# Ledger output location
LEDGER_PATH = "docs/rfc/theorem_ledger.jsonl"
MAX_LEDGER_MB = 10  # auto-rotate if exceeds ~10MB


def _ensure_dir_exists(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _rotate_ledger_if_needed(path: str):
    if not os.path.exists(path):
        return
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb >= MAX_LEDGER_MB:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        rotated = f"{path}.{timestamp}.bak"
        os.rename(path, rotated)
        print(f"[Ledger] Rotated old ledger -> {rotated}")


def append_theorem_entry(entry: Dict[str, Any]):
    """
    Append a Symatics theorem (law_check) entry to the JSONL ledger.
    Each line is a single valid JSON object.

    Expected shape:
    {
      "type": "theorem",
      "engine": "symatics",
      "action": "law_check",
      "operator": "⊕",
      "summary": "5/5 passed",
      "violations": [],
      "context": {...},
      "timestamp": 1729039201.123
    }
    """
    try:
        _ensure_dir_exists(LEDGER_PATH)
        _rotate_ledger_if_needed(LEDGER_PATH)

        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"[Ledger] ✅ Recorded theorem entry for {entry.get('operator', '?')} -> {entry.get('summary')}")
    except Exception as e:
        print(f"[⚠️ Ledger] Failed to write theorem entry: {e}")


# === Optional integration helper ===
def write_from_trace_event(event: Dict[str, Any]):
    """
    Accepts a CodexTrace-like event dict and writes to the ledger
    if it represents a theorem or law_check.
    """
    if not isinstance(event, dict):
        return
    if event.get("type") in {"theorem", "codex_trace"} and event.get("action") == "law_check":
        append_theorem_entry(event)


# === CLI self-test ===
if __name__ == "__main__":
    print("⚡ Running TheoremLedger self-test...")

    sample = {
        "type": "theorem",
        "engine": "symatics",
        "action": "law_check",
        "operator": "⊕",
        "summary": "5/5 passed",
        "violations": [],
        "context": {"test_mode": True},
        "timestamp": time.time(),
    }

    append_theorem_entry(sample)