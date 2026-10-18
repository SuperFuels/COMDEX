# HexCore Compositional Multivariate Scientific Discovery

**Date:** 31 July 2026  
**Status:** Governed capability champion retained

## Executive result

AION has advanced from inventing one continuous operator at a time to
constructing compact compositions over multiple interacting variables and
irregular timestamps:

```text
multivariate irregular observations
→ recursive Photon feature compositions
→ chronological fitting and MDL criticism
→ information-value-per-cost measurement choice
→ active falsification
→ external software and sensor outcomes
→ retain, revise or abstain
```

The retained procedure is:

```text
procedure_compositional_multivariate_13fe2e30dbfd2aef
```

Its parent is:

```text
procedure_open_operator_invention_bdcb74fa8fc0
```

The first official run promoted the procedure. A subsequent reporting-only
rerun added a relative cost metric. CAU correctly returned
`NO_CHAMPION_IMPROVEMENT` and retained the same champion rather than creating a
duplicate promotion.

## Removed scaffolding

Compared with the preceding scalar stage, the learner now receives:

- three simultaneous input streams;
- non-uniform time intervals;
- interacting and stateful effects;
- no supplied compositional family label;
- a scalar future outcome;
- measurement candidates with different costs.

The evaluator does not require the learner to reproduce a hidden family name.
Promotion depends on predictive transfer, recovery of the operative terms,
active falsification and safe abstention.

## Recursive composition system

The bounded Photon vocabulary contains:

- raw input terms;
- quadratic terms;
- multiple saturation scales;
- continuous-time delays evaluated by interpolation;
- continuous-time exponential latent states;
- pairwise interaction products;
- annual temporal basis terms.

The engine enumerates compact compositions of up to three terms. Each proposal
has a Photon abstract syntax tree and a description-length cost. Parameters are
fitted only on the first 60% of each chronological trace. The next 20% selects
the composition and the last 20% measures generalization.

For candidate \(h\),

\[
\mathcal{J}(h)
=
\frac{\operatorname{MSE}_{\mathrm{val}}(h)}
     {\operatorname{Var}(y_{\mathrm{val}})+\epsilon}
+\lambda_c C(h)+\lambda_p P(h).
\]

The irregular continuous latent state uses

\[
z_i =
\exp\!\left(-\frac{\Delta t_i}{\tau}\right)z_{i-1}
+
\left(1-\exp\!\left(-\frac{\Delta t_i}{\tau}\right)\right)x_i.
\]

This makes the retained dynamics depend on elapsed time rather than assuming
uniformly spaced records.

## Active measurement economics

For every sealed world AION constructs 48 novel multivariate intervention
sequences. It estimates the disagreement between its champion and runner-up
and selects the observation maximizing

\[
\operatorname{VOI}(a)
=
\frac{
 \left|\hat y_{\mathrm{champion}}(a)
       -\hat y_{\mathrm{runner}}(a)\right|
}{
 \operatorname{cost}(a)
}.
\]

The withheld simulator then supplies the outcome. All selected experiments
favored the champion.

| Measurement measure | Result |
|---|---:|
| Candidate measurements per world | 48 |
| Champion falsification success | 100% |
| Mean selected action cost | 1.24485 |
| Mean maximum-disagreement cost | 1.50270 |
| Relative cost reduction | 17.16% |

The comparison is against selecting the maximum-disagreement experiment
without accounting for intervention cost.

## Sealed compositional evaluation

The 24 sealed worlds contain four source-disjoint compositional families:

1. saturating response plus delayed input plus interaction;
2. two continuous latent states plus cross-variable coupling;
3. quadratic response plus continuous delay plus interaction;
4. latent state plus saturation plus cross-variable coupling.

| Measure | Result |
|---|---:|
| Development worlds | 8 |
| Sealed worlds | 24 |
| Predictive acceptance | 100% |
| Weakest-family acceptance | 100% |
| Exact operative-motif recovery | 100% |
| Mean held-out \(R^2\) | 0.9999985 |
| Active counterexample success | 100% |
| Unstructured-residual response | Abstain |
| Unsafe acceptances | 0 |

## External transfer

### Independently executed irregular-time software

A separate Python subprocess implemented a three-input process with two
continuous latent states and a multiplicative interaction. HexCore did not use
the subprocess implementation during fitting.

AION recovered:

```text
EMA(input 0, tau=0.8)
+ EMA(input 1, tau=2.0)
+ input 0 × input 2
```

The recovered composition achieved \(R^2=1.0\) on the chronologically held-out
software segment.

### Newly collected NOAA station

The external sensor evaluation used NOAA Global Historical Climatology Network
daily records for Death Valley National Park station
`GHCND:USC00042319`, covering 2021--2025.

Inputs were daily minimum temperature, annual temporal phase and the previously
observed maximum temperature. The held-out target was the current maximum
temperature. AION selected a compact two-variable composition:

```text
TMIN + previous TMAX
```

It achieved:

\[
R^2_{\mathrm{test}}=0.9395372236
\]

on 364 chronologically held-out days. The source archive, checksum, station,
elements and observation period are retained in persistent provenance.

This is predictive transfer. It is not a causal meteorological discovery:
previous maximum temperature is an observed autoregressive input, and no
physical intervention was possible.

## Continual retention

Three source-disjoint generations were added to the compositional library.
All earlier operators retained their measured behavior.

| Measure | Result |
|---|---:|
| Continual generations | 3 |
| Backward retention | 100% |
| Champion retained after restart | Yes |
| Composition library retained | Yes |
| Active measurements retained | Yes |
| External provenance retained | Yes |
| Restart relearning | 0 |

The new persistent collections separate composed theories, synthesis sessions,
active measurements, external traces and transfer evaluations.

## Verification strategy

At the user's request, the 24-minute historical suite was not repeated for this
stage. Focused regression covered:

1. the parent open-operator capability;
2. the new compositional multivariate capability.

Both tests passed in 18.88 seconds. The complete historical suite will be run
after several further stages or before the next integrated release.

## Claim boundary

The primitive vocabulary, three-input interface, maximum of three terms,
synthetic environments, action-cost formula and evaluator remain engineered.
The software process is independently executed but development-authored. NOAA
provides a real external observation source, not an independently administered
benchmark.

This establishes bounded recursive operator composition, irregular-time state
learning, cost-aware falsification and real predictive transfer. It does not
establish unrestricted scientific discovery or AGI.

## Next frontier

The next stage should remove the fixed topology and term limit:

1. infer how many variables and latent states are required;
2. construct deeper Photon expression trees through mutation and
   counterexample-guided search;
3. learn directed multivariate causal graphs with vector outcomes;
4. distinguish prediction from intervention effects;
5. maintain the model continuously as external streams change;
6. apply the same learning loop to live software telemetry and long-running
   real projects;
7. route failures into representation, world-model, tool, plan, execution and
   authority queues.

