# AION Self-Modelled Tactile Hand Apprenticeship

## Result

HexCore promoted
`procedure_self_modelled_tactile_hand_apprenticeship_v1`.  This procedure adds
a simulator-neutral embodiment layer between visual arm placement and object
manipulation.  AION no longer has to treat a hand as an opaque scalar gripper:
it can discover which action channel controls which visible digit, determine
the useful direction, estimate response magnitude and latency, bind fingertip
touch to that discovered digit, and use the resulting body schema to select and
place the task-relevant finger.

| Measure | Result |
|---|---:|
| Sealed finger-selection/contact tasks | 15/15 |
| Memory-free identity-map control | 0/15 |
| Unseen hand wirings | 3 |
| Digits exercised per hand | 5/5 |
| Correct visual digit selections | 15/15 |
| Pre-action commitments | 1,489 |
| Malformed or excessive actions rejected | 4/4 |
| Teacher actions | 0 |
| Privileged target identity | 0 |
| Restart reconstruction | Passed |

## Embodiment authority

Each MuJoCo hand contains five independently actuated solid fingertip bodies,
five genuine touch sensors and a solid target button.  The outcome authority
changes the actuator permutation, action direction, motor gain, delay and hand
spacing between worlds.  These variables are never supplied to the learner.
MuJoCo, rather than learner code, owns collision and contact force.

Runtime input is restricted to RGB, five joint positions, five joint
velocities, five fingertip touch values and time.  The hidden actuator map,
target-digit label, contact geometry and teacher action remain outside the
proposal boundary.

## Learned body-schema cycle

The retained method is:

1. visually discover the hand topology and the requested contact location;
2. issue bounded reversible probes through one unknown action channel at a
   time;
3. observe which physical digit moved and estimate direction, displacement and
   latency;
4. require a bijective channel-to-digit map, otherwise abstain;
5. bind tactile channels to the discovered visible digits;
6. select the digit nearest the visual target;
7. approach under joint feedback, stop on independent tactile evidence and
   counteract residual motion rather than continuing to push; and
8. retain the functional body schema as a digest-pinned skill capsule.

The cold controller assumes that action channel number equals finger number.
It therefore collapses when the tendons are permuted.  AION reconstructs the
functional map from consequences and succeeds across every sealed hand.

## Isaac transfer contract

`aion_tactile_hand_contract.py` provides the corresponding fail-closed Isaac
boundary.  It accepts contact-force vectors only from an explicitly discovered
set of fingertip bodies, rejects missing or additional bodies, rejects invalid
or excessive forces, produces a bounded ordered tactile vector and constructs
the official Isaac Lab contact-sensor configuration lazily inside the GPU
runtime.  It never converts object pose or a simulator contact graph into a
policy input.

## Consequence for manipulation

The next Franka controller should implement a contact-centred grasp sequence:

\[
\text{coarse visual approach}
\rightarrow \text{reobserve near object}
\rightarrow \text{independent digit alignment}
\rightarrow \text{first contact}
\rightarrow \text{asymmetric finger correction}
\rightarrow \text{balanced pressure}
\rightarrow \text{test lift}
\rightarrow \text{slip recovery}.
\]

This directly addresses the current PhysX failure: correct gross placement is
not enough when both fingers are closed symmetrically despite an asymmetric
millimetre-scale miss.

## Claim boundary

This is verified local five-digit self-modelling and tactile contact under
MuJoCo physics.  It is not yet dexterous multi-object manipulation, Isaac/PhysX
transfer, a real tactile hand or delicate-object competence.  The promoted
asset is a transferable method for learning a hand and grounding actions in
touch, not a claim that AION has mastered robotic hands.

