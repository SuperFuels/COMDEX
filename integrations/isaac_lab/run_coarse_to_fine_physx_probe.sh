#!/usr/bin/env bash
set -euo pipefail

ROOT="${AION_ISAAC_WORKSPACE:-/home/ubuntu/aion-isaaclab}"
cd "${ROOT}"

# Development-only matched comparison.  aion_retained is the frozen 15 mm
# cross/diagonal search; aion_distilled preserves that cross and expands to
# 30 mm only after all local cardinal attempts fail.
bash integrations/isaac_lab/run_brev_frozen_contract.sh \
  --output /workspace/aion/results/immutable/isaac_precision_franka/coarse_to_fine_paired_dev_receipt.json \
  --policy-plugin physx_search_radius_probe:propose \
  --arm aion_retained \
  --comparison-arm aion_distilled \
  --environment-id Isaac-Lift-Cube-Franka-v0 \
  --episodes 6 \
  --steps 250 \
  --seed 121001 \
  --deterministic
