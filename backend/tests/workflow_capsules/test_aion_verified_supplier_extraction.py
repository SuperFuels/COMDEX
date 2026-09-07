import pytest

from backend.modules.aion_inference import (
    extract_verified_supplier_fields,
    verify_proof_receipt,
)


@pytest.mark.parametrize(("prompt", "expected"), [
    ("Review payment to Acme Components Ltd for invoice INV-2048, amount EUR 1250.00.",
     {"supplier_name":"Acme Components Ltd","invoice_reference":"INV-2048","payment_amount":"EUR 1250.00"}),
    ("Supplier Northstar Office SL submitted invoice NS-771 for GBP 86.40.",
     {"supplier_name":"Northstar Office SL","invoice_reference":"NS-771","payment_amount":"GBP 86.40"}),
    ("Please review invoice BR-0091 from Blue River Tools GmbH for USD 9075.25.",
     {"supplier_name":"Blue River Tools GmbH","invoice_reference":"BR-0091","payment_amount":"USD 9075.25"}),
    ("Payment review: Sol y Mar Servicios, invoice SYM-44, EUR 319.99.",
     {"supplier_name":"Sol y Mar Servicios","invoice_reference":"SYM-44","payment_amount":"EUR 319.99"}),
    ("Check Cedar & Stone Limited invoice CS-8802 before paying GBP 4400.00.",
     {"supplier_name":"Cedar & Stone Limited","invoice_reference":"CS-8802","payment_amount":"GBP 4400.00"}),
    ("Vendor Atlas Packaging BV requests USD 72.18 against invoice AP-117.",
     {"supplier_name":"Atlas Packaging BV","invoice_reference":"AP-117","payment_amount":"USD 72.18"}),
    ("Review EUR 15000.00 for invoice MF-300 from Meridian Fabrication SAS.",
     {"supplier_name":"Meridian Fabrication SAS","invoice_reference":"MF-300","payment_amount":"EUR 15000.00"}),
    ("Invoice OL-62 from Oakline Logistics PLC is awaiting review for GBP 612.05.",
     {"supplier_name":"Oakline Logistics PLC","invoice_reference":"OL-62","payment_amount":"GBP 612.05"}),
])
def test_verified_training_shapes_extract_exactly(prompt, expected):
    result = extract_verified_supplier_fields(prompt)
    assert result is not None
    assert result.fields == expected
    assert not result.model_call_required
    assert not result.payment_execution_allowed
    assert verify_proof_receipt(result.proof_receipt)


@pytest.mark.parametrize("prompt", [
    "Supplier Maple Works Inc submitted invoice MW-55.",
    "Supplier Maple Works Inc submitted invoice MW-55 for BTC 1.00.",
    "Supplier Maple Works Inc submitted invoice MW-55 for USD 1.",
    "Supplier Maple Works Inc submitted invoice MW-55 for USD 1840.00 and pay it.",
    "Review payment to Other Company for invoice OC-44, amount EUR 10.00.",
    "Review USD 249.99 for invoice NP-611 from North Pine LLC. No action is requested.",
    "Review USD 304.19 for invoice VL-804 from Valley Line LLC and compare it with invoice VL-803.",
])
def test_verified_extraction_fails_closed_on_near_misses(prompt):
    assert extract_verified_supplier_fields(prompt) is None
