#!/usr/bin/env python3
"""
wirepack_v46.py — Streaming transport demo backend shim

Fixes the original bug where "delta" frames were still encoded as full templates.

Contract (stdin JSON):
  { "mode": "session_new" } -> { ok, session_id }
  { "mode": "encode_struct", "session_id": "...", "json_text": "..." }
  { "mode": "decode_struct", "session_id": "...", "encoded_b64": "..." }

Legacy compatibility:
  { "mode": "encode", "payload_text": "..." }
  { "mode": "decode", "encoded_b64": "..." }

Encoding formats:
  - Template frame: backend.modules.glyphos.wirepack_codec.encode_template(words)
  - Delta frame: custom "WPD46" patch against stored template_words in session.
    (delta packets are NOT passed through wirepack_codec; they are already compact)
"""

import base64
import json
import os
import secrets
import struct
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path
# /COMDEX/Glyph_Net_Browser/radio-node/wirepack_v46.py -> parents[2] == /COMDEX
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import encode_template, decode_template  # type: ignore

# -----------------------
# u32 word packing (unchanged)
# -----------------------


def pack_u32_words(data: bytes) -> list[int]:
    # Layout:
    #   word0 = original byte length (u32)
    #   word1.. = payload bytes packed little-endian 4-per-word, padded with zeros
    n = len(data)
    out = [n & 0xFFFFFFFF]
    for i in range(0, n, 4):
        chunk = data[i : i + 4]
        chunk = chunk + b"\x00" * (4 - len(chunk))
        w = chunk[0] | (chunk[1] << 8) | (chunk[2] << 16) | (chunk[3] << 24)
        out.append(w & 0xFFFFFFFF)
    return out


def unpack_u32_words(words: list[int]) -> bytes:
    if not words:
        return b""
    n = int(words[0]) & 0xFFFFFFFF
    raw = bytearray()
    for w in words[1:]:
        w = int(w) & 0xFFFFFFFF
        raw.append(w & 0xFF)
        raw.append((w >> 8) & 0xFF)
        raw.append((w >> 16) & 0xFF)
        raw.append((w >> 24) & 0xFF)
    return bytes(raw[:n])


# -----------------------
# v46 delta codec (template-once + patch thereafter)
# -----------------------

MAGIC = b"WPD46"  # 5 bytes
VER = 1  # 1 byte


def _uvarint_enc(x: int) -> bytes:
    x = int(x)
    if x < 0:
        raise ValueError("uvarint expects non-negative")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(0x80 | b)
        else:
            out.append(b)
            break
    return bytes(out)


def _uvarint_dec(buf: bytes, i: int) -> tuple[int, int]:
    shift = 0
    x = 0
    while True:
        if i >= len(buf):
            raise ValueError("uvarint eof")
        b = buf[i]
        i += 1
        x |= (b & 0x7F) << shift
        if not (b & 0x80):
            return x, i
        shift += 7
        if shift > 63:
            raise ValueError("uvarint too long")


def _delta_make(base_words: list[int], cur_words: list[int]) -> bytes:
    """
    Produce a compact patch that can reconstruct cur_words from base_words.

    Format:
      MAGIC (5) + VER (1)
      n_total uvarint
      n_updates uvarint
      repeated:
        idx uvarint
        word u32 little-endian
    """
    n_total = max(len(base_words), len(cur_words))
    updates: list[tuple[int, int]] = []

    for idx in range(n_total):
        bw = base_words[idx] if idx < len(base_words) else 0
        cw = cur_words[idx] if idx < len(cur_words) else 0
        bw &= 0xFFFFFFFF
        cw &= 0xFFFFFFFF
        if bw != cw:
            updates.append((idx, cw))

    out = bytearray()
    out += MAGIC
    out.append(VER)
    out += _uvarint_enc(n_total)
    out += _uvarint_enc(len(updates))
    for idx, w in updates:
        out += _uvarint_enc(idx)
        out += struct.pack("<I", int(w) & 0xFFFFFFFF)
    return bytes(out)


def _delta_apply(base_words: list[int], packed: bytes) -> list[int]:
    if not packed.startswith(MAGIC):
        raise ValueError("not a v46 delta packet")
    i = len(MAGIC)
    if i >= len(packed):
        raise ValueError("delta header eof")
    ver = packed[i]
    i += 1
    if ver != VER:
        raise ValueError(f"delta ver mismatch {ver} != {VER}")

    n_total, i = _uvarint_dec(packed, i)
    n_upd, i = _uvarint_dec(packed, i)

    # start from base (or 0-padded)
    out = list(base_words[:n_total])
    if len(out) < n_total:
        out.extend([0] * (n_total - len(out)))

    for _ in range(n_upd):
        idx, i = _uvarint_dec(packed, i)
        if i + 4 > len(packed):
            raise ValueError("delta word eof")
        w = struct.unpack("<I", packed[i : i + 4])[0]
        i += 4
        if 0 <= idx < n_total:
            out[idx] = int(w) & 0xFFFFFFFF

    return out


# -----------------------
# simple persistent session store (works even if this script is run per-request)
# -----------------------

