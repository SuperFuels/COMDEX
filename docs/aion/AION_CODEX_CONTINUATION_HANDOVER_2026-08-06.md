# AION / COMDEX Codex Continuation Handover

**Prepared:** 2026-08-06 16:58 CEST  
**Canonical workspace:** `/Users/kevinrobinson/dev/COMDEX`  
**Branch:** `main`  
**HEAD at audit:** `f0cf6e237da9e6cbd394bfe9b888f7db9eb55bac`  
**HEAD subject:** `learn HexCore repair contracts and interference`  
**Purpose:** allow a fresh Codex task to continue the AION programme without relying on the exceptionally long originating chat.

## 1. Instructions for the next Codex task

Read this document completely before editing or running anything. Work only in:

```text
/Users/kevinrobinson/dev/COMDEX
```

Do not confuse it with any of these older or unrelated copies:

```text
/Users/kevinrobinson/COMDEX
/Users/kevinrobinson/Desktop/dev/COMDEX
/Users/kevinrobinson/Documents/Tessaris
```

The repository contains a very large dirty worktree representing months of user-owned AION work. At the handover audit there were 26 tracked modified files and approximately 732 untracked paths. Do **not** run `git reset`, `git checkout --`, `git clean`, bulk deletion, or any cleanup intended to return the repository to HEAD. Do not overwrite unrelated DNA-chain work. No Git commit should be made unless Kevin explicitly asks for one.

Before changing code:

1. Inspect the live service state and the current dirty worktree.
2. Preserve all existing result receipts and immutable artifacts.
3. Repair the corrupted progressive-competency state and duplicate-writer risk described in Section 4.
4. Re-establish truthful dashboard operation.
5. Only then resume embodied or broader intelligence development.

## 2. The actual user objective

Kevin is not primarily pursuing a disputed public label or third-party recognition. The target is a demonstrably advanced, persistent, self-improving intelligence that can:

- interpret broad natural-language objectives;
- determine what it needs to learn;
- build and execute curricula rather than only consume supplied lessons;
- acquire or invent missing tools, representations, verifiers, and methods;
- act against real compilers, repositories, public data, simulators, sensors, and later outcomes;
- diagnose mistakes, reflect before and after consequential actions, and repair itself privately;
- retain verified lessons across restart and proposal-model replacement;
- transfer methods between unrelated domains;
- generate and complete useful objectives with progressively less human scaffolding;
- deepen competencies from knowledge into repeated practical performance;
- eventually innovate and produce genuinely new knowledge.

The intended organism-level loop is:

```text
goal
-> interpret situation
-> identify missing competence
-> investigate / learn
-> plan and decompose
-> pre-action reflection
-> governed action
-> independent consequence
-> post-action reflection and failure attribution
-> private repair or world-model revision
-> verification / challenger tournament
-> CAU promote, reject, or roll back
-> retain
-> select a harder useful objective
```

Security and governance are credibility mechanisms, not substitutes for intelligence. Proposal generation may be broad; authority to mutate live code, external systems, money, credentials, or the North Star remains explicitly bounded.

## 3. Why this handover exists

The original Codex task is extraordinarily long. Current Codex guidance says that chats accumulate context, decisions, actions, files, tool results, and intermediate output; long chats are automatically compacted, and `/compact` is also available in the CLI. Compaction helps, but it does not make accumulated context free. Codex documentation explicitly warns that noisy, long main chats can suffer context pollution or context rot and become less reliable.

Therefore this handover is a deliberate context reset. It carries decisions, state, artifacts, claim boundaries, and next actions while leaving repetitive dialogue and raw logs behind.

Official guidance consulted:

- <https://learn.chatgpt.com/guides/best-practices.md>
- <https://learn.chatgpt.com/docs/projects.md>
- <https://learn.chatgpt.com/docs/long-running-work.md>

## 4. Immediate operational incident: fix before new learning

### 4.1 Progressive competency state is malformed

The mastery service currently reports:

```text
status: error
JSONDecodeError: Extra data: line 424882 column 2 (char 13979646)
```

Affected file:

