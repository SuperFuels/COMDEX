import json
import os
import time

class QWaveWriter:
    """
    Runtime QWave snapshot writer (SRK-16).
    Persists beam telemetry to .qwv JSON logs.
    """

    def __init__(self, out_dir="runtime/qwave_logs"):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def write_snapshot(self, wave_id: str, snapshot: dict) -> str:
        """
        Writes a timestamped beam snapshot file.
        """
        filename = f"{wave_id}_{int(time.time() * 1000)}.qwv"
        path = os.path.join(self.out_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            return path
        except Exception as e:
            print(f"[QWaveWriter] Failed to write snapshot: {e}")
            return None

    def list_logs(self):
        """Return all QWave log files."""
        return [f for f in os.listdir(self.out_dir) if f.endswith(".qwv")]