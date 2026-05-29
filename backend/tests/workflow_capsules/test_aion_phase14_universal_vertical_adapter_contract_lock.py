from backend.modules.aion_gateway.universal_vertical_adapter import (
    FUTURE_VERTICAL_KEYS,
    UNIVERSAL_FIELD_KEYS,
    UNIVERSAL_VERTICAL_ADAPTER_VERSION,
    build_home_fixed_universal_vertical_adapter,
    build_universal_vertical_adapter_contract,
    build_universal_vertical_adapter_summary,
)


def test_universal_vertical_adapter_contract_has_stable_identity():
    adapter = build_home_fixed_universal_vertical_adapter()

    assert adapter["adapter_version"] == UNIVERSAL_VERTICAL_ADAPTER_VERSION
    assert adapter["business_id"] == "home_fixed"
    assert adapter["business_name"] == "Home Fixed"
    assert adapter["vertical_key"] == "home_repair"
    assert adapter["industry_key"] == "trades"
    assert len(adapter["adapter_hash"]) == 64
    assert len(adapter["summary_hash"]) == 64


def test_universal_vertical_adapter_is_not_trade_only():
    adapter = build_home_fixed_universal_vertical_adapter()

    assert adapter["compatibility"]["gateway_is_trade_only"] is False

    for key in (
        "home_repair",
        "legal",
        "ecommerce",
        "hospitality",
        "clinic",
        "property",
        "b2b_supplier",
    ):
        assert key in adapter["supported_verticals"]

    assert tuple(adapter["supported_verticals"]) == FUTURE_VERTICAL_KEYS


def test_home_repair_maps_to_universal_fields():
    adapter = build_home_fixed_universal_vertical_adapter()

    assert adapter["vertical_field_map"]["jobs"] == "service"
    assert adapter["vertical_field_map"]["quotes"] == "quote"
    assert adapter["vertical_field_map"]["availability"] == "availability"
    assert adapter["vertical_field_map"]["evidence"] == "evidence"
    assert adapter["vertical_field_map"]["proof_receipts"] == "proof"
    assert adapter["vertical_field_map"]["trust_summary"] == "trust"
    assert adapter["vertical_field_map"]["human_review_handoff"] == "human_review"

    for key in UNIVERSAL_FIELD_KEYS:
        assert key in adapter["universal_shape"]


def test_adapter_hash_is_deterministic_and_changes_with_meaningful_content():
    first = build_home_fixed_universal_vertical_adapter()
    second = build_home_fixed_universal_vertical_adapter()

    assert first["adapter_hash"] == second["adapter_hash"]
    assert first["summary_hash"] == second["summary_hash"]

    changed = build_universal_vertical_adapter_contract(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        industry_key="trades",
        vertical_fields={"jobs": ["different_service_preview"]},
    )

    assert changed["adapter_hash"] != first["adapter_hash"]


def test_adapter_safety_profile_remains_preview_only_and_non_executing():
    adapter = build_home_fixed_universal_vertical_adapter()
    safety = adapter["safety_profile"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_live_job"] is False
    assert safety["would_execute_goal_engine"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_release_funds"] is False
    assert safety["would_send_external_messages"] is False
    assert safety["would_dispatch_job"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["public_route_mounted"] is False


def test_adapter_summary_is_safe_and_deterministic():
    adapter = build_home_fixed_universal_vertical_adapter()
    first = build_universal_vertical_adapter_summary(adapter)
    second = build_universal_vertical_adapter_summary(adapter)

    assert first == second
    assert first["preview_only"] is True
    assert first["human_review_required"] is True
    assert first["gateway_is_trade_only"] is False
    assert len(first["adapter_hash"]) == 64
    assert len(first["summary_hash"]) == 64


def test_adapter_module_does_not_use_runtime_random_or_live_provider_terms():
    import inspect
    import backend.modules.aion_gateway.universal_vertical_adapter as module

    source = inspect.getsource(module)

    forbidden = [
        "uuid.uuid4",
        "random.random",
        "secrets.token",
        "time.time",
        "datetime.now",
        "smtplib",
        "twilio",
        "sendgrid",
        "stripe.",
        "revolut",
        "paypal",
        "release_escrow(",
        "capture_payment(",
        "send_email(",
        "send_sms(",
        "post_social(",
        "create_booking(",
        "dispatch_job(",
    ]

    for term in forbidden:
        assert term not in source
