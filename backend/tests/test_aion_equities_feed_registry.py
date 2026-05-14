from __future__ import annotations

from backend.modules.aion_equities.feed_adapter_base import StaticFeedAdapter
from backend.modules.aion_equities.feed_registry import FeedRegistry


def test_register_and_fetch_latest():
    registry = FeedRegistry()
    registry.register(
        StaticFeedAdapter(
            feed_key="FX_EURUSD",
            feed_type="fx",
            value=1.08,
            metadata={"base": "EUR", "quote": "USD"},
        )
    )

    obs = registry.fetch_latest("FX_EURUSD")
    assert obs.feed_key == "FX_EURUSD"
    assert obs.value == 1.08
    assert obs.metadata["base"] == "EUR"


def test_list_feed_keys_sorted():
    registry = FeedRegistry()
    registry.register(StaticFeedAdapter(feed_key="B", feed_type="macro", value=2))
    registry.register(StaticFeedAdapter(feed_key="A", feed_type="fx", value=1))

    assert registry.list_feed_keys() == ["A", "B"]


def test_upsert_replaces_existing_adapter():
    registry = FeedRegistry()
    registry.upsert(StaticFeedAdapter(feed_key="REC_UK_PERM", feed_type="macro", value=48.0))
    registry.upsert(StaticFeedAdapter(feed_key="REC_UK_PERM", feed_type="macro", value=51.0))

    obs = registry.fetch_latest("REC_UK_PERM")
    assert obs.value == 51.0


def test_duplicate_register_raises():
    registry = FeedRegistry()
    registry.register(StaticFeedAdapter(feed_key="GFK_UK", feed_type="macro", value=-18))
    try:
        registry.register(StaticFeedAdapter(feed_key="GFK_UK", feed_type="macro", value=-17))
        assert False, "Expected duplicate register to raise"
    except ValueError as e:
        assert "Feed already registered" in str(e)