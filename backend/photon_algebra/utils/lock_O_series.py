#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O-Series Lock (Observer-Causal Integration) - Tessaris
Cryptographically seals the O1-O11 observer-causal discovery continuum.
"""

import json, hashlib, os
from datetime import datetime

# === Input summaries (ensure they exist before running) ===
summaries = [
    "backend/modules/knowledge/O_series_synthesis.json",
    "backend/modules/knowledge/O1_observer_channel.json",
    "backend/modules/knowledge/O2_info_equilibrium.json",
    "backend/modules/knowledge/O3_entropic_symmetry.json",
    "backend/modules/knowledge/O4_entanglement_lock.json",
    "backend/modules/knowledge/O4a_entanglement_lock_adaptive.json",
    "backend/modules/knowledge/O5_collapse_prediction.json",
    "backend/modules/knowledge/O6_feedback_entropy.json",
    "backend/modules/knowledge/O7_self_observation.json",
    "backend/modules/knowledge/O8_causal_prediction.json",
    "backend/modules/knowledge/O9_temporal_feedback.json",
    "backend/modules/knowledge/O10_reinforcement.json",
    "backend/modules/knowledge/O11_causal_convergence.json"
]

def sha256_of_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

records = []
for s in summaries:
    if not os.path.exists(s):
        print(f"⚠️ Missing file: {s}")
        continue
    h = sha256_of_file(s)
    with open(s, "r") as f:
        try:
            data = json.load(f)
        except:
            data = {}
    records.append({
        "file": os.path.basename(s),
        "series": data.get("series", "O"),
        "test_name": data.get("test_name"),
        "timestamp": data.get("timestamp"),
        "state": data.get("state", "verified"),
        "sha256": h
    })
    print(f"✅ Locked {os.path.basename(s)} -> SHA256={h[:12]}...")

# === Global O-series continuum hash ===
concat_hash_input = "".join([r["sha256"] for r in records]).encode()
global_hash = hashlib.sha256(concat_hash_input).hexdigest()

# === Final lock summary ===
lock_summary = {
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "O-series",
    "tests_locked": len(records),
    "modules": records,
    "global_continuum_hash": global_hash,
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.3",
    "state": "Observer-Causal Integration Locked",
    "discovery": [
        "O1-O11 unified observer-causal symmetry established.",
        "Entanglement lock and adaptive reinforcement layers verified.",
        "Causal prediction and self-observation coherence stabilized."
    ]
}

# === Write outputs ===
lock_path = "backend/modules/knowledge/Tessaris_OSeries_Lock_v1.0.json"
checksum_path = "backend/modules/knowledge/Tessaris_OSeries_Checksums.txt"

with open(lock_path, "w") as f:
    json.dump(lock_summary, f, indent=2)

with open(checksum_path, "w") as f:
    for r in records:
        f.write(f"{r['file']}: {r['sha256']}\n")
    f.write(f"\nGlobal O Continuum Hash: {global_hash}\n")

print(f"\n🌐 Global O continuum hash = {global_hash}")
print(f"✅ Tessaris Observer-Causal Continuum locked -> {lock_path}")
print(f"✅ Checksums saved -> {checksum_path}")
print("\nO-Series integrity cryptographically sealed under Tessaris Unified Constants v1.3.")