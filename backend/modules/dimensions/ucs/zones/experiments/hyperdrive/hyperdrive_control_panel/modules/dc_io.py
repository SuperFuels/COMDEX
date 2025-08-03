# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/dc_io.py

import os
import json
from datetime import datetime

class DCContainerIO:
    @staticmethod
    def export(dc_data, path, stage=None, sqi_enabled=False):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if "timestamp" not in dc_data:
            dc_data["timestamp"] = datetime.utcnow().isoformat()

        dc_data["metadata"] = {
            "engine": "Hyperdrive",
            "stage": stage or "unknown",
            "sqi_enabled": sqi_enabled,
            "entangled_glyphs": len(dc_data.get("glyphs", [])),
            "timestamp": dc_data["timestamp"]
        }

        with open(path, "w") as f:
            json.dump(dc_data, f, indent=2)
        print(f"📦 Exported .dc container → {path} | Stage={stage or 'N/A'} | SQI={sqi_enabled}")

    @staticmethod
    def import_dc(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ DC file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        data.setdefault("glyphs", [])
        data.setdefault("metadata", {
            "engine": "Hyperdrive",
            "stage": "unknown",
            "sqi_enabled": False,
            "entangled_glyphs": len(data.get("glyphs", [])),
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"📥 Imported .dc container from {path} | Stage={data['metadata'].get('stage')} | SQI={data['metadata'].get('sqi_enabled')}")
        return data