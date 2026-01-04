# Evidence — GX1 metrics schema-compat hotfix

- File: backend/genome_engine/run_genomics_benchmark.py
- Sanitization:
  - metrics.pop("mode", None)
  - metrics.pop("stride", None)
  - metrics.pop("max_events", None)
- Reason: gx1_genome_benchmark_metrics.schema.json forbids additional root properties.
- Tests: backend/genome_engine/tests — 17 passed
