from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.feed_adapter_base import (
    FeedAdapterBase,
    FeedObservation,
)


class FeedRegistry:
    """
    Registry of feed adapters used by trigger maps / live variable tracker.

    Supports both:
      - adapter-based registration for real feed adapters
      - lightweight metadata-only registration for tests / mock feeds

    This keeps the richer adapter design intact while also exposing the
    simpler register_feed / get_feed API expected by the tracker tests.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, FeedAdapterBase] = {}
        self._feed_metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Primary adapter-based API
    # ------------------------------------------------------------------
    def register(self, adapter: FeedAdapterBase) -> FeedAdapterBase:
        feed_key = str(adapter.feed_key).strip()
        if not feed_key:
            raise ValueError("Feed adapter must define a non-empty feed_key")
        if feed_key in self._adapters or feed_key in self._feed_metadata:
            raise ValueError(f"Feed already registered: {feed_key}")

        self._adapters[feed_key] = adapter
        self._feed_metadata[feed_key] = self._build_metadata_from_adapter(adapter)
        return adapter

    def upsert(self, adapter: FeedAdapterBase) -> FeedAdapterBase:
        feed_key = str(adapter.feed_key).strip()
        if not feed_key:
            raise ValueError("Feed adapter must define a non-empty feed_key")

        self._adapters[feed_key] = adapter
        self._feed_metadata[feed_key] = self._build_metadata_from_adapter(adapter)
        return adapter

    def get(self, feed_key: str) -> FeedAdapterBase:
        key = str(feed_key).strip()
        if key not in self._adapters:
            raise KeyError(f"Unknown feed_key: {key}")
        return self._adapters[key]

    def fetch_latest(self, feed_key: str) -> FeedObservation:
        return self.get(feed_key).fetch_latest()

    def fetch_many(self, feed_keys: List[str]) -> Dict[str, FeedObservation]:
        out: Dict[str, FeedObservation] = {}
        for key in feed_keys:
            out[str(key)] = self.fetch_latest(str(key))
        return out

    def describe_feed(self, feed_key: str) -> Dict[str, Any]:
        key = str(feed_key).strip()
        if key in self._adapters:
            return deepcopy(self._adapters[key].describe())
        if key in self._feed_metadata:
            return deepcopy(self._feed_metadata[key])
        raise KeyError(f"Unknown feed_key: {key}")

    def infer_feed_type(self, feed_key: str) -> Optional[str]:
        key = str(feed_key).strip()
        if key in self._adapters:
            return getattr(self._adapters[key], "feed_type", None)
        if key in self._feed_metadata:
            return self._feed_metadata[key].get("source_type")
        return None

    # ------------------------------------------------------------------
    # Lightweight metadata API expected by tests / tracker plumbing
    # ------------------------------------------------------------------
    def register_feed(
        self,
        *,
        feed_id: str,
        source_type: str,
        description: str = "",
        frequency: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        key = str(feed_id).strip()
        if not key:
            raise ValueError("feed_id must be non-empty")
        if key in self._adapters or key in self._feed_metadata:
            raise ValueError(f"Feed already registered: {key}")

        payload = {
            "feed_id": key,
            "feed_key": key,
            "source_type": str(source_type or "").strip(),
            "feed_type": str(source_type or "").strip(),
            "description": str(description or ""),
            "frequency": str(frequency or ""),
            "metadata": deepcopy(metadata or {}),
        }
        self._feed_metadata[key] = payload
        return deepcopy(payload)

    def get_feed(self, feed_id: str) -> Optional[Dict[str, Any]]:
        key = str(feed_id).strip()
        if key in self._feed_metadata:
            return deepcopy(self._feed_metadata[key])
        if key in self._adapters:
            return self._build_metadata_from_adapter(self._adapters[key])
        return None

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def has_feed(self, feed_key: str) -> bool:
        key = str(feed_key).strip()
        return key in self._adapters or key in self._feed_metadata

    def unregister(self, feed_key: str) -> None:
        key = str(feed_key).strip()
        self._adapters.pop(key, None)
        self._feed_metadata.pop(key, None)

    def list_feed_keys(self) -> List[str]:
        keys = set(self._adapters.keys()) | set(self._feed_metadata.keys())
        return sorted(keys)

    def list_feeds(self) -> List[Dict[str, Any]]:
        return [self.describe_feed(k) for k in self.list_feed_keys()]

    def _build_metadata_from_adapter(self, adapter: FeedAdapterBase) -> Dict[str, Any]:
        described = deepcopy(adapter.describe())
        feed_key = str(getattr(adapter, "feed_key", "")).strip()

        return {
            "feed_id": described.get("feed_id", feed_key),
            "feed_key": described.get("feed_key", feed_key),
            "source_type": described.get("source_type", getattr(adapter, "feed_type", "")),
            "feed_type": described.get("feed_type", getattr(adapter, "feed_type", "")),
            "description": described.get("description", ""),
            "frequency": described.get("frequency", ""),
            "metadata": deepcopy(described.get("metadata", {})),
            **{
                k: deepcopy(v)
                for k, v in described.items()
                if k
                not in {
                    "feed_id",
                    "feed_key",
                    "source_type",
                    "feed_type",
                    "description",
                    "frequency",
                    "metadata",
                }
            },
        }


__all__ = ["FeedRegistry"]