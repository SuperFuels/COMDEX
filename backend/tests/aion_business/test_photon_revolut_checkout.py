from __future__ import annotations

from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonPriceBook
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_checkout import (
    PhotonRevolutCheckoutCoordinator,
)
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import (
    PhotonRevolutFulfilment,
)
from backend.modules.aion_business.runtime.revolut_merchant_adapter import (
    RevolutCheckoutOrder,
)


class Provider:
    environment = "sandbox"

    def __init__(self):
        self.calls = []

    def create_order(self, **kwargs):
        self.calls.append(kwargs)
        return RevolutCheckoutOrder(
            order_id="provider-order-1",
            token="provider-token-1",
            checkout_url="https://sandbox-merchant.revolut.com/checkout/1",
            external_reference=kwargs["external_reference"],
            amount_minor=kwargs["amount_minor"],
            currency=kwargs["currency"],
            state="pending",
        )


def price_record(**kwargs):
    book = PhotonPriceBook(
        version="price-v1", currency="GBP", minor_units_per_1000_photons=250,
        action_rates={"document.prepared": 10},
        effective_at="2026-10-18T00:00:00Z", region="global", cohort="all",
        reason="Initial approved pricing",
    )
    return {"payload": book.payload()}


def coordinator(tmp_path, provider=None):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    fulfilment = PhotonRevolutFulfilment(
        tmp_path / "fulfilment.sqlite3", ledger=ledger
    )
    return PhotonRevolutCheckoutCoordinator(
        provider=provider or Provider(), fulfilment=fulfilment,
        price_book_resolver=price_record,
        bundle_catalog={"bundle-10000": 10_000},
    ), fulfilment


def test_checkout_amount_and_photons_come_only_from_server_configuration(tmp_path):
    provider = Provider()
    service, fulfilment = coordinator(tmp_path, provider)
    result = service.create_checkout(
        tenant_id="tenant-1", product_id="bundle-10000",
        external_reference="checkout-1", currency="GBP", region="GB",
        cohort="standard", created_at="2026-10-18T01:00:00Z",
        redirect_url="https://billing.tessaris.example/return",
    )
    assert result["photons"] == 10_000
    assert result["amount_minor"] == 2500
    assert result["price_book_version"] == "price-v1"
    assert result["provider_environment"] == "sandbox"
    assert result["customer_content_included"] is False
    assert provider.calls[0]["amount_minor"] == 2500
    with fulfilment._connect() as connection:
        row = connection.execute(
            "SELECT tenant_id, photons, amount_minor, price_book_version FROM revolut_photon_intents"
        ).fetchone()
    assert tuple(row) == ("tenant-1", 10_000, 2500, "price-v1")


def test_unknown_bundle_fails_before_provider_or_intent(tmp_path):
    provider = Provider()
    service, fulfilment = coordinator(tmp_path, provider)
    try:
        service.create_checkout(
            tenant_id="tenant-1", product_id="bundle-invented",
            external_reference="checkout-1", currency="GBP", region="GB",
            cohort="standard", created_at="2026-10-18T01:00:00Z",
        )
    except KeyError as exc:
        assert "photon_bundle_not_found" in str(exc)
    else:
        raise AssertionError("unknown bundle was accepted")
    assert provider.calls == []
    with fulfilment._connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM revolut_photon_intents"
        ).fetchone()[0] == 0
