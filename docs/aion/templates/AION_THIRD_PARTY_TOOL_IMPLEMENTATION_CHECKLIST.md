# AION Third-Party Tool Implementation Checklist

Copy this file for each provider. Replace every bracketed field and retain it beside the provider implementation.

## Provider identity

- Provider: `[name]`
- Tool ID: `[stable_lowercase_id]`
- Business category: `[email / CRM / accounting / voice / payments / other]`
- Business outcome: `[what useful job this enables]`
- Implementation owner: `[owner]`
- Manifest path: `[path]`
- Manifest SHA-256: `[generated after validation]`

## Connection contract

- Connection type: `[OAuth 2 / API key / webhook / MCP / local / browser / desktop]`
- Vault reference: `vault.[provider].credentials`
- Minimum scopes: `[list only required scopes]`
- Health check: `[method]`
- Revocation method: `[method]`
- Secrets visible to model: `no`

## Skills and business knowledge

- Required AION skills: `[skill IDs]`
- Required approved company facts: `[facts/policies]`
- Relevant departments: `[departments]`
- Missing-information behaviour: `[ask / prepare with placeholders / stop]`
- Prohibited assumptions: `[list]`

## Atomic action table

Complete one row per action. Never use “do anything.”

| Action ID | Purpose | Read/write | Risk | Default authority | Limits | Dry run | Receipt | Adapter method |
|---|---|---|---|---|---|---|---|---|
| `[provider.action]` | `[purpose]` | `[read/write]` | `[low/medium/high/blocked]` | `[mode]` | `[allowlist/cap]` | `[yes/no]` | `[fields]` | `[method]` |

## Adapter contract

- [ ] `health_check` proves the connection works without a side effect.
- [ ] `prepare` validates and normalises every input.
- [ ] `preview` shows the exact proposed payload.
- [ ] `execute` accepts only a registered action and evaluated authority decision.
- [ ] external writes use an idempotency key or provider idempotency.
- [ ] `reconcile` reads provider state back after a write.
- [ ] timeouts and retries cannot duplicate side effects.
- [ ] arbitrary/custom API access is blocked unless explicitly allowlisted.

## Authority contract

- Policy key(s): `[keys]`
- Allowed modes: `[ask_each_time / auto_within_limits / full_access / blocked]`
- Recipient/account/record allowlists: `[limits]`
- Financial amount and currency limit: `[if applicable]`
- Exact-payload approval required: `[conditions]`
- Refusal behaviour: `[including ask_again=false]`
- Emergency kill switch: `[location and method]`

## Receipt contract

- [ ] workspace and provider recorded;
- [ ] action and policy decision recorded;
- [ ] exact payload hash recorded;
- [ ] provider request/result IDs recorded;
- [ ] start and completion timestamps recorded;
- [ ] reconciliation result recorded;
- [ ] uncertain outcomes remain uncertain until reconciled;
- [ ] no credential or unnecessary personal data appears in the receipt.

## Required verification

- [ ] manifest validation passes;
- [ ] unit and contract tests pass;
- [ ] missing/revoked credential test passes;
- [ ] insufficient-scope test passes;
- [ ] blocked and approval-required tests pass;
- [ ] dry run has zero external side effects;
- [ ] duplicate request test proves idempotency;
- [ ] timeout/rate-limit/error tests fail closed;
- [ ] sandbox write and read-back reconciliation pass;
- [ ] live test is bounded and explicitly authorised;
- [ ] generated receipt independently verifies;
- [ ] UI truthfully displays the achieved capability stage.

## Promotion record

- Current stage: `[defined / connected / read_verified / draft_verified / sandbox_write_verified / live_verified]`
- Evidence paths: `[paths]`
- Known limitations: `[limitations]`
- Claim boundary: `[what this integration demonstrably can and cannot do]`
- Approved for live use by: `[owner]`
- Approval date: `[date]`

