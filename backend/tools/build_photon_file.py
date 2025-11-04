#!/usr/bin/env python3
"""
Build a Photon compressed file (.photo) from text or JSONL logs.

Examples:
  # Text -> .photo (auto out path)
  python tools/build_photon_file.py -i notes.txt

  # JSONL -> .photo with session + tag
  python tools/build_photon_file.py -i events.jsonl -o out/demo.photo --session ucs_hub --tag demo

  # Read from stdin (text)
  cat notes.txt | python tools/build_photon_file.py -i - -o notes.photo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from backend.modules.photon.validation import validate_photon_capsule

# ------------------------------------------------------------
# 🌙 Lite-Boot Switch (default: lite mode unless PHOTON_BOOT_MODE=full)
# ------------------------------------------------------------
def activate_lite_mode(force: bool = False) -> None:
    """
    Enables AION/Tessaris lite mode - only glyph compression core.
    """
    if force or os.getenv("PHOTON_BOOT_MODE") == "lite":
        os.environ["AION_LITE"] = "1"

# detect --lite before imports
if any(a in ("--lite", "-l") for a in sys.argv):
    activate_lite_mode(force=True)
elif os.getenv("PHOTON_BOOT_MODE") != "full":
    activate_lite_mode()

# ------------------------------------------------------------
# Import compression tool AFTER lite mode activation
# ------------------------------------------------------------
from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs  # type: ignore


# ------------------------------------------------------------
# IO Helpers
# ------------------------------------------------------------
def read_stdin_text() -> str:
    try:
        return sys.stdin.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read stdin: {e}")

def read_file_text(fp: Path) -> str:
    try:
        return fp.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Failed to read {fp}: {e}")

def write_output(fp: Path, payload: dict) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


# ------------------------------------------------------------
# JSONL normalization → (text, resonance_meta)
# ------------------------------------------------------------
MetricKeys = (
    "ρ", "rho",
    "Ī", "I_bar", "I",
    "SQI", "sqi",
)

def _dig(d: Any, *keys: str) -> Any:
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def extract_text_from_object(obj: Any) -> str:
    """
    Heuristics to get textual content from a JSON event.
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        # common fields
        for path in (
            ("text",),
            ("message",),
            ("msg",),
            ("payload", "text"),
            ("body", "text"),
            ("data", "text"),
        ):
            v = _dig(obj, *path)
            if isinstance(v, str) and v.strip():
                return v
        # fallback to compact JSON
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    # lists / numbers, etc.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def extract_metrics_from_object(obj: Any) -> Dict[str, float]:
    """
    Pulls resonance metrics if present. Returns dict subset.
    """
    out: Dict[str, float] = {}
    if not isinstance(obj, dict):
        return out

    # direct keys
    for k in MetricKeys:
        v = obj.get(k)
        if isinstance(v, (int, float)):
            out[k] = float(v)

    # nested common spots
    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    for k in MetricKeys:
        v = meta.get(k)
        if isinstance(v, (int, float)):
            out.setdefault(k, float(v))

    return out

def accumulate_resonance(metrics_list: List[Dict[str, float]]) -> Dict[str, Any]:
    if not metrics_list:
        return {"n": 0}
    sums: Dict[str, float] = {}
    count = 0
    for m in metrics_list:
        if not m:
            continue
        count += 1
        for k, v in m.items():
            if isinstance(v, (int, float)):
                sums[k] = sums.get(k, 0.0) + float(v)

    def avg(k: str) -> Optional[float]:
        return round(sums[k] / count, 6) if k in sums and count else None

    return {
        "n": count,
        "rho_mean": avg("ρ") or avg("rho"),
        "I_mean":  avg("Ī") or avg("I_bar") or avg("I"),
        "SQI_mean": avg("SQI") or avg("sqi"),
    }

