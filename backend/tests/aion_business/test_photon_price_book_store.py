from __future__ import annotations

import hashlib
import os
import sqlite3

import pytest

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonPriceBook,
    sign_price_book,
)
from backend.modules.aion_business.runtime.photon_price_book_store import PhotonPriceBookStore


class Signer:
    public_key_b64 = "founder-pricing-key"

    def sign(self, payload):
        return hashlib.sha256(payload).hexdigest()


def verify(key, payload, signature):
    return key == "founder-pricing-key" and hashlib.sha256(payload).hexdigest() == signature


def book(version="v1", effective="2026-11-01T00:00:00+00:00", price=1000):
    return PhotonPriceBook(
        version=version, currency="GBP", minor_units_per_1000_photons=price,
        action_rates={"quote.prepared": 25}, effective_at=effective,
        region="GB", cohort="pilot", reason="pilot_calibration",
    )


def publish(store, value=None, preview_hash=None, **overrides):
    value = value or book()
    envelope = sign_price_book(value, Signer())
    return store.publish(
        envelope,
        approved_preview_hash=preview_hash or value.preview()["price_book_hash"],
        actor_id="founder-1", published_at="2026-10-17T20:00:00+00:00",
        reauthenticated=True, confirmation="PUBLISH PHOTON PRICE BOOK",
        verifier=verify, **overrides,
    )


def test_preview_and_reauthentication_are_required(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "pricing.sqlite3")
    value = book()
    envelope = sign_price_book(value, Signer())
    with pytest.raises(PermissionError, match="reauthentication_required"):
        store.publish(
            envelope, approved_preview_hash=value.preview()["price_book_hash"],
            actor_id="founder-1", published_at="2026-10-17T20:00:00+00:00",
            reauthenticated=False, confirmation="PUBLISH PHOTON PRICE BOOK", verifier=verify,
        )
    with pytest.raises(PermissionError, match="preview_mismatch"):
        publish(store, value, preview_hash="wrong")


def test_published_book_is_immutable_and_activates_only_when_effective(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "pricing.sqlite3")
    published = publish(store)
    assert store.get("v1") == published
    with pytest.raises(KeyError, match="applicable"):
        store.applicable(currency="GBP", region="GB", cohort="pilot", as_of="2026-10-31T23:59:59+00:00")
    assert store.applicable(
        currency="GBP", region="GB", cohort="pilot", as_of="2026-11-01T00:00:00+00:00"
    )["version"] == "v1"
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="photon_price_book_immutable"):
            connection.execute("UPDATE photon_price_books SET currency = 'EUR' WHERE version = 'v1'")


def test_new_price_does_not_rewrite_previous_version(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "pricing.sqlite3")
    first = publish(store)
    second_book = book(version="v2", effective="2026-12-01T00:00:00+00:00", price=3000)
    second = publish(store, second_book)
    assert first["payload"]["minor_units_per_1000_photons"] == 1000
    assert second["payload"]["minor_units_per_1000_photons"] == 3000
    assert store.get("v1")["payload"]["minor_units_per_1000_photons"] == 1000


def test_retroactive_effective_date_and_version_reuse_are_rejected(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "pricing.sqlite3")
    with pytest.raises(ValueError, match="effective_date_not_future"):
        publish(store, book(effective="2026-10-17T19:59:59+00:00"))
    publish(store)
    with pytest.raises(ValueError, match="version_reused"):
        publish(store, book(price=3000))


def test_future_cancellation_is_append_only_and_excluded_from_selection(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "pricing.sqlite3")
    publish(store)
    cancellation = store.cancel(
        "v1",
        actor_id="founder-1",
        cancelled_at="2026-10-20T00:00:00+00:00",
        reason="Withdraw scheduled calibration",
        reauthenticated=True,
        confirmation="CANCEL PHOTON PRICE BOOK",
    )
    assert store.cancel(
        "v1",
        actor_id="founder-1",
        cancelled_at="2026-10-20T00:00:00+00:00",
        reason="Withdraw scheduled calibration",
        reauthenticated=True,
        confirmation="CANCEL PHOTON PRICE BOOK",
    ) == cancellation
    assert store.scheduled(
        currency="GBP", region="GB", cohort="pilot",
        as_of="2026-10-21T00:00:00+00:00",
    ) == []
    with pytest.raises(KeyError, match="applicable"):
        store.applicable(
            currency="GBP", region="GB", cohort="pilot",
            as_of="2026-11-02T00:00:00+00:00",
        )
    assert store.get("v1")["version"] == "v1"
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="cancellation_immutable"):
            connection.execute(
                "UPDATE photon_price_book_cancellations SET reason = 'changed' WHERE version = 'v1'"
            )


def test_price_store_is_private_refuses_symlink_and_detects_payload_tamper(tmp_path):
    store = PhotonPriceBookStore(tmp_path / "private" / "pricing.sqlite3")
    publish(store)
    assert os.stat(store.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-pricing.sqlite3"
    link.symlink_to(store.path)
    with pytest.raises(ValueError, match="symlink_database_forbidden"):
        PhotonPriceBookStore(link)
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TRIGGER photon_price_books_no_update")
        connection.execute(
            "UPDATE photon_price_books SET payload_json = '{}' WHERE version = 'v1'"
        )
    with pytest.raises(ValueError, match="payload_hash_mismatch"):
        store.get("v1")
