# File: backend/modules/dna_chain/dna_proposer.py

import uuid
from datetime import datetime
from backend.modules.dna_chain.proposal_manager import load_proposals, save_proposals

def propose_dna_mutation(reason: str = "No reason provided", file: str = "unknown", replaced_code: str = "", new_code: str = ""):
    proposal_id = str(uuid.uuid4())

    # Build mutation record
    proposal = {
        "proposal_id": proposal_id,
        "file": file,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason,
        "replaced_code": replaced_code,
        "new_code": new_code,
        "approved": False,
        "applied_successfully": False
    }

    # Load, append, save
    proposals = load_proposals()
    proposals.append(proposal)
    save_proposals(proposals)

    print(f"[🧬] DNA mutation proposed: {proposal_id} — File: {file} — Reason: {reason}")
    return {
        "status": "proposed",
        "proposal_id": proposal_id,
        "file": file,
        "reason": reason,
    }