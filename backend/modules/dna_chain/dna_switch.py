# File: backend/modules/dna_chain/dna_switch.py

import os
import json
import shutil
from datetime import datetime
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_address_lookup import register_backend_path, register_frontend_path
from backend.modules.dna_chain.dna_registry import update_dna_proposal

# 🔐 Use environment variable to check for master key
MASTER_KEY = os.getenv("AION_MASTER_KEY")

DNA_SWITCH_LOG = os.path.join(os.path.dirname(__file__), "dna_switch_log.json")


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

            filename = os.path.basename(abs_path)

            if file_type == "backend":
                register_backend_path(name=filename, path=abs_path)
            elif file_type == "frontend":
                register_frontend_path(name=filename, path=abs_path)

    def _utc_now(self):
        return datetime.utcnow().isoformat() + "Z"

    def list(self):
        return self.tracked_files


# ✅ Use proposal manager for secure mutation approval + replacement
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

    # Log and update
    log_dna_switch({
        "proposal_id": proposal_id,
        "file": file_path,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "applied"
    })

    update_dna_proposal(proposal_id, {
        "approved": True,
        "applied_at": datetime.utcnow().isoformat(),
        "applied_successfully": True
    })

    return {"status": "applied", "file": matched["file"], "backup": backup_path}


# ✅ Manual DNA trigger for runtime executors (glyphs, dreams, etc.)
def register_dna_switch(proposal_id: str, new_code: str, file_path: str):
    success = apply_dna_switch(file_path, new_code)
    update_dna_proposal(proposal_id, {
        "approved": True,
        "applied_at": datetime.utcnow().isoformat(),
        "applied_successfully": success
    })


# ✅ Apply code directly and log it
def apply_dna_switch(file_path: str, new_code: str) -> bool:
    try:
        # Optional: backup before applying
        backup_path = file_path.replace(".py", "_OLD.py") if file_path.endswith(".py") else file_path + ".bak"
        shutil.copyfile(file_path, backup_path)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        log_dna_switch({
            "file": file_path,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "applied"
        })
        return True
    except Exception as e:
        print(f"❌ DNA switch failed for {file_path}: {e}")
        return False


# 🧠 Switch log for audit
def log_dna_switch(entry: dict):
    if not os.path.exists(DNA_SWITCH_LOG):
        with open(DNA_SWITCH_LOG, "w") as f:
            json.dump({"log": []}, f, indent=2)

    with open(DNA_SWITCH_LOG, "r") as f:
        data = json.load(f)

    data["log"].append(entry)

    with open(DNA_SWITCH_LOG, "w") as f:
        json.dump(data, f, indent=2)


# 🧠 Track Frontend Files (Optional)
def register_frontend(filepath: str):
    DNA_SWITCH.register(filepath, file_type="frontend")


def get_frontend_status():
    return {
        path: meta
        for path, meta in DNA_SWITCH.tracked_files.items()
        if meta.get("type") == "frontend"
    }


# ✅ DNA Switch Singleton
DNA_SWITCH = DNAModuleSwitch()

# ✅ Re-export symbolic mutation proposal function from dna_writer
from backend.modules.dna_chain.dna_writer import propose_dna_mutation