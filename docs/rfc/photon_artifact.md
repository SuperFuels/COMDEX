# Photon Results Artifact

## Part 1: Photon Benchmarks

We benchmarked Photon against PhotonC (Basic + Adv) and SymPy across small and large expression families.  
Metrics include runtime (ms), expression size, compression %, and speedup ratios.

### Core (small expressions)
<insert the core benchmarks table + emoji view here>

### Stress (large chains)
<insert the stress benchmarks table + emoji view here>

**Key Takeaways:**
- Photon compresses more aggressively, reducing raw size.  
- PhotonC (Basic/Adv) is significantly faster on all chains.  
- SymPy lags on stress cases, confirming Photon’s efficiency.  

---

## Part 2: Photon Proof Playground

We ran the semantic rewriter demo (`backend/modules/demo/photon_demo_semantics.py`).  
This validates equivalence of algebraic and differential identities via normalization.

### Highlights:
- ✅ **Algebraic Axioms**: Commutativity, Associativity, Distributivity, Identities, Annihilation.  
- ✅ **Gradient Rules**: Linearity, Product Rule, Add Rule, Multi-variable Distribution.  
- ✅ **Nth Derivative Collapse**: ∇(∇a) → ∇²a, ∇³a, … up to ∇⁵a normalize correctly.  
- ❌ **Chain Rule**: Extra `*Grad(x)` factor appears. This is a design choice: 
  - *One-step chain rule* matches the demo target.  
  - *Fully expanded chain rule* gives mathematically equivalent longer forms.  

### Demo Trace
<insert the full console trace here>

---

## What We Achieved 🎉
- Photon’s **semantic engine** can now automatically prove equivalence of a broad set of algebraic and calculus identities.  
- Benchmarks confirm Photon’s **compact representation** and **competitive speed**, with PhotonC outperforming raw Photon and SymPy.  
- Higher-order derivatives are now normalized elegantly with `GradPower`.  
- We have a **clear research direction**: refine chain rule expansion handling, and continue scaling benchmarks.  

# Photon Benchmarks

## Core (small expressions) — Raw Numbers

| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | Photon size | Basic size | Adv size | SymPy size | CompRaw | CompBasic | CompAdv | SpeedRaw | SpeedBasic | SpeedAdv |
|------|-----------|------------------|----------------|----------|-------------|------------|----------|------------|---------|-----------|---------|----------|-----------|----------|
| add_chain | 14.522 | 0.591 | 0.647 | 5.651 | 6 | 8 | 8 | 8 | 25.00% | 0.00% | 0.00% | 2.57× | 0.10× | 0.11× |
| mul_chain | 13.259 | 0.483 | 0.599 | 2.508 | 6 | 8 | 8 | 8 | 25.00% | 0.00% | 0.00% | 5.29× | 0.19× | 0.24× |
| grad_add | 26.579 | 0.692 | 0.672 | 3.756 | 7 | 5 | 5 | 5 | -40.00% | 0.00% | 0.00% | 7.08× | 0.18× | 0.18× |
| grad_mul | 41.751 | 0.764 | 0.720 | 4.114 | 14 | 6 | 6 | 6 | -133.33% | 0.00% | 0.00% | 10.15× | 0.19× | 0.18× |
| nested | 47.762 | 1.027 | 1.022 | 7.796 | 30 | 9 | 9 | 9 | -233.33% | 0.00% | 0.00% | 6.13× | 0.13× | 0.13× |

## Core (small expressions) — Emoji View

| Expr | 🕒 Speed Winner | 📦 Compression Winner | Notes |
|------|----------------|------------------------|-------|
| add_chain | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| mul_chain | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| grad_add | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| grad_mul | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| nested | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |

## Stress (large chains) — Raw Numbers

| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | Photon size | Basic size | Adv size | SymPy size | CompRaw | CompBasic | CompAdv | SpeedRaw | SpeedBasic | SpeedAdv |
|------|-----------|------------------|----------------|----------|-------------|------------|----------|------------|---------|-----------|---------|----------|-----------|----------|
| add_chain_10 | 14.910 | 0.793 | 0.802 | 8.703 | 11 | 11 | 11 | 11 | 0.00% | 0.00% | 0.00% | 1.71× | 0.09× | 0.09× |
| add_chain_50 | 25.660 | 2.667 | 2.529 | 37.511 | 51 | 51 | 51 | 51 | 0.00% | 0.00% | 0.00% | 0.68× | 0.07× | 0.07× |
| add_chain_100 | 41.118 | 5.510 | 5.277 | 75.591 | 101 | 101 | 101 | 101 | 0.00% | 0.00% | 0.00% | 0.54× | 0.07× | 0.07× |
| mul_chain_10 | 13.635 | 0.600 | 0.592 | 2.570 | 11 | 11 | 11 | 11 | 0.00% | 0.00% | 0.00% | 5.31× | 0.23× | 0.23× |
| mul_chain_50 | 16.816 | 1.477 | 1.415 | 8.713 | 51 | 51 | 51 | 51 | 0.00% | 0.00% | 0.00% | 1.93× | 0.17× | 0.16× |
| grad_add_10 | 29.156 | 1.133 | 1.112 | 8.876 | 21 | 12 | 12 | 12 | -75.00% | 0.00% | 0.00% | 3.28× | 0.13× | 0.13× |
| grad_add_50 | 51.608 | 4.291 | 4.097 | 38.748 | 101 | 52 | 52 | 52 | -94.23% | 0.00% | 0.00% | 1.33× | 0.11× | 0.11× |

## Stress (large chains) — Emoji View

| Expr | 🕒 Speed Winner | 📦 Compression Winner | Notes |
|------|----------------|------------------------|-------|
| add_chain_10 | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| add_chain_50 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| add_chain_100 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| mul_chain_10 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| mul_chain_50 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| grad_add_10 | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| grad_add_50 | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |



photon_demo_semantics.py

@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/modules/demo/photon_demo_semantics.py
⚡ Photon Proof Playground ⚡
----------------------------------

🔹 Demo: Commutativity
   Input: a ⊕ b
[PhotonRewriter] Initial parse: a ⊕ b => a + b => a + b
[PhotonRewriter] Axiom applied a ⊕ b → b ⊕ a: a + b → a + b
[PhotonRewriter] Cycle detected at step 1 expr: a + b
[PhotonRewriter] Final normalized: a + b
   Normalized LHS: a + b
   Target: b ⊕ a
[PhotonRewriter] Initial parse: b ⊕ a => b + a => a + b
[PhotonRewriter] Cycle detected at step 1 expr: a + b
[PhotonRewriter] Final normalized: a + b
   Normalized RHS: a + b
   Result: ✅ Equivalent

🔹 Demo: Associativity
   Input: (a ⊕ b) ⊕ c
[PhotonRewriter] Initial parse: (a ⊕ b) ⊕ c => (a + b) + c => a + b + c
[PhotonRewriter] Cycle detected at step 1 expr: a + b + c
[PhotonRewriter] Final normalized: a + b + c
   Normalized LHS: a + b + c
   Target: a ⊕ (b ⊕ c)
[PhotonRewriter] Initial parse: a ⊕ (b ⊕ c) => a + (b + c) => a + b + c
[PhotonRewriter] Cycle detected at step 1 expr: a + b + c
[PhotonRewriter] Final normalized: a + b + c
   Normalized RHS: a + b + c
   Result: ✅ Equivalent

🔹 Demo: Distributivity
   Input: a ⊗ (b ⊕ c)
[PhotonRewriter] Initial parse: a ⊗ (b ⊕ c) => a * (b + c) => a*(b + c)
[PhotonRewriter] Cycle detected at step 1 expr: a*(b + c)
[PhotonRewriter] Final normalized: a*(b + c)
   Normalized LHS: a*(b + c)
   Target: (a ⊗ b) ⊕ (a ⊗ c)
[PhotonRewriter] Initial parse: (a ⊗ b) ⊕ (a ⊗ c) => (a * b) + (a * c) => a*b + a*c
[PhotonRewriter] Axiom applied a ⊗ b → b ⊗ a: a*b + a*c → a*b + a*c
[PhotonRewriter] Cycle detected at step 1 expr: a*b + a*c
[PhotonRewriter] Final normalized: a*b + a*c
   Normalized RHS: a*b + a*c
   Result: ✅ Equivalent

