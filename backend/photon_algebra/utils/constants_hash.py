# backend/photon_algebra/utils/check_constants_hash.py
import hashlib, json, os
from datetime import datetime

constants_path = "backend/modules/knowledge/constants_v1.2.json"
hash_path = "backend/modules/knowledge/constants_hash.json"

def compute_hash(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()

if not os.path.exists(constants_path):
    raise FileNotFoundError(f"❌ Missing constants file: {constants_path}")

sha, md5 = compute_hash(constants_path)

hash_info = {
    "constants_version": "v1.2",
    "sha256": sha,
    "md5": md5,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    "source": constants_path,
    "verified": True
}

with open(hash_path, "w") as f:
    json.dump(hash_info, f, indent=2)

print(f"✅ Constants hash recorded → {hash_path}")
print(json.dumps(hash_info, indent=2))