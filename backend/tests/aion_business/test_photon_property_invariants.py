from __future__ import annotations

from hypothesis import given, settings, strategies as st

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedger,
    PhotonLedgerEntry,
    PhotonPriceBook,
)


@settings(max_examples=150, deadline=None)
@given(
    price=st.integers(min_value=1, max_value=1_000_000_000),
    lower=st.integers(min_value=0, max_value=1_000_000_000),
    increase=st.integers(min_value=0, max_value=1_000_000),
)
def test_price_conversion_is_integer_nonnegative_and_monotonic(price, lower, increase):
    book = PhotonPriceBook(
        version="property-v1", currency="GBP",
        minor_units_per_1000_photons=price,
        action_rates={"bounded.action": 1},
        effective_at="2026-10-18T00:00:00Z", region="global", cohort="all",
        reason="Property-test approved price",
    )
    first = book.minor_units_for(lower)
    second = book.minor_units_for(lower + increase)
    assert isinstance(first, int) and isinstance(second, int)
    assert 0 <= first <= second


@settings(max_examples=150, deadline=None)
@given(
    left=st.integers(min_value=1, max_value=1_000_000_000),
    right=st.integers(min_value=1, max_value=1_000_000_000),
)
def test_ledger_conservation_and_idempotency_hold_for_generated_entries(left, right):
    ledger = PhotonLedger()
    quantity = left + right
    entries = [
        PhotonLedgerEntry("platform.grant-liability", -quantity),
        PhotonLedgerEntry("customer.available", left),
        PhotonLedgerEntry("customer.reserved", right),
    ]
    first = ledger.post(
        transaction_id="generated-transaction", tenant_id="tenant-property",
        reason="property_grant", source_receipt_id="generated-receipt",
        rate_card_version="property-v1", idempotency_key="generated-key",
        recorded_at="2026-10-18T00:00:00Z", entries=entries,
    )
    replay = ledger.post(
        transaction_id="generated-transaction", tenant_id="tenant-property",
        reason="property_grant", source_receipt_id="generated-receipt",
        rate_card_version="property-v1", idempotency_key="generated-key",
        recorded_at="2026-10-18T00:00:00Z", entries=entries,
    )
    assert first == replay
    assert len(ledger.export()) == 1
    assert sum(ledger.balances(tenant_id="tenant-property").values()) == 0
