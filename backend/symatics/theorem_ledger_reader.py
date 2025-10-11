# 📁 backend/symatics/theorem_ledger_reader.py
# ------------------------------------------------
# Symatics Theorem Ledger Reader (v0.2)
# Reads docs/rfc/theorem_ledger.jsonl and provides:
#   • Summary stats by operator
#   • Violation filtering
#   • Chronological listing
#   • CLI query interface
# ------------------------------------------------

import os
import json
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

LEDGER_PATH = "docs/rfc/theorem_ledger.jsonl"


# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────
def _load_ledger(path: str = LEDGER_PATH) -> List[Dict[str, Any]]:
    """Load the JSONL ledger safely."""
    if not os.path.exists(path):
        print(f"[LedgerReader] No ledger found at {path}")
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                print(f"[⚠️ LedgerReader] Skipped malformed line: {line[:80]}")
    return entries


# ─────────────────────────────────────────────
# Core Queries
# ─────────────────────────────────────────────
def list_all_entries(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return all ledger entries (latest first)."""
    entries = _load_ledger()
    entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
    return entries if limit is None else entries[:limit]


def summarize_by_operator() -> Dict[str, Dict[str, Any]]:
    """
    Summarize theorem results grouped by operator symbol.
    Example:
      { "⊕": {"count": 12, "passes": 11, "fails": 1, "latest": ...}, ... }
    """
    entries = _load_ledger()
    summary = defaultdict(lambda: {"count": 0, "passes": 0, "fails": 0, "latest": None})

    for e in entries:
        op = e.get("operator", "?")
        summary[op]["count"] += 1
        passed = not e.get("violations")
        if passed:
            summary[op]["passes"] += 1
        else:
            summary[op]["fails"] += 1
        summary[op]["latest"] = e

    return dict(summary)


def filter_violations() -> List[Dict[str, Any]]:
    """Return all entries with one or more violations."""
    entries = _load_ledger()
    return [e for e in entries if e.get("violations")]


def get_operator_history(symbol: str) -> List[Dict[str, Any]]:
    """List all theorems for a given operator symbol."""
    entries = _load_ledger()
    return [e for e in entries if e.get("operator") == symbol]


# ─────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────
def print_summary_table():
    """Pretty-print summary by operator."""
    summary = summarize_by_operator()
    if not summary:
        print("[LedgerReader] No entries to summarize.")
        return

    print("─── Symatics Theorem Ledger Summary ───")
    print(f"{'Operator':^10} | {'Count':^7} | {'Pass':^6} | {'Fail':^6}")
    print("-" * 38)
    for op, data in summary.items():
        print(f"{op:^10} | {data['count']:^7} | {data['passes']:^6} | {data['fails']:^6}")
    print("-" * 38)
    print(f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")


def print_recent(limit: int = 10):
    """Print the latest N entries."""
    entries = list_all_entries(limit)
    print(f"─── Latest {len(entries)} Theorem Entries ───")
    for e in entries:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("timestamp", 0)))
        op = e.get("operator", "?")
        summary = e.get("summary", "")
        print(f"[{ts}] {op} → {summary}")
        if e.get("violations"):
            print(f"   ⚠️ Violations: {e['violations']}")
    print()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Symatics Theorem Ledger Reader")
    parser.add_argument("--summary", action="store_true", help="Show summary table by operator")
    parser.add_argument("--recent", type=int, help="Show most recent N entries")
    parser.add_argument("--violations", action="store_true", help="List only violation entries")
    parser.add_argument("--operator", type=str, help="List all entries for a given operator")

    args = parser.parse_args()

    if args.summary:
        print_summary_table()
    elif args.recent:
        print_recent(args.recent)
    elif args.violations:
        v = filter_violations()
        print(f"─── Theorems with Violations ({len(v)}) ───")
        for e in v:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("timestamp", 0)))
            print(f"[{ts}] {e.get('operator')} → {e.get('summary')}")
            print(f"   Violations: {e.get('violations')}")
    elif args.operator:
        hist = get_operator_history(args.operator)
        print(f"─── Theorem History for {args.operator} ({len(hist)} entries) ───")
        for e in hist:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get('timestamp', 0)))
            print(f"[{ts}] {e.get('summary')} | Violations: {e.get('violations')}")
    else:
        parser.print_help()