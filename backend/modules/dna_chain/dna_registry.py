import json
import os
from datetime import datetime

DNA_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__),
    "dna_registry.json"
)


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


def load_registry():
    if not os.path.exists(DNA_REGISTRY_PATH):
        return []
    with open(DNA_REGISTRY_PATH, "r") as f:
        return json.load(f)