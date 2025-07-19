import json
import os
import uuid
from datetime import datetime

DNA_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__),
    "dna_registry.json"
)

# Internal registry cache (optional but useful)
REGISTRY_CACHE = {"proposals": []}


def register_proposal(proposal: dict):
    if not os.path.exists(DNA_REGISTRY_PATH):
        with open(DNA_REGISTRY_PATH, "w") as f:
            json.dump({"proposals": []}, f, indent=2)

    with open(DNA_REGISTRY_PATH, "r") as f:
        data = json.load(f)

    proposal["timestamp"] = datetime.utcnow().isoformat()
    proposal["approved"] = False

    data["proposals"].append(proposal)

    with open(DNA_REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[🧬] Proposal stored in registry: {proposal['proposal_id']}")


def update_dna_proposal(proposal_id: str, updates: dict):
    if not os.path.exists(DNA_REGISTRY_PATH):
        raise FileNotFoundError("DNA registry file not found.")

    with open(DNA_REGISTRY_PATH, "r") as f:
        data = json.load(f)

    updated = False
    for proposal in data.get("proposals", []):
        if proposal.get("proposal_id") == proposal_id:
            proposal.update(updates)
            updated = True
            break

    if updated:
        with open(DNA_REGISTRY_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[✅] Proposal updated: {proposal_id}")
    else:
        raise ValueError(f"Proposal ID not found: {proposal_id}")


def load_registry():
    if not os.path.exists(DNA_REGISTRY_PATH):
        return {"proposals": []}
    with open(DNA_REGISTRY_PATH, "r") as f:
        return json.load(f)


def save_registry():
    with open(DNA_REGISTRY_PATH, "w") as f:
        json.dump(REGISTRY_CACHE, f, indent=2)
    print("[💾] DNA registry saved.")


# ✅ Unified proposal submission helper
def submit_dna_proposal(file, reason, replaced_code, new_code, diff):
    proposal = {
        "proposal_id": str(uuid.uuid4()),
        "file": file,
        "reason": reason,
        "replaced_code": replaced_code,
        "new_code": new_code,
        "diff": diff
    }
    register_proposal(proposal)
    return proposal


# ✅ Alias for backward compatibility
register_mutation_proposal = register_proposal

# ✅ Alias for crispr_ai.py compatibility
def store_proposal(proposal: dict):
    register_proposal(proposal)