# Photon-Aware Lexicon Enrichment

This tool merges GCIDE + Wiktionary into existing `.wiki.phn` capsules, adds domain tags,
symbolic overlays, and dual-signing metadata.

## Files Created
- `backend/modules/knowledge_graph/wiki_enrich_gcide.py` — the enrichment script
- `backend/modules/knowledge_graph/enrich_config.json` — optional config stub

## Quick Start

1) Put your sources in known paths, e.g.
```
/data/knowledge/Lexicon/                  # existing .wiki.phn capsules
/data/sources/gcide.xml                   # GCIDE XML dump
/data/sources/enwiktionary-pages.xml      # Wiktionary XML (pages-articles)
```

2) Dry run:
```bash
python3 wiki_enrich_gcide.py   --lexicon-dir /data/knowledge/Lexicon   --out-dir /data/knowledge/Lexicon_enriched   --gcide-xml /data/sources/gcide.xml   --wiktionary-xml /data/sources/enwiktionary-pages.xml   --dry-run
```

3) Execute (write enriched files):
```bash
python3 wiki_enrich_gcide.py   --lexicon-dir /data/knowledge/Lexicon   --out-dir /data/knowledge/Lexicon_enriched   --gcide-xml /data/sources/gcide.xml   --wiktionary-xml /data/sources/enwiktionary-pages.xml
```

## Output Format

The original `.wiki.phn` content is preserved. An ASCII-safe enrichment JSON block is appended:

```
# === Tessaris Enrichment Block (ASCII-safe) ===
```enrichment.json
{ ... merged data, overlays, entangled_links, checksums ... }
```
```

This ensures Photon executors that ignore fenced blocks keep working, while enrichment-aware tools can parse the JSON.

## Notes
- Parsers are best-effort and conservative to avoid breaking on noisy dumps.
- Domain/field detection uses keyword heuristics; refine `DOMAIN_PATTERNS` as needed.
- Dual signing is represented with `signed_by` and `checksum_aion` (SHA3-512 over the enrichment JSON).

