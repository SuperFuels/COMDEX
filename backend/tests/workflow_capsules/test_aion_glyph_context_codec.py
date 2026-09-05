from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from backend.modules.aion_inference.glyph_context import GlyphContextDictionary


PASSAGES = (
    "Policy: every quotation must receive human approval.",
    "Do not take payment without a second confirmation.",
    "Customer asked for a patio quotation and supplied dimensions.",
)


def test_first_packet_defines_glyphs_and_receiver_reconstructs_exact_context(tmp_path):
    sender = GlyphContextDictionary(tmp_path / "sender.sqlite3")
    receiver = GlyphContextDictionary(tmp_path / "receiver.sqlite3")
    packet = sender.encode(PASSAGES)
    assert len(packet.definitions) == 3
    assert receiver.decode(packet) == PASSAGES
    assert len(packet.policy_slots) == 2


def test_repeated_context_uses_only_small_slot_references(tmp_path):
    sender = GlyphContextDictionary(tmp_path / "sender.sqlite3")
    receiver = GlyphContextDictionary(tmp_path / "receiver.sqlite3")
    first = sender.encode(PASSAGES)
    assert receiver.decode(first) == PASSAGES
    subsequent = [sender.encode(PASSAGES, receiver_known_slots=receiver.known_slots()) for _ in range(50)]
    assert all(not packet.definitions for packet in subsequent)
    assert all(receiver.decode(packet) == PASSAGES for packet in subsequent)
    summary = sender.transmission_summary([first, *subsequent])
    assert summary["compression_percent"] > 50
    assert summary["policy_reference_count"] == 102


def test_tampered_definition_is_rejected_before_storage(tmp_path):
    sender = GlyphContextDictionary(tmp_path / "sender.sqlite3")
    receiver = GlyphContextDictionary(tmp_path / "receiver.sqlite3")
    packet = sender.encode(PASSAGES)
    broken_definition = replace(packet.definitions[0], text="Policy: approval is optional.")
    broken = replace(packet, definitions=(broken_definition, *packet.definitions[1:]))
    with pytest.raises(ValueError, match="hash or kind"):
        receiver.decode(broken)


def test_missing_policy_declaration_is_rejected(tmp_path):
    sender = GlyphContextDictionary(tmp_path / "sender.sqlite3")
    receiver = GlyphContextDictionary(tmp_path / "receiver.sqlite3")
    packet = sender.encode(PASSAGES)
    raw = asdict(packet)
    raw["policy_slots"] = []
    with pytest.raises(ValueError, match="policy slot"):
        receiver.decode(raw)


def test_unknown_reference_and_dictionary_mismatch_fail_closed(tmp_path):
    sender = GlyphContextDictionary(tmp_path / "sender.sqlite3")
    receiver = GlyphContextDictionary(tmp_path / "receiver.sqlite3")
    packet = sender.encode(PASSAGES)
    raw = asdict(packet)
    raw["definitions"] = []
    with pytest.raises(ValueError, match="unknown Glyph slot"):
        receiver.decode(raw)
    other = GlyphContextDictionary(tmp_path / "other.sqlite3", dictionary_id="other.v1")
    with pytest.raises(ValueError, match="identity mismatch"):
        other.decode(packet)
