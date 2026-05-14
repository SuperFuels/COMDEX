import pytest
import uuid
from backend.modules.dna_chain import dna_registry

def test_add_and_list_proposal():
    dna_registry.clear_registry()
    pid = str(uuid.uuid4())
    entry = {
        "proposal_id": pid,
        "file": "sample.py",
        "reason": "Fix bug in loop",
        "replaced_code": "for i in range(10): pass",
        "new_code": "for i in range(20): print(i)",
        "diff": "---\n+++"
    }
    added = dna_registry.add_proposal(entry)
    assert added["proposal_id"] == pid
    assert added["approved"] is False

    all_proposals = dna_registry.list_proposals()
    assert any(p["proposal_id"] == pid for p in all_proposals)

def test_approve_proposal():
    proposals = dna_registry.list_proposals()
    if not proposals:
        pytest.skip("No proposals to approve")
    pid = proposals[0]["proposal_id"]
    approved = dna_registry.approve_proposal(pid)
    assert approved["approved"] is True
