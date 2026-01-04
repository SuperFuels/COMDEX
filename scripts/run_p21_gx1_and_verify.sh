#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/COMDEX || exit 1
python -m backend.genome_engine.run_genomics_benchmark \
  --config backend/genome_engine/examples/gx1_config_p16pilot.json

./scripts/verify_p21_gx1.sh
