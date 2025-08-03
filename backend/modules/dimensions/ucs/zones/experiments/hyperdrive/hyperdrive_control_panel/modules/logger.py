# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/logger.py

import os, gzip, json
from datetime import datetime

class TelemetryLogger:
    def __init__(self, log_dir="data/qwave_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ECU runtime logs
        self.main_log = os.path.join(log_dir, f"ecu_runtime_log_{self.timestamp}.jsonl.gz")
        self.latest_log = os.path.join(log_dir, "ecu_runtime_latest.jsonl")
        self.segment_size = 2000
        self.tick_counter = 0
        self.log_file = gzip.open(self.main_log, "wt", encoding="utf-8")
        self.latest_file = open(self.latest_log, "w")

        # Ignition trace logs
        self.ignition_traces = {}
        self.resonance_traces = {}

    # =======================
    # ECU RUNTIME LOGGING
    # =======================
    def log(self, data: dict):
        """High-frequency ECU runtime telemetry logging."""
        json.dump(data, self.log_file); self.log_file.write("\n"); self.log_file.flush()
        self.latest_file.seek(0); self.latest_file.truncate()
        json.dump(data, self.latest_file); self.latest_file.write("\n"); self.latest_file.flush()
        self.tick_counter += 1
        if self.tick_counter % self.segment_size == 0:
            self._rotate_segment()

    def _rotate_segment(self):
        self.log_file.close()
        seg_file = os.path.join(self.log_dir, f"ecu_runtime_log_{self.timestamp}_seg{self.tick_counter//self.segment_size}.jsonl.gz")
        self.log_file = gzip.open(seg_file, "wt", encoding="utf-8")

    # =======================
    # IGNITION TRACE LOGGING
    # =======================
    def log_ignition_trace(self, engine_name: str, tick: int, resonance: float, drift: float, pulse: bool, fields: dict, particles: int, avg_density: float):
        """Structured ignition trace logging (one array per engine)."""
        if engine_name not in self.ignition_traces:
            self.ignition_traces[engine_name] = []
        self.ignition_traces[engine_name].append({
            "tick": tick,
            "resonance": resonance,
            "drift": drift,
            "pulse": pulse,
            "fields": fields,
            "particle_count": particles,
            "avg_density": round(avg_density, 4)
        })

    def log_resonance_trace(self, engine_name: str, resonance_value: float):
        """Structured resonance trace logging (flat array per engine)."""
        if engine_name not in self.resonance_traces:
            self.resonance_traces[engine_name] = []
        self.resonance_traces[engine_name].append(resonance_value)

    def export_ignition_traces(self):
        """Write ignition & resonance traces to JSON files per engine."""
        for engine_name, trace in self.ignition_traces.items():
            path = os.path.join(self.log_dir, f"ignition_trace_{engine_name}.json")
            with open(path, "w") as f: json.dump(trace, f, indent=2)
            print(f"💾 Ignition trace saved: {path}")

        for engine_name, trace in self.resonance_traces.items():
            path = os.path.join(self.log_dir, f"resonance_trace_{engine_name}.json")
            with open(path, "w") as f: json.dump(trace, f, indent=2)
            print(f"💾 Resonance trace saved: {path}")

    def close(self):
        self.log_file.close()
        self.latest_file.close()