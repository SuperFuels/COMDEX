import os
import json
import argparse
from datetime import datetime
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.writable_guard import is_write_allowed

# ✅ Register with DNA Switch
DNA_SWITCH.register(__file__)

# Directory to save version snapshots
VERSION_DIR = os.path.join(os.path.dirname(__file__), ".dna_versions")
os.makedirs(VERSION_DIR, exist_ok=True)

def _get_version_filename(file: str) -> str:
    """
    Generates a timestamped filename for a version snapshot of the given file.
    """
    base_name = file.replace("/", "_").replace("\\", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    return f"{base_name}_{timestamp}.bak"

def save_version_snapshot(file: str, contents: str) -> str:
    """
    Save a snapshot of the current file contents for version tracking.
    Returns the filename of the saved snapshot.
    """
    version_file = os.path.join(VERSION_DIR, _get_version_filename(file))
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(contents)
    print(f"💾 Saved version snapshot: {version_file}")
    return version_file

def get_versions_for_file(file: str):
    """
    List all saved versions for a given file.
    Returns list of version filenames.
    """
    base_name = file.replace("/", "_").replace("\\", "_")
    files = []
    for f in os.listdir(VERSION_DIR):
        if f.startswith(base_name):
            files.append(f)
    files.sort(reverse=True)  # newest first
    return files

def restore_version(file: str, version_filename: str):
    """
    Restore a given version snapshot into the target file.
    """
    version_path = os.path.join(VERSION_DIR, version_filename)
    if not os.path.exists(version_path):
        raise FileNotFoundError(f"Version file not found: {version_path}")

    abs_path = get_module_path(file)
    with open(version_path, "r", encoding="utf-8") as vf:
        version_contents = vf.read()

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(version_contents)

    print(f"♻️ Restored version {version_filename} into {file}")

def create_proposal(file, replaced_code, new_code, reason):
    # 🔄 Normalize file path
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

    # --- Save version snapshot BEFORE making proposal ---
    save_version_snapshot(normalized_file, contents)

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

def approve_dna_proposal(proposal_id: str) -> bool:
    """
    Marks a DNA proposal as approved by its proposal_id.
    """
    proposals = load_proposals()
    found = False

    for proposal in proposals:
        if proposal["proposal_id"] == proposal_id:
            proposal["approved"] = True
            proposal["approved_at"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        raise ValueError(f"❌ Proposal ID not found: {proposal_id}")

    save_proposals(proposals)
    print(f"✅ Proposal approved: {proposal_id}")
    return True

# ✅ Tessaris-compatible symbolic mutation proposal
def propose_dna_mutation(reason: str, source: str, code_context: str, new_logic: str):
    """
    Lightweight wrapper to auto-generate a DNA mutation proposal from symbolic trigger.
    - reason: human-readable explanation
    - source: origin module (e.g. tessaris_trigger)
    - code_context: placeholder code or symbolic marker to target
    - new_logic: string of replacement logic or symbolic code
    """
    file = "backend/modules/skills/goal_engine.py"  # ⛓️ Default symbolic target
    replaced_code = code_context
    new_code = new_logic

    return create_proposal(
        file=file,
        replaced_code=replaced_code,
        new_code=new_code,
        reason=f"{reason} (triggered by: {source})"
    )

# ✅ NEW: Gradient-based DNA mutation logging (used by SymbolicGradientEngine)
def write_gradient_mutation(container_id: str, glyph_id: str, failure_reason: str):
    """
    Records a DNA mutation suggestion derived from symbolic gradient feedback.
    This enables IGI/AION to evolve logic when encountering failed glyph paths.
    """
    proposal = {
        "proposal_id": f"dna-gradient-{container_id}-{glyph_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "file": f"container::{container_id}",
        "replaced_code": glyph_id,
        "new_code": f"# Suggested fix for glyph {glyph_id} after failure: {failure_reason}",
        "reason": f"Gradient mutation: {failure_reason}",
        "approved": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    proposals = load_proposals()
    proposals.append(proposal)
    save_proposals(proposals)
    print(f"🧬 Gradient DNA mutation logged: {proposal['proposal_id']}")
    return proposal

# 🧪 CLI usage
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