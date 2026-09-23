# AION Scientific Capability Battery

**Date:** 12 August 2026  
**Preserved run:** `20260812T173848Z`  
**Protocol hash:** `38f19f5846a901ad070baf611f8e8902835a74d320a466d0494c8c3701423127`  
**Overall result:** PASS (4/4 bounded capability tests)

## Purpose

This battery tests whether AION exhibits reproducible, causally attributable learning behaviour beyond a scripted response. It does not test consciousness, subjective experience, sentience or unrestricted general intelligence.

The protocol was frozen and hashed before execution. Each experiment used fresh isolated state and did not modify the live seven-day moonshot campaign. The timestamped evidence directory is immutable and the runner refuses to overwrite an existing run.

## Test A — Bounded causal responsiveness

AION received 24 balanced interventions, six for each possible target direction. A separate set of 24 negative controls changed an irrelevant tag while preserving the observable environment.

Results:

- Relevant intervention response: **24/24 correct**.
- Negative-control stability: **24/24 preserved the same observed tile**.
- State hashes changed under the negative controls, confirming that the test was not merely comparing identical inputs.
- Verdict: **PASS**.

Interpretation: within this bounded environment, AION's action selection changes for the relevant causal variable and remains stable under an irrelevant variable. This is stronger than a fixed output or string echo, but it is not evidence of subjective awareness.

## Test B — Active causal discovery and change detection

AION had to discover a hidden control rule through active experiments, retain a verified procedure, detect when the hidden rule changed and learn the replacement.

Results:

- Independent audit: **40 episodes** across two hidden modes.
- Hidden-mode identification: **97.5%**.
- Calibration success: **100%**.
- Mean discovery experiments: **2.3**; maximum: **4**.
- Mean experiment cost: **0.23**.
- Example posterior confidence for both learned rules: **0.9878** after two experiments.
- Each promoted procedure passed **200 verification rollouts at 99% success**.
- Rule change detected when predictive probability fell to **0.1098**, below the declared threshold.
- Restart test: both procedures remained verified with **zero relearning experiments**.
- Verdict: **PASS**.

Interpretation: AION can actively probe a bounded unknown system, form a useful causal model, notice predictive failure, relearn and retain the result across restart. It made one identification error in 40 audit episodes, so the result is strong but not perfect.

## Test C — Cross-domain structural transfer

AION learned an abstract causal structure and was then tested in three renamed unfamiliar domains. The test compared transferred learning against cold discovery.

Results:

- Mean reduction in structural discovery experiments: **73.33%**.
- Minimum reduction across domains: **73.33%**.
- Mean factor accuracy: **97.78%**; minimum: **96.67%**.
- Mean goal success: **93.33%**; minimum: **90%**.
- Mean runtime experiments: **3.89**.
- All transfer structures and all cold-control structures were correctly identified.
- Abstract skill promoted under the declared gates.
- Restart test retained the champion and domain graphs with **zero relearning experiments**.
- Verdict: **PASS**.

Interpretation: the useful result was not tied only to surface names. AION reused structural knowledge in unfamiliar renamed domains and required substantially fewer experiments than the cold control.

## Test D — Outcome-driven repair and evolution

AION's recorded failures were classified and used to produce a challenger. The challenger was compared with the retained champion on ten sealed worlds that were disjoint from development.

Results:

- Sealed evaluation: **10 worlds, 300 episodes**.
- Mean goal success: **85.67% to 93.33%** (**+7.67 percentage points**).
- Worst-family success: **73.33% to 83.33%** (**+10 points**).
- Factor accuracy: **87.33% to 96.33%** (**+9 points**).
- Experiment-budget failures: **135 to 76**.
- Belief errors: **28 to 8**.
- Planning errors: **30 to 11**.
- Execution-noise failures: **13 to 9**.
- Calibration errors: **18 to 7**.
- Challenger promoted under the frozen gates and retained after restart with zero relearning worlds.
- Failure queue contained **793** recorded outcomes.
- Verdict: **PASS**.

The improvement was not free:

- Mean experiments increased from **4.47 to 7.36** (**+64.7%**).
- Mean action cost increased from **1.519 to 2.095** (**+37.9%**).

Interpretation: AION converted outcome evidence into a more successful and robust method, particularly on the weakest family, but paid for that robustness with more investigation and action cost. Future work must improve efficiency rather than hiding this trade-off.

## Scientific verdict

This run provides reproducible evidence for four bounded capabilities:

1. Causal responsiveness with irrelevant-variable controls.
2. Active discovery, predictive change detection and restart retention.
3. Structural transfer to renamed unfamiliar domains with a cold comparison.
4. Failure-driven repair that improves sealed outcomes and survives restart.

It does **not** establish:

- consciousness, subjective experience or a proof of life;
- unrestricted AGI or competence outside the tested task families;
- external validity, because the task generators and scorer remain locally authored;
- a 10x claim, which remains closed;
- long-duration retention, which remains independently due on 15 August 2026.

## Limitations and next decisive tests

This is one locally executed preserved run. The strongest next evidence should be:

1. Repeat the frozen battery across independently generated seed packets.
2. Use an external administrator to provide hidden task packets and hold the answers.
3. Run matched full-AION, proposer-only, no-memory, no-repair and cold controls with identical proposer, tools and budgets.
4. Move from synthetic causal worlds to sealed real repositories, APIs, schema changes and operational missions.
5. Score the protected source-closed retention test after 15 August 2026 at 21:49 Madrid time.
6. Publish both gains and costs, including failures and non-promotions.

## Evidence locations

- Frozen protocol: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/protocol.json`
- Summary: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/summary.json`
- Bounded response: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/bounded_causal_responsiveness.json`
- Active discovery: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/active_causal_discovery.json`
- Transfer: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/cross_domain_transfer.json`
- Evolution: `results/immutable/aion_scientific_capability_battery/20260812T173848Z/outcome_driven_evolution.json`
- Reproducible runner: `scripts/aion_scientific_capability_battery.py`

No live learner scores were changed by this battery, and no claim was self-promoted from these results.
