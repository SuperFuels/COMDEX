from pathlib import Path


DOC = Path("docs/rfc/aion_public_embed_human_review_handoff_lock.tex")


def _text() -> str:
    assert DOC.exists(), f"Missing lock doc: {DOC}"
    return DOC.read_text()


def test_public_embed_human_review_handoff_doc_exists_and_names_phase():
    text = _text()
    assert "Phase 12F" in text
    assert "Public Embed Human Review Handoff Preview v0" in text


def test_public_embed_human_review_handoff_doc_lists_module_and_exports():
    text = _text()
    assert "public_embed_human_review_handoff.py" in text
    assert "PUBLIC\\_EMBED\\_HUMAN\\_REVIEW\\_HANDOFF\\_VERSION" in text
    assert "SUPPORTED\\_REVIEW\\_DECISIONS" in text
    assert "build\\_public\\_embed\\_human\\_review\\_handoff\\_preview" in text
    assert "build\\_public\\_embed\\_human\\_review\\_handoff\\_summary" in text


def test_public_embed_human_review_handoff_doc_lists_review_queue_and_decisions():
    text = _text()
    assert "aion_public_embed_human_review" in text
    for term in [
        "approve_preview_only",
        "reject_preview_only",
        "request_more_info_preview_only",
        "escalate_preview_only",
    ]:
        assert term in text


def test_public_embed_human_review_handoff_doc_lists_approval_boundary():
    text = _text()
    for term in [
        "human_review_required = true",
        "human_review_completed = false",
        "approval_decision_recorded = false",
        "approval_can_create_live_job = false",
        "approval_can_execute_goal_engine = false",
        "approval_can_move_money = false",
        "approval_can_send_external_messages = false",
        "next_step = future_guarded_approval_path",
    ]:
        assert term in text


def test_public_embed_human_review_handoff_doc_lists_hashes():
    text = _text()
    for term in [
        "review\\_package\\_hash",
        "approval\\_boundary\\_hash",
        "safety\\_hash",
        "response\\_hash",
        "summary\\_hash",
    ]:
        assert term in text


def test_public_embed_human_review_handoff_doc_states_safety():
    text = _text()
    for term in [
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "expose an unauthenticated public write route",
    ]:
        assert term in text


def test_public_embed_human_review_handoff_doc_says_no_frontend_smoke_test():
    text = _text()
    assert "does not create a new frontend visual surface" in text
    assert "No new manual frontend smoke test is required" in text


def test_public_embed_human_review_handoff_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
