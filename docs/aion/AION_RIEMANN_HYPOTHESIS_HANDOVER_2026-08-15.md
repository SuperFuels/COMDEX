# AION Riemann Hypothesis Programme — Continuation Handover

**Prepared:** 15 August 2026  
**Scope:** Riemann Hypothesis work only  
**Repository:** `/Users/kevinrobinson/dev/COMDEX`  
**Current status:** Trusted laboratory foundation built; one paid matched experiment completed; no new RH mathematics established

## 1. Executive handover

This work created a small, isolated Riemann Hypothesis research laboratory around Lean 4 and Mathlib. Its purpose is not to let an AI announce that it has solved RH. Its purpose is to make AION acquire, reconstruct, repair and retain mathematical proofs under a strict machine-checking authority.

The laboratory successfully compiles established zeta-function results and rejects incomplete Lean proofs. A fixture-based smoke test also proves that the surrounding experiment machinery can record source-closed reconstruction and compiler-guided repair without falsely labelling these as new mathematics.

One paid GPT-4.1 matched experiment was subsequently completed. It did **not** demonstrate an AION advantage:

| Arm | Lean-accepted tasks | Tasks attempted |
|---|---:|---:|
| Proposer alone | 0 | 3 |
| AION memory + repair | 1 | 3 |
| AION without memory | 1 | 3 |
| AION without repair | 1 | 3 |

Only the elementary `ζ(0)` reconstruction passed in the AION-labelled arms. The trivial-zero and right-half-plane non-vanishing tasks failed. The result is useful, but it is not yet a clean test of AION: the live harness represents “memory” as a prompt hint and “repair” as compiler diagnostics. It is not yet retrieving AION's durable verified memories or invoking its genuine repair and promotion machinery.

The immediate task is therefore **not another paid rerun**. The next AI must first make the experiment scientifically valid by wiring real AION memory and repair, reconciling the Lean theorem catalogue, and sealing held-out tasks.

## 2. Non-negotiable truth boundary

The following statements must remain explicit:

- AION has **not solved the Riemann Hypothesis**.
- No new theorem relevant to resolving RH has been established.
- Reproducing a Mathlib theorem is proof-system validation and competence evidence, not original mathematical progress.
- Numerical agreement, plots and zeros checked to a finite height do not prove RH.
- Model confidence, persuasive prose and self-awarded scores are not mathematical authority.
- A result counts only when the pinned Lean kernel accepts the complete source with no `sorry`, `admit`, local axiom or hidden placeholder.
- The factoring, prime-search and earlier Riemann visual-probe work is separate from this formal RH programme.
- Photon Algebra was deliberately excluded from the first laboratory because it was not necessary to test formal zeta-proof reconstruction.

## 3. Intended research programme

The intended governed loop is:

```text
conjecture or reconstruction task
    → proposer candidate
    → Lean verification
    → counterexample or compiler diagnostic
    → diagnosis
    → bounded repair
    → Lean verification
    → verified memory
    → source-closed delayed reconstruction
```

Success is meant to answer progressively stronger questions:

1. Can the system reproduce established zeta-function mathematics correctly?
2. Does AION's verified memory improve the same proposer's success, cost or number of attempts?
3. Does AION repair failed proof attempts better than an otherwise identical control?
4. Can it retain and reconstruct the method after sources close and time passes?
5. Can it formalise a genuine missing prerequisite or useful lemma without overstating the result?

Only after these are demonstrated should the programme approach a genuine RH bottleneck.

## 4. Work completed

### 4.1 Isolated Lean laboratory

The project pins a Lean toolchain and Mathlib dependency and contains a minimal namespace for verified RH-related work.

Established baseline theorems currently compile for:

- the value of the Riemann zeta function at zero;
- the family of trivial zeros at negative even integers;
- non-vanishing in the half-plane `Re(s) > 1`.

These are established results already available through Mathlib. They were selected to verify the end-to-end authority path.

### 4.2 Strict proof policy

The harness scans AION-authored Lean sources for prohibited incompleteness markers, including:

- `sorry`;
- `admit`;
- project-local `axiom` declarations.

The final authority is the Lean process return code and retained source hash—not an LLM judgement.

### 4.3 Dependency map

A preliminary dependency graph records the route through:

- complex analysis;
- Dirichlet series;
- analytic continuation;
- functional equation;
- Euler product;
- trivial zeros and zero symmetry;
- the critical strip;
- the critical line.

The critical line remains open. The selected initial prerequisite is the **critical strip**, where the objective is to reconstruct and formalise established mathematics before selecting any genuinely unresolved lemma.

### 4.4 Fixture-based smoke experiment

The local smoke harness uses fixed proof candidates to validate:

- Lean compilation;
- proof-policy enforcement;
- evidence hashing;
- source-closed fixture reconstruction;
- compiler-guided repair recording;
- explicit claim boundaries.

