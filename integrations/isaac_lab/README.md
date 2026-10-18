# AION Isaac Lab cloud execution bundle

This directory is a cloud worker, not AION's brain. It executes the frozen
contract in NVIDIA Isaac Lab/PhysX and emits content-addressed evidence for
local HexCore verification.

## Required authority

- Linux NVIDIA GPU host with a supported driver and NVIDIA Container Toolkit.
- NVIDIA Isaac Lab container. The handoff is pinned to the signed official
  `3.0.0-beta2-post1` image at digest
  `sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4`.
- Explicit NVIDIA EULA acceptance by the human/cloud operator.
- A policy plugin for each experimental arm.
- An independent Ed25519 signing key whose public key is registered locally.

The Mac cannot execute or self-certify the NVIDIA cohort.

## Frozen artifacts

Generate locally:

```bash
.venv/bin/python -m backend.modules.hexcore.simulator_disjoint_embodied_scaleup
```

Upload these files to the GPU worker:

- `results/aion_isaac_lab_embodied_handoff.json`
- `integrations/isaac_lab/aion_isaac_lab_runner.py`
- the chosen policy plugin and its digest-pinned skill capsules

The wrapper injects a renderer-backed RGB camera, strips the stock task's
object, target, reward and prior-action state, and exposes only RGB plus bounded
robot joint positions/velocities to the proposal plugin. It also contains one
narrow recovery for NVIDIA's missing 6.0 Franka USD: only the same official S3
authority's verified 5.1 Franka asset is permitted, and the substitution is
recorded in every receipt.

Inside the Isaac Lab container, execute each arm with independently committed
seeds. Example:

```bash
bash integrations/isaac_lab/run_brev_frozen_contract.sh \
  --output /workspace/aion/artifacts/aion_retained_receipt.json \
  --policy-plugin aion_isaac_policy:propose \
  --arm aion_retained \
  --environment-id Isaac-Lift-Cube-Franka-v0 \
  --episodes 6 --steps 1000 --seed 1701
```

Repeat under the matched budget for `aion_cold`, `aion_cosmos`, and
`gr00t_teacher`. The Cosmos and GR00T arms are proposal/teacher baselines; they
never become physics or promotional authorities.

## Fail-closed evidence path

The runner deliberately emits an incomplete unsigned receipt. The operator
must combine all arms, compute metrics, bind raw artifacts, attest the audit
flags, and sign the final receipt. Local HexCore rejects:

- unsigned or altered receipts;
- missing CUDA, Isaac Lab, Isaac Sim, driver or container identity;
- privileged simulator fields;
- missing cold, Cosmos or GR00T arms;
- unmatched budgets;
- unsafe actions;
- absent later reconstruction; or
- insufficient lift over cold control.

Package readiness is not Isaac competence. Promotion is possible only after a
non-fixture signed receipt passes the frozen local verifier.

## Authority probe result

On 2 August 2026 the retained arm completed a three-step real Franka lift
probe on an NVIDIA L40S. The exact container, PhysX backend, RGB/proprioception
filter, action-space digest, commit-before-act chain and official asset recovery
all executed successfully. No unsafe action occurred. The cube was not lifted,
so this closes execution grounding only; it is not manipulation competence or
Cosmos/GR00T mastery.
