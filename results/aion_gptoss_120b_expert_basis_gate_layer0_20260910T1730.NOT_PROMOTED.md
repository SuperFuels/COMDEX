# NOT PROMOTED — GPT-OSS 120B shared expert basis

The predeclared gate required both at least a 10x representation reduction and
held-out relative L2 error no greater than 0.05.

The best rank that retained the required reduction was rank 12. It provided a
nominal 10.67x representation reduction, but explained only 39.06% of training
variance and produced 0.5890 held-out relative L2 error. Even rank 64, which
reduced representation by only 2x, produced 0.4001 held-out relative L2 error.

Decision: `STOP_SHARED_EXPERT_BASIS`. Do not compile or train this basis and do
not infer any generated-token speed from this mechanism test.

The reported 622.97-second retrieval total is excluded from storage-throughput
claims because the long scan experienced external system interference. A fresh
diagnostic read of eight previously untouched layer-one experts retrieved
101,561,864 compressed bytes in 1.346 seconds. That diagnostic does not change
the failed functional-error gate or the model's measured generation speed.

Canonical evidence SHA-256:
`57f565c6b77228ee642f7e0980321949e4ccb9bcd0338489290aabbb8061ae43`
