import os
import shutil
import argparse
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.writable_guard import is_safe_path
from backend.modules.dna_chain.dna_switch import DNA_SWITCH

# ✅ Register with DNA Switch
DNA_SWITCH.register(__file__)

# 🔐 Load master key from environment
MASTER_KEY = os.getenv("AION_MASTER_KEY")

def approve_proposal(proposal_id, provided_key):
    if provided_key != MASTER_KEY:
        raise PermissionError("❌ Invalid master key.")

    proposals = load_proposals()
    matched = next((p for p in proposals if p["proposal_id"] == proposal_id), None)

    if not matched:
        raise ValueError("❌ Proposal not found.")

    file_path = get_module_path(matched["file"])

    # 🔒 Safety check
    if not is_safe_path(matched["file"]):
        raise PermissionError(f"❌ Writing to '{matched['file']}' is not permitted.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Target file not found: {file_path}")

    _, ext = os.path.splitext(file_path)
    if ext not in [".py", ".tsx"]:
        raise ValueError("❌ Only .py and .tsx files are supported.")

    # 📦 Backup original file
    backup_path = file_path.replace(ext, f"_OLD{ext}")
    shutil.copyfile(file_path, backup_path)

    with open(file_path, "r", encoding="utf-8") as f:
        contents = f.read()

    if matched["replaced_code"] not in contents:
        raise ValueError("❌ Original code block not found in file.")

    # ✅ Apply mutation
    updated = contents.replace(matched["replaced_code"], matched["new_code"])
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)

    # ✅ Mark proposal as approved
    matched["approved"] = True
    save_proposals(proposals)

    print(f"✅ Proposal '{proposal_id}' has been approved and applied.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Approve a DNA mutation proposal")
    parser.add_argument("--id", required=True, help="Proposal ID to approve and apply")
    parser.add_argument("--key", required=False, help="Master key (or use env var AION_MASTER_KEY)")
    args = parser.parse_args()

    approve_proposal(args.id, args.key or MASTER_KEY)