SESS_DIR = Path(__file__).resolve().parent / ".wirepack_v46_sessions"


def _sid_ok(s: str) -> bool:
    # keep it very simple: hex token
    return isinstance(s, str) and len(s) >= 16 and all(c in "0123456789abcdef" for c in s)


def _sess_path(session_id: str) -> Path:
    return SESS_DIR / f"{session_id}.json"


def load_sess(session_id: str) -> dict:
    p = _sess_path(session_id)
    if not p.exists():
        return {"frames": 0, "template_words": None}
    try:
        st = json.loads(p.read_text("utf-8") or "{}") or {}
        if "frames" not in st:
            st["frames"] = 0
        if "template_words" not in st:
            st["template_words"] = None
        return st
    except Exception:
        return {"frames": 0, "template_words": None}


def save_sess(session_id: str, st: dict) -> None:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    p = _sess_path(session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, separators=(",", ":")), "utf-8")
    os.replace(tmp, p)


def new_session_id() -> str:
    # 32 hex chars
    return secrets.token_hex(16)


# -----------------------
# v46 “HTTP contract” modes
# -----------------------


def mode_session_new() -> dict:
    sid = new_session_id()
    save_sess(sid, {"frames": 0, "template_words": None})
    return {"ok": True, "session_id": sid}


def mode_encode_struct(req: dict) -> dict:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "encode_struct: bad session_id"}

    json_text = str(req.get("json_text") or "")
    data = json_text.encode("utf-8")
    words = pack_u32_words(data)

    st = load_sess(session_id)
    frames = int(st.get("frames") or 0)
    base_words = st.get("template_words")

    # First frame (or missing base): emit real template + store base words
    if frames == 0 or not isinstance(base_words, list) or len(base_words) == 0:
        packed = encode_template(words)
        st["frames"] = frames + 1
        st["template_words"] = words
        save_sess(session_id, st)
        return {
            "ok": True,
            "kind": "template",
            "bytes_out": len(packed),
            "encoded_b64": base64.b64encode(packed).decode("ascii"),
        }

    # Subsequent frames: emit compact delta against stored base words
    packed = _delta_make(base_words, words)
    st["frames"] = frames + 1
    save_sess(session_id, st)

    return {
        "ok": True,
        "kind": "delta",
        "bytes_out": len(packed),
        "encoded_b64": base64.b64encode(packed).decode("ascii"),
    }


def mode_decode_struct(req: dict) -> dict:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "decode_struct: bad session_id"}

    encoded_b64 = str(req.get("encoded_b64") or "")
    try:
        packed = base64.b64decode(encoded_b64)
    except Exception:
        return {"ok": False, "error": "decode_struct: invalid base64"}

    st = load_sess(session_id)

    try:
        if packed.startswith(MAGIC):
            base_words = st.get("template_words")
            if not isinstance(base_words, list) or len(base_words) == 0:
                return {"ok": False, "error": "decode_struct: missing template in session"}
            words = _delta_apply(base_words, packed)
        else:
            words = decode_template(packed)
    except Exception as e:
        return {"ok": False, "error": f"decode_struct: {e}"}

    data = unpack_u32_words(words)
    try:
        txt = data.decode("utf-8")
    except Exception:
        txt = data.decode("utf-8", errors="replace")

    return {
        "ok": True,
        "kind": "struct",
        "decoded_text": txt,
        "bytes_in": len(packed),
        "raw_len": len(data),
        "words": len(words),
    }


# -----------------------
# legacy modes (keep compatibility with your old usage)
# -----------------------


def mode_encode(req: dict) -> dict:
    payload_text = str(req.get("payload_text") or "")
    data = payload_text.encode("utf-8")
    words = pack_u32_words(data)
    packed = encode_template(words)
    return {
        "ok": True,
        "encoded_b64": base64.b64encode(packed).decode("ascii"),
        "raw_len": len(data),
        "words": len(words),
        "bytes_out": len(packed),
        "kind": "template",
    }


def mode_decode(req: dict) -> dict:
    encoded_b64 = str(req.get("encoded_b64") or "")
    packed = base64.b64decode(encoded_b64)
    words = decode_template(packed)
    data = unpack_u32_words(words)
    try:
        txt = data.decode("utf-8")
    except Exception:
        txt = data.decode("utf-8", errors="replace")
    return {"ok": True, "decoded_text": txt, "raw_len": len(data), "words": len(words), "bytes_in": len(packed)}


def main() -> None:
    try:
        req: dict[str, Any] = json.loads(sys.stdin.read() or "{}")
    except Exception:
        req = {}
    mode = req.get("mode")

    if mode == "session_new":
        out = mode_session_new()
    elif mode == "encode_struct":
        out = mode_encode_struct(req)
    elif mode == "decode_struct":
        out = mode_decode_struct(req)
    elif mode == "encode":
        out = mode_encode(req)
    elif mode == "decode":
        out = mode_decode(req)
    else:
        out = {"ok": False, "error": "bad mode"}

    print(json.dumps(out))


if __name__ == "__main__":
    main()