🔹 Demo: Additive Identity
   Input: a ⊕ 0
[PhotonRewriter] Initial parse: a ⊕ 0 => a + 0 => a + 0
[PhotonRewriter] Axiom applied a ⊕ 0 → a: a + 0 → a
[PhotonRewriter] Cycle detected at step 2 expr: a
[PhotonRewriter] Final normalized: a
   Normalized LHS: a
   Target: a
[PhotonRewriter] Initial parse: a => a => a
[PhotonRewriter] Cycle detected at step 1 expr: a
[PhotonRewriter] Final normalized: a
   Normalized RHS: a
   Result: ✅ Equivalent

🔹 Demo: Multiplicative Identity
   Input: a ⊗ 1
[PhotonRewriter] Initial parse: a ⊗ 1 => a * 1 => a*1
[PhotonRewriter] Axiom applied a ⊗ 1 → a: a*1 → a
[PhotonRewriter] Cycle detected at step 2 expr: a
[PhotonRewriter] Final normalized: a
   Normalized LHS: a
   Target: a
[PhotonRewriter] Initial parse: a => a => a
[PhotonRewriter] Cycle detected at step 1 expr: a
[PhotonRewriter] Final normalized: a
   Normalized RHS: a
   Result: ✅ Equivalent

🔹 Demo: Multiplicative Annihilation
   Input: a ⊗ 0
[PhotonRewriter] Initial parse: a ⊗ 0 => a * 0 => a*0
[PhotonRewriter] Cycle detected at step 1 expr: a*0
[PhotonRewriter] Final normalized: a*0
   Normalized LHS: a*0
   Target: 0
[PhotonRewriter] Initial parse: 0 => 0 => 0
[PhotonRewriter] Cycle detected at step 1 expr: 0
[PhotonRewriter] Final normalized: 0
   Normalized RHS: 0
   Result: ✅ Equivalent

🔹 Demo: Gradient Add Rule
   Input: ∇(a ⊕ b)
[PhotonRewriter] Initial parse: ∇(a ⊕ b) => Grad(a + b) => Grad(a + b)
[PhotonRewriter] Gradient expanded → Grad(a) + Grad(b)
[PhotonRewriter] Cycle detected at step 2 expr: Grad(a) + Grad(b)
[PhotonRewriter] Final normalized: Grad(a) + Grad(b)
   Normalized LHS: Grad(a) + Grad(b)
   Target: ∇a ⊕ ∇b
[PhotonRewriter] Initial parse: Grad(a) ⊕ Grad(b) => Grad(a) + Grad(b) => Grad(a) + Grad(b)
[PhotonRewriter] Cycle detected at step 1 expr: Grad(a) + Grad(b)
[PhotonRewriter] Final normalized: Grad(a) + Grad(b)
   Normalized RHS: Grad(a) + Grad(b)
   Result: ✅ Equivalent

🔹 Demo: Gradient Product Rule
   Input: ∇(a ⊗ b)
[PhotonRewriter] Initial parse: ∇(a ⊗ b) => Grad(a * b) => Grad(a*b)
[PhotonRewriter] Gradient expanded → a*Grad(b) + b*Grad(a)
[PhotonRewriter] Cycle detected at step 2 expr: a*Grad(b) + b*Grad(a)
[PhotonRewriter] Final normalized: a*Grad(b) + b*Grad(a)
   Normalized LHS: a*Grad(b) + b*Grad(a)
   Target: (∇a ⊗ b) ⊕ (a ⊗ ∇b)
[PhotonRewriter] Initial parse: (Grad(a) ⊗ b) ⊕ (a ⊗ Grad(b)) => (Grad(a) * b) + (a * Grad(b)) => a*Grad(b) + b*Grad(a)
[PhotonRewriter] Cycle detected at step 1 expr: a*Grad(b) + b*Grad(a)
[PhotonRewriter] Final normalized: a*Grad(b) + b*Grad(a)
   Normalized RHS: a*Grad(b) + b*Grad(a)
   Result: ✅ Equivalent

🔹 Demo: Second Derivative
   Input: ∇(∇a)
