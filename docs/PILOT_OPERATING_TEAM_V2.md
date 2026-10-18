# AION Pilot Operating Team v2

Status: native v2 foundation operational  
Date: 2026-09-20

## Product position

> Grok Bot gives people persistent AI coworkers. AION gives a founder a governed
> operating team that understands the business, coordinates its departments,
> uses whichever accepted model the founder chooses, and can prove what it
> actually accomplished.

AION does not integrate OpenBot or Grok Bot. Their public product patterns were
used as comparative research only. The implementation remains native to AION.

The selected and accepted Vault model performs interpretation, reasoning,
planning and summarisation. It cannot create business facts, grant itself
authority, mutate durable memory or bypass an approval. AION owns capability
registration, department authority, computer access, approval, execution,
evidence, receipts and audit.

## Recovered foundation

The original Train Agent implementation was located and retained:

- Electron isolated browser and recorder injection
- follow-the-cursor / capture-next-click bridge
- semantic selectors and masked credential fields
- browser skill v1 contracts and local skill library
- browser skill chain builder
- visual node workflow architect
- dry-run workflow compilation
- approval checkpoints
- Train Agent sidebar surface

The historical limitation was also confirmed: browser chains compiled to
dry-run notifications because governed semantic replay was not connected.

## v2 architecture

### Persistent Department Pilot workspaces

Each Department Pilot receives:

- a durable capsule identity
- an independent Electron browser partition and login session
- department-scoped files, artifacts and downloads
- department connector grants
- deny-unregistered-destination network policy
- explicit controller state: Pilot, human or paused
- exact approval requirement for external writes

Finance, People, Sales, Marketing, Support, Products & Services, Operations and
the COO do not use one shared browser credential pool.

### Live work and human takeover

The Train Agent and Department Pilot surfaces expose:

- Watch computer
- Take control
- Return control to Pilot

Control transitions are durable and enter the hash-chained audit. Passwords,
passkeys, one-time codes and CAPTCHA responses stay outside model context and
recorded skill contracts.

### Teach by demonstration v2

The original browser recorder now feeds a v2 semantic skill contract:

- intended outcome
- owning department
- source systems
- semantic operation and target
- runtime input references
- waits and validation
- failure policy
- approval boundaries
- draft, validation and publication lifecycle

Captured secret values are omitted. High-consequence actions become approval
stops. A recorded skill cannot be published until selector, input, output and
approval-stop checks pass.

The Electron browser bridge can replay a demonstrated skill in dry-run mode to
resolve every target. Renderer-supplied approval hashes are not treated as
authority: direct live replay is rejected and must be routed through AION's
server-side External Tool Gateway after exact-payload approval verification.

### General routines and business events

Routines are no longer Finance-only contracts. A routine has:

- one Department Pilot owner
- a schedule or an event trigger, never both
- a current input source
- an expected result
- an exact approval policy
- stale-data and no-data behavior
- trigger-instance idempotency
- test state, enabled state, run and failure counts

An untested routine cannot be enabled. Matching business events and due
schedules create bounded COO missions and department assignments. Duplicate
event deliveries are ignored.

The desktop scheduler checks both the existing scheduled-work service and the
new generalized routine runtime.

### COO mission room and in-flight control

A mission records:

- founder outcome and constraints
- deliverables
- current owner
- typed department assignments
- dependencies
- handoff depth and fan-out limits
- an append-only timeline
- state and revision

The founder can pause, resume, stop or redirect remaining work. Redirecting
does not erase completed actions. Train Agent exposes these controls and keeps
recent missions visible.

### Completion packs

Every consequential mission can produce a sealed completion pack separating:

1. verified facts and their source authorities
2. assumptions and inferences
3. completed actions
4. exact approvals still waiting
5. unresolved questions
6. artifacts, screenshots and links

The pack is bound to the mission hash and has its own content hash.

### Scoped memory

Memory is separated into:

- authoritative facts
- approved preferences
- procedures
- temporary mission context

Authoritative facts require a named source authority. Temporary mission context
requires a mission. Every record declares that the selected model may not
mutate it directly.

### User-owned always-on workers

A user-owned Mac, server or other node can be registered as an optional worker.
Its record states:

- user ownership
- explicit capabilities
- availability
- restricted outbound policy
- inability to bypass approvals

Worker heartbeats may report only a subset of capabilities the founder already
registered. A worker cannot use its heartbeat to add authority to itself.

This is the local-first route to work that continues away from the main app. It
does not introduce a mandatory hosted-computer dependency.

### Reusable templates

Pilot, routine and skill configurations may be packaged as sanitized blueprints
and instantiated as fresh drafts. Reused skills return to draft validation and
reused routines return disabled and untested. Templates never copy:

- credentials
- browser sessions
- conversation history
- authoritative business memory

### Governed action gateway

The v2 preflight contract records:

- human, routine or Pilot initiator
- department
- registered capability status
- exact action type
- target
- redacted payload
- exact payload hash
- approval requirement
- allow/deny result

Sending, publishing, purchasing, payments, deletion, overwriting, permission
changes, production changes and legal acceptance always stop for exact
approval.

### Audit integrity

Operating-team events are appended to a JSONL audit. Each event contains the
previous event hash and its own canonical hash. The runtime exposes full-chain
verification. Concurrent writes are serialized before the new head is stored.

## User surfaces

### Train Agent

