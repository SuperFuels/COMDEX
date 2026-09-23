from pathlib import Path

import pytest

from backend.modules.aion_inference.business_map import (
    BUSINESS_MAP_TRUST_ANCHORS,
    SUPPLIER_PAYMENT_CARTRIDGE,
    SUPPLIER_PAYMENT_SIGNATURE,
    verify_business_map_cartridge,
)
from backend.scripts.promote_aion_business_map_to_sd import install_verified_bundle
from backend.scripts.run_aion_business_map_qwen_economics import _normalize_extraction


def test_business_map_install_is_verified_and_exclusive(tmp_path):
    destination = tmp_path / "business-maps" / "supplier-payment-controls-v1"
    report = install_verified_bundle(
        cartridge=SUPPLIER_PAYMENT_CARTRIDGE,
        signature=SUPPLIER_PAYMENT_SIGNATURE,
        trust_anchors=BUSINESS_MAP_TRUST_ANCHORS,
        destination=destination,
    )
    assert report["installed_verification_passed"]
    assert report["source_and_installed_hashes_identical"]
    assert report["install_receipt_sha256"]
    assert verify_business_map_cartridge(
        destination / SUPPLIER_PAYMENT_CARTRIDGE.name,
        destination / SUPPLIER_PAYMENT_SIGNATURE.name,
        destination / BUSINESS_MAP_TRUST_ANCHORS.name,
    ).passed
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        install_verified_bundle(
            cartridge=SUPPLIER_PAYMENT_CARTRIDGE,
            signature=SUPPLIER_PAYMENT_SIGNATURE,
            trust_anchors=BUSINESS_MAP_TRUST_ANCHORS,
            destination=destination,
        )


def test_business_map_install_rejects_tampered_source(tmp_path):
    cartridge = tmp_path / SUPPLIER_PAYMENT_CARTRIDGE.name
    cartridge.write_bytes(SUPPLIER_PAYMENT_CARTRIDGE.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source cartridge failed closed"):
        install_verified_bundle(
            cartridge=cartridge,
            signature=SUPPLIER_PAYMENT_SIGNATURE,
            trust_anchors=BUSINESS_MAP_TRUST_ANCHORS,
            destination=tmp_path / "installed",
        )


def test_qwen_extraction_normalizer_removes_only_leading_role_label():
    normalized, changes = _normalize_extraction({
        "supplier_name": "Vendor Atlas Packaging BV",
        "invoice_reference": "AP-117",
        "payment_amount": "USD 72.18",
    })
    assert normalized["supplier_name"] == "Atlas Packaging BV"
    assert changes == ("strip_leading_supplier_role_label",)
    unchanged, no_changes = _normalize_extraction({"supplier_name": "VendorWorks Ltd"})
    assert unchanged["supplier_name"] == "VendorWorks Ltd"
    assert no_changes == ()
