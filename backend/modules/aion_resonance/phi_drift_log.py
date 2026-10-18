from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

DRIFT_PATH = Path("data/phi_drift_log.json")
MAX_ENTRIES = 5000
DRIFT_VAULT = AionLearningVaultStore()


def _load_legacy(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def record_phi_drift(keyword: str, phi_vector: dict, *, vault_store=None, drift_path=None):
    """Append business-derived resonance drift as immutable evidence."""
    entry = {
        "timestamp": time.time(),
        "timestamp_readable": datetime.now(timezone.utc).isoformat(),
        "keyword": keyword,
        "Φ_load": phi_vector.get("Φ_load"),
        "Φ_flux": phi_vector.get("Φ_flux"),
        "Φ_entropy": phi_vector.get("Φ_entropy"),
        "Φ_coherence": phi_vector.get("Φ_coherence"),
    }
    store = vault_store or DRIFT_VAULT
    if drift_path is None and store.enabled:
        event_id = f"phi-drift-{time.time_ns()}"
        store.append_event(event_id, {
            **entry, "event_id": event_id, "event_type": "phi_drift",
            "ts_utc": entry["timestamp_readable"],
        })
        return entry
    path = Path(drift_path or DRIFT_PATH)
    rows = _load_legacy(path)
    rows.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows[-MAX_ENTRIES:], indent=2), encoding="utf-8")
    return entry


def get_drift_history(keyword=None, limit=100, *, vault_store=None, drift_path=None):
    store = vault_store or DRIFT_VAULT
    data = (
        store.list_events(kind="phi_drift")
        if drift_path is None and store.enabled
        else _load_legacy(Path(drift_path or DRIFT_PATH))
    )
    if keyword:
        data = [row for row in data if row.get("keyword") == keyword]
    return data[-max(0, int(limit)):]
