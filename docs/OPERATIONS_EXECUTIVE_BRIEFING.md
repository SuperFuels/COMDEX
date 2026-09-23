# Operations Executive Briefing and Department Channels

## Purpose

The Operations Command Centre is the founder-facing control surface for the COO. The left pane remains the founder's direct conversation with Operations Pilot. The right pane is a durable set of COO-to-Department-Pilot channels for Sales, Marketing, Finance, Support, People, and Products & Services.

These channels are business records. They are not simulated chat copy and they are not tied to the lifetime of a screen.

## Morning executive meeting

At 08:00 in the configured business timezone, the local desktop scheduler checks whether that local day's briefing exists. If it is due, AION runs it once and records a deduplication key for the local date. The Operations page performs the same protected check when opened and every five minutes while it remains open, so either path can recover a missed run without producing duplicate minutes. A user can also run a replacement briefing explicitly.

For every department, AION constructs a separate role-bound request containing:

- the department director mandate;
- only the authorised evidence projection for that department;
- the latest published Board meeting summaries, mandates and delegated actions;
- the department's previous conversation context when responding to a COO follow-up;
- rules that prohibit invented figures and prohibit claims that live work was executed.

The requested return contract covers yesterday's evidenced results, today's plan, outstanding work, risks, target variance, decisions required from the COO, and proposed actions. Missing sources remain explicitly unknown.

## Models and executive challenge

The primary reasoner is always the model selected and accepted through the Vault. No department is fixed to Qwen or any other model. AION owns evidence selection, role boundaries, validation, persistence and authority; the selected model supplies bounded judgement.

Each department is invoked separately with a different director role card. If no second accepted model is configured, the receipt says `single_model_role_separated`; the interface does not misrepresent this as independent multi-party debate.

An optional critic may be configured through `executive_briefing_config.critic_model_selection`. It must resolve to an accepted model that is distinct from the primary model. The critic receives the bounded department positions and Board context, challenges unsupported claims and cross-department conflicts, and cannot execute work. Successful use is recorded as `two_model_challenge`, including model provenance.

## Minutes, actions and escalation

The service writes dated morning minutes into each department's channel. It also writes a summary into the left-hand Operations Pilot stream. Proposed actions are entered into `executive_action_register` with an `open` state and with external execution disabled. Risks and material target variance are entered into `executive_board_feedback` with `staged_for_coo_ceo_board` status.

This is a feedback boundary, not an authority bypass: the briefing can surface and stage a Board item, but it cannot alter a Board target or approve an external action.

## COO follow-ups

The COO composer in each channel submits a protected, signed request for the selected Department Pilot. The response is built with that department's evidence, role card, Board context and recent channel history. This supports operational follow-up such as asking Sales about today's target or Support about a customer reply without losing the thread of accountability.

## Persistence and audit

Messages are retained in the workspace `operational_runtime_summary.shared_conversations` record. Each executive message contains:

- department, sender and message type;
- timestamp and bounded structured metadata;
- evidence source identifiers and model provenance;
- the previous record hash and its own canonical record hash;
- explicit approval and external-write state.

The initial UI request retrieves only a bounded recent page. The workspace retains the larger local record. Morning runs are also stored in `executive_briefings` with a canonical briefing hash.

## Safety boundary

Morning meetings and department replies are read-and-prepare operations. They never send email, change a CRM, move money, publish a campaign, contact an employee, or modify an external service. Such work must be routed through the registered Department Pilot capability and AION's exact approval gateway.

## API surface

All endpoints use the possession-bound signed desktop session, which fixes the person and workspace:

- `executive-status` returns schedule, due state and channel summaries;
- `morning-briefing` runs or deduplicates the daily meeting;
- `channel-history` returns one department's persistent stream;
- `channel-turn` records a COO instruction and the evidence-bounded Department Pilot reply.

The renderer never chooses another workspace and cannot manufacture execution authority.
