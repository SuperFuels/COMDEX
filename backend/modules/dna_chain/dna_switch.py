import os
import shutil
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_address_lookup import register_backend_path, register_frontend_path

# 🔐 Use environment variable to check for master key
MASTER_KEY = os.getenv("AION_MASTER_KEY")


class DNAModuleSwitch:
    def __init__(self):
        self.tracked_files = {}

    def register(self, path, file_type="backend"):
        abs_path = os.path.abspath(path)
        if abs_path not in self.tracked_files:
            self.tracked_files[abs_path] = {
                "type": file_type,
                "registered_at": self._utc_now(),
            }
            if file_type == "backend":
                register_backend_path(abs_path)
            elif file_type == "frontend":
                register_frontend_path(abs_path)

    def _utc_now(self):
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    def list(self):
        return self.tracked_files


def approve_proposal(proposal_id, provided_key):
    if provided_key != MASTER_KEY:
        raise PermissionError("Invalid master key.")

    proposals = load_proposals()
    matched = None

    for proposal in proposals:
        if proposal["proposal_id"] == proposal_id:
            matched = proposal
            break

    if not matched:
        raise ValueError("Proposal not found.")

    # Mark as approved
    matched["approved"] = True
    save_proposals(proposals)

    # Apply the change
    file_path = get_module_path(matched["file"])
    backup_path = (
        file_path.replace(".py", "_OLD.py")
        if file_path.endswith(".py")
        else file_path.replace(".tsx", "_OLD.tsx")
    )

    # Backup current version
    shutil.copyfile(file_path, backup_path)

    # Read original
    with open(file_path, "r", encoding="utf-8") as f:
        contents = f.read()

    # Replace code block
    if matched["replaced_code"] not in contents:
        raise ValueError("Original code block not found in file.")

    updated = contents.replace(matched["replaced_code"], matched["new_code"])

    # Write modified version
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)

    return {"status": "applied", "file": matched["file"], "backup": backup_path}


# 🧠 Track Frontend Files (Optional)
def register_frontend(filepath: str):
    DNA_SWITCH.register(filepath, file_type="frontend")


def get_frontend_status():
    return {
        path: meta
        for path, meta in DNA_SWITCH.tracked_files.items()
        if meta.get("type") == "frontend"
    }


# ✅ DNA Switch Instance (exported)
DNA_SWITCH = DNAModuleSwitch()