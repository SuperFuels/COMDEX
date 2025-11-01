import os
import json
from datetime import datetime

def update_constants_registry(base_path="backend/modules/knowledge"):
    constants_keys = ["ħ", "G", "Λ", "α", "β"]
    merged_constants = {k: None for k in constants_keys}
    summaries = [f for f in os.listdir(base_path) if f.endswith(".json")]
    
    for filename in summaries:
        path = os.path.join(base_path, filename)
        try:
            with open(path, "r") as f:
                data = json.load(f)
                for k in constants_keys:
                    if k in data and data[k] is not None:
                        merged_constants[k] = data[k]
        except Exception:
            continue

    merged_constants = {k: v for k, v in merged_constants.items() if v is not None}
    constants_out = {
        "constants": merged_constants,
        "source_files": summaries,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
        "meta": {
            "description": "Aggregated constants registry across N-series knowledge modules",
            "version": "v1.2"
        }
    }

    out_path = os.path.join(base_path, "constants_v1.2.json")
    with open(out_path, "w") as f:
        json.dump(constants_out, f, indent=2)

    print(f"✅ Aggregated constants written -> {out_path}")
    print(json.dumps(constants_out, indent=2))

if __name__ == "__main__":
    update_constants_registry()