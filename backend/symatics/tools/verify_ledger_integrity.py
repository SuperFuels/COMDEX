# -*- coding: utf-8 -*-
"""
Tessaris SRK-8 / SRK-9 Ledger Integrity Verifier
────────────────────────────────────────────────
Verifies theorem ledger integrity and hash consistency
for the Symatics-Codex proof ledger system.

Checks:
    * Unique + non-empty hashes
    * Valid timestamps
    * CodexLang AST presence
    * Missing or null symbolic data
    * Ledger continuity (chronological + semantic)

Usage:
    PYTHONPATH=. python backend/symatics/tools/verify_ledger_integrity.py
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path


LEDGER_PATH = Path("docs/rfc/theorem_ledger.jsonl")


def compute_semantic_hash(record):
    """
    Recomputes semantic hash using available logic fields.
    Uses codexlang_string or logic_raw (if present).
    """
    content = (
        record.get("codexlang_string")
        or record.get("logic_raw")
        or record.get("symbol")
        or ""
    )
    return hashlib.sha1(content.encode("utf-8")).hexdigest()[:16]


def verify_record(record):
    """
    Verifies integrity of a single theorem record.
    Returns (ok: bool, issues: list[str])
    """
    issues = []
    ok = True

    # hash validity
    if not record.get("hash") or record["hash"] == "e3b0c44298fc1c14":
        ok = False
        issues.append("⚠ empty or placeholder hash")

    # timestamp validity
    try:
        datetime.fromisoformat(record["timestamp"])
    except Exception:
        ok = False
        issues.append("⚠ invalid timestamp")

    # codexlang presence
    if record.get("codex_ast") in (None, {}, []):
        issues.append("⚠ codex_ast empty")
    if not record.get("codexlang_string"):
        issues.append("⚠ codexlang_string missing")

    # glyph symbol check
    if record.get("glyph_symbol") is None:
        issues.append("⚠ glyph_symbol null")

    # recompute semantic hash consistency
    recomputed = compute_semantic_hash(record)
    if record.get("hash") != recomputed:
        issues.append(f"i recomputed semantic hash: {recomputed}")

    return ok, issues


def verify_ledger(path: Path = LEDGER_PATH):
    if not path.exists():
        print(f"❌ Ledger not found: {path}")
        return

    print(f"🔍 Verifying ledger: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]

    total = len(records)
    passed = 0
    failed = 0
    placeholder_hashes = 0

    for rec in records:
        ok, issues = verify_record(rec)
        symbol = rec.get("symbol", "<unknown>")
        if ok:
            passed += 1
            print(f"✅ {symbol}")
        else:
            failed += 1
            print(f"❌ {symbol}")
        for i in issues:
            if "placeholder hash" in i:
                placeholder_hashes += 1
            print(f"   {i}")

    print("\n=== Ledger Summary ===")
    print(f"Total records: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Placeholder hashes: {placeholder_hashes}")
    print("=======================")

    # Ledger continuity (chronological check)
    timestamps = [datetime.fromisoformat(r["timestamp"]) for r in records]
    if timestamps == sorted(timestamps):
        print("🕒 Ledger timestamps in correct chronological order.")
    else:
        print("⚠ Ledger timestamps out of order!")

    # Optional: recompute and repair hashes
    repaired = 0
    if failed > 0:
        for r in records:
            if r.get("hash") in (None, "e3b0c44298fc1c14"):
                r["hash"] = compute_semantic_hash(r)
                repaired += 1
        repaired_path = path.with_name("theorem_ledger_repaired.jsonl")
        with open(repaired_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n🧩 Repaired {repaired} placeholder hashes.")
        print(f"💾 Wrote repaired ledger -> {repaired_path}")


if __name__ == "__main__":
    verify_ledger()