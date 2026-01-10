# v41 — Provenance / receipt-gated queries (auth + ancestry bound)

## Meaning
v41 stitches receipt-chain integrity into the analytics layer: an analytics answer is only accepted if it was computed over
a delta stream whose receipts are authenticated and ancestrally consistent.

Buyer claim: trustworthy analytics — dashboards can only be produced from authenticated history.

## What is proved (Lean)
This bridge models:
- a receipt-chain validity predicate (ChainOk),
- an analytics fold over deltas producing an answer,
- a gated predicate (GatedAnswer) requiring receipts verify and chain.

Key theorem (informal):
- **No spoofed provenance:** if `GatedAnswer` holds for a chain, then tampering (delta edits, deletion, reordering, splicing, parent change)
  causes gating to fail unless authentication is broken or digests collide.

Lean artifact:
- `V41_ReceiptGatedQueries.lean` (copied from workspace exact)

## What is measured (gated analytics harness)
The benchmark:
- generates a delta stream + receipt chain,
- computes an analytics answer,
- validates gating (`verify_ok=True`, `gated_ok=True`),
- demonstrates tamper cases where gating fails.

Locked output:
- `v41_receipt_gated_queries_out.txt`

Lock hashes:
- `v41_receipt_gated_queries_lock.sha256`

## Artifacts in this folder
- `LOCK_v41_receipt_gated_queries.txt`
- `v41_receipt_gated_queries_bridge.md`
- `v41_receipt_gated_queries_lock.sha256`
- `v41_receipt_gated_queries_out.txt`
- `V41_ReceiptGatedQueries.lean`

Lock ID: v41_receipt_gated_queries
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson.
