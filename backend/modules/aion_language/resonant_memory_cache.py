#!/usr/bin/env python3
# ================================================================
# 🧠 Phase 45F.9 - Semantic Memory Stabilization
# ================================================================
"""
Extends the Phase 39B Photon Persistence Layer into a unified,
atomic-safe Resonant Memory Cache (RMC).

Features:
    * Photon + lexical-semantic persistence
    * Φ-ψ-η-Λ tensor integration
    * Atomic JSON writes (no mid-write corruption)
    * Self-verifying saves and drift stabilization

Inputs:
    data/qtensor/langfield_resonance_adapted.qdata.json
Outputs:
    data/memory/resonant_memory_cache.json
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import os
import time
import tempfile
import logging
import shutil
from pathlib import Path
from statistics import mean

from filelock import FileLock, Timeout

QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"
log = logging.getLogger(__name__)

# --- SAVE/IO TUNING (very important for your “startup goes crazy” issue) ---
# Minimum seconds between writes to resonant_memory_cache.json (default 5s)
RMC_SAVE_MIN_INTERVAL_S = float(os.getenv("AION_RMC_SAVE_MIN_INTERVAL_S", "5"))
# Minimum seconds between .bak backups (default 60s)
RMC_BACKUP_MIN_INTERVAL_S = float(os.getenv("AION_RMC_BACKUP_MIN_INTERVAL_S", "60"))

# --- LOG TUNING (reduces “[RMC] ↑ Pushed harmonic sample …” spam) ---
# Minimum seconds between push_sample log lines (per-source) (default 15s)
RMC_PUSH_LOG_MIN_INTERVAL_S = float(os.getenv("AION_RMC_PUSH_LOG_MIN_INTERVAL_S", "15"))
# Set to 0 to disable push_sample logging completely
RMC_ENABLE_PUSH_LOG = os.getenv("AION_RMC_ENABLE_PUSH_LOG", "1").lower() in {"1", "true", "yes", "on"}

# Optional - reinforcement hook
try:
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
except Exception:
    akg = None

ADAPTED_QTENSOR_PATH = Path("data/qtensor/langfield_resonance_adapted.qdata.json")
CACHE_PATH = Path(__file__).resolve().parents[3] / "data/memory/resonant_memory_cache.json"
LOCK_PATH = Path(str(CACHE_PATH) + ".lock")

if not QUIET:
    print(f"[RMC] Using cache path: {CACHE_PATH.resolve()}")


# ================================================================
# 🔒 Utility: Atomic JSON Save
# ================================================================
def atomic_write_json(path: Path, data: dict, *, make_backup: bool = True) -> bool:
    """
    Atomically write verified JSON to disk under a global file lock.

    Backup behavior:
      - Copies existing file to .bak (copy, NOT move) but rate-limited by RMC_BACKUP_MIN_INTERVAL_S.
      - Avoids “rename-to-.bak every write” churn and avoids leaving CACHE_PATH missing if a write fails.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Lock is derived from the path we’re writing (not a global), so alternate cache paths work safely too.
    lock_path = Path(str(path) + ".lock")
    lock = FileLock(str(lock_path))

    try:
        with lock.acquire(timeout=30):
            # Backup (copy) occasionally
            if make_backup and path.exists():
                bak = path.with_suffix(".bak")
                try:
                    do_backup = True
                    if bak.exists():
                        age = time.time() - bak.stat().st_mtime
                        if age < RMC_BACKUP_MIN_INTERVAL_S:
                            do_backup = False
                    if do_backup:
                        shutil.copy2(path, bak)
                        if (not QUIET) and RMC_ENABLE_PUSH_LOG:
                            log.info(f"[RMC] 💾 Backup created -> {bak}")
                except Exception as e:
                    log.warning(f"[RMC] ⚠ Could not create backup: {e}")

            # Write to temp file
            tmp = tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                dir=path.parent,
                suffix=".tmp",
                encoding="utf-8",
            )
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()

            # Validate before commit
            try:
                json.loads(Path(tmp.name).read_text(encoding="utf-8"))
            except Exception as ve:
                log.error(f"[RMC] ❌ Validation failed before commit: {ve}")
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
                return False

            # Atomic replace
            os.replace(tmp.name, path)
            return True

    except Timeout:
        log.warning("[RMC] ⚠ Cache locked - another process is writing, skipping save.")
        return False