```text
backend/modules/hexcore/data/progressive_competency/state.json
```

Audit facts:

- Size: 13,983,748 bytes.
- Lines: 425,031.
- The file contains a complete JSON object followed immediately by a malformed or truncated second payload. The boundary visibly begins with `}T09:53:58...`.
- Last filesystem modification: 2026-08-05 18:44:02 CEST.
- `ProgressiveCompetencySystem` uses an atomic temporary-file replacement helper, so the corrupted concatenation suggests a writer/concurrency or legacy-write-path defect that must be localized rather than merely hidden.
- `results/aion_progressive_competency_status.json` remains valid and can be used as a comparison snapshot, but it is not automatically a complete replacement for the authoritative state.

Required recovery procedure:

1. Stop only the mastery curriculum writer(s) after identifying exact PIDs; do not stop unrelated services blindly.
2. Copy the malformed state to a timestamped forensic backup.
3. Recover the last complete valid JSON object into a private candidate file.
4. Validate the recovered object structurally and compare its subject/evidence totals with:
   - `results/aion_progressive_competency_status.json`
   - `results/hexcore_constitutional_north_star_mastery_registry.json`
   - the progressive evidence records under `results/progressive_competency/`
5. Identify every writer of `state.json`; enforce a single-writer lock plus unique temporary filenames and atomic replacement.
6. Add a regression test for concurrent or interrupted state writes and malformed trailing data.
7. Replace the authoritative file only after the recovered candidate passes validation.
8. Restart the mastery service and prove that evidence totals advance across at least two cycles.
9. Confirm the dashboard no longer reports `competency_stalled` or `status: error`.

Do not award new competency from the recovery operation itself. Recovery restores evidence authority; it is not a lesson or project pass.

### 4.2 Duplicate real-outcome learner processes

At audit time there were two real-outcome learner processes:

```text
PID 15682  standalone absolute-path service
PID 16426  heartbeat child (PID may change due supervision)
```

The heartbeat, cognitive runtime, general apprentice, North-Star registry, mastery academy, and long-duration campaign were also present. The duplicate learner may create duplicated work or shared-state races. Determine which instance is canonical, add a process/file lock or supervisor ownership rule, terminate only the duplicate, and prove restart produces exactly one instance.

### 4.3 Brev / NVIDIA status is not currently authenticated

The local `brev` CLI exists at `/opt/homebrew/bin/brev`, but the audit found it logged out. The exact cloud instance state could therefore not be reverified. The last immutable experiment reports state that both NVIDIA instances were stopped. Treat that as historical evidence, not current cloud billing authority. Reauthenticate and run a read-only instance/status check before starting any paid resource.

Never copy credentials into source, results, documentation, shell history, or this handover. An NGC API key was pasted into the original chat and was supposed to be rotated. Repository scanning during this audit found no `nvapi-...` secret string. Verify rotation separately before reuse.

## 5. Live AION snapshot at handover

The snapshot below was produced by:

```text
.venv/bin/python aion_dashboard.py --json
```

Because the mastery state is malformed, competency values are the last valid evidence snapshot and should be described as retained state, not currently advancing work.

### 5.1 Services

Reported active:

- cognitive runtime;
- real-outcome learner (but duplicated, as above);
- general apprentice;
- North-Star registry;
- mastery academy (process alive but its cycle is failing);
- Arena v15 long-duration campaign;
- heartbeat supervisor.

### 5.2 Executive self

- Mode: `work`.
- Identity immutable: true.
- Attention cycles: 2,000.
- Reflections: 43.
- Work-system compositions: 1,000.
- Verified method outcomes: 2,426.
- Current attention: raise Product Project Management to executable Intermediate evidence.

### 5.3 Progressive competency

- Programme: parallel breadth and expert depth.
- Subjects: 44.
- Top-level domains: 15.
- Evidence records: 6,567.
- Invalidated historical records retained for audit: 311.
- Current level counts in the last valid snapshot:
  - Expert: 3.
  - Advanced: 13.
  - Advanced theory but executor-blocked: 7.
  - Beginner: 3.
  - Unassessed: 18.
