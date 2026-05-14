#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] starting fusion kernel..."
python -u backend/modules/aion_cognition/tessaris_cognitive_fusion_kernel.py &

# Optional: if you actually need QFC broadcast derived from fusion:
# echo "[entrypoint] starting fusion->qfc bridge..."
# python -u backend/modules/visualization/stream_qfc_from_fusion.py &

echo "[entrypoint] starting api..."
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}"