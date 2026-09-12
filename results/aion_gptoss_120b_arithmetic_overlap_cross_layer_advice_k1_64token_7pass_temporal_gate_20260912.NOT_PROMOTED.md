# NOT PROMOTED — warmed temporally paired 64-token lookahead

This stricter retry used two complete 64-token warm-up passes followed by the
pattern control/candidate/control/candidate/control.  All seven passes retained
bit-for-bit routes, tokens, hidden states and step logits.

The settled median candidate was 3.3558% slower than control: 1.94225 versus
2.00969 tokens/s.  The first candidate was 12.69% slower than the mean of its
adjacent controls; the second was 3.85% faster.  Because neither the median nor
both temporal pairs cleared the unchanged 5% gate, long changing-route
lookahead is stopped.  The promoted nine-token two-family result remains valid
only within its measured short-window scope.

