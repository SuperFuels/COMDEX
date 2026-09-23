# HexCore Cross-Domain Causal Abstraction — Phase 7 Report

Date: 28 July 2026

## Claim boundary

This phase demonstrates transfer of a fixed causal-operator procedure across
three generated symbol families and two bounded graph shapes. No dictionary
mapping new names to causal roles was supplied. The causal operator grammar
remained fixed. The result is not unrestricted cross-domain intelligence.

The experiment-count comparison uses a declared fixed-budget cold-start
baseline: 720 structural observations per domain versus 192 for the transferred
procedure. It establishes success at a lower budget, not the mathematically
minimal number of observations a separately optimized cold learner might need.

## Transferred knowledge

AION was allowed to retain only the following abstract procedure:

1. enumerate action-history motifs;
2. construct the minimum adequate latent graph;
3. probe by expected information gain;
4. intervene toward a learned goal pattern;
5. execute the goal and verify the outcome.

Names such as actions, signals, domains, and goals were not retained as role
mappings. Each new domain had to establish those mappings through execution and
held-out prediction.

## New domain families

### Aster Lock

- one hidden factor;
- new signal `aura`;
- new intervention `invert`;
- new probe `listen`;
- new goal action `seal`;
- required hidden pattern: `(1)`.

### Reef Gate

- two independent hidden factors;
- new signals `tide_mark` and `salt_mark`;
- new interventions `turn_tide` and `turn_salt`;
- new probes `sample_tide` and `sample_salt`;
- new goal action `release`;
- conjunctive goal pattern: `(1,1)`.

### Orbital Latch

- two independent hidden factors;
- new signals `phase_echo` and `spin_echo`;
- new interventions `phase_kick` and `spin_kick`;
- new probes `phase_scan` and `spin_scan`;
- new goal action `dock`;
- mixed goal pattern: `(1,0)`.

The third domain required a different goal topology from the Phase 6 all-active
condition. Goal patterns are now part of the constructed graph rather than a
hard-coded planning assumption.

## Structure-learning results

Both the 720-observation cold baseline and the 192-observation transferred
procedure recovered the correct structure in all three domains.

| Domain | Factors | Cold observations | Transfer observations | Reduction |
|---|---:|---:|---:|---:|
| Aster Lock | 1 | 720 | 192 | 73.33% |
| Reef Gate | 2 | 720 | 192 | 73.33% |
| Orbital Latch | 2 | 720 | 192 | 73.33% |

The mean and minimum structural-experiment reduction were both 73.33%.
Transferred graphs were separately tested on twenty larger external held-out
episodes that were not used for construction or internal calibration.

The small internal transfer split used a provisional +0.01 multi-factor
likelihood gate rather than weakening the global Phase 6 +0.05 gate. Promotion
additionally required exact role recovery and successful external held-out
planning. This prevents a small internal split from rejecting a correct
low-data graph while retaining independent operational authority.

## Independent planning audit

Each transferred graph was evaluated across sixty new stochastic worlds:

| Domain | Hidden-state accuracy | Goal success | Mean runtime probes |
|---|---:|---:|---:|
| Aster Lock | 100.00% | 96.67% | 2.53 |
| Reef Gate | 96.67% | 90.00% | 4.57 |
| Orbital Latch | 93.33% | 93.33% | 4.60 |

Aggregate results:

- mean hidden-state accuracy: 96.67%;
- minimum domain hidden-state accuracy: 93.33%;
- mean goal success: 93.33%;
- minimum domain goal success: 90.00%;
- mean runtime experiments: 3.90.

Every domain passed its absolute structure, factor-accuracy, and goal-success
gates.

## Skill learning and restart

The verified abstract procedure was submitted to HexCore skill memory as a
challenger. CAU approved promotion only after all structures were correct,
every domain exceeded 50% structural data reduction, and aggregate goal success
exceeded 90%.

The promoted champion is:

`procedure_cross_domain_causal_d9e49d451e25`

After process restart:

- the abstract skill champion remained available;
- all three environment-specific graphs remained available;
- no structural relearning experiments were required.

The outcome and source graph identifiers are retained in the persistent
promotion ledger.

## Interpretation

This is the first explicit connection between HexCore world learning and skill
learning. AION did not merely retain three solved graphs. It retained a reusable
method for learning new graphs, demonstrated that the method operated under new
symbols and goal patterns, and promoted it only after measured cross-domain
benefit.

## Remaining development

The next high-value stage should remove more scaffolding:

1. sample domain structures rather than defining three fixed families;
2. include three or more latent factors and non-binary variables;
3. learn operator grammar extensions rather than keeping the grammar fixed;
4. compare transfer against a cold learner optimized for the same stopping
   rule, not only a fixed observation budget;
5. introduce structural changes during a planning episode;
6. use outcome memory to mutate experiment policies and challenge the current
   abstract skill;
7. connect natural-language descriptions to symbol proposals while preserving
   simulator and CAU authority.

