#!/usr/bin/env python3
import base64
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Ensure repo root is on sys.path
# /COMDEX/.../wirepack_v46.py -> parents[2] == /COMDEX  (adjust if your location differs)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import (  # type: ignore
    encode_template,
    decode_template,
    encode_delta,
    decode_delta,
    apply_delta_inplace,
)

# -----------------------
# u32 word packing (byte-stable, positional)
# -----------------------

def pack_u32_words(data: bytes) -> List[int]:
    """
    word0 = original byte length (u32)
    word1.. = payload bytes packed little-endian 4-per-word, padded with zeros
    """
    n = len(data)
    out: List[int] = [n & 0xFFFFFFFF]
    for i in range(0, n, 4):
        chunk = data[i : i + 4]
        chunk = chunk + b"\x00" * (4 - len(chunk))
        w = chunk[0] | (chunk[1] << 8) | (chunk[2] << 16) | (chunk[3] << 24)
        out.append(w & 0xFFFFFFFF)
    return out


def unpack_u32_words(words: List[int]) -> bytes:
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
# persistent session store (works even if script is run per-request)
# -----------------------

SESS_DIR = Path(__file__).resolve().parent / ".wirepack_v46_sessions"

def _sid_ok(s: str) -> bool:
    return isinstance(s, str) and len(s) >= 16 and all(c in "0123456789abcdef" for c in s)

def _sess_path(session_id: str) -> Path:
    return SESS_DIR / f"{session_id}.json"

def load_sess(session_id: str) -> Dict[str, Any]:
    p = _sess_path(session_id)
    if not p.exists():
        return {"frames": 0}
    try:
        st = json.loads(p.read_text("utf-8") or "{}") or {}
        if "frames" not in st:
            st["frames"] = 0
        return st
    except Exception:
        return {"frames": 0}

def save_sess(session_id: str, st: Dict[str, Any]) -> None:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    p = _sess_path(session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, separators=(",", ":")), "utf-8")
    os.replace(tmp, p)

def new_session_id() -> str:
    return secrets.token_hex(16)


# -----------------------
# canonical JSON (stable keys, no whitespace)
# -----------------------

def canonicalize_json_text(json_text: str) -> str:
    obj = json.loads(json_text or "null")
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# -----------------------
# delta helpers
# -----------------------

Op = Tuple[int, int]  # (index, new_word_u32)

def diff_ops(prev_words: List[int], next_words: List[int]) -> List[Op]:
    n = min(len(prev_words), len(next_words))
    ops: List[Op] = []
    for i in range(n):
        if int(prev_words[i]) != int(next_words[i]):
            ops.append((i, int(next_words[i]) & 0xFFFFFFFF))
    # if length changed, caller should fall back to template
    return ops


# -----------------------
# v46 “HTTP contract” modes
# -----------------------

def mode_session_new() -> Dict[str, Any]:
    sid = new_session_id()
    save_sess(sid, {"frames": 0})
    return {"ok": True, "session_id": sid}

def mode_session_clear(req: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "session_clear: bad session_id"}
    p = _sess_path(session_id)
    try:
        if p.exists():
            p.unlink()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"session_clear: {e}"}

def mode_encode_struct(req: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "encode_struct: bad session_id"}

    json_text = str(req.get("json_text") or "")
    try:
        canon = canonicalize_json_text(json_text)
    except Exception as e:
        return {"ok": False, "error": f"encode_struct: bad json_text: {e}"}

    next_words = pack_u32_words(canon.encode("utf-8"))

    st = load_sess(session_id)
    frames = int(st.get("frames") or 0)
    prev_words_any = st.get("prev_words")

    kind: str
    inner: bytes

    # first frame or incompatible shape -> template
    if frames == 0 or not isinstance(prev_words_any, list) or len(prev_words_any) != len(next_words):
        kind = "template"
        inner = encode_template(next_words)
        st["prev_words"] = next_words
    else:
        prev_words = [int(x) & 0xFFFFFFFF for x in prev_words_any]
        ops = diff_ops(prev_words, next_words)

        # heuristic: if too many changes, send template
        too_many = len(ops) > max(64, int(len(next_words) * 0.45))
        if too_many:
            kind = "template"
            inner = encode_template(next_words)
            st["prev_words"] = next_words
        else:
            kind = "delta"
            inner = encode_delta(ops)
            # keep session state correct using library apply
            apply_delta_inplace(prev_words, inner)
            st["prev_words"] = prev_words

    st["frames"] = frames + 1
    save_sess(session_id, st)

    tag = b"T" if kind == "template" else b"D"
    framed = tag + inner

    return {
        "ok": True,
        "kind": kind,
        "bytes_out": len(framed),
        "encoded_b64": base64.b64encode(framed).decode("ascii"),
    }

def mode_decode_struct(req: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(req.get("session_id") or "")
    if not _sid_ok(session_id):
        return {"ok": False, "error": "decode_struct: bad session_id"}

    encoded_b64 = str(req.get("encoded_b64") or "")
    if not encoded_b64:
        return {"ok": False, "error": "decode_struct: missing encoded_b64"}

    st = load_sess(session_id)
    prev_words_any = st.get("prev_words")
    prev_words: List[int] | None = None
    if isinstance(prev_words_any, list):
        prev_words = [int(x) & 0xFFFFFFFF for x in prev_words_any]

    try:
        framed = base64.b64decode(encoded_b64)
    except Exception as e:
        return {"ok": False, "error": f"decode_struct: bad b64: {e}"}

    if len(framed) < 2:
        return {"ok": False, "error": "decode_struct: bad frame"}

    tag = framed[0:1]
    inner = framed[1:]

    if tag == b"T":
        words = decode_template(inner)
        st["prev_words"] = [int(x) & 0xFFFFFFFF for x in words]
        kind = "template"
    elif tag == b"D":
        if prev_words is None:
            return {"ok": False, "error": "decode_struct: delta without session state"}
        apply_delta_inplace(prev_words, inner)
        st["prev_words"] = prev_words
        kind = "delta"
    else:
        return {"ok": False, "error": "decode_struct: unknown tag"}

    save_sess(session_id, st)

    data = unpack_u32_words([int(x) & 0xFFFFFFFF for x in st["prev_words"]])
    try:
        txt = data.decode("utf-8")
    except Exception:
        txt = data.decode("utf-8", errors="replace")

    return {
        "ok": True,
        "kind": kind,
        "decoded_text": txt,
        "bytes_in": len(framed),
        "raw_len": len(data),
        "words": len(st["prev_words"]),
    }


# -----------------------
# legacy modes
# -----------------------

def mode_encode(req: Dict[str, Any]) -> Dict[str, Any]:
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

def mode_decode(req: Dict[str, Any]) -> Dict[str, Any]:
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
    req = json.loads(sys.stdin.read() or "{}")
    mode = req.get("mode")

    if mode == "session_new":
        out = mode_session_new()
    elif mode == "session_clear":
        out = mode_session_clear(req)
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