#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon-Aware Lexicon Enrichment Tool
------------------------------------
Merges GCIDE + Wiktionary content into existing .wiki.phn capsules, adds
domain tags, symbolic overlays, and dual-signing metadata.

Usage (defaults are in --help):
  python3 wiki_enrich_gcide.py \
      --lexicon-dir /data/knowledge/Lexicon \
      --out-dir /data/knowledge/Lexicon_enriched \
      --gcide-xml /data/sources/gcide.xml \
      --wiktionary-xml /data/sources/enwiktionary-latest-pages-articles.xml \
      --dry-run

Notes:
- Parsers are tolerant and best-effort. They extract common fields even from
  noisy XML/WikiText. You can refine regexes incrementally.
- If a source is missing, enrichment still proceeds with whatever is available.
"""
import argparse
import json
import os
import re
import sys
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

import bz2
import gzip

def open_maybe_compressed(path: Path):
    """
    Transparently open .xml, .gz, or .bz2 files as text streams.
    """
    name = str(path)
    if name.endswith(".bz2"):
        return bz2.open(name, "rt", encoding="utf-8", errors="ignore")
    elif name.endswith(".gz"):
        return gzip.open(name, "rt", encoding="utf-8", errors="ignore")
    else:
        return open(name, "r", encoding="utf-8", errors="ignore")


from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("enrich")

# ------------------------------
# Helpers
# ------------------------------

def filename_to_lemma(p: Path) -> str:
    """
    Turn filenames like 'alpha.wiki.phn' or 'alpha.phn' or 'alpha.ptn'
    into a clean lemma 'alpha', then normalize.
    """
    name = p.name
    # strip the known multi-suffix first
    name = re.sub(r"\.wiki\.phn$", "", name, flags=re.I)
    # strip single suffix fallbacks
    name = re.sub(r"\.(phn|ptn)$", "", name, flags=re.I)
    return normalize_lemma(name)

def sha3_256_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()

def sha3_512_hex(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return path.read_text(encoding="latin-1", errors="replace")

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def normalize_lemma(s: str) -> str:
    """
    Normalize lemma and filenames to lowercase alphanumeric form
    (e.g. 'Photon', 'photon.', 'photon-' → 'photon').
    This ensures proper matching across GCIDE, Wiktionary, and Lexicon.
    """
    return re.sub(r'[^a-z0-9]+', '', s.lower().strip())

# ------------------------------
# Source Parsers (best-effort)
def parse_gcide(gcide_xml: Optional[Path]) -> Dict[str, Dict]:
    """
    GCIDE parser (flat paragraph-style version).
    Handles <p> blocks with <ent>, <hw>, <def>, <qex>, etc.
    Prefers <hw> as the headword; falls back to <ent>.
    Normalizes lemmas and skips non-alpha starts.
    """
    results: Dict[str, Dict] = {}
    if not gcide_xml or not gcide_xml.exists():
        log.warning("GCIDE XML not provided or missing; skipping.")
        return results

    log.info(f"Parsing GCIDE XML: {gcide_xml}")
    try:
        with open(gcide_xml, "r", encoding="utf-8", errors="ignore") as fh:
            current_lemma = None
            defs, exs = [], []

            for raw in fh:
                line = raw.strip()
                if not line:
                    continue

                # Extract inner tag text (not including the tag names)
                m_ent = re.search(r"<ent>(.*?)</ent>", line, re.I)
                m_hw  = re.search(r"<hw>(.*?)</hw>", line, re.I)
                m_def = re.findall(r"<def>(.*?)</def>", line, re.I)
                m_ex  = re.findall(r"<qex>(.*?)</qex>", line, re.I)

                # Start new entry
                if m_ent or m_hw:
                    if current_lemma:
                        results[current_lemma] = {
                            "definitions": list(dict.fromkeys(defs))[:8],
                            "examples": list(dict.fromkeys(exs))[:6],
                            "etymology": None,
                            "pronunciation": None,
                        }

                    head_raw = m_hw[0] if m_hw else m_ent[0]
                    # 🧹 Clean leftover tag artifacts like <hw>foo</hw>
                    head_clean = re.sub(r"<.*?>", "", head_raw).strip()
                    lemma = normalize_lemma(head_clean)
                    if not lemma or not lemma[0].isalpha():
                        current_lemma, defs, exs = None, [], []
                        continue

                    current_lemma = lemma
                    defs, exs = [], []

                if m_def:
                    defs.extend([re.sub(r"<.*?>", "", d).strip() for d in m_def if d.strip()])
                if m_ex:
                    exs.extend([re.sub(r"<.*?>", "", e).strip() for e in m_ex if e.strip()])

            # Flush last one
            if current_lemma and current_lemma not in results:
                results[current_lemma] = {
                    "definitions": list(dict.fromkeys(defs))[:8],
                    "examples": list(dict.fromkeys(exs))[:6],
                    "etymology": None,
                    "pronunciation": None,
                }

    except Exception as e:
        log.exception(f"GCIDE parse error: {e}")

    log.info(f"GCIDE parsed lemmas: {len(results)}")
    return results

def parse_wiktionary(wikt_xml: Optional[Path]) -> Dict[str, Dict]:
    """
    Very tolerant Wiktionary XML parser.
    Skips namespace pages (anything with ':' in title).
    Stores entries under normalize_lemma(title).
    """
    results: Dict[str, Dict] = {}
    if not wikt_xml or not wikt_xml.exists():
        log.warning("Wiktionary XML not provided or missing; skipping.")
        return results

    log.info(f"Parsing Wiktionary XML: {wikt_xml}")
    title, text = None, None

    try:
        with open_maybe_compressed(wikt_xml) as fh:
            for event, elem in ET.iterparse(fh, events=("end",)):
                tag = elem.tag.lower()
                if tag.endswith("title"):
                    title = (elem.text or "").strip()
                elif tag.endswith("text"):
                    text = (elem.text or "")
                elif tag.endswith("page"):
                    if title and text:
                        # skip namespaces like "Wiktionary:...", "Category:..."
                        if ":" in title:
                            title, text = None, None
                            elem.clear()
                            continue
                        lemma = normalize_lemma(title)
                        if not lemma or not lemma[0].isalpha():
                            title, text = None, None
                            elem.clear()
                            continue

                        defs, exs, ety, pron = [], [], None, None
                        ety_match = re.search(r"(?is)===\s*Etymology\s*===\s*(.+?)(?:==|$)", text)
                        if ety_match:
                            ety = re.sub(r"\s+", " ", ety_match.group(1).strip())
                        pron_match = re.search(r"(?is)==\s*Pronunciation\s*==\s*(.+?)(?:==|$)", text)
                        if pron_match:
                            pron = re.sub(r"\s+", " ", pron_match.group(1).strip())

                        for line in text.splitlines():
                            ls = line.strip()
                            if ls.startswith("#*"):
                                exs.append(re.sub(r"[*#]\s*", "", ls))
                            elif ls.startswith("#") and len(ls) > 2:
                                defs.append(re.sub(r"^#\s*", "", ls))

                        bucket = results.setdefault(lemma, {"definitions": [], "examples": [], "etymology": None, "pronunciation": None})
                        bucket["definitions"] += list(dict.fromkeys(defs))[:8]
                        bucket["examples"]    += list(dict.fromkeys(exs))[:6]
                        if ety and not bucket["etymology"]:
                            bucket["etymology"] = ety
                        if pron and not bucket["pronunciation"]:
                            bucket["pronunciation"] = pron

                    title, text = None, None
                    elem.clear()

    except Exception as e:
        log.exception(f"Wiktionary parse error: {e}")

    log.info(f"Wiktionary parsed lemmas: {len(results)}")
    return results

# ------------------------------
# Domain / Field Heuristics
# ------------------------------

DOMAIN_PATTERNS = [
    ("Physics", "Optics", r"\b(photon|wave|resonance|polariz|interference|diffraction|beam|coherence)\b"),
    ("Math", "Algebra", r"\b(group|ring|field|tensor|eigen|matrix|derivative|gradient)\b"),
    ("Biology", "Genetics", r"\b(gene|genome|allele|protein|rna|dna)\b"),
    ("Computing", "Systems", r"\b(kernel|compiler|runtime|protocol|socket|thread|memory)\b"),
]

def detect_domain(defs: List[str], examples: List[str]) -> Tuple[Optional[str], Optional[str]]:
    text = " ".join(defs + examples).lower()
    for domain, field, pat in DOMAIN_PATTERNS:
        if re.search(pat, text, re.I):
            return domain, field
    return None, None

# ------------------------------
# .wiki.phn IO (tolerant)
# ------------------------------

def load_wiki_phn(path: Path) -> Dict[str, str]:
    content = read_text(path)
    lemma = normalize_lemma(path.stem)
    return {"lemma": lemma, "content": content}

def render_enriched_wiki_phn(original: str,
                             lemma: str,
                             merge: Dict,
                             domain: Optional[str],
                             field: Optional[str],
                             overlays: Dict[str, str],
                             signer_list: List[str]) -> str:
    """
    Produce a new .wiki.phn content by appending an ASCII-safe enrichment block.
    We keep the original content intact and add a YAML-ish enrichment footer.
    """
    original_bytes = original.encode("utf-8")
    original_checksum = sha3_256_hex(original_bytes)

    enrichment = {
        "meta": {
            "version": "1.0",
            "enriched_at": now_iso(),
            "signed_by": signer_list,
            "original_checksum": f"SHA3-256:{original_checksum}",
        },
        "lexicon_enrichment": {
            "lemma": lemma,
            "gcide": {
                "definitions": merge.get("gcide", {}).get("definitions") or [],
                "examples": merge.get("gcide", {}).get("examples") or [],
                "etymology": merge.get("gcide", {}).get("etymology"),
                "pronunciation": merge.get("gcide", {}).get("pronunciation"),
            },
            "wiktionary": {
                "definitions": merge.get("wiktionary", {}).get("definitions") or [],
                "examples": merge.get("wiktionary", {}).get("examples") or [],
                "etymology": merge.get("wiktionary", {}).get("etymology"),
                "pronunciation": merge.get("wiktionary", {}).get("pronunciation"),
            },
            "entangled_links": {
                "source": "WordNet",
                "domain": domain,
                "field": field,
            },
            "symbolic_overlays": overlays,
        },
    }

    # Dual-sign checksum_aion across the enrichment JSON (stable)
    enrich_json = json.dumps(enrichment, ensure_ascii=False, sort_keys=True, indent=2)
    checksum_aion = sha3_512_hex(enrich_json.encode("utf-8"))
    # inject
    enrichment["meta"]["checksum_aion"] = f"SHA3-512:{checksum_aion}"

    block = []
    block.append("\n\n# === Tessaris Enrichment Block (ASCII-safe) ===")
    block.append("```enrichment.json")
    block.append(enrich_json)
    block.append("```")
    return original.rstrip() + "\n" + "\n".join(block) + "\n"

# ------------------------------
# Main Pipeline
# ------------------------------

def enrich_lexicon(
    lexicon_dir: Path,
    out_dir: Path,
    gcide_xml: Optional[Path],
    wiktionary_xml: Optional[Path],
    dry_run: bool = False,
    signer_list: Optional[List[str]] = None,
    overlays: Optional[Dict[str, str]] = None
) -> Dict[str, int]:
    signer_list = signer_list or ["Tessaris-Core", "Aion-Node"]
    overlays = overlays or {
        "⊕": "superposition / synthesis",
        "↔": "entanglement / correlation",
        "∇": "collapse / derivation",
        "⟲": "resonance / feedback",
    }

    gcide = parse_gcide(gcide_xml) if gcide_xml else {}
    wikt = parse_wiktionary(wiktionary_xml) if wiktionary_xml else {}

    # 🔍 Debug preview of parsed lemma keys
    log.info(f"Sample GCIDE keys: {list(gcide.keys())[:5]}")
    log.info(f"Sample Wikt keys: {list(wikt.keys())[:5]}")

    in_paths = sorted([p for p in lexicon_dir.rglob("*.wiki.phn") if p.is_file()])
    total = len(in_paths)
    log.info(f"Found {total} capsules")

    counters = {"processed": 0, "enriched": 0, "skipped": 0}
    gcide_hits = 0
    wikt_hits = 0
    sample_matches = []

    for idx, src in enumerate(in_paths, 1):
        rec = load_wiki_phn(src)
        lemma = filename_to_lemma(src)
        original = rec["content"]

        merged: Dict[str, Dict] = {}
        any_add = False

        # GCIDE + Wiktionary merge
        if lemma in gcide:
            merged["gcide"] = gcide[lemma]
            gcide_hits += 1
            any_add = True
        else:
            merged["gcide"] = {}

        if lemma in wikt:
            merged["wiktionary"] = wikt[lemma]
            wikt_hits += 1
            any_add = True
        else:
            merged["wiktionary"] = {}

        # Domain + field inference
        defs_all = (merged["gcide"].get("definitions") or []) + (merged["wiktionary"].get("definitions") or [])
        exs_all = (merged["gcide"].get("examples") or []) + (merged["wiktionary"].get("examples") or [])
        domain, field = detect_domain(defs_all, exs_all)

        if not any_add:
            counters["skipped"] += 1
            continue

        enriched = render_enriched_wiki_phn(
            original=original,
            lemma=lemma,
            merge=merged,
            domain=domain,
            field=field,
            overlays=overlays,
            signer_list=signer_list,
        )

        rel = src.relative_to(lexicon_dir)
        dst = out_dir / rel.parent / (src.stem + ".wiki.enriched.phn")

        if dry_run:
            counters["enriched"] += 1
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            write_text(dst, enriched)
            counters["enriched"] += 1

        counters["processed"] += 1

        # Progress checkpoint
        if idx % 1000 == 0:
            log.info(f"[{idx}/{total}] Enriched so far — {counters['enriched']} saved")

        # Collect examples for early verification
        if any_add and len(sample_matches) < 5:
            sample_matches.append(lemma)

        # Lightweight GC sweep every 500 iterations
        if idx % 500 == 0:
            import gc
            gc.collect()

    log.info(f"✅ GCIDE hits: {gcide_hits} / {total}  |  Wikt hits: {wikt_hits} / {total}")
    if sample_matches:
        log.info(f"Sample filename→lemma matches: {sample_matches}")

    log.info(f"🏁 Enrichment complete — processed={counters['processed']}, enriched={counters['enriched']}, skipped={counters['skipped']}")
    return counters

def main():
    ap = argparse.ArgumentParser(description="Photon-Aware Lexicon Enrichment Tool")
    ap.add_argument("--lexicon-dir", type=Path, required=True, help="Path to existing .wiki.phn capsules")
    ap.add_argument("--out-dir", type=Path, required=True, help="Output directory for enriched capsules")
    ap.add_argument("--gcide-xml", type=Path, default=None, help="Path to GCIDE XML dump")
    ap.add_argument("--wiktionary-xml", type=Path, default=None, help="Path to Wiktionary XML dump")
    ap.add_argument("--dry-run", action="store_true", help="Run without writing files")
    ap.add_argument("--signers", type=str, default="Tessaris-Core,Aion-Node", help="Comma-separated signer names")
    args = ap.parse_args()

    signers = [s.strip() for s in args.signers.split(",") if s.strip()] or ["Tessaris-Core", "Aion-Node"]

    log.info("Starting enrichment...")
    log.info(f"lexicon-dir   = {args.lexicon_dir}")
    log.info(f"out-dir        = {args.out_dir}")
    log.info(f"gcide-xml      = {args.gcide_xml}")
    log.info(f"wiktionary-xml = {args.wiktionary_xml}")

    counters = enrich_lexicon(
        lexicon_dir=args.lexicon_dir,
        out_dir=args.out_dir,
        gcide_xml=args.gcide_xml,
        wiktionary_xml=args.wiktionary_xml,
        dry_run=args.dry_run,
        signer_list=signers,
    )

    log.info(f"Done. {counters}")


if __name__ == "__main__":
    main()
