from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonPriceBook
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import (
    PhotonRevolutFulfilment,
)
from backend.modules.aion_business.runtime.revolut_merchant_adapter import (
    RevolutCheckoutOrder,
)


class CheckoutProvider(Protocol):
    def create_order(
        self,
        *,
        external_reference: str,
        amount_minor: int,
        currency: str,
        redirect_url: str | None = None,
    ) -> RevolutCheckoutOrder: ...


class PhotonRevolutCheckoutCoordinator:
    """Bind a fixed bundle and active signed price book to a provider order.

    The caller chooses a published bundle identifier, never the Photon quantity,
    fiat amount or price-book version. Those values are resolved server-side and
    frozen into the immutable fulfilment intent before checkout is returned.
    """

    def __init__(
        self,
        *,
        provider: CheckoutProvider,
        fulfilment: PhotonRevolutFulfilment,
        price_book_resolver: Callable[..., Mapping[str, Any]],
        bundle_catalog: Mapping[str, int],
    ) -> None:
        catalog: dict[str, int] = {}
        for product_id, photons in bundle_catalog.items():
            product = PhotonRevolutFulfilment._safe(product_id, "product_id")
            quantity = int(photons)
            if not 1 <= quantity <= 1_000_000_000:
                raise ValueError("photon_bundle_quantity_invalid")
            catalog[product] = quantity
        if not catalog:
            raise ValueError("photon_bundle_catalog_required")
        self.provider = provider
        self.fulfilment = fulfilment
        self.price_book_resolver = price_book_resolver
        self.bundle_catalog = catalog

    def create_checkout(
        self,
        *,
        tenant_id: str,
        product_id: str,
        external_reference: str,
        currency: str,
        region: str,
        cohort: str,
        created_at: str,
        redirect_url: str | None = None,
    ) -> dict[str, Any]:
        tenant = PhotonRevolutFulfilment._safe(tenant_id, "tenant_id")
        product = PhotonRevolutFulfilment._safe(product_id, "product_id")
        reference = PhotonRevolutFulfilment._safe(
            external_reference, "external_reference"
        )
        if product not in self.bundle_catalog:
            raise KeyError("photon_bundle_not_found")
        record = dict(
            self.price_book_resolver(
                currency=str(currency).upper(),
                region=str(region),
                cohort=str(cohort),
                as_of=str(created_at),
            )
        )
        payload = dict(record.get("payload") or {})
        book = PhotonPriceBook(
            version=str(payload.get("version") or ""),
            currency=str(payload.get("currency") or ""),
            minor_units_per_1000_photons=int(
                payload.get("minor_units_per_1000_photons") or 0
            ),
            action_rates=dict(payload.get("action_rates") or {}),
            effective_at=str(payload.get("effective_at") or ""),
            region=str(payload.get("region") or ""),
            cohort=str(payload.get("cohort") or ""),
            reason=str(payload.get("reason") or ""),
        )
        book.payload()
        photons = self.bundle_catalog[product]
        amount_minor = book.minor_units_for(photons)
        if amount_minor <= 0:
            raise ValueError("photon_bundle_amount_invalid")
        order = self.provider.create_order(
            external_reference=reference,
            amount_minor=amount_minor,
            currency=book.currency,
            redirect_url=redirect_url,
        )
        intent = self.fulfilment.record_checkout_intent(
            order_id=order.order_id,
            external_reference=reference,
            tenant_id=tenant,
            product_id=product,
            photons=photons,
            amount_minor=amount_minor,
            currency=book.currency,
            price_book_version=book.version,
            created_at=created_at,
        )
        return {
            "schema_version": "tessaris.photon-revolut-checkout.v1",
            "order_id": order.order_id,
            "token": order.token,
            "checkout_url": order.checkout_url,
            "external_reference": reference,
            "product_id": product,
            "photons": photons,
            "amount_minor": amount_minor,
            "currency": book.currency,
            "price_book_version": book.version,
            "provider": "revolut",
            "provider_environment": getattr(self.provider, "environment", "unknown"),
            "customer_content_included": False,
            "intent_recorded": intent["order_id"] == order.order_id,
        }
