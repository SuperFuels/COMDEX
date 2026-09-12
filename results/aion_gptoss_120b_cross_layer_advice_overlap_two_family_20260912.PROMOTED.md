# PROMOTED — exact cross-layer advice composed with same-layer overlap

The original next-layer router is applied early to the current post-attention
residual.  Its top-one expert prediction issues a macOS asynchronous no-copy
`F_RDADVISE` hint against persistent L2.  The existing four-way demand loader,
authoritative router, gates, weights and reduction order are unchanged.

- Arithmetic settled median: 2.16949 to 2.30511 tokens/s; 6.2516% faster.
- Extraction settled median: 1.98918 to 2.44821 tokens/s; 23.0765% faster.
- Tokens, routes, hidden states and step logits: bit-for-bit repeatable.
- Speculative user-space expert copies: zero.
- Lookahead synchronization waits: zero.
- SD fallback during settled comparisons: zero.
- Scope: two nine-token continuation windows after real prompts; longer and
  broader validation remains required before revising the global frontier.

