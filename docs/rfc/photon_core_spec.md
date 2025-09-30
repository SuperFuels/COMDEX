# Photon Core Specification

## Glyph Axioms (Philosophical View)

| Axiom | Pattern | Replacement | Description |
|-------|---------|-------------|-------------|
| comm_add | `a ⊕ b` | `b ⊕ a` | Commutativity of ⊕ |
| assoc_add | `(a ⊕ b) ⊕ c` | `a ⊕ (b ⊕ c)` | Associativity of ⊕ |
| id_add | `a ⊕ 0` | `a` | Identity element of ⊕ |
| inv_add | `a ⊕ (⊖a)` | `0` | Inverse under ⊕ |
| comm_mul | `a ⊗ b` | `b ⊗ a` | Commutativity of ⊗ |
| assoc_mul | `(a ⊗ b) ⊗ c` | `a ⊗ (b ⊗ c)` | Associativity of ⊗ |
| id_mul | `a ⊗ 1` | `a` | Identity element of ⊗ |
| inv_mul | `a ⊗ (÷a)` | `1` | Inverse under ⊗ |
| sym_eq | `a ↔ b` | `b ↔ a` | Symmetry of entanglement ↔ |
| ref_eq | `a ↔ a` | `✦` | Reflexivity of entanglement (collapse milestone) |
| grad_zero | `Grad(0)` | `0` | Gradient of zero is zero |
| grad_const | `Grad(c)` | `0` | Gradient of constant is zero |
| grad_add | `Grad(a + b)` | `Grad(a) + Grad(b)` | Gradient distributes over ⊕ |
| grad_mul | `Grad(a * b)` | `(Grad(a) * b) + (a * Grad(b))` | Product rule for ∇ |
| collapse_id | `⟲a` | `a` | Mutation collapse identity |

## Sympy Axioms (Machine View)

| Axiom | LHS (Sympy) | RHS (Sympy) | Description |
|-------|-------------|-------------|-------------|
| comm_add | `a ⊕ b` | `b ⊕ a` | Commutativity of ⊕ |
| assoc_add | `(a ⊕ b) ⊕ c` | `a ⊕ (b ⊕ c)` | Associativity of ⊕ |
| id_add | `a ⊕ 0` | `a` | Identity element of ⊕ |
| inv_add | `a ⊕ (⊖a)` | `0` | Inverse under ⊕ |
| comm_mul | `a ⊗ b` | `b ⊗ a` | Commutativity of ⊗ |
| assoc_mul | `(a ⊗ b) ⊗ c` | `a ⊗ (b ⊗ c)` | Associativity of ⊗ |
| id_mul | `a ⊗ 1` | `a` | Identity element of ⊗ |
| inv_mul | `a ⊗ (÷a)` | `1` | Inverse under ⊗ |
| sym_eq | `Eq(a, b)` | `Eq(b, a)` | Symmetry of entanglement ↔ |
| ref_eq | `Eq(a, a)` | `✦` | Reflexivity of entanglement (collapse milestone) |
| grad_zero | `Grad(0)` | `0` | Gradient of zero is zero |
| grad_const | `Grad(c)` | `0` | Gradient of constant is zero |
| grad_add | `Grad(a + b)` | `Grad(a) + Grad(b)` | Gradient distributes over ⊕ |
| grad_mul | `Grad(a * b)` | `(Grad(a) * b) + (a * Grad(b))` | Product rule for ∇ |
| collapse_id | `⟲a` | `a` | Mutation collapse identity |

## Theorem Verification

| Theorem | Statement | Result |
|---------|-----------|--------|
| T1_comm_add | (a ⊕ b) ≡ (b ⊕ a) | ✅ Proven |
| T2_assoc_add | ((a ⊕ b) ⊕ c) ≡ (a ⊕ (b ⊕ c)) | ✅ Proven |
| T3_grad_add | ∇(a ⊕ b) ≡ (∇a ⊕ ∇b) | ✅ Proven |
| T4_grad_mul | ∇(a ⊗ b) ≡ (∇a ⊗ b) ⊕ (a ⊗ ∇b) | ✅ Proven |
| T5_sym_eq | (a ↔ b) ≡ (b ↔ a) | ✅ Proven |
| T6_grad_nested | ∇((a ⊕ b) ⊗ c) ≡ ((∇a ⊕ ∇b) ⊗ c) ⊕ ((a ⊕ b) ⊗ ∇c) | ✅ Proven |



### Normal Form Invariant

All Photon expressions normalize to **sum-of-products**:
- No `⊕` directly under a `⊗`.
- `⊕` is flattened, order-canonical, idempotent, and `∅`-free (identity removed).
- `⊗` applies annihilator `∅` and respects dual-absorption with sums.

We **do not factor** `a ⊕ (b ⊗ c)` inside the `⊕` branch to avoid ping-pong with `⊗`-side distribution. Instead, a guarded T14-style step is applied only when safe; general distribution is handled structurally in the `⊗` branch.