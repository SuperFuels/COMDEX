from __future__ import annotations

import struct
from typing import Iterable, List, Tuple

Op = Tuple[int, int]  # (idx, new_value)

# -------------------------
# uvarint helpers (deterministic)
# -------------------------
def _uvarint_encode(x: int) -> bytes:
    if x < 0:
        raise ValueError("uvarint cannot encode negative")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)

def _uvarint_decode(buf: bytes, i: int) -> tuple[int, int]:
    shift = 0
    x = 0
    while True:
        if i >= len(buf):
            raise ValueError("truncated uvarint")
        b = buf[i]
        i += 1
        x |= (b & 0x7F) << shift
        if not (b & 0x80):
            return x, i
        shift += 7
        if shift > 63:
            raise ValueError("uvarint too large")

# -------------------------
# WirePack v1
# -------------------------
def encode_template(base_state: List[int]) -> bytes:
    out = bytearray()
    out += _uvarint_encode(len(base_state))
    for v in base_state:
        # uint32 little-endian (your bench values are 0..100000)
        out += struct.pack("<I", int(v) & 0xFFFFFFFF)
    return bytes(out)

def decode_template(b: bytes) -> List[int]:
    n, i = _uvarint_decode(b, 0)
    need = i + 4 * n
    if need > len(b):
        raise ValueError("truncated template body")
    vals = list(struct.unpack_from(f"<{n}I", b, i))
    return [int(x) for x in vals]

def encode_delta(ops: Iterable[Op]) -> bytes:
    ops_list = list(ops)
    out = bytearray()
    out += _uvarint_encode(len(ops_list))
    for idx, newv in ops_list:
        if idx < 0:
            raise ValueError("idx must be >= 0")
        out += _uvarint_encode(int(idx))
        out += struct.pack("<I", int(newv) & 0xFFFFFFFF)
    return bytes(out)

def decode_delta(b: bytes) -> List[Op]:
    m, i = _uvarint_decode(b, 0)
    ops: List[Op] = []
    for _ in range(m):
        idx, i = _uvarint_decode(b, i)
        if i + 4 > len(b):
            raise ValueError("truncated delta value")
        (newv,) = struct.unpack_from("<I", b, i)
        i += 4
        ops.append((int(idx), int(newv)))
    return ops

def canonicalize_delta(delta_bytes: bytes) -> bytes:
    ops = decode_delta(delta_bytes)
    ops.sort(key=lambda t: (t[0], t[1]))  # idx asc, value asc
    return encode_delta(ops)

def apply_delta_inplace(state: List[int], delta_bytes: bytes) -> None:
    for idx, newv in decode_delta(delta_bytes):
        state[idx] = newv

def encode_delta_stream(deltas: List[bytes]) -> bytes:
    """
    Deterministic framing: [K][len(d1)][d1]...[len(dK)][dK]
    """
    out = bytearray()
    out += _uvarint_encode(len(deltas))
    for d in deltas:
        out += _uvarint_encode(len(d))
        out += d
    return bytes(out)