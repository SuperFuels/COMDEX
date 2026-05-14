import json
import os
import uuid
from datetime import datetime

PROPOSAL_STORE = os.path.join(os.path.dirname(__file__), "dna_proposals.json")

def load_proposals():
    if not os.path.exists(PROPOSAL_STORE):
        return []
    with open(PROPOSAL_STORE, "r") as f:
        return json.load(f)

def save_proposals(proposals):
    with open(PROPOSAL_STORE, "w") as f:
        json.dump(proposals, f, indent=2)

def add_proposal(file_key, reason, replaced_code, new_code, diff):
    proposals = load_proposals()
    proposal = {
        "proposal_id": str(uuid.uuid4()),
        "file": file_key,
        "reason": reason,
        "replaced_code": replaced_code,
        "new_code": new_code,
        "diff": diff,
        "approved": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    proposals.append(proposal)
    save_proposals(proposals)
    return proposal