# backend/modules/glyphos/runtime_logger.py
# Logs glyph-triggered behavior to rotating trace file

import os
import json
import gzip
from datetime import datetime

LOG_DIR = "runtime_traces"
LOG_FILE = os.path.join(LOG_DIR, "glyph_triggers.log")
MAX_SIZE_MB = 5

os.makedirs(LOG_DIR, exist_ok=True)

def _rotate_log(log_file: str = LOG_FILE, max_size_mb: int = MAX_SIZE_MB):
    """Rotate and gzip log if too large."""
    if not os.path.exists(log_file):
        return

    size_mb = os.path.getsize(log_file) / 1_000_000
    if size_mb > max_size_mb:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archived = os.path.join(LOG_DIR, f"glyph_triggers_{timestamp}.log.gz")
        with open(log_file, "rb") as f_in, gzip.open(archived, "wb") as f_out:
            f_out.writelines(f_in)
        os.remove(log_file)
        print(f"[📦] Rotated log file -> {archived}")

def log_glyph_trace(glyph: str, metadata: dict, log_file: str = LOG_FILE):
    """Log a glyph trigger event to disk."""
    try:
        _rotate_log(log_file)
        event = {
            "time": datetime.utcnow().isoformat(),
            "glyph": glyph,
            "metadata": metadata
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
        print(f"[📌] Logged glyph '{glyph}' trace event.")
    except Exception as e:
        print(f"[❌] Failed to log glyph trace: {e}")