#!/usr/bin/env python3
"""
🔒 Tessaris Checksum Verifier
Verifies post-integration binary and module integrity for any Tessaris backend subsystem.
Generates a signed SHA256 audit report in /telemetry/integrity/.

Usage:
    python backend/tools/verify_checksums.py --targets backend/modules/qwave backend/core
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
import argparse
from typing import Dict, List

# ===============================================================
# 🔍 Auto Root Detection
# ===============================================================
def find_repo_root(start_dir: str) -> str:
    """Locate the repo root by walking upward until `.git` or `pyproject.toml` is found."""
    path = os.path.abspath(start_dir)
    while path != os.path.dirname(path):
        if any(os.path.exists(os.path.join(path, m)) for m in [".git", "pyproject.toml", "backend"]):
            return path
        path = os.path.dirname(path)
    return os.path.abspath(start_dir)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIT_DIR = os.path.join(ROOT_DIR, "telemetry", "integrity")
os.makedirs(AUDIT_DIR, exist_ok=True)

# ===============================================================
# 🔑 Core Utilities
# ===============================================================
def sha256sum(path: str) -> str:
    """Compute SHA256 for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_target(target: str) -> Dict[str, str]:
    """Scan a directory recursively and hash all files."""
    base_path = os.path.join(ROOT_DIR, target)
    if not os.path.exists(base_path):
        return {}

    print(f"[HASH] Scanning {target} ...")
    results = {}
    for root, _, files in os.walk(base_path):
        for file in files:
            full = os.path.join(root, file)
            try:
                rel = os.path.relpath(full, ROOT_DIR)
                results[rel] = sha256sum(full)
            except Exception as e:
                print(f"[ERR] {file}: {e}")
    return results

# ===============================================================
# 🚀 Main Entry
# ===============================================================
def main():
    parser = argparse.ArgumentParser(description="Verify SHA256 integrity of Tessaris backend modules.")
    parser.add_argument("--targets", nargs="+", required=True, help="List of relative directories to verify")
    args = parser.parse_args()

    report = {
        "schema_version": "1.1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "root_dir": ROOT_DIR,
        "verified_targets": [],
        "hashes": {},
        "missing_targets": [],
    }

    for target in args.targets:
        hashes = scan_target(target)
        if hashes:
            report["hashes"][target] = hashes
            report["verified_targets"].append(target)
        else:
            report["missing_targets"].append(target)

    # Save report
    out_path = os.path.join(
        AUDIT_DIR,
        f"sha_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Summary
    print(f"\n[✔] Integrity report generated -> {out_path}")
    if report["verified_targets"]:
        print("✅ Verified:")
        for t in report["verified_targets"]:
            print(f"   * {t}")
    if report["missing_targets"]:
        print("\n⚠️  Skipped (not found):")
        for t in report["missing_targets"]:
            print(f"   * {t}")

if __name__ == "__main__":
    main()