#!/usr/bin/env bash
set -euo pipefail
cd "/workspaces/COMDEX"
python -m backend.genome_engine.run_genomics_benchmark --config "/workspaces/COMDEX/docs/Artifacts/v0.4/P21_GX1/runs/P21_GX1_98e9ab26_S1337/CONFIG.json"
