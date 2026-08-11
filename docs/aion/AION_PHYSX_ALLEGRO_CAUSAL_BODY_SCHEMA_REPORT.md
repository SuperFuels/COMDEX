# AION PhysX Allegro Causal Body-Schema Report

**Date:** 2026-08-04  
**Earned procedure:** `procedure_physx_allegro_causal_body_schema_v1`  
**Manipulation challenger:** rejected; no manipulation procedure promoted

## Result

AION learned the complete action-to-joint anatomy of a 16-degree-of-freedom
Allegro hand from physical interventions under NVIDIA PhysX. No hand map or
teacher action was supplied to the learner. The final schema reconstructed the
strongest affected joint for all 16 action channels on a held-out intervention
amplitude, horizon and reset cohort.

| Measure | Result |
|---|---:|
| Action channels | 16 |
| Distinct joints assigned | 16 |
| Held-out causal reconstructions | 16/16 |
| Discovery intervention settings per channel | 9 |
| Teacher actions | 0 |
| Privileged object state used by policy | 0 |
| Pre-action commitments | 656 |
| Unsafe actions / ambient authority expansion | 0 / 0 |

The first single-pulse probe produced only 15 distinct effects because cube
contact and hand relaxation confounded two neighbouring joints. The replacement
learner used paired positive/negative interventions over three amplitudes and
three time horizons. It constructed a robust 16-by-16 causal response matrix,
solved the exact maximum-weight one-to-one assignment, and tested the learned
map using a previously unused amplitude and horizon.

Body calibration was subsequently isolated from object contact. During schema
learning only, the cube was moved out of reach and joint reset noise was
disabled. This is the robotic analogue of learning to move one's fingers before
attempting manipulation. Gymnasium, Torch and NumPy reset authorities were
seeded explicitly. Ordinary in-hand object resets were restored for the later
manipulation examination.

## Coordinated manipulation challenge

After the body-schema gate passed, AION grouped learned joints by digit and
constructed 12 teacher-free thumb--finger coordination programs. Development
outcomes selected thumb--index co-motion. On a disjoint sealed reset it reduced
object translation from 0.0661 m to 0.0431 m and improved cumulative reward
from -10.2631 to -7.2618. However, the inactive hand already experienced
0.7095 rad of cube rotation and the challenger reached only 0.7405 rad, a
margin of 0.0310 rad against a required 0.0500 rad. The manipulation gate
therefore failed and no manipulation procedure was promoted.

This rejection localizes the next bottleneck. AION now knows which actuator
moves every Allegro joint; an open-loop digit program still cannot distinguish
useful contact from passive cube motion. The next challenger must close the
loop over fingertip force, detect thumb--finger opposition, make short
interruptible corrections, and re-observe after every contact change.

## Integrity and provenance

The immutable receipt is
`results/immutable/isaac_precision_franka/allegro_embodied_schema_v5_physx_receipt.json`
with SHA-256
`ba794bde9efc7d647455eb40c4d9d16c2f6b05660b1c38a8b5ba9923778bcc08`.
The two earlier non-passing receipts remain preserved. The NVIDIA GPU was
stopped immediately after evidence retrieval. This is a bounded causal body
schema under public simulation physics, not general dexterity, robotics
mastery, AGA or AGI.

