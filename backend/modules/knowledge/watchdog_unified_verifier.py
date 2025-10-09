#!/usr/bin/env python3
"""Tessaris Unified Watchdog — auto-verifier for unified summary"""
import time, json, hashlib, subprocess
from pathlib import Path

BASE = Path(__file__).parent
TARGETS = [
    '/workspaces/COMDEX/backend/modules/knowledge/constants_v1.2.json', '/workspaces/COMDEX/backend/modules/knowledge/series_master_summary.json', '/workspaces/COMDEX/backend/modules/knowledge/unified_architecture_summary.json', '/workspaces/COMDEX/backend/modules/knowledge/J1_unified_field_summary.json', '/workspaces/COMDEX/backend/modules/knowledge/J2_ablation_kappa_summary.json', '/workspaces/COMDEX/backend/modules/knowledge/J3_ablation_beta_summary.json', '/workspaces/COMDEX/backend/modules/knowledge/J4_ablation_alpha_summary.json'
]
CHECKSUMS = {}
for t in TARGETS:
    try:
        CHECKSUMS[t] = hashlib.sha1(Path(t).read_bytes()).hexdigest()
    except FileNotFoundError:
        pass

print("👁️  Tessaris Unified Watchdog running. Press Ctrl+C to stop.")
while True:
    changed = []
    for t in TARGETS:
        try:
            new = hashlib.sha1(Path(t).read_bytes()).hexdigest()
            if new != CHECKSUMS.get(t):
                changed.append(t)
                CHECKSUMS[t] = new
        except FileNotFoundError:
            continue
    if changed:
        print(f"🔁 Change detected in: {changed} — re-running integrator …")
        subprocess.run(["python3", str(BASE / "unified_phase2_integrator.py")])
    time.sleep(10)
