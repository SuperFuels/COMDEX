import pytest

from backend.modules.aion_inference.candidate_supplier_intent_normalizer import (
    canonicalize_supplier_extraction_request,
)
from backend.modules.aion_inference import extract_verified_supplier_fields


@pytest.mark.parametrize("prompt", [
    "Atlas Components SL sent invoice AC-204 for EUR 910.40 for review.",
    "The GBP 81.22 invoice BN-771 was submitted by Blue North Ltd.",
    "For review: supplier Cobalt Works BV; invoice CW-62; amount USD 440.00.",
    "Could you check invoice DP-515 from Duna Paper SA for EUR 1200.50?",
    "East Field AB has requested SEK 775.10 for invoice EF-92.",
    "Record Forest Line LLC, invoice FL-804, payment USD 304.19 for review.",
    "The invoice awaiting review is GM-77 from Green Mesa PLC for GBP 630.00.",
    "Review Harbor Glass GmbH's EUR 95.75 invoice HG-311.",
])
def test_candidate_normalizes_bounded_paraphrases(prompt):
    canonical = canonicalize_supplier_extraction_request(prompt)
    assert canonical is not None
    assert extract_verified_supplier_fields(canonical) is not None


@pytest.mark.parametrize("prompt", [
    "Supplier Quartz Office SL submitted invoice QO-204 for EUR 910.40. Also draft a reply.",
    "Review USD 304.19 for invoice VL-804 from Valley Line LLC and compare it with invoice VL-803.",
    "Review payment to Yellow Glass GmbH for invoice YG-311, amount EUR 95.75, and email approval.",
    "Supplier Zero Labs BV submitted invoice ZL-44 for EUR 640.25 and USD 700.00.",
])
def test_candidate_rejects_compound_or_ambiguous_requests(prompt):
    assert canonicalize_supplier_extraction_request(prompt) is None