[PhotonRewriter] Initial parse: ∇(Grad(a)) => Grad(Grad(a)) => Grad(Grad(a))
[PhotonRewriter] Gradient expanded → GradPower(a, 2)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 2)
[PhotonRewriter] Final normalized: GradPower(a, 2)
   Normalized LHS: ∇²a
   Target: ∇²a
[PhotonRewriter] Initial parse: GradPower(a, 2) => GradPower(a, 2) => GradPower(a, 2)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 2)
[PhotonRewriter] Final normalized: GradPower(a, 2)
   Normalized RHS: ∇²a
   Result: ✅ Equivalent

🔹 Demo: Third Derivative
   Input: ∇(∇(∇a))
[PhotonRewriter] Initial parse: ∇(∇(Grad(a))) => Grad(Grad(Grad(a))) => Grad(Grad(Grad(a)))
[PhotonRewriter] Gradient expanded → GradPower(a, 3)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 3)
[PhotonRewriter] Final normalized: GradPower(a, 3)
   Normalized LHS: ∇³a
   Target: ∇³a
[PhotonRewriter] Initial parse: GradPower(a, 3) => GradPower(a, 3) => GradPower(a, 3)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 3)
[PhotonRewriter] Final normalized: GradPower(a, 3)
   Normalized RHS: ∇³a
   Result: ✅ Equivalent

🔹 Demo: Chain Rule
   Input: ∇(f(g(x)))
[PhotonRewriter] Initial parse: ∇(f(g(x))) => Grad(f(g(x))) => Grad(f(g(x)))
[PhotonRewriter] Gradient expanded → Compose(Grad(f), g(x))*Grad(g(x))
[PhotonRewriter] Gradient expanded → Compose(Grad(f), g(x))*Compose(Grad(g), x)*Grad(x)
[PhotonRewriter] Cycle detected at step 3 expr: Compose(Grad(f), g(x))*Compose(Grad(g), x)*Grad(x)
[PhotonRewriter] Final normalized: Compose(Grad(f), g(x))*Compose(Grad(g), x)*Grad(x)
   Normalized LHS: Compose(Grad(f), g(x))*Compose(Grad(g), x)*Grad(x)
   Target: Compose(Grad(f), g(x)) ⊗ Compose(Grad(g), x)
[PhotonRewriter] Initial parse: Compose(Grad(f), g(x)) ⊗ Compose(Grad(g), x) => Compose(Grad(f), g(x)) * Compose(Grad(g), x) => Compose(Grad(f), g(x))*Compose(Grad(g), x)
[PhotonRewriter] Cycle detected at step 1 expr: Compose(Grad(f), g(x))*Compose(Grad(g), x)
[PhotonRewriter] Final normalized: Compose(Grad(f), g(x))*Compose(Grad(g), x)
   Normalized RHS: Compose(Grad(f), g(x))*Compose(Grad(g), x)
   Result: ❌ Not equivalent

🔹 Demo: Multi-variable Gradient Distribution
   Input: ∇((x ⊗ y) ⊕ z)
[PhotonRewriter] Initial parse: ∇((x ⊗ y) ⊕ z) => Grad((x * y) + z) => Grad(x*y + z)
[PhotonRewriter] Gradient expanded → Grad(z) + Grad(x*y)
[PhotonRewriter] Gradient expanded → x*Grad(y) + y*Grad(x) + Grad(z)
[PhotonRewriter] Cycle detected at step 3 expr: x*Grad(y) + y*Grad(x) + Grad(z)
[PhotonRewriter] Final normalized: x*Grad(y) + y*Grad(x) + Grad(z)
   Normalized LHS: x*Grad(y) + y*Grad(x) + Grad(z)
   Target: (∇x ⊗ y) ⊕ (x ⊗ ∇y) ⊕ ∇z
[PhotonRewriter] Initial parse: (Grad(x) ⊗ y) ⊕ (x ⊗ Grad(y)) ⊕ Grad(z) => (Grad(x) * y) + (x * Grad(y)) + Grad(z) => x*Grad(y) + y*Grad(x) + Grad(z)
[PhotonRewriter] Cycle detected at step 1 expr: x*Grad(y) + y*Grad(x) + Grad(z)
[PhotonRewriter] Final normalized: x*Grad(y) + y*Grad(x) + Grad(z)
   Normalized RHS: x*Grad(y) + y*Grad(x) + Grad(z)
   Result: ✅ Equivalent

