from pathlib import Path
import ast
import re


GATEWAY_MODULES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
    "backend/modules/aion_gateway/fulfilment_job.py",
    "backend/modules/aion_gateway/fulfilment_job_core.py",
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
]


FORBIDDEN_LIVE_ESCROW_IMPORT_TERMS = [
    "escrow_provider",
    "escrowprovider",
    "paymentintent",
    "checkout.session",
    "release_payment",
    "release_escrow",
    "capture_payment",
    "transfer_funds",
]


REQUIRED_FALSE_OR_PREVIEW_TERMS = [
    "would_create_escrow",
    "would_release_funds",
    "would_move_money",
    "would_create_payment",
    "would_require_wallet",
    "preview_only",
    "human_review_required",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_no_escrow_gateway_modules_exist():
    for path in GATEWAY_MODULES:
        assert Path(path).exists(), path


def test_phase13_no_escrow_modules_do_not_import_live_escrow_or_payment_providers():
    for path in GATEWAY_MODULES:
        text = _text(path).lower()

        for forbidden in FORBIDDEN_LIVE_ESCROW_IMPORT_TERMS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_phase13_no_escrow_public_embed_guard_blocks_escrow_and_funds():
    text = _text("backend/modules/aion_gateway/public_embed_guard_envelope.py")

    for term in [
        '"would_create_escrow": False',
        '"would_release_funds": False',
        '"would_move_money": False',
        '"would_create_payment": False',
        '"would_require_wallet": False',
        '"preview_only": True',
        '"human_review_required": True',
    ]:
        assert term in text


def test_phase13_no_escrow_public_intent_gateway_blocks_escrow_and_funds():
    text = _text("backend/modules/aion_gateway/public_intent_gateway.py")

    for term in [
        "would_create_escrow",
        "would_move_money",
        "would_create_payment",
        "would_require_wallet",
        "preview_only",
        "human_review_required",
    ]:
        assert term in text


def test_phase13_no_escrow_public_widget_mapping_blocks_escrow_and_funds():
    text = _text("backend/modules/aion_gateway/public_widget_request_mapping.py")

    for term in [
        "would_create_escrow",
        "would_move_money",
        "would_create_payment",
        "would_require_wallet",
        "preview_only",
        "human_review_required",
    ]:
        assert term in text


def test_phase13_no_escrow_human_review_handoff_blocks_approval_money_path():
    text = _text("backend/modules/aion_gateway/public_embed_human_review_handoff.py")

    for term in [
        "approval_can_move_money",
        "approval_can_send_external_messages",
        "next_step",
        "future_guarded_approval_path",
    ]:
        assert term in text

    for term in [
        '"approval_can_move_money": False',
        '"approval_can_send_external_messages": False',
    ]:
        assert term in text


def test_phase13_no_escrow_settlement_readiness_is_preview_only_not_payment_rail():
    text = _text("backend/modules/aion_gateway/settlement_readiness.py").lower()

    for term in [
        "settlement",
        "readiness",
        "requires_wallet",
        "requires_token",
        "requires_pho",
    ]:
        assert term in text

    for forbidden in [
        "release_escrow",
        "capture_payment",
        "transfer_funds",
        "checkout.session",
        "paymentintent",
    ]:
        assert forbidden not in text


def test_phase13_no_escrow_regression_static_module_list_has_no_missing_paths():
    this_file = Path(__file__).read_text(encoding="utf-8")
    match = re.search(r"GATEWAY_MODULES\s*=\s*(\[[\s\S]*?\])", this_file)
    assert match

    modules = ast.literal_eval(match.group(1))
    missing = [path for path in modules if not Path(path).exists()]
    assert missing == []
