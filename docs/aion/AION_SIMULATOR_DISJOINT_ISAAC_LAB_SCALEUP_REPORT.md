# AION Simulator-Disjoint Isaac Lab Scale-Up

## Status

The cloud execution package is complete and a real NVIDIA authority probe has
executed. It remains deliberately **not promoted** as an Isaac Lab manipulation
capability: execution grounding is now positive, while the frozen four-arm
competence cohort and later reconstruction are still outstanding.

This is the transition from local embodied foundation work to a second,
independently implemented physics stack. The Mac retains AION's cognition,
HexCore authority, skill capsules and MuJoCo regression cohort. A Linux NVIDIA
GPU worker executes Isaac Lab/PhysX and returns signed evidence.

## Frozen contract

The content-addressed contract binds:

- the three-stage retained skill ancestry;
- NVIDIA Isaac Lab and PhysX authority identity;
- permitted manipulation environments;
- RGB-first observation rules and prohibited privileged fields;
- bounded actions and commit-before-act receipts;
- sealed randomization over mass, friction, restitution, lighting, camera,
  noise, motor strength, geometry and placement;
- matched compute, reset and intervention budgets;
- four isolated experimental arms;
- promotion thresholds and abstention requirements; and
- raw observation, action, outcome and artifact hash chains.

The first task family is contact-rich object manipulation using official Isaac
Lab manipulation environments: Franka cube lift, cube stacking and drawer
opening. This is intentionally not another reaching benchmark.

## Experimental arms

| Arm | Purpose | Authority boundary |
|---|---|---|
| `aion_retained` | Test transfer of stored visual/contact/articulated methods | Candidate only |
| `aion_cold` | Same tools and budget without accumulated physical memory | Matched cold control |
| `aion_cosmos` | Cosmos action-conditioned prediction as a proposal challenger | Never physics authority |
| `gr00t_teacher` | Demonstrations and teacher-policy baseline | Never AION champion authority |

The Cosmos target is the officially listed action-conditioned
`Cosmos-Predict2.5-2B/robot/action-cond`. Predictions receive credit only when
subsequent PhysX execution confirms them. GR00T competence remains baseline or
demonstration evidence and is never misreported as AION learning.

## Cloud worker

The headless runner:

1. loads and verifies the frozen contract digest;
2. starts Isaac Lab through the official `AppLauncher`;
3. permits only whitelisted environment IDs;
4. rejects observations without RGB or containing privileged fields;
5. records content hashes instead of importing simulator truth into AION;
6. requires bounded finite actions and prediction commitments before execution;
7. chains every observation, action and outcome cryptographically;
8. records GPU, driver, CUDA, Isaac Lab, Isaac Sim and container identity; and
9. emits an intentionally unsigned receipt for independent audit and signing.

The runner cannot self-authorize its result. The operator must bind all raw
artifacts, verify matched budgets and arm isolation, calculate cohort metrics
and sign the final receipt using Ed25519.

## Fail-closed verifier

The local verifier rejects:

- an absent or invalid signature;
- a changed contract or result after signing;
- missing CUDA/NVIDIA/Isaac runtime identity;
- absent raw hash chains;
- privileged simulator observations;
- unmatched budgets;
- missing baseline arms;
- unsafe actions;
- insufficient sealed or weakest-task performance;
- inadequate improvement over cold AION;
- missing cross-backend method reuse; and
- missing later reconstruction.

Local verification results:

| Test | Result |
|---|---:|
| Retained skill ancestry bound | 3 procedures |
| Experimental arms frozen | 4 |
| Properly signed local verifier fixture | Accepted |
| Altered signed fixture | Rejected |
| Unsigned fixture | Rejected |
| Package reconstruction | Passed |
| NVIDIA authority bootstrap | Passed on L40S |
| RGB + bounded-proprioception Franka probe | Passed |
| Commit-before-act hash chains | Passed, three actions |
| Unsafe probe actions | 0 |
| Probe manipulation success | 0/1 (diagnostic only) |
| Frozen multi-arm cohort | Not yet run |
| Isaac capability promotion | False |

The fixture exists solely to test cryptographic plumbing. Its fake runtime
identity is explicitly marked `LOCAL_TEST_FIXTURE` and can never be ingested as
external evidence.

## Deployment basis

Official 2026 documentation supports headless Linux/cloud deployment using the
NVIDIA Isaac Lab container and Isaac Automator on AWS, GCP, Azure and Alibaba
Cloud. The current development documentation lists the prebuilt
`nvcr.io/nvidia/isaac-lab:3.0.0-beta2` image. The exact immutable digest used by
the cloud run must be recorded; a mutable tag is insufficient evidence.