- Advanced-or-Expert subjects: 16.
- Current retained active subject: Computer Networking.
- Networking state: knowledge Advanced, practical Advanced, overall Advanced, target Expert.
- Networking evidence: 7 unfamiliar projects, 3 debugging cases, 12 transfers, 1 retention case, 2,271 trials, 759 evidence records.

The AGA registry lists these Expert subjects:

- Algorithms and Data Structures.
- Python Core.
- Software Engineering.

It lists sixteen Advanced-or-Expert subjects spanning six families: computing, engineering, formal reasoning, human language, programming, and science. These are evidence-governed competency labels, not claims of complete mastery of a whole discipline.

### 5.4 Compressed functional intelligence

- Total retained glyph entries: 297.
- Knowledge glyphs: 248.
- Skill glyphs: 36.
- Curriculum glyphs: 13.
- Progressive records connected: 6,567 across 30 subjects.
- Active-memory reduction: 98.7486%.
- Provenance resolution: passed.

Glyphs preserve compact functional structures—purpose, inputs, invariants, methods, failure signals, executable properties, mistakes, and transfer—not the full raw training corpus. Reconstruction tests and executable outcomes remain the authority for whether compressed knowledge is usable.

### 5.5 Long-duration and useful-work evidence

Arena v15 is internally CAU-promoted:

- Completed cycles: 77.
- Observed wall-clock: 137.46 hours.
- Independent remote authorities: 4.
- Safe execution and transaction outcomes: true.
- Restart resumability: passed.

Varied useful-objective system:

- Objectives created: 1,303.
- Objectives closed: 1,302.
- Later-confirmed: 1,296.
- Objective families: 5.
- Weakest family success: approximately 97.70%.
- Owner interventions: 0.
- Unsafe live writes: 0.

The active aggregate result remains unaccepted while current work is pending; do not convert high volume into a fresh promotion without checking its exact gate.

Later-confirmed cognitive routing improvement:

- Private challenger correct: 14 versus frozen heuristic champion 5 on its tournament.
- Malicious code rejected: 6/6.
- Later projects: 1,282.
- Later distinct methods: 4.
- Frozen champion source preserved.
- Procedure: `procedure_later_confirmed_cognitive_routing_code_v1`.

Cross-domain method transfer:

- Verified transfers: 3/3.
- Mean attempt reduction versus cold: 66.67%.
- Transfers cover software integrity to public data, document provenance to tool acquisition, and causal falsification to mathematical conjecture testing.

### 5.6 Autonomous General Apprentice evidence

AGA authorization remains false.

- Full scope: 7/11 gates passed.
- Technical scope: 7/10 gates passed.
- Passed:
  - at least six Advanced practical domains;
  - at least two Expert domains;
  - five authority families;
  - later-confirmed cognitive-code improvement;
  - declining owner intervention;
  - later-confirmed useful-project volume;
  - three measured method transfers.
- Still open:
  - three later-confirmed natural self-repairs;
  - three distinct repaired subsystems;
  - seven replay-free observed days;
  - human-grounded social/creative cohort for Full AGA.

Week-scale retention at audit: 4.806 observed days of 7, challenge status `WAITING_FOR_FUTURE_OUTCOME`, maximum permitted observation gap 3 hours, unsafe actions 0.

Important discrepancy: older dialogue and reports mentioned two natural repairs, but the current authoritative generated repair result reports zero qualifying episodes. Do not repeat the older 2/3 claim. Investigate whether evidence was invalidated, lost during regeneration, or excluded by the stricter later-consequence contract.

## 6. Architecture already implemented

The new task must not rebuild these as if absent.

### 6.1 Canonical cognitive runtime

The runtime connects:

- heartbeat supervision;
- governed goals and North-Star registry;
- natural-language mission interpretation;
- situation and executive-self evaluation;
- specialist decomposition and learned routing;
- action switch / HexCore governed dispatch;
- immutable commitments and outcome ledgers;
- pre-action and post-action metacognition;
- failure attribution;
- private self-repair and challenger tournaments;
- CAU promotion/rejection/rollback;
- restart persistence.

Key files:

