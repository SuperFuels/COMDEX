from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class FeedObservation:
    feed_key: str
    observed_at: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedAdapterBase(ABC):
    """
    Minimal base contract for feed adapters.

    Adapters may later wrap:
      - FX feeds
      - macro/economic releases
      - rates / yields
      - commodities
      - sector / company datapoints

    For now the runtime only needs a clean interface and metadata surface.
    """

    def __init__(
        self,
        *,
        feed_key: str,
        feed_type: str,
        provider: str = "internal",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.feed_key = str(feed_key).strip()
        self.feed_type = str(feed_type).strip()
        self.provider = str(provider).strip()
        self.config = dict(config or {})

        if not self.feed_key:
            raise ValueError("feed_key must be non-empty")
        if not self.feed_type:
            raise ValueError("feed_type must be non-empty")

    def describe(self) -> Dict[str, Any]:
        return {
            "feed_key": self.feed_key,
            "feed_type": self.feed_type,
            "provider": self.provider,
            "config": dict(self.config),
            "adapter_class": self.__class__.__name__,
        }

    @abstractmethod
    def fetch_latest(self) -> FeedObservation:
        """
        Return the latest observation for this feed.
        """
        raise NotImplementedError

    def build_observation(
        self,
        *,
        value: Any,
        observed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedObservation:
        return FeedObservation(
            feed_key=self.feed_key,
            observed_at=observed_at or _utc_now_iso(),
            value=value,
            metadata=dict(metadata or {}),
        )


class StaticFeedAdapter(FeedAdapterBase):
    """
    Simple in-memory adapter for tests and bootstrapping.
    """

    def __init__(
        self,
        *,
        feed_key: str,
        feed_type: str,
        value: Any,
        provider: str = "static",
        observed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            feed_key=feed_key,
            feed_type=feed_type,
            provider=provider,
            config=config,
        )
        self._value = value
        self._observed_at = observed_at
        self._metadata = dict(metadata or {})

    def fetch_latest(self) -> FeedObservation:
        return self.build_observation(
            value=self._value,
            observed_at=self._observed_at,
            metadata=self._metadata,
        )


__all__ = [
    "FeedObservation",
    "FeedAdapterBase",
    "StaticFeedAdapter",
]