def parse_jsonl(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Converts JSONL into newline-joined text and aggregates resonance meta.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    out_texts: List[str] = []
    metrics: List[Dict[str, float]] = []

    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            # keep raw line if not valid JSON
            out_texts.append(ln)
            continue

        out_texts.append(extract_text_from_object(obj))
        m = extract_metrics_from_object(obj)
        if m:
            metrics.append(m)

    joined = "\n".join([t for t in out_texts if t is not None])
    resonance = accumulate_resonance(metrics)
    return joined, resonance


# ------------------------------------------------------------
# Capsule build
# ------------------------------------------------------------
def sha256_b64(s: str) -> str:
    import base64
    return base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode("utf-8")

def build_capsule_from_text(
    text: str,
    source_file: str,
    *,
    session: Optional[str],
    tag: Optional[str],
    resonance_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a standardized .photon capsule using compress_to_glyphs().
    """
    # compress_to_glyphs may return:
    #   - dict with {glyphs|glyph_stream, semantics, meta, timestamp, hash}
    #   - list of glyph items
    #   - a single glyph/expr string
    glyph_packet: Any = compress_to_glyphs(text)

    # Preview/meta
    preview = text[:240] + ("…" if len(text) > 240 else "")
    length = len(text)

    # Header
    hdr = {
        "ver": 1,
        "ts": int(time.time()),
        "trace": str(uuid.uuid4()),
        "source": source_file,
    }
    if session:
        hdr["session"] = session
    if tag:
        hdr["tag"] = tag

    # Normalize glyphs/stream/semantics/meta across return shapes
    semantics: Optional[Dict[str, Any]] = None
    packet_meta: Dict[str, Any] = {}
    packet_ts: Optional[int] = None
    packet_hash: Optional[str] = None

    if isinstance(glyph_packet, dict):
        if ("operator" in glyph_packet) or ("symbol" in glyph_packet):
            glyphs = [glyph_packet]
        else:
            glyphs = glyph_packet.get("glyphs") or glyph_packet.get("glyph_stream") or []
        glyph_stream = glyph_packet.get("glyph_stream") or glyphs
        semantics = glyph_packet.get("semantics")
        packet_meta = glyph_packet.get("meta") or {}
        packet_ts = glyph_packet.get("timestamp")
        packet_hash = glyph_packet.get("hash")
    elif isinstance(glyph_packet, list):
        glyphs = glyph_packet
        glyph_stream = glyph_packet
    else:
        # string/other → wrap as single item
        glyphs = [glyph_packet]
        glyph_stream = glyphs

    # checksum on glyph_stream textual form (stable-ish)
    checksum_basis = json.dumps(glyph_stream, ensure_ascii=False, separators=(",", ":"))
    checksum = sha256_b64(checksum_basis)

    resonance_meta = {
        "n": 0,
        **(resonance_extra or {}),
    }

    capsule: Dict[str, Any] = {
        "type": "photon_capsule",
        "hdr": hdr,                       # provenance header
        "timestamp": packet_ts or hdr["ts"],
        "glyph_stream": glyph_stream,     # canonical
        "glyphs": glyphs,                 # legacy mirror
        "checksum": checksum,
        "resonance": resonance_meta,      # ρ/Ī/SQI rollups if available
        "source": source_file,
        "meta": {
            **packet_meta,
            "length": length,
            "chars_preview": preview,
        },
    }

    # Only include optional keys if non-null to satisfy strict schema
    if semantics is not None:
        capsule["semantics"] = semantics
    if packet_hash is not None:
        capsule["hash"] = packet_hash

    return capsule

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", required=True, help="Input file path or '-' for stdin")
    p.add_argument("--output", "-o", help="Output .photo path (defaults to <input>.photo)")
    p.add_argument("--format", "-f", choices=["auto", "text", "jsonl"], default="auto",
                   help="Input format (auto-detect by extension if 'auto')")
    p.add_argument("--session", help="Session id to embed in hdr.session", default=None)
    p.add_argument("--tag", help="Optional tag to embed in hdr.tag", default=None)
    p.add_argument("--lite", "-l", action="store_true", help="Force lite mode (already default unless PHOTON_BOOT_MODE=full)")

    args = p.parse_args()

    # Resolve input
    if args.input == "-":
        raw = read_stdin_text()
        input_path_str = "<stdin>"
        ext = ""
    else:
        ip = Path(args.input)
        if not ip.exists():
            raise FileNotFoundError(f"Input file not found: {ip}")
        raw = read_file_text(ip)
        input_path_str = str(ip)
        ext = ip.suffix.lower()

    # Decide output
    if args.output:
        out_path = Path(args.output)
    else:
        if args.input == "-":
            out_path = Path("stdin.photo")
        else:
            out_path = Path(args.input).with_suffix(".photo")

    # Format detect
    fmt = args.format
    if fmt == "auto":
        if ext in (".jsonl", ".ndjson", ".jl"):
            fmt = "jsonl"
        else:
            fmt = "text"

    # Normalize input
    resonance_extra: Dict[str, Any] = {}
    if fmt == "jsonl":
        normalized_text, resonance_extra = parse_jsonl(raw)
    else:
        normalized_text = raw

    # Build capsule
    capsule = build_capsule_from_text(
        normalized_text,
        input_path_str,
        session=args.session,
        tag=args.tag,
        resonance_extra=resonance_extra if resonance_extra else None,
    )

    validate_photon_capsule(capsule)
    # Write
    write_output(out_path, capsule)

    # Summary
    gs = capsule.get("glyph_stream") or capsule.get("glyphs") or []
    print(
        f"✅ Photon capsule written: {out_path}\n"
        f"   glyphs: {len(gs)} | checksum: {capsule.get('checksum')} | "
        f"session: {capsule['hdr'].get('session','-')} | tag: {capsule['hdr'].get('tag','-')}"
    )


if __name__ == "__main__":
    main()