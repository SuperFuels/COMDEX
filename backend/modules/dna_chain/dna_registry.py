import os
import json
from datetime import datetime
from backend.modules.dna_chain.ethics_sim import simulate_ethics_review

REGISTRY_PATH = "backend/modules/dna_chain/dna_registry.json"

def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return []
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)

def save_registry(registry):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

def add_proposal(entry):
    registry = load_registry()
    entry["timestamp"] = datetime.utcnow().isoformat()
    entry["approved"] = False
    registry.append(entry)
    save_registry(registry)
    return entry

def list_proposals():
    return load_registry()

def approve_proposal(proposal_id, override=False):
    registry = load_registry()
    for proposal in registry:
        if proposal["proposal_id"] == proposal_id:

            # 🧠 Ethics check first
            ethics = proposal.get("ethics_review") or simulate_ethics_review(proposal_id)
            if ethics.get("severity") == "block" and not override:
                print(f"[🛑] Blocked by Soul Laws. Severity: block. Use override=True to bypass.")
                return None

            proposal["approved"] = True
            save_registry(registry)
            print(f"[✅] Proposal approved: {proposal_id}")
            return proposal
    return None

def clear_registry():
    save_registry([])
