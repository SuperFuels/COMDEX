from backend.services.aion_mission_mode.canonical_payload_hashing import (
    approval_payload_hash_matches,
    canonical_json,
    create_payload_hash_record,
    invalidate_approval_if_payload_changed,
    payload_sha256,
    validate_payload_before_execution,
)


def test_phase20y_canonical_json_sorts_keys() -> None:
    first = canonical_json({"b": 2, "a": 1})
    second = canonical_json({"a": 1, "b": 2})

    assert first == second
    assert first == '{"a":1,"b":2}'


def test_phase20y_payload_hash_ignores_non_semantic_key_order() -> None:
    first = payload_sha256({"b": 2, "a": 1})
    second = payload_sha256({"a": 1, "b": 2})

    assert first == second
    assert first.startswith("sha256:")


def test_phase20y_payload_hash_changes_when_value_changes() -> None:
    first = payload_sha256({"message": "A"})
    second = payload_sha256({"message": "B"})

    assert first != second


def test_phase20y_payload_hash_record_contains_canonical_payload() -> None:
    record = create_payload_hash_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_001",
        step_id="step_001",
        action_type="publish_advert",
        payload={"b": 2, "a": 1},
    )

    assert record["payload_hash"].startswith("sha256:")
    assert record["canonical_payload"] == '{"a":1,"b":2}'
    assert record["hash_algorithm"] == "sha256"
    assert record["schema_version"] == "aion.payload_hash.v0"


def test_phase20y_execution_validation_allows_unchanged_payload() -> None:
    payload = {"message": "Draft", "cta": "Call"}
    approved_hash = payload_sha256(payload)

    result = validate_payload_before_execution(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_001",
        step_id="step_001",
        action_type="publish_advert",
        approved_payload_hash=approved_hash,
        current_payload=payload,
    )

    assert result["payload_unchanged"] is True
    assert result["execution_allowed"] is True
    assert result["reason"] == "payload_hash_match"
    assert result["validation_hash"].startswith("sha256:")


def test_phase20y_execution_validation_blocks_changed_payload() -> None:
    approved_payload = {"message": "Draft", "cta": "Call"}
    edited_payload = {"message": "Edited", "cta": "Call"}

    result = validate_payload_before_execution(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_001",
        step_id="step_001",
        action_type="publish_advert",
        approved_payload_hash=payload_sha256(approved_payload),
        current_payload=edited_payload,
    )

    assert result["payload_unchanged"] is False
    assert result["execution_allowed"] is False
    assert result["reason"] == "payload_hash_mismatch_requires_fresh_approval"


def test_phase20y_approval_payload_hash_matches_current_payload() -> None:
    payload = {"message": "Draft"}
    approval = {"payload_hash": payload_sha256(payload)}

    assert approval_payload_hash_matches(approval=approval, current_payload=payload) is True


def test_phase20y_approval_payload_hash_rejects_edited_payload() -> None:
    original = {"message": "Draft"}
    edited = {"message": "Edited"}
    approval = {"payload_hash": payload_sha256(original)}

    assert approval_payload_hash_matches(approval=approval, current_payload=edited) is False


def test_phase20y_invalidates_approval_if_payload_changed() -> None:
    original = {"message": "Draft"}
    edited = {"message": "Edited"}
    approval = {"payload_hash": payload_sha256(original)}

    result = invalidate_approval_if_payload_changed(
        approval=approval,
        current_payload=edited,
    )

    assert result["approval_valid"] is False
    assert result["requires_fresh_approval"] is True
    assert result["reason"] == "payload_changed_after_approval"


def test_phase20y_keeps_approval_valid_if_payload_unchanged() -> None:
    payload = {"message": "Draft"}
    approval = {"payload_hash": payload_sha256(payload)}

    result = invalidate_approval_if_payload_changed(
        approval=approval,
        current_payload=payload,
    )

    assert result["approval_valid"] is True
    assert result["requires_fresh_approval"] is False
    assert result["reason"] == "payload_unchanged"


def test_phase20y1_integral_float_and_int_hash_identically() -> None:
    from backend.services.aion_mission_mode.canonical_payload_hashing import (
        payload_sha256_normalized,
    )

    assert payload_sha256_normalized({"max_limit": 100}) == payload_sha256_normalized({"max_limit": 100.0})


def test_phase20y1_float_precision_is_deterministic() -> None:
    from backend.services.aion_mission_mode.canonical_payload_hashing import (
        canonical_json_normalized,
    )

    first = canonical_json_normalized({"price": 10.1234564})
    second = canonical_json_normalized({"price": 10.12345640001})

    assert first == second


def test_phase20y1_unicode_nfc_normalisation_hashes_equivalent_strings() -> None:
    from backend.services.aion_mission_mode.canonical_payload_hashing import (
        payload_sha256_normalized,
    )

    composed = {"text": "Café"}
    decomposed = {"text": "Cafe\u0301"}

    assert payload_sha256_normalized(composed) == payload_sha256_normalized(decomposed)


def test_phase20y1_normalized_validation_allows_int_float_equivalent_payload() -> None:
    from backend.services.aion_mission_mode.canonical_payload_hashing import (
        payload_sha256_normalized,
        validate_payload_before_execution_normalized,
    )

    approved_payload = {"max_limit": 100}
    current_payload = {"max_limit": 100.0}

    result = validate_payload_before_execution_normalized(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_001",
        step_id="step_001",
        action_type="publish_advert",
        approved_payload_hash=payload_sha256_normalized(approved_payload),
        current_payload=current_payload,
    )

    assert result["payload_unchanged"] is True
    assert result["execution_allowed"] is True
    assert result["validation_hash"].startswith("sha256:")


def test_phase20y1_validation_hash_closure_changes_when_decision_changes() -> None:
    from backend.services.aion_mission_mode.canonical_payload_hashing import (
        validation_hash_closure,
    )

    first = validation_hash_closure(
        approved_payload_hash="sha256:a",
        current_payload_hash="sha256:a",
        payload_unchanged=True,
        execution_allowed=True,
        reason="payload_hash_match",
        step_id="step_001",
    )

    second = validation_hash_closure(
        approved_payload_hash="sha256:a",
        current_payload_hash="sha256:b",
        payload_unchanged=False,
        execution_allowed=False,
        reason="payload_hash_mismatch_requires_fresh_approval",
        step_id="step_001",
    )

    assert first != second
    assert first.startswith("sha256:")
    assert second.startswith("sha256:")
