# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/dc_container_io_module.py

import os, json
from datetime import datetime
from typing import Dict, Any

class DCContainerIO:
    """
    Handles exporting and importing .dc containers for entangled glyph replay or GHX visualization.
    """
    @staticmethod
    def export(dc_data: Dict[str, Any], path: str, stage: str = None, sqi_enabled: bool = False):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if "timestamp" not in dc_data:
            dc_data["timestamp"] = datetime.utcnow().isoformat()

        dc_data["metadata"] = {
            "engine": "QWave",
            "stage": stage or "unknown",
            "sqi_enabled": sqi_enabled,
            "entangled_glyphs": len(dc_data.get("glyphs", [])),
            "timestamp": dc_data["timestamp"]
        }

        with open(path, "w") as f:
            json.dump(dc_data, f, indent=2)
        print(f"📦 Exported .dc container → {path} | Stage={stage or 'N/A'} | SQI={sqi_enabled}")

    @staticmethod
    def import_dc(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ DC file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)

        data.setdefault("glyphs", [])
        data.setdefault("metadata", {
            "engine": "QWave",
            "stage": "unknown",
            "sqi_enabled": False,
            "entangled_glyphs": len(data.get("glyphs", [])),
            "timestamp": datetime.utcnow().isoformat()
        })

        print(f"📥 Imported .dc container from {path} | Stage={data['metadata'].get('stage')} | SQI={data['metadata'].get('sqi_enabled')}")
        return data