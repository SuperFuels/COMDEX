from datetime import datetime
import json, os

class BaseQuantModule:
    """Abstract base for all Tessaris Q-Series modules."""

    module_name = "BaseQuant"
    version = "0.1"

    def __init__(self):
        self.created_at = datetime.utcnow().isoformat()
        self.trace = []

    def log(self, event, data=None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "data": data or {}
        }
        self.trace.append(entry)

    def export_schema(self, path):
        data = {
            "module": self.module_name,
            "version": self.version,
            "created_at": self.created_at,
            "trace": self.trace
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def compute_sqi(self, signal):
        """Basic Symbolic Quality Index placeholder."""
        if not signal:
            return 0.0
        return sum(abs(x) for x in signal) / len(signal)

    def attach_pattern_engine(self, engine):
        """Connect the global pattern engine to this module."""
        self.pattern_engine = engine
        self.log("pattern_engine_attached", {"engine": str(engine)})