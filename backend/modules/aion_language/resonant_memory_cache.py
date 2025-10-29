#!/usr/bin/env python3
# ================================================================
# 🧠 Phase 45F.9 — Semantic Memory Stabilization
# ================================================================
"""
Extends the Phase 39B Photon Persistence Layer into a unified,
atomic-safe Resonant Memory Cache (RMC).

Features:
    • Photon + lexical–semantic persistence
    • Φ–ψ–η–Λ tensor integration
    • Atomic JSON writes (no mid-write corruption)
    • Self-verifying saves and drift stabilization

Inputs:
    data/qtensor/langfield_resonance_adapted.qdata.json
Outputs:
    data/memory/resonant_memory_cache.json
"""
from typing import Any
import json, os, time, tempfile, logging
from pathlib import Path
from statistics import mean
from filelock import FileLock, Timeout
QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"
log = logging.getLogger(__name__)

# Optional — reinforcement hook
try:
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
except Exception:
    akg = None

ADAPTED_QTENSOR_PATH = Path("data/qtensor/langfield_resonance_adapted.qdata.json")
CACHE_PATH = Path(__file__).resolve().parents[3] / "data/memory/resonant_memory_cache.json"
if not QUIET:
    print(f"[RMC] Using cache path: {CACHE_PATH.resolve()}")
LOCK_PATH = Path(str(CACHE_PATH) + ".lock")

