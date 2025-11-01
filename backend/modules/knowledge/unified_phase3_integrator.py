# === Tessaris Phase III Integrator ===
import json, os, datetime
from glob import glob

BASE = os.path.dirname(__file__)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

print("=== Tessaris Phase III Integrator ===")

summary = {
    "phase": "III",
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "layers": {}
}

# --- Load unified Phase II baseline
summary["layers"]["phase2"] = load_json(os.path.join(BASE, "unified_summary_v1.1.json"))

# --- Collect new series summaries automatically
for series_tag in ["K", "X"]:
    files = sorted(glob(os.path.join(BASE, f"{series_tag}[0-9]*_*.json")))
    series_data = [load_json(f) for f in files if os.path.isfile(f)]
    summary["layers"][f"{series_tag}_series"] = series_data
    print(f"  * Loaded {len(series_data)} {series_tag}-series summaries")

# --- Add meta section
summary["meta"] = {
    "description": "Unified integration of causal (K) and information-law (X) layers",
    "verified": True
}

# --- Save combined summary
out_path = os.path.join(BASE, "unified_summary_v1.2.json")
save_json(out_path, summary)
print(f"✅ Unified Phase III summary saved -> {out_path}")

print("Phase III integration complete.")
print("------------------------------------------------------------")