The environment suite currently lists `Isaac-Lift-Cube-Franka-v0`,
`Isaac-Stack-Cube-Franka-v0` and `Isaac-Open-Drawer-Franka-v0`, providing the
required manipulation escalation.

## NVIDIA authority bootstrap (2 August 2026)

The first paid NVIDIA authority bootstrap completed on an NVIDIA Brev Linux
worker backed by one L40S GPU.  The instance exposed 48 GiB class VRAM, 12
CPUs, 72 GiB RAM and the NVIDIA 580.126.09 driver.  Docker 29.1.5 and NVIDIA
Container Toolkit 1.18.1 were present on the host.

The run used prepaid credit with auto-recharge disabled.  The non-pausable
worker was deleted immediately after evidence recovery.  Final compute cost
was USD 0.29, storage cost was USD 0.00 and no billable instance remained.

The original bootstrap used the following immutable digest:

```text
nvcr.io/nvidia/isaac-lab@sha256:970621075d00059c309f847fa835709de3fa634537407a7009c586c97893d218
```

Inside that exact image, CUDA exposed the L40S, PyTorch reported CUDA 12.8,
Isaac Lab imported successfully and a headless PhysX simulation completed five
steps with the marker `AION_ISAAC_PHYSX_SMOKE=PASS`.  Runtime enumeration also
confirmed all three frozen manipulation environment IDs.  The content-addressed
bootstrap receipt is stored at
`results/aion_isaac_lab_cloud_authority_bootstrap.json`.

This closes GPU, container, digest, CUDA, PhysX and environment-availability
uncertainty.  It does not close the competence gate: the four matched arms,
sealed outcomes, independent signature and later reconstruction remain due.

## RGB manipulation authority probe (2 August 2026)

The executable contract was then upgraded to NVIDIA's signed
`3.0.0-beta2-post1` image and pinned to the locally resolved repository digest:

```text
sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4
```

The image's configured Isaac 6.0 Franka asset key returned HTTP 404. Rather
than weakening the task or supplying a fabricated robot, the adapter recovered
only the same NVIDIA authority's prior public 5.1 Franka USD after an explicit
availability check. Cube and table assets remained at 6.0, and every receipt
records both URLs and the recovery decision.

The real `Isaac-Lift-Cube-Franka-v0` task then initialized with eight action
channels and a 36-value stock policy vector. The latter contains object pose,
target pose and previous-action state, so it was never supplied to AION. AION's
proposal boundary received only a 128-by-96 RGB observation and 18 bounded
robot joint position/velocity values. Simulator tensors and device handles were
also removed from that boundary; committed actions alone were copied back to
the GPU for execution.

The first diagnostic run correctly failed closed twice: initially because Kit
shutdown preceded receipt creation, and subsequently because a CUDA tensor
crossed the host-array boundary. The runner was changed to write diagnostic
receipts before shutdown, include bounded tracebacks, and sanitize all proposal
inputs. The third run completed three PhysX steps, produced nonzero observation,
action and outcome hash chains, recorded zero unsafe actions and preserved the
frozen contract digest. It did not lift the cube, so it establishes a genuine
observation-to-action-to-consequence path but not learned manipulation skill.

A matched cold arm then completed under the same seed and step budget. Its
return was indistinguishable from the retained arm and neither succeeded, so no
transfer lift was claimed. Both raw receipts are SHA-256-bound into
`results/aion_isaac_lab_rgb_authority_probe.json`; regression verification
checks those hashes and rejects any attempt to label the probe as Cosmos,
GR00T or manipulation mastery.

The paid worker was stopped immediately after artifact recovery. A cost-guarded
launcher now caps any later session by elapsed minutes and estimated compute
spend, and executes an unconditional `brev stop` in its finalizer. Its default
45-minute L40S session has a maximum compute estimate of USD 1.30 at USD 1.74
per hour. The focused local stack passes 19/19 tests.

## Remaining external action

The architecture no longer needs another local foundation phase. Completion
requires:

1. freeze independent cohort seeds against the recorded container digest;
2. supply the four isolated policy/baseline plugins;
3. run all four arms under matched budgets;
4. return the signed, artifact-bound outcome receipt;
5. verify it locally through HexCore; and
6. schedule later reconstruction before any promotion.

After a passing Isaac cohort, the next simulator-disjoint expansion is
Habitat/PARTNR household navigation and collaboration, followed by the
integrated Embodied Expedition and one modest sim-to-real transfer.

## Claim boundary

This work establishes a world-class **evaluation and transfer pathway**, not a
world-class NVIDIA result. AION has not yet mastered Isaac Lab, Cosmos or
GR00T. It has a frozen method for learning from them without surrendering truth
authority or confusing borrowed model competence with retained AION ability.
