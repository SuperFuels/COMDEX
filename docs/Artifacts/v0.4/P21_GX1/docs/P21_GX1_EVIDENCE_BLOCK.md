# P21_GX1_EVIDENCE_BLOCK (v0.4)

This phase records a deterministic genomics benchmark run (GX1) and its artifact ladder.

## Canonical entrypoint
```bash
python -m backend.genome_engine.run_genomics_benchmark --config <CONFIG.json>
```

## Latest run
RUN_ID: P21_GX1_77481708_S1337
GIT_REV: 6141b8f41cf41982de4228e109389311ed1ce318

## Verify
```bash
cd "/workspaces/COMDEX" || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```

## Notes
- Computational benchmark harness with engineered baselines.
- No wetlab / biological efficacy claim is made by this phase.
