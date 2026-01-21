#!/usr/bin/env python3
import base64
import json
import os
import secrets
import sys
from pathlib import Path

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
        return {"frames": 0}
    try:
        return json.loads(p.read_text("utf-8") or "{}") or {"frames": 0}
    except Exception:
        return {"frames": 0}


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
    save_sess(sid, {"frames": 0})
    return {"ok": True, "session_id": sid}


def mode_encode_struct(req: dict) -> dict:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "encode_struct: bad session_id"}

    json_text = str(req.get("json_text") or "")
    data = json_text.encode("utf-8")
    words = pack_u32_words(data)
    packed = encode_template(words)

    st = load_sess(session_id)
    frames = int(st.get("frames") or 0)
    kind = "template" if frames == 0 else "delta"

    st["frames"] = frames + 1
    save_sess(session_id, st)

    return {
        "ok": True,
        "kind": kind,  # <-- v10 relies on this (template once, then delta)
        "bytes_out": len(packed),
        "encoded_b64": base64.b64encode(packed).decode("ascii"),
    }


def mode_decode_struct(req: dict) -> dict:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "decode_struct: bad session_id"}

    encoded_b64 = str(req.get("encoded_b64") or "")
    packed = base64.b64decode(encoded_b64)
    words = decode_template(packed)
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


def main():
    req = json.loads(sys.stdin.read() or "{}")
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