Train Agent now owns the cross-cutting controls:

- set up or repair the operating team
- view every Department Computer Capsule
- watch or take control
- record a demonstration
- create a v2 skill draft
- validate and publish the skill
- create a disabled schedule- or event-driven routine
- review its inputs, output, audit, approval stop and failure behavior
- enable or pause only a successfully tested routine
- register an optional user-owned worker with explicit capabilities
- save a skill or routine as a credential-free template
- create a fresh draft from a reusable template
- create a COO mission
- pause, redirect, stop or resume missions
- inspect recent skills, routines, missions, completion packs and audit state

Teaching is now department-local rather than a separate global form. The eight
Department Computer cards render four per row on desktop, and each card owns
its skill name, expected result and Start teaching control. Only one recorder
may be active at a time.

### Taught processes as workflow nodes

A demonstrated skill that passes safe validation and human publication is now
exported as a version-pinned `Taught Processes` module in the workflow canvas.
It appears in the `Add a step` picker and can also be inserted directly from
the Demonstrated Skill Library. Draft or failed skills are not exposed.

The node carries the immutable skill ID and published skill hash, owning
department, required inputs, output contract and recorded approval boundaries.
Canvas compilation preserves those fields so a saved workflow cannot silently
float to a newly edited skill version.

At execution time the node creates an idempotent `workflow_skill_run` in the
owning Department Computer and changes the AION Flow run to `waiting`. Later
nodes do not run until the Department Computer returns verified evidence and
the workflow is resumed. A successful completion requires evidence; an
external effect at a recorded approval boundary also requires an approval
receipt hash. A duplicate trigger reuses the existing skill run rather than
repeating the process.

This provides the native composition model required for lead-to-cash and other
cross-department workflows: connector triggers, built-in application actions,
branches, waits and taught processes can share one graph. It does not weaken
the browser boundary: renderer-provided steps are not treated as authority,
and live browser replay remains governed by the Department Computer worker,
exact approvals and completion receipts.

The existing node workflow architect and browser skill-chain builder remain in
place underneath this surface.

### Mission Room execution bridge

`Plan and launch mission` now joins the operating-team surface to AION's
existing runtime instead of merely creating a mission record:

1. `CooMissionService` resolves the model selected in the Vault and retrieves a
   bounded, source-labelled fact projection from authoritative business
   containers.
2. The selected model may propose only registered Department Pilot
   capabilities.
3. Each proposal is converted into a department execution queue item and
   rebound to the durable operating-team mission identity.
4. `pilot_capability_adapter` converts every item into an External Tool Gateway
   request and records the deterministic gateway decision.
5. A durable task is written into the assigned Department Computer workspace;
   the capsule records the mission, task, capability, objective and activity
   state.
6. External writes remain unexecuted and wait for exact-payload approval.

The isolated browser now displays an explicit mission strip. An idle capsule
says that no mission is assigned and that watching does not start work. An
assigned capsule displays its current state, objective and task identifier.

### Department Pilot pages

Each Department Pilot page receives a compact Department Computer bar showing:

- current controller
- isolated-session status
- Watch work
- Take control / Return control

Department facts and actions continue to use their existing domain authority.

## Security differences from Grok Bot

AION deliberately does not reproduce:

- a computer and credential pool shared by every Bot
- natural-language permission prompts as the final authority
- model-only action review
- allow-all network defaults
- account-wide unscoped connectors
- cloud-only operation
- vendor-controlled model selection

Optional model review can warn about risk, but deterministic policy and exact
approval remain authoritative.

## AG-UI

AG-UI is deferred. It is not needed for native Pilot computer use,
department orchestration, routines or local models. A future adapter may expose
approved external agents at the boundary, but AION's internal mission,
capability, approval, memory and receipt contracts remain canonical.

## Primary implementation files

- `backend/modules/aion_business/runtime/pilot_operating_team_service.py`
- `backend/modules/aion_business/api/pilot_operating_team_api.py`
- `backend/desktop_app.py`
- `desktop/mac/electron/main.js`
- `desktop/mac/electron/preload.js`
- `desktop/mac/electron/isolated-browser.html`
- `desktop/mac/src/pilot_operating_team_ui.js`
- `desktop/mac/src/pilot_operating_team.css`
- `backend/tests/workflow_capsules/test_aion_pilot_operating_team_service.py`
- `backend/tests/workflow_capsules/test_aion_pilot_operating_team_ui_lock.py`

## Verification

The focused service suite covers:

- isolated capsule bootstrap
- takeover and return control
- secret-free demonstrations
- safe skill publication
- routine testing and enablement
- event matching and duplicate suppression
- scheduled dispatch
- COO delegation and mission controls
- completion packs
- scoped memory
- action preflight
- worker nodes
- safe templates
- audit-chain verification

The combined focused service and desktop contract suite contains 19 tests and
passes in full. JavaScript syntax checks pass for the desktop UI and Electron
main process, and the inline isolated-browser script parses successfully.

## Deliberate boundary

This layer provides the durable operating-team contracts, controls and user
surfaces. Mission planning and department dispatch now use the canonical
planner, capability router and External Tool Gateway. Demonstrated browser
skills are still safely validated before live replay; later live execution is
admitted only through the governed tool queue, exact-payload approval system
and receipt path. That fail-closed boundary avoids a desktop renderer or
selected model being able to turn an arbitrary string called an approval hash
into authority.
