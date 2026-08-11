# HexCore Adversarial Patch Tournament and Reproducibility Audit

## Outcome

The retained adapter-grounded property system was subjected to explicit
malicious mutations, plausible but incorrect repair proposals and repeated
fresh-process execution. Every gate passed and CAU promoted:

`procedure_adversarial_patch_tournament_292c602a670e`

## Tournament design

Each of the three repository repairs faced:

- six statically recognizable malicious mutation classes: dynamic execution,
  shell execution, verification weakening, world-writable permissions,
  embedded secrets and authentication/validation bypass;
- previously recorded plausible but unsuccessful repair proposals; and
- three fresh process seeds (`11`, `29`, `47`) for the original, selected repair
  and adversarial property suite.

Malicious candidates were required to fail closed before execution. Plausible
wrong candidates that passed static security were placed in fresh sandboxes and
judged by the independently invented functional and adversarial properties.

| Measure | Result |
|---|---:|
| Repositories | 3 |
| Process seeds per repository | 3 |
| Stable repositories | 3/3 |
| Weakest seed/repository success | 100% |
| Malicious candidates rejected | 18/18 |
| Malicious candidates executed | 0 |
| Plausible wrong candidates rejected | 3/3 |
| Live repository writes | 0 |
| Restart relearning | 0 |

Across every seed, the original checkout failed its invented functional
property, the selected repair passed that property and the selected repair
passed its adversarial suite. The result therefore tests the causal distinction
between original and repaired behavior, rather than only checking whether one
program happened to exit successfully.

## Significance

The software chain now contains explicit defenses at three levels:

1. source-attested environment acquisition prevents testing a substitute
   implementation;
2. executable properties reject plausible behaviorally wrong repairs; and
3. the absolute security scanner rejects known dangerous mutation classes
   before execution.

These decisions and seed audits survive restart. Functional success cannot
override a static security finding.

## Claim boundary

The malicious classes and process seeds were development-defined, and all three
repositories use Python. This establishes explicit malicious-candidate
rejection and initial reproducibility on the current public cohort. It is not a
professional penetration test, multi-language scale result, or independent
hidden certification.
