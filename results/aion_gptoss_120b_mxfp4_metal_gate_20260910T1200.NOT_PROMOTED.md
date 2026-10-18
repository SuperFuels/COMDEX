# NOT PROMOTED

The Apple M3 Pro Metal backend supports the real GPT-OSS MXFP4 expert graph,
but the narrow one-token expert calculation was 2.31 times slower at warm
median than the CPU reference and was not bitwise equal. The bounded numerical
error and equal argmax may justify a future batched/fused quality-gated test;
they do not justify exact-path or performance promotion.
