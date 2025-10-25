from datetime import datetime
from pathlib import Path

AUDIT_LOG = Path("/tmp/tessaris_audit.log")

def log_audit_event(event_type: str, capsule_path: Path, context: dict = None):
    """Record SQI changes, KG mutations, and safety events."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "capsule": str(capsule_path),
        "context": context or {},
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{entry}\n")