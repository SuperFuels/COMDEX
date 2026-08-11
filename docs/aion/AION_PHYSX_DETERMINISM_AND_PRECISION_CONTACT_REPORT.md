# AION PhysX Determinism and Precision-Contact Reconstruction

## Result

Two paid experiments produced one controller rejection and one more important
evaluation-authority rejection. A uniformly wider search and its coarse-to-fine
successor did not improve lift success. More importantly, identical frozen
controllers did not reconstruct identical PhysX trajectories across independent
container starts, despite explicit deterministic rendering, seeded environment
construction, global RNG binding and enhanced PhysX determinism.

No end-to-end manipulation procedure is promoted. Protected v13 remains the
historical cloud champion, but further one-shot comparisons are suspended until
the authority supplies a fresh independent world per arm/episode or uses a
precommitted replicated statistical design.

## Search experiments

The first matched experiment falsified uniform radius expansion:

| Controller | Lifts | Mean return |
|---|---:|---:|
| Retained 15 mm | 2/6 | 14.037160 |
| Challenger 30 mm | 1/6 | 9.361190 |

The complementary episode outcomes motivated a precommitted coarse-to-fine
controller: preserve the complete 15 mm cardinal cross, then expand to 30 mm.
It failed its explicit 3/6 development gate:

| Controller | Lifts | Mean return |
|---|---:|---:|
| Retained 15 mm | 1/6 | 6.386455 |
| Coarse-to-fine | 0/6 | 2.096912 |

The successor is rejected and no sealed tournament is authorized.

## Reproducibility diagnosis

The retained arm changed from 2/6 to 1/6 under the same nominal seed. AION then
constructed a fail-closed determinism authority that:

- seeds Python, NumPy, Torch CPU/CUDA and Warp;
- sets the seed before environment construction;
- disables cuDNN benchmarking and requires deterministic Torch algorithms;
- requests deterministic Isaac RTX rendering;
- enables enhanced PhysX determinism;
- records per-episode initial observation hashes; and
- compares full observation, action and outcome commitment chains.

Two independent container starts used the same frozen policy, image, GPU,
environment and seed. The first episode's initial observation hash matched
exactly. Later reset images, returns and all three trajectory chains differed.
The audit therefore failed. Equal lift counts would not have been sufficient:
the complete causal executions were not reconstructions of one another.

The likely boundary is sequential world reuse: later episodes and comparison
arms inherit solver/render history even when `reset(seed=...)` is called. The
existing runner executes arms sequentially in one world, so its
`matched_same_process` label is weaker than true matched initial conditions.

## Precision-contact successor

Code inspection exposed a separate mechanical error. The controller could
advance from approach into finger closure while as far as 32--35 mm from the
contact target. That tolerance is larger than the relevant grasp basin.

The offline successor now enforces:

| Phase | Old tolerance/step | New tolerance/step |
|---|---:|---:|
| Open-hand precontact | 32 mm / up to 25 mm | 8 mm / up to 8 mm |
| Closing/contact | 35 mm / up to 25 mm | 5 mm / up to 3 mm |
| Test lift | 45 mm / up to 25 mm | 20 mm / up to 6 mm |

This change preserves RGB, bounded proprioception and fingertip touch as the
only runtime observations. It does not receive object pose, reward, contact
geometry or teacher actions. The code passes its local property tests but is not
credited with PhysX competence.

## Next execution contract

Before another policy tournament, the evaluator must provide one of:

1. a fresh reconstructed environment for every arm and episode, with exact
   initial observation hashes; or
2. a counterbalanced, multi-repeat statistical tournament with confidence
   bounds that remain positive under process-level variance.

Only then may the precision-contact successor face the retained controller.
This prevents further cloud expenditure on noisy 1/12 versus 2/12 comparisons
that cannot reliably identify the better intelligence.

Both NVIDIA instances were stopped after evidence retrieval.
