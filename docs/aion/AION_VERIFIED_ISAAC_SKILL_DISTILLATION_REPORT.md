# AION Verified Isaac Skill Distillation and Corrective Apprenticeship

## Outcome

This stage moved AION from three-step execution grounding into a complete
embodied apprenticeship experiment under NVIDIA-owned physics. It trained an
official Isaac Lab PPO teacher, collected independently reset manipulation
trajectories, compiled teacher evidence into an AION-owned skill capsule,
removed the teacher, reconstructed one physical lift, ran a matched unseen-seed
cold control, diagnosed weak transfer, generated corrective DAgger evidence and
rejected four inadequate successor representations.

The result is deliberately **not promoted as transferable manipulation
competence**. The retained program reconstructed the source skill and produced
one unseen lift, but sealed transfer was only 1/12 against 0/12 cold. The
important advance is a real, auditable learn--act--falsify--revise pipeline and
a sharply localized next bottleneck.

## Immutable execution authority

- NVIDIA Brev L40S 48 GB at USD 1.74/hour.
- NVIDIA Isaac Lab/PhysX container fixed to
  `sha256:ae9c938a16df856effad6dab92115ee0dce2a8813f56847eeeccbebc008d02c4`.
- Official Franka 5.1 asset recovery was used after the newer beta asset URL
  failed; both the rejected URL and selected authority are retained.
- The paid instance was stopped after receipts were synchronized.

The student received RGB and 18 bounded joint position/velocity values. Object
pose, target pose, reward terms and the teacher's 36-value policy observation
were excluded. Every action was committed before PhysX revealed its
consequence. Success required post-action object-centre height above 0.10 m;
the earlier 0.04 m threshold was rejected because the resting cube itself
exceeded it.

## Teacher evidence

An official Isaac Lab RSL-RL PPO policy trained for 300 iterations over
approximately 14.75 million PhysX transitions. On 30 genuinely reset episodes,
it passed 28 strict lifts (93.33%). The two failures and all reset boundaries
remain in the outcome ledger. Only the 7,000 transitions from successful
episodes entered the initial student authority.

## Teacher-independent reconstruction

The first successful retained capsule stored 28 digest-bound skill programs and
an observation-to-program selector. After removing the PPO teacher it replayed
all 250 committed actions for source seed 9107 and lifted the cube to 0.5377 m,
earning return 81.73. This demonstrates executable procedural retention, not
merely stored documentation or a training-loss claim.

Under 12 unseen resets in a single matched process, AION achieved 1/12 strict
lifts against 0/12 cold. Mean return was 6.80 versus 0.75 and mean maximum
height was 0.0940 m versus the cold resting height of 0.0550 m. These are
positive differential signals but not robust transfer, so the challenger was
rejected.

## Failure-driven architecture revision

The rejection chain identified three distinct causal failures:

1. The initial success gate falsely counted the cube at rest. The evaluator was
   corrected before student promotion.
2. Archived fixed-length slices were not independent episodes. Collection was
   revised to explicitly reset physics and the recurrent teacher each episode.
3. Open-loop action sequences reconstructed a known reset but accumulated
   errors under changed placements.

Two closed-loop policies were then trained. The first used an 8-by-8 spatial
RGB summary and 140,552 parameters. Although action RMSE reached 0.0373, it
failed physical reconstruction, establishing that supervised fit is not task
authority.

AION then collected 5,000 DAgger states: the student controlled PhysX while the
frozen teacher labelled the corrective action at the states the student
actually visited. Failed student episodes were authorized only as corrective
proposal evidence, never as competence. Combined training used 12,000 rows.
Both an 8-by-8 corrective model and a four-times-finer 16-by-16 model (554,888
parameters) failed the strict teacher-removed lift. The finer model improved
return to 2.54 but was still rejected.

This converts a vague failure into a specific scientific conclusion: compact
colour-grid behavior cloning is insufficient for contact-rich Franka
manipulation. The next learner needs object-centric spatial features, temporal
belief and a recurrent or action-chunked closed-loop policy, preferably with
iterated DAgger or diffusion-policy supervision.

## GR00T and Cosmos boundary

