"""
Harmonic Memory Profile — Phase 40B
-----------------------------------
Persistent memory of all harmonic stabilization events.
Supports statistical recall for adaptive gain tuning and drift prediction.
"""

import json, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)
HMP_PATH = Path("data/analysis/harmonic_memory.json")

class HarmonicMemoryProfile:
    def __init__(self):
        self.events = []
        self.memory_log = []
        self.load()

    # ─────────────────────────────────────────────
    def log_event(self, record: dict):
        """Record a harmonic stabilization episode."""
        record["timestamp"] = record.get("time", time.time())
        self.events.append(record)
        logger.info(f"[HMP] Logged harmonic event for {record.get('target')}")
        self.save()

    def log_entry(self, entry: dict):
        """Append a reinforcement or learning event into harmonic memory."""
        if not isinstance(entry, dict):
            return
        entry["timestamp"] = entry.get("timestamp", time.time())
        self.memory_log.append(entry)
        self._save()
        print(f"[HMP] 🧩 Logged memory entry for {entry.get('goal', 'unknown')} ({entry.get('status')})")

    # ─────────────────────────────────────────────
    def average_gain(self):
        """Compute rolling average gain coefficient."""
        if not self.events:
            return 0.3
        return sum(e.get("gain", 0.3) for e in self.events[-50:]) / min(len(self.events), 50)

    # ─────────────────────────────────────────────
    def recent_stability(self):
        """Return average drift magnitude over recent corrections."""
        if not self.events:
            return 0.0
        return sum(e.get("drift_mag", 0.0) for e in self.events[-20:]) / min(len(self.events), 20)

    # ─────────────────────────────────────────────
    def _save(self):
        """Persist harmonic memory (events + reinforcement entries)."""
        HMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HMP_PATH, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "events": self.events[-200:],
                },
                f,
                indent=2,
            )
    # ─────────────────────────────────────────────
    def load(self):
        if HMP_PATH.exists():
            with open(HMP_PATH) as f:
                data = json.load(f)
                self.events = data.get("events", [])
            logger.info(f"[HMP] Loaded {len(self.events)} previous harmonic events.")

    # ─────────────────────────────────────────────
    # Phase 40D Support — Return Recent Events
    # ─────────────────────────────────────────────
    def get_recent_events(self, n=20):
        """Return up to n most recent harmonic correction events."""
        return self.memory_log[-n:] if hasattr(self, "memory_log") else []


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