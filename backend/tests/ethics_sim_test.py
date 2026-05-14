import pytest
from backend.modules.dna_chain.ethics_sim import simulate_ethics_review
from backend.modules.dna_chain.dna_registry import list_proposals

def test_ethics_review_basic():
    proposals = list_proposals()
    assert len(proposals) > 0, "No proposals found to test"

    proposal_id = proposals[-1]["proposal_id"]
    review = simulate_ethics_review(proposal_id)

    assert isinstance(review, dict)
    assert "allowed" in review
    assert "severity" in review
    assert "confidence" in review
    assert "rationale" in review
    print(f"[✅] Ethics review passed for {proposal_id}")
