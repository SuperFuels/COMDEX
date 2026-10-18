#!/usr/bin/env bash
set -euo pipefail

ROOT="${AION_ISAAC_WORKSPACE:-/home/ubuntu/aion-isaaclab}"
RUN_ID="${AION_FRESH_WORLD_RUN_ID:?Set a new immutable run identifier}"
EPISODES="${AION_FRESH_WORLD_EPISODES:-2}"
cd "${ROOT}"

for repeat in a b; do
  python3 integrations/isaac_lab/run_fresh_world_physx_authority.py \
    --workspace "${ROOT}" \
    --receipt-directory "results/immutable/isaac_precision_franka/${RUN_ID}_${repeat}_children" \
    --output "${ROOT}/results/immutable/isaac_precision_franka/${RUN_ID}_${repeat}.json" \
    --policy-plugin physx_determinism_probe:propose \
    --arms aion_retained \
    --episodes "${EPISODES}" \
    --steps 250 \
    --seed 123001
done

python3 integrations/isaac_lab/verify_fresh_world_physx.py \
  "results/immutable/isaac_precision_franka/${RUN_ID}_a.json" \
  "results/immutable/isaac_precision_franka/${RUN_ID}_b.json" \
  --output "results/immutable/isaac_precision_franka/${RUN_ID}_audit.json"
