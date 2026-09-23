# AION Active Tactile Grasp Apprenticeship v2

## Result

HexCore promoted
`procedure_active_tactile_grasp_apprenticeship_v2` as a bounded local physical
skill. The procedure replaces binary contact permission with this closed loop:

```text
RGB approach
-> contact-state belief
-> persistent one-sided diagnosis
-> bounded open/recentre action option
-> opposed-contact balancing
-> protected nominal route or progressive test lift
-> slip diagnosis and recovery
-> consequence-confirmed lift
```

The authority is a MuJoCo-owned free cube, opposing independently actuated
fingers and a laterally/vertically movable wrist. Mass, friction, object size,
action delay, tactile gain, initial pose, visual hand--eye calibration and
external disturbances vary outside the policy. Runtime observations contain
only RGB, joint position/velocity and two bounded fingertip force magnitudes.
Object pose, contact geometry, reward and teacher action are forbidden.

## Architecture

### Attachment belief state

The controller retains six states rather than treating any contact as
permission to lift:

```text
no_contact | left_only | right_only | dual_unstable | attached | slipping
```

Dual contact must persist before attachment is considered. Loss is debounced
to avoid reacting to one-frame solver noise, while loss of a latched grasp
during upward motion produces a slip state.

### Tactile correction option

One-sided contact is allowed a short transient window. If it persists, the
system opens both digits, executes a bounded six-step lateral correction toward
the contacting side, reobserves and recloses. This is an interruptible action
option rather than a long open-loop trajectory. Every step remains below the
authority's delta limit and is committed before execution.

### Governed routing and progressive load acquisition

Indiscriminate tactile recovery regressed easy grasps. The promoted controller
therefore preserves a nominal direct-lift route when opposed contact is stable
with no more than twenty corrective steps. Harder cases enter progressive
test-lift and recovery. The controller closes while raising the object through
a small test movement; one-sided or lost contact causes downward motion and
renewed closure rather than continued upward commitment.

## Sealed evidence

| Measure | Result |
|---|---:|
| Development worlds | 3/3 |
| Sealed worlds | 12/12 |
| Sealed binary control | 6/12 |
| Prospective source-disjoint worlds | 42/48 |
| Prospective binary control | 27/48 |
| Nominal calibration group | 22/24 |
| Severe calibration group | 20/24 |
| Severe binary control | 3/24 |
| Hidden-disturbance group | 13/16 |
| Unsafe actions | 0 |
| Malicious action classes rejected | 4/4 |
| Teacher actions | 0 |
| Privileged runtime geometry | 0 |
| Restart/capsule reconstruction | Passed |

The prospective cohort was generated from frozen seed `180801` and varied
object position, size, mass, friction, action delay, sensor gain, initial wrist
position and visual marker bias. Sixteen worlds also applied a hidden lateral
disturbance during contact or lifting. The severe calibration lane used
hand--eye offsets between 4.5 and 5.8 cm; active correction achieved 83.33%
versus 12.50% for the fixed strategy, a 6.67-times success ratio.

The weakest nominal group remained 91.67%, two cases below the fixed control's
24/24. That limitation is retained explicitly and prevents a claim of
universal non-regression.

## Rejected challengers and learning

- A binary future-lift classifier scored strongly offline but produced 0/12
  PhysX lifts when used as a hard veto.
- Immediate tactile correction interfered with ordinary transient contact.
- Single-frame corrections disappeared as soon as opening removed touch and
  never completed recentering.
- A minimum-force threshold overfit development outcomes and reduced
  source-disjoint transfer.
- Always-on tactile recovery regressed the protected nominal strategy.

These failures produced the promoted combination of persistence detection,
short correction options, progressive load testing and conditional routing.

## Safety and authority

Actions are four bounded deltas: wrist lateral, wrist vertical, left digit and
right digit. NaN, infinite, malformed and out-of-range programs are rejected
before simulation. The policy cannot read the MuJoCo cube body, contact list,
mass, friction, disturbance or score. Privileged state is used only by the
post-action authority to determine whether the independently simulated cube
actually rose by at least 7.5 cm.

## Claim boundary and next gate

This is a meaningful local manipulation advance: AION can use contact as an
information source, switch authority from biased vision to touch, execute
bounded correction options, test attachment and recover from disturbance over
source-disjoint MuJoCo worlds. It is not yet a PhysX promotion, general robot
dexterity, real-hardware competence or mastery of NVIDIA world models.

## Franka adapter and sealed PhysX result

The Franka adapter was subsequently constructed and passed its complete
offline contract. It mapped left/right fingertip-force histories through the
current hand frame into bounded task-space corrections, retained the promoted
v2 capsule as its parent, and passed three pose-direction checks, six action
bounds, three semantic checks, four malicious-program rejections and restart
reconstruction. Its immutable adapter digest is
`71569d3b43fae351bd795678fb29515d63f1f9d3dff6c7af34de3488e00bc9f8`.

One sealed NVIDIA PhysX tournament then compared the frozen tactile challenger
with protected v13 on twelve identical unseen resets. The teacher was absent,
runtime privileged object state was absent, budgets were matched and every
action was committed before execution.

| PhysX measure | Tactile challenger | Protected v13 |
|---|---:|---:|
| Strict lifts | 0/12 | 1/12 |
| Mean return | 1.427686 | 1.416214 |
| Maximum object height | 0.05500 m | 0.11123 m |
| Proposals | 3,000 | 3,000 |

The challenger failed the mandatory greater-than-2/12 absolute gate and did
not beat the protected controller on lift success. It was therefore rejected;
no PhysX procedure was promoted and v13 remains champion. Its cloud-policy
integration was removed after the sealed receipt was preserved.

Trace evidence localised the failure. The challenger produced ten ordinary
contact retries and two slip recoveries, but its active one-sided tactile
correction option was never selected. Only four proposals entered the
attachment/test-lift phase, while 149 proposals fell back on visual OOD. Thus
the local skill itself remains valid, but the Franka binding did not establish
that Isaac's fingertip-force signal carried the same directional contact
semantics as the MuJoCo authority. The next experiment must identify those
semantics from paired PhysX interventions before reusing the local correction
option; another threshold-tuned lift tournament is not justified.

The immutable outcome receipt is
`results/immutable/isaac_precision_franka/active_tactile_v10_physx_receipt.json`.
Its visual-evidence manifest commits six policy-input frames with no privileged
overlay under SHA-256
`a38d31a3f31e55d55e8f1b825803da4cbc76e2049206d3a466e361ae77ebbf49`.
Both paid NVIDIA instances were stopped immediately after receipt capture.
