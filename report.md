# Lean Injection Report

- **Type:** `dc_container`
- **ID:** `test_container`
- **Logic Field:** `symbolic_logic`
- **Count:** `5`
- **By Symbol:**
  - `⟦ Theorem ⟧`: 3
  - `⟦ Lemma ⟧`: 1
  - `⟦ Definition ⟧`: 1

## Entries

### add_zero  `⟦ Theorem ⟧`
- Raw: `n + 0 = n`
- Norm: `n = n`
- Source: `backend/modules/lean/examples/test_theorems.lean`

### zero_add  `⟦ Theorem ⟧`
- Raw: `0 + n = n`
- Norm: `n = n`
- Source: `backend/modules/lean/examples/test_theorems.lean`

### mul_one  `⟦ Lemma ⟧`
- Raw: `n * 1 = n`
- Norm: `n = n`
- Source: `backend/modules/lean/examples/test_theorems.lean`

### square  `⟦ Definition ⟧`
- Logic: `ℕ`
- Source: `backend/modules/lean/examples/test_theorems.lean`

### add_comm  `⟦ Theorem ⟧`
- Logic: `a + b = b + a`
- Source: `backend/modules/lean/examples/test.lean`
