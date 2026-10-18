# HexCore Stochastic Multi-Latent Discovery and Planning — Phase 6 Report

Date: 28 July 2026

## Claim boundary

This phase demonstrates bounded discovery and operational use of two binary
hidden factors under noisy observation. AION receives the observable variable
and action vocabularies plus a complexity-limited structural grammar. Hidden
factor labels and candidate graphs are not supplied. This is not unrestricted
world modelling or general intelligence.

## Research question

The previous phase established that AION could construct and revise one
deterministic hidden state. Phase 6 asks whether the same governed architecture
can:

- prefer two independent hidden factors over an underpowered one-factor model;
- discover noisy readout and intervention relationships;
- maintain probability over the joint hidden state;
- select experiments using expected information gain minus cost;
- plan actions from the inferred hidden state;
- remain calibrated under observation noise;
- retain and reuse the learned structure after restart.

## Environment

The bounded audit environment is a two-factor vault. The hidden factors are
never returned to AION. Five actions are available:

- `inspect_left` and `inspect_right` expose noisy signals;
- `flip_left` and `flip_right` intervene on the hidden factors;
- `open` succeeds only when both hidden factors are active.

Probe reliability is 90%; goal execution reliability is 98%. Initial hidden
states are random and unknown. Training structure was learned from 50 episodes
of 15 actions chosen through balanced ordered-pair experiment coverage.
Complete held-out episodes were excluded from graph construction.

## Constructed graph

AION selected a ten-complexity, two-factor graph. Latent factor numbering is
arbitrary, as expected, but the discovered causal roles were correct:

- `flip_left` changes the factor read by `inspect_left`;
- `flip_right` changes the factor read by `inspect_right`;
- the two noisy signals expose different factors;
- `open` depends jointly on both factors.

The two-factor graph exceeded the best generated one-factor control by
0.120934 normalized held-out log-likelihood. The minimum required gain was
0.05. The graph therefore passed both predictive and minimum-description
gates.

## Active belief and experiment selection

At runtime AION begins with a uniform posterior over four possible joint hidden
states. For every available probe it computes expected posterior entropy and
subtracts experiment cost. It executes the highest-utility probe, updates the
joint posterior from the noisy observation, and stops when both marginal
factor beliefs cross the confidence gate or the experiment budget is exhausted.

The resulting belief is then converted into a graph-informed plan:

- factors believed inactive are changed through their learned interventions;
- belief is updated through the deterministic intervention transition;
- the learned joint goal action is executed.

This separates structural learning, belief updating, experiment choice, and
goal planning while retaining an inspectable causal trace.

## Independent audit

The unchanged learner was evaluated across 100 new random worlds:

| Measure | Result |
|---|---:|
| Joint hidden-state accuracy | 95.00% |
| Goal success | 93.00% |
| Average confidence | 97.63% |
| Absolute calibration error | 2.63% |
| Average experiments | 4.48 |
| Maximum experiments | 6 |

Every selected diagnostic action had positive expected information gain.
All absolute operational gates passed:

- correct selection of a two-factor structure;
- positive held-out advantage over the one-factor control;
- active information-gain experiment selection;
- at least 90% hidden-state accuracy;
- at most 10% calibration error;
- at most six experiments on average;
- at least 90% goal success;
- restart retention without structural relearning.

## Persistence and governance

The accepted causal graph and both latent-variable records were committed
atomically through CAU. After process restart, AION restored the two-factor
graph, completed a fresh investigation and achieved the goal without any
structural relearning.

All 21 HexCore persistent-learning, governed-runtime, and conversation
governance tests pass.

## Interpretation

This is stronger than fitting a hidden label. AION constructed a compact
explanation of two unobservable causes, represented uncertainty over their
joint state, chose actions for information rather than immediate reward, and
used the resulting beliefs to form an effective plan.

The result remains bounded. Factor cardinality, grammar, observable variables,
and available actions were provided. The next material test is transfer beyond
this fixed vocabulary and grammar.

## Next development

The highest-value next stage is cross-domain causal abstraction:

1. generate environments with new variable names, action names, graph shapes,
   factor counts, and goal conditions;
2. separate generic causal operators from environment-specific symbols;
3. learn reusable experiment and planning procedures;
4. require positive transfer to unseen graph families with fewer experiments;
5. connect graph outcomes to HexCore skill memory and challenger promotion;
6. introduce stochastic structural change and posterior model averaging;
7. allow language providers to propose symbol mappings while execution remains
   the authority for correctness.

