import Mathlib

/-!
v27 — State-Space Scaling Law (Sparse High-Cardinality Telemetry)

Buyer-facing claim:
If a system state has n components (agents/sensors/rows) and each tick mutates only m << n of them,
then "snapshot logging" scales with n per tick, while "template+delta logging" scales with m per tick.

We model a simple byte-cost:
- Each state entry costs E bytes (value + constant structural overhead).
- Each delta edit costs (I + E) bytes: an index token (I) plus the new value payload (E).
- Over a stream of (k+1) states: initial + k updates.

Snapshot transport:
  naiveBytes = (k+1) * (n*E)

Delta transport:
  deltaBytes = (n*E) + k * (m*(I+E))

We prove:
- If m*(I+E) ≤ n*E (sparse updates + cheap indexing), then deltaBytes ≤ naiveBytes.
- And we package the exact savings identity under the same assumption.
-/

namespace SymaticsBridge.V27

/-- Total bytes for snapshot logging of (k+1) full states. -/
def naiveBytes (n E k : Nat) : Nat :=
  (k + 1) * (n * E)

/-- Total bytes for initial state + k sparse deltas, each touching m entries. -/
def deltaBytes (n E I m k : Nat) : Nat :=
  (n * E) + k * (m * (I + E))

/-- Main scaling-law dominance theorem (under a minimal "sparse update" condition). -/
theorem delta_le_naive
    {n E I m k : Nat}
    (h_sparse : m * (I + E) ≤ n * E) :
    deltaBytes n E I m k ≤ naiveBytes n E k := by
  -- delta = nE + k*(m*(I+E)) ≤ nE + k*(nE) = (k+1)*nE
  unfold deltaBytes naiveBytes
  have hk : k * (m * (I + E)) ≤ k * (n * E) := by
    exact Nat.mul_le_mul_left k h_sparse
  -- add nE both sides
  have : (n * E) + k * (m * (I + E)) ≤ (n * E) + k * (n * E) := by
    exact Nat.add_le_add_left hk (n * E)
  -- rewrite RHS as (k+1)*(nE)
  simpa [Nat.mul_add, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm] using this

/-- Exact savings identity (what buyers care about): naive = delta + k*(nE - m*(I+E)). -/
theorem savings_identity
    {n E I m k : Nat}
    (h_sparse : m * (I + E) ≤ n * E) :
    naiveBytes n E k =
      deltaBytes n E I m k + k * ((n * E) - (m * (I + E))) := by
  unfold naiveBytes deltaBytes
  -- naive = nE + k*nE
  -- delta = nE + k*m*(I+E)
  -- so naive = delta + k*(nE - m*(I+E)) provided m*(I+E) ≤ nE
  have hmul : k * (m * (I + E)) ≤ k * (n * E) := Nat.mul_le_mul_left k h_sparse

  -- We want: (nE + k*nE) = (nE + k*mX) + k*(nE - mX)
  -- where mX = m*(I+E). Use Nat arithmetic with sub guarded by h_sparse.
  set nE : Nat := n * E
  set mX : Nat := m * (I + E)

  have : (k * nE) = (k * mX) + k * (nE - mX) := by
    -- factor k out of the subtraction term using Nat.mul_sub_left_distrib (requires mX ≤ nE)
    -- but Nat.mul_sub_left_distrib is for (a-b)*c; we use:
    -- k*nE = k*mX + k*(nE-mX)
    -- since k*nE - k*mX = k*(nE-mX) and k*mX ≤ k*nE
    have hk_le : k * mX ≤ k * nE := by simpa [mX, nE] using hmul
    -- k*nE = k*mX + (k*nE - k*mX)
    calc
      k * nE = k * mX + (k * nE - k * mX) := by
        exact (Nat.add_sub_of_le hk_le).symm
      _ = k * mX + k * (nE - mX) := by
        -- (k*nE - k*mX) = k*(nE-mX) when mX ≤ nE
        -- Use Nat.mul_sub_left_distrib: k*(nE-mX) = k*nE - k*mX
        have hmX_le : mX ≤ nE := by
          -- from h_sparse
          simpa [mX, nE] using h_sparse
        -- rewrite (k*nE - k*mX)
        simpa [Nat.mul_sub_left_distrib, hmX_le] using (rfl : (k * nE - k * mX) = (k * nE - k * mX))

  -- finish by adding nE on both sides
  calc
    (k + 1) * (n * E)
        = nE + k * nE := by
            simp [nE, Nat.mul_add, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]
    _ = (nE + k * mX) + k * (nE - mX) := by
            -- substitute the identity for k*nE
            simpa [Nat.add_assoc, Nat.add_left_comm, Nat.add_comm] using congrArg (fun t => nE + t) this
    _ = (n * E + k * (m * (I + E))) + k * ((n * E) - (m * (I + E))) := by
            simp [nE, mX]

end SymaticsBridge.V27