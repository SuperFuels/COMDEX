#!/usr/bin/env python3
import base64
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import encode_template, decode_template  # type: ignore


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


def main():
    req = json.loads(sys.stdin.read() or "{}")
    mode = req.get("mode")

    if mode == "encode":
        payload_text = str(req.get("payload_text") or "")
        data = payload_text.encode("utf-8")
        words = pack_u32_words(data)
        packed = encode_template(words)
        print(
            json.dumps(
                {
                    "ok": True,
                    "encoded_b64": base64.b64encode(packed).decode("ascii"),
                    "raw_len": len(data),
                    "words": len(words),
                }
            )
        )
        return

    if mode == "decode":
        encoded_b64 = str(req.get("encoded_b64") or "")
        packed = base64.b64decode(encoded_b64)
        words = decode_template(packed)
        data = unpack_u32_words(words)
        try:
            txt = data.decode("utf-8")
        except Exception:
            # If someone fed non-utf8, return latin-1-ish safe decode
            txt = data.decode("utf-8", errors="replace")
        print(json.dumps({"ok": True, "decoded_text": txt, "raw_len": len(data), "words": len(words)}))
        return

    print(json.dumps({"ok": False, "error": "bad mode"}))


if __name__ == "__main__":
    main()