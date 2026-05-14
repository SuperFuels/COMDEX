# backend/photon_algebra/utils/build_registry_index.py
import os, json
from datetime import datetime

knowledge_dir = "backend/modules/knowledge"
index_path = os.path.join(knowledge_dir, "registry_index.json")
hash_file = os.path.join(knowledge_dir, "constants_hash.json")

with open(hash_file) as f:
    hash_data = json.load(f)

entries = []
for file in sorted(os.listdir(knowledge_dir)):
    if file.endswith(".json") and file not in ["constants_v1.2.json", "constants_hash.json", "registry_index.json"]:
        path = os.path.join(knowledge_dir, file)
        with open(path) as f:
            try:
                data = json.load(f)
                entries.append({
                    "file": file,
                    "timestamp": data.get("timestamp", "unknown"),
                    "constants_version": hash_data["constants_version"],
                    "hash_ref": hash_data["sha256"]
                })
            except Exception:
                entries.append({"file": file, "error": "Unreadable or invalid JSON"})

index = {
    "registry_version": "v1.0",
    "constants_ref": hash_data,
    "entries": entries,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open(index_path, "w") as f:
    json.dump(index, f, indent=2)

print(f"✅ Registry index built -> {index_path}")
print(f"🧩 Indexed {len(entries)} knowledge modules")