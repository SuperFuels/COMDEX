# 📁 backend/symatics/theorem_summary_generator.py
# -------------------------------------------------
# Symatics Theorem Summary Generator (v0.3-pre)
# Reads theorem_ledger.jsonl and writes a Markdown report
# to docs/rfc/theorem_summary.md
# -------------------------------------------------

import os
import json
import time
from collections import defaultdict
from typing import List, Dict, Any

LEDGER_PATH = "docs/rfc/theorem_ledger.jsonl"
SUMMARY_PATH = "docs/rfc/theorem_summary.md"


# ─────────────────────────────────────────────
# Utility: Load ledger
# ─────────────────────────────────────────────
def _load_ledger() -> List[Dict[str, Any]]:
    if not os.path.exists(LEDGER_PATH):
        print(f"[TheoremSummary] Ledger not found at {LEDGER_PATH}")
        return []
    entries = []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[⚠️] Skipping malformed entry: {line[:60]}")
    return entries


# ─────────────────────────────────────────────
# Core: Build Markdown Summary
# ─────────────────────────────────────────────
def build_summary(entries: List[Dict[str, Any]]) -> str:
    """Generate Markdown summary text."""
    header = (
        "# 📘 Symatics Theorem Summary Report\n"
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "> Automated theorem verification summary for Symatics v0.2+.\n"
        "> Each row corresponds to the latest law_check for an operator.\n\n"
    )

    if not entries:
        return header + "_No theorem data found._\n"

    # group by operator
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.get("operator", "?")].append(e)

    # markdown table
    lines = [
        "| Operator | Count | Pass | Fail | Last Summary | Violations |",
        "|-----------|-------|------|------|---------------|-------------|",
    ]

    for op, records in grouped.items():
        count = len(records)
        passes = len([r for r in records if not r.get("violations")])
        fails = count - passes
        latest = sorted(records, key=lambda x: x.get("timestamp", 0), reverse=True)[0]
        lines.append(
            f"| `{op}` | {count} | {passes} | {fails} | "
            f"{latest.get('summary', '')} | "
            f"{', '.join(latest.get('violations', [])) if latest.get('violations') else '-'} |"
        )

    summary_table = "\n".join(lines)
    footer = (
        "\n\n---\n"
        "_End of report - generated automatically by Tessaris Symatics._\n"
    )

    return header + summary_table + footer


# ─────────────────────────────────────────────
# Write summary file
# ─────────────────────────────────────────────
def write_summary():
    entries = _load_ledger()
    if not entries:
        print("[TheoremSummary] No entries found.")
        return
    md = build_summary(entries)
    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[TheoremSummary] Markdown summary written -> {SUMMARY_PATH}")


# ─────────────────────────────────────────────
# CLI Entry
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("⚡ Generating Symatics Theorem Markdown Summary...")
    write_summary()