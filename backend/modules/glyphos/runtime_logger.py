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

def _rotate_log():
    """Rotate and gzip log if too large."""
    if not os.path.exists(LOG_FILE):
        return

    size_mb = os.path.getsize(LOG_FILE) / 1_000_000
    if size_mb > MAX_SIZE_MB:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archived = os.path.join(LOG_DIR, f"glyph_triggers_{timestamp}.log.gz")
        with open(LOG_FILE, "rb") as f_in, gzip.open(archived, "wb") as f_out:
            f_out.writelines(f_in)
        os.remove(LOG_FILE)

def log_glyph_trace(glyph: str, metadata: dict):
    """Log a glyph trigger event to disk."""
    _rotate_log()
    event = {
        "time": datetime.utcnow().isoformat(),
        "glyph": glyph,
        "metadata": metadata
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")