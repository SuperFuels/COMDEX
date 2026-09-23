# AION Canonical Cognitive Runtime

## Status

The previously separate AION cognitive loops are now connected by one
restart-persistent orchestration runtime:

`backend/modules/hexcore/canonical_cognitive_runtime.py`

The implementation uses only the active repository at
`/Users/kevinrobinson/dev/COMDEX`. The older `/Users/kevinrobinson/COMDEX`
tree is not an authority for this integration.

This is an infrastructure integration result. It does not by itself promote a
new cognitive capability or authorize an AGI claim.

## Unified cycle

The canonical state machine is:

```text
goal
  -> investigate
  -> learn candidate context
  -> plan
  -> commit action
  -> act
  -> await delayed outcome when required
  -> observe
  -> criticise
  -> route failure to knowledge/world/skill learner
  -> evaluate private challenger
  -> retain verified outcome
  -> complete and schedule next wake
```

Every transition is written atomically. Every event is also appended to a
hash-chained outcome ledger. The runtime resumes an incomplete cycle from the
last durable stage rather than beginning a new goal.

## Existing components connected

The runtime does not replace AION's established architecture:

- the Goal Engine supplies active goals and records verified completion;
- Theta supplies fast/slow cognition, motivation, intent, reasoning, planning,
  strategic simulation and reflection;
- Tessaris remains the symbolic reflection, plan and action-proposal layer;
- HexCore remains the live cognition and governed action surface;
- `HexCoreGovernedRuntime` evaluates actions and controls verified learning;
- `HexCorePersistentLearningRuntime` retains knowledge, world models,
  procedures, outcomes, failure queues and champions;
- CAU remains the sole promotion authority;
- the heartbeat supervisor now starts and recovers the canonical runtime.

## Action authority

Planning and execution are deliberately separate. An action is SHA-256
committed before execution and receives an idempotency key. Goals without
`approval_policy=autonomous_allowed` remain proposal-only. Consent-bearing
actions are denied unless consent is explicitly present.

If a process stops after execution begins but before an outcome is durably
recorded, the runtime does not repeat the action. It records an
`interrupted_action` failure and requires revalidation. This prevents a restart
from duplicating payments, writes, commands or physical actions.

## Delayed outcomes

An adapter may return `status=awaiting_outcome` and an opaque outcome token.
The cycle then enters a durable `await_outcome` stage. A later process can bind
an independently revealed result through `submit_outcome`; only then does the
cycle continue through observation, criticism, learning and retention.

This supports tests, public API observations, repository changes, database
results, sensor readings and other consequences that arrive after the action
commitment.

## Failure attribution and learning routes

Criticism is assigned to a protected queue and routed as follows:

| Failure class | Learning route |
|---|---|
| perception, evidence, knowledge, verification | knowledge learner |
| reasoning, model, world, outcome | world learner |
| planning, tool, execution, interruption, runtime | skill learner |
| authority or consent | no learning authority |

Failure routing is itself CAU-controlled before entering persistent learning
state. Authority failures therefore cannot train AION to bypass authority.

## Challenger boundary

Repairs remain private challengers. A challenger can become a retained
procedure only when it contains a verified success outcome and exceeds the
current champion under the existing `GovernedSkillLearner` gate. Failed,
unverified or non-improving candidates remain private records.

## Scheduling and recovery

The heartbeat supervisor now includes:

`backend/AION/system/aion_cognitive_runtime_service.py`

The service wakes the runtime, selects the highest-priority eligible goal,
advances a complete cycle, records the next wake time and continues after
restart. Blocked goals receive persistent exponential backoff rather than being
retried in a tight loop.

Operational controls include:

```bash
python -m backend.modules.hexcore.canonical_cognitive_runtime --status
python -m backend.modules.hexcore.canonical_cognitive_runtime \
  --enqueue-goal "objective text" --approval-policy dry_run_only
python -m backend.modules.hexcore.canonical_cognitive_runtime --once
python -m backend.modules.hexcore.canonical_cognitive_runtime --run-forever
```

Delayed results can be submitted using `--submit-outcome-token` and
`--submit-outcome-json`. The heartbeat integration can be disabled with
`AION_COGNITIVE_RUNTIME=0`; its interval is configured through
`AION_COGNITIVE_RUNTIME_INTERVAL`.

## Verification

Focused verification covers:

- complete goal-to-retention execution;
- verified learning and procedure promotion;
- process reconstruction with the same cycle identifier;
- no duplicate execution after a safe pre-action restart;
- fail-closed handling of an ambiguous in-flight action;
- consent/governance denial before executor invocation;
- delayed external outcome submission after restart;
- priority-based goal selection;
- heartbeat service registration;
- compatibility with HexCore governance, Goal Engine field hooks and the
  existing HexCore flow.

The focused verification set passes 17 tests, including six new canonical
runtime tests.

## Claim boundary

This closes the runtime-unification gap: AION no longer needs another abstract
cognitive loop. It now has one durable control plane capable of connecting its
existing goal, investigation, planning, action, observation, criticism,
improvement and retention systems.

It does not mean that every older specialist automatically runs on every goal.
The next capability work is adapter coverage and sustained operation: attach
more Arena tools and outcome authorities to the canonical action interface,
run diverse goals over many days, and measure whether accumulated experience
increases success and reduces cost without forgetting protected skills.
