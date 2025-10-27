#!/usr/bin/env python3
"""
🎵 Harmonic Memory Profile — Phase 47B (Unified)
────────────────────────────────────────────────
Tracks harmonic stabilization, resonance drift,
and adaptive gain tuning for all reinforcement events.

Combines:
    • Phase 40B persistence & memory logging
    • Phase 47 statistical summarization & pruning

Functions:
    • log_event() — record resonance/gain events
    • log_entry() — append reinforcement/learning entry
    • summarize() — compute avg gain/drift/stability
    • prune_old() — trim stale harmonic data
"""

import json, time, logging
from pathlib import Path
from statistics import mean

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

HMP_PATH = Path("data/training/harmonic_memory_profile.json")
HMP_PATH.parent.mkdir(parents=True, exist_ok=True)


class HarmonicMemoryProfile:
    def __init__(self, path: Path = HMP_PATH):
        self.path = path
        self.events = []
        self.memory_log = []
        self._load()
        log.info(f"[HMP] Loaded {len(self.events)} harmonic events from {self.path}")

    # ─────────────────────────────────────────────
    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.events = data.get("events", [])
            self.memory_log = data.get("memory_log", [])
        except Exception as e:
            log.warning(f"[HMP] ⚠ Failed to load harmonic profile: {e}")
            self.events = []
            self.memory_log = []

    # ─────────────────────────────────────────────
    def _save(self):
        try:
            self.path.write_text(
                json.dumps(
                    {
                        "timestamp": time.time(),
                        "events": self.events[-500:],
                        "memory_log": self.memory_log[-500:],
                    },
                    indent=2,
                )
            )
        except Exception as e:
            log.warning(f"[HMP] ⚠ Failed to save profile: {e}")

    # ─────────────────────────────────────────────
    def log_event(self, record: dict):
        """Record a harmonic stabilization or drift event."""
        if not isinstance(record, dict) or "target" not in record:
            return
        record["timestamp"] = record.get("time", time.time())
        self.events.append(record)
        if len(self.events) % 100 == 0:
            self._save()
        log.info(
            f"[HMP] 🎶 Logged {record['target']} gain={record.get('gain',0):.3f} drift={record.get('drift_mag',0):.3f}"
        )

    def log_entry(self, entry: dict):
        """Append a reinforcement or learning entry into harmonic memory."""
        if not isinstance(entry, dict):
            return
        entry["timestamp"] = entry.get("timestamp", time.time())
        self.memory_log.append(entry)
        if len(self.memory_log) % 100 == 0:
            self._save()
        log.info(f"[HMP] 🧩 Logged memory entry for {entry.get('goal', 'unknown')} ({entry.get('status')})")

    # ─────────────────────────────────────────────
    def summarize(self) -> dict:
        """Compute current harmonic statistics."""
        if not self.events:
            return {"count": 0, "avg_gain": 0, "avg_drift": 0, "stability": 0}
        gains = [e.get("gain", 0) for e in self.events]
        drifts = [e.get("drift_mag", 0) for e in self.events]
        stability = round(1.0 - min(mean(drifts), 1.0), 3)
        summary = {
            "count": len(self.events),
            "avg_gain": round(mean(gains), 3),
            "avg_drift": round(mean(drifts), 3),
            "stability": stability,
        }
        log.info(f"[HMP] 📊 Summary: {summary}")
        return summary

    # ─────────────────────────────────────────────
    def prune_old(self, max_age_hours: float = 24.0):
        """Remove stale events older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        before = len(self.events)
        self.events = [e for e in self.events if e.get("timestamp", 0) >= cutoff]
        after = len(self.events)
        if before != after:
            log.info(f"[HMP] 🧹 Pruned {before - after} old entries.")
            self._save()

    # ─────────────────────────────────────────────
    def get_recent_events(self, n: int = 20):
        """Return last n harmonic correction events."""
        return self.events[-n:]


# ─────────────────────────────────────────────
try:
    HMP
except NameError:
    try:
        HMP = HarmonicMemoryProfile()
        print("🧠 HarmonicMemoryProfile global instance initialized as HMP")
    except Exception as e:
        print(f"⚠️ Could not initialize HMP: {e}")
        HMP = None


if __name__ == "__main__":
    hmp = HarmonicMemoryProfile()
    hmp.log_event({"target": "photon", "gain": 0.8, "drift_mag": 0.12, "time": time.time()})
    print(hmp.summarize())