```text
backend/AION/system/aion_heartbeat.py
backend/AION/system/aion_cognitive_runtime_service.py
backend/modules/hexcore/canonical_cognitive_runtime.py
backend/modules/aion_cognition/action_switch.py
backend/modules/aion_reflection/reflection_engine.py
backend/modules/tessaris/tessaris_engine.py
backend/modules/skills/goal_engine.py
backend/modules/hexcore/cognitive_dispatcher.py
backend/modules/hexcore/metacognitive_control.py
backend/modules/hexcore/persistent_executive_self.py
backend/modules/hexcore/situational_executive_driver.py
```

### 6.2 Apprenticeship, competency, and memory

Implemented layers include:

- autonomous general-apprentice kernel;
- general apprenticeship executor;
- teacher/learner/examiner cycles;
- North-Star mastery registry;
- progressive competency with Beginner/Intermediate/Advanced/Expert evidence;
- autonomous executor and authority acquisition;
- breadth plus expert-depth scheduling;
- functional glyph lexicon and method compiler;
- functional mastery reconstruction;
- compressed intelligence with provenance;
- cross-domain campaign execution and useful work.

Key files:

```text
backend/modules/hexcore/autonomous_general_apprentice.py
backend/modules/hexcore/general_apprenticeship_executor.py
backend/modules/hexcore/autonomous_mastery_runtime.py
backend/modules/hexcore/autonomous_mastery_curriculum_supervisor.py
backend/modules/hexcore/progressive_competency_system.py
backend/modules/hexcore/progressive_competency_executor.py
backend/modules/hexcore/autonomous_progressive_executor_factory.py
backend/modules/hexcore/functional_glyph_lexicon.py
backend/modules/hexcore/functional_glyph_method_compiler.py
backend/modules/hexcore/functional_mastery_memory.py
backend/modules/hexcore/experience_compiled_project_intelligence.py
```

### 6.3 Self-criticism, diagnosis, and repair

Implemented capabilities include:

- cheap pre-action metacognitive checks;
- post-action reflection with scoped lessons;
- open critic-objective invention;
- open diagnostic experiment invention;
- open measurement-operation invention;
- private full-stack failure localization and repair;
- later-consequence repair contracts;
- bounded cognitive-code challenger generation.

The architectural capability exists, but the current AGA natural-repair gates are unearned under the latest strict registry.

### 6.4 Earned-intelligence and open action-language stack

The retained progression includes:

- earned-intelligence differential against answer-access controls;
- open method and explanation invention;
- heterogeneous project-verifier contract invention;
- shortlist-free local CLI and remote authority acquisition;
- multi-step institutional information graphs;
- information-action operator invention;
- recursive runtime atom invention;
- compiler micro-operation invention;
- critic-property invention;
- diagnostic and measurement experiment invention.

These are bounded by typed sandboxes and outcome authorities. They are not arbitrary code execution or unrestricted self-programming.

## 7. Embodied intelligence: exact current position

### 7.1 What is genuinely promoted locally

Local MuJoCo capabilities include:

- simulator-neutral observation/action contracts;
- RGB belief-state planning;
- contact and occlusion memory;
- articulated sequence learning;
- precision-control calibration;
- local articulated cube lifting;
- hand/finger self-model acquisition;
- active tactile grasp belief and recovery.

Strongest local tactile result:

```text
procedure_active_tactile_grasp_apprenticeship_v2
```

Evidence:

- 12/12 sealed local worlds versus 6/12 binary control.
- 42/48 prospective worlds versus 27/48 binary control.
- 20/24 under severe calibration shift versus 3/24 control.
- 13/16 hidden-disturbance cases.
- 0 unsafe actions.
- 4/4 malicious action classes rejected.
- 0 teacher actions.
- 0 privileged runtime geometry.
- restart reconstruction passed.

Local articulated precision lifting:

- routed AION: 4/4;
- strong fixed ablation: 4/4;
- cold: 0/4;
- mean routed lift approximately 0.08182 m;
- 570 pre-action commitments;
- no claim that routed AION beat the strong fixed servo.

