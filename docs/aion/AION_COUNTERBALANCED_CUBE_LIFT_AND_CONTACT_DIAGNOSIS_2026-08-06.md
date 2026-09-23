# AION counterbalanced cube-lift and contact diagnosis

Date: 2026-08-06

## Verdict

The millimetre-precision controller did not improve cube lifting. In four
independent Isaac Lab processes, with order reversed between repeats, the
protected retained controller achieved 0/12 lifts and the challenger achieved
0/12. Neither controller moved the cube above its 0.055 m resting height. Both
had zero unsafe outcomes. The development gate failed, no sealed tournament
was opened and the challenger was not promoted.

The immutable authority receipt is
`results/immutable/isaac_precision_franka/precision_contact_counterbalanced_dev_20260806_v1.json`
with SHA-256
`ed0e4f273b9cce1d0fcd7d1913d47d3a387e05a05ddb1ec8ff13519bfefbf3c1`.

## What failed

The failure occurred before lifting: the policies did not establish a verified
two-finger attachment.

- The precision controller spent 2,523 proposal steps in phase 1 alignment and
  only 43 in phase 2 contact acquisition across its two processes.
- The retained controller reached phase 2 for 895 proposal steps.
- Precision saw only four dual-touch frames; retained saw seventeen.
- No attachment-signature event latched in either controller.
- The precision controller's 8 mm phase-1 gate therefore over-corrected the
  earlier 32--35 mm premature-close fault and starved the system of contact
  attempts.

This is a contact-acquisition failure, not evidence that the post-grasp lift
trajectory is wrong.

## Corrective controller

The next offline controller now:

1. enters contact acquisition at 12 mm rather than 8 mm;
2. keeps the fingers open while completing the final 5 mm alignment;
3. uses the existing 3 mm contact-motion limit;
4. starts the failed-close timer only when finger closing actually begins.

This keeps closure far inside the rejected 32--35 mm range while restoring
enough time for physical contact. Nineteen focused controller, tactile,
transition, authority and cost checks pass. The change has no cloud competence
credit until it produces successful lifts under a new precommitted evaluation.

## Compute state and claim boundary

Both NVIDIA Brev GPUs were stopped after artifact retrieval. The experiment is
a development result only. It does not establish Cosmos training, general
robotics competence, AGA or AGI.
