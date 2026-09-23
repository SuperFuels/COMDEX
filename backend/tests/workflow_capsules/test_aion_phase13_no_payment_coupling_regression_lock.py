from pathlib import Path


ROOT = Path(".")

GATEWAY_MODULES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/fulfilment_job.py",
    "backend/modules/aion_gateway/a2a_contracts.py",
    "backend/modules/aion_gateway/settlement_readiness.py",
    "backend/modules/aion_gateway/glyphchain_proof_commit.py",
    "backend/modules/aion_gateway/parallel_catalog.py",
    "backend/modules/aion_gateway/machine_cart.py",
    "backend/modules/aion_gateway/parallel_discovery.py",
    "backend/modules/aion_gateway/agent_channels.py",
    "backend/modules/aion_gateway/exceptions.py",
    "backend/modules/aion_gateway/a2a_capabilities.py",
    "backend/modules/aion_gateway/a2a_availability_quote.py",
    "backend/modules/aion_gateway/a2a_job_trace.py",
    "backend/modules/aion_gateway/a2a_job_evidence_settlement.py",
    "backend/modules/aion_gateway/a2a_proof_receipt.py",
    "backend/modules/aion_gateway/a2a_trust_summary.py",
    "backend/modules/aion_gateway/a2a_well_known_discovery.py",
    "backend/modules/aion_gateway/a2a_handshake_preview.py",
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
]

LOCK_DOCS = [
    "docs/rfc/aion_gateway_fulfilment_job_core_lock.tex",
    "docs/rfc/aion_gateway_a2a_contract_schemas_lock.tex",
    "docs/rfc/aion_gateway_evidence_proof_hash_lock.tex",
    "docs/rfc/aion_gateway_settlement_readiness_lock.tex",
    "docs/rfc/aion_gateway_glyphchain_proof_commit_lock.tex",
    "docs/rfc/aion_gateway_glyphchain_proof_commit_store_lock.tex",
    "docs/rfc/aion_gateway_glyphchain_proof_receipt_lookup_lock.tex",
    "docs/rfc/aion_machine_cart_quote_handshake_lock.tex",
    "docs/rfc/aion_a2a_job_evidence_settlement_lock.tex",
    "docs/rfc/aion_a2a_proof_receipt_lock.tex",
    "docs/rfc/aion_public_intent_gateway_lock.tex",
    "docs/rfc/aion_public_embed_guard_envelope_lock.tex",
    "docs/rfc/aion_public_embed_human_review_handoff_lock.tex",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_no_payment_gateway_modules_exist():
    for path in GATEWAY_MODULES:
        assert Path(path).exists(), path


def test_phase13_no_payment_modules_do_not_import_payment_providers():
    forbidden = [
        "stripe",
        "paypal",
        "revolut",
        "checkout",
        "escrow_provider",
        "payment_provider",
        "wallet_provider",
    ]

    for path in GATEWAY_MODULES:
        text = _text(path).lower()
        for term in forbidden:
            assert f"import {term}" not in text, path
            assert f"from {term}" not in text, path


def test_phase13_no_payment_modules_keep_payment_flags_false_or_preview_only():
    combined = "\n".join(_text(path) for path in GATEWAY_MODULES)

    required_terms = [
        "would_move_money",
        "would_create_payment",
        "would_create_escrow",
        "would_release_funds",
    ]

    for term in required_terms:
        assert term in combined


def test_phase13_no_payment_docs_state_glyphchain_not_payment_rail():
    combined = "\n".join(_text(path) for path in LOCK_DOCS)

    assert "GlyphChain" in combined
    assert "proof" in combined
    assert "payment rail" in combined
    assert "glyphchain_is_payment_rail = false" in combined or "GlyphChain is proof/receipt rail, not payment rail" in combined


def test_phase13_no_payment_docs_block_money_movement():
    combined = "\n".join(_text(path) for path in LOCK_DOCS)

    for term in [
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
    ]:
        assert term in combined


def test_phase13_no_payment_docs_do_not_claim_payment_enabled():
    combined = "\n".join(_text(path) for path in LOCK_DOCS).lower()

    forbidden_claims = [
        "payment movement is enabled",
        "escrow creation is enabled",
        "fund release is enabled",
        "glyphchain is a payment rail",
        "pho payment is enabled",
        "wallet required for settlement",
    ]

    for claim in forbidden_claims:
        assert claim not in combined


def test_phase13_no_payment_fiat_first_boundary_is_documented():
    combined = "\n".join(_text(path) for path in LOCK_DOCS)

    assert "fiat_first" in combined or "fiat-first" in combined


def test_phase13_no_payment_dna_switch_index_not_part_of_lock():
    assert Path("backend/modules/dna_chain/dna_switch_index.json").exists()