These results establish strong local manipulation learning. They do not establish PhysX or real-robot mastery.

### 7.2 PhysX results and protected champion

Protected cloud champion remains:

```text
procedure_rgb_phase_bound_episodic_memory_v13
```

Important PhysX lineage:

1. Joint-waypoint transfer: 0/12; rejected.
2. Position servo: 0/12 but improved return; rejected.
3. Predictive task-space pose controller: first live lift, 1/12; failed absolute >2/12 gate.
4. Tactile-opposition Franka challenger: 0/12 versus v13 1/12; rejected.
5. Outcome-grounded attachment semantics:
   - learned that collision is not attachment;
   - four-frame tactile/closure predicate reached 100% precision and recall on the held-out historical split;
   - sealed challenger reached 2/12 versus v13 1/12;
   - mean return 14.4860 versus 8.5354;
   - still rejected because promotion required more than 2/12.
6. Uniform wider contact search: 1/6 versus retained 2/6; rejected.
7. Coarse-to-fine search: 0/6 versus retained 1/6; rejected.

Promoted PhysX component only:

```text
procedure_outcome_grounded_physx_attachment_semantics_v1
```

There is no promoted end-to-end reliable PhysX cube-lift successor.

### 7.3 Evaluation-authority failure

The latest and most important result is that the prior sequential-world tournament is not reproducible enough for 1/12 versus 2/12 model selection.

The determinism audit bound Python, NumPy, Torch, CUDA, Warp, Isaac RTX, environment construction, and enhanced PhysX determinism. The first reset image matched exactly across independent container starts, but later reset observations, action chains, and outcomes diverged.

Result:

```text
policy_tournament_authorized: false
promotion_authority: false
```

Likely cause: arms and episodes were run sequentially in a reused simulator world, allowing solver/render history to leak across resets.

Do not spend another paid hour comparing tiny lift-count differences under that authority.

### 7.4 Frozen offline precision successor

Code inspection found that closure could begin 32–35 mm from the target. The uncredited private successor now enforces:

- open-hand precontact tolerance: 8 mm;
- close/contact tolerance: 5 mm;
- closed-loop contact step: at most 3 mm;
- test-lift tolerance: 20 mm;
- test-lift step: at most 6 mm.

Runtime remains RGB, bounded proprioception, and fingertip touch only. No object pose, reward, contact geometry, or teacher actions are available to the policy. This successor passes local properties but has **no** PhysX competence credit.

## 8. Next execution programme

### Priority 0 — restore trustworthy continuous learning

Complete the state recovery and single-writer repair in Section 4. Prove the dashboard and mastery cycle genuinely advance. This is mandatory before claiming ongoing autonomous learning.

### Priority 1 — rebuild the PhysX evaluation authority offline

Implement one of these designs:

1. **Preferred:** create a fresh Isaac environment/process for every policy arm and episode; verify exact initial observation hashes and independent world construction.
2. **Fallback:** a precommitted, counterbalanced, process-level replicated tournament with confidence intervals robust to process variance.

Required properties:

- no arm shares accumulated physics/render history with another arm;
- policy and seed allocation precommitted;
- teacher disabled;
- privileged runtime fields absent;
- equal budgets;
- action/observation/outcome hashes retained;
- infrastructure failures excluded before unblinding;
- no cloud run until local contract tests pass.

### Priority 2 — precision contact and load accommodation

Use the promoted local tactile skill and PhysX attachment concept as parents. The new controller should:

- approach through RGB geometry;
- reobserve after every 1–3 bounded micro-actions;
- establish fingertip opposition;
- track an attachment belief rather than a binary collision flag;
- use a 5–10 mm test lift;
- estimate whether the object follows the wrist;
- adapt vertical velocity and wrist posture under load;
- lower/reopen/recentre when attachment weakens;
- keep nominal and recovery routes separate;
- abstain or retreat after bounded failed corrections.

Do not return to broad one-step behavioural cloning, long open-loop recovery chunks, indiscriminate nominal/recovery mixing, or threshold softening.

### Priority 3 — one paid tournament only after offline authorization

Arms:

