# P15 Predictions (TODO)

Status: ROADMAP

## P15-PRED-0001 (placeholder; NOT ASSERTED)
- Dataset: ENCODE (candidate) — TF ChIP-seq + matched controls (TBD)
- Preprocessing: P15_PREPROCESS_V0_TBD (hash TBD)
- Metrics:
  - motif_enrichment_delta (directional; TBD)
  - selectivity_vs_background (TBD)
- Null model: TBD
- Negative controls:
  - shuffle_keys_preserve_gc
  - scramble_motif_positions
  - random_matched_regions
- Ablations:
  - remove_key_constraint
  - remove_topology_proxy
  - remove_separation_term
- PASS/FAIL rule:
  - TBD: effect size + uncertainty + multiple-hypothesis handling; negatives must fail; ablations must degrade.
