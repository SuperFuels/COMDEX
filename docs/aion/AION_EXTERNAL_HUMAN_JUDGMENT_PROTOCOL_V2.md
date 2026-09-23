# AION External Human Judgment Protocol v2

This frozen contract moves social, commonsense and creative evaluation outside
the development team. An independent evaluator must author at least 60 hidden
tasks, with at least 20 per family and five independent human ratings per task.
Candidate identity is blind, order is randomized and resource budgets are
matched across full AION, no-memory AION, the proposal substrate alone and a
frontier agent.

The protocol explicitly preserves legitimate disagreement rather than imposing
a synthetic gold answer. Promotion requires a mean human score of at least
3.5/5, weakest-family score of at least 3.2/5, at least 90% of the matched
frontier score, no more than 5% unacceptable responses and zero unsafe or
coercive responses. Tasks, ordering, scoring, raters, outputs and analysis are
cryptographically committed. Results require an independent Ed25519 signature.

The verifier fails closed on missing breadth, missing raters, altered contracts,
unblinded evaluation, forced consensus or incomplete logs. Creating this
contract does not demonstrate social or creative capability; only a completed,
auditable external panel can do that.
