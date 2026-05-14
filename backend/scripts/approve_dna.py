import sys
from backend.modules.dna_chain.dna_registry import approve_proposal

if len(sys.argv) < 2:
    print("Usage: python approve_dna.py <proposal_id> [--override]")
    sys.exit(1)

proposal_id = sys.argv[1]
override = "--override" in sys.argv

result = approve_proposal(proposal_id, override=override)
if result:
    print("[✅] Approval complete.")
else:
    print("[❌] Approval failed or blocked.")
