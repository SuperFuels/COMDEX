# 🧩 Tessaris Wiki Capsule Build Checklist — Phases 1–9

This checklist outlines the progressive development and validation path for the **Tessaris Wiki Capsule System**, which connects `.wiki.phn`, `.phn`, and `.ptn` capsules into the unified Photon Language ecosystem.

---

## ✅ Phase 1 — Foundations
- [x] Define `WikiCapsule` dataclass + schema
- [x] Implement serializer → `.wiki.phn`
- [x] Add test coverage (`test_create_capsule.py`)

## ✅ Phase 2 — Knowledge Graph Integration
- [x] `kg_query_extensions.py` → CRUD operations
- [x] `wiki_importer.py` → JSON → capsule converter
- [x] `test_kg_query.py` + `test_wiki_importer.py`

## ✅ Phase 3 — Photon Integration
- [x] Glyph plugin: 📚 (`wiki_plugin.py`)
- [x] Plugin registry integration
- [x] End-to-end tests → `test_wiki_plugin.py`

## ✅ Phase 4 — Safety & Curation
- [x] Signature verification (`signed_by`, checksum)
- [x] Whitelist + sandbox policy
- [x] Audit hooks for KG + SQI logging
- [x] `test_safety_layer.py`

## ✅ Phase 5 — Developer Tools
- [x] `search_api.py` → keyword/fuzzy search
- [x] `sci_autocomplete_plugin.py` → IDE integration
- [x] `graph_explorer_ui.py` → visualize Wiki Graph

## ✅ Phase 6 — Validation & Maintenance
- [x] `wiki_linter.py` → syntax/metadata validator  
- [x] `reference_validator.py` → cross-link checker  
- [x] `maintenance_jobs.py` → scheduled pruning  

## ✅ Phase 7 — Photon Runtime Integration
- [x] `photon_executor_extension.py`
- [x] `/codex/run-photon` API

## ✅ Phase 8 — Resonance Feedback Alignment
- [x] Integrate SQI (ρ, Ī) with Aion feedback channels
- [x] `resonance_alignment.py` + `wiki_resonance_sync.py`

## ✅ Phase 9 — Documentation & Examples
- [x] `WIKI_API_REFERENCE.md`
- [x] `WIKI_FORMAT_SPEC.md`
- [x] Example `.wiki.phn` capsules

---

### ⚙ Build Command Summary

```bash
PYTHONPATH=. pytest backend/modules/wiki_capsules/tests -v
PYTHONPATH=. pytest backend/modules/wiki_capsules/devtools_search/tests -v
PYTHONPATH=. pytest backend/modules/wiki_capsules/validation_maintenance/tests -v