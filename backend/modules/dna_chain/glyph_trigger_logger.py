from datetime import datetime
from typing import Dict, Any
import json
import os

LOG_DIR = "./logs/trigger_logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_trigger_trace(trigger_data: Dict[str, Any], container_id: str = "default"):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    log_file = os.path.join(LOG_DIR, f"{container_id}_trace_{timestamp}.json")
    
    try:
        with open(log_file, "w") as f:
            json.dump(trigger_data, f, indent=2)
        print(f"[GlyphTriggerLogger] Logged trigger trace to {log_file}")
    except Exception as e:
        print(f"[GlyphTriggerLogger] Failed to log trace: {e}")
