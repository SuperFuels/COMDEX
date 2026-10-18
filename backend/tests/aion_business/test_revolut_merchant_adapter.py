from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.revolut_merchant_adapter import (
    REVOLUT_API_VERSION,
    REVOLUT_SANDBOX_ORIGIN,
    RevolutMerchantAdapter,
    RevolutMerchantAdapterError,
)


def order_response(**overrides):
    result = {
        "id": "order-1",
        "token": "checkout-token-1",
        "checkout_url": "https://sandbox-merchant.revolut.com/checkout/order-1",
        "amount": 1000,
        "currency": "GBP",
        "state": "pending",
        "merchant_order_data": {"reference": "checkout-1"},
        "created_at": "2026-10-18T01:00:00Z",
        "updated_at": "2026-10-18T01:00:00Z",
    }
    result.update(overrides)
    return result


def test_sandbox_create_uses_secret_server_side_and_exact_snapshot():
    calls = []

    def transport(method, url, headers, body, timeout):
        calls.append((method, url, dict(headers), body, timeout))
        return 201, json.dumps(order_response()).encode()

    adapter = RevolutMerchantAdapter(
        secret_provider=lambda: "sk_sandbox_secret_value",
        transport=transport,
    )
    order = adapter.create_order(
        external_reference="checkout-1", amount_minor=1000, currency="gbp",
        redirect_url="https://billing.tessaris.example/return",
    )
    assert order.order_id == "order-1" and order.amount_minor == 1000
    method, url, headers, body, _ = calls[0]
    assert method == "POST" and url == REVOLUT_SANDBOX_ORIGIN + "/api/orders"
    assert headers["Authorization"] == "Bearer sk_sandbox_secret_value"
    assert headers["Revolut-Api-Version"] == REVOLUT_API_VERSION
    assert headers["Idempotency-Key"] == "checkout-1"
    sent = json.loads(body)
    assert sent == {
        "amount": 1000,
        "currency": "GBP",
        "merchant_order_data": {"reference": "checkout-1"},
        "redirect_url": "https://billing.tessaris.example/return",
    }


def test_retrieve_normalizes_only_fulfilment_fields():
    def transport(method, url, headers, body, timeout):
        assert method == "GET" and body is None
        return 200, json.dumps(order_response(state="completed")).encode()

    adapter = RevolutMerchantAdapter(
        secret_provider=lambda: "sk_sandbox_secret_value", transport=transport
    )
    assert adapter.retrieve_order("order-1") == {
        "id": "order-1",
        "external_reference": "checkout-1",
        "amount_minor": 1000,
        "currency": "GBP",
        "state": "completed",
        "updated_at": "2026-10-18T01:00:00Z",
    }


def test_production_and_insecure_redirect_fail_closed():
    with pytest.raises(RevolutMerchantAdapterError, match="production_not_enabled"):
        RevolutMerchantAdapter(
            secret_provider=lambda: "sk_production_secret", environment="production"
        )
    adapter = RevolutMerchantAdapter(
        secret_provider=lambda: "sk_sandbox_secret_value",
        transport=lambda *args: (500, b"{}"),
    )
    with pytest.raises(RevolutMerchantAdapterError, match="redirect_url_invalid"):
        adapter.create_order(
            external_reference="checkout-1", amount_minor=1000,
            currency="GBP", redirect_url="http://billing.example/return",
        )


def test_provider_mismatch_invalid_json_and_missing_secret_fail_closed():
    mismatch = RevolutMerchantAdapter(
        secret_provider=lambda: "sk_sandbox_secret_value",
        transport=lambda *args: (
            201, json.dumps(order_response(amount=999)).encode()
        ),
    )
    with pytest.raises(RevolutMerchantAdapterError, match="created_order_mismatch"):
        mismatch.create_order(
            external_reference="checkout-1", amount_minor=1000, currency="GBP"
        )

    invalid = RevolutMerchantAdapter(
        secret_provider=lambda: "sk_sandbox_secret_value",
        transport=lambda *args: (200, b"not-json"),
    )
    with pytest.raises(RevolutMerchantAdapterError, match="response_invalid"):
        invalid.retrieve_order("order-1")

    missing = RevolutMerchantAdapter(
        secret_provider=lambda: "", transport=lambda *args: (200, b"{}")
    )
    with pytest.raises(RevolutMerchantAdapterError, match="secret_unavailable"):
        missing.retrieve_order("order-1")