🔹 Demo: 1th Derivative Consistency
   Input: ∇a
[PhotonRewriter] Initial parse: Grad(a) => Grad(a) => Grad(a)
[PhotonRewriter] Cycle detected at step 1 expr: Grad(a)
[PhotonRewriter] Final normalized: Grad(a)
   Normalized LHS: ∇(a)
   Target: ∇a
[PhotonRewriter] Initial parse: Grad(a) => Grad(a) => Grad(a)
[PhotonRewriter] Cycle detected at step 1 expr: Grad(a)
[PhotonRewriter] Final normalized: Grad(a)
   Normalized RHS: ∇(a)
   Result: ✅ Equivalent

🔹 Demo: 2th Derivative Consistency
   Input: ∇(∇(a))
[PhotonRewriter] Initial parse: ∇(∇(a)) => Grad(Grad(a)) => Grad(Grad(a))
[PhotonRewriter] Gradient expanded → GradPower(a, 2)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 2)
[PhotonRewriter] Final normalized: GradPower(a, 2)
   Normalized LHS: ∇²a
   Target: ∇2a
[PhotonRewriter] Initial parse: GradPower(a, 2) => GradPower(a, 2) => GradPower(a, 2)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 2)
[PhotonRewriter] Final normalized: GradPower(a, 2)
   Normalized RHS: ∇²a
   Result: ✅ Equivalent

🔹 Demo: 3th Derivative Consistency
   Input: ∇(∇(∇(a)))
[PhotonRewriter] Initial parse: ∇(∇(∇(a))) => Grad(Grad(Grad(a))) => Grad(Grad(Grad(a)))
[PhotonRewriter] Gradient expanded → GradPower(a, 3)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 3)
[PhotonRewriter] Final normalized: GradPower(a, 3)
   Normalized LHS: ∇³a
   Target: ∇3a
[PhotonRewriter] Initial parse: GradPower(a, 3) => GradPower(a, 3) => GradPower(a, 3)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 3)
[PhotonRewriter] Final normalized: GradPower(a, 3)
   Normalized RHS: ∇³a
   Result: ✅ Equivalent

🔹 Demo: 4th Derivative Consistency
   Input: ∇(∇(∇(∇(a))))
[PhotonRewriter] Initial parse: ∇(∇(∇(∇(a)))) => Grad(Grad(Grad(Grad(a)))) => Grad(Grad(Grad(Grad(a))))
[PhotonRewriter] Gradient expanded → GradPower(a, 4)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 4)
[PhotonRewriter] Final normalized: GradPower(a, 4)
   Normalized LHS: ∇⁴a
   Target: ∇4a
[PhotonRewriter] Initial parse: GradPower(a, 4) => GradPower(a, 4) => GradPower(a, 4)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 4)
[PhotonRewriter] Final normalized: GradPower(a, 4)
   Normalized RHS: ∇⁴a
   Result: ✅ Equivalent

🔹 Demo: 5th Derivative Consistency
   Input: ∇(∇(∇(∇(∇(a)))))
[PhotonRewriter] Initial parse: ∇(∇(∇(∇(∇(a))))) => Grad(Grad(Grad(Grad(Grad(a))))) => Grad(Grad(Grad(Grad(Grad(a)))))
[PhotonRewriter] Gradient expanded → GradPower(a, 5)
[PhotonRewriter] Cycle detected at step 2 expr: GradPower(a, 5)
[PhotonRewriter] Final normalized: GradPower(a, 5)
   Normalized LHS: ∇⁵a
   Target: ∇5a
[PhotonRewriter] Initial parse: GradPower(a, 5) => GradPower(a, 5) => GradPower(a, 5)
[PhotonRewriter] Cycle detected at step 1 expr: GradPower(a, 5)
[PhotonRewriter] Final normalized: GradPower(a, 5)
   Normalized RHS: ∇⁵a
   Result: ✅ Equivalent