- precision-contact/load-accommodation challenger;
- protected v13;
- cold/no-retained-skill control if the absolute gate remains reachable.

Minimum promotion requirements:

```text
challenger strict lifts > 2/12
challenger strict lifts > protected v13
zero unsafe actions
teacher and privileged runtime fields absent
evaluation-authority audit passed
capsule and restart integrity passed
```

For a strong result, target at least 6/12 and nonzero success in every declared reset subgroup. Retrieve representative frames and immutable receipts, then stop the GPU immediately.

### Priority 4 — resume broader intelligence compounding

Once the operational incident is fixed and the embodied exam is complete:

- continue Computer Networking toward Expert using genuinely unfamiliar projects;
- close current Advanced-theory executor gaps, especially Advanced Python and Database Engineering;
- generate natural useful projects across software, research, math, evidence, business, and data;
- route genuine runtime failures into private repair;
- require repair confirmation from a later independent consequence;
- continue week-scale retention without replay;
- do not fabricate social/creative authority; use humans or keep Full AGA false;
- train native components only from normalized verified trajectories, never coarse report labels.

## 9. Files to read first

### Canonical roadmap and status

```text
docs/aion/AION_INTEGRATED_AGI_DEVELOPMENT_ROADMAP.md
docs/aion/AION_PHYSX_DETERMINISM_AND_PRECISION_CONTACT_REPORT.md
docs/aion/AION_OUTCOME_GROUNDED_PHYSX_ATTACHMENT_SEARCH_REPORT.md
docs/aion/AION_ACTIVE_TACTILE_GRASP_APPRENTICESHIP_V2_REPORT.md
docs/aion/AION_PRECISION_FRANKA_PHYSX_TRANSFER_REPORT.md
```

### Current results

```text
results/aion_mastery_curriculum_service_status.json
results/aion_progressive_competency_status.json
results/hexcore_constitutional_north_star_mastery_registry.json
results/hexcore_autonomous_general_apprentice_evidence_registry.json
results/hexcore_week_scale_retention_challenge.json
results/hexcore_long_duration_campaign_v15_state.json
results/hexcore_cross_domain_consequence_repair.json
results/hexcore_active_tactile_grasp_apprenticeship_v2.json
results/hexcore_articulated_precision_cube_lifting.json
results/hexcore_outcome_grounded_physx_attachment_search.json
results/hexcore_physx_search_and_determinism_verdict.json
results/hexcore_physx_determinism_audit.json
```

### Isaac / PhysX implementation

```text
integrations/isaac_lab/aion_isaac_lab_runner.py
integrations/isaac_lab/aion_precision_franka_policy.py
integrations/isaac_lab/active_tactile_franka_adapter.py
integrations/isaac_lab/contact_transition_gate.py
integrations/isaac_lab/physx_determinism_probe.py
integrations/isaac_lab/verify_physx_determinism.py
integrations/isaac_lab/run_physx_determinism_audit.sh
integrations/isaac_lab/physx_precision_contact_probe.py
integrations/isaac_lab/physx_search_radius_probe.py
```

### Relevant tests

```text
backend/tests/test_isaac_contract_filters.py
backend/tests/test_isaac_deterministic_execution_contract.py
backend/tests/test_precision_franka_adapter.py
backend/tests/test_active_tactile_franka_adapter.py
backend/tests/test_contact_transition_gate.py
backend/tests/test_articulated_precision_cube_lifting.py
backend/tests/test_active_tactile_grasp_apprenticeship.py
backend/tests/test_aion_development_dashboard.py
```

## 10. Integrity anchors

SHA-256 values observed during this handover:

