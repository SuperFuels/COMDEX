# ==========================================================
# 🔺 Symatic Logger - placeholder until v0.9 integration
# ==========================================================

import datetime

SYMATIC_LOG_PATH = "data/symatic_log.json"

def record_symatic_event(operator, equation):
    """Record a symatic equation event into local JSON log."""
    import json, os
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "operator": operator,
        "equation": equation
    }
    log = []
    if os.path.exists(SYMATIC_LOG_PATH):
        try:
            with open(SYMATIC_LOG_PATH, "r") as f:
                log = json.load(f)
        except Exception:
            log = []
    log.append(event)
    with open(SYMATIC_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
    return event


def load_log():
    """Return all logged symatic events."""
    import json, os
    if not os.path.exists(SYMATIC_LOG_PATH):
        return []
    try:
        with open(SYMATIC_LOG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


# Global interface expected by aion_brain.py
class _SymaticLogger:
    def record(self, operator, equation):
        return record_symatic_event(operator, equation)
    def read(self):
        return load_log()

SYMATIC_LOG = _SymaticLogger()