Its latest result is `PASS_TRUSTED_LAB_SMOKE_TEST`. This is a plumbing result only. It explicitly records that neither a live AION process nor a live proposer was invoked.

### 4.5 Paid live matched experiment

A live four-arm experiment was run with GPT-4.1 through the OpenAI Responses API. Each arm received the same three established theorem tasks and a maximum of two attempts per task.

Measured outcome:

- proposer alone: `0/3`;
- AION memory + repair: `1/3`;
- AION without memory: `1/3`;
- AION without repair: `1/3`;
- total provider tokens recorded across attempts: `5,449`;
- summed attempt time recorded: approximately `134.5 seconds`.

The accepted proof was the zeta-at-zero reconstruction using `riemannZeta_zero`. Other attempts failed with Lean syntax, binder, theorem-resolution or goal-shape errors.

This proves that a real provider call and a real Lean acceptance gate operated. It does **not** prove that AION improved GPT-4.1.

## 5. Current scientific problems

### 5.1 The live “memory” arm is not real AION memory

The current live harness adds a generic memory note to the prompt. It does not retrieve a sealed, verified method from AION's durable memory ledger. Consequently, the comparison cannot support a public claim about AION's memory architecture.

### 5.2 The live “repair” arm is only a compiler-feedback prompt

Attempt two receives the rejected proof and Lean diagnostic. That is a useful baseline, but it is not AION's full diagnosis, repair, consequence checking and promotion loop.

### 5.3 The theorem catalogue and generated source need reconciliation

The baseline Lean file can compile the selected established statements, while generated live candidates failed to resolve or correctly apply some of the same results. Before blaming proposer intelligence, check:

- exact imports;
- namespaces and qualified theorem names;
- binder placement in generated theorem declarations;
- the exact goal shape produced by each task template;
- whether the prompt exposes misleading theorem names or signatures.

### 5.4 Experiment state is inconsistent

`live_task_packet.json` still says `execution_status: not_run`, while live result files show that a paid run occurred. The focused test currently expects the stale `not_run` state. This must be corrected without rewriting or deleting the original result.

### 5.5 Tasks are not yet sufficiently sealed

The current tasks reproduce famous public theorems and expose substantial clues. They are suitable for plumbing but weak as evidence of retained mathematical competence. A stronger experiment needs held-out formulations, frozen hashes and source closure.

### 5.6 The RH work is uncommitted

At handover time, the RH laboratory, harnesses and focused test are untracked by Git. They are present locally but are not safely preserved in repository history. The next AI must not delete, overwrite or regenerate them from memory.

## 6. Authoritative file map

### Laboratory

- `research/riemann_lab/README.md` — scope, proof policy and claim boundary.
- `research/riemann_lab/lakefile.toml` — Lean project configuration.
- `research/riemann_lab/lean-toolchain` — pinned Lean toolchain.
- `research/riemann_lab/lake-manifest.json` — resolved dependencies.
- `research/riemann_lab/RiemannLab.lean` — laboratory root.
- `research/riemann_lab/RiemannLab/Tasks/EstablishedZeta.lean` — compiling established baseline theorems.
- `research/riemann_lab/CatalogProbe.lean` — theorem-name and catalogue probes.
- `research/riemann_lab/dependency_graph.json` — RH prerequisite graph and selected target.
- `research/riemann_lab/live_task_packet.json` — matched live-experiment contract; currently contains stale execution state.

### Harnesses and tests

- `scripts/aion_riemann_lab.py` — fixture-only trusted smoke harness.
- `scripts/aion_riemann_live_exam.py` — paid OpenAI/Lean matched-experiment harness.
- `backend/tests/test_aion_riemann_lab.py` — focused laboratory-policy tests; contains a stale assertion about live execution state.

### Evidence

- `results/riemann_lab/latest.json` — latest fixture smoke result.
- `results/riemann_lab/live_exam_latest.json` — latest paid live result.
- `results/riemann_lab/live_exam_20260814T213917Z.json` — timestamped immutable copy of that run.
- Other timestamped `riemann_lab_*.json` files — earlier smoke evidence.

### Older work outside this programme

The following may contain historical probes, but must not be silently merged into the trusted formal laboratory:

- `backend/tests/riemann_photon_driver.py`;
- `backend/tests/test_riemann_probe.py`;
- `backend/modules/codex/ops/execute_riemann.py`.

## 7. Exact takeover sequence

### Step 1 — Preserve and audit before changing anything

1. Read every file listed in Section 6.
2. Record the current hashes of the task packet, harnesses, Lean baseline and live result.
3. Check Git status and preserve all untracked RH files.
4. Do not rerun a paid experiment during this audit.

### Step 2 — Reconcile the local Lean authority path

