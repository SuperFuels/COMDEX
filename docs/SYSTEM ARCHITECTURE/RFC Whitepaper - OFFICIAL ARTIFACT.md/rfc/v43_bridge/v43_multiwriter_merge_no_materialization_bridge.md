# v43 — Multi-writer deterministic merge (CRDT-style, no materialization)

**Meaning.** Multiple writers emit deltas concurrently; we prove/measure a deterministic merge law:
merge order does not change the resulting state.

**Lean theorem.**
- `V43_MultiWriterMergeNoMaterialization.lean`

**Locked benchmark output.**
- `v43_multiwriter_merge_out.txt`

**Lock file (sha256).**
- `v43_multiwriter_merge_lock.sha256`

Lock ID: v43_multiwriter_merge  
Status: LOCKED  
Maintainer: Tessaris AI  
Author: Kevin Robinson.