# ================================================================
# 🧩 Auto-Recovery Bootstrap - Phase 45G.14
# ================================================================
def _auto_recover_json(path: Path, fallback: Optional[dict] = None):
    """
    Auto-repair loader for JSON memory files.

    - If file is missing -> create new.
    - If file corrupt -> move to .corrupt + restore from .bak or recreate clean.
    - Returns the JSON root (dict/list) without flattening away schema, so load() can
      decide how to interpret legacy vs structured formats.
    """
    fallback = fallback or {}
    path = Path(path)

    if not path.exists():
        log.warning(f"[Recovery] Missing {path.name}, creating new.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    except Exception as e:
        log.error(f"[Recovery] ⚠ Corruption in {path.name}: {e}")
        corrupt = path.with_suffix(".corrupt")
        backup = path.with_suffix(".bak")

        try:
            os.replace(path, corrupt)
            log.warning(f"[Recovery] Renamed bad file -> {corrupt}")
        except Exception:
            pass

        if backup.exists():
            log.info(f"[Recovery] Restoring from backup -> {backup}")
            try:
                data = json.loads(backup.read_text(encoding="utf-8"))
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
            except Exception as e2:
                log.warning(f"[Recovery] Backup restore failed: {e2}")

        log.warning("[Recovery] No usable backup found; creating clean file.")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback


def _abs(p: Path) -> Path:
    return Path(os.path.abspath(str(p)))


# ================================================================
# 🧠 ResonantMemoryCache
# ================================================================
class ResonantMemoryCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.last_update: Optional[float] = None

        # save + log throttles
        self._last_save_ts: float = 0.0
        self._last_push_log_ts: Dict[str, float] = {}

        self.load()

    # ------------------------------------------------------------
    def load(self):
        """Auto-recover and load existing cache safely (no silent re-init)."""
        global CACHE_PATH
        CACHE_PATH = _abs(CACHE_PATH)  # lock to absolute path

        # Create once if missing, with proper schema
        if not CACHE_PATH.exists():
            fallback = {
                "timestamp": 0,
                "entries": 0,
                "cache": {},
                "meta": {
                    "schema": "ResonantMemoryCache.v2",
                    "desc": "Unified photon + semantic Φ-ψ-η-Λ resonance cache",
                },
            }
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(fallback, f, indent=2)
            log.warning(f"[RMC] Creating new cache (first run) -> {CACHE_PATH}")

        raw = _auto_recover_json(CACHE_PATH, fallback={})

        # Supported formats:
        # 1) Structured v2: {"timestamp":..., "entries":..., "cache": {...}, "meta":...}
        # 2) Older dict: { key: entry, ... }
        # 3) Legacy list: [entry, entry, ...]
        if isinstance(raw, dict):
            if "cache" in raw and isinstance(raw.get("cache"), dict):
                self.cache = raw["cache"]
                self.last_update = float(raw.get("timestamp") or time.time())
            elif "entries" in raw and isinstance(raw.get("entries"), (list, dict)):
                ent = raw["entries"]
                if isinstance(ent, dict):
                    self.cache = ent
                else:
                    self.cache = {f"item_{i}": v for i, v in enumerate(ent)}
                self.last_update = float(raw.get("timestamp") or time.time())
            else:
                # Treat as dict-of-entries
                self.cache = raw
                # If this dict also happened to include timestamp/meta keys, keep timestamp if present.
                ts = raw.get("timestamp")
                self.last_update = float(ts) if isinstance(ts, (int, float)) else time.time()

        elif isinstance(raw, list):
            self.cache = {f"item_{i}": v for i, v in enumerate(raw)}
            self.last_update = time.time()

        else:
            log.warning(f"[RMC] Unexpected cache format: {type(raw)}; creating empty cache.")
            self.cache = {}
            self.last_update = time.time()

        if not QUIET:
            log.info(f"[RMC] ✅ Initialized ResonantMemoryCache with {len(self.cache)} entries")

    # ------------------------------------------------------------
    def save(self, force: bool = False) -> bool:
        """
        Thread-/process-safe JSON save with backup and lock.

        IMPORTANT:
          This is rate-limited to avoid runaway IO when other modules call rmc.save()
          inside heartbeat/startup loops. Set AION_RMC_SAVE_MIN_INTERVAL_S to tune.
        """
        if not isinstance(self.cache, dict):
            log.warning("[RMC] ⚠ Skip save - cache not a dict.")
            return False

        now = time.time()
        if (not force) and (now - self._last_save_ts) < RMC_SAVE_MIN_INTERVAL_S:
            return False

        self.last_update = now
        data = {
            "timestamp": self.last_update,
            "entries": len(self.cache),
            "cache": self.cache,
            "meta": {
                "schema": "ResonantMemoryCache.v2",
                "desc": "Unified photon + semantic Φ-ψ-η-Λ resonance cache",
            },
        }

        ok = atomic_write_json(CACHE_PATH, data, make_backup=True)
        if ok:
            self._last_save_ts = now
        return ok

    # ------------------------------------------------------------
    def lookup(self, wid: str):
        """Lookup a concept or photon entry with normalization."""
        wid = (wid or "").lower().strip()
        if wid in self.cache:
            return self.cache[wid]
        for k in list(self.cache.keys()):
            if isinstance(k, str) and k.lower().startswith(wid):
                return self.cache[k]
        return None

    # ------------------------------------------------------------
    def update_from_photons(self, photons: list):
        """Integrate new photons into persistence cache."""
        now = time.time()
        for p in photons:
            if not isinstance(p, dict):
                continue
            cid = p.get("λ", "unknown")
            entry = self.cache.get(
                cid,
                {
                    "count": 0,
                    "avg_phase": 0.0,
                    "avg_goal": 0.0,
                    "coherence": 0.0,
                    "last_seen": 0.0,
                },
            )
            entry["count"] += 1
            entry["avg_phase"] = round(
                (entry["avg_phase"] * (entry["count"] - 1) + p.get("φ", 0.0))
                / entry["count"],
                3,
            )
            entry["avg_goal"] = round(
                (entry["avg_goal"] * (entry["count"] - 1) + p.get("μ", 0.0))
                / entry["count"],
                3,
            )
            entry["coherence"] = round(
                mean([entry["avg_phase"], 1 - abs(0.5 - entry["avg_goal"])]), 3
            )
            entry["last_seen"] = now
            self.cache[cid] = entry

            # === ✅ Semantic resonance overlay ===
            sem = p.get("semantics", {})
            if isinstance(sem, dict):
                rho = sem.get("rho")
                I = sem.get("I")
                sqi = sem.get("SQI")

                if rho is not None:
                    entry["rho"] = round(float(rho), 4)
                if I is not None:
                    entry["intensity"] = round(float(I), 4)
                if sqi is not None:
                    entry["SQI"] = round(float(sqi), 4)

                lemma = p.get("lemma") or cid
                glyph = p.get("glyph") or cid
                if glyph != lemma and sqi is not None:
                    self.update_resonance_link(lemma, glyph, sqi, save=False)

        self.save()
        if not QUIET:
            log.info(f"[RMC] Updated cache with {len(photons)} photon entries.")
        return self.cache

    # ------------------------------------------------------------
    def update_resonance_link(self, a: str, b: str, sqi: float, *, weight: float = 1.0, save: bool = True):
        """Create or reinforce a resonance link a↔b."""
        try:
            a_norm = (a or "").strip().lower()
            b_norm = (b or "").strip().lower()
            if not a_norm or not b_norm or a_norm == b_norm:
                return

            key = "↔".join(sorted((a_norm, b_norm)))
            links = self.cache.setdefault("links", {})
            entry = links.get(key, {"count": 0, "SQI_avg": 0.0})

            sqi = max(0.0, min(1.0, float(sqi)))
            w = max(0.0, float(weight))

            prev_count = float(entry.get("count", 0))
            prev_avg = float(entry.get("SQI_avg", 0.0))
            new_count = prev_count + w if w > 0 else prev_count
            if new_count == 0:
                new_avg = sqi
                new_count = w if w > 0 else 1.0
            else:
                new_avg = (prev_avg * prev_count + sqi * w) / new_count

            entry.update({
                "SQI_avg": round(new_avg, 3),
                "count": new_count,
                "last_sqi": sqi,
                "last_updated": time.time(),
            })
            links[key] = entry

            if save:
                self.save()

            if not QUIET:
                log.info(f"[RMC] Linked {a_norm}↔{b_norm} -> SQI_avg={entry['SQI_avg']}, count={entry['count']:.2f}")

        except Exception as e:
            log.warning(f"[RMC] Failed to link {a}↔{b}: {e}")

    # ------------------------------------------------------------
    def reinforce_AKG(self, weight: float = 0.2):
        """Apply persistent reinforcement to AKG."""
        if not akg:
            log.warning("[RMC] AKG reinforcement skipped (module not loaded).")
            return
        for cid, entry in self.cache.items():
            if not isinstance(entry, dict):
                continue
            w = min(
                1.0,
                weight * entry.get("coherence", 0.5) * entry.get("count", 1) / 5,
            )
            akg.add_triplet(cid, "resonance_weight", str(round(w, 3)))
        if not QUIET:
            log.info(f"[RMC] Reinforced {len(self.cache)} cached concepts in AKG.")

    # ------------------------------------------------------------
    def _safe_load(self, path: Path):
        """
        Safely load a JSON file.
        - Returns {} on failure.
        - Supports both flat and structured cache formats.
        """
        if not path.exists():
            log.warning(f"[RMC] Missing file: {path}")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Support structured cache variant
            if isinstance(data, dict) and "cache" in data and isinstance(data.get("cache"), dict):
                return data

            if not isinstance(data, (list, dict)):
                log.warning(f"[RMC] Unexpected data type {type(data)} in {path.name}")
                return {}

            log.info(f"[RMC] Safely loaded {len(data) if isinstance(data, list) else len(list(data))} entries (structured ok)")
            return data

        except Exception as e:
            log.warning(f"[RMC] Failed to read {path}: {e}")
            return {}

    def ingest_tensors(self):
        """Load adapted QTensor and merge into memory cache."""
        data = self._safe_load(ADAPTED_QTENSOR_PATH)
        # allow either {"tensor_field": {...}} or direct tensor dict
        tensor = data.get("tensor_field", {}) if isinstance(data, dict) else {}
        if not tensor:
            log.warning("[RMC] No tensor data found to ingest.")
            return

        timestamp = time.time()
        for wid, t in tensor.items():
            if not isinstance(t, dict):
                continue
            self.cache[wid] = {
                "Φ": t.get("Φ", 1.0),
                "ψ": t.get("ψ", 1.0),
                "η": t.get("η", 1.0),
                "Λ": t.get("Λ", 1.0),
                "q_val": t.get("q_val", 1.0),
                "phase": t.get("phase", 0.0),
                "stability": 1.0,
                "last_update": timestamp,
            }

        self.last_update = timestamp
        self.save(force=True)
        if not QUIET:
            log.info(f"[RMC] Ingested {len(tensor)} tensor entries into cache.")

    def stabilize(self, decay_rate: float = 0.001):
        """Apply slow decay to simulate semantic drift stabilization."""
        if not self.cache:
            log.warning("[RMC] No memory to stabilize.")
            return
        for _, m in self.cache.items():
            if isinstance(m, dict) and "stability" in m:
                m["stability"] = round(m["stability"] * (1 - decay_rate), 6)
        self.save()
        if not QUIET:
            log.info(f"[RMC] Applied stability decay: rate={decay_rate}")

    def recall(self, wid: str):
        """Retrieve stabilized tensor or photon entry for given id."""
        return self.cache.get((wid or "").lower())

    def set(self, key: str, value: Any):
        """Store a value in the in-memory cache and persist to disk."""
        self.cache[key] = value
        try:
            self.save()
            if (not QUIET) and RMC_ENABLE_PUSH_LOG:
                print(f"[RMC] 💾 Set key='{key}'")
        except Exception as e:
            print(f"[RMC] ⚠️ Failed to persist key='{key}': {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from cache (with default)."""
        return self.cache.get(key, default)

    def export(self):
        """Export unified cache with schema + timestamp under a file lock."""
        data = {
            "timestamp": self.last_update or time.time(),
            "entries": len(self.cache),
            "cache": self.cache,
            "meta": {
                "schema": "ResonantMemoryCache.v2",
                "desc": "Unified photon + semantic Φ-ψ-η-Λ resonance cache",
            },
        }
        lock = FileLock(str(LOCK_PATH))
        try:
            with lock.acquire(timeout=30):
                atomic_write_json(CACHE_PATH, data, make_backup=True)
                if not QUIET:
                    log.info(f"[RMC] ✅ Exported unified cache -> {CACHE_PATH}")
        except Timeout:
            if not QUIET:
                log.warning("[RMC] ⚠ Cache locked - export skipped.")

    # ------------------------------------------------------------
    # 🌀 Phase 53 - Harmonic Resonance Tracking
    # ------------------------------------------------------------
    def push_sample(self, rho: float, entropy: float, sqi: float, delta: float, source: str = "unknown"):
        """
        Append a resonance feedback sample (ρ, Ī, SQI, ΔΦ) into cache history.

        NOTE:
          Uses save() which is globally rate-limited (AION_RMC_SAVE_MIN_INTERVAL_S),
          so callers in fast loops won’t hammer disk anymore.

          Logging is also rate-limited per-source (AION_RMC_PUSH_LOG_MIN_INTERVAL_S)
          to avoid console spam.
        """
        try:
            src_name = (source or "unknown").strip() or "unknown"
            src = f"harmonics::{src_name}"
            entry = self.cache.get(src, {"samples": [], "avg": {}})

            entry["samples"].append({
                "timestamp": time.time(),
                "ρ": round(float(rho), 3),
                "Ī": round(float(entropy), 3),
                "SQI": round(float(sqi), 3),
                "ΔΦ": round(float(delta), 3),
            })
            if len(entry["samples"]) > 200:
                entry["samples"] = entry["samples"][-200:]

            sqis = [s["SQI"] for s in entry["samples"]]
            deltas = [s["ΔΦ"] for s in entry["samples"]]
            entry["avg"] = {
                "ρ": round(sum(s["ρ"] for s in entry["samples"]) / len(entry["samples"]), 3),
                "Ī": round(sum(s["Ī"] for s in entry["samples"]) / len(entry["samples"]), 3),
                "SQI": round(sum(sqis) / len(sqis), 3),
                "ΔΦ": round(sum(deltas) / len(deltas), 3),
                "count": len(entry["samples"]),
            }

            self.cache[src] = entry
            self.last_update = time.time()

            # write (rate-limited)
            self.save()

            # log (rate-limited per-source)
            if (not QUIET) and RMC_ENABLE_PUSH_LOG:
                now = time.time()
                last = self._last_push_log_ts.get(src_name, 0.0)
                if (now - last) >= RMC_PUSH_LOG_MIN_INTERVAL_S:
                    log.info(f"[RMC] ↑ Pushed harmonic sample from {src_name} -> SQI={float(sqi):.3f}, ΔΦ={float(delta):.3f}")
                    self._last_push_log_ts[src_name] = now

        except Exception as e:
            log.warning(f"[RMC] push_sample error ({source}): {e}")

    # ------------------------------------------------------------
    def average_sqi(self) -> float:
        """Compute the average SQI from the cache. Returns 0.5 if empty."""
        try:
            if not isinstance(self.cache, dict) or not self.cache:
                return 0.5
            sqis = []
            for _, v in self.cache.items():
                if isinstance(v, dict):
                    val = v.get("sqi") or v.get("stability")
                    if isinstance(val, (int, float)):
                        sqis.append(float(val))
            return round(sum(sqis) / len(sqis), 3) if sqis else 0.5
        except Exception as e:
            logging.getLogger(__name__).warning(f"[RMC] average_sqi() failed: {e}")
            return 0.5

    # ------------------------------------------------------------
    def export_harmonic_profile(self) -> dict:
        """Summarized harmonic snapshot across all sources."""
        summary = {}
        try:
            for k, v in self.cache.items():
                if not isinstance(k, str) or not k.startswith("harmonics::") or not isinstance(v, dict):
                    continue
                avg = v.get("avg", {})
                summary[k.split("::")[-1]] = {
                    "avg_SQI": avg.get("SQI", 0),
                    "avg_ΔΦ": avg.get("ΔΦ", 0),
                    "count": avg.get("count", 0),
                }
        except Exception as e:
            log.warning(f"[RMC] export_harmonic_profile error: {e}")
        return summary

    # ------------------------------------------------------------
    def summarize_latest(self) -> dict:
        """Flattened latest resonance view suitable for dashboard updates."""
        profiles = self.export_harmonic_profile()
        overall_sqi = round(
            sum(v["avg_SQI"] for v in profiles.values()) / max(len(profiles), 1), 3
        )
        overall_delta = round(
            sum(v["avg_ΔΦ"] for v in profiles.values()) / max(len(profiles), 1), 3
        )
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "profiles": profiles,
            "overall_SQI": overall_sqi,
            "overall_ΔΦ": overall_delta,
        }

    def summary(self) -> dict:
        """Return a compact snapshot summary of the current RMC state."""
        return {
            "entries": len(self.cache),
            "last_update": getattr(self, "last_update", None),
            "avg_stability": self.get_average("stability"),
            "avg_entropy": self.get_average("entropy"),
            "avg_sqi": self.get_average("SQI"),
        }

    def get_average(self, key: str) -> Optional[float]:
        """Compute the mean value of a given numeric field across all cache entries."""
        vals = []
        for v in self.cache.values():
            if isinstance(v, dict) and key in v:
                try:
                    vals.append(float(v[key]))
                except (ValueError, TypeError):
                    continue
        return (sum(vals) / len(vals)) if vals else None


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rmc = ResonantMemoryCache()
    rmc.ingest_tensors()
    rmc.stabilize(decay_rate=0.001)
    rmc.export()
    print("✅ Resonant Memory Cache stabilization complete.")