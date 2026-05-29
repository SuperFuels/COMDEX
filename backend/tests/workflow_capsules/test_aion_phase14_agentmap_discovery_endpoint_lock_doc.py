from pathlib import Path

DOC = Path("docs/rfc/aion_phase14_agentmap_discovery_endpoint_lock.tex")


def test_phase14c_doc_exists():
    assert DOC.exists()


def test_phase14c_doc_mentions_required_contract_terms():
    text = DOC.read_text().lower()

    required_terms = [
        "phase 14c",
        "read-only agentmap discovery endpoint",
        "/agentmap.json",
        "/.well-known/agentmap.json",
        "agentmap_hash",
        "endpoint_hash",
        "summary_hash",
        "safe capability routes",
        "input_schema_ref",
        "output_schema_ref",
        "preview_only",
        "read_only",
        "human_review_required",
        "public_route_mounted",
        "would_create_booking",
        "would_create_payment",
        "would_create_escrow",
        "would_send_external_messages",
        "lock id",
    ]

    for term in required_terms:
        assert term in text


def test_phase14c_doc_states_no_live_side_effects():
    text = DOC.read_text().lower()

    required_terms = [
        "must not create bookings",
        "must not create live jobs",
        "must not execute the goal engine",
        "must not move money",
        "must not create payments",
        "must not create escrow",
        "must not release funds",
        "must not dispatch work",
        "must not send external messages",
        "must not write live chain data",
    ]

    for term in required_terms:
        assert term in text


def test_phase14c_doc_has_footer():
    text = DOC.read_text()

    assert "Lock ID:" in text
    assert "AION-PHASE14C-AGENTMAP-DISCOVERY-ENDPOINT-PREVIEW-v0.1" in text
    assert "Status:" in text
    assert "Maintainer:" in text
    assert "Tessaris AI" in text
    assert "Author:" in text
    assert "Kevin Robinson" in text
