"""Exact, policy-aware Glyph dictionary transport for repeated context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


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
    """Exact address-to-slot dictionary with Guardian-backed persistence.

    Customer passages are durable only when the customer learning Vault is
    configured.  The path argument remains as a compatibility namespace for
    bounded experiments, but non-Vault operation is deliberately memory-only
    and creates no raw business-data database.
    """

    def __init__(
        self,
        path: Path | None = None,
        *,
        dictionary_id: str = "aion.context.default.v1",
        vault_store: AionLearningVaultStore | None = None,
    ) -> None:
        self.path = path
        self.dictionary_id = dictionary_id
        self.vault_store = vault_store or AionLearningVaultStore()
        namespace = dictionary_id if self.vault_store.enabled else (
            str(path) if path is not None else dictionary_id
        )
        self._state_id = "aion_inference_glyph_context_" + hashlib.sha256(
            f"{dictionary_id}|{namespace}".encode("utf-8")
        ).hexdigest()[:32]
        self._records: dict[int, GlyphContextPassage] = {}
        if self.vault_store.enabled:
            saved = self.vault_store.get_state(self._state_id, {"records": []})
            for item in saved.get("records", []):
                record = GlyphContextPassage(
                    slot=int(item["slot"]),
                    glyph_address=str(item["glyph_address"]),
                    kind=str(item["kind"]),
                    text=str(item["text"]),
                )
                self._records[record.slot] = record

    def _persist(self) -> None:
        if not self.vault_store.enabled:
            return
        self.vault_store.put_state(
            self._state_id,
            {
                "schema_version": "aion.glyph_context.dictionary.v2",
                "dictionary_id": self.dictionary_id,
                "records": [
                    asdict(self._records[slot]) for slot in sorted(self._records)
                ],
            },
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
        for record in self._records.values():
            if record.glyph_address == address:
                return record
        record = GlyphContextPassage(
            slot=max(self._records, default=0) + 1,
            glyph_address=address,
            kind=kind,
            text=clean,
        )
        self._records[record.slot] = record
        self._persist()
        return record

    def known_slots(self) -> set[int]:
        return set(self._records)

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
        pending = dict(self._records)
        for definition in definitions:
            slot = int(definition["slot"])
            address = str(definition["glyph_address"])
            kind = str(definition["kind"])
            text = _normalize(definition["text"])
            if kind not in {"policy", "evidence"} or _address(kind, text) != address:
                raise ValueError("Glyph definition hash or kind is invalid")
            record = GlyphContextPassage(slot, address, kind, text)
            existing = pending.get(slot)
            if existing is not None and existing != record:
                raise ValueError("Glyph slot collision")
            pending[slot] = record
        decoded: list[str] = []
        actual_policy_slots: set[int] = set()
        for raw_slot in raw.get("references", ()):
            slot = int(raw_slot)
            row = pending.get(slot)
            if row is None:
                raise ValueError("packet references an unknown Glyph slot")
            if row.kind == "policy":
                actual_policy_slots.add(slot)
            decoded.append(row.text)
        declared_policy_slots = {int(slot) for slot in raw.get("policy_slots", ())}
        if actual_policy_slots != declared_policy_slots:
            raise ValueError("policy slot declaration does not match decoded context")
        if pending != self._records:
            self._records = pending
            self._persist()
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
