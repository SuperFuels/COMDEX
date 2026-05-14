#!/usr/bin/env python3
# ================================================================
# 🧠 Phase 45F.11 - Verified Rebuild of Resonant Memory Cache (with Locking)
# ================================================================
"""
Rebuilds the Resonant Memory Cache (RMC) from LexMemory data
under strict atomic and concurrency-safe conditions.

Features:
  * Exclusive file lock during rebuild (prevents concurrent writes)
  * Verified JSON structure before commit
  * Backup + fallback recovery for cache and lex data
  * JSON-serializable enforcement for all values
"""

import json, os, tempfile, time, logging, shutil
from pathlib import Path
from filelock import FileLock, Timeout  # 🔒 concurrency protection

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Standard Aion Memory Paths
LEX_PATH = Path("data/memory/cee_lex_memory.json")
CACHE_PATH = Path("data/memory/resonant_memory_cache.json")
LOCK_PATH = Path(str(CACHE_PATH) + ".lock")

# ============================================================
# 🔒 Atomic + Verified JSON Writer
# ============================================================
def atomic_write_json(path: Path, data: dict):
    """Safely write JSON with full validation and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Backup if existing file is present
    if path.exists():
        bak = path.with_suffix(".bak")
        try:
            shutil.copy2(path, bak)
            log.info(f"[Rebuild] 💾 Backup saved -> {bak}")
        except Exception as e:
            log.warning(f"[Rebuild] ⚠ Could not backup cache: {e}")

    # 2. Write to a temporary file first
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, suffix=".tmp")
    try:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno()) # Ensure data is physically on disk
        tmp.close()

        # 3. Verify JSON integrity by reading it back
        with open(tmp.name, 'r', encoding="utf-8") as f:
            json.loads(f.read())
            
        # 4. Atomic Replace (Standard OS level rename)
        os.replace(tmp.name, path)
        log.info(f"[Rebuild] ✅ Atomic save verified -> {path}")
        
    except Exception as e:
        log.error(f"[Rebuild] ❌ Validation failed, aborting write: {e}")
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise

# ============================================================
# 🧩 Safe Value Conversion
# ============================================================
def safe_value(v):
    """Ensure all exported values are JSON-serializable to avoid encoding errors."""
    if isinstance(v, (float, int, str, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [safe_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): safe_value(val) for k, val in v.items()}
    return str(v)

# ============================================================
# 🔁 Rebuild Routine
# ============================================================
def rebuild():
    """
    Main Logic: Rebuilds RMC by mapping the current LexMemory state 
    to fresh resonance profiles.
    """
    if not LEX_PATH.exists():
        log.error(f"[Rebuild] Critical: LexMemory missing at {LEX_PATH}")
        return 0

    try:
        lex_data = json.loads(LEX_PATH.read_text(encoding="utf-8"))
        log.info(f"[Rebuild] Loaded LexMemory with {len(lex_data)} entries.")
    except Exception as e:
        corrupt = LEX_PATH.with_suffix(".corrupt")
        os.replace(LEX_PATH, corrupt)
        log.error(f"[Rebuild] ⚠ LexMemory corrupt ({e}) -> moved to {corrupt}")
        lex_data = {}

    cache = {}
    now = time.time()
    
    # Map raw lexemes to resonance entries
    for k, v in lex_data.items():
        # Initialize with baseline resonance metrics
        cache[str(k)] = {
            "count": 1,
            "avg_phase": 0.5,
            "avg_goal": 0.5,
            "coherence": 0.5,
            "last_seen": now,
            "source": "lexmemory",
        }

    # Wrap in standard RMC schema
    result = {
        "timestamp": now,
        "entries": len(cache),
        "cache": cache,
        "meta": {
            "schema": "ResonantMemoryCache.v2",
            "desc": "Rebuilt from LexMemory - atomic verified save",
        },
    }

    # 🔒 Lock acquisition to prevent race conditions with the 
    # ResonantDriftMonitor or HarmonicStabilizerEngine.
    lock = FileLock(str(LOCK_PATH))
    try:
        with lock.acquire(timeout=30):
            atomic_write_json(CACHE_PATH, safe_value(result))
            log.info(f"[Rebuild] ✅ Wrote {len(cache)} entries under lock.")
            return len(cache)
    except Timeout:
        log.warning(f"[Rebuild] ⚠ Another process is writing - rebuild timed out.")
        return 0

# ============================================================
# 🧪 CLI Entry
# ============================================================
if __name__ == "__main__":
    print("🧠 Starting Phase 45F.11 Rebuild...")
    try:
        n = rebuild()
        if n > 0:
            print(f"🧩 Rebuild complete: {n} resonance entries written safely.")
        else:
            print("⚠ Rebuild skipped or no data found.")
    except Exception as e:
        print(f"❌ Rebuild failed with exception: {e}")