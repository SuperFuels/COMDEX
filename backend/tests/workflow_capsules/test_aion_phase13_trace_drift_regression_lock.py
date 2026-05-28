from pathlib import Path


TRACE_LOCK_FILES = [
    "backend/modules/aion_gateway/machine_trace.py",
    "backend/modules/aion_gateway/a2a_job_trace.py",
    "backend/modules/aion_gateway/a2a_job_evidence_settlement.py",
    "backend/modules/aion_gateway/a2a_proof_receipt.py",
    "backend/modules/aion_gateway/glyphchain_proof_commit.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
]


REQUIRED_TRACE_TERMS = [
    "hash",
    "trace",
    "request",
    "response",
]


FORBIDDEN_DRIFT_TERMS = [
    "random.uuid",
    "uuid.uuid4",
    "datetime.now()",
    "datetime.utcnow()",
    "secrets.token",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_trace_drift_files_exist():
    for path in TRACE_LOCK_FILES:
        assert Path(path).exists(), path


def test_phase13_trace_drift_files_have_trace_or_hash_terms():
    for path in TRACE_LOCK_FILES:
        text = _text(path).lower()
        assert any(term in text for term in REQUIRED_TRACE_TERMS), path


def test_phase13_trace_drift_avoids_runtime_random_trace_ids():
    for path in TRACE_LOCK_FILES:
        text = _text(path).lower()
        for forbidden in FORBIDDEN_DRIFT_TERMS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_phase13_trace_drift_allows_existing_glyphchain_timestamp_only_not_identity():
    text = _text("backend/modules/aion_gateway/glyphchain_proof_commit.py").lower()

    # Existing proof commits may record a timestamp, but trace/proof identity
    # must still be deterministic/hash-derived rather than runtime-random.
    assert "time.time()" in text
    assert "hashlib" in text
    assert "sha256" in text
    assert "_stable_hash" in text
    assert "proof_hash" in text
    assert "receipt_hash" in text
    assert "uuid.uuid4" not in text
    assert "random.uuid" not in text
    assert "secrets.token" not in text


def test_phase13_public_widget_mapping_has_stable_hashes():
    text = _text("backend/modules/aion_gateway/public_widget_request_mapping.py")

    for term in [
        "request_hash",
        "normalized_intent_hash",
        "machine_cart_request_hash",
        "response_hash",
        "summary_hash",
    ]:
        assert term in text


def test_phase13_public_embed_guard_envelope_has_stable_hashes():
    text = _text("backend/modules/aion_gateway/public_embed_guard_envelope.py")

    for term in [
        "request_hash",
        "guard_hash",
        "safety_hash",
        "response_hash",
        "summary_hash",
    ]:
        assert term in text


def test_phase13_public_embed_handoff_has_stable_hashes():
    text = _text("backend/modules/aion_gateway/public_embed_human_review_handoff.py")

    for term in [
        "review_package_hash",
        "approval_boundary_hash",
        "safety_hash",
        "response_hash",
        "summary_hash",
    ]:
        assert term in text


def test_phase13_trace_drift_no_public_embed_side_effects():
    combined = "\n".join(
        _text(path)
        for path in [
            "backend/modules/aion_gateway/public_widget_request_mapping.py",
            "backend/modules/aion_gateway/public_embed_guard_envelope.py",
            "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
        ]
    ).lower()

    for term in [
        "preview_only",
        "human_review_required",
    ]:
        assert term in combined

    for forbidden in [
        "would_create_live_job\": true",
        "would_execute_goal_engine\": true",
        "would_move_money\": true",
        "would_create_payment\": true",
        "would_create_escrow\": true",
        "would_release_funds\": true",
        "would_send_external_messages\": true",
        "unauthenticated_public_write_route_exposed\": true",
    ]:
        assert forbidden not in combined
