import os
import json
import argparse
from datetime import datetime
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.dna_chain.writable_guard import is_write_allowed


# ✅ Register with DNA Switch
DNA_SWITCH.register(__file__)

def create_proposal(file, replaced_code, new_code, reason):
    # 🔄 Normalize file path to use forward slashes and remove leading './'
    normalized_file = file.replace("\\", "/").lstrip("./")

    # 🔐 Restriction check
    if not is_write_allowed(normalized_file):
        raise PermissionError(f"❌ AION is not permitted to modify or create: {file}")

    abs_path = get_module_path(normalized_file)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    _, ext = os.path.splitext(normalized_file)
    if ext not in [".py", ".tsx"]:
        raise ValueError("Only .py and .tsx files are supported.")

    # Load original file contents
    with open(abs_path, "r", encoding="utf-8") as f:
        contents = f.read()

    if replaced_code not in contents:
        raise ValueError("Replaced code block not found in target file.")

    # Create proposal object
    proposals = load_proposals()
    next_id = len(proposals) + 1

    proposal_id = f"{ext.strip('.')}-{normalized_file.replace('/', '_').replace('.', '_')}-{next_id}"

    proposal = {
        "proposal_id": proposal_id,
        "file": normalized_file,
        "replaced_code": replaced_code,
        "new_code": new_code,
        "reason": reason,
        "approved": False,
        "timestamp": datetime.utcnow().isoformat()
    }

    proposals.append(proposal)
    save_proposals(proposals)

    print(f"✅ Proposal created: {proposal_id}")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a DNA mutation proposal")
    parser.add_argument("--file", required=True, help="Relative path to target file")
    parser.add_argument("--replaced", required=True, help="Original code block")
    parser.add_argument("--new", required=True, help="New code block to replace with")
    parser.add_argument("--reason", required=True, help="Reason for the change")

    args = parser.parse_args()

    create_proposal(
        file=args.file,
        replaced_code=args.replaced,
        new_code=args.new,
        reason=args.reason
    )