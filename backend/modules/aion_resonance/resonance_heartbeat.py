#!/usr/bin/env python3
"""
⚛ ResonanceHeartbeat - Tessaris Adaptive Core (Phase 57a)
───────────────────────────────────────────────────────────────
Unified Θ-pulse generator driving all resonant subsystems.
Now fully supports AION_SILENT_MODE for background operation.
"""

import os
import time, json, threading, logging
from collections import deque
from pathlib import Path
from statistics import mean, fmean, StatisticsError

# ─────────────────────────────────────────────────────────────
# Global configuration
# ─────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
QUIET = os.getenv("AION_SILENT_MODE", "0") == "1"
if QUIET:
    logging.getLogger().setLevel(logging.WARNING)


class ResonanceHeartbeat:
    def __init__(
        self,
        namespace: str = "core",
        base_interval: float = 1.5,
        window: int = 60,
        auto_tick: bool = True
    ):
        """
        Resonance Heartbeat - passive/active mode.
        Manages rolling Φ metrics (ρ, entropy, SQI, ΔΦ) and emits adaptive
        Θ-frequency pulses for resonance monitoring.
        """
        self.namespace = namespace
        self.interval = max(0.25, float(base_interval))
        self.window = max(10, int(window))
        self.auto_tick = auto_tick

        # Threading + state
        self.listeners = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._drift_thread = None
        self._drift_running = False
        self.active = False

        # Rolling metrics
        self._rho = deque(maxlen=self.window)
        self._entropy = deque(maxlen=self.window)
        self._sqi = deque(maxlen=self.window)
        self._delta = deque(maxlen=self.window)

        # Last pulse snapshot
        self._last_pulse = {
            "namespace": self.namespace,
            "Φ_coherence": 0.5,
            "Φ_entropy": 0.5,
            "Φ_flux": 0.0,
            "sqi": 0.5,
            "resonance_delta": 0.0,
            "Θ_frequency": 1.0,
            "timestamp": time.time(),
        }

        # Persistent heartbeat file
        self.log_path = Path(f"data/aion_field/{self.namespace}_heartbeat_live.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize according to mode
        if self.auto_tick:
            self.start()
            if not QUIET:
                log.info(f"[Θ] Heartbeat initialized in ACTIVE mode -> {namespace}")
        else:
            if not QUIET:
                log.info(f"[Θ] Heartbeat initialized in PASSIVE mode -> {namespace}")

    # ------------------------------------------------------------
    def register_listener(self, callback):
        """Attach a callable listener for each Θ-pulse."""
        with self._lock:
            if callback not in self.listeners:
                self.listeners.append(callback)

    # ------------------------------------------------------------
    def push_sample(self, *, rho=None, entropy=None, sqi=None, delta=None, source="unknown"):
        """Push a new harmonic sample into rolling metrics."""
        with self._lock:
            if rho is not None:
                self._rho.append(max(0.0, min(1.0, float(rho))))
            if entropy is not None:
                self._entropy.append(max(0.0, min(1.0, float(entropy))))
            if sqi is not None:
                self._sqi.append(max(0.0, min(1.0, float(sqi))))
            if delta is not None:
                self._delta.append(float(delta))

        if not self.auto_tick and not QUIET:
            log.debug(f"[Θ] Passive sample ({self.namespace}) -> SQI={sqi}, ΔΦ={delta}")

    # ------------------------------------------------------------
    def tick(self):
        """Emit one Θ-pulse (manual or automatic)."""
        with self._lock:
            phi = mean(self._rho) if self._rho else self._last_pulse["Φ_coherence"]
            ent = mean(self._entropy) if self._entropy else self._last_pulse["Φ_entropy"]
            flux = mean(abs(d) for d in self._delta) if self._delta else self._last_pulse["Φ_flux"]
            sqi = mean(self._sqi) if self._sqi else self._last_pulse["sqi"]
            delta_now = self._delta[-1] if self._delta else 0.0

            freq_mod = 1.0 + ((phi - ent) * 0.75)
            freq_mod = max(0.5, min(2.0, freq_mod))

            pulse = {
                "namespace": self.namespace,
                "Φ_coherence": round(phi, 3),
                "Φ_entropy": round(ent, 3),
                "Φ_flux": round(flux, 3),
                "sqi": round(sqi, 3),
                "resonance_delta": round(delta_now, 3),
                "Θ_frequency": round(freq_mod, 3),
                "timestamp": time.time(),
            }
            self._last_pulse = pulse

        # Notify listeners
        for cb in list(self.listeners):
            try:
                cb(pulse)
            except Exception as e:
                if not QUIET:
                    log.warning(f"[{self.namespace}::Heartbeat] listener error: {e}")

        # Persist live state
        try:
            self.log_path.write_text(json.dumps(pulse, indent=2))
        except Exception as e:
            if not QUIET:
                log.debug(f"[Θ] write_text failed -> {e}")

        if self.auto_tick and not QUIET:
            log.debug(f"[Θ] Auto-tick -> {self.namespace}")
        return pulse

    emit = tick

    # ------------------------------------------------------------
    # ------------------------------------------------------------
    def start(self):
        """Begin adaptive Θ-pulse loop (respects silent mode)."""
        if QUIET:
            return
        if self._running:
            return

        self._running = True

        def _loop():
            while self._running:
                start_t = time.time()
                pulse = self.tick()
                next_interval = self.interval / pulse["Θ_frequency"]
                time.sleep(max(0.1, next_interval - (time.time() - start_t)))

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

        if not QUIET:
            print(f"[Heartbeat] ⚛ Started adaptive Θ-pulse @ base={self.interval:.2f}s ({self.namespace})")

    # ------------------------------------------------------------
    def stop(self):
        """Stop adaptive Θ-pulse loop."""
        self._running = False
        self._drift_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._drift_thread:
            self._drift_thread.join(timeout=1.0)
        self.active = False
        if not QUIET:
            log.info(f"[Heartbeat] ⏹ Stopped Θ-pulse ({self.namespace})")

    # ------------------------------------------------------------
    def event(self, name: str, **kwargs):
        """Emit and log a semantic event (for dashboard)."""
        payload = {
            "namespace": self.namespace,
            "event": name,
            "timestamp": time.time(),
            **kwargs,
        }
        log_path = Path("data/analysis/aion_live_dashboard.jsonl")
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            if not QUIET:
                log.debug(f"[Θ] Event {name} -> {payload}")
        except Exception as e:
            if not QUIET:
                log.warning(f"[Θ] event() error: {e}")

    # ------------------------------------------------------------
    def get_last_pulse(self):
        """Return last recorded pulse snapshot."""
        return self._last_pulse

    def is_active(self) -> bool:
        """Return True if background loop is running."""
        return self.active

    # ------------------------------------------------------------
    def sync_all(self, emit_pulse: bool = True):
        """Synchronize all active Θ heartbeats and compute harmony."""
        hb_dir = Path("data/aion_field")
        hb_files = list(hb_dir.glob("*heartbeat_live.json"))
        if not hb_files:
            if not QUIET:
                print("[Θ] sync_all -> no heartbeat files found.")
            return None

        phases = []
        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                phases.append(float(js.get("Θ_frequency", 1.0)))
            except Exception:
                continue

        if not phases:
            return None

        master = fmean(phases)
        harmony = 1 - (sum(abs(p - master) for p in phases) / len(phases))
        harmony = round(max(0.0, min(1.0, harmony)), 3)

        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                js["Θ_frequency"] = round(master, 3)
                f.write_text(json.dumps(js, indent=2))
            except Exception:
                pass

        if emit_pulse:
            self.tick()
        self.event("sync_all", harmony_score=harmony, master_frequency=round(master, 3))

        if not QUIET:
            print(f"[Θ] sync_all -> Harmony={harmony:.3f}, Θ_master={master:.3f}")
        return harmony

    # ------------------------------------------------------------
    def monitor_drift(self, interval: float = 5.0, threshold: float = 0.05, correction_rate: float = 0.2):
        """
        Continuously monitor ΔΦ drift among all engines and apply corrections.
        """
        if self._drift_running:
            return
        self._drift_running = True

        drift_log = Path("data/aion_field/resonant_drift_log.jsonl")
        drift_log.parent.mkdir(parents=True, exist_ok=True)

        def _drift_loop():
            while self._drift_running:
                try:
                    hb_dir = Path("data/aion_field")
                    files = list(hb_dir.glob("*heartbeat_live.json"))
                    phases = []
                    for f in files:
                        try:
                            js = json.loads(f.read_text())
                            phases.append((f, float(js.get("Θ_frequency", 1.0))))
                        except Exception:
                            continue

                    if not phases:
                        time.sleep(interval)
                        continue

                    master = fmean(p[1] for p in phases)
                    for f, theta in phases:
                        drift = theta - master
                        if abs(drift) > threshold:
                            corrected = theta - (correction_rate * drift)
                            js = json.loads(f.read_text())
                            js["Θ_frequency"] = round(corrected, 3)
                            f.write_text(json.dumps(js, indent=2))
                            payload = {
                                "namespace": f.stem,
                                "event": "drift_corrected",
                                "ΔΦ": round(drift, 4),
                                "corrected_to": round(corrected, 3),
                                "timestamp": time.time(),
                            }
                            with open(drift_log, "a", encoding="utf-8") as df:
                                df.write(json.dumps(payload) + "\n")
                            self.event("drift_corrected", **payload)
                    time.sleep(interval)
                except Exception as e:
                    if not QUIET:
                        print(f"[Θ] drift monitor error: {e}")
                    time.sleep(interval)

        self._drift_thread = threading.Thread(target=_drift_loop, daemon=True)
        self._drift_thread.start()

        if not QUIET:
            print(f"[Θ] Drift monitor started (interval={interval}s, threshold={threshold})")

    # ------------------------------------------------------------
    def feedback(self, *args, **kwargs):
        """Accepts feedback payloads from other subsystems."""
        try:
            payload = {"namespace": self.namespace, "event": "feedback", **kwargs}
            self.event("feedback", **payload)
        except Exception as e:
            if not QUIET:
                print(f"[Θ] feedback() error: {e}")

    # ------------------------------------------------------------
    def snapshot(self):
        """Return a thread-safe copy of the last pulse."""
        with self._lock:
            return dict(self._last_pulse)


# ------------------------------------------------------------
if __name__ == "__main__":
    hb = ResonanceHeartbeat(namespace="demo", base_interval=1.0)
    hb.register_listener(lambda p: print(f"Θ {p['Θ_frequency']:.2f} | SQI={p['sqi']:.3f}") if not QUIET else None)
    hb.start()
    hb.monitor_drift(interval=3.0)
    try:
        time.sleep(15)
        hb.sync_all()
    finally:
        hb.stop()