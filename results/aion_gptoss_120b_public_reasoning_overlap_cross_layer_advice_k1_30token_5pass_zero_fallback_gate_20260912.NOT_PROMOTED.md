# NOT PROMOTED — zero-fallback reasoning lookahead

All five passes recorded zero SD fallback and bit-for-bit routes, tokens,
hidden states and logits.  Median candidate throughput was 3.16174 tokens/s
versus 3.10025 for control, only 1.9835% faster.  Adjacent comparisons were
+22.04% and +3.74%, exposing continued first-pair warm-state drift.  The fixed
5% median gate was not met, so reasoning lookahead is stopped.