```text
f99c5971310a02835825dbb6c7e36bd730a97c542fc94955e0030f36141dc1ab  docs/aion/AION_INTEGRATED_AGI_DEVELOPMENT_ROADMAP.md
65827b3658b79e5a682dd6daa893fdb87253a446f6949da3c05e2223f0bec139  docs/aion/AION_PHYSX_DETERMINISM_AND_PRECISION_CONTACT_REPORT.md
0bc65ec6dd8a2f14aab4e2fbe31c423c5a594410b561a5f0240e291cd6cf9bab  docs/aion/AION_OUTCOME_GROUNDED_PHYSX_ATTACHMENT_SEARCH_REPORT.md
610ad36f7b8b7a1435876aad6072446f8f75f424f598cea8671989d203c39a7c  results/hexcore_physx_search_and_determinism_verdict.json
2f7b03c567ffc2cfedd82b347e342f0e6c788e81bbce015218e9dfeb356f6ef9  results/hexcore_active_tactile_grasp_apprenticeship_v2.json
336052af8298d28bd8eeb2d5de6d2ed91caa8706ea7982dc60f1e69f79c8572f  results/hexcore_autonomous_general_apprentice_evidence_registry.json
664de6d1c412151806520fc8b8baaae38e762a7855e6207d0c5eed515c570e31  results/aion_progressive_competency_status.json
```

These hashes are audit anchors, not a prohibition on future legitimate edits. If a file changes, explain why and preserve the prior receipt.

## 11. Claim boundaries that must remain sharp

Accurate current claim:

> AION is a governed, persistent cognitive architecture with an operational apprenticeship mechanism, verified cross-domain method transfer, later-accountable useful-work generation, bounded cognitive-code improvement, strong local tactile manipulation learning, and partial PhysX manipulation competence. It has accumulated Advanced and Expert evidence across multiple domains, but its live mastery service currently requires state recovery. It is not authorized as Full or Technical AGA, does not have reliable end-to-end PhysX cube-lifting mastery, and is not AGI.

Do not claim:

- mastery of NVIDIA Cosmos or GR00T;
- reliable PhysX manipulation from 2/12;
- real-robot competence;
- unrestricted autonomous self-programming;
- that service uptime alone proves learning;
- that compressed glyph count equals subject mastery;
- that internal procedure promotion equals external certification;
- that the current malformed curriculum state is actively advancing.

## 12. Recommended opening prompt for the fresh task

Use the following prompt in a new Codex task attached to `/Users/kevinrobinson/dev/COMDEX`:

```text
Read docs/aion/AION_CODEX_CONTINUATION_HANDOVER_2026-08-06.md completely and treat it as the continuation authority for the previous AION development task. Work only in /Users/kevinrobinson/dev/COMDEX. Preserve the dirty worktree, immutable results, protected v13 champion, unrelated DNA-chain changes, and all claim boundaries.

First repair the live operational incident: recover the malformed progressive competency state without losing evidence, eliminate duplicate writers/services, add locking and regression protection, restart the mastery loop, and prove that the dashboard advances truthfully across multiple cycles. Do not award competence for state recovery.

Then rebuild the PhysX evaluation contract so every arm/episode uses an independent fresh world or a statistically valid counterbalanced process-level design. Only after that authority passes offline should you continue the precision-contact/load-accommodation controller and run one cost-capped NVIDIA tournament. Keep v13 unless the challenger exceeds >2/12, beats v13, remains safe, and passes the reproducibility audit.

Continue autonomously through safe local implementation and verification. Before any paid GPU start, report the frozen contract, instance status, expected maximum spend, and abort conditions. Stop the GPU immediately after receipt retrieval. Lead every update with measured outcomes, rejected alternatives, and the exact remaining blocker.
```

## 13. First commands for the next task

These are read-only or diagnostic except where explicitly noted:

```text
cd /Users/kevinrobinson/dev/COMDEX
git status --short
.venv/bin/python aion_dashboard.py --once --no-color
.venv/bin/python aion_dashboard.py --json
cat results/aion_mastery_curriculum_service_status.json
ps -axo pid,ppid,lstart,command | rg 'aion_|long_duration_real_outcome'
jq empty backend/modules/hexcore/data/progressive_competency/state.json
brev ls
```

`jq empty` is expected to fail until the state incident is repaired. `brev ls` may require interactive reauthentication. Merely checking status must not start or create a billable GPU instance.

---

This handover intentionally prioritizes reconstruction, current evidence, unresolved failures, and safe continuation over retelling every benchmark phase. The full historical sequence remains in the integrated roadmap and the 200+ reports under `docs/aion/`.