The official Isaac-GR00T repository and frozen Python environment were built,
and the public `nvidia/GR00T-N1.7-LIBERO` checkpoint was downloaded. Inference
failed closed because the checkpoint depends on gated
`nvidia/Cosmos-Reason2-2B` access. No unofficial substitute, guessed endpoint or
fabricated GR00T result was accepted.

Cosmos and GR00T remain proposal/teacher candidates. PhysX or later hardware
must remain outcome authority, and AION must retain competence after those
models are removed.

## Claim boundary and next experiment

The defensible claim is that AION now owns a simulator-disjoint, independently
scored embodied apprenticeship pipeline that can reconstruct one learned Isaac
skill after teacher removal, expose brittle transfer, learn from student-visited
failure states and reject impressive-looking neural challengers that do not
move the physical object.

This is not robust Franka manipulation, Cosmos mastery, robotics mastery, AGA
or AGI. The next paid cohort should begin only after a local replay gate proves
an object-centric recurrent/action-chunked policy. It must then beat cold on
unseen lift resets before stack, drawer, changed dynamics or Cosmos assistance
are authorized.

## Phase-bound episodic intelligence extension

A subsequent bounded cohort tested whether AION could retain manipulation as
functional experience rather than compress it prematurely into a neural
regressor. A 1.30-million-parameter recurrent visual policy was first trained
from the 12,000-row authority. It used full spatial convolutions, generic
label-free visual centroids, two-frame motion and a recurrent belief state. Its
temporal training loss reached 0.0132, yet the teacher-removed cube did not
move. The challenger was rejected, demonstrating again that representation
loss is not execution authority.

AION then compiled all verified states into a 4,627-dimensional spatial skill
memory. Unrestricted visual retrieval also failed: it selected plausible robot
states from the wrong phase of the manipulation. The resulting diagnosis was a
temporal-binding failure rather than a perception or tool failure.

The corrected v13 memory constrained retrieval to the same public action phase,
then used current RGB, previous RGB and bounded joint state to choose among 48
independent teacher/corrective episodes at every step. With the teacher absent,
v13 exactly reconstructed the source lift: 250/250 proposals, zero abstentions,
height 0.5377 m and return 81.73. On a new 12-seed sealed cohort it achieved
2/12 strict lifts against 0/12 cold. Mean return was 12.57 versus 0.76 and mean
maximum height was 0.1323 m versus 0.0550 m.

The 2/12 result is a meaningful improvement over the earlier 1/12 program-bank
champion, but remains below robust promotion quality. A second corrective
generation added 7,378 states visited by v13, expanding memory to 19,378
states. On a third disjoint seed cohort it regressed to 0/12. HexCore therefore
rejected v14 and retained v13 unchanged.

This establishes a cross-domain governance lesson under real PhysX outcomes:
more memory is not automatically more intelligence. Corrective evidence must
be routed by relevance and causal regime; indiscriminate accumulation can
destroy a useful local policy. The next manipulation learner should combine
phase binding with a learned relevance router, object-centric pretrained visual
embeddings and action-chunk/receding-horizon control. Further paid execution is
not justified until that selector passes replay and protected-memory tests
locally.

## Asymmetric visual apprenticeship and corrective rejection (v16)

The v13--v15 rejection chain localized the remaining fault more precisely than
"insufficient training": pixel-neighbour retrieval preserved actions but could
not reliably reconstruct the cube--goal geometry that makes those actions
relevant.  A new asymmetric learner has therefore been implemented.  During
private training only, PhysX object position and the commanded goal pose may be
retained as a ten-value auxiliary teaching target.  These labels are explicitly
marked `privileged_training_labels_quarantined` and are never passed to the
behaviour policy during collection.

The deployable student consumes only two RGB frames, 18 bounded joint values
and its own previous action.  A convolutional encoder predicts a normalized
object/goal belief, while a recurrent controller uses that inferred belief to
propose the next action.  The runtime API has no parameter for simulator
geometry.  Manifests containing any privileged runtime input fail closed;
weights and manifests are independently hash-bound; non-finite or
out-of-distribution proprioception causes abstention; recurrent state resets at
episode boundaries.

The funded experiment collected 60 independently reset episodes and 15,000
committed transitions.  The official teacher completed 55/60 strict lifts.
All 13,750 transitions from successful episodes entered the first private
student; the resulting capsule contained no teacher and no privileged runtime
channel.  Its source-disjoint physical probe scored 0/3, equal to cold, and was
rejected despite a final joint training loss of 0.1865.

