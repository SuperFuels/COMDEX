"""
lock_omega_series_results.py
Consolidates and cryptographically locks all Ω-series results
(Ω4 - Ω6) under the Tessaris Unified Constants v1.2 protocol.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

# === File targets ===
omega_files = [
    "backend/modules/knowledge/Ω4_meta_causal_synchronization_summary.json",
    "backend/modules/knowledge/Ω5_observer_coupling_summary.json",
    "backend/modules/knowledge/Ω6_continuum_echo_summary.json",
]

lock_output = "backend/modules/knowledge/Tessaris_OmegaSeries_Lock_v1.0.json"
checksums_output = "backend/modules/knowledge/Tessaris_OmegaSeries_Checksums.txt"

# === Helper: hash generator ===
def sha256sum(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# === Lock sequence ===
aggregate = {
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "Ω-Series",
    "protocol": "Tessaris Unified Constants v1.2",
    "locked_files": [],
    "global_hash": None,
}

Path(checksums_output).write_text("")  # clear previous

combined = b""
for fpath in omega_files:
    if Path(fpath).exists():
        file_hash = sha256sum(fpath)
        combined += file_hash.encode()
        aggregate["locked_files"].append({
            "file": fpath,
            "sha256": file_hash
        })
        with open(checksums_output, "a") as f:
            f.write(f"{Path(fpath).name} -> SHA256={file_hash}\n")
        print(f"✅ Locked {Path(fpath).name} -> SHA256={file_hash[:12]}...")
    else:
        print(f"⚠️ Missing {fpath} - skipped.")

# === Global continuum hash ===
aggregate["global_hash"] = hashlib.sha256(combined).hexdigest()

# === Save lock file ===
with open(lock_output, "w") as f:
    json.dump(aggregate, f, indent=2)

print("\n🌐 Global Ω continuum hash =", aggregate["global_hash"])
print(f"✅ Tessaris Meta-Causal Continuum locked -> {lock_output}")
print(f"✅ Checksums saved -> {checksums_output}")
print("\nΩ-Series integrity now cryptographically sealed under Tessaris Unified Constants v1.2.")