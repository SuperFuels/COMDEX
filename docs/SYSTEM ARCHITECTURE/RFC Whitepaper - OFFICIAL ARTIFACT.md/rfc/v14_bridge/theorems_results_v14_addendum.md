# Addendum: WirePack v14 Results — DNF Blowup vs Canonical Tree

This benchmark instantiates the Lean theorem family and measures wire sizes for:

- **Canonical tree JSON** (GlyphOS-style nested operator tree)
- **Fully-expanded DNF JSON** (enumerating all DNF terms)

Gzip uses level 9.

## Headline

Even after gzip, the expanded DNF stream rapidly dominates the canonical tree size.
In the shown run (n=18), the gzipped DNF encoding is **~4538× larger** than the gzipped canonical tree.

## Table (from `glyphos_wirepack_v14_dnf_blowup_benchmark.py`)

> (See `glyphos_wirepack_v14_dnf_blowup_results.md` for the full printed table and `glyphos_wirepack_v14_dnf_blowup_results.json` for machine-readable output.)

## Lock (SHA-256)

- `SymaticsBridge/DNFBlowup.lean`: **b8fb5eea0fae3b965a71be6fcc7d54df0f6109ece344af328ef8c8b9baec0d5c**
- `backend/tests/glyphos_wirepack_v14_dnf_blowup_benchmark.py`: **b72f4bc665b8ac7ad3d8c736096e807b5312bb7d920b06306405781431304cb2**
