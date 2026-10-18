#!/usr/bin/env bash
set -euo pipefail

IMAGE="nvcr.io/nvidia/isaac-lab@sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4"
IMAGE_DIGEST="sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4"
WORKSPACE="${AION_ISAAC_WORKSPACE:-/home/ubuntu/aion-isaaclab}"
CACHE="${AION_ISAAC_CACHE:-/home/ubuntu/aion-isaac-cache}"

if [[ ! -f "${WORKSPACE}/results/aion_isaac_lab_embodied_handoff.json" ]]; then
  echo "Missing frozen AION contract in ${WORKSPACE}/results" >&2
  exit 2
fi

mkdir -p "${CACHE}"/{ov,warp,pip,nvidia,compute,logs}

if [[ $# -eq 0 ]]; then
  echo "Pass the frozen runner arguments, including --policy-plugin, --arm and --seed." >&2
  exit 2
fi

exec docker run --rm --gpus all \
  --network=host \
  -e ACCEPT_EULA=Y \
  -e PRIVACY_CONSENT=Y \
  -e AION_ISAAC_CONTAINER_DIGEST="${IMAGE_DIGEST}" \
  -v "${WORKSPACE}:/workspace/aion:rw" \
  -v "${CACHE}/ov:/root/.cache/ov:rw" \
  -v "${CACHE}/warp:/root/.cache/warp:rw" \
  -v "${CACHE}/pip:/root/.cache/pip:rw" \
  -v "${CACHE}/nvidia:/root/.cache/nvidia:rw" \
  -v "${CACHE}/compute:/root/.nv/ComputeCache:rw" \
  -v "${CACHE}/logs:/root/.nvidia-omniverse/logs:rw" \
  --entrypoint /workspace/isaaclab/isaaclab.sh \
  "${IMAGE}" \
  -p /workspace/aion/integrations/isaac_lab/aion_isaac_lab_runner.py \
  --headless --enable_cameras \
  --contract /workspace/aion/results/aion_isaac_lab_embodied_handoff.json \
  "$@"
