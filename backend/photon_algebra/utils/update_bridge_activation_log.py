# backend/photon_algebra/utils/update_bridge_activation_log.py
import json, os
from datetime import datetime

bridge_log = "backend/modules/knowledge/bridge_activation_log.json"
hash_file = "backend/modules/knowledge/constants_hash.json"

if not os.path.exists(bridge_log):
    raise FileNotFoundError("❌ bridge_activation_log.json not found")
if not os.path.exists(hash_file):
    raise FileNotFoundError("❌ constants_hash.json not found - run check_constants_hash.py first")

with open(hash_file) as f:
    hdata = json.load(f)

with open(bridge_log) as f:
    blog = json.load(f)

blog["constants_version"] = hdata["constants_version"]
blog["constants_hash"] = hdata["sha256"]
blog["updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")

with open(bridge_log, "w") as f:
    json.dump(blog, f, indent=2)

print(f"✅ Bridge activation log linked to constants_v{hdata['constants_version']}")
print(f"   -> SHA256: {hdata['sha256'][:16]}...")