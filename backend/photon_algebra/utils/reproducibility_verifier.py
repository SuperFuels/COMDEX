import json, os, hashlib
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

KNOWLEDGE_DIR = "backend/modules/knowledge"
TOLERANCE = 1e-6  # allowable numeric drift

def hash_constants(constants):
    data = json.dumps(constants, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def main():
    print(f"=== Reproducibility Verifier ({datetime.utcnow().strftime('%Y-%m-%d %H:%MZ')}) ===")

    const_path = os.path.join(KNOWLEDGE_DIR, "constants_v1.2.json")
    ref_hash = load_json(os.path.join(KNOWLEDGE_DIR, "constants_hash.json"))["sha256"]
    constants = load_json(const_path)["constants"]

    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".json") and f != "constants_v1.2.json"]
    drift_records = []

    for file in files:
        path = os.path.join(KNOWLEDGE_DIR, file)
        try:
            data = load_json(path)
            local_consts = data.get("constants", constants)
            local_hash = hash_constants(local_consts)
            diff = {k: abs(local_consts[k] - constants[k]) for k in constants if k in local_consts}
            drift = any(v > TOLERANCE for v in diff.values())

            if drift:
                drift_records.append((file, diff))
                print(f"⚠️  Drift detected in {file}: {diff}")
            else:
                print(f"✅  {file} consistent with constants_v1.2")

        except Exception as e:
            print(f"❌  Error in {file}: {e}")

    if drift_records:
        plt.figure()
        drift_vals = [np.mean(list(d[1].values())) for d in drift_records]
        plt.bar(range(len(drift_records)), drift_vals)
        plt.xticks(range(len(drift_records)), [d[0] for d in drift_records], rotation=90)
        plt.ylabel("Mean Constant Drift")
        plt.title("Reproducibility Drift Map")
        plt.tight_layout()
        out_path = os.path.join(KNOWLEDGE_DIR, "ReproducibilityDriftMap.png")
        plt.savefig(out_path)
        print(f"\n📊 Drift map saved -> {out_path}")
    else:
        print("\n✅ All knowledge modules reproducible under constants_v1.2")

    out_summary = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
        "reference_constants": "v1.2",
        "reference_hash": ref_hash,
        "drift_detected": len(drift_records),
        "tolerance": TOLERANCE,
        "summary_file": f"{len(files)} checked, {len(drift_records)} drifted"
    }

    out_path = os.path.join(KNOWLEDGE_DIR, "reproducibility_check_summary.json")
    with open(out_path, "w") as f:
        json.dump(out_summary, f, indent=2)
    print(f"\n📄 Summary saved -> {out_path}")

if __name__ == "__main__":
    main()