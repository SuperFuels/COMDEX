# ==========================================================
# 🔺 Symatic Logger - placeholder until v0.9 integration
# ==========================================================

from backend.modules.aion_resonance.symatic_event_store import SYMATIC_EVENTS

def record_symatic_event(operator, equation):
    """Record a Symatic equation in the configured customer authority."""
    return SYMATIC_EVENTS.record(operator, equation)


def load_log():
    """Return all logged symatic events."""
    return SYMATIC_EVENTS.list()


# Global interface expected by aion_brain.py
class _SymaticLogger:
    def record(self, operator, equation):
        return record_symatic_event(operator, equation)
    def read(self):
        return load_log()

SYMATIC_LOG = _SymaticLogger()
