# NOT PROMOTED — 64-token cross-layer advice replication

The 64-token arithmetic run remained bit-for-bit exact across all five passes,
but the balanced settled median was 1.2066% slower than control (1.34246 versus
1.35885 tokens/s).  Pass-to-pass warm-state drift was exceptionally large:
the two candidate passes measured 1.0393 and 1.8955 tokens/s, while surrounding
controls measured 0.9895 and 2.1681 tokens/s.  The five-pass protocol therefore
does not promote the short-window gain to longer changing-route generation.

The exact short two-family promotion remains valid within its measured scope.
A future long gate requires additional full-length warm-up passes and closer
temporal pairing; the acceptance threshold remains unchanged.

