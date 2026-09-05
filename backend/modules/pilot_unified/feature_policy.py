from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MobileFeaturePolicy:
    """Default-deny boundary for dormant economic features in the new app."""

    economic_features_enabled: bool = False

    _blocked_route_fragments = (
        "/api/wallet",
        "/api/photon",
        "/api/mesh/local_send",
        "/wallet/dev",
        "/photon-pay",
    )
    _blocked_capability_prefixes = (
        "pho.",
        "photonpay.",
        "wallet.",
        "token.",
        "bond.",
        "staking.",
        "mint.",
    )
    _economic_intent_terms = frozenset({
        "pho", "photonpay", "photon pay", "tess token", "wrapped glyph",
        "glyph bond", "mint token", "stake token",
    })

    def route_allowed(self, route: str) -> bool:
        if self.economic_features_enabled:
            return True
        normalized = "/" + str(route or "").strip().lower().lstrip("/")
        return not any(fragment in normalized for fragment in self._blocked_route_fragments)

    def capability_allowed(self, capability: str) -> bool:
        if self.economic_features_enabled:
            return True
        normalized = re.sub(r"\s+", "", str(capability or "").lower())
        return not any(normalized.startswith(prefix) for prefix in self._blocked_capability_prefixes)

    def request_allowed(self, request: str) -> bool:
        if self.economic_features_enabled:
            return True
        normalized = " ".join(str(request or "").lower().split())
        return not any(term in normalized for term in self._economic_intent_terms)

    def filter_manifest(self, capabilities: Iterable[str]) -> tuple[str, ...]:
        return tuple(item for item in capabilities if self.capability_allowed(item))

    def require_allowed(self, *, route: str = "", capability: str = "", request: str = "") -> None:
        if route and not self.route_allowed(route):
            raise PermissionError("Dormant economic route is unavailable")
        if capability and not self.capability_allowed(capability):
            raise PermissionError("Dormant economic capability is unavailable")
        if request and not self.request_allowed(request):
            raise PermissionError("Dormant economic request is unavailable")


DEFAULT_MOBILE_FEATURE_POLICY = MobileFeaturePolicy()