AION then performed an asymmetric DAgger generation.  The failed student drove
20 new resets while the frozen teacher labelled the recovery action at all
5,000 student-visited states.  Object and goal geometry remained quarantined as
training-only auxiliary targets.  Retraining over 75 episodes and 18,750
transitions reduced joint loss to 0.1385 and slightly raised mean return from
0.7675 cold to 0.8576, but still achieved 0/3 strict lifts.  It was rejected.

A final factorized challenger separated perception from procedural execution:
the learned visual belief selected one of 55 complete successful manipulation
programs, preserving coherent action phases instead of averaging actions.
This geometry-routed program memory also scored 0/3 and was rejected.  Across
the three teacher-removed cohorts, no candidate moved the cube above its
0.055 m resting height.

The result is a strong negative causal boundary, not the requested order-of-
magnitude competence gain.  Quarantined pose supervision, one DAgger recovery
generation and coherent episodic routing are insufficient with this small
camera encoder.  v13 remains the immutable bounded champion at 2/12 unseen
lifts.  Further paid runs require a genuinely stronger perception/action
substrate: explicit object masks or keypoints with measured geometry accuracy,
and an action-chunk or diffusion/transformer policy tested offline before
PhysX.  The focused integrity stack remains 10/10 and the GPU was stopped after
the immutable evidence bundle was synchronized.

## Explicit visual geometry and recovery chunks (v20--v24)

The next stage enforced the two offline gates before permitting further paid
PhysX execution. The first gate asked whether cube geometry could be recovered
from RGB on student-visited states disjoint from visual calibration. The second
asked whether the same state could select a coherent eight-to-sixteen-step
corrective chunk rather than an averaged one-step action.

The previous neural representation was rejected. Its best development result
reached 4.19 pixels but produced 10.52 cm object-position error, and it
collapsed to 18.25 pixels on student-visited recovery states. Investigation
also showed that the simulator's exact goal coordinate was not rendered as a
visible object. The runtime contract was corrected: the public mission supplies
``lift cube`` while vision locates the visible cube; hidden goal coordinates
are neither inferred nor passed at runtime.

AION learned a chromatic keypoint prototype only inside label-authorised
training crops, learned an affine camera correction on training resets, and
froze both before six unseen recovery episodes were scored. The detector
achieved 0.727-pixel mean error, 0.235-pixel median error and 0.932-pixel
90th-percentile error. This decisively passes the precommitted five-pixel mean
and seven-pixel tail bounds with zero privileged runtime inputs.

Four action-chunk challengers were then evaluated without reopening PhysX.
The coherent nearest-program memory improved 31.97% over repeating its first
action, but scored 0.4070 MAE. An explicit-state extra-trees program reduced
error to 0.35084 and retained 75.81% of target temporal variation, missing the
fixed 0.35000 gate by 0.00084. The result was not rounded or relaxed into a
pass. A smooth 277,568-parameter eight-step policy scored 0.3642. Finally,
adding 13,365 chunks from 55 successful teacher resets to 2,430 student-visited
recovery chunks regressed to 0.4740, showing that nominal success experience
can dilute recovery competence when routed indiscriminately.

Geometry Gate A is passed; recovery Action Gate B remains failed. No new paid
PhysX tournament was authorized and v13 remains the bounded physical champion
at 2/12 unseen lifts. The next justified acquisition is a small,
intervention-targeted recovery cohort around contact and post-contact boundary
states, followed by a fresh-reset evaluation never used for model choice.

## Targeted recovery acquisition and temporal routing (v25--v28)

The next paid acquisition was restricted to the failure boundary identified by
the offline gate rather than collecting another broad teacher cohort. Across 30
independent PhysX resets, AION executed bounded interventions at pre-grasp,
grasp-slip and lift-instability phases, then recorded the official teacher's
32-step recovery response. The resulting immutable cohort contains 7,500
transitions, 320 recovery states per regime and 30 explicit interventions per
regime. The teacher completed 28/30 strict lifts. Simulator geometry remained a
quarantined training label and was absent from every candidate at runtime.

