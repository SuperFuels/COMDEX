from backend.modules.aion_inference import draft_verified_quotation, verify_proof_receipt


def test_bounded_quotation_is_exact_and_cannot_be_sent_or_paid():
    result = draft_verified_quotation(
        "Prepare a draft quotation for Patio Repair: base EUR 120, markup 20%. "
        "Do not send it; human approval is required."
    )
    assert result is not None
    assert result.answer == (
        "DRAFT — Patio Repair: base EUR 120.00; markup 20%; total EUR 144.00. "
        "Not sent; human approval required."
    )
    assert result.structured_result["total"] == "144.00"
    assert result.proof_receipt["inverse_verified"]
    assert verify_proof_receipt(result.proof_receipt)
    assert not result.model_call_required
    assert result.human_approval_required
    assert not result.send_allowed
    assert not result.payment_allowed


def test_quotation_fails_closed_outside_complete_grammar_or_bounds():
    assert draft_verified_quotation(
        "Prepare a quotation for Patio Repair: base EUR 120, markup 20%."
    ) is None
    assert draft_verified_quotation(
        "Prepare a draft quotation for Patio Repair: base EUR 120, markup 101%. "
        "Do not send it; human approval is required."
    ) is None
    assert draft_verified_quotation(
        "Prepare a draft quotation for Patio Repair: base EUR 120, markup 20%. "
        "Send it automatically."
    ) is None
