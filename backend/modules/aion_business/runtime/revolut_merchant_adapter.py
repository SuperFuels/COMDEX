from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import quote, urlparse


REVOLUT_API_VERSION = "2026-08-17"
REVOLUT_SANDBOX_ORIGIN = "https://sandbox-merchant.revolut.com"
REVOLUT_PRODUCTION_ORIGIN = "https://merchant.revolut.com"
SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_RESPONSE_BYTES = 1_048_576


class RevolutMerchantAdapterError(RuntimeError):
    pass


class SecretProvider(Protocol):
    def __call__(self) -> str: ...


class HttpTransport(Protocol):
    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> tuple[int, bytes]: ...


@dataclass(frozen=True)
class RevolutCheckoutOrder:
    order_id: str
    token: str
    checkout_url: str
    external_reference: str
    amount_minor: int
    currency: str
    state: str


def _default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout_seconds: float,
) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url=url, data=body, headers=dict(headers), method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            return int(response.status), payload
    except urllib.error.HTTPError as exc:
        # Never copy a provider response body into an exception: it may contain
        # customer or payment data. The status is enough for the operational log.
        raise RevolutMerchantAdapterError(
            f"revolut_merchant_http_error:{int(exc.code)}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RevolutMerchantAdapterError("revolut_merchant_transport_error") from exc


class RevolutMerchantAdapter:
    """Narrow server-side Revolut Merchant adapter.

    It deliberately receives the API key from an injected secret provider for
    each call, supports sandbox by default and requires an explicit production
    enablement. It returns only the fields needed by checkout and fulfilment.
    """

    def __init__(
        self,
        *,
        secret_provider: SecretProvider,
        environment: str = "sandbox",
        api_version: str = REVOLUT_API_VERSION,
        transport: HttpTransport | None = None,
        timeout_seconds: float = 10.0,
        allow_production: bool = False,
    ) -> None:
        environment = str(environment).strip().lower()
        if environment not in {"sandbox", "production"}:
            raise RevolutMerchantAdapterError("revolut_environment_invalid")
        if environment == "production" and not allow_production:
            raise RevolutMerchantAdapterError("revolut_production_not_enabled")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(api_version)):
            raise RevolutMerchantAdapterError("revolut_api_version_invalid")
        self.origin = (
            REVOLUT_SANDBOX_ORIGIN
            if environment == "sandbox"
            else REVOLUT_PRODUCTION_ORIGIN
        )
        self.environment = environment
        self.api_version = str(api_version)
        self.secret_provider = secret_provider
        self.transport = transport or _default_transport
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 30.0))

    def create_order(
        self,
        *,
        external_reference: str,
        amount_minor: int,
        currency: str,
        redirect_url: str | None = None,
    ) -> RevolutCheckoutOrder:
        reference = self._reference(external_reference)
        amount = int(amount_minor)
        currency = self._currency(currency)
        if amount <= 0:
            raise RevolutMerchantAdapterError("revolut_order_amount_invalid")
        request_payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "merchant_order_data": {"reference": reference},
        }
        if redirect_url is not None:
            self._https_url(redirect_url, "redirect_url")
            request_payload["redirect_url"] = redirect_url
        response = self._request(
            "POST", "/api/orders", request_payload,
            extra_headers={"Idempotency-Key": reference},
            expected_statuses={200, 201},
        )
        normalized = self._normalize_order(response)
        if (
            normalized["external_reference"] != reference
            or normalized["amount_minor"] != amount
            or normalized["currency"] != currency
        ):
            raise RevolutMerchantAdapterError("revolut_created_order_mismatch")
        token = self._bounded(response.get("token"), "token", 512)
        checkout_url = self._https_url(response.get("checkout_url"), "checkout_url")
        return RevolutCheckoutOrder(
            order_id=normalized["id"],
            token=token,
            checkout_url=checkout_url,
            external_reference=reference,
            amount_minor=amount,
            currency=currency,
            state=normalized["state"],
        )

    def retrieve_order(self, order_id: str) -> dict[str, Any]:
        order_id = self._reference(order_id)
        response = self._request(
            "GET", f"/api/orders/{quote(order_id, safe='')}", None,
            expected_statuses={200},
        )
        normalized = self._normalize_order(response)
        if normalized["id"] != order_id:
            raise RevolutMerchantAdapterError("revolut_retrieved_order_mismatch")
        return normalized

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None,
        *,
        expected_statuses: set[int],
        extra_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        secret = str(self.secret_provider() or "")
        if not 12 <= len(secret) <= 4096 or any(ch.isspace() for ch in secret):
            raise RevolutMerchantAdapterError("revolut_secret_unavailable")
        url = self.origin + path
        parsed = urlparse(url)
        if parsed.scheme != "https" or f"{parsed.scheme}://{parsed.netloc}" != self.origin:
            raise RevolutMerchantAdapterError("revolut_origin_invalid")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {secret}",
            "Revolut-Api-Version": self.api_version,
        }
        body = None
        if payload is not None:
            body = json.dumps(
                dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
        status, raw = self.transport(method, url, headers, body, self.timeout_seconds)
        if int(status) not in expected_statuses:
            raise RevolutMerchantAdapterError(f"revolut_merchant_http_error:{int(status)}")
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RevolutMerchantAdapterError("revolut_response_too_large")
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RevolutMerchantAdapterError("revolut_response_invalid") from exc
        if not isinstance(response, dict):
            raise RevolutMerchantAdapterError("revolut_response_invalid")
        return response

    def _normalize_order(self, response: Mapping[str, Any]) -> dict[str, Any]:
        merchant_data = response.get("merchant_order_data") or {}
        if not isinstance(merchant_data, Mapping):
            raise RevolutMerchantAdapterError("revolut_order_shape_invalid")
        updated_at = str(response.get("updated_at") or response.get("created_at") or "")
        if not updated_at or len(updated_at) > 64:
            raise RevolutMerchantAdapterError("revolut_order_shape_invalid")
        amount = int(response.get("amount") or 0)
        if amount <= 0:
            raise RevolutMerchantAdapterError("revolut_order_shape_invalid")
        return {
            "id": self._reference(response.get("id")),
            "external_reference": self._reference(merchant_data.get("reference")),
            "amount_minor": amount,
            "currency": self._currency(response.get("currency")),
            "state": self._bounded(response.get("state"), "state", 32).lower(),
            "updated_at": updated_at,
        }

    @staticmethod
    def _reference(value: Any) -> str:
        result = str(value or "")
        if not SAFE_REFERENCE.fullmatch(result):
            raise RevolutMerchantAdapterError("revolut_reference_invalid")
        return result

    @staticmethod
    def _currency(value: Any) -> str:
        result = str(value or "").upper()
        if len(result) != 3 or not result.isalpha():
            raise RevolutMerchantAdapterError("revolut_currency_invalid")
        return result

    @staticmethod
    def _bounded(value: Any, name: str, maximum: int) -> str:
        result = str(value or "")
        if not result or len(result) > maximum or any(ord(ch) < 32 for ch in result):
            raise RevolutMerchantAdapterError(f"revolut_{name}_invalid")
        return result

    @staticmethod
    def _https_url(value: Any, name: str) -> str:
        result = str(value or "")
        parsed = urlparse(result)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise RevolutMerchantAdapterError(f"revolut_{name}_invalid")
        return result
