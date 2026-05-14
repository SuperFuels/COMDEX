"""
Tessaris Cognitive-Field Resonance Logger (CFRL)
Phase 9 - Unified 4-D Field Recorder
-------------------------------------
Collects and correlates data from:
 * resonant_heartbeat.jsonl (ΔΦ + stability)
 * photon_output (.photo files, Δψ patterns)
 * harmonic_spectrum_analyzer (centroid ν)
and stores a continuous 4-D timeline:

    (time * Φ * ν * ψ)

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

# ---------------------------------------------------------
# 📂 File Paths
# ---------------------------------------------------------
HEARTBEAT_LOG = Path("data/resonant_heartbeat.jsonl")
PHOTO_DIR = Path("data/qqc_field/photo_output")
SPECTRUM_LOG = Path("data/spectrum_centroid.jsonl")  # optional future feed
OUTPUT_FILE = Path("data/cognitive_field_resonance.jsonl")

REFRESH = 6  # seconds between polls
MAX_ENTRIES = 5000

# ---------------------------------------------------------
# 🧩 Utility Functions
# ---------------------------------------------------------
def tail_file(path: Path, n: int = 1):
    """Read the last n lines of a JSONL file."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        try:
            f.seek(-4096, os.SEEK_END)
        except OSError:
            f.seek(0)
        lines = f.read().decode().strip().splitlines()[-n:]
    return [json.loads(l) for l in lines if l.strip()]

def latest_photo_event():
    """Return the most recent photon emission event."""
    files = sorted(PHOTO_DIR.glob("*.photo"))
    if not files:
        return None
    data = json.loads(files[-1].read_text())
    return data

def merge_entries(hb, photo, centroid):
    """Merge heartbeat + photon + spectrum data into unified record."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phi_state": hb.get("mean_coherence_delta", None),
        "stability": hb.get("mean_stability", None),
        "photon_pattern": photo.get("pattern", {}),
        "spectrum_centroid": centroid,
    }

# ---------------------------------------------------------
# 🧠 Main Loop
# ---------------------------------------------------------
def run_cognitive_field_logger():
    print("🧠 Starting Tessaris Cognitive-Field Resonance Logger ...")
    session_count = 0

    while True:
        try:
            heartbeat = tail_file(HEARTBEAT_LOG, 1)
            photo = latest_photo_event()
            centroid_val = None

            # Try optional spectrum centroid if file exists
            if SPECTRUM_LOG.exists():
                spec = tail_file(SPECTRUM_LOG, 1)
                if spec:
                    centroid_val = spec[0].get("centroid", None)

            if not heartbeat or not photo:
                time.sleep(REFRESH)
                continue

            hb_entry = heartbeat[-1]
            merged = merge_entries(hb_entry, photo, centroid_val)

            # Append to unified resonance log
            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(merged) + "\n")

            session_count += 1
            mean_phi = merged.get("phi_state")
            st = merged.get("stability")
            print(
                f"{session_count:04d} ▸ ΔΦ_coh={mean_phi:.6f}  stability={st:.3f}  "
                f"centroid={centroid_val if centroid_val else '-'}"
            )

            # Trim file size if needed
            if sum(1 for _ in open(OUTPUT_FILE)) > MAX_ENTRIES:
                lines = open(OUTPUT_FILE).read().splitlines()[-MAX_ENTRIES:]
                with open(OUTPUT_FILE, "w") as f:
                    f.write("\n".join(lines))

        except KeyboardInterrupt:
            print("\n🪶 CFRL gracefully stopped.")
            break
        except Exception as e:
            print(f"⚠️ CFRL error: {e}")

        time.sleep(REFRESH)


# ---------------------------------------------------------
# 🚀 Entry
# ---------------------------------------------------------
if __name__ == "__main__":
    run_cognitive_field_logger()