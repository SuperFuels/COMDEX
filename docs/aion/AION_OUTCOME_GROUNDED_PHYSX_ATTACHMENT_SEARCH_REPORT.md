# AION Outcome-Grounded PhysX Attachment Search

## Executive result

AION replaced a binary collision heuristic with an outcome-grounded physical
concept of attachment. The resulting controller produced an 18.15-times
development return increase, completed a full PhysX lift, and then doubled
sealed lift success from 1/12 to 2/12 while improving matched mean return by
69.72%. The end-to-end challenger nevertheless failed the precommitted
greater-than-2/12 absolute lift gate and was rejected. Protected v13 remains
the cloud champion.

HexCore promotes only the bounded component
`procedure_outcome_grounded_physx_attachment_semantics_v1`. It does not promote
the end-to-end lift controller.

## Failure-driven reconstruction

The previous local tactile skill assumed that either fingertip force above
0.35 indicated meaningful contact and that six consecutive one-sided frames
would be available for correction. A private PhysX acquisition trace showed
that contact is impulsive and highly asymmetric:

- most one-sided bursts lasted only one to three frames;
- force peaks saturated at 250;
- many dual contacts occurred with an almost fully closed gripper and did not
  move the cube;
- the local six-frame correction option almost never executed.

A matched causal experiment then assigned identical resets to opposite
correction directions. The opposed hypothesis generated 22 dual-contact frames
versus five for the declared hand-axis direction, but neither arm lifted. This
falsified raw dual contact as an attachment authority.

## Learned attachment semantics

The retained independent transition authority contained 5,867 PhysX
transitions and later object-height consequences. AION searched compact
four-frame tactile/closure predicates using the first sixteen episodes and
evaluated the frozen predicate on the remaining eight episodes. The selected
signature requires:

```text
four-frame median force on both fingers: 30--150 N
minimum / maximum force ratio: at least 0.85
mean finger closure: 20--26 mm
```

It identified all three development attachment episodes with zero false
positives and all two episode-disjoint attachment episodes with zero false
positives. Object pose, reward and teacher action are forbidden at runtime.

## Controller reconstruction

The final research challenger combined four changes:

1. translation-first task-space movement;
2. demonstrated wrist posture regulated only in the positional null space;
3. bounded two-dimensional contact search with an opposed-direction tactile
   information action;
4. attachment-gated test lift and debounced slip recovery.

The controller therefore distinguishes proximity, collision and genuine
attachment. Only the learned attachment state can authorize the lift phase.

## Results

| Measure | Prior branch | Reconstructed branch |
|---|---:|---:|
| Development lifts | 0/4 | 1/4 |
| Development mean return | 1.210548 | 21.973324 |
| Development return ratio | 1.0x | 18.15x |
| Sealed lifts | protected v13: 1/12 | challenger: 2/12 |
| Sealed mean return | protected v13: 8.535382 | challenger: 14.486028 |
| Verified attached actions | -- | 300 |
| Teacher actions | 0 | 0 |
| Privileged runtime inputs | 0 | 0 |
| Unsafe actions | 0 | 0 |

The sealed challenger met the relative success requirement but missed the
absolute promotion requirement by one lift. It was rejected without changing
the gate. This is a meaningful competence increase and a successful physical
representation discovery, not a promoted end-to-end manipulation skill.

## Next boundary

The remaining loss is after attachment acquisition: only six sealed proposals
entered phase three, and verified grasps sometimes failed to convert into a
stable upward trajectory. The next development objective is a dedicated
load-accommodation controller learned from attached transitions: estimate
object-following response during a 1--2 cm test lift, adjust vertical velocity
and wrist posture under load, and abort/regrasp on negative object-following
evidence. No further sealed lift tournament should run until this controller
passes an episode-disjoint attachment-to-lift conversion gate.

Both NVIDIA instances were stopped after artifact retrieval.

## Search-scale falsification and frozen successor

A later matched development experiment tested whether the sealed shortfall was
caused by insufficient spatial coverage. The successful attachment controller
was held fixed while the search radius changed from 15 mm to 30 mm. Both arms
ran in the same Isaac process over identical seeds and budgets.

| Measure | 15 mm retained | 30 mm challenger |
|---|---:|---:|
| Development lifts | 2/6 | 1/6 |
| Mean return | 14.037160 | 9.361190 |
| Maximum cube height | 0.354496 m | 0.395983 m |
| Unsafe actions | 0 | 0 |
| Teacher/runtime privileged fields | 0 | 0 |

The wider search was therefore rejected. More spatial displacement is not a
monotonic improvement: it can skip a valid local grasp basin. The important
episode-level result was complementary rather than uniformly dominant. The
15 mm arm succeeded on episodes zero and four, while the 30 mm arm uniquely
succeeded on episode five.

This evidence produced a frozen coarse-to-fine successor. It preserves the
entire 15 mm local cardinal cross before permitting 30 mm cardinal expansion;
diagonal moves are attempted only afterward. Its implementation, runner,
development seed, hashes and selection rule were committed before execution.
The selection gate is at least 3/6 lifts, strictly above the retained 15 mm arm,
with zero unsafe, teacher or privileged actions. Failure forbids a sealed
tournament.

The provider rejected the requested run because cloud credit was exhausted.
This is recorded as an infrastructure block, not a policy result. Both NVIDIA
instances remain stopped, and no competence or promotion credit has been
awarded to the unexecuted successor.