1. Compile `EstablishedZeta.lean` with the pinned project.
2. Compile each generated task template locally using known-correct proof terms.
3. Fix imports, namespaces, binders and theorem signatures until all three templates accept their known-correct proof.
4. Add focused tests that fail if the baseline and live templates diverge again.

This step must complete without an API call.

### Step 3 — Correct experiment state without erasing history

1. Preserve the existing timestamped paid result unchanged.
2. Update the task packet with a truthful completed-run reference or create a new versioned packet for the next run.
3. Replace the stale `execution_status == not_run` test with assertions that validate the result reference, hashes, arms and claim boundary.

### Step 4 — Wire genuine AION mechanisms

The full-AION arm must retrieve only machine-verified, source-closed proof methods from the actual AION memory store. The no-memory arm must use the same proposer, task, tools and budget without that retrieval.

The full repair arm must use AION's diagnosis and repair record. The no-repair arm must not receive that mechanism. Compiler diagnostics can be made available as a separately named baseline so that “AION repair” is not confused with ordinary iterative prompting.

Log exactly which memory identifiers and repair records were supplied to each arm.

### Step 5 — Create a fair sealed task set

Use established mathematics—not RH itself—for the next comparison. Select several equivalent or prerequisite statements whose solutions can be independently Lean-verified, then:

- freeze statement and environment hashes;
- prevent answer text from entering the retained memory;
- use identical proposer version, temperature, tools and token/attempt budgets;
- include multiple tasks and more than one theorem family;
- precommit the scoring rule;
- keep a cold control;
- separate immediate reconstruction from delayed retention.

### Step 6 — Run one bounded comparison

Only after all local checks pass:

1. launch exactly one matched run;
2. save the process identifier or active execution session;
3. record model, resolved model version, calls, tokens, elapsed time and Lean diagnostics;
4. write an immutable timestamped result;
5. report every arm, including failures;
6. make no superiority claim unless the precommitted comparison supports it.

### Step 7 — Run delayed source-closed retention

At the precommitted boundary, give the arms equivalent reformulations without reopening the original source. Count only fresh Lean acceptance. This is the decisive test of AION's intended advantage.

### Step 8 — Advance toward meaningful RH work

If real memory and repair advantages are demonstrated, move to the selected `critical_strip` prerequisite:

1. map existing Mathlib coverage;
2. reproduce the established proof dependency chain;
3. identify a precise missing formalisation rather than an open-ended “solve RH” prompt;
4. formalise useful supporting lemmas;
5. distinguish clearly between a new formalisation of known mathematics and genuinely new mathematics;
6. require external mathematical review before any public research claim.

## 8. Stop conditions and operating discipline

The previous session lost substantial time to repeated setup commentary and edits that did not launch. The next AI must follow these rules:

- Never say a test is running unless a real process or execution session exists.
- Do not spend API credit until local Lean templates and focused tests pass.
- Do not repeatedly announce the same next step.
- If an edit fails, state the exact failure once, correct it, and verify locally.
- Use one bounded paid run, then stop and report.
- Do not mutate the frozen mission after seeing model failures.
- Do not turn a failed or tied result into a positive AION claim.
- Do not pursue consciousness, “proof of life” or self-awareness claims inside the RH evaluation.

## 9. What the next AI must understand

The most important architectural point is this:

> The opportunity is not to make an LLM speculate about RH. It is to test whether AION can turn formally verified mathematical experience into retained, repairable competence under source closure.

That requires a clean causal comparison. The same frontier proposer must face the same task and budget. Only verified memory and governed repair should differ. If the full AION arm then succeeds more often, uses fewer attempts, retains competence later or transfers to a harder prerequisite, the evidence belongs to the architecture rather than to a stronger underlying model.

The current laboratory is a credible foundation for that test. The current paid result is not yet that proof.

## 10. First bounded action for the new AI

The first action should be:

> Compile known-correct proofs through the exact live task templates, reconcile the theorem catalogue and imports, update the stale packet/test state, and produce a local verification report. Do not make a paid call.

After that report passes, wire actual AION memory retrieval and repair records. Only then prepare the next sealed comparison.

## 11. Final status at handover

| Claim | Status |
|---|---|
| Trusted Lean laboratory exists | **Yes** |
| Established zeta baseline compiles | **Yes** |
| Strict no-placeholder policy exists | **Yes** |
| Fixture smoke harness passes | **Yes** |
| Real paid provider experiment completed | **Yes** |
| Current result shows AION superiority | **No** |
| Live harness uses genuine AION memory | **No** |
| Live harness uses full AION repair loop | **No** |
| Source-closed delayed retention completed | **No** |
| New RH-relevant mathematics established | **No** |
| Riemann Hypothesis solved | **No** |

The programme is ready for a careful takeover, not for another immediate rerun.
