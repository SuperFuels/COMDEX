# PhotonAlgebra Theorems Results

Automated proof snapshot (Lean).

## Bridge

| Item | Statement | Status |
|---|---|---|
| wf_invariant_normStep | `normalizeWF (normStep e) = normalizeWF e` | ✅ |
| wf_invariant_normalizeFuel | `normalizeWF (normalizeFuel k e) = normalizeWF e` | ✅ |
| normalize_bridge | `normalizeWF (normalize e) = normalizeWF e` | ✅ |

## Phase-1 (EqNF laws)

| Theorem | Statement | Status |
|---|---|---|
| CollapseWF | `normalizeWF (∇a) = ∇(normalizeWF a)` | ✅ |
| T8 | `EqNF (a ⊗ (b ⊕ c)) ((a ⊗ b) ⊕ (a ⊗ c))` | ✅ |
| T9 | `EqNF (¬(¬a)) a` | ⚠️ TODO |
| T10 | `EqNF ((a↔b) ⊕ (a↔c)) (a↔(b⊕c))` | ✅ |
| T11 | `EqNF (a↔a) a` | ✅ |
| T12 | `EqNF (★(a↔b)) ((★a) ⊕ (★b))` | ⚠️ TODO |
| T13 | `EqNF (a ⊕ (a ⊗ b)) a` | ✅ |
| T14 | `NO RULE: factoring is excluded (one-way distribution only)` | ℹ️ DESIGN |
| T15R | `EqNF (a ⊖ ∅) a` | ✅ |
| T15L | `EqNF (∅ ⊖ a) a` | ✅ |
| T15C | `EqNF (a ⊖ a) ∅` | ✅ |

Generated from `PhotonAlgebra/SnapshotGen.lean`.