The first regime-specific challenger produced an important rejection. It
classified the three constructed recovery regimes at 92.67% accuracy and
reduced eight-step chunk MAE to 0.27459, but a pooled recovery learner was
slightly better at 0.27015. The evidence therefore justified separating nominal
skill from recovery skill, but not forcing recovery into three independent
controllers.

A fresh train/development/sealed split by complete episode was then frozen:
episodes 0--17, 18--23 and 24--29 respectively. A new RGB keypoint learner
passed the sealed geometry gate at 1.638 pixels mean, 0.731 pixels median and
1.874 pixels p90. The pooled eight-step recovery learner passed Gate B at
0.26594 MAE, 44.51% better than repeated one-step control and 24.20% below the
previous best 0.35084 result, while preserving 67.87% of target temporal
variation.

Snapshot routing nevertheless failed: its balanced sealed accuracy was only
71.95%, and threshold calibration reached 77.96%. A temporal router using only
RGB keypoint motion, bounded proprioceptive deltas, AION's own executed-action
history and episode time then passed at 84.22% balanced accuracy, 80.21%
recovery recall and 88.23% nominal recall. These three offline gates authorized
exactly one fresh physical tournament.

The teacher-free tournament used resets 88107--88118, 250 actions per episode
and the immutable Isaac Lab container. Cold achieved 0/12 lifts. The protected
v13 policy retained 2/12 lifts, mean return 12.45 and mean maximum object height
0.1337 m. The v28 challenger achieved only 1/12 lifts, mean return 8.37 and mean
height 0.0987 m. It triggered recovery 108 times and committed 756 continuation
actions, placing 864/3,000 steps under recovery control. Offline recovery
competence was therefore real, but the full eight-step commitment was too
coarse: false or stale triggers interrupted nominal progress and erased the
gain.

HexCore rejected v28 and preserved v13. No threshold was softened and no
offline metric was allowed to override NVIDIA-owned physical outcomes. The
next architecture is now sharply constrained: nominal v13 control remains
protected; recovery is entered only after a measured progress/contact anomaly;
one or a short receding-horizon recovery action is executed; and the trigger is
re-evaluated before any continuation. The paid L40S was stopped after all
receipts were synchronized.

## Interruptible recovery and causal-onset revision (v29--v32)

The first interruptible controller implemented asymmetric switching cost,
conservative entry, aggressive exit, one-to-three-action bursts and mandatory
re-observation after every action. Its evaluation also exposed and corrected a
leakage hazard: the v28 router had been refitted on development episodes, so it
could not be reused to calibrate a new threshold on those same episodes. The
replacement router was trained only on episodes 0--17, calibrated on 18--23
and sealed on 24--29.

Under this honest split, recovery-state classification did not transfer. The
best conservative option achieved only 70% development precision and 44.44%
sealed precision. The paid probe remained blocked.

Failure analysis then identified a target error. The original label marked all
32 teacher steps following an intervention as recovery. This trained a
persistent occupancy classifier even though online control needs a sparse
causal event: the moment nominal behavior has failed and a corrective action is
valuable. A new onset learner used a four-step window after each intervention
but received no intervention flag at runtime. On six untouched episodes it
detected 6/6 onsets with 100% entry precision, zero false entries and only six
controlled rows. The development cohort produced the same 6/6 and zero-false
result.

The onset result was not sufficient for physical authorization. The inherited
general recovery chunk's first action scored 0.54944 MAE at the causal
boundary. A specialized onset-action learner reduced this by 32.37% to 0.37160
but missed the immutable 0.35000 gate. A protected-v13 residual corrector
improved on v13's boundary action by 45.62% but reached only 0.62561 absolute
MAE and was also rejected.

The resulting boundary is exact: AION can now identify when recovery should
begin without crowding out nominal control, but the small 30-event cohort does
not yet support a sufficiently accurate boundary action. No paid GPU probe was
opened. The next acquisition, if authorized, is therefore not another general
teacher sweep; it is a compact set of diverse causal-boundary interventions
whose only learning target is the first successful corrective action.

The Isaac runner now optionally commits a small visual-evidence archive from
selected steps of the primary arm. The next authorized cloud comparison can
therefore return six representative RGB frames from the robot's first episode
without enabling a live stream, privileged overlays or continuous recording.
