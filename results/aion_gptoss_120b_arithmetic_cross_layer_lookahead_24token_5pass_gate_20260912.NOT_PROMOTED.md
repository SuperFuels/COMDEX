# NOT PROMOTED — buffered four-expert cross-layer lookahead

The candidate was bit-for-bit exact, but its settled median continuation time
was 40.6559% worse than control.  Four sequential speculative L2 reads did not
complete inside the available layer window, added approximately 3.87 GB per
pass, and forced the authoritative path to wait.  The prediction evidence is
valid; this physical implementation is stopped.

