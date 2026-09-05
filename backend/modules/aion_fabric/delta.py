from __future__ import annotations

import base64
import json
import zlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .identity import DeviceIdentity


def state_delta(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    changes: Dict[str, Any] = {}
    for key in sorted(previous.keys() | current.keys()):
        if key not in current:
            changes[key] = {"op": "remove"}
        elif key not in previous or previous[key] != current[key]:
            changes[key] = {"op": "set", "value": current[key]}
    return changes


def apply_state_delta(previous: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(previous)
    for key, operation in changes.items():
        if operation.get("op") == "remove":
            result.pop(key, None)
        elif operation.get("op") == "set":
            result[key] = operation.get("value")
        else:
            raise ValueError(f"Unsupported delta operation for {key!r}")
    return result


@dataclass(slots=True)
class DeltaPacket:
    packet_id: str
    node_id: str
    sequence: int
    base_state_hash: str
    result_state_hash: str
    changes: Dict[str, Any]
    created_at: str
    payload_hash: str = ""
    signature: str = ""

    def unsigned_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "node_id": self.node_id,
            "sequence": self.sequence,
            "base_state_hash": self.base_state_hash,
            "result_state_hash": self.result_state_hash,
            "changes": self.changes,
            "created_at": self.created_at,
        }

    def seal(self, identity: DeviceIdentity) -> None:
        self.payload_hash = canonical_hash(self.unsigned_dict())
        self.signature = identity.sign(canonical_bytes(self.unsigned_dict()))

    def verify(self, public_key_b64: str) -> bool:
        return (
            self.payload_hash == canonical_hash(self.unsigned_dict())
            and DeviceIdentity.verify(public_key_b64, canonical_bytes(self.unsigned_dict()), self.signature)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {**self.unsigned_dict(), "payload_hash": self.payload_hash, "signature": self.signature}

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "DeltaPacket":
        return cls(**value)

    def encoded(self) -> bytes:
        """Compact transport form; semantics remain the canonical delta packet."""
        return zlib.compress(canonical_bytes(self.to_dict()), level=9)

    def transport_envelope(self) -> Dict[str, Any]:
        encoded = self.encoded()
        return {
            "codec": "aion-glyph-delta+zlib-v1",
            "packet_id": self.packet_id,
            "payload": base64.b64encode(encoded).decode("ascii"),
            "encoded_bytes": len(encoded),
        }

    @classmethod
    def from_transport_envelope(cls, envelope: Dict[str, Any]) -> "DeltaPacket":
        if envelope.get("codec") != "aion-glyph-delta+zlib-v1":
            raise ValueError("Unsupported AION Fabric delta codec")
        raw = zlib.decompress(base64.b64decode(envelope["payload"]))
        return cls.from_dict(json.loads(raw.decode("utf-8")))


def new_delta_packet(
    *,
    node_id: str,
    sequence: int,
    previous: Dict[str, Any],
    current: Dict[str, Any],
    identity: DeviceIdentity,
) -> DeltaPacket:
    packet = DeltaPacket(
        packet_id=f"delta_{node_id}_{sequence:012d}",
        node_id=node_id,
        sequence=sequence,
        base_state_hash=canonical_hash(previous),
        result_state_hash=canonical_hash(current),
        changes=state_delta(previous, current),
        created_at=utc_now_iso(),
    )
    packet.seal(identity)
    return packet


@dataclass(slots=True)
class GlyphDeltaStream:
    """One signed, compact template+delta stream for constrained nodes.

    Short wire keys are intentional. Meaning is fixed by ``v=1`` and the
    canonical encoder, while the expanded API remains descriptive.
    """

    node_id: str
    stream_id: str
    start_sequence: int
    fields: List[str]
    base: List[List[Any]]
    deltas: List[List[List[Any]]]
    created_at: str
    payload_hash: str = ""
    signature: str = ""

    def compact_dict(self) -> Dict[str, Any]:
        return {
            "v": 1,
            "n": self.node_id,
            "i": self.stream_id,
            "q": self.start_sequence,
            "f": self.fields,
            "b": self.base,
            "d": self.deltas,
            "t": self.created_at,
        }

    def seal(self, identity: DeviceIdentity) -> None:
        payload = canonical_bytes(self.compact_dict())
        self.payload_hash = canonical_hash(self.compact_dict())
        self.signature = identity.sign(payload)

    def verify(self, public_key_b64: str) -> bool:
        payload = canonical_bytes(self.compact_dict())
        return self.payload_hash == canonical_hash(self.compact_dict()) and DeviceIdentity.verify(
            public_key_b64, payload, self.signature
        )

    @property
    def update_count(self) -> int:
        return len(self.deltas)

    @property
    def end_sequence(self) -> int:
        return self.start_sequence + self.update_count - 1

    def states(self) -> List[Dict[str, Any]]:
        state = {self.fields[index]: value for index, value in self.base}
        result = [dict(state)]
        for operations in self.deltas:
            for operation in operations:
                index, opcode = int(operation[0]), int(operation[1])
                key = self.fields[index]
                if opcode == 0:
                    state.pop(key, None)
                elif opcode == 1 and len(operation) == 3:
                    state[key] = operation[2]
                else:
                    raise ValueError("Invalid Glyph delta-stream operation")
            result.append(dict(state))
        return result

    def encoded_payload(self) -> bytes:
        return zlib.compress(canonical_bytes(self.compact_dict()), level=9)

    def transport_envelope(self) -> Dict[str, Any]:
        payload = self.encoded_payload()
        return {
            "codec": "aion-glyph-stream+zlib-v1",
            "payload": base64.b64encode(payload).decode("ascii"),
            "hash": self.payload_hash,
            "sig": self.signature,
        }

    @classmethod
    def from_transport_envelope(cls, envelope: Dict[str, Any]) -> "GlyphDeltaStream":
        if envelope.get("codec") != "aion-glyph-stream+zlib-v1":
            raise ValueError("Unsupported AION Fabric stream codec")
        raw = zlib.decompress(base64.b64decode(envelope["payload"]))
        compact = json.loads(raw.decode("utf-8"))
        if compact.get("v") != 1:
            raise ValueError("Unsupported AION Fabric stream version")
        return cls(
            node_id=compact["n"],
            stream_id=compact["i"],
            start_sequence=int(compact["q"]),
            fields=list(compact["f"]),
            base=list(compact["b"]),
            deltas=list(compact["d"]),
            created_at=compact["t"],
            payload_hash=envelope["hash"],
            signature=envelope["sig"],
        )


def new_glyph_delta_stream(
    *,
    node_id: str,
    start_sequence: int,
    states: Iterable[Dict[str, Any]],
    identity: DeviceIdentity,
) -> GlyphDeltaStream:
    snapshots = [dict(state) for state in states]
    if len(snapshots) < 2:
        raise ValueError("A Glyph delta stream requires a base state and at least one update")
    fields = sorted(set().union(*(state.keys() for state in snapshots)))
    field_index = {field: index for index, field in enumerate(fields)}
    base = [[field_index[key], value] for key, value in sorted(snapshots[0].items())]
    deltas: List[List[List[Any]]] = []
    previous = snapshots[0]
    for current in snapshots[1:]:
        operations: List[List[Any]] = []
        for key in sorted(previous.keys() | current.keys()):
            if key not in current:
                operations.append([field_index[key], 0])
            elif key not in previous or previous[key] != current[key]:
                operations.append([field_index[key], 1, current[key]])
        deltas.append(operations)
        previous = current
    stream = GlyphDeltaStream(
        node_id=node_id,
        stream_id=f"stream_{uuid4().hex}",
        start_sequence=start_sequence,
        fields=fields,
        base=base,
        deltas=deltas,
        created_at=utc_now_iso(),
    )
    stream.seal(identity)
    return stream
