"""Exact, policy-aware Glyph dictionary transport for repeated context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping, Sequence


POLICY_PATTERN = re.compile(
    r"\b(must|mustn't|must not|required|prohibited|authorised|authorized|do not|don't|never|policy|approval|consent)\b",
    re.I,
)


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _normalize(text: str) -> str:
    return " ".join(str(text).split())


def _address(kind: str, text: str) -> str:
    digest = hashlib.sha256(_canonical({"kind": kind, "text": text})).hexdigest()
    return f"glyph:sha256:{digest}"


@dataclass(frozen=True)
class GlyphContextPassage:
    slot: int
    glyph_address: str
    kind: str
    text: str


@dataclass(frozen=True)
class GlyphContextPacket:
    schema_version: str
    dictionary_id: str
    definitions: tuple[GlyphContextPassage, ...]
    references: tuple[int, ...]
    policy_slots: tuple[int, ...]
    original_utf8_bytes: int
    encoded_utf8_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GlyphContextDictionary:
    """Persistent address-to-small-slot dictionary with exact reconstruction."""

    def __init__(self, path: Path, *, dictionary_id: str = "aion.context.default.v1") -> None:
        self.path = path
        self.dictionary_id = dictionary_id
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS glyph_context_dictionary (
                    slot INTEGER PRIMARY KEY AUTOINCREMENT,
                    glyph_address TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    text_value TEXT NOT NULL
                )"""
            )

    @staticmethod
    def classify(text: str) -> str:
        return "policy" if POLICY_PATTERN.search(text) else "evidence"

    def _ensure(self, text: str) -> GlyphContextPassage:
        clean = _normalize(text)
        if not clean:
            raise ValueError("context passages must not be empty")
        kind = self.classify(clean)
        address = _address(kind, clean)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO glyph_context_dictionary(glyph_address,kind,text_value) VALUES(?,?,?)",
                (address, kind, clean),
            )
            row = connection.execute(
                "SELECT slot,glyph_address,kind,text_value FROM glyph_context_dictionary WHERE glyph_address=?",
                (address,),
            ).fetchone()
        return GlyphContextPassage(int(row[0]), str(row[1]), str(row[2]), str(row[3]))

    def known_slots(self) -> set[int]:
        with sqlite3.connect(self.path) as connection:
            return {int(row[0]) for row in connection.execute("SELECT slot FROM glyph_context_dictionary")}

    def encode(
        self,
        passages: Iterable[str],
        *,
        receiver_known_slots: Iterable[int] = (),
    ) -> GlyphContextPacket:
        normalized = tuple(_normalize(passage) for passage in passages if _normalize(passage))
        records = tuple(self._ensure(passage) for passage in normalized)
        known = {int(slot) for slot in receiver_known_slots}
        definitions = tuple(record for record in records if record.slot not in known)
        provisional = {
            "schema_version": "aion.glyph_context.packet.v1",
            "dictionary_id": self.dictionary_id,
            "definitions": [asdict(item) for item in definitions],
            "references": [item.slot for item in records],
            "policy_slots": [item.slot for item in records if item.kind == "policy"],
        }
        wire = {
            "v": 1,
            "d": self.dictionary_id,
            "n": [[item.slot, item.glyph_address, item.kind, item.text] for item in definitions],
            "r": provisional["references"],
            "p": provisional["policy_slots"],
        }
        return GlyphContextPacket(
            schema_version=provisional["schema_version"],
            dictionary_id=self.dictionary_id,
            definitions=definitions,
            references=tuple(provisional["references"]),
            policy_slots=tuple(provisional["policy_slots"]),
            original_utf8_bytes=len(_canonical(list(normalized))),
            encoded_utf8_bytes=len(_canonical(wire)),
        )

    def decode(self, packet: GlyphContextPacket | Mapping[str, Any]) -> tuple[str, ...]:
        raw = packet.to_dict() if isinstance(packet, GlyphContextPacket) else dict(packet)
        if raw.get("schema_version") != "aion.glyph_context.packet.v1":
            raise ValueError("unsupported Glyph context packet schema")
        if raw.get("dictionary_id") != self.dictionary_id:
            raise ValueError("Glyph context dictionary identity mismatch")
        definitions = raw.get("definitions", ())
        with sqlite3.connect(self.path) as connection:
            for definition in definitions:
                slot = int(definition["slot"])
                address = str(definition["glyph_address"])
                kind = str(definition["kind"])
                text = _normalize(definition["text"])
                if kind not in {"policy", "evidence"} or _address(kind, text) != address:
                    raise ValueError("Glyph definition hash or kind is invalid")
                existing = connection.execute(
                    "SELECT glyph_address,kind,text_value FROM glyph_context_dictionary WHERE slot=?",
                    (slot,),
                ).fetchone()
                if existing is not None and tuple(existing) != (address, kind, text):
                    raise ValueError("Glyph slot collision")
                connection.execute(
                    "INSERT OR IGNORE INTO glyph_context_dictionary(slot,glyph_address,kind,text_value) VALUES(?,?,?,?)",
                    (slot, address, kind, text),
                )
            decoded: list[str] = []
            actual_policy_slots: set[int] = set()
            for raw_slot in raw.get("references", ()):
                slot = int(raw_slot)
                row = connection.execute(
                    "SELECT kind,text_value FROM glyph_context_dictionary WHERE slot=?",
                    (slot,),
                ).fetchone()
                if row is None:
                    raise ValueError("packet references an unknown Glyph slot")
                if row[0] == "policy":
                    actual_policy_slots.add(slot)
                decoded.append(str(row[1]))
        declared_policy_slots = {int(slot) for slot in raw.get("policy_slots", ())}
        if actual_policy_slots != declared_policy_slots:
            raise ValueError("policy slot declaration does not match decoded context")
        return tuple(decoded)

    @staticmethod
    def transmission_summary(packets: Sequence[GlyphContextPacket]) -> Mapping[str, Any]:
        original = sum(packet.original_utf8_bytes for packet in packets)
        encoded = sum(packet.encoded_utf8_bytes for packet in packets)
        return {
            "schema_version": "aion.glyph_context.transmission_summary.v1",
            "packet_count": len(packets),
            "original_utf8_bytes": original,
            "encoded_utf8_bytes": encoded,
            "compression_percent": (1.0 - encoded / original) * 100 if original else 0.0,
            "policy_reference_count": sum(len(packet.policy_slots) for packet in packets),
            "definition_count": sum(len(packet.definitions) for packet in packets),
            "exact_reconstruction_required": True,
        }