# ================================================================
# 🔒 Utility: Atomic JSON Save
# ================================================================
def atomic_write_json(path: Path, data: dict):
    """Atomically write verified JSON to disk under a global file lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(LOCK_PATH))

    try:
        with lock.acquire(timeout=30):
            tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, suffix=".tmp")
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()

            # Validate before replace
            try:
                json.loads(Path(tmp.name).read_text(encoding="utf-8"))
            except Exception as ve:
                log.error(f"[RMC] ❌ Validation failed before commit: {ve}")
                os.unlink(tmp.name)
                return False

            os.replace(tmp.name, path)

            # Create a simple backup copy
            bak = path.with_suffix(".bak")
            try:
                Path(path).write_text(Path(path).read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

            if not QUIET:
                log.info(f"[RMC] 💾 Backup created → {bak}")
            return True

    except Timeout:
        log.warning(f"[RMC] ⚠ Cache locked — another process is writing, skipping save.")
        return False

# ================================================================
# 🧩 Auto-Recovery Bootstrap — Phase 45G.14
# ================================================================
def _auto_recover_json(path: Path, fallback: dict = None):
    """
    Auto-repair loader for JSON memory files.
    - If file is missing → create new.
    - If file corrupt → move to .corrupt + restore from .bak or recreate clean.
    - Supports structured cache format ({"timestamp":..., "cache": {...}}).
    """
    fallback = fallback or {}
    if not path.exists():
        log.warning(f"[Recovery] Missing {path.name}, creating new.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 🔍 Handle both flat and structured formats
        if isinstance(data, dict):
            if "cache" in data:
                cache_data = data["cache"]
                # Some structured caches use dict-of-dicts
                if isinstance(cache_data, dict):
                    cache_data = list(cache_data.values())
                data = cache_data
            elif "entries" in data and isinstance(data["entries"], (list, dict)):
                # Alternate form with 'entries' key
                ent = data["entries"]
                data = list(ent.values()) if isinstance(ent, dict) else ent
            else:
                data = list(data.values())

        if not isinstance(data, list):
            log.warning(f"[Recovery] Unexpected JSON root type ({type(data)}), using fallback.")
            data = fallback

        if not QUIET:
            log.info(f"[RMC] Loaded {len(data)} entries (from structured cache)")
        return data

    except Exception as e:
        log.error(f"[Recovery] ⚠ Corruption in {path.name}: {e}")
        corrupt = path.with_suffix(".corrupt")
        backup = path.with_suffix(".bak")

        try:
            os.replace(path, corrupt)
            log.warning(f"[Recovery] Renamed bad file → {corrupt}")
        except Exception:
            pass

        if backup.exists():
            log.info(f"[Recovery] Restoring from backup → {backup}")
            data = json.loads(backup.read_text(encoding="utf-8"))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return data

        log.warning(f"[Recovery] No backup found; creating clean file.")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback

# --- helper (place above the class, near CACHE_PATH etc.) ---
def _abs(p: Path) -> Path:
    return Path(os.path.abspath(str(p)))

# ================================================================
# 🧠 ResonantMemoryCache
# ================================================================
class ResonantMemoryCache:
    def __init__(self):
        self.cache = {}
        self.last_update = None
        self.load()

    # ------------------------------------------------------------
    def load(self):
        """Auto-recover and load existing cache safely (no silent re-init)."""
        global CACHE_PATH
        CACHE_PATH = _abs(CACHE_PATH)  # lock to absolute path
        log.info(f"[RMC] Using cache path: {CACHE_PATH}")

        # Create once if missing, with proper schema
        if not CACHE_PATH.exists():
            fallback = {
                "timestamp": 0,
                "entries": 0,
                "cache": {},
                "meta": {
                    "schema": "ResonantMemoryCache.v2",
                    "desc": "Unified photon + semantic Φ–ψ–η–Λ resonance cache",
                },
            }
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(fallback, f, indent=2)
            log.warning(f"[RMC] Creating new cache (first run) → {CACHE_PATH}")

        # Load once, using recovery logic
        raw = _auto_recover_json(CACHE_PATH)

        # 🧠 Handle all known formats
        if isinstance(raw, dict):
            if "cache" in raw:
                self.cache = raw["cache"]
            elif "entries" in raw:
                # structured dict with entries
                ent = raw["entries"]
                self.cache = ent if isinstance(ent, dict) else {f"item_{i}": v for i, v in enumerate(ent)}
            else:
                self.cache = raw
            self.last_update = raw.get("timestamp", time.time())
        elif isinstance(raw, list):
            # convert flat list into keyed dict
            self.cache = {f"item_{i}": v for i, v in enumerate(raw)}
            self.last_update = time.time()
        else:
            log.warning(f"[RMC] Unexpected cache format: {type(raw)}; creating empty cache.")
            self.cache = {}
            self.last_update = time.time()

        if not QUIET:
            log.info(f"[RMC] ✅ Initialized ResonantMemoryCache with {len(self.cache)} entries")

    # ------------------------------------------------------------
    def save(self):
        """Thread-/process-safe JSON save with backup and lock."""
        if not isinstance(self.cache, dict):
            log.warning("[RMC] ⚠ Skip save — cache not a dict.")
            return

        self.last_update = time.time()
        data = {
            "timestamp": self.last_update,
            "entries": len(self.cache),
            "cache": self.cache,
            "meta": {
                "schema": "ResonantMemoryCache.v2",
                "desc": "Unified photon + semantic Φ–ψ–η–Λ resonance cache",
            },
        }

        # Backup before save
        if CACHE_PATH.exists():
            bak = CACHE_PATH.with_suffix(".bak")
            try:
                os.replace(CACHE_PATH, bak)
                if not QUIET:
                    log.info(f"[RMC] 💾 Backup created → {bak}")
            except Exception as e:
                log.warning(f"[RMC] ⚠ Could not backup cache: {e}")

        atomic_write_json(CACHE_PATH, data)

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

        self.save()
        if not QUIET:
            log.info(f"[RMC] Updated cache with {len(photons)} photon entries.")
        return self.cache

    # ------------------------------------------------------------
    def update_resonance_link(self, a: str, b: str, sqi: float, *, weight: float = 1.0, save: bool = True):
        """
        Create or reinforce a resonance link a↔b.

        - Canonicalizes the key so a↔b == b↔a (sorted, lowercased).
        - SQI is clamped to [0, 1].
        - 'weight' lets you up/down-weight this sample (default 1.0).
        - Persists immediately unless save=False.
        """
        try:
            # Normalize / canonicalize (avoid self-links)
            a_norm = (a or "").strip().lower()
            b_norm = (b or "").strip().lower()
            if not a_norm or not b_norm or a_norm == b_norm:
                return

            key = "↔".join(sorted((a_norm, b_norm)))
            links = self.cache.setdefault("links", {})

            # Ensure structure
            entry = links.get(key, {"count": 0, "SQI_avg": 0.0})

            # Clamp inputs
            sqi = max(0.0, min(1.0, float(sqi)))
            w = max(0.0, float(weight))

            # Incremental weighted mean
            prev_count = float(entry.get("count", 0))
            prev_avg = float(entry.get("SQI_avg", 0.0))
            new_count = prev_count + w if w > 0 else prev_count
            if new_count == 0:
                new_avg = sqi
                new_count = w if w > 0 else 1.0
            else:
                new_avg = (prev_avg * prev_count + sqi * w) / new_count

            # Update entry
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
                log.info(f"[RMC] Linked {a_norm}↔{b_norm} → SQI_avg={entry['SQI_avg']}, count={entry['count']:.2f}")

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

            # 🔍 Handle structured cache variants
            if isinstance(data, dict):
                if "cache" in data:
                    cache_data = data["cache"]
                    if isinstance(cache_data, dict):
                        cache_data = list(cache_data.values())
                    data = cache_data
                elif "entries" in data and isinstance(data["entries"], (list, dict)):
                    ent = data["entries"]
                    data = list(ent.values()) if isinstance(ent, dict) else ent
                else:
                    data = list(data.values())

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
        tensor = data.get("tensor_field", {})
        if not tensor:
            log.warning("[RMC] No tensor data found to ingest.")
            return
        timestamp = time.time()
        for wid, t in tensor.items():
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
        self.save()
        if not QUIET:
            log.info(f"[RMC] Ingested {len(tensor)} tensor entries into cache.")

    def stabilize(self, decay_rate: float = 0.001):
        """Apply slow decay to simulate semantic drift stabilization."""
        if not self.cache:
            log.warning("[RMC] No memory to stabilize.")
            return
        for wid, m in self.cache.items():
            if isinstance(m, dict) and "stability" in m:
                m["stability"] = round(m["stability"] * (1 - decay_rate), 6)
        self.save()
        if not QUIET:
            log.info(f"[RMC] Applied stability decay: rate={decay_rate}")

    def recall(self, wid: str):
        """Retrieve stabilized tensor or photon entry for given id."""
        return self.cache.get(wid.lower())

    def set(self, key: str, value: Any):
        """Store a value in the in-memory cache and persist to disk."""
        self.cache[key] = value
        try:
            self.save()  # if your class already has save()
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
                "desc": "Unified photon + semantic Φ–ψ–η–Λ resonance cache",
            },
        }
        lock = FileLock(str(LOCK_PATH))
        try:
            with lock.acquire(timeout=30):
                atomic_write_json(CACHE_PATH, data)
                if not QUIET:
                    log.info(f"[RMC] ✅ Exported unified cache → {CACHE_PATH}")
        except Timeout:
            if not QUIET:
                log.warning(f"[RMC] ⚠ Cache locked — export skipped.")

    # ------------------------------------------------------------
    # 🌀 Phase 53 — Harmonic Resonance Tracking
    # ------------------------------------------------------------
    def push_sample(self, rho: float, entropy: float, sqi: float, delta: float, source: str = "unknown"):
        """
        Append a resonance feedback sample (ρ, Ī, SQI, ΔΦ) into cache history.
        Each source (reflection/personality/awareness) maintains its own rolling list.
        Auto-saves every 5 seconds (rate-limited) to prevent excessive writes.
        """
        try:
            # Initialize throttle timer if missing
            if not hasattr(self, "_last_save"):
                self._last_save = 0.0

            src = f"harmonics::{source}"
            entry = self.cache.get(src, {"samples": [], "avg": {}})

            # Append bounded sample
            entry["samples"].append({
                "timestamp": time.time(),
                "ρ": round(rho, 3),
                "Ī": round(entropy, 3),
                "SQI": round(sqi, 3),
                "ΔΦ": round(delta, 3)
            })
            if len(entry["samples"]) > 200:
                entry["samples"] = entry["samples"][-200:]

            # Recalculate averages
            sqis = [s["SQI"] for s in entry["samples"]]
            deltas = [s["ΔΦ"] for s in entry["samples"]]
            entry["avg"] = {
                "ρ": round(sum(s["ρ"] for s in entry["samples"]) / len(entry["samples"]), 3),
                "Ī": round(sum(s["Ī"] for s in entry["samples"]) / len(entry["samples"]), 3),
                "SQI": round(sum(sqis) / len(sqis), 3),
                "ΔΦ": round(sum(deltas) / len(deltas), 3),
                "count": len(entry["samples"])
            }

            self.cache[src] = entry
            self.last_update = time.time()

            # 🔄 Throttled save (only every 5 seconds)
            now = time.time()
            if now - self._last_save > 5:
                self.save()
                self._last_save = now

            if not QUIET:
                log.info(f"[RMC] ↑ Pushed harmonic sample from {source} → SQI={sqi:.3f}, ΔΦ={delta:.3f}")

        except Exception as e:
            log.warning(f"[RMC] push_sample error ({source}): {e}")

    # ------------------------------------------------------------
    def average_sqi(self) -> float:
        """
        Compute the average SQI (Symatic Quality Index) from the cache.
        Returns 0.5 if empty.
        """
        try:
            if not hasattr(self, "cache") or not isinstance(self.cache, dict) or not self.cache:
                return 0.5
            sqis = []
            for k, v in self.cache.items():
                if isinstance(v, dict):
                    val = v.get("sqi") or v.get("stability")
                    if isinstance(val, (int, float)):
                        sqis.append(val)
            return round(sum(sqis) / len(sqis), 3) if sqis else 0.5
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[RMC] average_sqi() failed: {e}")
            return 0.5

    # ------------------------------------------------------------
    def export_harmonic_profile(self) -> dict:
        """
        Compute a summarized harmonic snapshot across all sources.
        Returns { source: {avg_SQI, avg_ΔΦ, count} }
        """
        summary = {}
        try:
            for k, v in self.cache.items():
                if not k.startswith("harmonics::") or not isinstance(v, dict):
                    continue
                avg = v.get("avg", {})
                summary[k.split("::")[-1]] = {
                    "avg_SQI": avg.get("SQI", 0),
                    "avg_ΔΦ": avg.get("ΔΦ", 0),
                    "count": avg.get("count", 0)
                }
        except Exception as e:
            log.warning(f"[RMC] export_harmonic_profile error: {e}")
        return summary

    # ------------------------------------------------------------
    def summarize_latest(self) -> dict:
        """
        Returns a flattened latest resonance view suitable for dashboard updates.
        """
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

    def get_average(self, key: str) -> float:
        """Compute the mean value of a given numeric field across all cache entries."""
        vals = []
        for v in self.cache.values():
            if isinstance(v, dict) and key in v:
                try:
                    vals.append(float(v[key]))
                except (ValueError, TypeError):
                    continue
        return sum(vals) / len(vals) if vals else None

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