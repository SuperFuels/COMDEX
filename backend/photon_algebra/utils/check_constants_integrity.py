import os
import json
from datetime import datetime

def check_constants_integrity(base_path="backend/modules/knowledge"):
    required_fields = ["ħ", "G", "Λ", "α", "β"]
    summary_files = [f for f in os.listdir(base_path) if f.endswith(".json")]
    
    print(f"=== Constants Integrity Check ({datetime.utcnow().strftime('%Y-%m-%d %H:%MZ')}) ===")
    print(f"Scanning directory: {base_path}")
    print(f"Found {len(summary_files)} JSON files\n")

    valid_files = 0
    missing_fields = {}
    errors = []

    for filename in summary_files:
        file_path = os.path.join(base_path, filename)
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        # Look for constants
        found_fields = [k for k in data.keys() if k in required_fields]
        missing = [k for k in required_fields if k not in data.keys()]
        if missing:
            missing_fields[filename] = missing
        else:
            valid_files += 1

    print("=== Summary ===")
    print(f"✅ Valid constant sets: {valid_files}/{len(summary_files)}")
    if missing_fields:
        print(f"⚠️ Missing fields in {len(missing_fields)} files:")
        for f, m in missing_fields.items():
            print(f"   - {f}: missing {', '.join(m)}")

    if errors:
        print(f"\n❌ Errors reading {len(errors)} files:")
        for f, e in errors:
            print(f"   - {f}: {e}")

    if not missing_fields and not errors:
        print("\n🎯 All knowledge modules are consistent and complete!")

    print("\nDone.")

if __name__ == "__main__":
    check_constants_integrity()