# AION contact geometry and capture fail-fast report

Date: 2026-08-06

## Outcome

The cube has not yet been lifted. Two bounded four-episode L40S probes completed
with zero unsafe outcomes and zero strict lifts. The first probe nevertheless
produced the first opposed two-fingertip PhysX contact in this diagnostic line
(two frames). Previous precision probes produced none.

No tournament, promotion or manipulation-competence credit was issued.

## Root cause corrected

The v3 contact builder measured the Franka hand at the first finger-close frame
against the cube position at reset. In the successful teacher archive, the cube
settled roughly 32 mm between those instants. The resulting internally
consistent model commanded the hand about 30 mm too low and allowed empty
finger closes.

The v4 builder time-aligns the hand and cube at the same grasp frame. Its mean
learned hand-to-cube offset changed from approximately 61 mm to 93 mm vertically.
All offline gates passed, including 80% sealed coverage within 20 mm, and all 20
focused tests passed.

## PhysX probes

### Contact geometry v4

- Seed: 125301
- Episodes: 4 x 250 steps
- Strict lifts: 0/4
- Opposed fingertip-contact frames: 2
- Attachment signatures: 0
- Unsafe outcomes: 0

This validates the direction of the geometry correction, but contact was brief
and occurred during final approach rather than becoming a secure grasp.

### Contact capture

The controller was then changed to freeze the physically observed pose and
close immediately whenever opposed fingertip contact appeared during final
approach. The bounded close window increased from 10 to 16 frames so finger
closure plus the four-frame sealed attachment signature can complete. The
attachment signature remains mandatory before lift.

- Seed: 125401
- Episodes: 4 x 250 steps
- Strict lifts: 0/4
- Opposed fingertip-contact frames: 0
- Attachment signatures: 0
- Unsafe outcomes: 0

The different seed cohort did not reacquire contact, so the capture transition
was not physically exercised. It remains an unpromoted development candidate.

## Current diagnosis

The dominant failure has moved from a systematically wrong vertical grasp
target to unreliable final-approach convergence. Phase-one task distance often
diverged above 100 mm even though some episodes reached 4--8 mm and one cohort
made real opposed contact. The learned one-step inverse-dynamics controller is
therefore not consistently holding the gripper on the narrow contact corridor.

The next decisive change is a direct, bounded joint-position/IK contact servo
calibrated to Isaac Lab's actual action mapping. It should first demonstrate
repeatable opposed contact in a tiny cohort; only then should the attachment and
lift transition be tested or a larger tournament be funded.

## Evidence

- `results/hexcore_contact_ready_franka_adapter_v4.json`
- `results/immutable/isaac_precision_franka/contact_ready_franka_v4.json`
- `results/immutable/isaac_precision_franka/contact_ready_franka_v4.npz`
- `results/immutable/isaac_precision_franka/contact_geometry_v4_fail_fast_20260806_v1.json`
- `results/immutable/isaac_precision_franka/contact_capture_fail_fast_20260806_v1.json`
- `integrations/isaac_lab/build_precision_franka_adapter.py`
- `integrations/isaac_lab/aion_precision_franka_policy.py`

Both Brev workspaces were commanded stopped after evidence retrieval. Estimated
GPU spend for the two probes is about $0.20, subject to Brev billing granularity.
